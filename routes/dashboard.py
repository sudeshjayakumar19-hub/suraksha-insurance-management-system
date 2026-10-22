from flask import Blueprint, render_template
from database import query, query_scalar

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
def index():
    # 1. Combined single-query metrics from DUAL for sub-second page loads
    meta = query("""
        SELECT
          (SELECT COUNT(*) FROM customer) AS customers,
          (SELECT COUNT(*) FROM policy) AS policies,
          (SELECT COUNT(*) FROM beneficiary) AS beneficiaries,
          (SELECT COUNT(*) FROM agent) AS agents,
          (SELECT COUNT(*) FROM branch) AS branches,
          (SELECT COUNT(*) FROM policy_plan) AS plans,
          (SELECT COUNT(*) FROM premium_schedule) AS schedules,
          (SELECT COUNT(*) FROM premium_payment) AS payments,
          (SELECT COUNT(*) FROM claim) AS claims,
          (SELECT COUNT(*) FROM claim_document) AS documents,
          (SELECT COUNT(*) FROM claim_assessment) AS assessments,
          (SELECT COUNT(*) FROM claim_settlement) AS settlements,
          (SELECT COUNT(*) FROM policy_beneficiary) AS policy_beneficiaries,
          (SELECT COUNT(*) FROM policy_renewal) AS renewals,
          (SELECT NVL(SUM(installment_amount), 0) FROM premium_schedule) AS scheduled_premium,
          (SELECT NVL(SUM(amount_paid), 0) FROM premium_payment) AS collected_premium,
          (SELECT NVL(SUM(claimed_amount), 0) FROM claim) AS claimed_exposure,
          (SELECT NVL(SUM(net_paid_amount), 0) FROM claim_settlement) AS settlement_disbursed
        FROM DUAL
    """)
    m = meta[0] if meta else {}
    counts = {
        "customers": int(m.get("customers", 0)),
        "policies": int(m.get("policies", 0)),
        "beneficiaries": int(m.get("beneficiaries", 0)),
        "agents": int(m.get("agents", 0)),
        "branches": int(m.get("branches", 0)),
        "plans": int(m.get("plans", 0)),
        "schedules": int(m.get("schedules", 0)),
        "payments": int(m.get("payments", 0)),
        "claims": int(m.get("claims", 0)),
        "documents": int(m.get("documents", 0)),
        "assessments": int(m.get("assessments", 0)),
        "settlements": int(m.get("settlements", 0)),
    }
    counts["total_rows"] = sum(int(m.get(k, 0)) for k in [
        "customers", "policies", "beneficiaries", "agents", "branches", "plans",
        "schedules", "payments", "claims", "documents", "assessments", "settlements",
        "policy_beneficiaries", "renewals"
    ])

    financials = {
        "scheduled_premium": float(m.get("scheduled_premium", 0)),
        "collected_premium": float(m.get("collected_premium", 0)),
        "claimed_exposure": float(m.get("claimed_exposure", 0)),
        "settlement_disbursed": float(m.get("settlement_disbursed", 0)),
    }
    financials["net_margin"] = financials["collected_premium"] - financials["settlement_disbursed"]

    # 3. Recent policies table
    recent_policies = query("""
        SELECT p.policy_id, p.policy_number, c.first_name || ' ' || c.last_name AS customer_name,
               pp.plan_name, pp.policy_type, p.sum_assured, p.premium_amount, p.policy_status
        FROM policy p
        JOIN customer c ON p.customer_id = c.customer_id
        JOIN policy_plan pp ON p.plan_id = pp.plan_id
        WHERE ROWNUM <= 6
        ORDER BY p.issue_date DESC
    """)

    # 4. Recent claims table
    recent_claims = query("""
        SELECT cl.claim_id, cl.claim_number, p.policy_number, cl.incident_date,
               cl.filing_date, cl.claimed_amount, cl.claim_status
        FROM claim cl
        JOIN policy p ON cl.policy_id = p.policy_id
        WHERE ROWNUM <= 6
        ORDER BY cl.filing_date DESC
    """)

    # 5. Claims by status distribution
    claim_status_dist = query("""
        SELECT claim_status, COUNT(*) AS count, NVL(SUM(claimed_amount), 0) AS total_amount
        FROM claim
        GROUP BY claim_status
        ORDER BY count DESC
    """)

    return render_template(
        "dashboard.html",
        counts=counts,
        financials=financials,
        recent_policies=recent_policies,
        recent_claims=recent_claims,
        claim_status_dist=claim_status_dist
    )
