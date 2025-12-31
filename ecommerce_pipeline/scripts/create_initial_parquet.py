#!/usr/bin/env python3
"""Create a small sample Parquet file in `output/orders` for testing/appending.

Writes a few rows with the same schema used by the pipeline.
"""
from pathlib import Path
import pandas as pd

OUT_DIR = Path(__file__).resolve().parents[1] / 'output' / 'orders'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / 'part-00000.parquet'

# sample rows
rows = [
    {"order_id": 1, "customer_name": "Sample A", "restaurant_name": "Resto 1", "item": "Pizza", "amount": 10.5, "order_status": "PLACED", "created_at": "2025-12-05 12:00:00.000000"},
    {"order_id": 2, "customer_name": "Sample B", "restaurant_name": "Resto 2", "item": "Sushi", "amount": 20.75, "order_status": "DELIVERED", "created_at": "2025-12-05 12:01:00.000000"}
]

df = pd.DataFrame(rows)
# write parquet with pyarrow engine
df.to_parquet(OUT_FILE, engine='pyarrow', index=False)

print(f"Wrote sample Parquet to: {OUT_FILE}")
