@echo off
cd /d "%~dp0"
pip install -r requirements.txt --quiet
start "" pythonw main.py
