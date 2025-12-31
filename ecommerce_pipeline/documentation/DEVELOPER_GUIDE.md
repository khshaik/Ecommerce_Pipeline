# Developer Guide

## Code Organization

### Producer: `producers/orders_cdc_producer.py`

**Responsibility**: Incremental Change Data Capture from PostgreSQL to Kafka

**Key Sections**:

1. **Configuration Loading** (Lines 53-77)
   - Loads YAML configuration file
   - Validates file existence
   - Returns parsed config dictionary

2. **Spark Initialization** (Lines 84-111)
   - Creates Spark session with Kafka connector
   - Configures memory and optimization
   - Sets log level to WARN

3. **State Management** (Lines 118-191)
   - `read_last_processed_timestamp()`: Reads state file or returns default
   - `write_last_processed_timestamp()`: Atomically writes state
   - Format: `timestamp|order_id` for tie-breaking

4. **JDBC Configuration** (Lines 197-231)
   - `build_jdbc_url()`: Constructs PostgreSQL connection string
   - `build_jdbc_options()`: Builds Spark JDBC options dictionary

5. **CDC Query Building** (Lines 238-280)
   - `build_cdc_query()`: Constructs SQL for new records
   - Uses timestamp + order_id tie-breaker
   - Applies batch limit for memory efficiency

6. **Data Transformation** (Lines 287-307)
   - `convert_dataframe_to_json()`: Converts rows to JSON strings
   - Uses Spark `to_json(struct(*))` function

7. **Kafka Publishing** (Lines 314-350)
   - `publish_to_kafka()`: Writes JSON to Kafka topic
   - Uses Spark DataFrame writer API
   - Returns success/failure status

8. **Main Loop** (Lines 357-471)
   - `run_cdc_polling_loop()`: Infinite polling loop
   - Handles KeyboardInterrupt for graceful shutdown
   - Logs detailed progress information

9. **Entry Point** (Lines 478-527)
   - `main()`: Parses arguments and orchestrates flow
   - Handles exceptions and exits cleanly

**Key Algorithm**:
```python
while True:
    # Read state
    last_ts, last_id = read_last_processed_timestamp(state_file, default_ts)
    
    # Query new records
    query = build_cdc_query(config, last_ts, last_id)
    df = spark.read.jdbc(url, query)
    
    # Process if records found
    if df.count() > 0:
        df_json = convert_dataframe_to_json(df)
        success = publish_to_kafka(df_json, config)
        
        # Update state only if publish succeeded
        if success:
            max_ts = df.agg(max("created_at")).collect()[0][0]
            write_last_processed_timestamp(state_file, max_ts)
    
    sleep(poll_interval)
```

### Consumer: `consumers/orders_stream_consumer.py`

**Responsibility**: Stream processing, validation, and data lake persistence

**Key Sections**:

1. **Configuration Loading** (Lines 58-82)
   - Loads YAML configuration
   - Validates file existence

2. **Spark Initialization** (Lines 89-116)
   - Creates Spark session with Kafka connector
   - Enables schema inference
   - Sets log level to WARN

3. **Schema Definition** (Lines 123-151)
   - `build_schema()`: Defines DataFrame schema
   - Maps to PostgreSQL table structure
   - Specifies nullability for each field

4. **Kafka Configuration** (Lines 158-194)
   - `build_kafka_consumer_config()`: Builds consumer options
   - Sets starting offsets to "earliest"
   - Configures consumer group and batch size

5. **Data Validation** (Lines 201-263)
   - `apply_data_validation()`: Tags rows as SUCCESS/FAILED
   - Implements 7 validation rules
   - Preserves all rows for audit trail

6. **Partition Derivation** (Lines 270-293)
   - `add_date_partition()`: Extracts date from timestamp
   - Creates partition column for Parquet output
   - Format: YYYY-MM-DD

7. **Streaming Writer Setup** (Lines 300-351)
   - `setup_streaming_writer()`: Configures Parquet writer
   - Sets checkpoint location for recovery
   - Configures trigger interval

8. **Streaming Query** (Lines 358-501)
   - `run_streaming_consumer()`: Main streaming pipeline
   - Reads from Kafka, validates, writes to Parquet
   - Handles KeyboardInterrupt for graceful shutdown

9. **Entry Point** (Lines 508-557)
   - `main()`: Parses arguments and orchestrates flow

**Key Algorithm**:
```python
# Read from Kafka
df_kafka = spark.readStream.format("kafka").options(...).load()

# Parse JSON
df_json = df_kafka.select(
    from_json(col("value"), schema).alias("data")
).select("data.*")

# Validate
df_validated = apply_data_validation(df_json, config)

# Filter success
df_success = df_validated.filter(col("validation_status") == "SUCCESS")

# Add partition
df_partitioned = add_date_partition(df_success)

# Write to Parquet
query = df_partitioned.writeStream \
    .format("parquet") \
    .partitionBy("date") \
    .option("checkpointLocation", checkpoint_dir) \
    .start()

query.awaitTermination()
```

## Configuration Management

### YAML Structure

**File**: `configs/orders_stream.yml`

**Sections**:

1. **postgres**: Database connection
   - `host`: PostgreSQL hostname
   - `port`: PostgreSQL port
   - `db`: Database name
   - `user`: Username
   - `password`: Password
   - `driver`: JDBC driver class
   - `table`: Source table name

2. **kafka**: Message broker configuration
   - `brokers`: Bootstrap servers
   - `topic`: Topic name
   - `num_partitions`: Number of partitions
   - `replication_factor`: Replication factor
   - `consumer_group`: Consumer group ID

3. **streaming**: Streaming parameters
   - `checkpoint_location`: Checkpoint directory
   - `last_processed_timestamp_location`: State file directory
   - `batch_interval`: Trigger interval in seconds

4. **cdc**: Change Data Capture settings
   - `poll_interval_sec`: Polling interval
   - `batch_limit`: Max records per poll
   - `default_start_timestamp`: Starting timestamp

5. **datalake**: Data lake configuration
   - `path`: Output directory
   - `format`: Storage format (parquet)

6. **consumer**: Consumer settings
   - `maxOffsetsPerTrigger`: Batch size
   - `trigger_interval_ms`: Trigger interval
   - `await_termination_timeout`: Timeout (0 = infinite)

7. **schema**: Data schema definition
   - Field names and types
   - Used for JSON parsing

8. **validation**: Validation rules
   - `allow_null_order_id`: Allow null order IDs
   - `allow_negative_amount`: Allow negative amounts
   - `drop_invalid_rows`: Drop or keep invalid rows

9. **logging**: Logging configuration
   - `level`: Log level (INFO, DEBUG, WARN, ERROR)
   - `print_samples`: Print sample records
   - `sample_count`: Number of samples to print

## Common Development Tasks

### Adding a New Field to Orders

**Step 1**: Update PostgreSQL schema
```sql
ALTER TABLE "2025em1100102_orders" ADD COLUMN delivery_address VARCHAR(255);
```

**Step 2**: Update YAML schema
```yaml
schema:
  order_id: "bigint"
  customer_name: "string"
  # ... existing fields ...
  delivery_address: "string"  # Add this
```

**Step 3**: Update validation rules (if needed)
```yaml
validation:
  # Add rule for new field if required
```

**Step 4**: Restart producer and consumer
```bash
docker-compose restart spark-runner
```

### Changing Polling Interval

**Edit**: `configs/orders_stream.yml`
```yaml
cdc:
  poll_interval_sec: 10  # Changed from 5
```

**Effect**: Producer will query PostgreSQL every 10 seconds instead of 5

### Increasing Kafka Partitions

**Step 1**: Update docker-compose.yml
```yaml
environment:
  KAFKA_CREATE_TOPICS: "2025em1100102_food_orders_raw:5:1"  # Changed from 3
```

**Step 2**: Recreate Kafka container
```bash
docker-compose down kafka zookeeper
docker-compose up -d kafka zookeeper
```

**Step 3**: Update YAML config
```yaml
kafka:
  num_partitions: 5  # Changed from 3
```

### Adding Custom Validation Rule

**Edit**: `consumers/orders_stream_consumer.py`

In `apply_data_validation()` function:
```python
# Add new rule
print("[CONSUMER] RULE 8: custom_field must be in allowed values")
allowed_values = ['VALUE1', 'VALUE2']
cond = cond & col("custom_field").isin(allowed_values)
```

### Debugging Data Issues

**Check PostgreSQL data**:
```bash
docker-compose exec postgres psql -U student -d food_delivery_db \
  -c "SELECT * FROM \"2025em1100102_orders\" ORDER BY created_at DESC LIMIT 10;"
```

**Check Kafka messages**:
```bash
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server kafka:9095 \
  --topic 2025em1100102_food_orders_raw \
  --from-beginning \
  --max-messages 5
```

**Check Parquet files**:
```bash
docker-compose exec spark-runner python3 scripts/read_parquet_records.py \
  --config configs/orders_stream.yml
```

**Check validation failures**:
```bash
docker-compose logs spark-runner | grep "FAILED validation"
```

## Testing

### Unit Testing

**Test PostgreSQL Connection**:
```bash
docker-compose exec spark-runner python3 scripts/test_postgres_connection.py
```

**Test Kafka Producer**:
```bash
docker-compose exec spark-runner python3 scripts/test_kafka_producer.py
```

**Test Kafka Consumer**:
```bash
docker-compose exec spark-runner python3 scripts/test_kafka_consumer.py
```

### Integration Testing

**End-to-End Verification**:
```bash
docker-compose exec spark-runner python3 scripts/verify_pipeline.py \
  --config configs/orders_stream.yml
```

**Insert Test Data**:
```bash
docker-compose exec spark-runner python3 scripts/insert_test_orders.py \
  --config configs/orders_stream.yml
```

### Manual Testing

**Step 1**: Start producer
```bash
docker-compose exec spark-runner bash scripts/producer_spark_submit.sh
```

**Step 2**: Insert test data (in another terminal)
```bash
docker-compose exec spark-runner python3 scripts/insert_test_orders.py \
  --config configs/orders_stream.yml
```

**Step 3**: Start consumer (in another terminal)
```bash
docker-compose exec spark-runner bash scripts/consumer_spark_submit.sh
```

**Step 4**: Verify data flow
```bash
# Check Kafka messages
docker-compose exec kafka kafka-console-consumer \
  --bootstrap-server kafka:9095 \
  --topic 2025em1100102_food_orders_raw \
  --from-beginning

# Check Parquet files
docker-compose exec spark-runner python3 scripts/read_parquet_records.py \
  --config configs/orders_stream.yml
```

## Performance Optimization

### Reduce Memory Usage

**Decrease batch sizes**:
```yaml
cdc:
  batch_limit: 500  # From 1000

consumer:
  maxOffsetsPerTrigger: 500  # From 1000
```

**Decrease memory allocation**:
```yaml
# In docker-compose.yml
environment:
  - SPARK_DRIVER_MEMORY=1g
  - SPARK_EXECUTOR_MEMORY=1g
```

### Increase Throughput

**Increase batch sizes**:
```yaml
cdc:
  batch_limit: 5000

consumer:
  maxOffsetsPerTrigger: 5000
```

**Decrease polling interval**:
```yaml
cdc:
  poll_interval_sec: 1  # From 5
```

**Increase Kafka partitions**:
```yaml
kafka:
  num_partitions: 10  # From 3
```

### Optimize Parquet Writing

**Enable compression**:
```python
# In orders_stream_consumer.py
writer = (df.writeStream
    .format("parquet")
    .option("compression", "snappy")  # Add this
    .start())
```

**Adjust file size**:
```python
# In orders_stream_consumer.py
writer = (df.writeStream
    .format("parquet")
    .option("maxRecordsPerFile", 10000)  # Add this
    .start())
```

## Debugging Tips

### Enable Debug Logging

**Edit**: `configs/orders_stream.yml`
```yaml
logging:
  level: "DEBUG"  # Changed from INFO
```

### Add Custom Logging

**In producer**:
```python
print(f"[PRODUCER] DEBUG: {variable_name} = {variable_value}")
```

**In consumer**:
```python
print(f"[CONSUMER] DEBUG: {variable_name} = {variable_value}")
```

### Monitor Spark Jobs

**Open Spark UI**: http://localhost:9090

**Check**:
- Running applications
- Job execution time
- Stage details
- Task metrics

### Check Container Resource Usage

```bash
docker stats spark-runner postgres kafka
```

### View Full Logs

```bash
# All logs
docker-compose logs

# Specific service
docker-compose logs spark-runner

# Follow logs
docker-compose logs -f spark-runner

# Last 100 lines
docker-compose logs --tail=100 spark-runner
```

## Common Issues & Solutions

### Issue: Duplicate Records in Data Lake

**Cause**: Producer state not updated after Kafka publish

**Solution**:
1. Check producer logs for publish failures
2. Verify Kafka connectivity
3. Ensure state file is writable
4. Check disk space

### Issue: Missing Records

**Cause**: Consumer not reading all Kafka messages

**Solution**:
1. Check consumer logs for errors
2. Verify Kafka topic has messages
3. Check checkpoint directory
4. Verify consumer group offset

### Issue: Slow Processing

**Cause**: Insufficient resources or large batches

**Solution**:
1. Decrease batch sizes
2. Increase memory allocation
3. Add more Spark workers
4. Increase Kafka partitions

### Issue: Data Quality Issues

**Cause**: Invalid data in source or validation rules too strict

**Solution**:
1. Check validation rules in config
2. Review failed records in consumer logs
3. Validate source data in PostgreSQL
4. Adjust validation rules as needed

## Code Style Guidelines

### Python Style

- Follow PEP 8
- Use descriptive variable names
- Add docstrings to functions
- Use type hints where possible
- Keep functions focused and small

### Logging Style

- Use consistent prefixes: `[PRODUCER]`, `[CONSUMER]`
- Include timestamp in logs
- Use appropriate log levels: INFO, DEBUG, WARN, ERROR
- Log important state changes

### Configuration Style

- Use YAML for configuration
- Document all parameters
- Use sensible defaults
- Validate configuration on load

## Contributing

### Before Making Changes

1. Create a feature branch
2. Make changes in isolated environment
3. Test thoroughly with manual testing
4. Verify with integration tests
5. Update documentation

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Documentation updated
- [ ] No hardcoded values
- [ ] Error handling implemented
- [ ] Logging added
- [ ] Performance acceptable

### Documentation Updates

- Update README.md for user-facing changes
- Update ARCHITECTURE.md for design changes
- Update this guide for developer-facing changes
- Add inline comments for complex logic
