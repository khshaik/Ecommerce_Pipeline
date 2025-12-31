from kafka import KafkaProducer
import json
import time

# 1. Connect to Kafka
# We use 'kafka:29092' because this script runs INSIDE the docker network
print("Attempting to connect to Kafka at kafka:29092...")
producer = KafkaProducer(
    bootstrap_servers=['kafka:29092'],
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

print("Connected! Sending messages...")

# 2. Send dummy data
topic_name = 'test_topic'

for i in range(1, 11):
    data = {'id': i, 'message': f'Hello Spark, this is message {i}'}
    producer.send(topic_name, value=data)
    print(f"Sent to {topic_name}: {data}")
    time.sleep(1) # Sleep to simulate streaming

# 3. Flush and close
producer.flush()
print("Done sending messages.")