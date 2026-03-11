@echo off
REM Launch Flower dashboard for Celery monitoring
call .venv\Scripts\Activate.bat
call .venv\Scripts\celery.exe -A safety_report_trial.workers flower
pause
