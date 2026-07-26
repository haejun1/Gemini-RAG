# 🤖 Gemini 기반 문서 대화형 AI 에이전트 (RAG 시스템)

> 업로드한 PDF 문서를 기반으로 질문에 답변하는 **RAG(Retrieval-Augmented Generation) 기반 대화형 AI 에이전트**입니다.  
> Google Gemini API의 **Free Tier** 환경에서도 안정적으로 동작하도록 **하이브리드 모델 탐색** 과 **지수 백오프(Exponential Backoff)** 를 적용했습니다.

---

# 📌 1. 프로젝트 소개

사용자가 PDF 문서를 업로드하면 문서를 벡터화하여 저장하고, 질문이 들어왔을 때 관련 문서를 검색한 뒤 Gemini가 이를 바탕으로 답변하는 **RAG 시스템**입니다.

### 주요 기능

- 📄 PDF 문서 업로드 및 자동 분석
- 🔍 FAISS 기반 유사 문서 검색
- 🤖 Gemini 기반 자연어 질의응답
- ⚡ 무료 API 환경에서도 안정적인 요청 처리
- 💬 메신저 형태의 대화형 UI

---

# 🚀 2. 실행 방법

## 1️⃣ 사전 준비

- Python **3.10 이상** 설치

---

## 2️⃣ 패키지 설치

프로젝트 폴더에서 아래 명령어를 실행합니다.

```bash
pip install -r requirements.txt
```

---

## 3️⃣ Google API Key 설정

프로젝트 루트에 `.env` 파일을 생성합니다.

```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

---

## 4️⃣ 실행

```bash
streamlit run app.py
```

실행 후 브라우저가 자동으로 열리며 서비스를 사용할 수 있습니다.

---

# 🛠️ 3. 기술 스택

| 기술 | 사용 라이브러리 | 선택 이유 |
|------|----------------|----------|
| **LLM** | Gemini Flash Lite | 무료 API 환경에서 빠른 응답과 최신 Alias 기반 모델 지원 |
| **문서 로더** | PyMuPDFLoader | 한글 PDF 추출 정확도가 높고 처리 속도가 빠름 |
| **텍스트 분할** | RecursiveCharacterTextSplitter | 문단 단위 분할로 문맥 손실 최소화 |
| **벡터 DB** | FAISS | 별도 서버 없이 빠른 벡터 검색 가능 |
| **Prompt Engineering** | Role Prompt + CoT | 환각(Hallucination)을 줄이고 구조화된 답변 생성 |

---

# 💡 4. 개발 과정 및 고민

## ① API 모델명이 계속 변경되는 문제

### ❗ 문제

초기에는 모델명을 코드에 고정하여 사용했습니다.

하지만 Google API 업데이트나 계정 권한에 따라

- `404 NOT_FOUND`
- 모델 삭제
- 모델명 변경

문제가 자주 발생했습니다.

### ✅ 해결

실행 시 사용 가능한 모델을 자동으로 조회하도록 변경했습니다.

동작 순서는 다음과 같습니다.

```
사용 가능한 모델 조회
          ↓
gemini-flash-lite-latest 우선 선택
          ↓
사용 불가 시 다른 Flash 모델 탐색
          ↓
특수 목적 모델 제외
          ↓
최종 사용 가능한 모델 선택
```

이를 통해 모델명이 변경되더라도 프로그램이 중단되지 않도록 개선했습니다.

---

## ② 무료 API Rate Limit 문제

### ❗ 문제

무료 Tier에서는 PDF 임베딩을 한 번에 수행하면

```
429 Rate Limit Exceeded
```

오류가 자주 발생했습니다.

### ✅ 해결

다음과 같은 전략을 적용했습니다.

- Batch 단위(5개) 임베딩
- Exponential Backoff
- Retry
- Sleep

처리 흐름

```
Chunk 생성
      ↓
5개씩 Batch 처리
      ↓
429 발생
      ↓
2초 대기
      ↓
재시도
      ↓
실패 시
4초 → 8초 → 16초 ...
```

이를 통해 대용량 PDF도 안정적으로 처리할 수 있도록 개선했습니다.

---

# ⚠️ 5. 한계점 및 향후 발전 방향

## 1. 무료 API 호출 제한

### 현재 한계

- Free Tier의 RPM 제한
- 대용량 문서 처리 시 응답 지연

### 개선 계획

- Gemini 유료 플랜 적용
- Redis 캐싱 도입
- 벡터 캐시 활용
- 비동기 처리 적용

---

# 🎯 프로젝트 특징

- ✅ RAG 기반 문서 질의응답
- ✅ Gemini API Free Tier 최적화
- ✅ 하이브리드 모델 탐색
- ✅ Exponential Backoff 적용
- ✅ FAISS 기반 벡터 검색
- ✅ PyMuPDF 기반 한글 PDF 지원
- ✅ Streamlit 기반 대화형 UI
- ✅ 구조화된 Prompt Engineering 적용