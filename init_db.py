import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "data" / "telecom_ops.db"
SCHEMA_PATH = BASE_DIR / "sql" / "01_schema.sql"
SEED_PATH = BASE_DIR / "sql" / "02_seed_data.sql"


def initialize_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Database path: {DB_PATH}")

    # Start clean during initial setup.
    if DB_PATH.exists():
        DB_PATH.unlink()
        print("Existing database removed.")

    connection = sqlite3.connect(DB_PATH)

    try:
        cursor = connection.cursor()

        print("\n[1/2] Creating database schema...")

        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
        cursor.executescript(schema_sql)

        print("Schema created successfully.")

        print("\n[2/2] Loading seed data...")

        seed_sql = SEED_PATH.read_text(encoding="utf-8")
        cursor.executescript(seed_sql)

        connection.commit()

        print("Seed data loaded successfully.")

    except Exception as exc:
        connection.rollback()
        print(f"\nDatabase initialization failed: {exc}")
        raise

    finally:
        connection.close()

    print("\nDatabase initialization completed.")
    print(f"Created: {DB_PATH}")


if __name__ == "__main__":
    initialize_database()