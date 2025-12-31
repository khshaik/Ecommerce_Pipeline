#!/usr/bin/env python3
# ============================================================================
# CONSUMER: orders_stream_consumer.py
# ============================================================================
# Real-Time Food Delivery Streaming - Spark Structured Streaming Consumer
#
# PURPOSE:
#   Continuously reads JSON events from Kafka, validates data, and writes
#   partitioned Parquet files to data lake using Spark Structured Streaming.
#
# LOGIC FLOW:
#   1. Initialize Spark Session with Kafka connector
#   2. Load configuration from YAML file
#   3. Define DataFrame schema (order fields and types)
#   4. Read streaming data from Kafka topic
#   5. Parse JSON messages using schema
#   6. Apply data validation/cleaning:
#      - Drop rows with null order_id
#      - Drop rows with negative amount
#   7. Derive date partition (extract YYYY-MM-DD from created_at)
#   8. Write to partitioned Parquet with checkpointing
#   9. Start stream and wait indefinitely (production mode)
#
# TODO TASKS:
#   - [COMPLETED] Read YAML config
#   - [COMPLETED] Build Kafka consumer config
#   - [COMPLETED] Define schema from config
#   - [COMPLETED] Read from Kafka topic
#   - [COMPLETED] Parse JSON with schema
#   - [COMPLETED] Validate/clean rows
#   - [COMPLETED] Add date partition column
#   - [COMPLETED] Write partitioned Parquet
#   - [COMPLETED] Setup checkpointing
#
# ============================================================================

import sys
import argparse
import yaml
from pathlib import Path
from datetime import datetime

# Spark imports
from pyspark.sql import SparkSession
from pyspark.sql.functions import trim, length, when, lit, col
from pyspark.sql.functions import (
    from_json, col, when, date_format, to_timestamp
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, 
    LongType, TimestampType, IntegerType
)

# ============================================================================
# CONFIGURATION LOADING
# ============================================================================

def load_config(config_path):
    """
    Load YAML configuration file.
    
    Args:
        config_path (str): Path to YAML config file
        
    Returns:
        dict: Parsed configuration dictionary
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is invalid
    """
    print(f"[CONSUMER] Loading configuration from: {config_path}")
    
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    print(f"[CONSUMER] Configuration loaded successfully")
    return config


# ============================================================================
# SPARK SESSION INITIALIZATION
# ============================================================================

def init_spark_session():
    """
    Initialize Spark Session with necessary configurations.
    
    Includes:
    - Kafka connector JAR (org.apache.spark:spark-sql-kafka-0-10)
    - Parquet writer support (built-in)
    
    Returns:
        SparkSession: Configured Spark session
    """
    print("[CONSUMER] Initializing Spark Session...")
    
    spark = (SparkSession.builder
        .appName("FoodOrdersStreamConsumer")
        .config("spark.jars.packages", 
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1")
        .config("spark.driver.memory", "2g")
        .config("spark.executor.memory", "2g")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.streaming.schemaInference", "true")
        .getOrCreate())
    
    # Reduce logging verbosity
    spark.sparkContext.setLogLevel("WARN")
    
    print("[CONSUMER] Spark Session initialized")
    return spark


# ============================================================================
# SCHEMA DEFINITION
# ============================================================================

def build_schema():
    """
    Define Spark SQL schema for orders data.
    
    Schema matches the PostgreSQL orders table:
    - order_id: BIGINT (primary key)
    - customer_name: STRING
    - restaurant_name: STRING
    - item: STRING
    - amount: DOUBLE (in currency units)
    - order_status: STRING (enum: PLACED, PREPARING, DELIVERED, CANCELLED)
    - created_at: TIMESTAMP (record creation time in UTC)
    
    Returns:
        StructType: Spark schema
    """
    schema = StructType([
        StructField("order_id", LongType(), False),           # NOT NULL
        StructField("customer_name", StringType(), True),     # Nullable
        StructField("restaurant_name", StringType(), True),   # Nullable
        StructField("item", StringType(), True),              # Nullable
        StructField("amount", DoubleType(), True),            # Nullable
        StructField("order_status", StringType(), True),      # Nullable
        StructField("created_at", TimestampType(), True),     # Nullable
    ])
    
    print("[CONSUMER] Schema defined")
    
    return schema


# ============================================================================
# KAFKA READER CONFIGURATION
# ============================================================================

def build_kafka_consumer_config(config):
    """
    Build Kafka consumer configuration dictionary.
    
    Used by Spark readStream.format("kafka").options(...).
    
    Args:
        config (dict): Configuration dictionary with Kafka settings
        
    Returns:
        dict: Kafka options (bootstrap.servers, subscribe, startingOffsets, etc.)
    """
    kafka_config = config['kafka']
    consumer_config = config['consumer']
    
    options = {
        "kafka.bootstrap.servers": kafka_config['brokers'],
        "subscribe": kafka_config['topic'],
        # Start from earliest offsets on FIRST run only
        # On subsequent runs, Kafka consumer group tracks offsets automatically
        # This ensures all historical messages are consumed initially
        "startingOffsets": "earliest",
        # For consumer group and offset tracking
        # Kafka remembers where each consumer group left off
        "kafka.group.id": kafka_config['consumer_group'],
        # Max offsets per trigger (batch size control)
        "maxOffsetsPerTrigger": str(consumer_config['maxOffsetsPerTrigger']),
        # Handle Kafka data loss gracefully (retention policy may delete old messages)
        # If offsets are lost, skip to latest available instead of failing
        "failOnDataLoss": "false",
    }
    
    print("[CONSUMER] Kafka consumer configuration:")
    for key, val in options.items():
        print(f"  {key}: {val}")
    
    return options


# ============================================================================
# DATA VALIDATION & CLEANING
# ============================================================================

def apply_data_validation(df, config):
    """
    Tag each row as SUCCESS / FAILED based on validation rules,
    without dropping any rows.

    Rules (from config.validation):
    1. Filter out rows with null order_id (existing check - preserved logically)
    2. Filter out rows with negative amount (existing check - preserved logically)
    3. Filter out rows with null/empty customer_name
    4. Filter out rows with null/empty restaurant_name
    5. Filter out rows with null/empty item
    6. Filter out rows with null/empty order_status
    7. Filter out rows with null amount
    """
    from pyspark.sql.functions import trim, length

    validation = config.get('validation', {})
    allow_null_order_id = validation.get('allow_null_order_id', False)
    allow_negative_amount = validation.get('allow_negative_amount', False)

    print("[CONSUMER] Applying data validation rules (tagging rows)...")

    # Build one big "is_valid" condition
    cond = lit(True)

    # Rule 1: order_id must be non-null
    if not allow_null_order_id:
        print("[CONSUMER] RULE 1: order_id must be non-null")
        cond = cond & col("order_id").isNotNull()

    # Rule 2: amount must be non-negativea and non-zero
    if not allow_negative_amount:
        print("[CONSUMER] RULE 2: amount must be non-negative and non-zero i.e. >0")
        cond = cond & (col("amount") > 0)

    # Rule 3: customer_name must be not null and not empty
    print("[CONSUMER] RULE 3: customer_name must be not null/empty")
    cond = cond & col("customer_name").isNotNull() & (length(trim(col("customer_name"))) > 0)

    # Rule 4: restaurant_name must be not null and not empty
    print("[CONSUMER] RULE 4: restaurant_name must be not null/empty")
    cond = cond & col("restaurant_name").isNotNull() & (length(trim(col("restaurant_name"))) > 0)

    # Rule 5: item must be not null and not empty
    print("[CONSUMER] RULE 5: item must be not null/empty")
    cond = cond & col("item").isNotNull() & (length(trim(col("item"))) > 0)

    # Rule 6: order_status must be not null and not empty
    print("[CONSUMER] RULE 6: order_status must be not null/empty")
    cond = cond & col("order_status").isNotNull() & (length(trim(col("order_status"))) > 0)

    # Rule 7: amount must be not null
    print("[CONSUMER] RULE 7: amount must be not null")
    cond = cond & col("amount").isNotNull()

    # Tag rows with SUCCESS / FAILED
    df = df.withColumn(
        "validation_status",
        when(cond, lit("SUCCESS")).otherwise(lit("FAILED"))
    )

    print("[CONSUMER] Data validation tagging applied")
    return df


# ============================================================================
# DATE PARTITION DERIVATION
# ============================================================================

def add_date_partition(df):
    """
    Derive date partition column from created_at timestamp.
    
    Extracts YYYY-MM-DD from created_at, stored in 'date' column.
    Used for partitioning Parquet output by date.
    
    Format: /output_path/date=2025-11-18/part-0001.parquet
    
    Args:
        df (DataFrame): DataFrame with 'created_at' timestamp column
        
    Returns:
        DataFrame: Same DataFrame with added 'date' column
    """
    print("[CONSUMER] Adding date partition column...")
    
    df = df.withColumn(
        "date",
        date_format(col("created_at"), "yyyy-MM-dd")
    )
    
    print("[CONSUMER] Date partition column added")
    return df


# ============================================================================
# SPARK STRUCTURED STREAMING WRITER
# ============================================================================

def setup_streaming_writer(df, config):
    """
    Configure and return Spark Structured Streaming DataFrame writer.
    
    Configuration:
    - Format: Parquet (columnar, compressed, efficient)
    - Output path: Partitioned by date (YYYY-MM-DD)
    - Checkpoint location: For offset tracking and recovery
    - Mode: append (add new data without removing existing)
    - Trigger: every N seconds or continuous
    
    Args:
        df (DataFrame): Input streaming DataFrame (after validation)
        config (dict): Configuration with consumer settings
        
    Returns:
        DataFrameWriter: Configured writer (not yet executed)
    """
    consumer = config['consumer']
    # Get output path from datalake configuration
    datalake_cfg = config['datalake']
    output_path = datalake_cfg['path']

    streaming_cfg = config['streaming']
    checkpoint_dir = streaming_cfg['checkpoint_location']
    batch_interval_sec = streaming_cfg['batch_interval']
    
    # Convert batch_interval (in seconds) to Scala Duration format
    # Scala Duration parser accepts formats like "5 seconds", "100 milliseconds", etc.
    if isinstance(batch_interval_sec, str):
        interval_sec = int(batch_interval_sec.strip())
    else:
        interval_sec = int(batch_interval_sec)
    
    trigger_interval_str = f"{interval_sec} seconds"
    
    print("[CONSUMER] Setting up streaming writer...")
    print(f"  Output path: {output_path}")
    print(f"  Checkpoint dir: {checkpoint_dir}")
    print(f"  Partition by: date")
    print(f"  Trigger interval: {trigger_interval_str}")
    
    # Configure write stream
    writer = (df.writeStream
        .format("parquet")
        .option("path", output_path)
        .option("checkpointLocation", checkpoint_dir)
        .partitionBy("date")
        .outputMode("append")
        .trigger(processingTime=trigger_interval_str))
    
    return writer


# ============================================================================
# STREAMING QUERY EXECUTION
# ============================================================================

def run_streaming_consumer(spark, config):
    """
    Main streaming consumer - reads Kafka and writes Parquet indefinitely.
    
    Steps:
    1. Read from Kafka topic as streaming DataFrame
    2. Extract JSON from Kafka message value
    3. Parse JSON using schema
    4. Apply validation/cleaning
    5. Add date partition column
    6. Write to partitioned Parquet
    7. Run indefinitely (await termination)
    
    Args:
        spark (SparkSession): Spark session
        config (dict): Configuration dictionary
        
    Raises:
        KeyboardInterrupt: When user presses Ctrl+C
        Exception: If streaming query fails
    """
    query = None
    print("[CONSUMER] ========================================")
    print("[CONSUMER] STARTING SPARK STRUCTURED STREAMING")
    print("[CONSUMER] ========================================")
    
    try:
        # STEP 1: Read from Kafka
        print("\n[CONSUMER] STEP 1: Reading from Kafka topic...")
        kafka_options = build_kafka_consumer_config(config)
        
        df_kafka = (spark
            .readStream
            .format("kafka")
            .options(**kafka_options)
            .load())
        
        # DEBUG: Print Kafka raw messages (value only)
        df_kafka.select(col("value").cast("string")).writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", False) \
        .trigger(processingTime="10 seconds") \
        .start()
        
        print(f"[CONSUMER] Kafka stream initialized")
        
        # STEP 2: Extract and parse JSON
        print("[CONSUMER] STEP 2: Parsing JSON messages...")
        schema = build_schema()
        
        # Kafka message format:
        # {
        #   "key": null,
        #   "value": "{\"order_id\":1,\"customer_name\":\"Alice\",...}",
        #   "topic": "2025em1100102_food_orders_raw",
        #   "partition": 0,
        #   "offset": 123,
        #   "timestamp": 1234567890000,
        #   "timestampType": 0
        # }
        
        # Extract value column (JSON string) and parse it
        df_json = df_kafka.select(
            from_json(
                col("value").cast("string"),
                schema
            ).alias("data")
        ).select("data.*")

        # Capture original incoming records as FAILED (will be anti-joined)
        df_failed = df_json.withColumn("validation_status", lit("FAILED"))
        
        print("[CONSUMER] JSON parsed successfully")
        
        # STEP 3: Validate and clean
        print("[CONSUMER] STEP 3: Applying data validation...")
        df_with_status = apply_data_validation(df_json, config)

        # DEBUG: Print FAILED validation records
        print("[CONSUMER] FAILED validation records...")
        df_failed_records = df_with_status.filter(col("validation_status") == "FAILED")
        df_failed_records.select("*").writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", False) \
        .trigger(processingTime="10 seconds") \
        .start()
        
        # STEP 4: Add partition column
        print("[CONSUMER] SUCCESS validation records...")
        print("[CONSUMER] STEP 4: Adding date partition...")
        df_success = df_with_status.filter(col("validation_status") == "SUCCESS")
        df_partitioned = add_date_partition(df_success)

        # DEBUG: Print parsed validated rows before Parquet write
        df_partitioned.writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", False) \
        .trigger(processingTime="10 seconds") \
        .start()
        
        # STEP 5: Setup and execute writer
        print("[CONSUMER] STEP 5: Writing to Parquet...")
        writer = setup_streaming_writer(df_partitioned, config)
        
        # STEP 6: Start streaming query
        print("[CONSUMER] STEP 6: Starting streaming query...")
        query = writer.start()
        
        print("[CONSUMER] ========================================")
        print("[CONSUMER] STREAMING QUERY STARTED")
        print("[CONSUMER] Query ID:", query.id)
        print("[CONSUMER] Query Name:", query.name)
        print("[CONSUMER] ========================================")
        
        # STEP 7: Run indefinitely
        # In production, this awaits termination (never returns unless error)
        timeout_sec = config['consumer']['await_termination_timeout']
        
        if timeout_sec > 0:
            print(f"[CONSUMER] Waiting for {timeout_sec} seconds...")
            query.awaitTermination(timeout=timeout_sec)
        else:
            print("[CONSUMER] Running indefinitely (Ctrl+C to stop)...")
            query.awaitTermination()
        
    except KeyboardInterrupt:
        print("\n[CONSUMER] ========================================")
        print("[CONSUMER] RECEIVED SHUTDOWN SIGNAL (Ctrl+C)")
        print("[CONSUMER] Gracefully shutting down...")
        print("[CONSUMER] ========================================")
        if query:
            query.stop()
        sys.exit(0)
        
    except Exception as e:
        print(f"[CONSUMER] ERROR in streaming query: {e}")
        import traceback
        traceback.print_exc()
        if query:
            query.stop()
        raise


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """
    Main entry point for Spark Structured Streaming Consumer.
    
    Parses command-line arguments:
    --config: Path to YAML configuration file
    
    Initializes Spark and starts streaming consumer.
    """
    parser = argparse.ArgumentParser(
        description="Food Orders Stream Consumer - Reads from Kafka, writes Parquet"
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to YAML configuration file (e.g., configs/orders_stream.yml)"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("FOOD DELIVERY - REAL-TIME STREAMING CONSUMER")
    print("=" * 80)
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Initialize Spark Session
        spark = init_spark_session()
        
        # Start streaming consumer
        run_streaming_consumer(spark, config)
        
    except FileNotFoundError as e:
        print(f"[CONSUMER] FATAL: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("[CONSUMER] Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"[CONSUMER] FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()