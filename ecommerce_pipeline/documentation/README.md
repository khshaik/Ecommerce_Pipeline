1. Run [db/orders.sql](cci:7://file:///Users/81194246/Desktop/Workspace/DS/DSP/2/s3/DSP_GA2_2025em1100102_201207/2025em1100102/db/orders.sql:0:0-0:0) to create table and initial 10 records.
2. Insert 5 new records into `2025em1100102_orders`.
3. Run `scripts/producer_spark_submit.sh` and `scripts/consumer_spark_submit.sh`.
4. Verify 5 new Parquet records under `datalake/food/2025em1100102/output/orders/date=YYYY-MM-DD/`.
5. Insert 5 more records and repeat; confirm counts increase without duplicates.
6. chmod +x scripts/producer_spark_submit.sh scripts/consumer_spark_submit.sh

<rollnumber>/food_delivery_streaming/<s3_or_local>/
├── db/
│   └── orders.sql
├── producers/
│   └── orders_cdc_producer.py
├── consumers/
│   └── orders_stream_consumer.py
├── scripts/
│   ├── producer_spark_submit.sh
│   └── consumer_spark_submit.sh
├── configs/
│   └── orders_stream.yml
└── README.md
