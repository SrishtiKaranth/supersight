import logging
from pyspark.sql import DataFrame
from psycopg2.extras import execute_values

from src.db_connection.connector import get_conn

logger = logging.getLogger(__name__)

HOURLY_INSERT = """
    INSERT INTO hourly_aggregations (location, hour, date, total_in, total_out, net_flow, occupancy)
    VALUES %s
"""

DAILY_INSERT = """
    INSERT INTO daily_aggregations (location, date, total_in, total_out, net_flow)
    VALUES %s
"""


def load_hourly(df: DataFrame):
    rows = [
        (r["location"], r["hour"], r["date"], r["total_in"], r["total_out"], r["net_flow"], r["occupancy"])
        for r in df.collect()
    ]
    _batch_insert(HOURLY_INSERT, rows, "hourly_aggregations")


def load_daily(df: DataFrame):
    rows = [
        (r["location"], r["date"], r["total_in"], r["total_out"], r["net_flow"])
        for r in df.collect()
    ]
    _batch_insert(DAILY_INSERT, rows, "daily_aggregations")


def _batch_insert(query: str, rows: list, table_name: str):
    if not rows:
        logger.warning("no rows for %s", table_name)
        return

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            execute_values(cur, query, rows, page_size=1000)
        conn.commit()
        logger.info("loaded %d rows into %s", len(rows), table_name)
    except Exception:
        conn.rollback()
        logger.exception("failed to insert into %s", table_name)
        raise
    finally:
        conn.close()
