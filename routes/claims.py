from flask import Blueprint, render_template, request, abort, redirect, url_for, flash
from database import query, query_one, query_scalar, execute_dml
from routes.auth import role_required

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
        ORDER BY cl.claim_id DESC
    """
    claims = query(sql)

    # Status distribution summary
    status_summary = query("""
        SELECT claim_status, COUNT(*) AS count, NVL(SUM(claimed_amount), 0) AS total_claimed
        FROM claim
        GROUP BY claim_status
        ORDER BY count DESC
    """)

    # Active policies for Add Claim modal
    active_policies = query("SELECT policy_id, policy_number, sum_assured FROM policy WHERE policy_status = 'ACTIVE' ORDER BY policy_number")

    return render_template(
        "claims.html",
        claims=claims,
        status_filter=status_filter,
        status_summary=status_summary,
        active_policies=active_policies
    )

@claims_bp.route("/claims/add", methods=["POST"])
@role_required("ADMIN", "SURVEYOR")
def claim_add():
    policy_id = request.form.get("policy_id")
    incident_date = request.form.get("incident_date", "2026-02-10").strip()
    filing_date = request.form.get("filing_date", "2026-02-12").strip()
    claimed_amount = request.form.get("claimed_amount", "75000").strip()
    description = request.form.get("claim_description", "Hospitalization medical claim").strip()

    if not policy_id or not claimed_amount:
        flash("Policy selection and claimed amount are required.", "danger")
        return redirect(url_for("claims.claim_list"))

    try:
        next_cid = query_scalar("SELECT NVL(MAX(claim_id), 0) + 1 FROM claim", default=100) or 100
        claim_num = f"CLM-2026-{int(next_cid):04d}"
        desc_clean = description.replace("'", "''")

        sql = f"""
            INSERT INTO claim (
                policy_id, claim_number, incident_date, filing_date,
                claimed_amount, claim_description, claim_status
            ) VALUES (
                {policy_id}, '{claim_num}', TO_DATE('{incident_date}', 'YYYY-MM-DD'),
                TO_DATE('{filing_date}', 'YYYY-MM-DD'), {claimed_amount},
                '{desc_clean}', 'SUBMITTED'
            )
        """
        execute_dml(sql)
        flash(f"Claim '{claim_num}' (₹{claimed_amount}) successfully registered in Oracle 10g database!", "success")
    except Exception as e:
        flash(f"Oracle 10g Error: {e}", "danger")

    return redirect(url_for("claims.claim_list"))

@claims_bp.route("/claims/status/<int:claim_id>/<new_status>", methods=["POST"])
@role_required("ADMIN", "SURVEYOR")
def claim_update_status(claim_id, new_status):
    valid_statuses = ["SUBMITTED", "UNDER_INVESTIGATION", "APPROVED", "REJECTED", "SETTLED"]
    clean_status = new_status.upper().strip()
    if clean_status not in valid_statuses:
        flash(f"Invalid claim status: {clean_status}", "danger")
        return redirect(url_for("claims.claim_list"))

    try:
        execute_dml(f"UPDATE claim SET claim_status = '{clean_status}' WHERE claim_id = {claim_id}")
        flash(f"Claim #{claim_id} status successfully transitioned to '{clean_status}' in Oracle 10g!", "success")
    except Exception as e:
        flash(f"Database Error: {e}", "danger")

    return redirect(request.referrer or url_for("claims.claim_list"))

@claims_bp.route("/claims/delete/<int:claim_id>", methods=["POST"])
@role_required("ADMIN")
def claim_delete(claim_id):
    try:
        execute_dml(f"DELETE FROM claim WHERE claim_id = {claim_id}")
        flash(f"Claim #{claim_id} successfully deleted from Oracle 10g database.", "success")
    except RuntimeError as e:
        err_msg = str(e)
        if "ORA-02292" in err_msg:
            flash(f"Cannot delete Claim #{claim_id}: Linked documents, surveyor assessments, or settlement disbursements exist (Protected by Oracle FK Constraint).", "warning")
        else:
            flash(f"Database Error: {e}", "danger")
    except Exception as e:
        flash(f"Error: {e}", "danger")

    return redirect(url_for("claims.claim_list"))

@claims_bp.route("/claims/<claim_id>")
def claim_detail(claim_id):
    cid_clean = claim_id.replace("'", "''")
    if cid_clean.isdigit():
        c_where = f"cl.claim_id = {cid_clean}"
    else:
        c_where = f"UPPER(cl.claim_number) = UPPER('{cid_clean}')"

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

    documents = query(f"""
        SELECT document_id, document_type, document_title, file_storage_path,
               uploaded_date, verification_status
        FROM claim_document
        WHERE claim_id = {real_cid}
        ORDER BY document_id
    """)

    assessment = query_one(f"""
        SELECT assessment_id, assessor_name, assessor_license_no,
               inspection_date, assessment_date, assessed_loss_amount,
               recommended_amount, assessment_report_summary, assessment_decision
        FROM claim_assessment
        WHERE claim_id = {real_cid}
    """)

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
