#!/usr/bin/env bash
source de_env/bin/activate
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 \
  consumers/orders_stream_consumer.py \
  --config configs/orders_stream.yml