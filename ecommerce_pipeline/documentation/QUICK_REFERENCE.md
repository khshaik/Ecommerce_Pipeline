# Quick Reference Guide

## Essential Commands

### Start Everything
```bash
docker-compose up -d
```

### Stop Everything
```bash
docker-compose down
```

### Check Status
```bash
docker-compose ps
```

### View Logs
```bash
docker-compose logs -f spark-runner
```

---

## Running the Pipeline

### Terminal 1: Start Producer (CDC Polling)
```bash
docker-compose exec spark-runner bash scripts/producer_spark_submit.sh
```

### Terminal 2: Start Consumer (Streaming)
```bash
docker-compose exec spark-runner bash scripts/consumer_spark_submit.sh
```

### Terminal 3: Insert Test Data
```bash
docker-compose exec spark-runner python3 scripts/insert_test_orders.py --config configs/orders_stream.yml
```

### Terminal 4: Monitor Pipeline
```bash
docker-compose exec spark-runner python3 scripts/verify_pipeline.py --config configs/orders_stream.yml
```

---

## Monitoring URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Spark Master | http://localhost:9090 | Monitor jobs & workers |
| Spark Worker A | http://localhost:9091 | Worker A details |
| Spark Worker B | http://localhost:9785 | Worker B details |

---

## Key Files

| File | Purpose |
|------|---------|
| `README.md` | **START HERE** - Complete project overview |
| `SETUP.md` | Installation & configuration |
| `ARCHITECTURE.md` | System design & data flow |
| `DEVELOPER_GUIDE.md` | Code structure & development |
| `configs/orders_stream.yml` | Central configuration |
| `producers/orders_cdc_producer.py` | CDC polling logic |
| `consumers/orders_stream_consumer.py` | Stream processing logic |
| `db/orders.sql` | Database schema |
| `docker-compose.yml` | Service definitions |

---

## Database Access

### Connect to PostgreSQL
```bash
docker-compose exec postgres psql -U student -d food_delivery_db
```

### View Orders Table
```bash
docker-compose exec postgres psql -U student -d food_delivery_db \
  -c "SELECT * FROM \"2025em1100102_orders\" LIMIT 10;"
```

### Count Records
```bash
docker-compose exec postgres psql -U student -d food_delivery_db \
  -c "SELECT COUNT(*) FROM \"2025em1100102_orders\";"
```

---

## Kafka Commands

### List Topics
```bash
docker-compose exec kafka kafka-topics --list --bootstrap-server kafka:9095
```

### View Topic Details
```bash
docker-compose exec kafka kafka-topics --describe \
  --topic 2025em1100102_food_orders_raw \
  --bootstrap-server kafka:9095
```

### Read Messages
```bash
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server kafka:9095 \
  --topic 2025em1100102_food_orders_raw \
  --from-beginning \
  --max-messages 10
```

### Check Consumer Group
```bash
docker-compose exec kafka kafka-consumer-groups \
  --bootstrap-server kafka:9095 \
  --list
```

---

## Data Lake Access

### List Output Files
```bash
docker-compose exec spark-runner ls -lh datalake/food/2025em1100102/output/orders/
```

### View Parquet Files
```bash
docker-compose exec spark-runner python3 scripts/read_parquet_records.py \
  --config configs/orders_stream.yml
```

### Check Last Processed Timestamp
```bash
docker-compose exec spark-runner cat datalake/food/2025em1100102/lastprocess/orders/last_processed_timestamp.txt
```

---

## Testing Commands

### Test PostgreSQL
```bash
docker-compose exec spark-runner python3 scripts/test_postgres_connection.py
```

### Test Kafka Producer
```bash
docker-compose exec spark-runner python3 scripts/test_kafka_producer.py
```

### Test Kafka Consumer
```bash
docker-compose exec spark-runner python3 scripts/test_kafka_consumer.py
```

### Full Pipeline Verification
```bash
docker-compose exec spark-runner python3 scripts/verify_pipeline.py \
  --config configs/orders_stream.yml
```

---

## Configuration Quick Reference

### File: `configs/orders_stream.yml`

**PostgreSQL**:
```yaml
postgres:
  host: postgres
  port: 5432
  db: food_delivery_db
  user: student
  password: student123
  table: 2025em1100102_orders
```

**Kafka**:
```yaml
kafka:
  brokers: kafka:9095
  topic: 2025em1100102_food_orders_raw
  num_partitions: 3
  consumer_group: food_orders_consumer_group
```

**CDC Settings**:
```yaml
cdc:
  poll_interval_sec: 5        # How often to query PostgreSQL
  batch_limit: 1000           # Max records per poll
  default_start_timestamp: "2025-11-18 00:00:00"
```

**Consumer Settings**:
```yaml
consumer:
  maxOffsetsPerTrigger: 1000  # Batch size
  trigger_interval_ms: 5000   # Process every 5 seconds
  await_termination_timeout: 0 # Run indefinitely
```

---

## Data Schema

### PostgreSQL Table: `2025em1100102_orders`

| Column | Type | Constraints |
|--------|------|-------------|
| `order_id` | SERIAL | PRIMARY KEY |
| `customer_name` | VARCHAR(255) | NOT NULL |
| `restaurant_name` | VARCHAR(255) | NOT NULL |
| `item` | VARCHAR(255) | NOT NULL |
| `amount` | NUMERIC(10,2) | NOT NULL |
| `order_status` | VARCHAR(50) | CHECK (PLACED, PREPARING, DELIVERED, CANCELLED) |
| `created_at` | TIMESTAMP | DEFAULT NOW() |

---

## Validation Rules

Records are validated against these rules:

| Rule | Field | Condition |
|------|-------|-----------|
| 1 | `order_id` | NOT NULL |
| 2 | `amount` | > 0 |
| 3 | `customer_name` | NOT EMPTY |
| 4 | `restaurant_name` | NOT EMPTY |
| 5 | `item` | NOT EMPTY |
| 6 | `order_status` | NOT EMPTY |
| 7 | `amount` | NOT NULL |

---

## Troubleshooting Quick Fixes

### Producer Not Publishing
```bash
# Check logs
docker-compose logs spark-runner | grep PRODUCER

# Verify PostgreSQL has data
docker-compose exec postgres psql -U student -d food_delivery_db \
  -c "SELECT COUNT(*) FROM \"2025em1100102_orders\";"

# Test Kafka
docker-compose exec spark-runner python3 scripts/test_kafka_producer.py
```

### Consumer Not Writing Parquet
```bash
# Check logs
docker-compose logs spark-runner | grep CONSUMER

# Verify Kafka has messages
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server kafka:9095 \
  --topic 2025em1100102_food_orders_raw \
  --from-beginning \
  --max-messages 1

# Check output directory
docker-compose exec spark-runner ls -la datalake/food/2025em1100102/output/orders/
```

### PostgreSQL Connection Failed
```bash
# Check if running
docker-compose ps postgres

# Restart
docker-compose restart postgres

# Test connection
docker-compose exec spark-runner python3 scripts/test_postgres_connection.py
```

### Kafka Not Working
```bash
# Check if running
docker-compose ps kafka zookeeper

# Restart
docker-compose restart kafka zookeeper

# Test connection
docker-compose exec spark-runner python3 scripts/test_kafka_producer.py
```

---

## Performance Tuning

### Increase Throughput
```yaml
# In configs/orders_stream.yml
cdc:
  poll_interval_sec: 1        # Faster polling
  batch_limit: 5000           # Larger batches

consumer:
  maxOffsetsPerTrigger: 5000  # Larger batches
  trigger_interval_ms: 1000   # More frequent processing

kafka:
  num_partitions: 10          # More parallelism
```

### Reduce Memory Usage
```yaml
# In configs/orders_stream.yml
cdc:
  batch_limit: 500            # Smaller batches

consumer:
  maxOffsetsPerTrigger: 500   # Smaller batches
```

### Increase Memory Allocation
```yaml
# In docker-compose.yml
environment:
  - SPARK_DRIVER_MEMORY=4g
  - SPARK_EXECUTOR_MEMORY=4g
  - SPARK_WORKER_MEMORY=4g
```

---

## Directory Structure

```
2025em1100102/
├── README.md                 # Start here!
├── SETUP.md                  # Installation guide
├── ARCHITECTURE.md           # System design
├── DEVELOPER_GUIDE.md        # Code documentation
├── QUICK_REFERENCE.md        # This file
│
├── configs/
│   └── orders_stream.yml     # Configuration
│
├── producers/
│   └── orders_cdc_producer.py
│
├── consumers/
│   └── orders_stream_consumer.py
│
├── scripts/
│   ├── producer_spark_submit.sh
│   ├── consumer_spark_submit.sh
│   ├── insert_test_orders.py
│   ├── test_postgres_connection.py
│   ├── test_kafka_producer.py
│   ├── test_kafka_consumer.py
│   ├── verify_pipeline.py
│   └── read_parquet_records.py
│
├── db/
│   └── orders.sql
│
├── docker-compose.yml
├── Dockerfile
└── spark-defaults.conf
```

---

## Common Workflows

### Workflow 1: Full Pipeline Test

```bash
# Terminal 1: Start services
docker-compose up -d

# Terminal 2: Start producer
docker-compose exec spark-runner bash scripts/producer_spark_submit.sh

# Terminal 3: Start consumer
docker-compose exec spark-runner bash scripts/consumer_spark_submit.sh

# Terminal 4: Insert test data
docker-compose exec spark-runner python3 scripts/insert_test_orders.py \
  --config configs/orders_stream.yml

# Terminal 5: Monitor
docker-compose exec spark-runner python3 scripts/verify_pipeline.py \
  --config configs/orders_stream.yml
```

### Workflow 2: Debug Data Issues

```bash
# Check source data
docker-compose exec postgres psql -U student -d food_delivery_db \
  -c "SELECT * FROM \"2025em1100102_orders\" ORDER BY created_at DESC LIMIT 5;"

# Check Kafka messages
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server kafka:9095 \
  --topic 2025em1100102_food_orders_raw \
  --from-beginning \
  --max-messages 5

# Check output data
docker-compose exec spark-runner python3 scripts/read_parquet_records.py \
  --config configs/orders_stream.yml

# Check validation failures
docker-compose logs spark-runner | grep "FAILED validation"
```

### Workflow 3: Performance Testing

```bash
# Update config for higher throughput
# Edit configs/orders_stream.yml:
# - cdc.poll_interval_sec: 1
# - cdc.batch_limit: 5000
# - consumer.maxOffsetsPerTrigger: 5000

# Restart services
docker-compose restart spark-runner

# Monitor Spark UI
# Open http://localhost:9090

# Insert large dataset
docker-compose exec spark-runner python3 scripts/insert_test_orders.py \
  --config configs/orders_stream.yml

# Check throughput
docker-compose exec spark-runner python3 scripts/verify_pipeline.py \
  --config configs/orders_stream.yml
```

---

## Important Notes

⚠️ **Before Production**:
- [ ] Change default PostgreSQL password
- [ ] Enable Kafka authentication (SASL/SSL)
- [ ] Use environment variables for credentials
- [ ] Enable SSL/TLS for all connections
- [ ] Implement monitoring and alerting
- [ ] Set up backup strategy
- [ ] Configure high availability (HA)

⚠️ **Data Retention**:
- PostgreSQL: Persisted in `./postgres_data`
- Data Lake: Persisted in `./datalake`
- Kafka: Configured for 7 days retention
- Checkpoints: Persisted for recovery

⚠️ **Cleanup**:
```bash
# Stop services (keep data)
docker-compose stop

# Remove containers (keep volumes)
docker-compose down

# Complete cleanup (remove everything)
docker-compose down -v
```

---

## Support Resources

- **README.md**: Complete project overview and features
- **SETUP.md**: Installation and configuration details
- **ARCHITECTURE.md**: System design and data flow
- **DEVELOPER_GUIDE.md**: Code structure and development
- **Spark Documentation**: https://spark.apache.org/docs/latest/
- **Kafka Documentation**: https://kafka.apache.org/documentation/
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/

---

## Version Info

- **Spark**: 3.4.0
- **Kafka**: 7.5.0
- **PostgreSQL**: 13
- **Python**: 3.8+
- **Docker Compose**: 2.0+

---

**Last Updated**: December 31, 2025
