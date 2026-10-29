import os
import secrets

class Config:
    """
    Configuration settings for SURAKSHA Insurance Management System.
    Supports both local development and cloud production deployment (e.g., Render).
    """

    # Environment detection
    IS_PRODUCTION = (
        os.environ.get("RENDER") is not None
        or os.environ.get("FLASK_ENV") == "production"
        or os.environ.get("ENVIRONMENT", "").lower() in ("production", "prod")
    )

    # Secret Key: in production, use environment variable or generate a secure ephemeral token.
    # In local development, retain the default dev key if unset.
    if IS_PRODUCTION:
        SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    else:
        SECRET_KEY = os.environ.get("SECRET_KEY", "insurance-dbms-secret-key-2026")

    # Oracle Database Bridge Configuration
    # In production, do not use insecure hardcoded fallback credentials.
    ORACLE_HOST = os.environ.get("ORACLE_HOST", "" if IS_PRODUCTION else "localhost")
    ORACLE_PORT = os.environ.get("ORACLE_PORT", "" if IS_PRODUCTION else "5560")
    ORACLE_CONNECT_ID = os.environ.get("ORACLE_CONNECT_ID", "" if IS_PRODUCTION else "orcl")

    if IS_PRODUCTION:
        ORACLE_USER = os.environ.get("ORACLE_USER", "")
        ORACLE_PASSWORD = os.environ.get("ORACLE_PASSWORD", "")
    else:
        ORACLE_USER = os.environ.get("ORACLE_USER", "scott")
        ORACLE_PASSWORD = os.environ.get("ORACLE_PASSWORD", "tiger")

    # Safe construction of iSQL*Plus URL
    if ORACLE_HOST and ORACLE_PORT:
        ISQLPLUS_URL = f"http://{ORACLE_HOST}:{ORACLE_PORT}/isqlplus"
    elif ORACLE_HOST:
        ISQLPLUS_URL = f"http://{ORACLE_HOST}/isqlplus"
    else:
        ISQLPLUS_URL = ""

    # Port configuration: Respect Render-provided PORT first, then FLASK_PORT, defaulting to 5000
    _port_raw = os.environ.get("PORT") or os.environ.get("FLASK_PORT", "5000")
    try:
        FLASK_PORT = int(_port_raw)
    except (ValueError, TypeError):
        FLASK_PORT = 5000

    FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1")
