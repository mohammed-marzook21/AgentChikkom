import sqlite3
from pathlib import Path


DB_PATH = Path("data") / "telecom_ops.db"

NETWORK_TABLES = [
    "network_towers",
    "network_outages",
    "tower_performance",
    "open_incidents",
]


conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

for table in NETWORK_TABLES:

    print("\n" + "=" * 70)
    print(f"TABLE: {table}")
    print("=" * 70)

    columns = cursor.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    print("\nCOLUMNS:")
    for column in columns:
        column_name = column[1]
        column_type = column[2]

        print(f"  {column_name:<30} {column_type}")

    count = cursor.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]

    print(f"\nROW COUNT: {count}")

    print("\nSAMPLE ROWS:")

    rows = cursor.execute(
        f"SELECT * FROM {table} LIMIT 3"
    ).fetchall()

    for row in rows:
        print(row)


conn.close()