import sqlite3
from pathlib import Path


DB_PATH = Path("data") / "telecom_ops.db"

print(f"Checking database: {DB_PATH}")

if not DB_PATH.exists():
    print("❌ Database does not exist.")
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# --------------------------------------------------
# 1. Check tables
# --------------------------------------------------

tables = cursor.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
    """
).fetchall()

print("\nDATABASE TABLES")
print("-" * 50)

for table in tables:
    print(f"✓ {table[0]}")

print(f"\nTotal tables: {len(tables)}")


# --------------------------------------------------
# 2. Check row counts
# --------------------------------------------------

print("\nROW COUNTS")
print("-" * 50)

for (table_name,) in tables:
    count = cursor.execute(
        f'SELECT COUNT(*) FROM "{table_name}"'
    ).fetchone()[0]

    print(f"{table_name:<25} {count}")


# --------------------------------------------------
# 3. Validate network towers
# --------------------------------------------------

tower_count = cursor.execute(
    "SELECT COUNT(*) FROM network_towers"
).fetchone()[0]

print("\nNETWORK VALIDATION")
print("-" * 50)

print(f"network_towers count: {tower_count}")

if tower_count == 10:
    print("✅ Expected 10 network towers found.")
else:
    print("❌ Expected 10 network towers.")


# --------------------------------------------------
# 4. Inspect billing_charges structure
# --------------------------------------------------

print("\nBILLING_CHARGES COLUMNS")
print("-" * 50)

columns = cursor.execute(
    "PRAGMA table_info(billing_charges)"
).fetchall()

for column in columns:
    print(f"{column[1]:<25} {column[2]}")


# --------------------------------------------------
# 5. Show CUST-10002 billing charges
# --------------------------------------------------

print("\nCUST-10002 BILLING CHARGES")
print("-" * 50)

try:
    charges = cursor.execute(
        """
        SELECT *
        FROM billing_charges
        WHERE customer_id = 'CUST-10002'
        """
    ).fetchall()

    for charge in charges:
        print(charge)

    print(f"\nCharges found: {len(charges)}")

except sqlite3.OperationalError as exc:
    print("Could not query by customer_id directly.")
    print(f"Reason: {exc}")
    print("We'll use the displayed column structure to correct the query.")

conn.close()

print("\n✅ Validation completed.")