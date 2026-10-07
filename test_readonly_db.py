import sqlite3
from pathlib import Path

import pytest


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "telecom_ops.db"


def test_database_rejects_write_in_read_only_mode():
    db_uri = DB_PATH.as_uri() + "?mode=ro"

    conn = sqlite3.connect(db_uri, uri=True)

    try:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute(
                """
                INSERT INTO network_towers (
                    tower_id,
                    tower_name
                )
                VALUES (
                    'TEST-READONLY',
                    'Read Only Test Tower'
                )
                """
            )
    finally:
        conn.close()