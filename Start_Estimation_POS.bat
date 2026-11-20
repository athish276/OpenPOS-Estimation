@echo off
title OpenPOS Estimation System
cd /d "%~dp0"
echo Starting OpenPOS Estimation POS System...
start "" "http://localhost:3000"
"C:\Users\HP\AppData\Local\Python\bin\python.exe" estimation_server.py
pause
