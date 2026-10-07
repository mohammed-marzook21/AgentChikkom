import sqlite3
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "telecom_ops.db"


def get_db_connection() -> sqlite3.Connection:
    """Open the telecom operational database with billing write access."""

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Telecom database not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def lookup_billing_account(customer_id: str) -> dict[str, Any]:
    """
    Look up a customer's billing account and recent charges.

    Args:
        customer_id: Customer identifier such as CUST-10002.

    Returns:
        Billing account information and recent charges.
    """

    customer_id = customer_id.strip().upper()

    if not customer_id:
        return {
            "status": "error",
            "message": "customer_id cannot be empty",
        }

    conn = get_db_connection()

    try:
        account = conn.execute(
            """
            SELECT
                customer_id,
                customer_name,
                account_type,
                current_balance,
                currency,
                service_region,
                city,
                state,
                billing_cycle,
                auto_pay_enabled,
                account_status,
                last_updated
            FROM billing_accounts
            WHERE customer_id = ?
            """,
            (customer_id,),
        ).fetchone()

        if account is None:
            return {
                "status": "not_found",
                "message": f"Billing account {customer_id} was not found.",
            }

        charges = conn.execute(
            """
            SELECT
                charge_id,
                description,
                amount,
                billing_period,
                charge_date,
                charge_type,
                is_duplicate_flag,
                invoice_status
            FROM billing_charges
            WHERE customer_id = ?
            ORDER BY charge_date DESC, charge_id DESC
            LIMIT 10
            """,
            (customer_id,),
        ).fetchall()

        credits = conn.execute(
            """
            SELECT
                credit_id,
                amount,
                reason,
                status,
                created_at,
                related_charge_id
            FROM billing_credits
            WHERE customer_id = ?
            ORDER BY created_at DESC, credit_id DESC
            LIMIT 10
            """,
            (customer_id,),
        ).fetchall()

        disputes = conn.execute(
            """
            SELECT
                dispute_id,
                charge_id,
                reason,
                status,
                opened_at,
                resolved_at,
                resolution_notes
            FROM billing_disputes
            WHERE customer_id = ?
            ORDER BY opened_at DESC
            LIMIT 10
            """,
            (customer_id,),
        ).fetchall()

        return {
            "status": "success",
            "account": dict(account),
            "recent_charges": [dict(row) for row in charges],
            "recent_credits": [dict(row) for row in credits],
            "recent_disputes": [dict(row) for row in disputes],
        }

    finally:
        conn.close()


def check_duplicate_charges(customer_id: str) -> dict[str, Any]:
    """
    Check a customer's billing history for duplicate charges.

    Duplicate detection uses the operational duplicate flag and also
    identifies matching charges with the same amount, billing period
    and charge type.

    Args:
        customer_id: Customer identifier such as CUST-10002.

    Returns:
        Duplicate charge information for the customer.
    """

    customer_id = customer_id.strip().upper()

    if not customer_id:
        return {
            "status": "error",
            "message": "customer_id cannot be empty",
        }

    conn = get_db_connection()

    try:
        account = conn.execute(
            """
            SELECT customer_id, customer_name
            FROM billing_accounts
            WHERE customer_id = ?
            """,
            (customer_id,),
        ).fetchone()

        if account is None:
            return {
                "status": "not_found",
                "message": f"Billing account {customer_id} was not found.",
            }

        duplicate_charges = conn.execute(
            """
            SELECT
                charge_id,
                description,
                amount,
                billing_period,
                charge_date,
                charge_type,
                is_duplicate_flag,
                invoice_status
            FROM billing_charges
            WHERE customer_id = ?
              AND is_duplicate_flag = 1
            ORDER BY charge_date DESC
            """,
            (customer_id,),
        ).fetchall()

        matching_groups = conn.execute(
            """
            SELECT
                amount,
                billing_period,
                charge_type,
                COUNT(*) AS charge_count,
                GROUP_CONCAT(charge_id) AS charge_ids
            FROM billing_charges
            WHERE customer_id = ?
            GROUP BY amount, billing_period, charge_type
            HAVING COUNT(*) > 1
            ORDER BY billing_period DESC
            """,
            (customer_id,),
        ).fetchall()

        return {
            "status": "success",
            "customer_id": customer_id,
            "customer_name": account["customer_name"],
            "duplicate_found": len(duplicate_charges) > 0,
            "flagged_duplicate_count": len(duplicate_charges),
            "flagged_duplicate_charges": [
                dict(row) for row in duplicate_charges
            ],
            "matching_charge_groups": [
                dict(row) for row in matching_groups
            ],
        }

    finally:
        conn.close()


def apply_billing_credit(
    customer_id: str,
    amount: float,
    reason: str,
    related_charge_id: str = "",
) -> dict[str, Any]:
    """
    Create a billing credit using the project's approval rules.

    Credits of 50 USD or less are automatically APPLIED and reduce
    the customer's current balance.

    Credits above 50 USD are stored as PENDING_APPROVAL and do not
    change the account balance until human approval.

    Args:
        customer_id: Customer identifier such as CUST-10002.
        amount: Positive credit amount in USD.
        reason: Business reason for the credit.
        related_charge_id: Optional charge associated with the credit.

    Returns:
        Credit status and resulting billing information.
    """

    customer_id = customer_id.strip().upper()
    reason = reason.strip()
    related_charge_id = related_charge_id.strip().upper()

    if not customer_id:
        return {
            "status": "error",
            "message": "customer_id cannot be empty",
        }

    if amount <= 0:
        return {
            "status": "error",
            "message": "Credit amount must be greater than zero.",
        }

    if not reason:
        return {
            "status": "error",
            "message": "Credit reason cannot be empty.",
        }

    conn = get_db_connection()

    try:
        account = conn.execute(
            """
            SELECT
                customer_id,
                current_balance,
                currency,
                account_status
            FROM billing_accounts
            WHERE customer_id = ?
            """,
            (customer_id,),
        ).fetchone()

        if account is None:
            return {
                "status": "not_found",
                "message": f"Billing account {customer_id} was not found.",
            }

        if related_charge_id:
            charge = conn.execute(
                """
                SELECT charge_id, customer_id, amount
                FROM billing_charges
                WHERE charge_id = ?
                """,
                (related_charge_id,),
            ).fetchone()

            if charge is None:
                return {
                    "status": "not_found",
                    "message": (
                        f"Related charge {related_charge_id} was not found."
                    ),
                }

            if charge["customer_id"] != customer_id:
                return {
                    "status": "error",
                    "message": (
                        f"Charge {related_charge_id} does not belong "
                        f"to customer {customer_id}."
                    ),
                }

            existing_credit = conn.execute(
                """
                SELECT
                    credit_id,
                    amount,
                    status
                FROM billing_credits
                WHERE customer_id = ?
                  AND related_charge_id = ?
                  AND status IN ('APPLIED', 'PENDING_APPROVAL')
                LIMIT 1
                """,
                (customer_id, related_charge_id),
            ).fetchone()

            if existing_credit is not None:
                return {
                    "status": "already_credited",
                    "message": (
                        f"Charge {related_charge_id} already has an "
                        "active billing credit."
                    ),
                    "existing_credit": dict(existing_credit),
                }

        credit_status = (
            "APPLIED"
            if amount <= 50
            else "PENDING_APPROVAL"
        )

        cursor = conn.execute(
            """
            INSERT INTO billing_credits
            (
                customer_id,
                amount,
                reason,
                status,
                related_charge_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                customer_id,
                amount,
                reason,
                credit_status,
                related_charge_id if related_charge_id else None,
            ),
        )

        credit_id = cursor.lastrowid

        old_balance = float(account["current_balance"])
        new_balance = old_balance

        if credit_status == "APPLIED":
            new_balance = old_balance - float(amount)

            conn.execute(
                """
                UPDATE billing_accounts
                SET
                    current_balance = ?,
                    last_updated = datetime('now')
                WHERE customer_id = ?
                """,
                (new_balance, customer_id),
            )

        conn.commit()

        return {
            "status": "success",
            "credit_id": credit_id,
            "customer_id": customer_id,
            "amount": float(amount),
            "currency": account["currency"],
            "credit_status": credit_status,
            "approval_required": credit_status == "PENDING_APPROVAL",
            "related_charge_id": (
                related_charge_id if related_charge_id else None
            ),
            "previous_balance": old_balance,
            "current_balance": new_balance,
            "message": (
                "Credit applied successfully."
                if credit_status == "APPLIED"
                else "Credit created and is pending human approval."
            ),
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()