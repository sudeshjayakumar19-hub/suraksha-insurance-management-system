# Suraksha Insurance Management System — Web Application

A full-stack, enterprise-grade insurance policy, premium, and claims management platform built with **Python & Flask** connecting directly to an **Oracle Database 10g Enterprise Edition** relational backend.

Developed for academic DBMS project presentation, viva defense, and relational modeling evaluation.

---

## Key Features

1. **Live Oracle 10g Integration**: Real-time querying across 14 normalized 3NF tables with zero static mockups.
2. **Executive Dashboard**: Live KPI cards tracking customers (25), policies (40), claims (12), premiums collected (₹2.60 Lakhs), and settlements disbursed (₹52.07 Lakhs).
3. **Underwriting & Customer Profiles**: Full 3NF relational navigation linking customers to multi-line policies and insurance plan terms.
4. **Beneficiary Allocation Audit**: Evaluates M:N associative entity splits and verifies 100.00% nominee allocations per policy.
5. **Premium Accounts Receivable**: Installment billing aging ledger categorized by Paid, Pending, Overdue, and Waived.
6. **3-Stage Claim Lifecycle Dossier**: Visualizes the complete claim journey:
   - **Stage 1**: Supporting documents dossier
   - **Stage 2**: Independent surveyor loss assessment (1:0..1)
   - **Stage 3**: Banking liquidation voucher & deductible audit (1:0..1)
7. **10 Interactive Business Reports**: Core reports including the zero-multiplication policy financial balance sheet.
8. **SQL Demonstration Panel**: Predefined, parameterized SQL query executor for technical viva defense.
9. **Database Health Audit**: Live 14-table row count verification ledger confirming zero data mutations (223 rows).

---

## Quick Start

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch the application
python app.py

# 3. Access in browser
http://127.0.0.1:5000
```

Refer to [WORKING_MODEL_DEMO_GUIDE.txt](../WORKING_MODEL_DEMO_GUIDE.txt) for the step-by-step presentation script.
