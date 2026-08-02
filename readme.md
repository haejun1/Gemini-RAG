# 💬 Gemini 기반 AI 문서 분석 비서 (RAG Agent)

> **"무료 API 환경에서도 거침없이 동작하는 최고 성능의 문서 질의응답 비서"**  
> 본 프로젝트는 PDF 문서를 기반으로 질문에 정확히 답변하는 **RAG(Retrieval-Augmented Generation)** 대화형 AI 에이전트입니다.  
> **Google Gemini Free Tier**의 한계를 극복하기 위한 **하이브리드 모델 탐색**, **지수 백오프(Exponential Backoff)**, **MD5 캐싱** 메커니즘을 내장하여 높은 안정성과 신뢰성을 제공합니다.

---

# 🚀 실행 및 설정 가이드

### 1️⃣ 사전 준비
- Python **3.10 이상** 설치 필수

### 2️⃣ 패키지 설치
```bash
pip install -r requirements.txt
```

### 3️⃣ 환경 변수 설정
프로젝트 루트 경로에 `.env` 파일을 생성하고 Google Gemini API Key를 입력합니다.
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 4️⃣ 애플리케이션 실행
```bash
python -m streamlit run app.py
```

---

# 🌟 1. 프로젝트 핵심 설계 철학

본 프로젝트는 단순한 기능 구현을 넘어 **실제 서비스 수준의 완성도**를 목표로 다음 3가지 핵심 가치를 바탕으로 설계되었습니다.

| 설계 축 | 핵심 내용 | 반영된 기술 및 구조 |
| :--- | :--- | :--- |
| **👤 사용자 친화성 (User-Centric UI/UX)** | 직관적인 인터페이스와 친절한 피드백 제공 | • 메신저 형태의 대화형 UI (Streamlit)<br>• API 한도 도달 시 복구 안내 및 대기 시간 실시간 피드백<br>• 사이드바를 통한 문서 조각 크기, 참고 개수 등 유연한 파라미터 조절 |
| **🏗️ 구조적 & 재사용성 (Clean Architecture)** | 프론트엔드와 백엔드 엔진의 완벽한 분리 | • UI 레이어(`app.py`)와 RAG 백엔드 엔진(`rag_module.py`)의 모듈화<br>• 캡슐화된 `RAGModule` 및 `HybridGeminiManager` 클래스 설계로 다른 프레임워크 확장 용이 |
| **⚡ 무료 버전 맞춤형 (Free-Tier Optimized)** | Gemini Free Tier 제약(RPM/TPM) 극복 | • 배치 임베딩 + 지수 백오프 기반의 자동 재시도 로직<br>• 동적 모델 스캐닝을 통한 API 404/Deprecation 에러 방지<br>• MD5 해시 기반 세션 캐싱으로 불필요한 API 호출 최적화 |

---

# 📌 2. 주요 기능

- 📄 **PDF 문서 자동 분석**: PyMuPDF 기반의 고성능 한글/영문 PDF 텍스트 추출 및 분할
- 🔍 **FAISS 기반 고속 벡터 검색**: 질문과 가장 연관성이 높은 문서 조각(Top-K) 즉시 검색
- 🤖 **Gemini 기반 지능형 질의응답**: 문서 근거 기반 답변 생성으로 환각(Hallucination) 현상 방지
- 🔄 **스마트 모델 탐색**: 이용 가능한 Gemini 모델(Flash/Lite 등)을 자동으로 감지하여 최적 할당
- 🛡️ **안정적인 예외 처리**: Rate Limit(429) 감지 시 자동 재시도 및 사용자 가이드 제공

---

# 🛠️ 3. 기술 스택

```
[ Frontend ]    Streamlit
[ LLM & Embed ]  Google Gemini (Gemini Flash / Gemini Embedding)
[ Framework ]   LangChain (Core, Community, Google-GenAI, Text-Splitters)
[ Vector DB ]   FAISS (Facebook AI Similarity Search)
[ PDF Engine ]  PyMuPDF (Fitz)
[ Utility ]     Python-dotenv, Hashlib
```

| 구분 | 기술 / 라이브러리 | 선택 이유 및 핵심 역할 |
| :--- | :--- | :--- |
| **UI Framework** | `Streamlit` | 빠른 대화형 웹 인터페이스 구축 및 세션 상태 관리 |
| **LLM & Embedding** | `Gemini API` | 무료 Tier 지원, 빠른 속도 및 높은 한국어 이해 능력 |
| **Orchestration** | `LangChain` | RAG 체인 구성, 프롬프트 템플릿 관리, 벡터 DB연동 |
| **Vector DB** | `FAISS` | 별도 DB 서버 없이 메모리 내 고속 유사도 검색 수행 |
| **Document Loader** | `PyMuPDFLoader` | 한글 PDF 레이아웃 및 텍스트 추출 속도/정확도 우수 |

---

# 🔄 4. RAG 시스템 작동 파이프라인 (Pipeline Architecture)

전체 파이프라인은 문서 수집부터 벡터화, 검색, 답변 생성까지 5단계의 정교한 과정으로 진행됩니다.

```
┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│  1. Document   │ ──► │  2. Text Chunk │ ──► │  3. Vector DB  │
│     Upload     │     │   Splitting    │     │   & Embedding  │
└────────────────┘     └────────────────┘     └────────────────┘
                                                       │
┌────────────────┐     ┌────────────────┐              │
│ 5. Structured  │ ◄── │  4. Top-K RAG  │ ◄────────────┘
│  LLM Response  │     │   Chain Exec   │
└────────────────┘     └────────────────┘
```

### ⚙️ 단계별 상세 동작 로직

1. **📄 문서 업로드 & MD5 해시 식별**
   * 사용자가 PDF 파일을 업로드하면 파일 바이트 데이터로 **MD5 해시**를 즉시 생성합니다.
   * `temp_files/` 폴더에 임시 저장 후 분석을 준비합니다.

2. **✂️ 문맥 보존 텍스트 분할 (Chunking)**
   * `PyMuPDFLoader`로 PDF 내부 글자를 추출합니다.
   * `RecursiveCharacterTextSplitter`를 사용하여 문단 단절을 방지하며 조각화합니다. (기본값: Chunk Size 700자 / Overlap 100자)

3. **🧠 지수 백오프 기반 배치 임베딩 & FAISS 구축**
   * Free Tier 제한(429)을 피하기 위해 문서 조각을 **5개 단위(Batch)**로 나누어 처리합니다.
   * API 한도 초과 시 **지수 백오프 (4초 ➔ 8초 ➔ 16초...)** 알고리즘으로 자동 재시도하며 FAISS VectorDB에 누적 저장합니다.
   * 임베딩 완결 후 원본 임시 파일은 즉시 삭제(`os.remove`)하여 서버 자원을 정제합니다.

4. **🤖 동적 모델 할당 및 RAG 체인 구성**
   * `HybridGeminiManager`가 현재 API 계정에서 호출 가능한 최선의 LLM/임베딩 모델을 자동으로 탐색 및 바인딩합니다.
   * 사용자가 설정한 $K$개(기본 3개)의 관련 문서 조각을 검색하는 `Retriever`를 생성합니다.

5. **💬 맥락 유지 기반 답변 생성 (Multi-turn Execution)**
   * 사용자 질문 수신 시 FAISS에서 질문과 가장 연관성이 높은 문서 조각을 추출합니다.
   * 세션 상태의 이전 대화 내역(`chat_history`)과 검색된 컨텍스트(`context`), 현재 질문(`question`)을 `ChatPromptTemplate`에 통합 주입합니다.
   * Gemini LLM을 통해 이전 맥락을 이어받은 가독성 높은 마크다운 응답을 출력합니다.

---

# 💡 5. 개발 과정 및 문제 해결 (Engineering Decisions)

개발 과정에서 직면한 난관과 이를 해결하기 위한 기술적 의사결정을 우선순위(중요도/난이도) 순으로 정리했습니다.

### 1️⃣ [크리티컬] 무료 API Rate Limit (429 Error) 극복
* **문제**: Free Tier 환경에서 대용량 PDF 임베딩 시 `429 Rate Limit Exceeded` 오류로 서비스가 중단됨.
* **해결**: 
  - 5개 단위의 **배치(Batch) 임베딩** 구조 도입.
  - 429 감지 시 `4 * (2 ** attempt)` 초 단위로 대기 시간이 늘어나는 **지수 백오프(Exponential Backoff)** 재시도 알고리즘 구현.
  - 배치 간 2.0초의 하드 슬립을 부여하여 API 부하 최소화.

### 2️⃣ [안전성] API 모델명 변경 및 404 Deprecation 대응
* **문제**: Google API 업데이트나 계정 권한 변화로 하드코딩된 모델명 호출 시 `404 NOT_FOUND` 발생.
* **해결**: 
  - `genai.list_models()`를 통해 계정이 접근 가능한 모델 목록을 동적으로 스캐닝하는 `HybridGeminiManager` 구현.
  - `gemini-flash-lite-latest` ➔ `gemini-2.0-flash-lite` ➔ `gemini-2.0-flash` 순의 **Fallback 계층** 구성.
  - TTS, Vision, Audio 등 특수 목적 키워드가 들어간 불적합 모델 자동 제외.

### 3️⃣ [정확성] 동일 파일명 재업로드 시 오답 캐싱 버그 해결
* **문제**: Streamlit의 `@st.cache_resource`가 파일 경로 기준이어서, 내용이 다른 문서를 같은 파일명으로 업로드하면 이전 문서의 벡터 DB가 재사용되는 오류 발생.
* **해결**: 
  - 업로드된 바이트 단위 데이터를 기반으로 **MD5 해시값**을 계산.
  - 캐시 함수의 인자로 `file_hash`를 추가하여 내용이 변경되면 즉시 캐시가 자발적으로 갱신되도록 제어.

### 4️⃣ [사용성] 이전 대화 맥락 손실 문제 해결 (Multi-turn RAG)
* **문제**: 단발성 질문만 전달할 경우 "아까 말한 첫 번째 항목에 대해 설명해줘"와 같은 연속 대화에서 오답을 출력함.
* **해결**: 
  - `st.session_state.messages` 내역을 텍스트로 포맷팅하여 프롬프트의 `{chat_history}` 영역에 동적 주입.
  - LCEL 체인에서 `itemgetter`를 활용해 질문 검색과 대화 내역 유지를 동시에 처리하는 Multi-turn 체인 구축.

### 5️⃣ [무결성] 재시도 실패 시 은밀한 문서 누락 방지
* **문제**: 임베딩 재시도를 모두 소비한 후 실패해도 루프를 그냥 빠져나가 일부 문서가 누락된 채 "분석 완료"로 잘못 표시되는 위험 존재.
* **해결**: 
  - 배치 성공 여부(`batch_success`) 플래그 추적.
  - 최대 재시도 실패 시 `RuntimeError`를 발생시키고 UI 상에 명확한 가이드 메시지("조각 크기를 늘려주세요") 출력.

### 6️⃣ [상태관리] Streamlit Re-run 주기 내 대화 체인(`rag_chain`) 보존
* **문제**: Streamlit의 Re-run 특성으로 인해 질문 입력 시 지역 변수로 선언된 `rag_chain`의 참조 스코프가 모호해지는 현상.
* **해결**: 
  - 생성된 RAG 체인을 `st.session_state.rag_chain`에 안전하게 바인딩.
  - 질문 처리 시에도 `st.session_state.rag_chain.invoke(user_query)`로 일관되게 호출하여 세션 생명주기 보장.

### 7️⃣ [자원관리] 임시 파일 및 메모리 누수 방지
* **문제**: 업로드된 파일이 서버 디렉토리에 누적되거나 메모리가 지연 점유되는 현상.
* **해결**: 
  - FAISS DB 생성을 마친 직후 `temp_files/` 내 원본 PDF를 `os.remove`로 즉시 정제.
  - 캐시 유지 시간을 1시간(`ttl="1h"`)으로 제한.

---

# ⚠️ 6. 한계점 및 향후 발전 방향

1. **복잡한 표/이미지 데이터 처리의 한계**
   - 텍스트 기반 분할 방식을 사용하므로 복잡한 표나 도표/이미지 위주의 PDF 파싱 시 일부 정보가 손실될 수 있음.
   - *향후 과제*: Multimodal LLM 또는 LlamaIndex/Unstructured 라이브러리를 연동한 멀티모달 파싱 고도화.