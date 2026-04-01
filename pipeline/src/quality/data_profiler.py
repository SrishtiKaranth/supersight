import logging
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, min as _min, max as _max
from pyspark.sql.types import NumericType

logger = logging.getLogger(__name__)


def _is_numeric(df: DataFrame, field: str) -> bool:
    return isinstance(df.schema[field].dataType, NumericType)


def profile(df: DataFrame) -> dict:
    """Profile raw input data. row count, nulls, value ranges, duplicates."""
    total = df.count()
    logger.info("profiling %d records", total)

    # Null counts per column 
    null_counts = {}
    for field in df.columns:
        condition = col(field).isNull()
        null_count = df.filter(condition).count()
        null_counts[field] = null_count
        if null_count > 0:
            logger.warning("'%s' has %d nulls (%.1f%%)", field, null_count, 100 * null_count / total)

    # Value ranges for numeric columns
    stats = df.select(
        _min("in").alias("min_in"),
        _max("in").alias("max_in"),
        _min("out").alias("min_out"),
        _max("out").alias("max_out"),
    ).first()

    logger.info("in: [%s, %s] out: [%s, %s]",
                stats["min_in"], stats["max_in"], stats["min_out"], stats["max_out"])

    # Duplicate rows
    distinct_count = df.distinct().count()
    duplicates = total - distinct_count
    if duplicates > 0:
        logger.warning("Found %d duplicate rows", duplicates)

    # Timestamp range
    ts_stats = df.select(
        _min("timestamp").alias("earliest"),
        _max("timestamp").alias("latest"),
    ).first()
    logger.info("timestamps: %s to %s", ts_stats["earliest"], ts_stats["latest"])

    return {
        "total_rows": total,
        "distinct_rows": distinct_count,
        "duplicates": duplicates,
        "null_counts": null_counts,
        "value_ranges": {
            "in": (stats["min_in"], stats["max_in"]),
            "out": (stats["min_out"], stats["max_out"]),
        },
        "timestamp_range": (ts_stats["earliest"], ts_stats["latest"]),
    }
