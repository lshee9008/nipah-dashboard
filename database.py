import os
import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# ── DB URL: 환경변수 DATABASE_URL 있으면 PostgreSQL, 없으면 SQLite (로컬 개발용) ──
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # Render/Railway PostgreSQL은 postgres:// 로 오는 경우가 있어 교정
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    DB_PATH = os.environ.get("DB_PATH", "./nipah.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class NipahData(Base):
    __tablename__ = "nipah_cases"
    id            = Column(Integer, primary_key=True, index=True)
    country       = Column(String, unique=True, index=True)
    confirmed     = Column(Integer, default=0)
    deaths        = Column(Integer, default=0)
    recovered     = Column(Integer, default=0)
    lat           = Column(Float)
    lon           = Column(Float)
    region        = Column(String, default="")
    outbreak_year = Column(String, default="")
    fatality_rate = Column(Float, default=0.0)
    status        = Column(String, default="historical")
    last_updated  = Column(DateTime, default=datetime.utcnow)


class NipahNews(Base):
    __tablename__ = "nipah_news"
    id       = Column(Integer, primary_key=True, index=True)
    title    = Column(String)
    link     = Column(String, unique=True)
    pub_date = Column(String)
    source   = Column(String)
    category = Column(String, default="general")
    is_alert = Column(Boolean, default=False)


class OutbreakTimeline(Base):
    __tablename__ = "outbreak_timeline"
    id          = Column(Integer, primary_key=True, index=True)
    year        = Column(Integer)
    country     = Column(String)
    confirmed   = Column(Integer, default=0)
    deaths      = Column(Integer, default=0)
    source_note = Column(Text, default="")


_MIGRATIONS = {
    "nipah_cases": [
        ("recovered",     "INTEGER", "0"),
        ("region",        "TEXT",    "''"),
        ("outbreak_year", "TEXT",    "''"),
        ("fatality_rate", "REAL",    "0.0"),
        ("status",        "TEXT",    "'historical'"),
    ],
    "nipah_news": [
        ("category", "TEXT",    "'general'"),
        ("is_alert", "INTEGER", "0"),
    ],
}


def _migrate_sqlite(conn):
    cursor = conn.cursor()
    for table, cols in _MIGRATIONS.items():
        cursor.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in cursor.fetchall()}
        for col_name, col_type, default in cols:
            if col_name not in existing:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type} DEFAULT {default}")
                print(f"  ✅ 마이그레이션: {table}.{col_name}")
    conn.commit()


def create_tables():
    Base.metadata.create_all(bind=engine)
    # SQLite 전용 마이그레이션 (PostgreSQL은 create_all이 컬럼 자동 처리)
    if "sqlite" in str(engine.url):
        db_path = str(engine.url).replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        try:
            _migrate_sqlite(conn)
        finally:
            conn.close()