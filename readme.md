# 💬 Gemini 기반 AI 문서 분석 비서 (RAG Agent)

> **"2단계 멀티모달 및 하이브리드 검색 기반의 문서 분석·출력 AI 에이전트"**

> 본 프로젝트는 복수의 PDF 문서 및 정밀 표/이미지 캡셔닝 기반으로 질문에 정확히 답변하고, 맞춤형 보고서(.docx) 및 Presentation(.pptx) 파일까지 즉시 생성해 주는 대화형 RAG(Retrieval-Augmented Generation) 에이전트입니다.

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

# 📌 1. 주요 기능

* 📄 **다량 문서 동시 통합 인덱싱**: `st.file_uploader`를 통해 복수의 PDF 파일을 업로드받아 단일 FAISS DB로 병합, 다중 문서 교차 질의응답 구현
* 🖼️ **이미지 캡셔닝 & 멀티모달 RAG**: PDF 내 주요 표/이미지 영역을 추출하여 경량 시각 특화 모델(`gemini-3.1-flash-lite`)로 정밀 수치·단위·축 정보를 텍스트화한 뒤 원본 문맥에 통합 및 벡터화
* 🔍 **EnsembleRetriever 하이브리드 검색**: 고유명사·정밀 수치 탐색을 위한 키워드 검색(BM25, 0.4)과 문맥 탐색을 위한 의미 검색(FAISS, 0.6)을 결합하여 Retrieval Quality 극대화
* 🤖 **Multi-LLM (Multi-Agent) 파이프라인**: 1차 시각 특화 전처리 모델과 2차 정밀 추론 모델을 역할 분담시켜 속도, 비용, 추론 정밀도 동시 확보
* 🎯 **직관적 UX (사전 설정 모드)**: 3가지 목적별 사전 설정(표준 기술 분석, 빠른 핵심 검색, 심층 보고서)으로 유저 친화적 챗봇 상세 설정 가능
* 🎨 **출력 형태 커스텀 & 파일 내보내기**: 답변 수준(전문가/비전공자) 및 형태(대화형/마크다운/PPT) 선택 기능 및 `python-pptx`, `python-docx` 기반 원본 다운로드 기능 제공
* 📄 **자동 출처 추적 (RunnableParallel)**: 답변 생성 시 근거가 된 원본 파일명과 페이지 번호를 하단에 투명하게 명시해 환각 현상 방지
* 🧹 **서버 리소스 및 세션 자동 정제**: 파일 구성 변경 시 통합 해시(`final_combined_hash`) 기반 대화 자동 초기화, `os.remove` 기반 임시 파일 정제, `@st.cache_resource(ttl="1h")` 및 `gc.collect()`를 통한 OOM 방지

---

### 🛠️ 2. 기술 스택 & 핵심 기능 아키텍처

| 구분 | 핵심 기술 / 라이브러리 | 적용된 기술 요소 및 역할 |
| :--- | :--- | :--- |
| **Multi-LLM Agent Architecture** | `gemini-3.6-flash`<br>`gemini-3.1-flash-lite`<br>`gemini-3.1-pro-preview`<br>`gemini-flash-latest` | **2단계 역할 분담 (Agentic Pipeline)**<br>• **1차 시각 전처리 에이전트:** `gemini-3.1-flash-lite` 기반 정밀 이미지/표 캡셔닝<br>• **2차 추론 에이전트:** `gemini-3.6-flash` 기반 사용자 질문 정밀 응답<br>• **Model Fallback:** 스캐닝 실패 시 `gemini-flash-latest` 별칭 자동 바인딩 |
| **Embedding & Vector Mapping** | `models/gemini-embedding-2` | **고차원 텍스트 벡터화**<br>• 복잡한 PDF 문맥 및 표/차트 캡션 데이터를 고차원 벡터 공간에 맵핑하여 Retrieval 정확도 대폭 상승 |
| **Hybrid Search Engine** | `FAISS` (Dense Vector)<br>`BM25` (Sparse Keyword)<br>`EnsembleRetriever` | **2중 하이브리드 검색 (FAISS 0.6 : BM25 0.4)**<br>• 모델명, 규격, 수치 등 고유명사는 BM25로 핀포인트 타겟팅<br>• 심층 기술 문맥 및 시각 캡션 데이터는 FAISS 벡터 DB로 유사도 검색 |
| **Vision & PDF Processing** | `PyMuPDF` (Fitz)<br>`Pillow` (PIL) | **멀티모달 바이너리 파싱**<br>• PDF 내 표/차트/이미지 바이너리를 영역별로 직접 추출(Extraction)<br>• 아이콘성 노이즈 이미지 스킵 및 시각 데이터 텍스트화 전처리 |
| **RAG Orchestration & Tracing** | `LangChain` (LCEL)<br>`RunnableParallel`<br>`RunnablePassthrough` | **병렬 스트림 & 출처 동적 추적**<br>• 답변 생성(Answer Stream)과 출처 추출(Source Doc Stream)을 병렬 처리<br>• 답변 하단에 `📄 출처: [파일명] (Page X)` 레퍼런스 자동 표기 및 환각 방지 |
| **Dynamic Document Exporter** | `python-pptx`<br>`python-docx` | **AI 에이전트 파일 자동 생성 (NotebookLM 스타일)**<br>• 마크다운 응답을 파싱하여 디자인 테마가 적용된 와이드 16:9 `.pptx` 및 양식 보고서 `.docx` 내보내기 |
| **State & Resource Manager** | `Hashlib` (MD5)<br>`gc` (Garbage Collector)<br>`Streamlit Cache` | **메모리 누수 & 캐시 제어**<br>• 다중 파일 바이너리 결합 해시(`final_combined_hash`) 기반 세션 자동 초기화<br>• `@st.cache_resource(ttl="1h")` 및 `os.remove()`, `gc.collect()` 기반 OOM 방지 |

---

# 🔄 3. RAG 시스템 작동 파이프라인 (Pipeline Architecture)

전체 파이프라인은 다중 문서 업로드부터 시각 데이터 캡셔닝, 하이브리드 검색, 병렬 추론, 맞춤형 파일 내보내기까지 6단계의 정교한 과정으로 진행됩니다.

```
┌──────────────────────────────────────┐
  1. 다중 PDF 업로드                    
     & 통합 해시 검증                   
     (Concatenated MD5 Hash)           
└──────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────┐
  2. 시각 에이전트                      
     표/이미지 캡셔닝                   
     (gemini-3.1-flash-lite)           
└──────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────┐
  3. 의미 단위 문맥 자르기              
     (Chunking)                        
     (Recursive Splitter)              
└──────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────┐
  4. 하이브리드 검색                   
     (FAISS + BM25)                    
     EnsembleRetriever                 
└──────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────┐
  5. 병렬 추론 및                       
     근거 출처 자동 추적                
     (RunnableParallel Chain)          
└──────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────┐
  6. 최종 답변 출력                     
     & 원본 파일 내보내기               
     (.pptx / .docx 다운로드)           
└──────────────────────────────────────┘

```

---

# ⚙️ 4. 단계별 상세 동작 로직

### **1️⃣ 다량 문서 업로드 & final_combined_hash 세션 감지**

* `st.file_uploader(accept_multiple_files=True)`를 통해 복수의 PDF 파일을 한 번에 업로드 받습니다.
* 각 파일 바이트 데이터의 MD5 해시를 하나로 이어서(Concatenate) 최종 `final_combined_hash`를 생성합니다.
* 통합 해시가 변경되면 파일 구성 수정을 즉시 감지하여 이전 대화 내역(`st.session_state.messages`)을 자동 초기화함으로써 불필요한 토큰 비용 폭증을 방지합니다.

### **2️⃣ 1차 시각 에이전트 전처리 (이미지/표 캡셔닝)**

* `PyMuPDF(fitz)` 파서가 PDF 내 주요 표, 차트, 이미지 영역의 바이너리를 직접 extraction합니다.
* 1차 전처리로 경량 시각 특화 모델 `gemini-3.1-flash-lite`에 역할 지정(Role Prompting) 프롬프트를 전달하여 표의 행/열 데이터, 정밀 수치, 단위, 차트 축 의미를 정밀 텍스트(캡션)로 변환한 후 원본 문맥 위치에 통합시킵니다.

### **3️⃣ 의미 단위 청킹 & 초고속 단일 FAISS DB 구축**

* `RecursiveCharacterTextSplitter`에 `separators` 구문을 추가하여 단어나 문장의 부자연스러운 단절을 방지하고 의미 단위(문단 $\rightarrow$ 문장 $\rightarrow$ 단어)로 정밀 분할합니다.
* 최신 `models/gemini-embedding-2` 모델을 사용하여 단 한 번에 통합 FAISS DB를 초고속 인덱싱합니다.
* 인덱싱 완료 직후 `os.remove()`로 디스크 임시 PDF를 즉시 삭제하고 `gc.collect()`를 구동하여 memory leak 및 OOM(Out of Memory) 현상을 전면 차단합니다.

### **4️⃣ EnsembleRetriever 하이브리드 검색 (FAISS + BM25)**

* 단일 벡터 검색 방식에서 벗어나, 키워드 기반 **BM25 검색기**와 의미 기반 **FAISS 검색기**를 결합한 **EnsembleRetriever** 하이브리드 검색 엔진을 구축합니다.
* 기술 사양, 특허, 규격 번호 등 정밀 수치 및 고유명사는 BM25로 타겟팅하고, 복잡한 문장의 문맥은 FAISS로 보완하여 검색 정밀도(Retrieval Accuracy)를 극대화합니다.

### **5️⃣ RunnableParallel 기반 병렬 추론 & 출처 자동 추적**

* LangChain LCEL의 `RunnableParallel` 구조를 도입하여 RAG 파이프라인 흐름을 분기합니다.
* 선택된 2차 추론 LLM(`gemini-3.6-flash` 등)이 메인 답변을 생성하는 동시에, 출처 추출 스트림이 병렬 실행되어 답변 하단에 `📄 출처: [파일명] (Page X)` 형태로 근거 문서 레퍼런스를 자동으로 명시하여 환각(Hallucination) 현상을 완전히 차단합니다.

### **6️⃣ 사용자 맞춤형 출력 & 원본 파일 내보내기 (Exporter)**

* 사이드바 옵션을 통해 지정된 답변 수준(전문가/비전공자) 및 출력 형태(대화형/마크다운 보고서/PPT 슬라이드)가 동적으로 프롬프트에 전달되어 응답을 구조화합니다.
* PPTX 또는 DOCX 형태 선택 시 `document_exporter.py` 모듈이 작동하여 마크다운 텍스트를 실제 파싱한 후, 디자인 테마가 적용된 발표용 슬라이드(`.pptx`) 및 정식 보고서(`.docx`) 원본 파일 다운로드 버튼(`st.download_button`)을 실시간 제공합니다.