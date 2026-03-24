# Nipah Tracker — 포트폴리오

## 프로젝트 개요

| 항목 | 내용 |
|---|---|
| **프로젝트명** | Nipah Tracker |
| **기간** | 2026년 3월 |
| **유형** | 개인 프로젝트 (풀스택) |
| **라이브** | https://nipah-tracker.onrender.com |
| **GitHub** | https://github.com/lshee9008/nipah-dashboard |

---

## 기획 배경

2026년 1월 인도 West Bengal과 방글라데시에서 니파 바이러스가 동시 발생하며 아시아 전역이 긴장했다. 그러나 국내에는 코로나 수준의 실시간 현황판이 없었고, 흩어진 WHO 보고서를 찾아봐야 하는 불편함이 있었다.

**"코로나 현황판처럼 니파 바이러스도 한눈에 볼 수 있으면 어떨까?"** 라는 질문에서 시작했다.

---

## 핵심 문제와 해결

### 문제 1: 데이터 부정확성
기존 위키피디아 데이터는 오류가 많았다.
- India 확진자: 27명(위키) → **106명**(WHO DON 전체 집계)
- Malaysia: 265명 → **283명**(보건부 1998~1999 전체 집계)
- Bangladesh 연도별 데이터 다수 누락

**해결**: WHO Disease Outbreak News, IEDCR 공식 대시보드, ScienceDirect 2024 리뷰 논문을 **3중 교차검증**하여 1998년부터 2026년까지 35건의 정확한 연도별 데이터를 구축했다.

### 문제 2: 데이터 최신성
스크래핑만으로는 뉴스가 업데이트되지 않는다.

**해결**: APScheduler로 **6시간마다 자동 수집** 파이프라인 구축. 서버 시작 시 초기 수집, 이후 백그라운드에서 지속 갱신.

### 문제 3: SQLAlchemy 객체 직렬화 오류
Render 배포 후 `TypeError: unhashable type: 'dict'` 오류 발생.

**해결**: Jinja2 `TemplateResponse` 대신 `Environment` 직접 초기화로 우회. 모든 SQLAlchemy ORM 객체를 `row_to_dict()` 함수로 순수 dict 변환.

---

## 기술적 구현 포인트

### 데이터 파이프라인 설계
```python
# Wikipedia 스크래핑은 보조 수단, 내부 데이터가 주(主)
def scrape_wikipedia_stats(db):
    totals = _build_country_totals()  # WHO 기반 하드코딩
    wiki_data = _scrape_wiki()        # 보조 수집
    # 타임라인 합산이 항상 우선
    save_cases_to_db(db, totals)
```

### DB 자동 마이그레이션
신규 컬럼 추가 시 기존 DB가 있어도 자동으로 `ALTER TABLE`:
```python
def _migrate_sqlite(conn):
    for table, cols in _MIGRATIONS.items():
        existing = get_existing_cols(table)
        for col in cols:
            if col not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col}")
```

### SQLite ↔ PostgreSQL 자동 전환
```python
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    # Render PostgreSQL
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    # 로컬 SQLite
    engine = create_engine("sqlite:///./nipah.db")
```

---

## 성과

- WHO 공식 수치 대비 **오차 1% 이내** 데이터 정확도 달성
- 1998~2026년 **35개 연도별 이벤트** 수집·검증
- Render 무료 플랜에서 **안정적 운영** 중
- 뉴스 수집: 한국어·영어 **16건 이상** 자동 수집

---

## 배운 점

- 공개 데이터(위키피디아)의 신뢰성 한계와 **1차 출처(WHO DON) 중요성**
- FastAPI + Jinja2 조합에서 **ORM 객체 직렬화** 주의사항
- 클라우드 배포 환경에서의 **DB 휘발성** 대응 (SQLite → PostgreSQL 전환 설계)
- 실시간 데이터 서비스에서 **스케줄러**의 필요성

---

## 스택 선택 이유

| 기술 | 선택 이유 |
|---|---|
| **FastAPI** | 비동기 지원, 자동 API 문서화, 빠른 개발 속도 |
| **SQLAlchemy** | ORM으로 SQLite↔PostgreSQL 환경 전환 용이 |
| **Leaflet.js** | 오픈소스, 경량, 커스터마이징 자유도 높음 |
| **Chart.js** | 반응형 차트, 다크 테마 적용 쉬움 |
| **Render** | 무료 티어, render.yaml 기반 원클릭 배포 |

