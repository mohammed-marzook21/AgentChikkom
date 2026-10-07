import sqlite3


conn = sqlite3.connect("data/telecom_ops.db")

credit = conn.execute(
    """
    SELECT
        credit_id,
        customer_id,
        amount,
        status,
        related_charge_id
    FROM billing_credits
    WHERE credit_id = 7
    """
).fetchone()

balance = conn.execute(
    """
    SELECT
        customer_id,
        current_balance
    FROM billing_accounts
    WHERE customer_id = ?
    """,
    ("CUST-10002",),
).fetchone()

conn.close()

print("CREDIT:", credit)
print("BALANCE:", balance)