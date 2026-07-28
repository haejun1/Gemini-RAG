import streamlit as st
import os
import re
import hashlib
from rag_module import RAGModule  # 백엔드 모듈 연결

# 웹 페이지의 기본 틀을 설정합니다.
st.set_page_config(
    page_title="AI 문서 분석 비서",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

def calculate_file_hash(file_bytes: bytes) -> str:
    """파일 내용의 고유한 MD5 해시값을 계산합니다."""
    return hashlib.md5(file_bytes).hexdigest()

# 분석 모듈을 불러오고 컴퓨터 기억 장치에 임시 저장합니다.
    # 캐시 키에 file_hash를 추가하여 파일명이 같아도 내용이 바뀌면 캐시를 갱신합니다.
@st.cache_resource(show_spinner=False, ttl="1h")
def load_rag_module(pdf_path: str, file_hash: str, chunk_size: int, chunk_overlap: int, preferred_llm: str):
    """
    문서 분석 모듈을 안전하게 불러오고 오류를 처리합니다.
    """
    try:
        model_arg = None if preferred_llm == "자동 선택 (추천)" else preferred_llm
        
        module = RAGModule(
            pdf_path=pdf_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            preferred_llm=model_arg
        )
        return module, None
    except Exception as e:
        return None, str(e)

# 사이드바 영역: 파일 업로드와 세부 설정을 하나의 흐름으로 배치하여 직관성을 높였습니다.
with st.sidebar:
    st.header("🛠️ 대화 설정 및 파일 관리")
    st.markdown("분석할 문서를 업로드하고 맞춤형 설정을 조정해 보세요.")
    st.divider()

    # 1. 파일 업로드 영역을 사이드바 상단에 배치하여 자연스러운 진입 동선 제공
    st.subheader("📁 문서 파일 첨부")
    uploaded_file = st.file_uploader("PDF 파일을 올려주세요", type=['pdf'], label_visibility="collapsed")
    st.divider()

    # 2. 인공지능 모델 선택 설정
    st.subheader("🤖 인공지능 모델")
    preferred_model = st.selectbox(
        "사용할 모델 선택",
        options=[
            "자동 선택 (추천)",
            "gemini-flash-lite-latest",
            "gemini-2.0-flash-lite",
            "gemini-2.0-flash",
            "gemini-flash-latest"
        ],
        index=0,
        label_visibility="collapsed"
    )
    st.caption("✨ 자동 선택을 이용하시면 가장 안정적인 모델이 적용됩니다.")
    st.divider()

    # 3. 문서 조각 크기 설정 (청크 크기)
    st.subheader("📏 문서 조각 크기")
    chunk_size = st.slider(
        "조각 크기", 
        min_value=300, max_value=1500, value=700, step=100,
        label_visibility="collapsed"
    )
    st.caption("💡 문서를 나누는 단위입니다. 700에서 800 사이가 가장 자연스럽습니다.")
    st.divider()

    # 4. 문서 조각 겹침 설정 및 검색 개수
    st.subheader("🔗 문맥 연결 및 참고 개수")
    chunk_overlap = st.slider("조각 겹침 크기", min_value=0, max_value=300, value=100, step=20)
    k_value = st.slider("참고할 문서 조각 수", min_value=1, max_value=6, value=3, step=1)
    st.divider()

    # 대화 기록 초기화 버튼
    if st.button("🧹 대화 내용 지우기", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# 메인 화면 영역: 대화형 인터페이스 중심의 친절한 안내 제공
st.title("💬 문서 대화형 인공지능 비서")
st.markdown("왼쪽 메뉴에서 PDF 파일을 올리신 후, 아래 대화창에서 문서에 대해 자유롭게 물어보세요.")

# 파일이 업로드된 경우의 동작 흐름
if uploaded_file:
    # 임시 폴더에 파일 저장
    temp_dir = "temp_files"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, uploaded_file.name)

    file_bytes = uploaded_file.getvalue()
    file_hash = calculate_file_hash(file_bytes)
    
    with open(temp_path, "wb") as f:
        f.write(file_bytes)

    # 백엔드 모듈을 통해 문서 분석 진행
    with st.spinner("☕ 인공지능 비서가 문서를 꼼꼼히 읽고 분석하는 중입니다. 잠시만 기다려주세요..."):
        rag_module, error_msg = load_rag_module(temp_path, file_hash, chunk_size, chunk_overlap, preferred_model)

    # 사용 후 임시 파일 정리 (삭제)
    if os.path.exists(temp_path):
        os.remove(temp_path)

    # 오류 발생 시 친절한 안내 메시지 출력
    if error_msg:
        st.error("앗, 문서 분석 중에 문제가 생겼어요.")
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            retry_match = re.search(r"retry in (\d+)", error_msg, re.IGNORECASE)
            wait_sec = retry_match.group(1) if retry_match else "30"
            
            st.warning("⏳ 무료 이용량 한도에 잠시 도달했습니다.")
            st.info(
                f"**해결 팁:**\n"
                f"1. 약 {wait_sec}초 동안 잠시 숨을 고르신 후 다시 시도해 주세요.\n"
                f"2. 왼쪽 메뉴에서 조각 크기를 1000으로 늘리시면 원활하게 작동합니다."
            )
        else:
            st.info(f"오류 내용: {error_msg}\n\n💡 글자가 아닌 이미지로만 이루어진 PDF 파일인지 확인해 주세요.")
        st.stop()

    st.success(f"🎉 '{uploaded_file.name}' 분석이 완료되었습니다! 아래에서 편하게 질문해 주세요.")
    
    # 현재 작동 중인 시스템 정보 확인 상자
    with st.expander("🔍 현재 적용된 인공지능 설정 확인하기", expanded=False):
        info_col1, info_col2, info_col3 = st.columns(3)
        with info_col1:
            st.metric(label="사용 중인 모델", value=rag_module.llm_model_name.replace("models/", ""))
        with info_col2:
            st.metric(label="변환 방식", value=rag_module.embedding_model_name.replace("models/", ""))
        with info_col3:
            st.metric(label="참고 조각 수", value=f"{k_value}개")
    
    # 대화 체인 생성 및 session_state 보존
    rag_chain = rag_module.get_rag_chain(k=k_value)
    st.session_state.rag_chain = rag_chain  # session_state에 참조 저장

    # 대화 내용 기록 관리
    if "messages" not in st.session_state or st.session_state.get("last_file_hash") != file_hash:
        st.session_state.last_file_hash = file_hash
        st.session_state.messages = [
            {"role": "assistant", "content": "안녕하세요! 업로드하신 문서를 완벽하게 숙지했습니다. 문서 내용 중 궁금한 점을 편하게 물어보세요!"}
        ]

    # 대화 화면 출력
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 사용자 입력 및 응답 생성 처리
    if user_query := st.chat_input("문서에 대해 궁금한 점을 입력해 주세요..."):
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("🤔 문서를 찾아보고 가장 정확한 답변을 정리하고 있어요..."):
                try:
                    response = st.session_state.rag_chain.invoke({
                        "question": user_query,
                        "chat_history": st.session_state.messages
                    })
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        st.error("⏳ 인공지능 이용량이 많아 잠시 멈췄습니다. 20초 정도 기다리신 후 다시 질문해 주세요.")
                    else:
                        st.error(f"답변을 만드는 도중 문제가 발생했습니다: {e}")

else:
    st.info("👈 먼저 화면 왼쪽 메뉴의 [문서 파일 첨부] 칸에 PDF 파일을 올려주세요.")