from flask import Blueprint, render_template, request, abort
from database import query, query_one

claims_bp = Blueprint("claims", __name__)

@claims_bp.route("/claims")
def claim_list():
    status_filter = request.args.get("status", "").strip().upper()
    where_clause = ""
    if status_filter and status_filter != "ALL":
        safe_status = status_filter.replace("'", "''")
        where_clause = f"WHERE cl.claim_status = '{safe_status}'"

    sql = f"""
        SELECT cl.claim_id, cl.claim_number, cl.incident_date, cl.filing_date,
               cl.claimed_amount, cl.claim_status,
               p.policy_id, p.policy_number,
               c.customer_id, c.first_name || ' ' || c.last_name AS customer_name,
               ca.assessor_name, ca.recommended_amount,
               cs.settlement_number, cs.net_paid_amount, cs.settlement_decision
        FROM claim cl
        JOIN policy p ON cl.policy_id = p.policy_id
        JOIN customer c ON p.customer_id = c.customer_id
        LEFT JOIN claim_assessment ca ON cl.claim_id = ca.claim_id
        LEFT JOIN claim_settlement cs ON cl.claim_id = cs.claim_id
        {where_clause}
        ORDER BY cl.claim_id
    """
    claims = query(sql)

    # Status distribution
    status_summary = query("""
        SELECT claim_status, COUNT(*) AS count, NVL(SUM(claimed_amount), 0) AS total_claimed
        FROM claim
        GROUP BY claim_status
        ORDER BY count DESC
    """)

    return render_template(
        "claims.html",
        claims=claims,
        status_filter=status_filter,
        status_summary=status_summary
    )

@claims_bp.route("/claims/<claim_id>")
def claim_detail(claim_id):
    cid_clean = claim_id.replace("'", "''")
    if cid_clean.isdigit():
        c_where = f"cl.claim_id = {cid_clean}"
    else:
        c_where = f"UPPER(cl.claim_number) = UPPER('{cid_clean}')"

    # Core claim with policy and customer
    sql = f"""
        SELECT cl.*,
               p.policy_number, p.sum_assured, p.start_date AS pol_start, p.end_date AS pol_end,
               p.policy_status,
               pp.plan_name, pp.policy_type,
               c.customer_code, c.first_name AS cust_first, c.last_name AS cust_last,
               c.phone_number AS cust_phone, c.email AS cust_email, c.city AS cust_city
        FROM claim cl
        JOIN policy p ON cl.policy_id = p.policy_id
        JOIN policy_plan pp ON p.plan_id = pp.plan_id
        JOIN customer c ON p.customer_id = c.customer_id
        WHERE {c_where}
    """
    claim = query_one(sql)
    if not claim:
        abort(404, description="Claim not found")

    real_cid = claim.get("claim_id")

    # Documents
    documents = query(f"""
        SELECT document_id, document_type, document_title, file_storage_path,
               uploaded_date, verification_status
        FROM claim_document
        WHERE claim_id = {real_cid}
        ORDER BY document_id
    """)

    # Assessment
    assessment = query_one(f"""
        SELECT assessment_id, assessor_name, assessor_license_no,
               inspection_date, assessment_date, assessed_loss_amount,
               recommended_amount, assessment_report_summary, assessment_decision
        FROM claim_assessment
        WHERE claim_id = {real_cid}
    """)

    # Settlement
    settlement = query_one(f"""
        SELECT settlement_id, settlement_number, settlement_decision,
               gross_settlement_amount, deductible_amount, net_paid_amount,
               settlement_date, payment_channel, disbursement_reference_no, remarks
        FROM claim_settlement
        WHERE claim_id = {real_cid}
    """)

    return render_template(
        "claim_detail.html",
        claim=claim,
        documents=documents,
        assessment=assessment,
        settlement=settlement
    )
