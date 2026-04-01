import logging
from pathlib import Path

import psycopg2
from src.config.settings import DB_CONFIG

logger = logging.getLogger(__name__)

SQL_DIR = Path(__file__).resolve().parent.parent.parent / "sql"


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def check_connection():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        logger.info("db connected")
    finally:
        conn.close()


def setup_tables():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            sql = (SQL_DIR / "create_tables.sql").read_text()
            cur.execute(sql)
            cur.execute("TRUNCATE hourly_aggregations, daily_aggregations;")
        conn.commit()
        logger.info("tables ready")
    finally:
        conn.close()
