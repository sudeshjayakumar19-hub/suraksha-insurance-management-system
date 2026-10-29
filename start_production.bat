@echo off
title Suraksha Insurance Management System - Production WSGI Server
color 0A

echo =======================================================================
echo          SURAKSHA INSURANCE MANAGEMENT SYSTEM - 1-CLICK LAUNCHER
echo =======================================================================
echo.

cd /d "%~dp0"

echo [1/3] Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found on your system PATH.
    echo Please install Python 3.10+ from python.org and check "Add to PATH".
    pause
    exit /b 1
)

echo [2/3] Checking dependencies (Flask, Waitress, Requests)...
python -c "import flask, waitress, requests, bs4" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [NOTICE] Installing required packages...
    pip install -r requirements.txt
)

echo [3/3] Launching Production Multi-Threaded WSGI Server (Waitress)...
echo.
python deploy_production.py

pause
