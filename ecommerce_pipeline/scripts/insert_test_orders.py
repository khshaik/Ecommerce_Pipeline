#!/usr/bin/env python3
# ============================================================================
# HELPER SCRIPT: insert_test_orders.py
# ============================================================================
# Utility script to insert test records into PostgreSQL 2025em1100102_orders table.
#
# PURPOSE:
#   Quickly insert N rows of test data into the 2025em1100102_orders table for testing
#   the CDC pipeline.
#
# USAGE:
#   python3 scripts/insert_test_orders.py \
#       --host localhost \
#       --port 5432 \
#       --database food_delivery_db \
#       --user student \
#       --password student123 \
#       --count 5
#
# TODO TASKS:
#   - [COMPLETED] Connect to PostgreSQL
#   - [COMPLETED] Generate test records
#   - [COMPLETED] Insert with current timestamp
#   - [COMPLETED] Verify insertion count
#
# ============================================================================

import argparse
import sys
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values


def generate_test_records(count=5):
    """
    Generate N test order records.
    
    Each record includes:
    - customer_name: Test Customer {i}
    - restaurant_name: Test Restaurant {i}
    - item: Test Item {i}
    - amount: Random amount between 50 and 500
    - order_status: Random status from {PLACED, PREPARING, DELIVERED, CANCELLED}
    - created_at: Current timestamp (will be set by DB)
    
    Args:
        count (int): Number of records to generate
        
    Returns:
        list: List of tuples (customer_name, restaurant_name, item, amount, order_status)
    """
    import random
    
    statuses = ['PLACED', 'PREPARING', 'DELIVERED', 'CANCELLED']
    records = []
    
    for i in range(count):
        customer = f"Test Customer {i+1}"
        restaurant = f"Test Restaurant {i+1}"
        item = f"Test Item {i+1}"
        amount = round(random.uniform(50, 500), 2)
        status = random.choice(statuses)
        
        records.append((customer, restaurant, item, amount, status))
    
    return records


def insert_test_orders(host, port, database, user, password, count):
    """
    Connect to PostgreSQL and insert test records.
    
    Args:
        host (str): PostgreSQL host
        port (int): PostgreSQL port
        database (str): Database name
        user (str): Database user
        password (str): Database password
        count (int): Number of records to insert
        
    Returns:
        int: Number of records inserted successfully
    """
    print(f"[INSERT] Connecting to PostgreSQL at {host}:{port}/{database}...")
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        cursor = conn.cursor()
        
        print("[INSERT] Connection successful")
        
        # Generate test records
        print(f"[INSERT] Generating {count} test records...")
        records = generate_test_records(count)
        
        # Prepare SQL for batch insert
        # Quote table name because it starts with a number
        sql = """
        INSERT INTO "2025em1100102_orders" (customer_name, restaurant_name, item, amount, order_status, created_at)
        VALUES %s
        RETURNING order_id
        """
        
        # Add current timestamp to each record
        now = datetime.now()
        records_with_ts = [
            (rec[0], rec[1], rec[2], rec[3], rec[4], now)
            for rec in records
        ]
        
        print(f"[INSERT] Inserting {len(records)} records...")
        execute_values(cursor, sql, records_with_ts)
        
        # Get inserted record IDs
        inserted_ids = [row[0] for row in cursor.fetchall()]
        
        # Commit transaction
        conn.commit()
        
        print(f"[INSERT] Successfully inserted {len(inserted_ids)} records")
        print(f"[INSERT] Inserted Order IDs: {inserted_ids}")
        
        # Verify
        cursor.execute('SELECT COUNT(*) FROM "2025em1100102_orders"')
        total_count = cursor.fetchone()[0]
        print(f"[INSERT] Total records in 2025em1100102_orders table: {total_count}")
        
        # Display inserted records
        print("\n[INSERT] Recently inserted records:")
        cursor.execute(
            'SELECT order_id, customer_name, amount, order_status, created_at '
            'FROM "2025em1100102_orders" ORDER BY order_id DESC LIMIT %s',
            (count,)
        )
        
        for row in cursor.fetchall():
            print(f"  Order #{row[0]}: {row[1]} | ${row[2]} | {row[3]} | {row[4]}")
        
        cursor.close()
        conn.close()
        
        return len(inserted_ids)
        
    except Exception as e:
        print(f"[INSERT] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Insert test records into 2025em1100102_orders table"
    )
    parser.add_argument("--host", type=str, default="localhost",
                        help="PostgreSQL host (default: localhost)")
    parser.add_argument("--port", type=int, default=5432,
                        help="PostgreSQL port (default: 5432)")
    parser.add_argument("--database", type=str, default="food_delivery_db",
                        help="Database name (default: food_delivery_db)")
    parser.add_argument("--user", type=str, default="student",
                        help="Database user (default: student)")
    parser.add_argument("--password", type=str, default="student123",
                        help="Database password (default: student123)")
    parser.add_argument("--count", type=int, default=5,
                        help="Number of records to insert (default: 5)")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("TEST DATA INSERTION UTILITY")
    print("=" * 80)
    
    result = insert_test_orders(
        host=args.host,
        port=args.port,
        database=args.database,
        user=args.user,
        password=args.password,
        count=args.count
    )
    
    if result > 0:
        print("\n[INSERT] ✓ Test data inserted successfully")
        sys.exit(0)
    else:
        print("\n[INSERT] ✗ Failed to insert test data")
        sys.exit(1)


if __name__ == "__main__":
    main()
