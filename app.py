import os
import sys
from flask import Flask, render_template, request, redirect, url_for, session
from config import Config

# Ensure application directory is in python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database import DatabaseConnectionError

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

    @app.errorhandler(DatabaseConnectionError)
    @app.errorhandler(ConnectionError)
    def db_connection_error(e):
        """
        Graceful error handler for database connection or bridge availability issues.
        Never displays sensitive credentials or stack traces.
        """
        return render_template(
            "error.html",
            page_header="Database Service Unavailable",
            title="Oracle Database Bridge Unavailable",
            message="The application is running, but the Oracle 10g database bridge is currently unreachable. Database-backed operations and real-time records are temporarily paused."
        ), 503

    @app.errorhandler(404)
    def not_found(e):
        return render_template(
            "error.html",
            page_header="Page Not Found",
            title="404 - Record or Page Not Found",
            message="The requested entity or route does not exist in the Oracle 10g database system."
        ), 404

    @app.errorhandler(500)
    def server_error(e):
        # Prevent leaking sensitive stack traces or credentials in production
        msg = str(e) if app.debug else "An unexpected application error occurred. Please contact the administrator."
        return render_template(
            "error.html",
            page_header="Server Error",
            title="500 - Application Error",
            message=msg
        ), 500

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT") or Config.FLASK_PORT)
    host = os.environ.get("HOST", "0.0.0.0")
    print("================================================================")
    print("SURAKSHA INSURANCE MANAGEMENT SYSTEM - ACADEMIC DBMS DEMO")
    print(f"Target Database: Oracle 10g Enterprise Edition (ORCL / SCOTT)")
    print(f"Live Server URL: http://{host}:{port}")
    print(f"Mode: {'DEVELOPMENT' if Config.FLASK_DEBUG else 'PRODUCTION'}")
    print("================================================================")
    app.run(host=host, port=port, debug=Config.FLASK_DEBUG, threaded=True)
