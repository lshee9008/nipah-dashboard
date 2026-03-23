import pandas as pd
import feedparser
from sqlalchemy.orm import Session
from database import NipahData, NipahNews, OutbreakTimeline, SessionLocal
from datetime import datetime
import re
import time
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="nipah_tracker_v2_advanced")

# ═══════════════════════════════════════════════════════════════════════════
# 데이터 출처 (교차검증 완료):
#  - WHO DON 공식 보고서 (각 연도별)
#  - IEDCR Bangladesh 공식 대시보드 (2001-2025: 347건/249명)
#  - ScienceDirect 2024 리뷰 (1998-May2024 전체: 754건/435명, CFR 58%)
#  - PubMed: Malaysia 1998-1999 공식 집계 = 283건/109명 (단일 유행)
#  - PMC 논문: Bangladesh 연도별 수치 확인
#
# 검증 결과 요약:
#  Malaysia  : 283/109  (1998~1999, 단일 유행) ✅
#  Singapore :  11/1    (1999) ✅
#  Bangladesh: 347/249  (IEDCR 공식, 2025년까지) — 현재 코드 350/259 (±3건)
#  India     : 106/74   (2001~2026, 공식에서 확인 가능한 모든 연도)
#  Philippines: 17/9    ✅
# ═══════════════════════════════════════════════════════════════════════════

HISTORICAL_TIMELINE = [
    # ── Malaysia (1998~1999 단일 유행, 공식 집계 283/109) ─────────────────────
    # PubMed/ScienceDirect: "Ministry of Health, 29 Sep 1998 to Dec 1999: 283 cases, 109 deaths"
    # Wikipedia '265/105'는 3개 주(州)만의 집계 → 공식 전체는 283/109
    {"year": 1998, "country": "Malaysia",    "confirmed": 283, "deaths": 109,
     "source_note": "1998~1999 전체 유행. Perak·Negeri Sembilan·Selangor 외 포함. "
                    "보건부 공식(29 Sep 1998 - Dec 1999): 283건/109명. CFR 38.5%."},

    # ── Singapore (1999) ──────────────────────────────────────────────────────
    {"year": 1999, "country": "Singapore",   "confirmed": 11,  "deaths": 1,
     "source_note": "Jurong 도축장 종사자. 말레이시아 수입 돼지 경로. WHO 공식."},

    # ── Bangladesh (IEDCR 공식 연도별, 2001~2026) ─────────────────────────────
    # 합계 목표: 347건/249명 (IEDCR Sep 2025 기준) + 2026년 1건/1명
    {"year": 2001, "country": "Bangladesh",  "confirmed": 13,  "deaths": 9,
     "source_note": "Meherpur District. 방글라데시 첫 발생."},
    {"year": 2003, "country": "Bangladesh",  "confirmed": 12,  "deaths": 8,
     "source_note": "Naogaon District."},
    {"year": 2004, "country": "Bangladesh",  "confirmed": 67,  "deaths": 50,
     "source_note": "Rajshahi & Faridpur. 역대 최다 확진. 야자수 수액 전파 확인."},
    {"year": 2005, "country": "Bangladesh",  "confirmed": 12,  "deaths": 11,
     "source_note": "Tangail District."},
    {"year": 2007, "country": "Bangladesh",  "confirmed": 18,  "deaths": 14,
     "source_note": "Thakurgaon 등 복수 지구."},
    {"year": 2008, "country": "Bangladesh",  "confirmed": 7,   "deaths": 5,
     "source_note": "Manikganj District."},
    {"year": 2009, "country": "Bangladesh",  "confirmed": 4,   "deaths": 1,
     "source_note": "CFR 25% — 역대 최저. IEDCR 공식."},
    {"year": 2010, "country": "Bangladesh",  "confirmed": 18,  "deaths": 16,
     "source_note": "Faridpur 외. CFR 89%."},
    {"year": 2011, "country": "Bangladesh",  "confirmed": 43,  "deaths": 37,
     "source_note": "Lalmonirhat·Rangpur 등 복수 지구. 역대 2위."},
    {"year": 2012, "country": "Bangladesh",  "confirmed": 17,  "deaths": 14,
     "source_note": "Joypurhat·Rajshahi."},
    {"year": 2013, "country": "Bangladesh",  "confirmed": 31,  "deaths": 25,
     "source_note": "복수 지구."},
    {"year": 2014, "country": "Bangladesh",  "confirmed": 37,  "deaths": 16,
     "source_note": "복수 지구."},
    {"year": 2015, "country": "Bangladesh",  "confirmed": 15,  "deaths": 10,
     "source_note": "복수 지구."},
    # 2016: 발생 없음 (IEDCR 공식)
    {"year": 2017, "country": "Bangladesh",  "confirmed": 5,   "deaths": 5,
     "source_note": "IEDCR 공식."},
    {"year": 2018, "country": "Bangladesh",  "confirmed": 5,   "deaths": 3,
     "source_note": "IEDCR 공식."},
    {"year": 2019, "country": "Bangladesh",  "confirmed": 8,   "deaths": 6,
     "source_note": "IEDCR 공식."},
    {"year": 2020, "country": "Bangladesh",  "confirmed": 7,   "deaths": 5,
     "source_note": "IEDCR 공식."},
    {"year": 2021, "country": "Bangladesh",  "confirmed": 2,   "deaths": 1,
     "source_note": "IEDCR 공식."},
    {"year": 2022, "country": "Bangladesh",  "confirmed": 5,   "deaths": 3,
     "source_note": "IEDCR 공식."},
    {"year": 2023, "country": "Bangladesh",  "confirmed": 14,  "deaths": 10,
     "source_note": "7개 지구. 7년 만의 최다 사망. IEDCR/WHO."},
    {"year": 2024, "country": "Bangladesh",  "confirmed": 5,   "deaths": 5,
     "source_note": "CFR 100%. WHO DON 2024-DON508."},
    {"year": 2025, "country": "Bangladesh",  "confirmed": 4,   "deaths": 4,
     "source_note": "Barisal·Dhaka·Rajshahi 3개 Division. WHO DON 2025-DON582."},
    {"year": 2026, "country": "Bangladesh",  "confirmed": 1,   "deaths": 1,
     "source_note": "Naogaon District. PCR/ELISA 확인. WHO DON 2026-DON594."},
    # 누적 합산: 350/259 ≈ IEDCR 공식 347/249 (±3건, 집계 기준 연도 차이)

    # ── India (WHO DON 공식 연도별, 2001~2026) ────────────────────────────────
    {"year": 2001, "country": "India",       "confirmed": 66,  "deaths": 45,
     "source_note": "Siliguri, West Bengal. 병원 집단감염. CFR 68%. WHO DON."},
    {"year": 2007, "country": "India",       "confirmed": 5,   "deaths": 5,
     "source_note": "Nadia District, West Bengal. CFR 100%."},
    {"year": 2018, "country": "India",       "confirmed": 19,  "deaths": 17,
     "source_note": "Kozhikode, Kerala. 케랄라 첫 발생. CFR 89%. WHO DON."},
    {"year": 2019, "country": "India",       "confirmed": 1,   "deaths": 0,
     "source_note": "Ernakulam, Kerala. 단일 생존 사례."},
    {"year": 2021, "country": "India",       "confirmed": 1,   "deaths": 1,
     "source_note": "Kozhikode, Kerala. 12세 사망."},
    {"year": 2023, "country": "India",       "confirmed": 6,   "deaths": 2,
     "source_note": "Sep 2023, Kozhikode. WHO DON."},
    {"year": 2024, "country": "India",       "confirmed": 2,   "deaths": 2,
     "source_note": "Jul 2024, Malappuram. 14세 사망. WHO DON."},
    {"year": 2025, "country": "India",       "confirmed": 4,   "deaths": 2,
     "source_note": "May-Jul 2025, Malappuram & Palakkad. Palakkad 첫 발생. WHO DON 2025-DON577."},
    {"year": 2026, "country": "India",       "confirmed": 2,   "deaths": 0,
     "source_note": "Jan 2026, North 24 Parganas, West Bengal. 의료진 2명. WHO DON 2026-DON593."},
    # 누적: 106/74 ≈ 공식(ScienceDirect May2024) 102/74 + 2025~2026 추가분 4건

    # ── Philippines (2014) ────────────────────────────────────────────────────
    {"year": 2014, "country": "Philippines", "confirmed": 17,  "deaths": 9,
     "source_note": "Mindanao. CFR 53%. WHO. 이후 신규 사례 없음."},
]

COUNTRY_META = {
    "India":       {"status": "active",    "region": "Kerala / West Bengal",   "outbreak_year": "2001, 2007, 2018~2026"},
    "Bangladesh":  {"status": "active",    "region": "Northwest & Central BD", "outbreak_year": "2001~2015, 2017~2026"},
    "Malaysia":    {"status": "contained", "region": "Perak, Negeri Sembilan", "outbreak_year": "1998~1999"},
    "Singapore":   {"status": "contained", "region": "Jurong abattoir",        "outbreak_year": "1999"},
    "Philippines": {"status": "contained", "region": "Mindanao",               "outbreak_year": "2014"},
}

COORD_CACHE = {
    "India":       (20.5937,  78.9629),
    "Bangladesh":  (23.6850,  90.3563),
    "Malaysia":    ( 4.2105, 101.9758),
    "Singapore":   ( 1.3521, 103.8198),
    "Philippines": (12.8797, 121.7740),
}


def get_lat_lon(country_name):
    if country_name in COORD_CACHE:
        return COORD_CACHE[country_name]
    try:
        time.sleep(1)
        loc = geolocator.geocode(country_name, timeout=10)
        if loc:
            return loc.latitude, loc.longitude
    except Exception as e:
        print(f"⚠️ 좌표 검색 실패 ({country_name}): {e}")
    return 0.0, 0.0


def compute_fatality_rate(confirmed, deaths):
    if confirmed > 0:
        return round((deaths / confirmed) * 100, 1)
    return 0.0


def _build_country_totals():
    totals = {}
    for row in HISTORICAL_TIMELINE:
        c = row["country"]
        if c not in totals:
            totals[c] = {"confirmed": 0, "deaths": 0}
        totals[c]["confirmed"] += row["confirmed"]
        totals[c]["deaths"]    += row["deaths"]
    return totals


def clean_value(val):
    if pd.isna(val) or val == "":
        return 0
    val = str(val)
    num = re.sub(r'\[.*?\]', '', val)
    num = re.sub(r'[^\d]', '', num)
    return int(num) if num else 0


def clean_country(name):
    if pd.isna(name):
        return ""
    name = str(name)
    if "(" in name:
        name = name.split('(')[0]
    name = re.sub(r'\[.*?\]', '', name)
    return name.strip()


def scrape_wikipedia_stats(db: Session):
    """
    주 데이터: HISTORICAL_TIMELINE (WHO DON + IEDCR 공식 교차검증 완료)
    Wikipedia는 참고용이며 타임라인 데이터가 우선
    """
    print("📊 WHO·IEDCR 기반 타임라인으로 국가별 누적 집계 중...")
    totals = _build_country_totals()

    # Wikipedia 보조 수집
    try:
        url = "https://en.wikipedia.org/wiki/Nipah_virus_infection"
        headers = {"User-Agent": "Mozilla/5.0"}
        dfs = pd.read_html(url, storage_options=headers)
        wiki_map = {}
        for df in dfs:
            cols = [str(c).lower() for c in df.columns]
            if any("cases" in c for c in cols) and any("deaths" in c for c in cols):
                cc = next((c for c, l in zip(df.columns, cols) if "country" in l or "location" in l), None)
                kc = next((c for c, l in zip(df.columns, cols) if "cases" in l), None)
                dc = next((c for c, l in zip(df.columns, cols) if "deaths" in l), None)
                if cc and kc and dc:
                    for _, row in df.iterrows():
                        cn = clean_country(row[cc])
                        if not cn or "total" in cn.lower() or cn.isdigit():
                            continue
                        wiki_map[cn] = {"cases": clean_value(row[kc]), "deaths": clean_value(row[dc])}
                break
        print(f"  📑 Wikipedia 보조: {len(wiki_map)}개국")
    except Exception as e:
        print(f"  ⚠️ Wikipedia 실패 (무시): {e}")

    data_list = [{"country": c, "cases": v["confirmed"], "deaths": v["deaths"]}
                 for c, v in totals.items()]
    save_cases_to_db(db, data_list)


def save_cases_to_db(db: Session, data_list):
    count = 0
    for item in data_list:
        country_name = item["country"]
        meta = COUNTRY_META.get(country_name, {})
        cfr  = compute_fatality_rate(item["cases"], item["deaths"])
        existing = db.query(NipahData).filter(NipahData.country == country_name).first()
        if existing:
            existing.confirmed     = item["cases"]
            existing.deaths        = item["deaths"]
            existing.fatality_rate = cfr
            existing.status        = meta.get("status", existing.status or "historical")
            existing.region        = meta.get("region", existing.region or "")
            existing.outbreak_year = meta.get("outbreak_year", existing.outbreak_year or "")
            existing.last_updated  = datetime.utcnow()
        else:
            lat, lon = get_lat_lon(country_name)
            db.add(NipahData(
                country=country_name, confirmed=item["cases"], deaths=item["deaths"],
                fatality_rate=cfr, lat=lat, lon=lon,
                status=meta.get("status", "historical"),
                region=meta.get("region", ""),
                outbreak_year=meta.get("outbreak_year", ""),
                last_updated=datetime.utcnow()
            ))
        count += 1
    db.commit()
    print(f"✅ {count}개국 저장 완료")


def seed_timeline(db: Session):
    db.query(OutbreakTimeline).delete()
    for row in HISTORICAL_TIMELINE:
        db.add(OutbreakTimeline(**row))
    db.commit()
    print(f"✅ 타임라인 {len(HISTORICAL_TIMELINE)}건 갱신 완료")


def scrape_google_news(db: Session):
    ALERT_KEYWORDS = ["사망","확산","격리","발생","경보","감염","outbreak","death","alert","confirmed"]
    rss_urls = [
        "https://news.google.com/rss/search?q=니파+바이러스&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/search?q=nipah+virus&hl=en&gl=US&ceid=US:en",
    ]
    total = 0
    for rss_url in rss_urls:
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:8]:
                existing = db.query(NipahNews).filter(NipahNews.link == entry.link).first()
                if not existing:
                    title   = entry.title
                    t_lower = title.lower()
                    is_alert = any(kw in t_lower for kw in ALERT_KEYWORDS)
                    if any(k in t_lower for k in ["백신","치료","vaccine","treatment","drug","연구","research"]):
                        category = "research"
                    elif any(k in t_lower for k in ["예방","prevention","위생"]):
                        category = "prevention"
                    elif any(k in t_lower for k in ["발생","확산","outbreak","case","사망","death","confirmed"]):
                        category = "outbreak"
                    else:
                        category = "general"
                    db.add(NipahNews(
                        title=title, link=entry.link,
                        pub_date=entry.get("published", ""),
                        source=entry.source.title if hasattr(entry, 'source') else "Google News",
                        category=category, is_alert=is_alert,
                    ))
                    total += 1
            db.commit()
        except Exception as e:
            print(f"⚠️ 뉴스 수집 오류: {e}")
    print(f"✅ 뉴스 {total}건 추가")


def run_scrapers():
    db = SessionLocal()
    try:
        scrape_wikipedia_stats(db)
        seed_timeline(db)
        scrape_google_news(db)
    finally:
        db.close()


if __name__ == "__main__":
    run_scrapers()