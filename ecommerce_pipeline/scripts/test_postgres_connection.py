import psycopg2
import time

# 1. Configuration matching docker-compose
# Note: Host is 'postgres', matching the service name
db_config = {
    "host": "postgres",
    "port": "5432",
    "database": "food_delivery_db",
    "user": "student",
    "password": "student123"
}

print(f"Connecting to Postgres at {db_config['host']}...")

try:
    # 2. Establish Connection
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    print("Connection successful!")

    # 3. Query the table created by orders.sql
    print("Querying 'orders' table...")
    cursor.execute("SELECT order_id, customer_name, amount, created_at FROM orders LIMIT 5;")
    rows = cursor.fetchall()

    print(f"\nFound {len(rows)} rows:")
    print("-" * 50)
    for row in rows:
        print(f"ID: {row[0]} | Name: {row[1]} | Amount: {row[2]} | Time: {row[3]}")
    print("-" * 50)

    # 4. Check if table is empty
    if len(rows) == 0:
        print("WARNING: Table exists but is empty. Did orders.sql run?")
    else:
        print("SUCCESS: Data read successfully.")

    cursor.close()
    conn.close()

except Exception as e:
    print("\n[ERROR] Failed to connect or query Postgres.")
    print(f"Error details: {e}")