"""
Suraksha Insurance Management System - Production WSGI Runner
Using Waitress (Production-grade, Multi-threaded WSGI Server for Windows & Linux)
"""

import os
import sys
import socket
from waitress import serve

# Add current directory to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
from database import db

def get_lan_ip():
    """Retrieve the primary local LAN IP address for cross-device access."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def main():
    port = int(os.environ.get("PORT", 5000))
    host = "0.0.0.0"
    lan_ip = get_lan_ip()

    print("=" * 70)
    print(" SURAKSHA INSURANCE MANAGEMENT SYSTEM - PRODUCTION DEPLOYMENT")
    print("=" * 70)
    print(f" * Backend Database: Oracle Database 10g Enterprise Edition (SCOTT@ORCL)")
    print(f" * Testing Oracle Connectivity...")
    
    try:
        if db.test_connection():
            print(f" * [SUCCESS] Oracle 10g Database Bridge is ONLINE and RESPONDING.")
        else:
            print(f" * [WARNING] Oracle Bridge returned false. Server will start in standalone mode.")
    except Exception as e:
        print(f" * [NOTICE] Database check notice: {e}")

    print("-" * 70)
    print(f" * Production Server Engine: Waitress WSGI (Multi-Threaded Pool: 12 Threads)")
    print(f" * Listening Interface: {host}:{port}")
    print(f"")
    print(f" >> LOCAL ACCESS (This Machine):")
    print(f"    http://127.0.0.1:{port}   or   http://localhost:{port}")
    print(f"")
    print(f" >> INTRANET / WI-FI ACCESS (Faculty, Classmates, Mobile Devices):")
    print(f"    http://{lan_ip}:{port}")
    print(f"")
    print(f" >> AUTHORIZED DEMO CREDENTIALS:")
    print(f"    - Admin:       admin / admin123        (CUO / Full Root Access)")
    print(f"    - Underwriter: underwriter / policy123 (Underwriting & Issuance)")
    print(f"    - Surveyor:    surveyor / claims123    (Claims Adjudication)")
    print(f"    - Agent:       agent / agent123        (Customer Onboarding)")
    print(f"    - Oracle DBA:  scott / tiger           (Schema Administration)")
    print("=" * 70)
    print(f" Server is running. Press CTRL+C to safely shut down.\n")

    serve(app, host=host, port=port, threads=12, channel_timeout=60)

if __name__ == "__main__":
    main()
