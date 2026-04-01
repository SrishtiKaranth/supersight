import logging
from src.db_connection.connector import get_conn

logger = logging.getLogger(__name__)

EXPECTED_SCHEMA = {
    "hourly_aggregations": {
        "id":        "integer",
        "location":  "text",
        "hour":      "timestamp without time zone",
        "date":      "date",
        "total_in":  "integer",
        "total_out": "integer",
        "net_flow":  "integer",
        "occupancy": "integer",
    },
    "daily_aggregations": {
        "id":       "integer",
        "location": "text",
        "date":     "date",
        "total_in": "integer",
        "total_out":"integer",
        "net_flow": "integer",
    },
}


def validate_schema():
    """Compare actual DB schema against expected."""
    conn = get_conn()
    errors = []
    try:
        with conn.cursor() as cur:
            for table, expected_columns in EXPECTED_SCHEMA.items():
                cur.execute("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (table,))
                actual_columns = {row[0]: row[1] for row in cur.fetchall()}

                if not actual_columns:
                    errors.append(f"Table '{table}' does not exist after setup")
                    continue

                for col_name, expected_type in expected_columns.items():
                    actual_type = actual_columns.get(col_name)
                    if actual_type is None:
                        errors.append(f"Table '{table}': missing column '{col_name}'")
                    elif actual_type != expected_type:
                        errors.append(
                            f"Table '{table}': column '{col_name}' has type '{actual_type}', expected '{expected_type}'"
                        )

                extra = set(actual_columns) - set(expected_columns)
                if extra:
                    errors.append(f"Table '{table}': unexpected columns {extra}")
    finally:
        conn.close()

    if errors:
        raise RuntimeError("schema validation failed:\n  " + "\n  ".join(errors))

    logger.info("schema valid")
