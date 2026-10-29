import os
import sys
from flask import Flask, render_template, request, redirect, url_for, session
from config import Config

# Ensure application directory is in python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from routes import (
    auth_bp,
    dashboard_bp,
    customers_bp,
    policies_bp,
    beneficiaries_bp,
    premiums_bp,
    claims_bp,
    reports_bp,
    health_bp
)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(policies_bp)
    app.register_blueprint(beneficiaries_bp)
    app.register_blueprint(premiums_bp)
    app.register_blueprint(claims_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(health_bp)

    @app.before_request
    def check_authentication():
        # Public endpoints that don't require authentication
        public_endpoints = ["auth.login", "auth.logout", "static", "health.db_health"]
        if request.endpoint:
            if any(request.endpoint.startswith(p) for p in public_endpoints):
                return None
            if "user" not in session:
                auto_param = request.args.get("auto")
                if auto_param:
                    return redirect(url_for("auth.login", auto=auto_param, next=request.path))
                return redirect(url_for("auth.login", next=request.path))

    @app.errorhandler(404)
    def not_found(e):
        return render_template("base.html", page_header="Page Not Found", content="<div class='card'><div class='card-body'><h3>404 - Record or Page Not Found</h3><p>The requested entity does not exist in the Oracle 10g database.</p></div></div>"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("base.html", page_header="Server Error", content=f"<div class='card'><div class='card-body'><h3>500 - Application Error</h3><p>{e}</p></div></div>"), 500

    return app

app = create_app()

if __name__ == "__main__":
    print(f"================================================================")
    print(f"SURAKSHA INSURANCE MANAGEMENT SYSTEM - ACADEMIC DBMS DEMO")
    print(f"Target Database: Oracle 10g Enterprise Edition (ORCL / SCOTT)")
    print(f"Live Server URL: http://127.0.0.1:{Config.FLASK_PORT}")
    print(f"Mode: INTERACTIVE DEMONSTRATION (CRUD Enabled on Oracle 10g)")
    print(f"================================================================")
    app.run(host="127.0.0.1", port=Config.FLASK_PORT, debug=Config.FLASK_DEBUG, threaded=True)
