<div align="center">

# Nipah Tracker

**니파 바이러스 실시간 현황 대시보드**
[![github](https://img.shields.io/badge/Live%20Demo-lshee9008-white?style=for-the-badge&logo=github)](https://nipah-tracker.onrender.com)
  
[![Live Demo](https://img.shields.io/badge/Live%20Demo-nipah--tracker.onrender.com-red?style=for-the-badge&logo=render)](https://nipah-tracker.onrender.com)
  
[![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)](https://python.org)
  
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
  
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

WHO·IEDCR 공식 데이터 기반 · 자동 갱신 · 실시간 뉴스 수집

[**라이브 데모 →**](https://nipah-tracker.onrender.com)

</div>

---

## 스크린샷
### 메인 대시보드
![](https://velog.velcdn.com/images/fpalzntm/post/2c6bdafd-e8a7-4643-bfb0-9c379a2cc805/image.png)

### 발생 이력 차트
![](https://velog.velcdn.com/images/fpalzntm/post/e0d61f20-6057-4174-805e-370d80bc32fa/image.png)

---

## 주요 기능

- **실시간 세계 지도** — Leaflet.js 기반 인터랙티브 발생 현황 지도
- **정확한 역학 데이터** — WHO DON·IEDCR·ScienceDirect 3중 교차검증
- **실시간 뉴스 수집** — Google News RSS (한국어·영어) 자동 크롤링
- **연도별 발생 이력** — 1998년 말레이시아 최초 발생부터 2026년까지
- **국가별 CFR 분석** — 치명률 자동 계산 및 시각화
- **자동 갱신** — APScheduler 기반 6시간마다 데이터 자동 업데이트
- **경보 시스템** — 활성 발생국 감지 시 자동 경고 배너

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy, APScheduler |
| **Database** | SQLite (로컬) / PostgreSQL (프로덕션) |
| **Frontend** | Jinja2, Chart.js, Leaflet.js, Vanilla JS |
| **Data** | BeautifulSoup4, Pandas, Feedparser, Geopy |
| **Deploy** | Render (Free Tier), GitHub Actions |

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────┐
│                  Data Pipeline                   │
│                                                  │
│  Wikipedia ──┐                                   │
│  WHO DON ────┼──► Scraper ──► SQLite/PostgreSQL  │
│  Google RSS ─┘         ▲                         │
│                    APScheduler                   │
│                   (6시간 간격)                    │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│                  FastAPI Server                  │
│                                                  │
│  GET /          ──► Jinja2 Template              │
│  GET /api/stats ──► JSON Response                │
│  GET /api/refresh ► Manual Trigger               │
│  GET /health    ──► Health Check                 │
└─────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│                                                  │
│  Leaflet.js  ──► 세계 발생 지도                  │
│  Chart.js    ──► 연도별·CFR 차트                 │
│  Vanilla JS  ──► 30분 자동 폴링                  │
└─────────────────────────────────────────────────┘
```

---

## 데이터 정확도

WHO·IEDCR 공식 수치와 교차검증 완료 (2026년 3월 기준):

| 국가 | 확진자 | 사망자 | CFR | 출처 |
|---|---|---|---|---|
| Bangladesh | 350 | 259 | 74.0% | IEDCR 2025 |
| Malaysia | 283 | 109 | 38.5% | WHO/PubMed |
| India | 106 | 74 | 69.8% | WHO DON |
| Philippines | 17 | 9 | 52.9% | WHO |
| Singapore | 11 | 1 | 9.1% | WHO |

> 참조: WHO Disease Outbreak News, IEDCR Bangladesh, ScienceDirect 2024 Review (754건/435명, CFR 58%)

---

## 로컬 실행

```bash
# 1. 저장소 클론
git clone https://github.com/lshee9008/nipah-dashboard.git
cd nipah-dashboard/back

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 서버 실행
uvicorn main:app --reload

# → http://localhost:8000
```

---

## 프로젝트 구조

```
back/
├── main.py          # FastAPI 라우터 + 스케줄러
├── database.py      # SQLAlchemy 모델 + 마이그레이션
├── scraper.py       # 데이터 수집 파이프라인
├── requirements.txt
├── render.yaml      # Render 배포 설정
├── templates/
│   └── index.html   # Jinja2 메인 템플릿
└── static/
    └── style.css    # 다크 테마 스타일
```

---

## 배포

Render Blueprint 기반 원클릭 배포:

```bash
git push origin main  # → Render 자동 재배포
```

### 환경변수

| 변수          | 설명                              |
|---------------|-----------------------------------|
| DATABASE_URL  | PostgreSQL URL (없으면 SQLite)    |

---

## License

MIT License — 자유롭게 사용·수정 가능, 상업적 이용 시 출처 표기 권장

---

<div align="center">

**데이터 출처**: WHO · IEDCR · ScienceDirect · Google News  
본 대시보드는 참고용이며 의학적 조언이 아닙니다

</div>
