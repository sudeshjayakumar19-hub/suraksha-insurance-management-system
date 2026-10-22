from flask import Blueprint, render_template
from database import query

beneficiaries_bp = Blueprint("beneficiaries", __name__)

@beneficiaries_bp.route("/beneficiaries")
def beneficiary_list():
    sql = """
        SELECT p.policy_id, p.policy_number, p.sum_assured,
               b.beneficiary_id, b.first_name || ' ' || b.last_name AS beneficiary_name,
               pb.relationship_to_insured, pb.allocation_percentage,
               pb.is_primary, pb.designated_date,
               b.contact_number, b.email, b.national_id
        FROM policy p
        JOIN policy_beneficiary pb ON p.policy_id = pb.policy_id
        JOIN beneficiary b ON pb.beneficiary_id = b.beneficiary_id
        ORDER BY p.policy_number, pb.is_primary DESC
    """
    rows = query(sql)
    for r in rows:
        sa = float(r.get("sum_assured", 0))
        pct = float(r.get("allocation_percentage", 0))
        r["benefit_amount"] = (sa * pct / 100.0)
        r["designation"] = "PRIMARY" if str(r.get("is_primary")) == "1" else "CONTINGENT"

    # Also get policy-level allocation sums to prove 100.00% split
    policy_sums = query("""
        SELECT p.policy_number, COUNT(pb.beneficiary_id) AS total_nominees,
               SUM(pb.allocation_percentage) AS total_allocation_pct
        FROM policy p
        JOIN policy_beneficiary pb ON p.policy_id = pb.policy_id
        GROUP BY p.policy_number
        ORDER BY p.policy_number
    """)

    return render_template("beneficiaries.html", beneficiaries=rows, policy_sums=policy_sums)
