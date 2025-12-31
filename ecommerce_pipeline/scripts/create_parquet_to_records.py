#!/usr/bin/env python3
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, LongType, StringType, DoubleType, TimestampType
from datetime import datetime

spark = (SparkSession.builder
         .appName("CreateSampleParquetRecords")
         .getOrCreate())

schema = StructType([
    StructField("order_id", LongType(), False),
    StructField("customer_name", StringType(), True),
    StructField("restaurant_name", StringType(), True),
    StructField("item", StringType(), True),
    StructField("amount", DoubleType(), True),
    StructField("order_status", StringType(), True),
    StructField("created_at", TimestampType(), True),
])

rows = [
    (2001, "SparkRec A", "R1", "Salad", 8.5, "PLACED", datetime.strptime("2025-12-05 12:10:00.000000", "%Y-%m-%d %H:%M:%S.%f")),
    (2002, "SparkRec B", "R2", "Pasta", 15.0, "DELIVERED", datetime.strptime("2025-12-05 12:11:00.000000", "%Y-%m-%d %H:%M:%S.%f")),
]

df = spark.createDataFrame(rows, schema=schema)
output_path = "/app/2025em1100102/output/records"
# write into a single-file parquet for easy inspection
(df.coalesce(1)
   .write
   .mode("overwrite")
   .parquet(output_path))

print(f"Wrote Parquet to: {output_path}")
spark.stop()
