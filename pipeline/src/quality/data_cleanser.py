import logging
from pyspark.sql import DataFrame

logger = logging.getLogger(__name__)


def cleanse(df: DataFrame) -> DataFrame:
    """Clean raw data: fill missing numeric values with zero."""
    before = df.count()

    df = df.fillna({"in": 0, "out": 0})

    after = df.count()
    logger.info("cleansed %d rows, filled missing in/out with 0", after)

    return df
