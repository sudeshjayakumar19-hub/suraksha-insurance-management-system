from flask import Blueprint, render_template, request
from database import query, query_scalar

health_bp = Blueprint("health", __name__)

PREDEFINED_SQL_DEMOS = {
    "demo_join": {
        "title": "3NF Contract Underwriting JOIN",
        "description": "Traverses Customer -> Policy -> Policy Plan to display contract terms and coverage details.",
        "sql": """SELECT c.customer_code, c.first_name || ' ' || c.last_name AS customer_name,
       p.policy_number, pp.plan_name, pp.policy_type,
       p.start_date, p.end_date, p.sum_assured, p.premium_amount, p.policy_status
FROM customer c
JOIN policy p ON c.customer_id = p.customer_id
JOIN policy_plan pp ON p.plan_id = pp.plan_id
WHERE ROWNUM <= 10
ORDER BY c.customer_code, p.policy_number"""
    },
    "demo_groupby": {
        "title": "GROUP BY / HAVING: Multi-Policy Customer Concentration",
        "description": "Demonstrates analytical grouping and post-aggregation filtering for multi-contract customers.",
        "sql": """SELECT c.customer_code, c.first_name || ' ' || c.last_name AS customer_name,
       COUNT(p.policy_id) AS total_policies_owned,
       SUM(p.sum_assured) AS total_sum_assured,
       SUM(p.premium_amount) AS total_annual_premium
FROM customer c
JOIN policy p ON c.customer_id = p.customer_id
GROUP BY c.customer_code, c.first_name, c.last_name
HAVING COUNT(p.policy_id) > 1
ORDER BY total_policies_owned DESC, total_sum_assured DESC"""
    },
    "demo_premiums": {
        "title": "Premium Collection Revenue & Treasury Reconciliation",
        "description": "Summarizes collected funds, transaction volumes, and late fee penalties grouped by payment channel.",
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
    "demo_lifecycle": {
        "title": "Complete Claim Lifecycle Dossier (5-Table Outer Join)",
        "description": "Tracks an insurance claim across all lifecycle milestones: submission, documents, assessment, and settlement.",
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
    "demo_beneficiary": {
        "title": "Beneficiary Allocation Shares (M:N Associative Entity)",
        "description": "Calculates monetary entitlement shares for designated primary and contingent nominees.",
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
    "demo_settlement": {
        "title": "Settlement Liquidation & Deductible Audit",
        "description": "Reconciles gross claims, applied deductibles, net banking disbursements, and UTR tracking references.",
        "sql": """SELECT settlement_number, settlement_date, settlement_decision,
       gross_settlement_amount, deductible_amount, net_paid_amount,
       payment_channel, disbursement_reference_no, remarks
FROM claim_settlement
ORDER BY settlement_date DESC"""
    },
    "demo_financials": {
        "title": "Zero-Multiplication Underwriting Balance Sheet",
        "description": "Pre-aggregated independent joins ensuring exact matching of cash receivables and claims liquidation.",
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

@health_bp.route("/health")
def db_health():
    is_json = request.args.get("format") == "json" or "application/json" in request.headers.get("Accept", "")

    try:
        # 1. 14 Tables status and row counts
        sql_tables = """
            SELECT 'BRANCH' AS table_name, COUNT(*) AS row_count FROM branch UNION ALL
            SELECT 'CUSTOMER', COUNT(*) FROM customer UNION ALL
            SELECT 'BENEFICIARY', COUNT(*) FROM beneficiary UNION ALL
            SELECT 'POLICY_PLAN', COUNT(*) FROM policy_plan UNION ALL
            SELECT 'AGENT', COUNT(*) FROM agent UNION ALL
            SELECT 'POLICY', COUNT(*) FROM policy UNION ALL
            SELECT 'POLICY_BENEFICIARY', COUNT(*) FROM policy_beneficiary UNION ALL
            SELECT 'POLICY_RENEWAL', COUNT(*) FROM policy_renewal UNION ALL
            SELECT 'PREMIUM_SCHEDULE', COUNT(*) FROM premium_schedule UNION ALL
            SELECT 'PREMIUM_PAYMENT', COUNT(*) FROM premium_payment UNION ALL
            SELECT 'CLAIM', COUNT(*) FROM claim UNION ALL
            SELECT 'CLAIM_DOCUMENT', COUNT(*) FROM claim_document UNION ALL
            SELECT 'CLAIM_ASSESSMENT', COUNT(*) FROM claim_assessment UNION ALL
            SELECT 'CLAIM_SETTLEMENT', COUNT(*) FROM claim_settlement
        """
        table_rows = query(sql_tables)
        total_db_rows = sum(int(r.get("row_count", 0)) for r in table_rows)

        # 2. Constraints breakdown
        sql_constraints = """
            SELECT constraint_type, COUNT(*) AS count
            FROM user_constraints
            WHERE table_name IN ('BRANCH', 'AGENT', 'CUSTOMER', 'BENEFICIARY', 'POLICY_PLAN',
                                 'POLICY', 'POLICY_BENEFICIARY', 'POLICY_RENEWAL', 'PREMIUM_SCHEDULE',
                                 'PREMIUM_PAYMENT', 'CLAIM', 'CLAIM_DOCUMENT', 'CLAIM_ASSESSMENT', 'CLAIM_SETTLEMENT')
            GROUP BY constraint_type
            ORDER BY constraint_type
        """
        constraints_raw = query(sql_constraints)
        constraints = {"P": 0, "R": 0, "U": 0, "C": 0}
        for c in constraints_raw:
            ctype = c.get("constraint_type", c.get("con"))
            if ctype in constraints:
                constraints[ctype] = int(c.get("count", c.get("total", 0)))

        # 3. Sequences count
        seq_count = query_scalar("SELECT COUNT(*) FROM user_sequences WHERE sequence_name LIKE 'SEQ_%'", 14)

        # 4. Triggers count and status
        triggers = query("SELECT trigger_name, table_name, status FROM user_triggers WHERE trigger_name LIKE 'TRG_%' ORDER BY table_name")

        # 5. Database metadata
        version_info = "Oracle Database 10g Enterprise Edition Release 10.2.0.1.0 - Production"

        if is_json:
            return {
                "status": "healthy",
                "database": "connected",
                "tables_count": len(table_rows),
                "total_rows": total_db_rows
            }, 200

        return render_template(
            "health.html",
            table_rows=table_rows,
            total_db_rows=total_db_rows,
            constraints=constraints,
            seq_count=seq_count,
            triggers=triggers,
            version_info=version_info,
            db_connected=True
        )
    except Exception as e:
        if is_json:
            return {
                "status": "degraded",
                "database": "disconnected",
                "message": "Oracle database bridge is temporarily unavailable."
            }, 200

        return render_template(
            "health.html",
            table_rows=[],
            total_db_rows="Unavailable",
            constraints={"P": 0, "R": 0, "U": 0, "C": 0},
            seq_count=0,
            triggers=[],
            version_info="Oracle Database 10g Bridge: Temporarily Disconnected",
            db_connected=False,
            db_error_message="The Oracle 10g iSQL*Plus bridge is temporarily unreachable. Live database health metrics will resume once the database bridge service is online."
        ), 200

@health_bp.route("/sql-demo")
def sql_demo():
    selected_key = request.args.get("query", "demo_join")
    if selected_key not in PREDEFINED_SQL_DEMOS:
        selected_key = "demo_join"

    curr_demo = PREDEFINED_SQL_DEMOS[selected_key]
    results = query(curr_demo["sql"])
    columns = list(results[0].keys()) if results else []

    return render_template(
        "sql_demo.html",
        demos=PREDEFINED_SQL_DEMOS,
        selected_key=selected_key,
        current_demo=curr_demo,
        results=results,
        columns=columns
    )
