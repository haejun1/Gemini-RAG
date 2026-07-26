import os
import time
from typing import List, Optional
from dotenv import load_dotenv

import google.generativeai as genai
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# 환경 변수에서 구글 API 키를 불러옵니다.
load_dotenv()


class HybridGeminiManager:
    """
    구글 인공지능 모델 관리 클래스입니다.
    사용 가능한 모델을 동적으로 확인하고 안정적인 모델을 우선 선택합니다.
    """
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)

        # 안정성과 속도가 검증된 텍스트 생성 모델 후보 순위입니다.
        self.PRIMARY_LLM_CANDIDATES = [
            "gemini-flash-lite-latest",
            "gemini-2.0-flash-lite",
            "gemini-2.0-flash",
            "gemini-flash-latest",
            "gemini-1.5-flash"
        ]

        # 텍스트 임베딩 변환 모델 후보 순위입니다.
        self.PRIMARY_EMBEDDING_CANDIDATES = [
            "models/gemini-embedding-001",
            "models/gemini-embedding-2"
        ]

    def get_best_llm_model(self, preferred_model: Optional[str] = None) -> str:
        """
        현재 계정에서 사용 가능한 최적의 언어 모델 이름을 반환합니다.
        """
        try:
            raw_models = [
                m.name for m in genai.list_models()
                if "generateContent" in m.supported_generation_methods
            ]
            available_models = [m.replace("models/", "") for m in raw_models]
        except Exception as e:
            print(f"모델 목록 조회 중 오류 발생: {e}. 기본 모델을 반환합니다.")
            return "gemini-flash-lite-latest"

        # 사용자가 직접 지정한 모델이 있고 사용 가능하면 우선 적용합니다.
        if preferred_model:
            clean_preferred = preferred_model.replace("models/", "")
            if clean_preferred in available_models:
                return clean_preferred

        # 검증된 모델 목록 중 사용 가능한 것을 순서대로 선택합니다.
        for candidate in self.PRIMARY_LLM_CANDIDATES:
            if candidate in available_models:
                return candidate

        # 검증 목록이 모두 실패하면 특수 목적 모델을 제외한 대안 모델을 탐색합니다.
        excluded_keywords = ["tts", "image", "robotics", "computer-use", "deep-research", "audio", "vision", "omni", "lyria", "antigravity", "banana"]
        
        safe_dynamic_models = [
            m for m in available_models
            if not any(bad_kw in m.lower() for bad_kw in excluded_keywords)
        ]

        if safe_dynamic_models:
            lite_dynamic = [m for m in safe_dynamic_models if "lite" in m.lower()]
            if lite_dynamic:
                return lite_dynamic[0]
            
            flash_dynamic = [m for m in safe_dynamic_models if "flash" in m.lower()]
            if flash_dynamic:
                return flash_dynamic[0]

            return safe_dynamic_models[0]

        return "gemini-flash-lite-latest"

    def get_best_embedding_model(self) -> str:
        """
        사용 가능한 최적의 임베딩 모델 이름을 반환합니다.
        """
        try:
            available_models = [
                m.name for m in genai.list_models()
                if "embedContent" in m.supported_generation_methods
            ]
        except Exception:
            return "models/gemini-embedding-001"

        for candidate in self.PRIMARY_EMBEDDING_CANDIDATES:
            if candidate in available_models:
                return candidate

        for model in available_models:
            if "embedding" in model.lower():
                return model

        return available_models[0] if available_models else "models/gemini-embedding-001"


class RAGModule:
    """
    문서 기반 검색 증강 생성 파이프라인을 총괄하는 핵심 모듈입니다.
    """
    def __init__(
        self, 
        pdf_path: str, 
        chunk_size: int = 700, 
        chunk_overlap: int = 100,
        preferred_llm: Optional[str] = None
    ):
        self.pdf_path = pdf_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 모델 관리자를 통해 최적의 인공지능 모델을 할당합니다.
        self.model_manager = HybridGeminiManager()
        self.llm_model_name = self.model_manager.get_best_llm_model(preferred_llm)
        self.embedding_model_name = self.model_manager.get_best_embedding_model()

        print("=" * 50)
        print(f"선택된 언어 모델: {self.llm_model_name}")
        print(f"선택된 임베딩 모델: {self.embedding_model_name}")
        print("=" * 50)

        # 문서 벡터 데이터베이스를 구축합니다.
        self.vectorstore = self._build_vectorstore()

    def _build_vectorstore(self):
        """
        PDF 문서를 불러와 조각으로 나누고 벡터로 변환하여 데이터베이스에 저장합니다.
        """
        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {self.pdf_path}")

        # 1단계: PDF 문서 내용을 텍스트로 추출합니다.
        loader = PyMuPDFLoader(self.pdf_path)
        docs = loader.load()

        # 2단계: 문맥이 끊기지 않도록 일정한 크기로 텍스트를 분할합니다.
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        split_documents = text_splitter.split_documents(docs)

        # 3단계: 임베딩 처리기를 생성합니다.
        embeddings = GoogleGenerativeAIEmbeddings(model=self.embedding_model_name)

        # 4단계: 무료 버전 요청 제한 오류를 방지하기 위해 나누어 처리합니다.
        batch_size = 5
        vectorstore = None

        for i in range(0, len(split_documents), batch_size):
            batch_docs = split_documents[i:i + batch_size]
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if vectorstore is None:
                        vectorstore = FAISS.from_documents(documents=batch_docs, embedding=embeddings)
                    else:
                        vectorstore.add_documents(documents=batch_docs)
                    break
                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                        wait_time = (attempt + 1) * 12
                        print(f"요청 제한 감지. {wait_time}초 후 다시 시도합니다. ({attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        print(f"임베딩 처리 중 오류 발생: {e}")
                        raise e

            time.sleep(2.0)

        return vectorstore

    def get_rag_chain(self, k: int = 3):
        """
        질문과 관련 문서를 연결하여 정확한 답변을 생성하는 대화 체인을 구성합니다.
        """
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": k})

        # 정확도와 논리적 추론을 유도하는 프롬프트 템플릿입니다.
        template = """#명령문
당신은 업로드된 문서를 기반으로 정확하고 깊이 있는 정보를 제공하는 문서 분석 전문 상담원입니다.
아래의 제약 조건과 참고 문서 내용을 바탕으로 사용자 질문에 대해 차근차근 생각해 본 뒤 명확하게 답변해 주세요.

#제약조건
1. 오직 아래 제공된 참고 문서 내용에 명시된 사실만을 기반으로 답변할 것.
2. 문서에 관련 내용이 없을 경우 절대 내용을 지어내지 말고 해당 내용을 찾을 수 없다고 솔직히 답할 것.
3. 답변은 마크다운 형식을 활용하여 가독성 있게 작성할 것.
4. 복잡한 질문일 경우 단계를 나누어 핵심 요지를 설명할 것.

#참고 문서 내용
{context}

#입력문
{question}

#출력형식
- [핵심 요약]: 참고 문서에서 찾은 핵심 근거 정리
- [답변]: 알기 쉽게 구조화된 최종 답변 제공"""

        prompt = ChatPromptTemplate.from_template(template)

        # 인공지능 생성 모델 객체를 생성합니다.
        llm = ChatGoogleGenerativeAI(
            model=self.llm_model_name,
            temperature=0,
            convert_system_message_to_human=True
        )

        rag_chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )

        return rag_chain