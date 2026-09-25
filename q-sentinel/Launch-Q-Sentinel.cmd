@echo off
cd /d "%~dp0"
if exist "..\.venv\Scripts\python.exe" (
  "..\.venv\Scripts\python.exe" -m streamlit run app.py
) else if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m streamlit run app.py
) else (
  echo Install Python 3.12 and follow README.md to create the environment.
  pause
)
