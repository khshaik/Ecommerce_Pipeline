from pyspark.sql import SparkSession

# 1. Initialize Spark with Kafka connector
spark = SparkSession.builder \
    .appName("KafkaTestConnection") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

print("Spark Session Created. Connecting to Kafka...")

# 2. Read from Kafka
# We must use 'kafka:29092' for internal Docker communication. kafka is the internal docker service name
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:29092") \
    .option("subscribe", "test_topic") \
    .option("startingOffsets", "earliest") \
    .load()

# 3. Cast the value from binary to string so we can read it
df_readable = df.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)")

# 4. Write to console to verify
print("Starting stream... (Wait 10-20 seconds for output)")
query = df_readable.writeStream \
    .outputMode("append") \
    .format("console") \
    .start()

# Run for 30 seconds then stop (just for testing purposes)
query.awaitTermination(timeout=30)
print("Test complete.")