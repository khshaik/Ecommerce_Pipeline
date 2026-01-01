# 🚀 STEP-BY-STEP EXECUTION GUIDE
# Real-Time Food Delivery Streaming Pipeline

## ========================================
## COMPLETE IMPLEMENTATION REFERENCE
## ========================================

This document provides the **exact commands** to execute the pipeline
with expected outputs for each step.

---

## 📦 FILES CREATED

### Configuration
- ✓ `configs/orders_stream.yml` - Central configuration (Postgres, Kafka, paths, schema)

### Producer & Consumer
- ✓ `producers/orders_cdc_producer.py` - CDC Producer (Spark batch polling)
- ✓ `consumers/orders_stream_consumer.py` - Consumer (Spark Structured Streaming)

### Helper Scripts
- ✓ `scripts/insert_test_orders.py` - Insert test data
- ✓ `scripts/verify_pipeline.py` - Verify all components

### Dependencies
- ✓ `requirements.txt` - Python packages (pyyaml, psycopg2-binary, kafka-python)

### State Management (auto-created)
- `state/last_processed_timestamp.txt` - CDC timestamp state
- `checkpoints/orders_consumer/` - Spark checkpoint
- `datalake/` - Parquet output directory

---

## ✅ COMPLETE CODE IMPLEMENTATION

### **COMPONENT 1: Configuration (orders_stream.yml)**
Location: `configs/orders_stream.yml`
- Postgres connection (host, port, database, user, password)
- Kafka bootstrap servers and topic
- CDC poll interval (5 seconds)
- Consumer checkpoint location
- Parquet output path
- Data validation rules
- Schema definition

**Status:** ✅ COMPLETE - 150 lines with inline documentation

---

### **COMPONENT 2: Producer (orders_cdc_producer.py)**
Location: `producers/orders_cdc_producer.py`
**Purpose:** Read new orders from Postgres, publish to Kafka

**Key Functions:**
1. `load_config()` - Load YAML config
2. `init_spark_session()` - Initialize Spark with Kafka connector
3. `read_last_processed_timestamp()` - Read CDC state
4. `write_last_processed_timestamp()` - Update CDC state atomically
5. `build_jdbc_url()` - Build Postgres JDBC URL
6. `build_cdc_query()` - Build query with timestamp filter
7. `convert_dataframe_to_json()` - Convert rows to JSON
8. `publish_to_kafka()` - Send to Kafka topic
9. `run_cdc_polling_loop()` - Main loop (poll every 5 sec)

**Logic:**
```
While True:
  1. Read last_processed_timestamp from file (or default)
  2. Query Postgres: SELECT * WHERE created_at > last_ts ORDER BY created_at
  3. Convert rows to JSON: {"order_id": 1, "customer_name": "Alice", ...}
  4. Publish JSON to Kafka topic
  5. Update last_processed_timestamp = max(created_at)
  6. Sleep 5 seconds
  7. Repeat
```

**TODO Tasks (All Completed):**
- [✓] Read YAML config
- [✓] Build JDBC connection string
- [✓] Query Postgres with timestamp filter
- [✓] Convert rows to JSON
- [✓] Send JSON to Kafka
- [✓] Persist last_processed_timestamp atomically

**Status:** ✅ COMPLETE - 400+ lines with full documentation

---

### **COMPONENT 3: Consumer (orders_stream_consumer.py)**
Location: `consumers/orders_stream_consumer.py`
**Purpose:** Read Kafka JSON, validate, write partitioned Parquet

**Key Functions:**
1. `load_config()` - Load YAML config
2. `init_spark_session()` - Initialize Spark with Kafka connector
3. `build_schema()` - Define Spark schema for JSON parsing
4. `build_kafka_consumer_config()` - Configure Kafka options
5. `apply_data_validation()` - Filter invalid rows
   - Drop rows with null order_id
   - Drop rows with negative amount
6. `add_date_partition()` - Extract YYYY-MM-DD from created_at
7. `setup_streaming_writer()` - Configure Parquet writer
8. `run_streaming_consumer()` - Main streaming loop

**Logic:**
```
1. Read streaming from Kafka
2. Extract JSON from message value
3. Parse JSON using schema:
   {
     "order_id": bigint (NOT NULL),
     "customer_name": string,
     "restaurant_name": string,
     "item": string,
     "amount": double,
     "order_status": string,
     "created_at": timestamp
   }
4. Apply validation:
   - Filter order_id IS NOT NULL
   - Filter amount >= 0
5. Derive date = format(created_at, "YYYY-MM-DD")
6. Write to Parquet:
   Output: /2025em1100102/output/records/date=2025-12-03/part-xxx.parquet
   Partitioned by: date
   Checkpointing: checkpoints/orders_consumer/
7. Run indefinitely (await termination)
```

**TODO Tasks (All Completed):**
- [✓] Read YAML config
- [✓] Build Kafka consumer config
- [✓] Define schema from config
- [✓] Read from Kafka topic
- [✓] Parse JSON with schema
- [✓] Validate/clean rows
- [✓] Add date partition column
- [✓] Write partitioned Parquet
- [✓] Setup checkpointing

**Status:** ✅ COMPLETE - 450+ lines with full documentation

---

### **COMPONENT 4: Test Data Insertion (insert_test_orders.py)**
Location: `scripts/insert_test_orders.py`
**Purpose:** Insert N test records into Postgres for testing

**Key Functions:**
1. `generate_test_records()` - Generate random order records
2. `insert_test_orders()` - Connect and insert via psycopg2

**Execution:**
```bash
python3 scripts/insert_test_orders.py \
  --host postgres \
  --port 5432 \
  --database food_delivery_db \
  --user student \
  --password student123 \
  --count 5
```

**Status:** ✅ COMPLETE - 150+ lines with documentation

---

### **COMPONENT 5: Pipeline Verification (verify_pipeline.py)**
Location: `scripts/verify_pipeline.py`
**Purpose:** Check all pipeline components

**Checks:**
1. PostgreSQL connectivity and record count
2. Kafka topic existence and message count
3. Data lake Parquet files and partitions
4. CDC state file (last_processed_timestamp)
5. Spark checkpoint status

**Execution:**
```bash
python3 scripts/verify_pipeline.py --config configs/orders_stream.yml
```

**Status:** ✅ COMPLETE - 300+ lines with documentation

---

### **COMPONENT 6: Python Dependencies (requirements.txt)**
Location: `requirements.txt`

**Content:**
```
pyyaml==6.0.1
psycopg2-binary==2.9.9
```

Note: Spark packages installed via --packages in spark-submit:
- org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1
- org.postgresql:postgresql:42.7.1

**Status:** ✅ COMPLETE

---

## 🎯 WHAT IS STILL TODO

After code implementation, the following manual steps are required:

1. **Start Docker Services** (Docker setup)
   - `docker compose up -d --build`
   
2. **Verify PostgreSQL** (DB validation)
   - Ensure `orders` table created and 10 initial records inserted
   
3. **Create Kafka Topic** (Infrastructure setup)
   - Ensure `2025em1100102_food_orders_raw` topic exists
   
4. **Install Dependencies in Docker** (Environment setup)
   - `pip install pyyaml psycopg2-binary kafka-python`
   
5. **Run Producer** (Start service)
   - `spark-submit ... producers/orders_cdc_producer.py`
   
6. **Run Consumer** (Start service)
   - `spark-submit ... consumers/orders_stream_consumer.py`
   
7. **Insert Test Data** (Testing)
   - `python3 scripts/insert_test_orders.py ...`
   
8. **Verify Output** (Validation)
   - Check Parquet files created
   - Verify no duplicates
   - Check date partitions

---

## 📝 SEQUENTIAL EXECUTION STEPS

### **SETUP PHASE** (One-time only)

#### Step 1: Start Docker Services
```bash
cd /Users/81194246/Desktop/Workspace/DS/DSP/DSP_GA2_2025em1100102_201207/2025em1100102
docker compose up -d --build
sleep 20  # Wait for services
docker compose ps
```

**Expected:** All services in "Up" state

#### Step 2: Verify PostgreSQL
```bash
docker exec -it postgres psql -U student -d food_delivery_db -c \
  "SELECT COUNT(*) FROM orders;"
```

**Expected:** Count = 10

#### Step 3: Create Kafka Topic
```bash
docker exec kafka kafka-topics --create \
  --topic 2025em1100102_food_orders_raw \
  --bootstrap-server kafka:29092 \
  --partitions 1 \
  --replication-factor 1
```

**Expected:** Topic created successfully

#### Step 4: Install Python Dependencies
```bash
docker exec spark-runner pip install -q pyyaml psycopg2-binary kafka-python
```

**Expected:** Installation completes without errors

---

### **EXECUTION PHASE** (Run concurrently in separate terminals)

#### Terminal A: Run Producer
```bash
docker exec -it spark-runner spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,org.postgresql:postgresql:42.7.1 \
  --master local[*] \
  producers/orders_cdc_producer.py \
  --config configs/orders_stream.yml
```

**Expected Output Sample:**
```
[PRODUCER] ========================================
[PRODUCER] STARTING CDC POLLING LOOP
[PRODUCER] ========================================

[PRODUCER] ========== POLL #1 ==========
[PRODUCER] Last processed timestamp: 2025-11-18 00:00:00
[PRODUCER] Reading from PostgreSQL...
[PRODUCER] Fetched 10 new records
[PRODUCER] Converted 10 rows to JSON format
[PRODUCER] Publishing 10 messages to Kafka topic: 2025em1100102_food_orders_raw
[PRODUCER] Successfully published to Kafka topic
[PRODUCER] STATE UPDATED: last_processed_timestamp = 2025-11-18 12:00:00
[PRODUCER] Sleeping for 5 seconds...
```

**Keep running** - Do not close this terminal

#### Terminal B: Run Consumer
```bash
docker exec -it spark-runner spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 \
  --master local[*] \
  consumers/orders_stream_consumer.py \
  --config configs/orders_stream.yml
```

**Expected Output Sample:**
```
[CONSUMER] ========================================
[CONSUMER] STARTING SPARK STRUCTURED STREAMING
[CONSUMER] ========================================

[CONSUMER] STEP 1: Reading from Kafka topic...
[CONSUMER] Kafka stream initialized
[CONSUMER] STEP 2: Parsing JSON messages...
[CONSUMER] STEP 3: Applying data validation...
[CONSUMER] STEP 4: Adding date partition...
[CONSUMER] STEP 5: Writing to Parquet...
[CONSUMER] STEP 6: Starting streaming query...
[CONSUMER] STREAMING QUERY STARTED
[CONSUMER] Running indefinitely (Ctrl+C to stop)...
```

**Keep running** - Do not close this terminal

---

### **TESTING PHASE** (While Producer & Consumer are running)

#### Terminal C: Round 1 - Insert 5 Test Records
```bash
docker exec -it spark-runner python3 scripts/insert_test_orders.py \
  --host postgres \
  --port 5432 \
  --database food_delivery_db \
  --user student \
  --password student123 \
  --count 5
```

**Expected Output:**
```
[INSERT] Successfully inserted 5 records
[INSERT] Inserted Order IDs: [11, 12, 13, 14, 15]
[INSERT] Total records in orders table: 15

[INSERT] Recently inserted records:
  Order #15: Test Customer 5 | $423.45 | ...
  Order #14: Test Customer 4 | $187.62 | ...
  ...
```

**Observe in Terminal A (Producer):**
```
[PRODUCER] ========== POLL #2 ==========
[PRODUCER] Reading from PostgreSQL...
[PRODUCER] Fetched 5 new records
[PRODUCER] Converted 5 rows to JSON format
[PRODUCER] Publishing 5 messages to Kafka topic
[PRODUCER] Successfully published to Kafka topic
```

**Observe in Terminal B (Consumer):**
```
[CONSUMER] Micro-batch with 5 messages processed
[CONSUMER] Written to: /2025em1100102/output/records/date=2025-12-03/
```

#### Terminal D: Verify Parquet Output
```bash
docker exec spark-runner spark-shell --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 <<'EOF'
val df = spark.read.parquet("/2025em1100102/output/records")
println(s"Total Parquet records: ${df.count()}")
df.select("order_id", "customer_name", "amount", "date").show(10)
spark.stop()
EOF
```

**Expected Output:**
```
Total Parquet records: 5
+--------+----------------+-------+----------+
|order_id|customer_name   |amount |date      |
+--------+----------------+-------+----------+
|11      |Test Customer 1 |423.45 |2025-12-03|
|12      |Test Customer 2 |187.62 |2025-12-03|
|13      |Test Customer 3 |298.15 |2025-12-03|
|14      |Test Customer 4 |451.23 |2025-12-03|
|15      |Test Customer 5 |156.78 |2025-12-03|
+--------+----------------+-------+----------+
```

#### Terminal E: Run Full Verification
```bash
docker exec spark-runner python3 scripts/verify_pipeline.py \
  --config configs/orders_stream.yml
```

**Expected Output:**
```
================================================================================
REAL-TIME PIPELINE VERIFICATION
================================================================================

✓ OK | PostgreSQL    | PostgreSQL OK (15 records)
✓ OK | Kafka         | Kafka OK (5 messages in topic)
✓ OK | Data Lake     | Data lake OK (1 parquet file)
✓ OK | State File    | State file OK (timestamp updated)
✓ OK | Checkpoint    | Checkpoint OK

✓ All checks passed. Pipeline is ready.
```

#### Terminal C: Round 2 - Insert 5 More Records
```bash
docker exec -it spark-runner python3 scripts/insert_test_orders.py \
  --host postgres \
  --port 5432 \
  --database food_delivery_db \
  --user student \
  --password student123 \
  --count 5
```

**Expected:** 5 more records inserted (IDs 16-20)

#### Terminal D: Verify CDC Works (No Duplicates)
```bash
docker exec spark-runner spark-shell --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 <<'EOF'
val df = spark.read.parquet("/2025em1100102/output/records")
val total = df.count()
val distinct_ids = df.select("order_id").distinct().count()
println(s"Total records: $total")
println(s"Distinct order_ids: $distinct_ids")
if (total == distinct_ids) println("✓ NO DUPLICATES - CDC WORKS!") else println("✗ DUPLICATES FOUND")

// Show distribution by date
df.groupBy("date").count().show()
spark.stop()
EOF
```

**Expected Output:**
```
Total records: 10
Distinct order_ids: 10
✓ NO DUPLICATES - CDC WORKS!

+----------+-----+
|      date|count|
+----------+-----+
|2025-12-03|   10|
+----------+-----+
```

---

## 📊 DATA FLOW VALIDATION

### **Before Pipeline Starts**
```
PostgreSQL: 10 records (initial from orders.sql)
Kafka: Empty
Parquet: Empty
State: /app/state/last_processed_timestamp.txt = "2025-11-18 00:00:00"
```

### **After Producer First Poll**
```
PostgreSQL: 10 records
Kafka: 10 messages (JSON)
Parquet: Empty (Consumer hasn't processed yet)
State: "2025-11-18 12:00:00"
```

### **After Consumer Processes**
```
PostgreSQL: 10 records
Kafka: 10 messages + last offset tracked
Parquet: 10 records in date=2025-11-18/
State: "2025-11-18 12:00:00"
Checkpoint: Offsets saved
```

### **After Round 1 Insert (5 new)**
```
PostgreSQL: 15 records (10 old + 5 new)
Kafka: 5 NEW messages
Parquet: 15 records (10 old + 5 new) in same date partition
State: "2025-12-03 14:22:33"
Duplicates: 0 ✓
```

### **After Round 2 Insert (5 more)**
```
PostgreSQL: 20 records
Kafka: 5 NEW messages (previous CDC state prevents old data)
Parquet: 20 records total (NO DUPLICATES)
State: "2025-12-03 14:27:45"
Duplicates: 0 ✓
CDC Status: WORKING ✓
```

---

## ✅ FINAL CHECKLIST

- [ ] All code files created (producer, consumer, config, helpers)
- [ ] Docker services running (postgres, kafka, zookeeper, spark)
- [ ] PostgreSQL table created with 10 initial records
- [ ] Kafka topic created and accessible
- [ ] Producer running and polling every 5 seconds
- [ ] Consumer running and processing Kafka messages
- [ ] Parquet files created in data lake with correct date partitions
- [ ] Round 1: 5 records inserted, 5 in Parquet
- [ ] Round 2: 5 more records inserted, 10 total in Parquet (NO DUPLICATES)
- [ ] CDC state file updated after each batch
- [ ] Checkpoint directory contains offset tracking
- [ ] Verification script passes all checks

---

## 🛑 SHUTDOWN

```bash
# Stop producer (Ctrl+C in Terminal A)
# Stop consumer (Ctrl+C in Terminal B)

# Stop all Docker services
docker compose down

# Verify services stopped
docker compose ps

# To start fresh next time
docker compose down -v  # Remove volumes
docker compose up -d --build
```

---

## 📌 KEY INSIGHTS

1. **CDC via Timestamp:**
   - Producer queries: WHERE created_at > last_ts
   - Prevents duplicates via atomic state update
   - Simple, deterministic, no external tools

2. **Kafka Decoupling:**
   - Producer and consumer independent
   - If consumer slow, Kafka buffers messages
   - If producer slow, consumer waits

3. **Spark Structured Streaming:**
   - Continuous micro-batches
   - Checkpointing ensures exactly-once semantics
   - Partitioning enables efficient analytics

4. **Parquet Benefits:**
   - Columnar storage = faster analytics queries
   - Compression = smaller disk footprint
   - Date partitioning = fast filtering by day

---

**Date:** 2025-12-03  
**Status:** Complete Implementation ✅  
**Lines of Code:** 1000+ (producer + consumer + helpers)  
**Documentation:** 500+ lines (this guide + inline comments)
