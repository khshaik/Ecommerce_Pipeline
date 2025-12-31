#!/usr/bin/env python3
# ============================================================================
# UTILITY: read_parquet_records.py
# ============================================================================
# Read and display records from Parquet files in the output records directory
#
# PURPOSE:
#   Load Parquet files from a date partition directory, display record count,
#   schema, and sample records to verify streaming pipeline output.
#
# USAGE:
#   python3 read_parquet_records.py [--path <path>] [--limit <n>]
#   
# EXAMPLES:
#   # Read from current directory (assumed to be inside date=YYYY-MM-DD folder)
#   python3 read_parquet_records.py
#   
#   # Read from specific path with custom limit
#   python3 read_parquet_records.py --path /app/2025em1100102/output/records/date=2025-12-04 --limit 20
#   
#   # Read from host path
#   python3 read_parquet_records.py --path ./output/records/date=2025-12-04
#
# ============================================================================

import sys
import argparse
from pathlib import Path
from datetime import datetime

try:
    from pyspark.sql import SparkSession
except ImportError:
    print("ERROR: PySpark not installed. Install with: pip install pyspark")
    sys.exit(1)


def init_spark():
    """Initialize a minimal Spark session for reading Parquet."""
    spark = (SparkSession.builder
        .appName("ParquetRecordReader")
        .config("spark.driver.memory", "2g")
        .getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def read_parquet_records(spark, parquet_path, limit=10):
    """
    Read Parquet files from a directory and display records.
    
    Args:
        spark (SparkSession): Spark session
        parquet_path (str): Path to Parquet directory
        limit (int): Number of records to display
    """
    path_obj = Path(parquet_path)
    
    # Validate path exists
    if not path_obj.exists():
        print(f"ERROR: Path does not exist: {parquet_path}")
        return False
    
    if not path_obj.is_dir():
        print(f"ERROR: Path is not a directory: {parquet_path}")
        return False
    
    # Check for Parquet files
    parquet_files = list(path_obj.glob("*.parquet"))
    if not parquet_files:
        print(f"WARNING: No Parquet files found in {parquet_path}")
        return False
    
    print("=" * 80)
    print("PARQUET RECORDS READER")
    print("=" * 80)
    print(f"\nReading from: {parquet_path}")
    print(f"Parquet files found: {len(parquet_files)}")
    print()
    
    # Read Parquet files
    try:
        df = spark.read.parquet(str(path_obj))
        
        # Display basic info
        record_count = df.count()
        print(f"[INFO] Total records: {record_count}")
        print()
        
        # Display schema
        print("[SCHEMA]")
        df.printSchema()
        print()
        
        # Display summary statistics
        print("[SUMMARY STATISTICS]")
        numeric_cols = [field.name for field in df.schema.fields 
                       if field.dataType.typeName() in ['double', 'long', 'integer']]
        if numeric_cols:
            df.describe(numeric_cols).show()
        print()
        
        # Display sample records
        print(f"[SAMPLE RECORDS] (showing up to {limit} records)")
        print("-" * 80)
        df.limit(limit).show(truncate=False)
        print()
        
        # Display by order_status if available
        if "order_status" in df.columns:
            print("[RECORDS BY ORDER STATUS]")
            df.groupBy("order_status").count().show()
            print()
        
        # Display by date if available
        if "date" in df.columns:
            print("[RECORDS BY DATE PARTITION]")
            df.groupBy("date").count().show()
            print()
        
        # Display order_id range if available
        if "order_id" in df.columns:
            print("[ORDER ID RANGE]")
            stats_df = df.agg({
                "order_id": "min",
                "order_id": "max",
            }).collect()
            min_id_df = df.agg({"order_id": "min"}).collect()[0][0]
            max_id_df = df.agg({"order_id": "max"}).collect()[0][0]
            print(f"Min Order ID: {min_id_df}")
            print(f"Max Order ID: {max_id_df}")
            print(f"Total unique orders: {df.select('order_id').distinct().count()}")
            print()
        
        print("=" * 80)
        print(f"✓ Successfully read {record_count} records from Parquet")
        print("=" * 80)
        return True
        
    except Exception as e:
        print(f"ERROR reading Parquet: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Read and display records from Parquet files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  # Read from current directory (assumed to be date=YYYY-MM-DD folder)
  python3 read_parquet_records.py
  
  # Read from specific path
  python3 read_parquet_records.py --path /app/2025em1100102/output/records/date=2025-12-04
  
  # Read with custom record limit
  python3 read_parquet_records.py --path ./output/records/date=2025-12-04 --limit 50
        """)
    
    parser.add_argument("--path", 
                       type=str, 
                       default=".",
                       help="Path to Parquet directory (default: current directory)")
    parser.add_argument("--limit", 
                       type=int, 
                       default=10,
                       help="Number of sample records to display (default: 10)")
    
    args = parser.parse_args()
    
    # Resolve path
    parquet_path = Path(args.path).resolve()
    
    # Initialize Spark
    print(f"Initializing Spark Session...")
    spark = init_spark()
    
    # Read and display records
    success = read_parquet_records(spark, str(parquet_path), args.limit)
    
    # Cleanup
    spark.stop()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
