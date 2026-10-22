from flask import Blueprint, render_template, request
from database import query

reports_bp = Blueprint("reports", __name__)

REPORTS_REGISTRY = {
    "customer_portfolio": {
        "title": "Customer Policy Portfolio Summary",
        "description": "Consolidated customer portfolio tracking active insurance holdings, total insured valuation, and annual commitments.",
        "sql": """SELECT c.customer_code, c.first_name || ' ' || c.last_name AS customer_name, c.city, c.kyc_status,
       COUNT(p.policy_id) AS total_policies_owned,
       NVL(SUM(p.sum_assured), 0) AS total_portfolio_sum_assured,
       NVL(SUM(p.premium_amount), 0) AS total_annual_premium
FROM customer c
LEFT JOIN policy p ON c.customer_id = p.customer_id
GROUP BY c.customer_code, c.first_name, c.last_name, c.city, c.kyc_status
ORDER BY total_annual_premium DESC"""
    },
    "agent_portfolio": {
        "title": "Agent Policy Portfolio & Inception Performance",
        "description": "Sales agent production ledger showing policies written, sum assured serviced, and commission earned.",
        "sql": """SELECT a.agent_code, a.first_name || ' ' || a.last_name AS agent_name,
       b.branch_name, a.commission_rate,
       COUNT(p.policy_id) AS policies_underwritten,
       NVL(SUM(p.sum_assured), 0) AS total_coverage_serviced,
       NVL(SUM(p.premium_amount), 0) AS total_premium_collected,
       ROUND(NVL(SUM(p.premium_amount * a.commission_rate / 100), 0), 2) AS commission_earned
FROM branch b
JOIN agent a ON b.branch_id = a.branch_id
JOIN policy p ON a.agent_id = p.agent_id
GROUP BY a.agent_code, a.first_name, a.last_name, b.branch_name, a.commission_rate
ORDER BY total_premium_collected DESC"""
    },
    "branch_performance": {
        "title": "Branch Performance & Regional Distribution",
        "description": "Regional branch distribution summarizing station headcount, active policies under management, and premium volume.",
        "sql": """SELECT b.branch_code, b.branch_name, b.city, b.state,
       COUNT(DISTINCT a.agent_id) AS licensed_agents,
       COUNT(p.policy_id) AS policies_under_management,
       NVL(SUM(p.premium_amount), 0) AS total_branch_premium_volume
FROM branch b
LEFT JOIN agent a ON b.branch_id = a.branch_id
LEFT JOIN policy p ON a.agent_id = p.agent_id
GROUP BY b.branch_code, b.branch_name, b.city, b.state
ORDER BY total_branch_premium_volume DESC"""
    },
    "premium_collection": {
        "title": "Premium Collection Revenue & Payment Mode Distribution",
        "description": "Treasury reconciliation report summarizing funds collected across payment modes (UPI, Net Banking, etc.).",
        "sql": """SELECT payment_mode,
       COUNT(payment_id) AS transaction_count,
       SUM(amount_paid) AS total_funds_collected,
       SUM(late_fee_applied) AS total_late_fees_collected,
       ROUND(AVG(amount_paid), 2) AS average_transaction_value
FROM premium_payment
WHERE payment_status = 'SUCCESS'
GROUP BY payment_mode
ORDER BY total_funds_collected DESC"""
    },
    "outstanding_premium": {
        "title": "Outstanding & Overdue Premium Ledger Analysis",
        "description": "Accounts receivable aging summary identifying unpaid, pending, overdue, and waived installments.",
        "sql": """SELECT status AS schedule_status,
       COUNT(schedule_id) AS installment_count,
       SUM(installment_amount) AS total_outstanding_amount,
       MIN(due_date) AS oldest_due_date,
       MAX(due_date) AS newest_due_date
FROM premium_schedule
GROUP BY status
ORDER BY total_outstanding_amount DESC"""
    },
    "claim_pipeline": {
        "title": "Claim Status Pipeline & Adjudication Summary",
        "description": "Operational tracking of claims workflow across all adjudication stages.",
        "sql": """SELECT claim_status,
       COUNT(claim_id) AS claim_count,
       SUM(claimed_amount) AS total_claimed_amount,
       ROUND(AVG(claimed_amount), 2) AS average_claim_amount,
       MIN(filing_date) AS earliest_filing_date,
       MAX(filing_date) AS latest_filing_date
FROM claim
GROUP BY claim_status
ORDER BY total_claimed_amount DESC"""
    },
    "claim_lifecycle": {
        "title": "Complete Claim Lifecycle Dossier Audit",
        "description": "End-to-end dossier linking policy contracts, loss events, surveyor inspections, and bank liquidation vouchers.",
        "sql": """SELECT cl.claim_number, p.policy_number, cl.claim_status, cl.claimed_amount,
       COUNT(cd.document_id) AS total_verified_documents,
       NVL(ca.assessor_name, 'NOT_ASSIGNED') AS assessor_name,
       NVL(ca.recommended_amount, 0) AS surveyor_recommended_payout,
       NVL(cs.settlement_number, 'UNSETTLED') AS settlement_voucher_no,
       NVL(cs.settlement_decision, 'PENDING') AS settlement_decision,
       NVL(cs.net_paid_amount, 0) AS net_settlement_disbursed
FROM policy p
JOIN claim cl ON p.policy_id = cl.policy_id
LEFT JOIN claim_document cd ON cl.claim_id = cd.claim_id
LEFT JOIN claim_assessment ca ON cl.claim_id = ca.claim_id
LEFT JOIN claim_settlement cs ON cl.claim_id = cs.claim_id
GROUP BY cl.claim_number, p.policy_number, cl.claim_status, cl.claimed_amount,
         ca.assessor_name, ca.recommended_amount,
         cs.settlement_number, cs.settlement_decision, cs.net_paid_amount
ORDER BY cl.claim_number"""
    },
    "beneficiary_allocation": {
        "title": "Beneficiary Allocation Shares & Benefit Calculation",
        "description": "Nominee entitlement distribution validating that allocations split cleanly to 100.00%.",
        "sql": """SELECT p.policy_number, p.sum_assured,
       b.first_name || ' ' || b.last_name AS beneficiary_name,
       pb.relationship_to_insured, pb.allocation_percentage,
       ROUND((p.sum_assured * pb.allocation_percentage / 100), 2) AS calculated_entitlement_amount,
       CASE WHEN pb.is_primary = 1 THEN 'PRIMARY' ELSE 'CONTINGENT' END AS designation_type
FROM policy p
JOIN policy_beneficiary pb ON p.policy_id = pb.policy_id
JOIN beneficiary b ON pb.beneficiary_id = b.beneficiary_id
ORDER BY p.policy_number, pb.is_primary DESC"""
    },
    "settlement_audit": {
        "title": "Claim Settlement Disbursement & Banking Channel Audit",
        "description": "Financial liquidation audit reconciling gross liabilities, applied deductibles, and bank UTR numbers.",
        "sql": """SELECT settlement_number, settlement_date, settlement_decision,
       gross_settlement_amount, deductible_amount, net_paid_amount,
       payment_channel, disbursement_reference_no, remarks
FROM claim_settlement
ORDER BY settlement_date DESC"""
    },
    "financial_summary": {
        "title": "Policy Financial Summary (Zero-Multiplication Underwriting Balance Sheet)",
        "description": "Underwriting margin calculation matching verified Step 11 values with zero cartesian multiplication.",
        "sql": """SELECT p.policy_number, p.policy_status,
       NVL(ps_agg.scheduled_premium, 0) AS total_scheduled_premium,
       NVL(pay_agg.collected_premium, 0) AS total_collected_premium,
       NVL(cl_agg.total_claimed, 0) AS total_claimed_exposure,
       NVL(cs_agg.total_settled, 0) AS total_settlement_disbursed,
       (NVL(pay_agg.collected_premium, 0) - NVL(cs_agg.total_settled, 0)) AS net_underwriting_margin
FROM policy p
LEFT JOIN (
    SELECT policy_id, SUM(installment_amount) AS scheduled_premium
    FROM premium_schedule GROUP BY policy_id
) ps_agg ON p.policy_id = ps_agg.policy_id
LEFT JOIN (
    SELECT ps.policy_id, SUM(pp.amount_paid) AS collected_premium
    FROM premium_schedule ps JOIN premium_payment pp ON ps.schedule_id = pp.schedule_id
    GROUP BY ps.policy_id
) pay_agg ON p.policy_id = pay_agg.policy_id
LEFT JOIN (
    SELECT policy_id, SUM(claimed_amount) AS total_claimed
    FROM claim GROUP BY policy_id
) cl_agg ON p.policy_id = cl_agg.policy_id
LEFT JOIN (
    SELECT cl.policy_id, SUM(cs.net_paid_amount) AS total_settled
    FROM claim cl JOIN claim_settlement cs ON cl.claim_id = cs.claim_id
    GROUP BY cl.policy_id
) cs_agg ON p.policy_id = cs_agg.policy_id
WHERE ps_agg.scheduled_premium IS NOT NULL OR cl_agg.total_claimed IS NOT NULL
ORDER BY p.policy_number"""
    }
}

@reports_bp.route("/reports")
def report_view():
    report_key = request.args.get("type", "customer_portfolio")
    if report_key not in REPORTS_REGISTRY:
        report_key = "customer_portfolio"

    curr_report = REPORTS_REGISTRY[report_key]
    report_data = query(curr_report["sql"])

    # Get column names for dynamic table rendering
    columns = list(report_data[0].keys()) if report_data else []

    return render_template(
        "reports.html",
        registry=REPORTS_REGISTRY,
        active_key=report_key,
        current_report=curr_report,
        report_data=report_data,
        columns=columns
    )
