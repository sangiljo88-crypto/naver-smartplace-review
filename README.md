# 🏪 네이버 스마트플레이스 리뷰 답글 자동화

네이버 스마트플레이스에 등록된 업체의 리뷰를 관리하고, AI를 활용하여 자동으로 답글을 생성/등록할 수 있는 웹 애플리케이션입니다.

## ✨ 주요 기능

- 🔐 **네이버 쿠키 로그인**: 안전한 쿠키 기반 인증
- 📝 **리뷰 목록 조회**: 답글 유무 필터링, 검색 기능
- 🤖 **AI 답글 생성**: OpenAI GPT / Google Gemini 지원
- ⚡ **빠른 답글 등록**: 생성된 답글 바로 등록
- 📊 **통계 대시보드**: 전체 리뷰, 미답글 현황

## 🚀 설치 및 실행

### 1. 요구사항

- Python 3.8 이상
- Chrome 브라우저 (Playwright용)

### 2. 설치

```bash
# 저장소 클론 또는 다운로드
cd naver-smartplace-review

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium
```

### 3. 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

## 📖 사용 방법

### 1️⃣ 네이버 쿠키 가져오기

1. **크롬 브라우저**에서 [네이버](https://naver.com)에 로그인
2. **F12** 키를 눌러 개발자 도구 열기
3. **Application** 탭 → **Cookies** → `https://www.naver.com` 클릭
4. 아래 쿠키 값 복사:
   - `NID_AUT`
   - `NID_SES`
5. 형식: `NID_AUT=값; NID_SES=값`

### 2️⃣ AI API 키 발급

**OpenAI (GPT)**
1. [OpenAI Platform](https://platform.openai.com) 접속
2. API Keys 메뉴에서 새 키 생성

**Google Gemini**
1. [Google AI Studio](https://makersuite.google.com/app/apikey) 접속
2. Create API Key 클릭

### 3️⃣ 리뷰 관리

1. 쿠키로 로그인
2. 업체 선택
3. 새로고침으로 리뷰 불러오기
4. AI 답글 생성 또는 직접 작성
5. 답글 등록

## 🌐 배포 (Railway)

### Railway로 배포하기

1. [Railway](https://railway.app) 가입
2. "New Project" → "Deploy from GitHub"
3. 저장소 연결
4. 자동 배포 완료!

### 환경변수 설정 (선택)

Railway Dashboard에서:
- `OPENAI_API_KEY`: OpenAI API 키
- `GEMINI_API_KEY`: Gemini API 키

## ⚠️ 주의사항

1. **네이버 이용약관**: 자동화 도구 사용은 약관 위반 가능성이 있습니다
2. **봇 탐지**: 너무 빠른 작업은 차단될 수 있습니다 (권장: 5초 이상 간격)
3. **쿠키 보안**: 쿠키는 민감한 정보입니다. 타인에게 공유하지 마세요
4. **API 비용**: OpenAI/Gemini API 사용량에 따른 비용 발생

## 📁 프로젝트 구조

```
naver-smartplace-review/
├── app.py                 # 메인 Streamlit 앱
├── requirements.txt       # 의존성 패키지
├── README.md             # 프로젝트 설명
├── database/
│   ├── db.py             # 데이터베이스 연결
│   └── reviews.db        # SQLite DB (자동 생성)
└── services/
    ├── naver_auth.py     # 네이버 로그인
    ├── review_scraper.py # 리뷰 스크래핑
    ├── ai_generator.py   # AI 답글 생성
    └── reply_poster.py   # 답글 등록
```

## 🔧 기술 스택

- **Frontend/Backend**: Streamlit
- **브라우저 자동화**: Playwright
- **AI**: OpenAI GPT / Google Gemini
- **데이터베이스**: SQLite

## 📄 라이선스

MIT License

## 💬 문의

이슈나 기능 요청은 GitHub Issues를 이용해주세요.
