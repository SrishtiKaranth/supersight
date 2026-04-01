import logging
import sys

from pyspark.sql import SparkSession

from src.config.logging_config import setup_logging
from src.db_connection.connector import check_connection, setup_tables
from src.quality.schema_validator import validate_schema
from src.quality.data_profiler import profile
from src.quality.data_cleanser import cleanse
from src.extract.fetch_data import extract
from src.transform.aggregations import build_hourly, build_daily
from src.load.load_to_db import load_hourly, load_daily

logger = logging.getLogger(__name__)


def main():
    setup_logging()

    
    try: 
        check_connection() #verify database connectivity
    except Exception as e:
        logger.error("db connection failed: %s", e)
        sys.exit(1)

    #setup and validate schema
    try:
        setup_tables()
        validate_schema()
    except Exception as e:
        logger.error("schema setup failed: %s", e)
        sys.exit(1)

    logger.info("pipeline started")

    spark = SparkSession.builder.appName("CountingPeople").getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")

    try:
        #extract
        raw = extract(spark)

        #profile
        profile(raw)

        #cleanse
        cleaned = cleanse(raw)

        #transform
        hourly = build_hourly(cleaned)
        daily = build_daily(hourly)

        #load
        load_hourly(hourly)
        load_daily(daily)

        logger.info("pipeline complete")
    except Exception as e:
        logger.error("pipeline failed: %s", e)
        sys.exit(1)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
