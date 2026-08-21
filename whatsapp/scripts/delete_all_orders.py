"""Delete all CONVERTED orders (and related child rows) from kannans.db."""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "kannans.db"


def main() -> None:
    if not DB.exists():
        raise SystemExit(f"DB not found: {DB}")

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    before = {
        "Enquiry": cur.execute("SELECT COUNT(1) FROM Enquiry").fetchone()[0],
        "CONVERTED": cur.execute(
            "SELECT COUNT(1) FROM Enquiry WHERE status = 'CONVERTED'"
        ).fetchone()[0],
        "EnquiryDish": cur.execute("SELECT COUNT(1) FROM EnquiryDish").fetchone()[0],
        "EnquiryPayment": cur.execute("SELECT COUNT(1) FROM EnquiryPayment").fetchone()[0],
    }
    print("before", before)

    order_ids = [
        r[0]
        for r in cur.execute(
            "SELECT id FROM Enquiry WHERE status = 'CONVERTED'"
        ).fetchall()
    ]
    if not order_ids:
        print("No CONVERTED orders to delete")
        conn.close()
        return

    placeholders = ",".join("?" for _ in order_ids)

    # Null out optional FKs that are SET NULL on delete
    for table, col in (
        ("Notification", "enquiryId"),
        ("InvoiceUpload", "enquiryId"),
        ("WorkerAssignment", "enquiryId"),
    ):
        try:
            cur.execute(
                f"UPDATE {table} SET {col} = NULL WHERE {col} IN ({placeholders})",
                order_ids,
            )
        except sqlite3.OperationalError as exc:
            print(f"skip {table}: {exc}")

    cur.execute(
        f"DELETE FROM EnquiryDish WHERE enquiryId IN ({placeholders})",
        order_ids,
    )
    cur.execute(
        f"DELETE FROM EnquiryPayment WHERE enquiryId IN ({placeholders})",
        order_ids,
    )
    cur.execute(
        f"DELETE FROM Enquiry WHERE id IN ({placeholders})",
        order_ids,
    )
    conn.commit()

    after = {
        "Enquiry": cur.execute("SELECT COUNT(1) FROM Enquiry").fetchone()[0],
        "CONVERTED": cur.execute(
            "SELECT COUNT(1) FROM Enquiry WHERE status = 'CONVERTED'"
        ).fetchone()[0],
        "EnquiryDish": cur.execute("SELECT COUNT(1) FROM EnquiryDish").fetchone()[0],
        "EnquiryPayment": cur.execute("SELECT COUNT(1) FROM EnquiryPayment").fetchone()[0],
        "deleted_orders": len(order_ids),
    }
    print("after", after)
    conn.close()


if __name__ == "__main__":
    main()
