import shutil
from pathlib import Path

import pytest

from agents.billing_resolution import tools


BASE_DIR = Path(__file__).resolve().parent.parent.parent
REAL_DB = BASE_DIR / "data" / "telecom_ops.db"


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    test_db = tmp_path / "telecom_ops_test.db"
    shutil.copy2(REAL_DB, test_db)

    monkeypatch.setattr(tools, "DB_PATH", test_db)

    return test_db


def test_lookup_billing_account():
    result = tools.lookup_billing_account("CUST-10002")

    assert result["status"] == "success"
    assert result["account"]["customer_id"] == "CUST-10002"
    assert result["account"]["customer_name"] == "Alex Romero"
    assert result["account"]["service_region"] == "Southwest"
    assert result["account"]["account_status"] == "ACTIVE"


def test_check_duplicate_charges():
    result = tools.check_duplicate_charges("CUST-10002")

    assert result["status"] == "success"
    assert result["customer_id"] == "CUST-10002"
    assert result["duplicate_found"] is True
    assert result["flagged_duplicate_count"] == 1

    duplicate = result["flagged_duplicate_charges"][0]

    assert duplicate["charge_id"] == "CHG-50022"
    assert duplicate["amount"] == 65.99
    assert duplicate["billing_period"] == "2026-09"
    assert duplicate["is_duplicate_flag"] == 1


def test_credit_under_50_is_applied_in_isolated_db(isolated_db):
    result = tools.apply_billing_credit(
        "CUST-10002",
        25.00,
        "Automated test credit",
        "CHG-50021",
    )

    assert result["status"] == "success"
    assert result["credit_status"] == "APPLIED"
    assert result["approval_required"] is False
    assert result["amount"] == 25.00
    assert result["related_charge_id"] == "CHG-50021"

    assert result["current_balance"] == pytest.approx(
        result["previous_balance"] - 25.00
    )


def test_credit_over_50_requires_approval(isolated_db):
    result = tools.apply_billing_credit(
        "CUST-10002",
        75.00,
        "Automated test approval credit",
        "CHG-50021",
    )

    assert result["status"] == "success"
    assert result["credit_status"] == "PENDING_APPROVAL"
    assert result["approval_required"] is True
    assert result["amount"] == 75.00

    assert result["current_balance"] == result["previous_balance"]


def test_duplicate_active_credit_is_rejected(isolated_db):
    first = tools.apply_billing_credit(
        "CUST-10002",
        25.00,
        "First isolated test credit",
        "CHG-50021",
    )

    assert first["status"] == "success"
    assert first["credit_status"] == "APPLIED"

    second = tools.apply_billing_credit(
        "CUST-10002",
        25.00,
        "Second isolated test credit",
        "CHG-50021",
    )

    assert second["status"] == "already_credited"
    assert "already has an active billing credit" in second["message"]
