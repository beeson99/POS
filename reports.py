"""
X and Z report generation for the POS system.
Handles data aggregation from the database and formats report text
for display and printing.
"""
from datetime import datetime
from psycopg2 import connect

from config import (
    DB_HOST, DB_PORT, DB_NAME, DB_USER, REGISTER_ID,
    DEPARTMENTS,
    BOLDON, BOLDOFF, DOUBLEWIDTHHEIGHT, NORMAL, CENTER,
)
from printer import print_x_report
from database import (
    create_z_report, assign_z_id_to_sales, assign_z_id_to_departments,
)


def _conn():
    return connect(f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER}")


def _get_payment_totals(cur, register_id):
    """Return (cash, check, card) transaction count + total tuples."""
    # Overall totals
    cur.execute("""
        SELECT COUNT(*),
               COALESCE(SUM(subtotal), 0),
               COALESCE(SUM(tax), 0),
               COALESCE(SUM(total), 0)
        FROM sales
        WHERE z_id IS NULL AND COALESCE(voided, 0) = 0
          AND register_id = %s
    """, (register_id,))
    txns, subtotal, tax, total = cur.fetchone()

    # Check payments
    cur.execute("""
        SELECT COUNT(*),
               COALESCE(SUM(subtotal), 0),
               COALESCE(SUM(tax), 0),
               COALESCE(SUM(total), 0)
        FROM sales
        WHERE check_number IS NOT NULL
          AND z_id IS NULL AND COALESCE(voided, 0) = 0
          AND register_id = %s
    """, (register_id,))
    checkTns, checkSubtotal, checkTax, checkTotal = cur.fetchone()

    # Card payments
    cur.execute("""
        SELECT COUNT(*),
               COALESCE(SUM(subtotal), 0),
               COALESCE(SUM(tax), 0),
               COALESCE(SUM(total), 0)
        FROM sales
        WHERE card_last4 IS NOT NULL
          AND z_id IS NULL AND COALESCE(voided, 0) = 0
          AND register_id = %s
    """, (register_id,))
    cardTns, cardSubtotal, cardTax, cardTotal = cur.fetchone()

    # Cash payments
    cur.execute("""
        SELECT COUNT(*),
               COALESCE(SUM(subtotal), 0),
               COALESCE(SUM(tax), 0),
               COALESCE(SUM(total), 0)
        FROM sales
        WHERE card_last4 IS NULL AND check_number IS NULL
          AND z_id IS NULL AND COALESCE(voided, 0) = 0
          AND register_id = %s
    """, (register_id,))
    cashTns, cashSubtotal, cashTax, cashTotal = cur.fetchone()

    return {
        "txns": txns, "subtotal": subtotal, "tax": tax, "total": total,
        "check": (checkTns, checkTotal),
        "card": (cardTns, cardTotal),
        "cash": (cashTns, cashTotal),
    }


def _get_department_totals(cur, register_id, include_quantity=True):
    """Return dict of per-department counts and totals (non-voided)."""
    results = {}
    for dept_code in sorted(DEPARTMENTS.keys()):
        if include_quantity:
            cur.execute("""
                SELECT COUNT(*),
                       COALESCE(SUM(price), 0),
                       COALESCE(SUM(quantity), 0)
                FROM department
                WHERE z_id IS NULL AND voided = 0
                  AND Department = %s AND register_id = %s
            """, (dept_code, register_id))
            count, total, quantity = cur.fetchone()
            results[dept_code] = (count, total, quantity)
        else:
            cur.execute("""
                SELECT COUNT(*), COALESCE(SUM(price), 0)
                FROM department
                WHERE z_id IS NULL AND voided = 0
                  AND Department = %s AND register_id = %s
            """, (dept_code, register_id))
            count, total = cur.fetchone()
            results[dept_code] = (count, total)
    return results


def _get_department_voids(cur, register_id, include_quantity=True):
    """Return dict of per-department void counts and totals."""
    results = {}
    for dept_code in sorted(DEPARTMENTS.keys()):
        if include_quantity:
            cur.execute("""
                SELECT COUNT(*),
                       COALESCE(SUM(price), 0),
                       COALESCE(SUM(quantity), 0)
                FROM department
                WHERE z_id IS NULL AND voided > 0
                  AND Department = %s AND register_id = %s
            """, (dept_code, register_id))
            count, total, quantity = cur.fetchone()
            results[dept_code] = (count, total, quantity)
        else:
            cur.execute("""
                SELECT COUNT(*), COALESCE(SUM(price), 0)
                FROM department
                WHERE z_id IS NULL AND voided > 0
                  AND Department = %s AND register_id = %s
            """, (dept_code, register_id))
            count, total = cur.fetchone()
            results[dept_code] = (count, total)
    return results


def _get_cashier_breakdown(cur, register_id):
    """Return (per_cashier_rows, totals_row)."""
    cur.execute("""
        SELECT COALESCE(SUM(subtotal), 0),
               COALESCE(SUM(tax), 0),
               COALESCE(SUM(total), 0),
               COALESCE(SUM(cash_received), 0),
               COALESCE(SUM(change_given), 0),
               cashier
        FROM sales
        WHERE voided = 0 AND z_id IS NULL
          AND register_id = %s
        GROUP BY cashier
        ORDER BY cashier
    """, (register_id,))
    rows = cur.fetchall()

    cur.execute("""
        SELECT COALESCE(SUM(subtotal), 0),
               COALESCE(SUM(tax), 0),
               COALESCE(SUM(total), 0),
               COALESCE(SUM(cash_received), 0),
               COALESCE(SUM(change_given), 0),
               'totals'
        FROM sales
        WHERE register_id = %s
          AND voided = 0 AND z_id IS NULL
    """, (register_id,))
    totrows = cur.fetchall()

    return rows, totrows


def _format_report(now_str, pay, dept_totals, dept_voids,
                   cashier_rows, totals_rows, include_quantity=False):
    """Build the report text string. Shared by X and Z reports."""
    report = []
    report.append(f"{DOUBLEWIDTHHEIGHT}")
    report.append(f"{CENTER}")
    report.append("X REPORT")
    report.append(f"{NORMAL}")
    report.append(now_str)
    report.append("-" * 42)
    report.append(f"{CENTER}Sales and Taxes Summary{NORMAL}")
    report.append("-" * 42)
    report.append(f"Total Net Sales: ${pay['subtotal']:8.2f}".rjust(42))
    report.append(f"Tax:             ${pay['tax']:8.2f}".rjust(42))
    report.append(f"Total Sales:     ${pay['total']:8.2f}".rjust(42))
    report.append(f"Transactions :    {pay['txns']}".rjust(42))

    # Departments
    report.append("")
    report.append("-" * 42)
    report.append("Departments".center(42))
    report.append("-" * 42)
    report.append(f"{BOLDON}     Department             Count    Amount   {BOLDOFF}")

    dept_count_total = 0
    dept_amount_total = 0
    for dept_code in sorted(DEPARTMENTS.keys()):
        dept_name = DEPARTMENTS[dept_code]
        count, total = dept_totals[dept_code][0], dept_totals[dept_code][1]
        dept_count_total += count
        dept_amount_total += total
        report.append(
            f"{dept_code} ({dept_name:^11}): ({count:4}) ${total:8.2f}".rjust(42)
        )
    report.append(
        f"Department Totals ({dept_count_total:4}) ${dept_amount_total:8.2f}".rjust(42)
    )

    # Voids by department
    report.append("")
    report.append("-" * 42)
    report.append("Voids by Department".center(42))
    report.append("-" * 42)
    report.append(f"{BOLDON}     Department             Count    Amount   {BOLDOFF}")

    void_count_total = 0
    void_amount_total = 0
    for dept_code in sorted(DEPARTMENTS.keys()):
        dept_name = DEPARTMENTS[dept_code]
        vcount, vtotal = dept_voids[dept_code][0], dept_voids[dept_code][1]
        void_count_total += vcount
        void_amount_total += vtotal
        report.append(
            f"{dept_code} ({dept_name:^11}): ({vcount:4}) ${vtotal:8.2f}".rjust(42)
        )
    report.append(
        f"Department Totals ({void_count_total:4}) ${void_amount_total:8.2f}".rjust(42)
    )

    # Cashier breakdown
    report.append("")
    report.append("-" * 42)
    report.append("Breakdown by User".center(42))
    report.append("-" * 42)
    report.append("")
    report.append(f"{BOLDON}Cashier       Subtotal   Tax      Total   {BOLDOFF}".rjust(42))
    for row in cashier_rows:
        subtotal, tax, total, cash_rec, change_given, cashier = row
        report.append(f"{cashier:13} ${subtotal:8.2f} ${tax:8.2f} ${total:8.2f}")
    for row in totals_rows:
        subtotal, tax, total, cash_rec, change_given, cashier = row
        report.append(f"{'  Total':13} ${subtotal:8.2f} ${tax:8.2f} ${total:8.2f}")

    # Payment details
    report.append("")
    report.append("-" * 42)
    report.append("Payment Details".center(42))
    report.append("-" * 42)
    cashTns, cashTotal = pay["cash"]
    cardTns, cardTotal = pay["card"]
    checkTns, checkTotal = pay["check"]
    report.append(f"{'Cash':<15}{cashTns:>5} ${cashTotal:>10.2f}".rjust(42))
    report.append(f"{'Credit':<15}{cardTns:>5} ${cardTotal:>10.2f}".rjust(42))
    report.append(f"{'Checks':<15}{checkTns:>5} ${checkTotal:>10.2f}".rjust(42))
    report.append("")
    report.append("")

    return "\n".join(report)


def x_report():
    """Generate and print an X report. Returns the report text."""
    now = datetime.now()
    formatted_now = now.strftime("%m/%d/%Y %H:%M")

    conn = _conn()
    cur = conn.cursor()

    pay = _get_payment_totals(cur, REGISTER_ID)
    dept_totals = _get_department_totals(cur, REGISTER_ID, include_quantity=True)
    dept_voids = _get_department_voids(cur, REGISTER_ID, include_quantity=True)
    cashier_rows, totals_rows = _get_cashier_breakdown(cur, REGISTER_ID)

    conn.close()

    report_text = _format_report(
        formatted_now, pay, dept_totals, dept_voids,
        cashier_rows, totals_rows,
    )

    try:
        print_x_report(report_text)
    except Exception as e:
        print(f"Printer Error: {e}")

    return report_text


def z_report():
    """Generate and print a Z report, then close out all sales. Returns report text."""
    now = datetime.now()
    formatted_now = now.strftime("%m/%d/%Y %H:%M")

    conn = _conn()
    cur = conn.cursor()

    pay = _get_payment_totals(cur, REGISTER_ID)
    dept_totals = _get_department_totals(cur, REGISTER_ID, include_quantity=False)
    dept_voids = _get_department_voids(cur, REGISTER_ID, include_quantity=False)
    cashier_rows, totals_rows = _get_cashier_breakdown(cur, REGISTER_ID)

    conn.close()

    report_text = _format_report(
        formatted_now, pay, dept_totals, dept_voids,
        cashier_rows, totals_rows,
    )

    # Close out: create z_report record and assign z_id to sales/departments
    z_id = create_z_report(
        pay["txns"], pay["total"], pay["tax"], REGISTER_ID
    )
    assign_z_id_to_sales(z_id, REGISTER_ID)
    assign_z_id_to_departments(z_id, REGISTER_ID)

    try:
        print_x_report(report_text)
    except Exception as e:
        print(f"Printer Error: {e}")

    return report_text
