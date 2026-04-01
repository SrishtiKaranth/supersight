from pyspark.sql import DataFrame
from pyspark.sql.functions import col, date_trunc, sum as _sum, to_date
from pyspark.sql.window import Window


def build_hourly(df: DataFrame) -> DataFrame:
    hourly = (
        df.withColumn("hour", date_trunc("hour", col("timestamp")))
        .groupBy("location", "hour")
        .agg(
            _sum("in").alias("total_in"),
            _sum("out").alias("total_out"),
        )
        .withColumn("net_flow", col("total_in") - col("total_out"))
        .withColumn("date", to_date(col("hour")))
    )

    window = (
        Window.partitionBy("location", "date")
        .orderBy("hour")
        .rowsBetween(Window.unboundedPreceding, Window.currentRow)
    )

    return hourly.withColumn("occupancy", _sum("net_flow").over(window)).orderBy("location", "hour")


def build_daily(hourly: DataFrame) -> DataFrame:
    return (
        hourly.groupBy("location", "date")
        .agg(
            _sum("total_in").alias("total_in"),
            _sum("total_out").alias("total_out"),
        )
        .withColumn("net_flow", col("total_in") - col("total_out"))
        .orderBy("location", "date")
    )
