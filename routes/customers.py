from flask import Blueprint, render_template, request, abort
from database import query, query_one

customers_bp = Blueprint("customers", __name__)

@customers_bp.route("/customers")
def customer_list():
    search = request.args.get("q", "").strip()
    if search:
        search_safe = search.replace("'", "''")
        sql = f"""
            SELECT customer_id, customer_code, first_name, last_name,
                   email, phone_number, city, state, kyc_status,
                   date_of_birth, gender
            FROM customer
            WHERE UPPER(first_name) LIKE UPPER('%{search_safe}%')
               OR UPPER(last_name) LIKE UPPER('%{search_safe}%')
               OR UPPER(customer_code) LIKE UPPER('%{search_safe}%')
               OR UPPER(city) LIKE UPPER('%{search_safe}%')
            ORDER BY customer_id
        """
    else:
        sql = """
            SELECT customer_id, customer_code, first_name, last_name,
                   email, phone_number, city, state, kyc_status,
                   date_of_birth, gender
            FROM customer
            ORDER BY customer_id
        """
    customers = query(sql)
    return render_template("customers.html", customers=customers, search=search)

@customers_bp.route("/customers/<customer_id>")
def customer_detail(customer_id):
    # Lookup customer by id or code
    cust_id_clean = customer_id.replace("'", "''")
    if cust_id_clean.isdigit():
        cust_sql = f"SELECT * FROM customer WHERE customer_id = {cust_id_clean}"
    else:
        cust_sql = f"SELECT * FROM customer WHERE UPPER(customer_code) = UPPER('{cust_id_clean}')"

    customer = query_one(cust_sql)
    if not customer:
        abort(404, description="Customer not found")

    real_cust_id = customer.get("customer_id")

    # Get policies for this customer
    policies = query(f"""
        SELECT p.policy_id, p.policy_number, pp.plan_name, pp.policy_type,
               p.start_date, p.end_date, p.sum_assured, p.premium_amount,
               p.payment_frequency, p.policy_status,
               a.agent_code, a.first_name || ' ' || a.last_name AS agent_name
        FROM policy p
        JOIN policy_plan pp ON p.plan_id = pp.plan_id
        JOIN agent a ON p.agent_id = a.agent_id
        WHERE p.customer_id = {real_cust_id}
        ORDER BY p.start_date DESC
    """)

    # Get claims filed for this customer's policies
    claims = query(f"""
        SELECT cl.claim_id, cl.claim_number, p.policy_number, pp.plan_name,
               cl.incident_date, cl.filing_date, cl.claimed_amount, cl.claim_status
        FROM claim cl
        JOIN policy p ON cl.policy_id = p.policy_id
        JOIN policy_plan pp ON p.plan_id = pp.plan_id
        WHERE p.customer_id = {real_cust_id}
        ORDER BY cl.filing_date DESC
    """)

    # Summary metrics
    total_coverage = sum(float(p.get("sum_assured", 0)) for p in policies if p.get("sum_assured"))
    total_premium = sum(float(p.get("premium_amount", 0)) for p in policies if p.get("premium_amount"))

    return render_template(
        "customer_detail.html",
        customer=customer,
        policies=policies,
        claims=claims,
        total_coverage=total_coverage,
        total_premium=total_premium
    )
