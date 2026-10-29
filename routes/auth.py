from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from datetime import datetime

auth_bp = Blueprint("auth", __name__)

# Registry of Authorized Users with Role-Based Access Control (RBAC)
AUTHORIZED_USERS = {
    "admin": {
        "password": "admin123",
        "name": "Dr. R. K. Sharma",
        "email": "rk.sharma@surakshainsure.in",
        "department": "Executive Underwriting",
        "role": "ADMIN",
        "title": "Chief Underwriting Officer",
        "badge": "ADMIN / CUO",
        "badge_color": "#d97706",
        "status": "ACTIVE",
        "last_login": "2026-10-29 18:15",
        "permissions": ["all", "manage_users", "delete", "approve_claims", "issue_policies", "access_sql"]
    },
    "underwriter": {
        "password": "policy123",
        "name": "Pooja Malhotra",
        "email": "pooja.m@surakshainsure.in",
        "department": "Actuarial & Risk",
        "role": "UNDERWRITER",
        "title": "Lead Underwriter",
        "badge": "UNDERWRITER",
        "badge_color": "#0284c7",
        "status": "ACTIVE",
        "last_login": "2026-10-29 17:30",
        "permissions": ["issue_policies", "view_all", "edit_policies"]
    },
    "surveyor": {
        "password": "claims123",
        "name": "Ananya Sen",
        "email": "ananya.sen@surakshainsure.in",
        "department": "Claims Adjudication",
        "role": "SURVEYOR",
        "title": "Senior Claims Surveyor",
        "badge": "SURVEYOR",
        "badge_color": "#2563eb",
        "status": "ACTIVE",
        "last_login": "2026-10-29 16:45",
        "permissions": ["add_claims", "approve_claims", "reject_claims", "investigate_claims"]
    },
    "agent": {
        "password": "agent123",
        "name": "Rajesh Kumar",
        "email": "rajesh.k@surakshainsure.in",
        "department": "Agency Distribution",
        "role": "AGENT",
        "title": "Agency Branch Manager",
        "badge": "AGENT",
        "badge_color": "#10b981",
        "status": "ACTIVE",
        "last_login": "2026-10-29 15:20",
        "permissions": ["add_customers", "issue_policies", "view_all"]
    },
    "scott": {
        "password": "tiger",
        "name": "SCOTT (DBA)",
        "email": "scott@oracle10g.local",
        "department": "Database Systems",
        "role": "DBA",
        "title": "Oracle 10g Administrator",
        "badge": "DBA",
        "badge_color": "#7c3aed",
        "status": "ACTIVE",
        "last_login": "2026-10-29 18:00",
        "permissions": ["all", "access_sql", "health_check"]
    }
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user" not in session:
                return redirect(url_for("auth.login", next=request.path))
            user = session.get("user", {})
            user_role = user.get("role", "")
            # Admin and DBA bypass role restrictions
            if user_role in ["ADMIN", "DBA"] or user_role in allowed_roles:
                return f(*args, **kwargs)
            
            flash(f"Access Denied: Your assigned role '{user_role}' does not hold clearance for this operation. Required: {', '.join(allowed_roles)}.", "danger")
            return redirect(request.referrer or url_for("dashboard.index"))
        return decorated_function
    return decorator

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("dashboard.index"))

    error = None
    next_url = request.args.get("next") or url_for("dashboard.index")

    # Quick 1-click URL bypass: /login?auto=admin
    auto_user = request.args.get("auto", "").strip().lower()
    if auto_user and auto_user in AUTHORIZED_USERS:
        user_record = AUTHORIZED_USERS[auto_user]
        if user_record.get("status") != "SUSPENDED":
            user_data = user_record.copy()
            user_data["username"] = auto_user
            user_record["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            session["user"] = user_data
            flash(f"Welcome, {user_record['name']}! Authenticated as {user_record['badge']}.", "success")
            return redirect(next_url)

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()

        if username in AUTHORIZED_USERS:
            user_record = AUTHORIZED_USERS[username]
            if user_record.get("status") == "SUSPENDED":
                error = f"Account '{username}' is SUSPENDED. Please contact your System Administrator."
            elif user_record["password"] == password:
                user_data = user_record.copy()
                user_data["username"] = username
                user_record["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                session["user"] = user_data
                flash(f"Welcome back, {user_record['name']}! Authenticated as {user_record['badge']}.", "success")
                return redirect(next_url)
            else:
                error = "Authentication failed: Invalid security password."
        else:
            error = f"Unauthorized access attempt: User '{username}' is not in the Authorized Personnel registry."

    return render_template("login.html", error=error, demo_users=AUTHORIZED_USERS, next_url=next_url)

@auth_bp.route("/logout")
def logout():
    user = session.pop("user", None)
    if user:
        flash(f"User {user.get('name')} successfully logged out. Secure session terminated.", "info")
    return redirect(url_for("auth.login"))

# Authorized Users Management View
@auth_bp.route("/users")
@login_required
def user_list():
    current_user = session.get("user", {})
    return render_template(
        "users.html",
        users=AUTHORIZED_USERS,
        current_user=current_user
    )

@auth_bp.route("/users/add", methods=["POST"])
@login_required
@role_required("ADMIN")
def user_add():
    username = request.form.get("username", "").strip().lower()
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    role = request.form.get("role", "AGENT").strip().upper()
    department = request.form.get("department", "General Insurance").strip()

    if not username or not password or not name:
        flash("Username, full name, and password are required.", "danger")
        return redirect(url_for("auth.user_list"))

    if username in AUTHORIZED_USERS:
        flash(f"Username '{username}' already exists in the authorized registry.", "warning")
        return redirect(url_for("auth.user_list"))

    role_colors = {
        "ADMIN": "#d97706",
        "UNDERWRITER": "#0284c7",
        "SURVEYOR": "#2563eb",
        "AGENT": "#10b981",
        "DBA": "#7c3aed"
    }

    AUTHORIZED_USERS[username] = {
        "password": password,
        "name": name,
        "email": email or f"{username}@surakshainsure.in",
        "department": department,
        "role": role,
        "title": f"Authorized {role.title()}",
        "badge": role,
        "badge_color": role_colors.get(role, "#64748b"),
        "status": "ACTIVE",
        "last_login": "Never",
        "permissions": ["view_all", "issue_policies"] if role == "UNDERWRITER" else ["all"]
    }

    flash(f"New authorized user '{name}' ({username}) provisioned with role {role}!", "success")
    return redirect(url_for("auth.user_list"))

@auth_bp.route("/users/toggle-status/<username>", methods=["POST"])
@login_required
@role_required("ADMIN")
def user_toggle_status(username):
    username = username.lower()
    if username == "admin":
        flash("System Master Administrator account cannot be suspended.", "danger")
        return redirect(url_for("auth.user_list"))

    if username in AUTHORIZED_USERS:
        current_status = AUTHORIZED_USERS[username].get("status", "ACTIVE")
        new_status = "SUSPENDED" if current_status == "ACTIVE" else "ACTIVE"
        AUTHORIZED_USERS[username]["status"] = new_status
        flash(f"User '{username}' status updated to {new_status}.", "warning" if new_status == "SUSPENDED" else "success")
    else:
        flash(f"User '{username}' not found.", "danger")

    return redirect(url_for("auth.user_list"))

@auth_bp.route("/users/delete/<username>", methods=["POST"])
@login_required
@role_required("ADMIN")
def user_delete(username):
    username = username.lower()
    if username in ["admin", "scott"]:
        flash("Protected system accounts cannot be revoked.", "danger")
        return redirect(url_for("auth.user_list"))

    if username in AUTHORIZED_USERS:
        del AUTHORIZED_USERS[username]
        flash(f"Authorized user '{username}' has been revoked from the system.", "success")
    else:
        flash(f"User '{username}' not found.", "danger")

    return redirect(url_for("auth.user_list"))
