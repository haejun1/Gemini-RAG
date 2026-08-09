import os
import hashlib
import gc
import traceback
import streamlit as st
from rag_module import RAGModule  # 백엔드 모듈 연동
from document_exporter import create_styled_pptx, create_styled_docx

# Streamlit Cloud 및 로컬 API 키 예외 처리
try:
    if "GOOGLE_API_KEY" in st.secrets:
        os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
    elif "google_apikey" in st.secrets:
        os.environ["GOOGLE_API_KEY"] = st.secrets["google_apikey"]
except Exception:
    pass

# 기본 페이지 레이아웃 세팅 (Tech-GPT 브랜드 반영)
st.set_page_config(
    page_title="Tech-GPT : 기술 문서 분석 AI 비서",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded"
)

def calculate_file_hash(file_bytes: bytes) -> str:
    """PDF 파일 내용 기반 고유 해시값 계산"""
    return hashlib.md5(file_bytes).hexdigest()

# 1시간 후 메모리에서 쓰이지 않는 FAISS DB 객체 자동 파기
@st.cache_resource(show_spinner=False, ttl="1h")
def load_rag_module(pdf_paths: list[str], combined_hash: str, chunk_size: int, chunk_overlap: int, preferred_llm: str):
    """
    다량 문서 경로 목록과 통합 파일 해시를 받아서 RAGModule을 구축합니다.
    """
    try:
        model_arg = None if "Gemini 3.6 Flash" in preferred_llm else preferred_llm
        
        module = RAGModule(
            pdf_paths=pdf_paths,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            preferred_llm=model_arg
        )
        return module, None
    except Exception as e:
        return None, str(e)

# ==========================================================================
# 🛠️ 사이드바 제어 패널 (개선된 UI/UX)
# ==========================================================================
with st.sidebar:
    st.title("⚙️ 스마트 설정 패널")
    st.markdown("기술 문서 분석을 위한 AI 엔진 및 답변 양식을 조율합니다.")
    st.divider()

    # 1. 파일 업로드 영역 (다중 문서 지원 및 안내 개선)
    st.subheader("📁 기술 문서 등록")
    uploaded_files = st.file_uploader(
        "분석할 PDF 기술 문서를 모두 선택해 주세요 (복수 선택 가능)", 
        type=['pdf'], 
        accept_multiple_files=True,
        help="Ctrl 키를 누른 상태에서 여러 문서를 한 번에 올리시거나 drag-and-drop 하실 수 있습니다."
    )
    st.caption("✨ **Native 멀티모달 기본 탑재:** PDF 내 텍스트뿐만 아니라 **표, 차트, 이미지**까지 자동으로 인식하여 정밀 분석합니다.")
    st.divider()

    # 2. 모델 선택 및 동적 설명 변경 (요구사항 4 반영)
    st.subheader("🤖 AI 분석 엔진 선택")
    
    model_options = {
        "gemini-3.6-flash": "⚡ Gemini 3.6 Flash (표준 추천)",
        "gemini-3.1-pro-preview": "🏆 Gemini 3.1 Pro (고성능 정밀추론)",
        "gemini-3.1-flash-lite": "🚀 Gemini 3.1 Flash-Lite (초고속 경량)",
        "gemini-flash-latest": "🔄 Gemini Flash Latest (최신 모델 자동 갱신)"
    }
    
    selected_model_key = st.selectbox(
        "AI 모델 지정",
        options=list(model_options.keys()),
        format_func=lambda x: model_options[x],
        index=0,
        label_visibility="collapsed"
    )

    # 선택된 모델에 따른 동적 안내 문구 제공
    if selected_model_key == "gemini-3.6-flash":
        st.info("💡 **엔진 안내:** 기본값으로 가장 안정적이고 속도와 정확도의 균형이 뛰어난 'Gemini 3.6 Flash' 모델이 가동됩니다.")
    elif selected_model_key == "gemini-3.1-pro-preview":
        st.success("💡 **엔진 안내:** 최고 성능의 'Pro' 모델이 선택되었습니다. 수식, 표, 다단 구조 특허 등 난이도 높은 기술 문서의 정밀 분석에 적합합니다.")
    elif selected_model_key == "gemini-3.1-flash-lite":
        st.warning("💡 **엔진 안내:** 가장 가볍고 빠른 'Lite' 모델이 선택되었습니다. 단순 요약 및 빠른 질의응답 응답성에 최적화되어 있습니다.")
    elif selected_model_key == "gemini-flash-latest":
        st.info("💡 **엔진 안내:** 구글의 최신 표준 업그레이드 사양이 항상 자동 적용되는 상시 최신화 모델입니다.")
    st.divider()

    # 3. 커스텀 프롬프트 옵션 제어 구역
    st.subheader("🎭 답변 스타일 설정")

    difficulty_level = st.radio(
        "답변 수준 선택",
        options=[
            "🔬 전문가 수준 (정밀 수치/구조 중심)",
            "🌱 비전공자 수준 (쉽고 체계적인 정리)"
        ],
        index=0
    )

    output_format = st.radio(
        "출력 형태 지정",
        options=[
            "💬 일반 대화형 답변",
            "📑 마크다운 보고서 (서론-본론-결론)",
            "📊 PPT 슬라이드 발표 형식"
        ],
        index=0
    )

    if "PPT 슬라이드" in output_format:
        st.info(
            "💡 **PPT 활용 팁:** 질문할 때 *'슬라이드 4장으로 요약해줘'* 나 "
            "*'다크모드 테마 추천도 포함해줘'* 처럼 질문창에 세부 요청을 붙이시면 더욱 정교하게 답변합니다."
        )
    st.divider()

    # 4. 문서 분석 목적별 사전 설정
    st.subheader("🎯 문서 분석 목적 및 정밀도")
    st.markdown("질문 성격에 맞게 AI가 문서를 읽는 깊이를 자동으로 조율합니다.")

    analysis_mode = st.radio(
        "분석 방식 선택",
        options=[
            "⚖️ 표준 기술 분석 (추천)",
            "⚡ 빠른 단답 / 핵심 검색",
            "📖 심층 기술 보고서 / 전체 요약"
        ],
        index=0
    )

    # 선택한 모드에 따른 백엔드 파라미터 매핑
    if analysis_mode == "⚖️ 표준 기술 분석 (추천)":
        chunk_size = 800
        chunk_overlap = 100
        k_value = 4
        st.caption("🔍 **작동 모드:** 문맥을 800자 단위로 자연스럽게 읽고 관련 문서 4개를 종합 참조합니다.")
    elif analysis_mode == "⚡ 빠른 단답 / 핵심 검색":
        chunk_size = 400
        chunk_overlap = 50
        k_value = 5
        st.caption("🔍 **작동 모드:** 특정 키워드, 수치, 담당자, 규격 정보 등 정밀한 사실 관계를 즉시 찾고 분석하는 데 최적화되어 있습니다.")
    elif analysis_mode == "📖 심층 기술 보고서 / 전체 요약":
        chunk_size = 1200
        chunk_overlap = 200
        k_value = 3
        st.caption("🔍 **작동 모드:** 문단을 크게 묶어 전체적인 흐름, 기술 배경, 장단점 비교 등 통섭적 질의에 답변합니다.")

    st.divider()

    # 세션 초기화 버튼
    if st.button("🧹 대화 내역 초기화", use_container_width=True):
        st.session_state.messages = []
        gc.collect()
        st.rerun()

# ==========================================================================
# 💬 메인 화면 영역 (Tech-GPT 브랜드 및 인터페이스)
# ==========================================================================
st.title("💡 Tech-GPT : 테크 전문가를 위한 AI 문서 분석 비서")
st.markdown("업로드하신 **기술 사양서, 특허 문서, 연구 논문**의 내용을 정밀 분석하여 정확한 사실 기반 답변을 제공합니다.")

if uploaded_files:
    temp_dir = "temp_files"
    os.makedirs(temp_dir, exist_ok=True)
    
    saved_temp_paths = []
    combined_hash_str = ""

    # 다중 문서 파일 수거 및 통합 해시 생성
    for up_file in uploaded_files:
        t_path = os.path.join(temp_dir, up_file.name)
        f_bytes = up_file.getvalue()
        
        with open(t_path, "wb") as f:
            f.write(f_bytes)
            
        saved_temp_paths.append(t_path)
        combined_hash_str += calculate_file_hash(f_bytes)

    final_combined_hash = hashlib.md5(combined_hash_str.encode()).hexdigest()

    # RAG 파이프라인 가동
    with st.spinner(f"⚡ {len(uploaded_files)}개 기술 문서를 지능형 지식 DB로 변환 중입니다..."):
        rag_module, error_msg = load_rag_module(
            saved_temp_paths, final_combined_hash, chunk_size, chunk_overlap, selected_model_key
        )

    # 임시 파일 디스크 즉시 정리
    for path_to_del in saved_temp_paths:
        if os.path.exists(path_to_del):
            try:
                os.remove(path_to_del)
            except Exception:
                pass

    if error_msg:
        st.error("기술 문서 분석 중 문제가 발생했습니다.")
        st.info(f"상세 오류 원인: {error_msg}")
        st.stop()

    st.success(f"🎉 총 {len(uploaded_files)}개 기술 문서 분석이 완료되었습니다! 아래 대화창에서 자유롭게 전문 질문을 입력하세요.")
    
    # 시스템 작동 스펙 모니터
    with st.expander("🔍 현재 가동 중인 Tech-GPT 엔진 정보 확인하기", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(label="선택된 AI 모델", value=rag_module.llm_model_name.replace("models/", ""))
        with c2:
            st.metric(label="임베딩 파이프라인", value=rag_module.embedding_model_name.replace("models/", ""))
        with c3:
            st.metric(label="참조 문맥 분량(Top-K)", value=f"{k_value}개 구역")
    
    rag_chain = rag_module.get_rag_chain(
        k=k_value,
        difficulty_level=difficulty_level,
        output_format=output_format
    )
    st.session_state.rag_chain = rag_chain

    # 새 문서 묶음 업로드 시 세션 자동 초기화
    if "messages" not in st.session_state or st.session_state.get("last_file_hash") != final_combined_hash:
        st.session_state.last_file_hash = final_combined_hash
        st.session_state.messages = [
            {"role": "assistant", "content": f"안녕하세요! 등록해주신 {len(uploaded_files)}개 기술 문서 검토를 마쳤습니다. 궁금하신 기술적 내용을 물어보세요!"}
        ]

    # 대화 출력
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 사용자 질문 및 답변 처리
    if user_query := st.chat_input("기술 문서에 대해 궁금한 점을 입력하세요 (예: 본 문서의 핵심 특허 범위 요약해줘)"):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("🤔 등록된 기술 문서에서 하이브리드 검색으로 근거를 추적 중입니다..."):
                try:
                    # 💡 RunnableParallel 실행 결과에서 answer(답변)와 context_docs(출처 문서) 분리 수령
                    result = st.session_state.rag_chain.invoke({
                        "question": user_query,
                        "chat_history": st.session_state.messages
                    })
                    
                    response_text = result["answer"]
                    context_docs = result["context_docs"]

                    # 1. 텍스트 답변 출력
                    st.markdown(response_text)

                    # 2. 답변 하단에 근거 출처 문서(Source Reference) 명시
                    if context_docs:
                        st.markdown("---")
                        st.caption("📌 **[답변 근거 문서 및 출처 레퍼런스]**")
                        sources_set = set()
                        for doc in context_docs:
                            src = doc.metadata.get("source_file", "알 수 없는 문서")
                            page = doc.metadata.get("page_number", "N/A")
                            sources_set.add(f"📄 `{src}` (Page {page})")
                        
                        for src_info in sorted(sources_set):
                            st.caption(f"• {src_info}")

                    if "PPT 슬라이드" in output_format:
                        pptx_path = create_styled_pptx(response_text, "Tech_GPT_Presentation.pptx")
                        with open(pptx_path, "rb") as f:
                            st.download_button(
                                label="📥 [PPTX] 발표용 슬라이드 원본 파일 다운로드",
                                data=f,
                                file_name="Tech_GPT_Presentation.pptx",
                                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                use_container_width=True
                            )
                    elif "마크다운 보고서" in output_format:
                        docx_path = create_styled_docx(response_text, "Tech_GPT_Report.docx")
                        with open(docx_path, "rb") as f:
                            st.download_button(
                                label="📥 [DOCX] 정식 기술 보고서 원본 파일 다운로드",
                                data=f,
                                file_name="Tech_GPT_Report.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                use_container_width=True
                            )

                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                except Exception as e:
                    st.error(f"답변 생성 중 문제가 발생했습니다: {e}")

else:
    st.info("👈 먼저 좌측 사이드바의 [기술 문서 등록] 칸에 분석할 PDF 파일들을 업로드해 주세요.")