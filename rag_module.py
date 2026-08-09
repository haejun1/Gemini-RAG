import os
import time
import gc
from typing import Optional
from operator import itemgetter
from dotenv import load_dotenv

from google import genai
from google.genai import types  # 최신 Native SDK types
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import fitz  # PyMuPDF 이미지/표 직접 파싱용
import io
from PIL import Image

# 환경 변수 로드
load_dotenv()


class HybridGeminiManager:
    """
    지정된 3개 주요 모델을 최우선 검증하며, 미지원 시 최신 별칭(gemini-flash-latest)으로 고속 폴백합니다.
    """
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

        # 🎯 지정된 핵심 모델 리스트 (기본값: gemini-3.6-flash)
        self.PRIMARY_LLM_CANDIDATES = [
            "gemini-3.6-flash",          # 기본 및 최우선 추천 모델 (표준)
            "gemini-3.1-flash-lite",     # 경량/고속 모델
            "gemini-3.1-pro-preview",    # 고성능 정밀 추론 모델
            "gemini-flash-latest"        # 3개 다 불가능할 경우를 대비한 최신 표준 별칭 (Fallback)
        ]

        # 📐 고성능 정밀 텍스트 임베딩 모델
        self.EMBEDDING_MODEL = "models/gemini-embedding-2"

    def get_best_llm_model(self, preferred_model: Optional[str] = None) -> str:
        """
        사용 가능한 LLM 모델을 신속하게 선별합니다.
        """
        try:
            # 내 계정에서 현재 활성화된 모델 목록 스캐닝
            raw_models = list(self.client.models.list()) if self.client else []
            available_models = [m.name.replace("models/", "") for m in raw_models]
        except Exception as e:
            print(f"[경고] 모델 목록 스캐닝 실패: {e}. 기본 모델(gemini-3.6-flash)을 반환합니다.")
            return "gemini-3.6-flash"

        # 1. 사용자가 직접 지정한 모델이 있고 사용 가능하면 우선 적용
        if preferred_model:
            clean_preferred = preferred_model.replace("models/", "")
            if clean_preferred in available_models:
                return clean_preferred

        # 2. 지정된 후보 리스트 순서대로 존재하는지 순차 매칭
        for candidate in self.PRIMARY_LLM_CANDIDATES:
            if candidate in available_models:
                return candidate

        # 3. 최후의 보루 (기본값 고정)
        return "gemini-3.6-flash"

    def get_best_embedding_model(self) -> str:
        """최신 gemini-embedding-2 모델을 반환합니다."""
        return self.EMBEDDING_MODEL


class RAGModule:
    """
    [API 최적화 RAG 파이프라인 엔진]
    대기시간 없이 고속 파싱 및 지능형 RAG 체인을 생성합니다.

    다중 파일 목록(pdf_paths) 지원 및 
    FAISS 기반 Multi-Document 스토리지 및 Native Gemini 멀티모달 연동
    """
    def __init__(
        self, 
        pdf_paths: list[str],  # 단일 str -> list[str] 다량 문서 경로 리스트
        chunk_size: int = 700, 
        chunk_overlap: int = 100,
        preferred_llm: Optional[str] = None
    ):
        self.pdf_paths = pdf_paths if isinstance(pdf_paths, list) else [pdf_paths]
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 모델 매니저를 통한 최적 모델 할당
        self.model_manager = HybridGeminiManager()
        self.llm_model_name = self.model_manager.get_best_llm_model(preferred_llm)
        self.embedding_model_name = self.model_manager.get_best_embedding_model()

        print(f"==================================================")
        print(f"[RAG 엔진 가동] 적용 LLM: {self.llm_model_name}")
        print(f"[RAG 엔진 가동] 적용 임베딩: {self.embedding_model_name}")
        print(f"==================================================")

        # 전체 분할 문서 객체(all_split_docs) / 다중 문서 다중 FAISS / 통합 Vectorstore 구축
        self.all_split_docs, self.vectorstore = self._build_vectorstore()

    def _generate_image_caption(self, pil_image: Image.Image) -> str:
        """
        PDF 내부 이미지/표 자원을 Gemini Vision으로 요약 설명(캡션)으로 전환합니다.
        """
        client = self.model_manager.client or genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        try:
            # Bytes 변환 후 전달
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()

            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",  # 고속 경량 멀티모달 사용
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                    """
                    [역할]: 기술 문서 내 표/차트/이미지 데이터 추출 전문가
                    [지시]: 아래 규칙에 따라 이미지를 정밀 분석하여 텍스트로 전환하세요.
                    1. 표(Table)인 경우: 행과 열의 주요 항목 이름, 숫자, 사양, 단위 데이터를 빠짐없이 텍스트로 나열할 것.
                    2. 차트/그림인 경우: 그래프의 축 의미, 핵심 수치, 결론적 기술 메세지를 명확히 요약할 것.
                    3. 수식이나 텍스트가 있는 경우: 텍스트를 오타 없이 그대로 텍스트화할 것.
                    4. 불필요한 인사말 없이 오직 정보 텍스트만 2~3문장 내외로 출력할 것.
                    """
                ]
            )
            return response.text if response.text else ""
        except Exception as e:
            print(f"[경고] 이미지 캡셔닝 실패: {e}")
            return ""

    def _build_vectorstore(self):
        """
        여러 PDF 문서를 순회하며 문맥 조각을 하나의 통합 FAISS DB로 병합 생성
        """
        all_split_docs = []

        for pdf_path in self.pdf_paths:
            if not os.path.exists(pdf_path):
                continue
            
            # 1. PDF 텍스트 로드 및 메타데이터(출처 파일명) 할당
            loader = PyMuPDFLoader(pdf_path)
            docs = loader.load()

            try:
                doc_pdf = fitz.open(pdf_path)
                for page_idx, page in enumerate(doc_pdf):
                    image_list = page.get_images(full=True)
                    if image_list and page_idx < len(docs):
                        captions = []
                        # 페이지당 주요 이미지 최대 3개까지만 처리 (속도/비용 방어)
                        for img_info in image_list[:3]:
                            xref = img_info[0]
                            base_image = doc_pdf.extract_image(xref)
                            image_bytes = base_image["image"]
                            pil_img = Image.open(io.BytesIO(image_bytes))

                            # 너무 작거나 가로세로 비가 찌그러진 아이콘성 이미지 스킵
                            if pil_img.width < 100 or pil_img.height < 100:
                                continue

                            caption_text = self._generate_image_caption(pil_img)
                            if caption_text:
                                captions.append(f"\n[페이지 내 시각 데이터 요약 (표/이미지)]: {caption_text}\n")
                        
                        if captions and page_idx < len(docs):
                            docs[page_idx].page_content += "\n" + "".join(captions)
                doc_pdf.close()
            except Exception as e:
                print(f"[경고] PDF 이미지 처리 중 예외 발생 (기본 텍스트로만 진행): {e}")
            
            for doc in docs:
                doc.metadata["source_file"] = os.path.basename(pdf_path)

            # 2. 텍스트 분할 (청킹 - separators 적용)
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            all_split_docs.extend(text_splitter.split_documents(docs))

        # 3. 임베딩 엔진 생성 및 FAISS 벡터 DB 구축
        embeddings = GoogleGenerativeAIEmbeddings(model=self.embedding_model_name)
        
        try:
            vectorstore = FAISS.from_documents(documents=all_split_docs, embedding=embeddings)
            # 가비지 컬렉션으로 임시 파싱 객체 메모리 즉시 정제
            gc.collect()
            return vectorstore
        except Exception as e:
            print(f"[오류] FAISS 벡터 DB 생성 중 예외 발생: {e}")
            raise e
        
    def analyze_multimodal_pdf_native(self, pdf_path: str, user_prompt: str) -> str:
        """
        [하위 호환성 유지용 메서드 레거시 백업]
        이미지 캡셔닝 기반 통합 FAISS 체인이 가동되므로, 동일 RAG 체인을 경유하도록 안전 우회합니다.
        """
        chain = self.get_rag_chain(k=4)
        return chain.invoke({"question": user_prompt, "chat_history": []})


    def get_rag_chain(
        self, 
        k: int = 4,
        difficulty_level: str = "🔬 전문가 수준",
        output_format: str = "💬 일반 대화형 답변"
    ):
        # 1. FAISS 벡터 검색기 (의미 기반)
        faiss_retriever = self.vectorstore.as_retriever(search_kwargs={"k": k})

        # 2. BM25 키워드 검색기 (정확한 단어/고유명사/수치 기반)
        bm25_retriever = BM25Retriever.from_documents(self.all_split_docs)
        bm25_retriever.k = k

        # 3. EnsembleRetriever 결합 (가중치: FAISS 0.6 + BM25 0.4)
        hybrid_retriever = EnsembleRetriever(
            retrievers=[faiss_retriever, bm25_retriever],
            weights=[0.6, 0.4]
        )

        # [1. 시스템 페르소나 고도화 (전천후 AI 수석 컨설턴트)]
        role_instruction = (
            "당신은 업로드된 첨부 문서의 도메인(AI/SW, 바이오/의료, 제조/공정, 특허/법률, 신소재, 조선/해양 등)을 "
            "스스로 완벽히 파악하여, 해당 분야 수석 연구원 수준의 정밀한 기술적 시각과 엄격한 사실 검증 태도로 답변을 제공하는 "
            "'AI 기술 문서 분석 수석 컨설턴트'입니다."
        )

        # [2. 답변 난이도 제어]
        if "비전공자" in difficulty_level:
            difficulty_instruction = (
                "전문 용어나 난해한 기술 사양은 직관적인 비유와 쉬운 언어로 순화해서 설명하세요. "
                "내용을 한눈에 파악할 수 있도록 개요, 핵심 포인트, 결론으로 알기 쉽게 정리하세요."
            )
        else:  # 전문가 수준
            difficulty_instruction = (
                "기술적 사양, 전문 용어, 수치, 구조를 생략 없이 정밀하고 깊이 있게 분석하세요. "
                "기초 개념이나 단순 정의에 대한 지루한 설명은 자제하고, 핵심 인과관계 및 기술적 메커니즘 위주로 본론을 바로 제시하세요."
            )

        # [3. 출력 형태 동적 분기]
        if "PPT 슬라이드" in output_format:
            format_instruction = """
#출력형식: 프레젠테이션 발표용 슬라이드 양식
- 답변 내용의 정보량에 따라 슬라이드 개수를 유기적으로 구성하세요. (페이지 수 제한 없이 필요한 만큼 구성)
- 각 슬라이드는 아래 마크다운 형태를 반드시 준수하세요.

---
### 🖼️ [Slide 1: 슬라이드 제목]
- **핵심 요약**: (발표 시 한눈에 들어오는 핵심 메세지 1문장)
* (발표용 불렛포인트 1)
* (발표용 불렛포인트 2)
> 💡 **발표자 스크립트 / 참고 요약**: (발표자가 언급할 추가 설명)

---
### 🖼️ [Slide 2: ...]
...
---
*(마지막 줄에는 슬라이드의 시각적 발표를 위한 '추천 디자인 테마/배색 아이디어'를 1줄 팁으로 덧붙이세요.)*
"""
        elif "마크다운 보고서" in output_format:
            format_instruction = """
#출력형식: 정식 기술 보고서 양식 (Markdown)
# 📊 [기술 요약 보고서]: {사용자 질문의 핵심 주제}

## 1. 서론 (개요 및 목적)
- (문서에 기반한 기술적 배경 및 요지)

## 2. 본론 (핵심 기술 분석 및 데이터)
- (수치, 사양, 구조, 표 데이터를 마크다운 표| | 또는 불렛포인트로 정밀 분류)

## 3. 결론 (종합 의견 및 시사점)
- (분석 결론 및 핵심 시사점 정리)
"""
        else:  # 일반 대화형
            format_instruction = """
#출력형식:
* [핵심 요약]: 참고 문서에서 찾은 핵심 근거를 단계를 나누어 간결히 정리
* [최종 답변]: 알기 쉽게 마크다운으로 구조화된 최종 답변 제공
"""

        # 고도화된 프롬프트 템플릿 결합
        template = f"""
#역할 및 페르소나
{role_instruction}

#명령문
당신은 업로드된 기술 문서를 기반으로 사실에 입각해 정밀하게 답변하는 전문 분석 에이전트입니다.
아래 지침과 제약 조건을 엄격히 준수하여 답변을 작성하세요.

#답변 난이도 지침
{difficulty_instruction}

#제약조건
1. 오직 아래 제공된 [참고 문서 내용]에 명시된 사실만을 기반으로 답변하세요. (지어내기 절대 금지)
2. 관련 내용이 없을 경우 "제공된 문서에서 관련 내용을 찾을 수 없습니다."라고 솔직히 답하세요.
3. 문서 내 표나 이미지 캡션 데이터가 포함되어 있다면 수치와 사양을 빠짐없이 활용하세요.

#이전 대화 내용
{{chat_history}}

#참고 문서 내용
{{context}}

#입력문 (사용자 질문)
{{question}}

{format_instruction}
"""

        prompt = ChatPromptTemplate.from_template(template)
        llm = ChatGoogleGenerativeAI(
            model=self.llm_model_name,
            temperature=0,
            convert_system_message_to_human=True
        )

        retrieval_chain = RunnableParallel({
            "context_docs": itemgetter("question") | hybrid_retriever,
            "question": itemgetter("question"),
            "chat_history": itemgetter("chat_history")
        })

        return retrieval_chain | RunnableParallel({
            "answer": (
                RunnablePassthrough.assign(
                    context=lambda x: "\n\n".join([doc.page_content for doc in x["context_docs"]])
                )
                | prompt
                | llm
                | StrOutputParser()
            ),
            "context_docs": itemgetter("context_docs")
        })