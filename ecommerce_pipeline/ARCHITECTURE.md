# Architecture & Design Documentation

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    REAL-TIME STREAMING PIPELINE                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────────┐    │
│  │ PostgreSQL   │      │ Kafka Topic  │      │ Spark Structured │    │
│  │ (Source)     │◄────►│ (Queue)      │◄────►│ Streaming        │    │
│  │              │      │              │      │ (Processing)     │    │
│  └──────────────┘      └──────────────┘      └──────────────────┘    │
│       ▲                       ▲                       │                │
│       │                       │                       │                │
│   CDC Polling            Message Broker          Stream Query         │
│   (every 5s)             (3 partitions)          (every 5s)           │
│                                                      │                │
│                                                      ▼                │
│                                              ┌──────────────────┐    │
│                                              │ Data Lake        │    │
│                                              │ (Parquet Files)  │    │
│                                              │ Partitioned by   │    │
│                                              │ date=YYYY-MM-DD  │    │
│                                              └──────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Interactions

```
┌─────────────────────────────────────────────────────────────────┐
│ PRODUCER PHASE                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  orders_cdc_producer.py                                        │
│  ├─ Load config from YAML                                      │
│  ├─ Initialize Spark Session                                   │
│  └─ Enter polling loop:                                        │
│     ├─ Read last_processed_timestamp from state file           │
│     ├─ Query PostgreSQL for new records                        │
│     │  WHERE created_at > last_timestamp                       │
│     ├─ Convert DataFrame to JSON                               │
│     ├─ Publish to Kafka topic                                  │
│     └─ Update state file with max(created_at)                  │
│                                                                 │
│  State File: /datalake/food/2025em1100102/lastprocess/orders/  │
│  Format: timestamp|order_id                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ JSON Messages
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ MESSAGE QUEUE PHASE                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Kafka Topic: 2025em1100102_food_orders_raw                    │
│  ├─ Partitions: 3                                              │
│  ├─ Replication Factor: 1                                      │
│  ├─ Consumer Group: food_orders_consumer_group                 │
│  └─ Message Format: JSON                                       │
│     {                                                          │
│       "order_id": 1,                                           │
│       "customer_name": "Alice",                                │
│       "restaurant_name": "Spice Garden",                       │
│       "item": "Butter Chicken",                                │
│       "amount": 350.00,                                        │
│       "order_status": "DELIVERED",                             │
│       "created_at": "2025-11-18T10:00:00Z"                     │
│     }                                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Streaming Read
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ CONSUMER PHASE                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  orders_stream_consumer.py                                     │
│  ├─ Load config from YAML                                      │
│  ├─ Initialize Spark Session                                   │
│  ├─ Read from Kafka (streaming)                                │
│  ├─ Parse JSON using schema                                    │
│  ├─ Apply validation rules:                                    │
│  │  ├─ order_id NOT NULL                                       │
│  │  ├─ amount > 0                                              │
│  │  ├─ customer_name NOT EMPTY                                 │
│  │  ├─ restaurant_name NOT EMPTY                               │
│  │  ├─ item NOT EMPTY                                          │
│  │  └─ order_status NOT EMPTY                                  │
│  ├─ Filter SUCCESS rows                                        │
│  ├─ Add date partition (YYYY-MM-DD)                            │
│  ├─ Write to Parquet (partitioned by date)                     │
│  └─ Checkpoint offsets for recovery                            │
│                                                                 │
│  Checkpoint Dir: /datalake/food/2025em1100102/checkpoints/     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Parquet Files
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ DATA LAKE PHASE                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  /datalake/food/2025em1100102/output/orders/                   │
│  ├─ date=2025-11-18/                                           │
│  │  ├─ part-00000-abc123.parquet                               │
│  │  ├─ part-00001-def456.parquet                               │
│  │  └─ ...                                                     │
│  ├─ date=2025-11-19/                                           │
│  │  ├─ part-00000-ghi789.parquet                               │
│  │  └─ ...                                                     │
│  └─ ...                                                        │
│                                                                 │
│  Format: Parquet (columnar, compressed)                        │
│  Partitioning: By date (YYYY-MM-DD)                            │
│  Retention: Indefinite (append-only)                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

### Detailed Message Flow

```
Time: 2025-11-18 10:00:00

┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: New Order Created in PostgreSQL                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INSERT INTO "2025em1100102_orders" VALUES (                   │
│    1, 'Alice Smith', 'Spice Garden', 'Butter Chicken',         │
│    350.00, 'DELIVERED', '2025-11-18 10:00:00'                  │
│  );                                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ (5 second poll interval)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Producer Polls PostgreSQL                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Last processed timestamp: 2025-11-18 09:55:00                 │
│                                                                 │
│  Query:                                                        │
│  SELECT * FROM "2025em1100102_orders"                          │
│  WHERE created_at > '2025-11-18 09:55:00'                      │
│  ORDER BY created_at ASC                                       │
│  LIMIT 1000                                                    │
│                                                                 │
│  Result: 1 new row found                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Convert to JSON                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  {                                                             │
│    "order_id": 1,                                              │
│    "customer_name": "Alice Smith",                             │
│    "restaurant_name": "Spice Garden",                          │
│    "item": "Butter Chicken",                                   │
│    "amount": 350.00,                                           │
│    "order_status": "DELIVERED",                                │
│    "created_at": "2025-11-18 10:00:00"                         │
│  }                                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Publish to Kafka                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Topic: 2025em1100102_food_orders_raw                          │
│  Partition: 0 (round-robin)                                    │
│  Offset: 42                                                    │
│  Message: (JSON string above)                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: Update Producer State                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  File: /datalake/food/2025em1100102/lastprocess/orders/        │
│        last_processed_timestamp.txt                            │
│                                                                 │
│  Content: 2025-11-18 10:00:00.000000|1                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ (Consumer reads continuously)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: Consumer Reads from Kafka                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Kafka Message:                                                │
│  {                                                             │
│    "key": null,                                                │
│    "value": "{\"order_id\":1,...}",                            │
│    "topic": "2025em1100102_food_orders_raw",                   │
│    "partition": 0,                                             │
│    "offset": 42,                                               │
│    "timestamp": 1234567890000,                                 │
│    "timestampType": 0                                          │
│  }                                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 7: Parse JSON                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DataFrame:                                                    │
│  ┌─────────┬──────────────┬─────────────────┬──────────────┐  │
│  │order_id │customer_name │restaurant_name  │item          │  │
│  ├─────────┼──────────────┼─────────────────┼──────────────┤  │
│  │1        │Alice Smith   │Spice Garden     │Butter Chicken│  │
│  └─────────┴──────────────┴─────────────────┴──────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 8: Validate Data                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Validation Rules:                                             │
│  ✓ order_id NOT NULL → PASS                                    │
│  ✓ amount > 0 → PASS (350.00)                                  │
│  ✓ customer_name NOT EMPTY → PASS                              │
│  ✓ restaurant_name NOT EMPTY → PASS                            │
│  ✓ item NOT EMPTY → PASS                                       │
│  ✓ order_status NOT EMPTY → PASS                               │
│                                                                 │
│  Result: validation_status = "SUCCESS"                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 9: Add Date Partition                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Extract from created_at: 2025-11-18 10:00:00                  │
│  Partition column: date = "2025-11-18"                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 10: Write to Parquet                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Output Path:                                                  │
│  /datalake/food/2025em1100102/output/orders/                   │
│  date=2025-11-18/                                              │
│  part-00000-abc123.parquet                                     │
│                                                                 │
│  Checkpoint:                                                   │
│  /datalake/food/2025em1100102/checkpoints/orders/              │
│  offsets/0/42                                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Design Patterns

### 1. Change Data Capture (CDC)

**Pattern**: Incremental polling with timestamp tracking

**Implementation**:
- Producer polls PostgreSQL at fixed intervals
- Tracks last processed timestamp in state file
- Queries only new records: `WHERE created_at > last_timestamp`
- Updates state atomically after successful publish

**Advantages**:
- Simple to implement
- No database triggers required
- Handles late-arriving data
- Recoverable from failures

**Limitations**:
- Not true real-time (polling interval latency)
- Requires timestamp column in source table
- Potential for duplicates if state not updated atomically

### 2. Exactly-Once Semantics

**Pattern**: Idempotent state management

**Implementation**:
- State file contains: `timestamp|order_id`
- Tie-breaker logic handles records with same timestamp
- State updated only after Kafka publish succeeds
- Consumer uses checkpointing for offset tracking

**Guarantees**:
- No data loss (state persisted before continuing)
- No duplicates (tie-breaker prevents re-reading)
- Recoverable from producer/consumer crashes

### 3. Streaming Data Validation

**Pattern**: Tag-based validation (not drop-based)

**Implementation**:
- Add `validation_status` column to each row
- Tag as "SUCCESS" or "FAILED"
- Filter by status downstream
- Enables audit trail of invalid records

**Advantages**:
- Preserves invalid records for debugging
- Enables separate handling of failures
- Audit trail for data quality

### 4. Partitioned Data Lake

**Pattern**: Date-based partitioning

**Implementation**:
- Partition Parquet files by date (YYYY-MM-DD)
- Separate directory per date
- Enables efficient date-range queries
- Supports incremental data loading

**Directory Structure**:
```
/datalake/food/2025em1100102/output/orders/
├── date=2025-11-18/
│   ├── part-00000.parquet
│   ├── part-00001.parquet
│   └── ...
├── date=2025-11-19/
│   └── ...
└── ...
```

## Scalability Considerations

### Horizontal Scaling

**Kafka Partitions**:
- Currently: 3 partitions
- Can increase for higher throughput
- Each partition processed independently
- Enables parallel consumption

**Spark Workers**:
- Currently: 2 workers
- Can add more workers in docker-compose.yml
- Distributes computation across cluster
- Improves processing speed

**PostgreSQL Sharding**:
- Currently: Single database
- Could shard by customer_id or restaurant_id
- Producer would need to query multiple shards
- Increases complexity significantly

### Vertical Scaling

**Memory Allocation**:
```yaml
SPARK_DRIVER_MEMORY=2g      # Currently 1g
SPARK_EXECUTOR_MEMORY=2g    # Currently 1g
SPARK_WORKER_MEMORY=2g      # Currently 1g
```

**Batch Size**:
```yaml
consumer.maxOffsetsPerTrigger: 1000  # Can increase
cdc.batch_limit: 1000                # Can increase
```

## Failure Handling

### Producer Failures

**Scenario**: Producer crashes after querying PostgreSQL but before publishing to Kafka

**Recovery**:
1. State file not updated
2. Next poll reads same records again
3. Kafka deduplicates (same order_id)
4. No data loss

**Scenario**: Producer crashes after publishing but before updating state

**Recovery**:
1. State file not updated
2. Next poll reads same records again
3. Kafka receives duplicates
4. Consumer deduplicates via order_id

### Consumer Failures

**Scenario**: Consumer crashes mid-stream

**Recovery**:
1. Checkpoint directory tracks last offset
2. Next restart reads from last checkpoint
3. No data loss or duplicates
4. Automatic recovery

### Kafka Failures

**Scenario**: Kafka broker goes down

**Recovery**:
1. Producer queues messages in memory (limited)
2. Consumer waits for Kafka to recover
3. Replication factor = 1 (no redundancy)
4. Data loss if broker not recovered

**Mitigation**:
- Increase replication factor to 3 (requires 3 brokers)
- Implement producer retry logic
- Monitor Kafka broker health

## Performance Characteristics

### Latency

| Component | Latency | Notes |
|-----------|---------|-------|
| CDC Poll | 5 seconds | Configurable |
| Kafka Publish | <100ms | Network dependent |
| Consumer Trigger | 5 seconds | Configurable |
| Total End-to-End | ~10 seconds | Sum of above |

### Throughput

| Component | Capacity | Notes |
|-----------|----------|-------|
| PostgreSQL Query | 1000 rows/poll | Configurable batch_limit |
| Kafka Topic | 3 partitions | Can increase |
| Spark Consumer | 1000 offsets/trigger | Configurable |
| Parquet Write | Limited by disk I/O | Depends on hardware |

### Storage

| Component | Size | Notes |
|-----------|------|-------|
| Per Order | ~500 bytes | JSON + Parquet overhead |
| Daily (1000 orders) | ~500 KB | Compressed Parquet |
| Monthly (30K orders) | ~15 MB | Partitioned by date |
| Yearly (365K orders) | ~180 MB | Scalable storage |

## Security Considerations

### Current Implementation

**Database Credentials**:
- Hardcoded in docker-compose.yml
- Hardcoded in configs/orders_stream.yml
- ⚠️ Not suitable for production

**Kafka Security**:
- No authentication (PLAINTEXT)
- No encryption (PLAINTEXT)
- ⚠️ Not suitable for production

**Network Security**:
- All services on Docker bridge network
- Exposed ports for monitoring only
- ⚠️ Not suitable for production

### Production Recommendations

**Database**:
- Use environment variables for credentials
- Implement SSL/TLS for connections
- Use IAM roles instead of passwords
- Rotate credentials regularly

**Kafka**:
- Enable SASL/SSL authentication
- Implement ACLs for topic access
- Use encrypted connections
- Monitor access logs

**Network**:
- Use private networks (VPC)
- Implement network policies
- Use service mesh (Istio)
- Enable audit logging

## Monitoring & Observability

### Current Monitoring

**Spark UI**: http://localhost:9090
- Job execution details
- Stage information
- Task metrics

**Container Logs**: `docker-compose logs`
- Application logs
- Error messages
- Debug output

### Recommended Enhancements

**Metrics Collection**:
- Prometheus for metrics
- Grafana for dashboards
- Custom metrics in code

**Logging**:
- ELK stack (Elasticsearch, Logstash, Kibana)
- Structured logging (JSON format)
- Centralized log aggregation

**Tracing**:
- Jaeger for distributed tracing
- Track requests across services
- Identify bottlenecks

**Alerting**:
- Alert on pipeline failures
- Alert on data quality issues
- Alert on performance degradation
