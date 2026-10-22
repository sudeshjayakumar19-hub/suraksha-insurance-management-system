from flask import Blueprint, render_template, request
from database import query, query_scalar

premiums_bp = Blueprint("premiums", __name__)

@premiums_bp.route("/premiums")
def premium_list():
    status_filter = request.args.get("status", "").strip().upper()

    where_clause = ""
    if status_filter and status_filter != "ALL":
        safe_status = status_filter.replace("'", "''")
        where_clause = f"WHERE ps.status = '{safe_status}'"

    sql = f"""
        SELECT ps.schedule_id, ps.installment_number, ps.due_date,
               ps.installment_amount, ps.grace_period_end_date, ps.status AS schedule_status,
               p.policy_id, p.policy_number,
               c.first_name || ' ' || c.last_name AS customer_name,
               pp.payment_id, pp.payment_reference_no, pp.payment_date,
               pp.amount_paid, pp.late_fee_applied, pp.payment_mode, pp.payment_status
        FROM premium_schedule ps
        JOIN policy p ON ps.policy_id = p.policy_id
        JOIN customer c ON p.customer_id = c.customer_id
        LEFT JOIN premium_payment pp ON ps.schedule_id = pp.schedule_id
        {where_clause}
        ORDER BY ps.due_date DESC, ps.installment_number
    """
    schedules = query(sql)

    # Summary metrics
    scheduled_total = query_scalar("SELECT NVL(SUM(installment_amount), 0) FROM premium_schedule", 0.0)
    collected_total = query_scalar("SELECT NVL(SUM(amount_paid), 0) FROM premium_payment", 0.0)
    outstanding_total = query_scalar("SELECT NVL(SUM(installment_amount), 0) FROM premium_schedule WHERE status IN ('PENDING', 'OVERDUE')", 0.0)

    # Status counts
    status_counts = query("""
        SELECT status, COUNT(*) AS count, NVL(SUM(installment_amount), 0) AS total_amount
        FROM premium_schedule
        GROUP BY status
        ORDER BY status
    """)

    return render_template(
        "premiums.html",
        schedules=schedules,
        status_filter=status_filter,
        scheduled_total=scheduled_total,
        collected_total=collected_total,
        outstanding_total=outstanding_total,
        status_counts=status_counts
    )
