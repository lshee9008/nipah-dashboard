from fastapi import FastAPI, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from database import SessionLocal, create_tables, NipahData, NipahNews, OutbreakTimeline
import scraper
from contextlib import asynccontextmanager
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone="UTC")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def scheduled_scrape():
    try:
        scraper.run_scrapers()
    except Exception as e:
        logger.error(f"크롤링 실패: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    scraper.run_scrapers()
    scheduler.add_job(scheduled_scrape, "interval", hours=6, id="auto_scrape")
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def row_to_dict(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}

@app.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    stats_raw = db.query(NipahData).all()
    stats = [row_to_dict(d) for d in stats_raw]

    total_confirmed = sum(d["confirmed"] for d in stats)
    total_deaths    = sum(d["deaths"] for d in stats)
    avg_cfr = round((total_deaths / total_confirmed * 100) if total_confirmed else 0, 1)
    active_count = sum(1 for d in stats if d["status"] == "active")

    news_raw = (
        db.query(NipahNews)
          .order_by(NipahNews.is_alert.desc(), NipahNews.id.desc())
          .limit(10).all()
    )
    news_list = [row_to_dict(n) for n in news_raw]

    current_year = datetime.now().year
    recent_years = list(range(current_year - 4, current_year + 1))

    timeline_raw = db.query(OutbreakTimeline).order_by(OutbreakTimeline.year).all()
    all_by_year = {}
    for row in timeline_raw:
        y = row.year
        if y not in all_by_year:
            all_by_year[y] = {"confirmed": 0, "deaths": 0}
        all_by_year[y]["confirmed"] += row.confirmed
        all_by_year[y]["deaths"]    += row.deaths

    recent_confirmed = [all_by_year.get(y, {}).get("confirmed", 0) for y in recent_years]
    recent_deaths    = [all_by_year.get(y, {}).get("deaths", 0)    for y in recent_years]
    all_labels    = sorted(all_by_year.keys())
    all_confirmed = [all_by_year[y]["confirmed"] for y in all_labels]
    all_deaths    = [all_by_year[y]["deaths"]    for y in all_labels]

    cfr_data = sorted(
        [{"country": d["country"], "cfr": d["fatality_rate"]} for d in stats if d["confirmed"] > 0],
        key=lambda x: x["cfr"], reverse=True
    )

    recent_events = sorted(
        [{"year": r.year, "country": r.country, "confirmed": r.confirmed,
          "deaths": r.deaths, "source_note": (r.source_note or "")[:35]}
         for r in timeline_raw if r.year >= current_year - 3],
        key=lambda x: (x["year"], x["confirmed"]), reverse=True
    )[:8]

    last_raw = db.query(NipahData).order_by(NipahData.last_updated.desc()).first()
    last_updated_str = last_raw.last_updated.strftime("%Y-%m-%d %H:%M UTC") if last_raw else "—"

    return templates.TemplateResponse("index.html", {
        "request":          request,
        "stats":            stats,
        "total_confirmed":  total_confirmed,
        "total_deaths":     total_deaths,
        "avg_cfr":          avg_cfr,
        "active_count":     active_count,
        "news_list":        news_list,
        "recent_labels":    json.dumps(recent_years),
        "recent_confirmed": json.dumps(recent_confirmed),
        "recent_deaths":    json.dumps(recent_deaths),
        "all_labels":       json.dumps(all_labels),
        "all_confirmed":    json.dumps(all_confirmed),
        "all_deaths":       json.dumps(all_deaths),
        "cfr_labels":       json.dumps([d["country"] for d in cfr_data]),
        "cfr_values":       json.dumps([d["cfr"]     for d in cfr_data]),
        "recent_events":    recent_events,
        "last_updated_str": last_updated_str,
        "current_year":     current_year,
    })

@app.get("/health")
async def health():
    return {"status": "ok", "ts": datetime.utcnow().isoformat()}

@app.get("/api/refresh")
async def refresh():
    scraper.run_scrapers()
    return JSONResponse({"status": "ok", "ts": datetime.utcnow().isoformat()})

@app.get("/api/stats")
async def api_stats(db: Session = Depends(get_db)):
    stats = db.query(NipahData).all()
    return [row_to_dict(d) for d in stats]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
