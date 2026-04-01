from pyspark.sql import SparkSession
from pyspark.sql.functions import to_timestamp, col, lit
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

from src.config.settings import DATA_DIR, DEVICES

SCHEMA = StructType([
    StructField("timestamp", StringType(), True),
    StructField("in", IntegerType(), True),
    StructField("out", IntegerType(), True),
])


def load_device(spark: SparkSession, device: str):
    path = str(DATA_DIR / device / "*.csv")
    return (
        spark.read.csv(path, header=True, schema=SCHEMA)
        .withColumn("location", lit(device))
        .withColumn("timestamp", to_timestamp(col("timestamp")))
    )


def extract(spark: SparkSession):
    if not DEVICES:
        raise RuntimeError(f"No device directories found in {DATA_DIR}")

    frames = [load_device(spark, device) for device in DEVICES]
    df = frames[0]
    for frame in frames[1:]:
        df = df.unionByName(frame)
    return df
