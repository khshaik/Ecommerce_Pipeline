# Real-Time Food Delivery Streaming Pipeline

## 📋 Project Overview

This is a **real-time data streaming pipeline** for a food delivery system that captures order events from a PostgreSQL database, streams them through Apache Kafka, and persists them to a data lake using Apache Spark. The system implements **Change Data Capture (CDC)** patterns to incrementally capture new orders and process them in real-time.

### Key Features
- **Real-time CDC**: Incremental polling of PostgreSQL for new orders
- **Kafka Streaming**: Publish-subscribe messaging for order events
- **Spark Structured Streaming**: Continuous processing and validation
- **Data Lake Storage**: Partitioned Parquet files organized by date
- **Docker Containerization**: Complete isolated environment with all services
- **Comprehensive Validation**: Data quality checks and error handling

---

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    REAL-TIME PIPELINE FLOW                      │
└─────────────────────────────────────────────────────────────────┘

PostgreSQL Database          Kafka Message Broker         Data Lake
(Source)                     (Message Queue)              (Sink)
    │                             │                          │
    │  1. CDC Polling             │                          │
    │  (every 5 sec)              │                          │
    │                             │                          │
    ├─────────────────────────────┤                          │
    │ orders_cdc_producer.py      │                          │
    │ - Query new orders          │                          │
    │ - Convert to JSON           │                          │
    │ - Publish to Kafka          │                          │
    │                             │                          │
    │                    2. Stream Processing                │
    │                             │                          │
    │                    ┌────────┴────────┐                 │
    │                    │ Kafka Topic:    │                 │
    │                    │ 2025em1100102_  │                 │
    │                    │ food_orders_raw │                 │
    │                    └────────┬────────┘                 │
    │                             │                          │
    │                             ├──────────────────────────┤
    │                             │ orders_stream_consumer.py│
    │                             │ - Read from Kafka       │
    │                             │ - Parse JSON            │
    │                             │ - Validate data         │
    │                             │ - Add date partition    │
    │                             │ - Write Parquet         │
    │                             │                          │
    │                             │      3. Persist         │
    │                             │                          │
    │                             │      ┌──────────────────┤
    │                             │      │ /datalake/food/  │
    │                             │      │ 2025em1100102/   │
    │                             │      │ output/orders/   │
    │                             │      │ date=YYYY-MM-DD/ │
    │                             │      │ part-*.parquet   │
    │                             │      └──────────────────┘
```

### Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Message Queue** | Apache Kafka | 7.5.0 | Real-time event streaming |
| **Coordination** | Apache Zookeeper | 7.5.0 | Kafka cluster management |
| **Stream Processing** | Apache Spark | 3.4.0 | Distributed data processing |
| **Database** | PostgreSQL | 13 | Source of truth for orders |
| **Storage Format** | Parquet | - | Columnar storage in data lake |
| **Configuration** | YAML | - | Centralized pipeline config |
| **Containerization** | Docker Compose | - | Service orchestration |

---

## 📁 Project Structure

```
2025em1100102/
├── Dockerfile                          # Custom Spark image with dependencies
├── docker-compose.yml                  # Service definitions (Spark, Kafka, Postgres)
├── spark-defaults.conf                 # Spark configuration
│
├── configs/
│   └── orders_stream.yml              # Central configuration file (YAML)
│
├── producers/
│   └── orders_cdc_producer.py          # CDC polling + Kafka publishing
│
├── consumers/
│   └── orders_stream_consumer.py       # Kafka reading + Spark streaming + Parquet writing
│
├── db/
│   └── orders.sql                      # PostgreSQL schema + sample data
│
├── scripts/
│   ├── producer_spark_submit.sh        # Launch producer in Spark cluster
│   ├── consumer_spark_submit.sh        # Launch consumer in Spark cluster
│   ├── insert_test_orders.py           # Insert test data into PostgreSQL
│   ├── test_postgres_connection.py     # Verify PostgreSQL connectivity
│   ├── test_kafka_producer.py          # Test Kafka producer
│   ├── test_kafka_consumer.py          # Test Kafka consumer
│   ├── verify_pipeline.py              # End-to-end pipeline verification
│   ├── read_parquet_records.py         # Read and display Parquet files
│   └── create_parquet_*.py             # Utility scripts for Parquet operations
│
├── setup/
│   └── docker/                         # Docker setup utilities
│
├── logs/                               # Application logs
├── postgres_data/                      # PostgreSQL persistent data volume
└── datalake/                           # Data lake output directory (created at runtime)
```

---

## 🚀 Quick Start Guide

### Prerequisites

- **Docker & Docker Compose** installed
- **Python 3.8+** (for local script execution)
- **4GB+ RAM** available for containers
- **Disk space**: ~2GB for data volumes

### Step 1: Clone/Navigate to Project

```bash
cd /path/to/2025em1100102
```

### Step 2: Start All Services

```bash
docker-compose up -d
```

This starts:
- **Spark Master** (port 9090)
- **Spark Workers** (ports 9091, 9785)
- **PostgreSQL** (port 5432)
- **Kafka** (port 29095)
- **Zookeeper** (port 2888)

### Step 3: Verify Services are Running

```bash
docker-compose ps
```

Expected output:
```
NAME                COMMAND                  SERVICE             STATUS
spark-master        /opt/spark/bin/spark-... spark-master        Up
spark-worker-a      /opt/spark/bin/spark-... spark-worker-a      Up
spark-worker-b      /opt/spark/bin/spark-... spark-worker-b      Up
postgres            docker-entrypoint.s...   postgres            Up
kafka               /etc/confluent/docker... kafka               Up
zookeeper           /etc/confluent/docker... zookeeper           Up
spark-runner        tail -f /dev/null        spark-runner        Up
```

### Step 4: Insert Test Data (Optional)

```bash
docker-compose exec spark-runner python3 scripts/insert_test_orders.py --config configs/orders_stream.yml
```

### Step 5: Start Producer (CDC Polling)

```bash
docker-compose exec spark-runner bash scripts/producer_spark_submit.sh
```

This starts polling PostgreSQL every 5 seconds for new orders.

### Step 6: Start Consumer (Streaming Processing)

In a new terminal:
```bash
docker-compose exec spark-runner bash scripts/consumer_spark_submit.sh
```

This reads from Kafka and writes to Parquet files.

### Step 7: Monitor Pipeline

```bash
docker-compose exec spark-runner python3 scripts/verify_pipeline.py --config configs/orders_stream.yml
```

---

## 🔧 Configuration Guide

### Central Configuration File: `configs/orders_stream.yml`

All pipeline parameters are centralized in this YAML file. Key sections:

#### PostgreSQL Configuration
```yaml
postgres:
  host: postgres                    # Docker service name
  port: 5432
  db: food_delivery_db
  user: student
  password: student123
  driver: org.postgresql.Driver
  table: 2025em1100102_orders       # Source table
```

#### Kafka Configuration
```yaml
kafka:
  brokers: kafka:9095               # Docker service name
  topic: 2025em1100102_food_orders_raw
  num_partitions: 3
  replication_factor: 1
  consumer_group: food_orders_consumer_group
```

#### Streaming Configuration
```yaml
streaming:
  checkpoint_location: /app/datalake/food/2025em1100102/checkpoints/orders
  last_processed_timestamp_location: /app/datalake/food/2025em1100102/lastprocess/orders
  batch_interval: 5                 # seconds

cdc:
  poll_interval_sec: 5              # How often to query PostgreSQL
  batch_limit: 1000                 # Max records per poll
  default_start_timestamp: "2025-11-18 00:00:00"
```

#### Data Lake Configuration
```yaml
datalake:
  path: /app/datalake/food/2025em1100102/output/orders
  format: parquet
```

#### Consumer Configuration
```yaml
consumer:
  maxOffsetsPerTrigger: 1000        # Batch size control
  trigger_interval_ms: 5000         # Process every 5 seconds
  await_termination_timeout: 0      # Run indefinitely
```

#### Data Validation Rules
```yaml
validation:
  allow_null_order_id: false
  allow_negative_amount: false
  drop_invalid_rows: true
```

---

## 📊 Data Flow & Workflow

### End-to-End Processing Flow

#### 1. **CDC Producer Phase** (`orders_cdc_producer.py`)

**Purpose**: Incrementally capture new orders from PostgreSQL

**Process**:
```
┌─────────────────────────────────────────┐
│ POLL LOOP (every 5 seconds)             │
├─────────────────────────────────────────┤
│ 1. Read last_processed_timestamp        │
│    from state file                      │
│                                         │
│ 2. Query PostgreSQL:                    │
│    SELECT * FROM orders                 │
│    WHERE created_at > last_timestamp    │
│    ORDER BY created_at ASC              │
│    LIMIT 1000                           │
│                                         │
│ 3. Convert rows to JSON:                │
│    {"order_id": 1, "customer_name": ..} │
│                                         │
│ 4. Publish to Kafka topic               │
│                                         │
│ 5. Update state file with:              │
│    max(created_at)|max(order_id)        │
│                                         │
│ 6. Sleep 5 seconds                      │
└─────────────────────────────────────────┘
```

**Key Features**:
- **Incremental Processing**: Only fetches records with `created_at > last_timestamp`
- **Tie-breaker Logic**: Uses `order_id` to handle records with same timestamp
- **Atomic State Management**: Updates state only after successful Kafka publish
- **Graceful Shutdown**: Handles Ctrl+C cleanly

**State File Format**:
```
2025-11-18 12:30:45.123456|42
├─ Timestamp with microseconds
└─ Last order_id at that timestamp
```

#### 2. **Kafka Message Queue**

**Topic**: `2025em1100102_food_orders_raw`
- **Partitions**: 3 (for parallelism)
- **Replication Factor**: 1 (single broker)
- **Message Format**: JSON strings

**Example Message**:
```json
{
  "order_id": 1,
  "customer_name": "Alice Smith",
  "restaurant_name": "Spice Garden",
  "item": "Butter Chicken",
  "amount": 350.00,
  "order_status": "DELIVERED",
  "created_at": "2025-11-18T10:00:00Z"
}
```

#### 3. **Spark Structured Streaming Consumer** (`orders_stream_consumer.py`)

**Purpose**: Validate, enrich, and persist streaming data

**Process**:
```
┌──────────────────────────────────────┐
│ STREAMING QUERY (continuous)         │
├──────────────────────────────────────┤
│ 1. Read from Kafka topic             │
│    (startingOffsets: earliest)        │
│                                      │
│ 2. Parse JSON messages               │
│    using predefined schema            │
│                                      │
│ 3. Apply validation rules:           │
│    ✓ order_id NOT NULL               │
│    ✓ amount > 0                      │
│    ✓ customer_name NOT EMPTY         │
│    ✓ restaurant_name NOT EMPTY       │
│    ✓ item NOT EMPTY                  │
│    ✓ order_status NOT EMPTY          │
│                                      │
│ 4. Tag rows: SUCCESS / FAILED        │
│                                      │
│ 5. Filter SUCCESS rows               │
│                                      │
│ 6. Add date partition:               │
│    date = YYYY-MM-DD                 │
│                                      │
│ 7. Write to Parquet:                 │
│    /datalake/.../output/orders/      │
│    date=2025-11-18/part-*.parquet    │
│                                      │
│ 8. Checkpoint offsets                │
│    (for recovery)                    │
│                                      │
│ 9. Trigger every 5 seconds           │
└──────────────────────────────────────┘
```

**Validation Rules**:
| Field | Rule | Action |
|-------|------|--------|
| `order_id` | NOT NULL | Drop if null |
| `amount` | > 0 | Drop if ≤ 0 |
| `customer_name` | NOT EMPTY | Drop if null/empty |
| `restaurant_name` | NOT EMPTY | Drop if null/empty |
| `item` | NOT EMPTY | Drop if null/empty |
| `order_status` | NOT EMPTY | Drop if null/empty |

#### 4. **Data Lake Storage**

**Output Structure**:
```
/datalake/food/2025em1100102/output/orders/
├── date=2025-11-18/
│   ├── part-00000-abc123.parquet
│   ├── part-00001-def456.parquet
│   └── ...
├── date=2025-11-19/
│   ├── part-00000-ghi789.parquet
│   └── ...
└── ...
```

**Checkpoint Directory** (for recovery):
```
/datalake/food/2025em1100102/checkpoints/orders/
├── metadata
├── offsets
└── ...
```

---

## 💾 Database Schema

### PostgreSQL Table: `2025em1100102_orders`

```sql
CREATE TABLE "2025em1100102_orders" (
    order_id SERIAL PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    restaurant_name VARCHAR(255) NOT NULL,
    item VARCHAR(255) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    order_status VARCHAR(50) CHECK (order_status IN ('PLACED', 'PREPARING', 'DELIVERED', 'CANCELLED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Field Descriptions

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `order_id` | SERIAL | PRIMARY KEY | Unique order identifier |
| `customer_name` | VARCHAR(255) | NOT NULL | Name of customer placing order |
| `restaurant_name` | VARCHAR(255) | NOT NULL | Name of restaurant |
| `item` | VARCHAR(255) | NOT NULL | Food item ordered |
| `amount` | NUMERIC(10,2) | NOT NULL | Order amount in currency |
| `order_status` | VARCHAR(50) | CHECK constraint | Status: PLACED, PREPARING, DELIVERED, CANCELLED |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Record creation timestamp |

### Sample Data

10 sample orders are automatically inserted during PostgreSQL initialization:

```
Order #1: Alice Smith | Spice Garden | Butter Chicken | $350.00 | DELIVERED
Order #2: Bob Jones | Burger King | Whopper Meal | $250.50 | DELIVERED
Order #3: Charlie Brown | Pizza Hut | Margherita Pizza | $199.00 | DELIVERED
...
```

---

## 🧪 Testing & Verification

### 1. Test PostgreSQL Connection

```bash
docker-compose exec spark-runner python3 scripts/test_postgres_connection.py
```

**Expected Output**:
```
✓ Connected to PostgreSQL (postgres:5432)
✓ Database: food_delivery_db
✓ Table: 2025em1100102_orders
✓ Record count: 10
```

### 2. Test Kafka Producer

```bash
docker-compose exec spark-runner python3 scripts/test_kafka_producer.py
```

**Expected Output**:
```
✓ Connected to Kafka (kafka:9095)
✓ Published test message to topic: 2025em1100102_food_orders_raw
✓ Message ID: 123
```

### 3. Test Kafka Consumer

```bash
docker-compose exec spark-runner python3 scripts/test_kafka_consumer.py
```

**Expected Output**:
```
✓ Connected to Kafka (kafka:9095)
✓ Subscribed to topic: 2025em1100102_food_orders_raw
✓ Received message: {"order_id": 1, ...}
```

### 4. Verify End-to-End Pipeline

```bash
docker-compose exec spark-runner python3 scripts/verify_pipeline.py --config configs/orders_stream.yml
```

**Expected Output**:
```
========== PostgreSQL Check ==========
✓ Connected to PostgreSQL (postgres:5432)
✓ Table '2025em1100102_orders' contains 10 records
✓ Recent records:
    Order #10: Jack Black | $120.00 | 2025-11-18 12:00:00
    ...

========== Kafka Check ==========
✓ Connected to Kafka (kafka:9095)
✓ Topic '2025em1100102_food_orders_raw' exists
✓ Partitions: 3
✓ Messages in topic: 15

========== Data Lake Check ==========
✓ Parquet files found: /datalake/food/2025em1100102/output/orders/
✓ Date partitions: 2025-11-18, 2025-11-19
✓ Total records in data lake: 15
✓ No duplicates detected

========== Pipeline Status ==========
✓ PIPELINE HEALTHY
```

### 5. Read Parquet Files

```bash
docker-compose exec spark-runner python3 scripts/read_parquet_records.py --config configs/orders_stream.yml
```

**Expected Output**:
```
Reading Parquet files from: /datalake/food/2025em1100102/output/orders/

Total records: 15
Sample records:
  Order #1: Alice Smith | Spice Garden | $350.00 | 2025-11-18
  Order #2: Bob Jones | Burger King | $250.50 | 2025-11-18
  ...
```

---

## 🔍 Monitoring & Debugging

### View Spark Master UI

Open browser: `http://localhost:9090`

Shows:
- Running applications
- Worker status
- Job execution details
- Stage information

### View Spark Worker UIs

- Worker A: `http://localhost:9091`
- Worker B: `http://localhost:9785`

### Check Container Logs

```bash
# Producer logs
docker-compose logs -f spark-runner | grep PRODUCER

# Consumer logs
docker-compose logs -f spark-runner | grep CONSUMER

# PostgreSQL logs
docker-compose logs -f postgres

# Kafka logs
docker-compose logs -f kafka
```

### Monitor Data Lake Growth

```bash
# Check output directory
docker-compose exec spark-runner ls -lh datalake/food/2025em1100102/output/orders/

# Count records in Parquet
docker-compose exec spark-runner python3 scripts/read_parquet_records.py --config configs/orders_stream.yml
```

### Check Last Processed Timestamp

```bash
docker-compose exec spark-runner cat datalake/food/2025em1100102/lastprocess/orders/last_processed_timestamp.txt
```

---

## 🛑 Stopping & Cleanup

### Stop All Services (Keep Data)

```bash
docker-compose stop
```

### Stop and Remove Containers (Keep Volumes)

```bash
docker-compose down
```

### Complete Cleanup (Remove Everything)

```bash
docker-compose down -v
```

⚠️ **Warning**: This removes all data volumes including PostgreSQL data and data lake files.

---

## 🐛 Troubleshooting

### Issue: Producer Not Publishing Messages

**Symptoms**: No messages in Kafka topic

**Solutions**:
1. Check PostgreSQL has data: `docker-compose exec postgres psql -U student -d food_delivery_db -c "SELECT COUNT(*) FROM \"2025em1100102_orders\";"`
2. Check Kafka connectivity: `docker-compose exec spark-runner python3 scripts/test_kafka_producer.py`
3. Check producer logs: `docker-compose logs spark-runner | grep PRODUCER`
4. Verify config file: `cat configs/orders_stream.yml`

### Issue: Consumer Not Writing Parquet Files

**Symptoms**: Data lake directory is empty

**Solutions**:
1. Check Kafka has messages: `docker-compose exec spark-runner python3 scripts/test_kafka_consumer.py`
2. Check consumer logs: `docker-compose logs spark-runner | grep CONSUMER`
3. Verify checkpoint directory exists: `docker-compose exec spark-runner ls -la datalake/food/2025em1100102/checkpoints/`
4. Check Spark worker status: Visit `http://localhost:9091`

### Issue: PostgreSQL Connection Refused

**Symptoms**: `psycopg2.OperationalError: could not connect to server`

**Solutions**:
1. Check PostgreSQL is running: `docker-compose ps postgres`
2. Verify credentials in config: `postgres.user`, `postgres.password`
3. Check port mapping: `docker-compose port postgres 5432`
4. Restart PostgreSQL: `docker-compose restart postgres`

### Issue: Kafka Topic Not Found

**Symptoms**: `Topic does not exist`

**Solutions**:
1. Check topic exists: `docker-compose exec kafka kafka-topics --list --bootstrap-server kafka:9095`
2. Create topic manually: `docker-compose exec kafka kafka-topics --create --topic 2025em1100102_food_orders_raw --partitions 3 --replication-factor 1 --bootstrap-server kafka:9095`
3. Verify docker-compose.yml has topic creation config

### Issue: Out of Memory Errors

**Symptoms**: `java.lang.OutOfMemoryError`

**Solutions**:
1. Increase Spark memory in docker-compose.yml:
   ```yaml
   environment:
     - SPARK_DRIVER_MEMORY=4g
     - SPARK_EXECUTOR_MEMORY=4g
   ```
2. Reduce batch size: `consumer.maxOffsetsPerTrigger: 500`
3. Increase poll interval: `cdc.poll_interval_sec: 10`

---

## 📚 Code Documentation

### Producer: `orders_cdc_producer.py`

**Main Functions**:

| Function | Purpose |
|----------|---------|
| `load_config()` | Load YAML configuration |
| `init_spark_session()` | Initialize Spark with Kafka connector |
| `read_last_processed_timestamp()` | Read state file for incremental processing |
| `write_last_processed_timestamp()` | Persist state after successful publish |
| `build_jdbc_url()` | Build PostgreSQL JDBC connection string |
| `build_cdc_query()` | Build SQL query for new records |
| `convert_dataframe_to_json()` | Convert DataFrame rows to JSON |
| `publish_to_kafka()` | Write JSON to Kafka topic |
| `run_cdc_polling_loop()` | Main polling loop (runs indefinitely) |

**Key Algorithm**:
```python
while True:
    last_ts, last_id = read_last_processed_timestamp()
    df = spark.read.jdbc(
        url, 
        query=f"SELECT * FROM orders WHERE created_at > '{last_ts}' OR (created_at = '{last_ts}' AND order_id > {last_id})"
    )
    if df.count() > 0:
        df_json = convert_dataframe_to_json(df)
        publish_to_kafka(df_json)
        max_ts = df.agg(max("created_at")).collect()[0][0]
        write_last_processed_timestamp(max_ts)
    sleep(poll_interval)
```

### Consumer: `orders_stream_consumer.py`

**Main Functions**:

| Function | Purpose |
|----------|---------|
| `load_config()` | Load YAML configuration |
| `init_spark_session()` | Initialize Spark with Kafka connector |
| `build_schema()` | Define DataFrame schema for orders |
| `build_kafka_consumer_config()` | Build Kafka consumer options |
| `apply_data_validation()` | Tag rows as SUCCESS/FAILED |
| `add_date_partition()` | Extract date from timestamp |
| `setup_streaming_writer()` | Configure Parquet writer |
| `run_streaming_consumer()` | Main streaming query (runs indefinitely) |

**Key Algorithm**:
```python
df_kafka = spark.readStream.format("kafka").options(...).load()
df_json = df_kafka.select(from_json(col("value"), schema).alias("data")).select("data.*")
df_validated = apply_data_validation(df_json)
df_success = df_validated.filter(col("validation_status") == "SUCCESS")
df_partitioned = add_date_partition(df_success)
query = df_partitioned.writeStream.format("parquet").partitionBy("date").start()
query.awaitTermination()
```

---

## 📖 Additional Resources

### Configuration Reference
See `configs/orders_stream.yml` for all available parameters and their descriptions.

### Docker Compose Reference
See `docker-compose.yml` for service definitions, port mappings, and volume configurations.

### Database Schema
See `db/orders.sql` for PostgreSQL table definition and sample data.

### Spark Documentation
- [Spark Structured Streaming](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)
- [Spark SQL Kafka Integration](https://spark.apache.org/docs/latest/structured-streaming-kafka-integration.html)
- [Spark JDBC Data Source](https://spark.apache.org/docs/latest/sql-data-sources-jdbc.html)

### Kafka Documentation
- [Kafka Producer API](https://kafka.apache.org/documentation/#producerconfigs)
- [Kafka Consumer API](https://kafka.apache.org/documentation/#consumerconfigs)
- [Kafka Topics](https://kafka.apache.org/documentation/#topicconfigs)

---

## 👥 For New Developers

### Getting Started Checklist

- [ ] Clone/navigate to project directory
- [ ] Install Docker & Docker Compose
- [ ] Read this README completely
- [ ] Review `configs/orders_stream.yml` to understand configuration
- [ ] Review `db/orders.sql` to understand data schema
- [ ] Start services: `docker-compose up -d`
- [ ] Run verification: `docker-compose exec spark-runner python3 scripts/verify_pipeline.py --config configs/orders_stream.yml`
- [ ] Start producer: `docker-compose exec spark-runner bash scripts/producer_spark_submit.sh`
- [ ] Start consumer: `docker-compose exec spark-runner bash scripts/consumer_spark_submit.sh`
- [ ] Monitor Spark UI: Open `http://localhost:9090`
- [ ] Check data lake: `docker-compose exec spark-runner ls -la datalake/food/2025em1100102/output/orders/`

### Key Files to Understand

1. **Start here**: `configs/orders_stream.yml` - Understand all configuration parameters
2. **Then read**: `producers/orders_cdc_producer.py` - Understand CDC polling logic
3. **Then read**: `consumers/orders_stream_consumer.py` - Understand streaming processing
4. **Reference**: `db/orders.sql` - Understand data schema
5. **Reference**: `docker-compose.yml` - Understand service setup

### Common Tasks

**Insert test data**:
```bash
docker-compose exec spark-runner python3 scripts/insert_test_orders.py --config configs/orders_stream.yml
```

**View recent orders in PostgreSQL**:
```bash
docker-compose exec postgres psql -U student -d food_delivery_db -c "SELECT * FROM \"2025em1100102_orders\" ORDER BY created_at DESC LIMIT 5;"
```

**View Parquet files**:
```bash
docker-compose exec spark-runner python3 scripts/read_parquet_records.py --config configs/orders_stream.yml
```

**Check pipeline health**:
```bash
docker-compose exec spark-runner python3 scripts/verify_pipeline.py --config configs/orders_stream.yml
```

---

## 📝 License & Notes

This is a graded assignment for the Data Stores & Pipelines course.

**Student ID**: 2025em1100102

**Assignment**: Real-Time Food Delivery Streaming Pipeline

---

**Last Updated**: December 31, 2025
