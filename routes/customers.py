from flask import Blueprint, render_template, request, abort, redirect, url_for, flash
from database import query, query_one, query_scalar, execute_dml
from routes.auth import role_required

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
            ORDER BY customer_id DESC
        """
    else:
        sql = """
            SELECT customer_id, customer_code, first_name, last_name,
                   email, phone_number, city, state, kyc_status,
                   date_of_birth, gender
            FROM customer
            ORDER BY customer_id DESC
        """
    customers = query(sql)
    return render_template("customers.html", customers=customers, search=search)

@customers_bp.route("/customers/add", methods=["POST"])
@role_required("ADMIN", "UNDERWRITER", "AGENT")
def customer_add():
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    gender = request.form.get("gender", "MALE").strip()
    dob = request.form.get("dob", "1992-05-15").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    national_id = request.form.get("national_id", "").strip()
    address = request.form.get("address", "").strip()
    city = request.form.get("city", "Mumbai").strip()
    state = request.form.get("state", "Maharashtra").strip()
    postal_code = request.form.get("postal_code", "400001").strip()
    kyc_status = request.form.get("kyc_status", "VERIFIED").strip()

    if not first_name or not last_name or not email:
        flash("First name, last name, and email are required fields.", "danger")
        return redirect(url_for("customers.customer_list"))

    f_name = first_name.replace("'", "''")
    l_name = last_name.replace("'", "''")
    em = email.replace("'", "''")
    ph = phone.replace("'", "''") if phone else "9876543210"
    nat_id = national_id.replace("'", "''") if national_id else f"PAN-{first_name[:3].upper()}9999Z"
    addr = address.replace("'", "''") if address else "Flat 101, Marine Drive"
    ct = city.replace("'", "''")
    st = state.replace("'", "''")
    pc = postal_code.replace("'", "''")

    # Generate next code
    next_seq = query_scalar("SELECT NVL(MAX(customer_id), 0) + 1 FROM customer", default=100) or 100
    cust_code = f"CUST-2026-{int(next_seq):04d}"

    sql = f"""
        INSERT INTO customer (
            customer_code, first_name, last_name, date_of_birth, gender,
            email, phone_number, national_id, address_line, city, state, postal_code,
            registration_date, kyc_status
        ) VALUES (
            '{cust_code}', '{f_name}', '{l_name}', TO_DATE('{dob}', 'YYYY-MM-DD'), '{gender}',
            '{em}', '{ph}', '{nat_id}', '{addr}', '{ct}', '{st}', '{pc}',
            SYSDATE, '{kyc_status}'
        )
    """
    try:
        execute_dml(sql)
        flash(f"Customer '{first_name} {last_name}' ({cust_code}) successfully created in Oracle 10g database!", "success")
    except Exception as e:
        flash(f"Oracle 10g Error: {e}", "danger")

    return redirect(url_for("customers.customer_list"))

@customers_bp.route("/customers/verify-kyc/<int:customer_id>", methods=["POST"])
@role_required("ADMIN", "UNDERWRITER", "AGENT")
def customer_verify_kyc(customer_id):
    try:
        execute_dml(f"UPDATE customer SET kyc_status = 'VERIFIED' WHERE customer_id = {customer_id}")
        flash(f"Customer #{customer_id} KYC verification status updated to 'VERIFIED' in Oracle 10g.", "success")
    except Exception as e:
        flash(f"Database Error: {e}", "danger")

    return redirect(request.referrer or url_for("customers.customer_list"))

@customers_bp.route("/customers/delete/<int:customer_id>", methods=["POST"])
@role_required("ADMIN")
def customer_delete(customer_id):
    try:
        execute_dml(f"DELETE FROM customer WHERE customer_id = {customer_id}")
        flash(f"Customer #{customer_id} successfully deleted from Oracle 10g database.", "success")
    except RuntimeError as e:
        err_msg = str(e)
        if "ORA-02292" in err_msg:
            flash(f"Cannot delete Customer #{customer_id}: Active insurance policies are linked to this customer (Oracle Foreign Key Constraint Enforced).", "warning")
        else:
            flash(f"Database Error: {e}", "danger")
    except Exception as e:
        flash(f"Unexpected error: {e}", "danger")

    return redirect(url_for("customers.customer_list"))

@customers_bp.route("/customers/<customer_id>")
def customer_detail(customer_id):
    cust_id_clean = customer_id.replace("'", "''")
    if cust_id_clean.isdigit():
        cust_sql = f"SELECT * FROM customer WHERE customer_id = {cust_id_clean}"
    else:
        cust_sql = f"SELECT * FROM customer WHERE UPPER(customer_code) = UPPER('{cust_id_clean}')"

    customer = query_one(cust_sql)
    if not customer:
        abort(404, description="Customer not found")

    real_cust_id = customer.get("customer_id")

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

    claims = query(f"""
        SELECT cl.claim_id, cl.claim_number, p.policy_number, pp.plan_name,
               cl.incident_date, cl.filing_date, cl.claimed_amount, cl.claim_status
        FROM claim cl
        JOIN policy p ON cl.policy_id = p.policy_id
        JOIN policy_plan pp ON p.plan_id = pp.plan_id
        WHERE p.customer_id = {real_cust_id}
        ORDER BY cl.filing_date DESC
    """)

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
