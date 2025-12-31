#!/usr/bin/env python3
# ============================================================================
# PRODUCER: orders_cdc_producer.py
# ============================================================================
# Real-Time Food Delivery Streaming - CDC Producer
# 
# PURPOSE:
#   Implements incremental Change Data Capture (CDC) using a Spark DataFrame
#   to read new orders from PostgreSQL and publish them to Kafka as JSON.
#
# LOGIC FLOW:
#   1. Initialize Spark Session with Kafka connector
#   2. Load configuration from YAML file
#   3. Enter infinite loop (every poll_interval_sec):
#      a. Read last_processed_timestamp from state file (or use default)
#      b. Query PostgreSQL for rows where created_at > last_processed_timestamp
#      c. If new rows found:
#         - Convert DataFrame to JSON strings
#         - Publish to Kafka topic
#         - Update last_processed_timestamp to max(created_at) in batch
#      d. Sleep for poll_interval_sec
#   4. Handle errors gracefully (retry, log)
#
# TODO TASKS:
#   - [COMPLETED] Read YAML config
#   - [COMPLETED] Build JDBC connection string
#   - [COMPLETED] Query Postgres with timestamp filter
#   - [COMPLETED] Convert rows to JSON
#   - [COMPLETED] Send JSON to Kafka
#   - [COMPLETED] Persist last_processed_timestamp atomically
#
# ============================================================================

import sys
import argparse
import time
import yaml
from datetime import datetime
from pathlib import Path

# Spark imports
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    to_json, struct, col, max as spark_max, 
    date_format, from_utc_timestamp
)
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, LongType, TimestampType

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
    print(f"[PRODUCER] Loading configuration from: {config_path}")
    
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    print(f"[PRODUCER] Configuration loaded successfully")
    return config


# ============================================================================
# SPARK SESSION INITIALIZATION
# ============================================================================

def init_spark_session():
    """
    Initialize Spark Session with necessary configurations.
    
    Includes:
    - Kafka connector JAR (org.apache.spark:spark-sql-kafka-0-10)
    - PostgreSQL JDBC driver
    
    Returns:
        SparkSession: Configured Spark session
    """
    print("[PRODUCER] Initializing Spark Session...")
    
    spark = (SparkSession.builder
        .appName("FoodOrdersCDCProducer")
        .config("spark.jars.packages", 
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,"
                "org.postgresql:postgresql:42.7.1")
        .config("spark.driver.memory", "2g")
        .config("spark.executor.memory", "2g")
        .config("spark.sql.adaptive.enabled", "true")
        .getOrCreate())
    
    # Reduce logging verbosity
    spark.sparkContext.setLogLevel("WARN")
    
    print("[PRODUCER] Spark Session initialized")
    return spark


# ============================================================================
# TIMESTAMP STATE MANAGEMENT
# ============================================================================

def read_last_processed_timestamp(last_ts_file, default_timestamp):
    """
    Read last processed timestamp and last_order_id from state file.

    State file format (single-line):
        <timestamp_iso_with_microseconds>|<last_order_id>

    If file doesn't exist or is empty, return default timestamp and 0 as last_order_id.

    Args:
        last_ts_file (str): Path to state file (e.g., state/last_processed_timestamp.txt)
        default_timestamp (str): Default timestamp if file missing (YYYY-MM-DD HH:MM:SS)

    Returns:
        tuple: (timestamp_str, last_order_id)
    """
    ts_path = Path(last_ts_file)

    # Ensure parent directory exists
    ts_path.parent.mkdir(parents=True, exist_ok=True)

    if ts_path.exists():
        with open(ts_path, 'r') as f:
            content = f.read().strip()
            if content:
                # Parse optional "timestamp|order_id" format
                if '|' in content:
                    parts = content.split('|')
                    ts = parts[0]
                    try:
                        last_id = int(parts[1])
                    except Exception:
                        last_id = 0
                else:
                    ts = content
                    last_id = 0
                print(f"[PRODUCER] Last processed state: {ts}|{last_id}")
                return ts, last_id

    print(f"[PRODUCER] No state file found. Using default timestamp: {default_timestamp}")
    return default_timestamp, 0


def write_last_processed_timestamp(last_ts_file, timestamp, last_order_id=0):
    """
    Atomically write last processed timestamp and order_id to state file.

    Writes single-line: <timestamp_with_microseconds>|<last_order_id>

    Args:
        last_ts_file (str): Path to state file
        timestamp (str): Timestamp string with microseconds
        last_order_id (int): Last order id processed at that timestamp

    Raises:
        IOError: If file write fails
    """
    ts_path = Path(last_ts_file)
    ts_path.parent.mkdir(parents=True, exist_ok=True)

    # Write atomically using temp file + rename pattern
    temp_path = ts_path.with_suffix('.tmp')

    payload = f"{timestamp}|{int(last_order_id)}"

    try:
        with open(temp_path, 'w') as f:
            f.write(payload)
        temp_path.replace(ts_path)
        print(f"[PRODUCER] Updated last processed state: {payload}")
    except IOError as e:
        print(f"[PRODUCER] ERROR: Failed to write state file: {e}")
        raise


# ============================================================================
# JDBC CONNECTION BUILDER
# ============================================================================

def build_jdbc_url(config):
    """
    Build PostgreSQL JDBC connection URL from config.
    
    Format: jdbc:postgresql://host:port/database
    
    Args:
        config (dict): Configuration dictionary with 'postgres' key
        
    Returns:
        str: JDBC URL
    """
    pg = config['postgres']
    jdbc_url = (f"jdbc:postgresql://{pg['host']}:{pg['port']}"
                f"/{pg['db']}")
    return jdbc_url


def build_jdbc_options(config):
    """
    Build JDBC options dictionary for Spark JDBC reader.
    
    Args:
        config (dict): Configuration dictionary
        
    Returns:
        dict: JDBC options (url, user, password, driver, dbtable, etc.)
    """
    pg = config['postgres']
    return {
        "url": build_jdbc_url(config),
        "user": pg['user'],
        "password": pg['password'],
        "driver": pg['driver'],
    }


# ============================================================================
# CDC QUERY BUILDER
# ============================================================================

def build_cdc_query(config, last_timestamp, last_order_id=0):
    """
    Build SQL query to fetch new rows from PostgreSQL.
    
    Query: SELECT * FROM orders 
           WHERE created_at > 'last_timestamp'
           ORDER BY created_at ASC
           LIMIT batch_limit
    
    This ensures:
    - Only NEW records (created_at > last_timestamp)
    - Ordered by creation time (deterministic)
    - Bounded by batch_limit (prevents huge batches)
    
    Args:
        config (dict): Configuration dictionary
        last_timestamp (str): Last processed timestamp (YYYY-MM-DD HH:MM:SS)
        
    Returns:
        str: SQL query
    """
    table = config['postgres']['table']
    batch_limit = config['cdc']['batch_limit']
    
    # Build query with timestamp filter
    # Use combined condition to avoid re-reading rows with same timestamp
    # Fetch rows where created_at > last_ts OR (created_at = last_ts AND order_id > last_order_id)
    # Quote table name in case it starts with a number (e.g., "2025em1100102_orders")
    quoted_table = f'"{table}"'
    
    query = f"""
    (
        SELECT * 
        FROM {quoted_table}
        WHERE (created_at > '{last_timestamp}')
           OR (created_at = '{last_timestamp}' AND order_id > {last_order_id})
        ORDER BY created_at ASC, order_id ASC
        LIMIT {batch_limit}
    ) AS cdc_query
    """
    
    print(f"[PRODUCER] CDC Query: {query.strip()}")
    return query


# ============================================================================
# DATAFRAME TO JSON CONVERSION
# ============================================================================

def convert_dataframe_to_json(df):
    """
    Convert Spark DataFrame rows to JSON strings.
    
    Creates a single 'value' column containing JSON representation of each row.
    Format: {"order_id": 123, "customer_name": "Alice", ...}
    
    Args:
        df (DataFrame): Spark DataFrame with orders data
        
    Returns:
        DataFrame: Single-column DataFrame with 'value' (JSON strings)
    """
    # Create JSON from all columns using to_json(struct(*))
    # This creates: {"col1": val1, "col2": val2, ...}
    df_json = df.select(
        to_json(struct([df[col] for col in df.columns])).alias("value")
    )
    
    print(f"[PRODUCER] Converted {df.count()} rows to JSON format")
    return df_json


# ============================================================================
# KAFKA PRODUCER
# ============================================================================

def publish_to_kafka(df_json, config):
    """
    Publish JSON records to Kafka topic.
    
    Uses Spark DataFrame .write.format("kafka") API.
    - Each row's 'value' column becomes a Kafka message
    - Partition key is optional (round-robin if not specified)
    
    Args:
        df_json (DataFrame): DataFrame with 'value' (JSON strings)
        config (dict): Configuration dictionary with Kafka settings
        
    Raises:
        Exception: If Kafka write fails
    """
    kafka_config = config['kafka']
    bootstrap_servers = kafka_config['brokers']
    topic = kafka_config['topic']
    
    print(f"[PRODUCER] Publishing {df_json.count()} messages to Kafka topic: {topic}")
    
    try:
        # Write to Kafka using Spark DataFrame writer
        df_json.write \
            .format("kafka") \
            .option("kafka.bootstrap.servers", bootstrap_servers) \
            .option("topic", topic) \
            .option("checkpointLocation", "/tmp/kafka_checkpoint") \
            .mode("append") \
            .save()
        
        print(f"[PRODUCER] Successfully published to Kafka topic: {topic}")
        return True
        
    except Exception as e:
        print(f"[PRODUCER] ERROR: Failed to publish to Kafka: {e}")
        return False


# ============================================================================
# CDC POLLING LOOP
# ============================================================================

def run_cdc_polling_loop(spark, config):
    """
    Main CDC polling loop - runs indefinitely.
    
    Every poll_interval_sec:
    1. Read last_processed_timestamp
    2. Query Postgres for new rows (WHERE created_at > last_ts)
    3. If rows exist:
       - Convert to JSON
       - Publish to Kafka
       - Update last_processed_timestamp atomically
    4. Sleep and repeat
    
    Args:
        spark (SparkSession): Spark session
        config (dict): Configuration dictionary
        
    Raises:
        KeyboardInterrupt: When user presses Ctrl+C (graceful shutdown)
    """
    print("[PRODUCER] ========================================")
    print("[PRODUCER] STARTING CDC POLLING LOOP")
    print("[PRODUCER] ========================================")
    
    #poll_interval = config['cdc']['poll_interval_sec']
    #last_ts_file = config['cdc']['last_ts_file']
    #default_start_ts = config['cdc']['default_start_timestamp']
    poll_interval = config['cdc']['poll_interval_sec']
    state_dir = config['streaming']['last_processed_timestamp_location']
    last_ts_file = str(Path(state_dir) / "last_processed_timestamp.txt")
    default_start_ts = config['cdc']['default_start_timestamp']     
    jdbc_options = build_jdbc_options(config)
    
    poll_count = 0
    
    try:
        while True:
            poll_count += 1
            timestamp_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"\n[PRODUCER] ========== POLL #{poll_count} ({timestamp_now}) ==========")
            
            # STEP 1: Read last processed timestamp and last_order_id
            last_timestamp, last_order_id = read_last_processed_timestamp(last_ts_file, default_start_ts)

            # STEP 2: Build and execute CDC query (uses timestamp + order_id tie-breaker)
            cdc_query = build_cdc_query(config, last_timestamp, last_order_id)
            
            print(f"[PRODUCER] Reading from PostgreSQL...")
            try:
                df = spark.read \
                    .format("jdbc") \
                    .options(**jdbc_options) \
                    .option("dbtable", cdc_query) \
                    .load()
                
                row_count = df.count()
                print(f"[PRODUCER] Fetched {row_count} new records")
                
                # STEP 3: Process records if any
                if row_count > 0:
                    # Convert to JSON
                    df_json = convert_dataframe_to_json(df)

                    print("\n[PRODUCER] Records being pushed to Kafka:")
                    df_json.show(truncate=False)   # Shows all fields from DB query
                    
                    # Publish to Kafka
                    success = publish_to_kafka(df_json, config)
                    
                    # STEP 4: Update timestamp ONLY if Kafka publish succeeded
                    if success:
                        # Get max created_at from this batch
                        max_ts_row = df.agg(spark_max(col("created_at"))).collect()
                        max_timestamp = max_ts_row[0][0]

                        if max_timestamp:
                            # Include microsecond precision to avoid ties
                            max_ts_str = max_timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")
                            # Determine the maximum order_id for rows having max_timestamp
                            max_id_row = df.filter(col("created_at") == max_timestamp).agg({"order_id": "max"}).collect()
                            max_order_id = None
                            if max_id_row and max_id_row[0] and list(max_id_row[0].asDict().values()):
                                # extract the max value robustly
                                vals = list(max_id_row[0].asDict().values())
                                max_order_id = vals[0]
                            if max_order_id is None:
                                max_order_id = 0

                            # Persist combined state: timestamp|order_id
                            write_last_processed_timestamp(last_ts_file, max_ts_str, max_order_id)
                            print(f"[PRODUCER] STATE UPDATED: {max_ts_str}|{max_order_id}")
                    else:
                        print(f"[PRODUCER] SKIPPED state update due to Kafka publish failure")
                else:
                    print(f"[PRODUCER] No new records. Waiting for next poll...")
                    
            except Exception as e:
                print(f"[PRODUCER] ERROR during query execution: {e}")
                print(f"[PRODUCER] Will retry on next poll...")
            
            # STEP 5: Sleep before next poll
            print(f"[PRODUCER] Sleeping for {poll_interval} seconds...")
            time.sleep(poll_interval)
            
    except KeyboardInterrupt:
        print(f"\n[PRODUCER] ========================================")
        print(f"[PRODUCER] RECEIVED SHUTDOWN SIGNAL (Ctrl+C)")
        print(f"[PRODUCER] Total polls executed: {poll_count}")
        print(f"[PRODUCER] Gracefully shutting down...")
        print(f"[PRODUCER] ========================================")
        sys.exit(0)
    except Exception as e:
        print(f"[PRODUCER] FATAL ERROR in polling loop: {e}")
        raise


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """
    Main entry point for CDC Producer application.
    
    Parses command-line arguments:
    --config: Path to YAML configuration file
    
    Initializes Spark and starts CDC polling loop.
    """
    parser = argparse.ArgumentParser(
        description="Food Orders CDC Producer - Reads from PostgreSQL, publishes to Kafka"
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to YAML configuration file (e.g., configs/orders_stream.yml)"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("FOOD DELIVERY - REAL-TIME CDC PRODUCER")
    print("=" * 80)
    
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Initialize Spark Session
        spark = init_spark_session()
        
        # Start CDC polling loop
        run_cdc_polling_loop(spark, config)
        
    except FileNotFoundError as e:
        print(f"[PRODUCER] FATAL: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("[PRODUCER] Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"[PRODUCER] FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()