from flask import Blueprint, render_template, request, abort
from database import query, query_one

policies_bp = Blueprint("policies", __name__)

@policies_bp.route("/policies")
def policy_list():
    search = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()

    where_clauses = []
    if search:
        search_safe = search.replace("'", "''")
        where_clauses.append(f"""
            (UPPER(p.policy_number) LIKE UPPER('%{search_safe}%')
             OR UPPER(c.first_name) LIKE UPPER('%{search_safe}%')
             OR UPPER(c.last_name) LIKE UPPER('%{search_safe}%')
             OR UPPER(pp.plan_name) LIKE UPPER('%{search_safe}%'))
        """)
    if status_filter:
        status_safe = status_filter.replace("'", "''")
        where_clauses.append(f"p.policy_status = '{status_safe}'")

    where_str = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    sql = f"""
        SELECT p.policy_id, p.policy_number,
               c.customer_id, c.customer_code, c.first_name || ' ' || c.last_name AS customer_name,
               a.agent_code, a.first_name || ' ' || a.last_name AS agent_name,
               pp.plan_name, pp.policy_type,
               p.start_date, p.end_date, p.sum_assured, p.premium_amount,
               p.payment_frequency, p.policy_status
        FROM policy p
        JOIN customer c ON p.customer_id = c.customer_id
        JOIN agent a ON p.agent_id = a.agent_id
        JOIN policy_plan pp ON p.plan_id = pp.plan_id
        {where_str}
        ORDER BY p.policy_id
    """
    policies = query(sql)
    return render_template("policies.html", policies=policies, search=search, status_filter=status_filter)

@policies_bp.route("/policies/<policy_id>")
def policy_detail(policy_id):
    pid_clean = policy_id.replace("'", "''")
    if pid_clean.isdigit():
        pol_where = f"p.policy_id = {pid_clean}"
    else:
        pol_where = f"UPPER(p.policy_number) = UPPER('{pid_clean}')"

    sql = f"""
        SELECT p.*,
               c.customer_code, c.first_name AS cust_first, c.last_name AS cust_last,
               c.email AS cust_email, c.phone_number AS cust_phone, c.city AS cust_city,
               pp.plan_code, pp.plan_name, pp.policy_type, pp.base_premium_rate, pp.min_sum_assured,
               a.agent_code, a.first_name AS ag_first, a.last_name AS ag_last,
               a.license_number, a.commission_rate,
               b.branch_code, b.branch_name, b.city AS branch_city
        FROM policy p
        JOIN customer c ON p.customer_id = c.customer_id
        JOIN policy_plan pp ON p.plan_id = pp.plan_id
        JOIN agent a ON p.agent_id = a.agent_id
        JOIN branch b ON a.branch_id = b.branch_id
        WHERE {pol_where}
    """
    policy = query_one(sql)
    if not policy:
        abort(404, description="Policy not found")

    real_pid = policy.get("policy_id")
    sum_assured_val = float(policy.get("sum_assured", 0))

    # Beneficiaries
    beneficiaries = query(f"""
        SELECT pb.policy_beneficiary_id, b.beneficiary_id,
               b.first_name || ' ' || b.last_name AS beneficiary_name,
               pb.relationship_to_insured, pb.allocation_percentage,
               pb.is_primary, pb.designated_date,
               b.contact_number, b.email, b.national_id
        FROM policy_beneficiary pb
        JOIN beneficiary b ON pb.beneficiary_id = b.beneficiary_id
        WHERE pb.policy_id = {real_pid}
        ORDER BY pb.is_primary DESC
    """)
    for b in beneficiaries:
        pct = float(b.get("allocation_percentage", 0))
        b["calculated_amount"] = (sum_assured_val * pct / 100.0)

    # Renewals
    renewals = query(f"""
        SELECT renewal_id, renewal_number, renewal_request_date,
               effective_from, effective_to, renewed_premium_amount,
               renewal_status, remarks
        FROM policy_renewal
        WHERE policy_id = {real_pid}
        ORDER BY renewal_number
    """)

    # Premium Schedules and Payments
    schedules = query(f"""
        SELECT ps.schedule_id, ps.installment_number, ps.due_date,
               ps.installment_amount, ps.grace_period_end_date, ps.status AS schedule_status,
               pp.payment_id, pp.payment_reference_no, pp.payment_date,
               pp.amount_paid, pp.late_fee_applied, pp.payment_mode, pp.payment_status
        FROM premium_schedule ps
        LEFT JOIN premium_payment pp ON ps.schedule_id = pp.schedule_id
        WHERE ps.policy_id = {real_pid}
        ORDER BY ps.installment_number
    """)

    # Claims
    claims = query(f"""
        SELECT cl.claim_id, cl.claim_number, cl.incident_date, cl.filing_date,
               cl.claimed_amount, cl.claim_status,
               ca.assessor_name, ca.recommended_amount,
               cs.settlement_number, cs.net_paid_amount, cs.settlement_decision
        FROM claim cl
        LEFT JOIN claim_assessment ca ON cl.claim_id = ca.claim_id
        LEFT JOIN claim_settlement cs ON cl.claim_id = cs.claim_id
        WHERE cl.policy_id = {real_pid}
        ORDER BY cl.filing_date DESC
    """)

    return render_template(
        "policy_detail.html",
        policy=policy,
        beneficiaries=beneficiaries,
        renewals=renewals,
        schedules=schedules,
        claims=claims
    )
