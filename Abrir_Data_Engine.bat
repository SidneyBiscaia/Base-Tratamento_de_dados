@echo off
setlocal
cd /d "%~dp0"
python -c "import streamlit, pandas, openpyxl, xlrd, pypdf, ofxparse, matplotlib" >nul 2>nul
if errorlevel 1 (
  echo Installing Data Engine and its standard file readers...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Installation failed. Check Python and internet access, then try again.
    pause
    exit /b 1
  )
)
python -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
