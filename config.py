import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "insurance-dbms-secret-key-2026")
    ORACLE_HOST = os.environ.get("ORACLE_HOST", "localhost")
    ORACLE_PORT = os.environ.get("ORACLE_PORT", "5560")
    ORACLE_CONNECT_ID = os.environ.get("ORACLE_CONNECT_ID", "orcl")
    ORACLE_USER = os.environ.get("ORACLE_USER", "scott")
    ORACLE_PASSWORD = os.environ.get("ORACLE_PASSWORD", "tiger")
    ISQLPLUS_URL = f"http://{ORACLE_HOST}:{ORACLE_PORT}/isqlplus"
    FLASK_PORT = int(os.environ.get("FLASK_PORT", 5000))
    FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1")
