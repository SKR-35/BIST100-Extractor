@echo off
setlocal

chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

echo ==================================
echo BIST100 Daily Ingest Job
echo ==================================

REM -------------------------------
REM Paths
REM -------------------------------

REM Update project path
set "PROJECT_DIR=C:\Users\your-path\BIST100-Extractor"

REM SQLite database location
set "BIST_DB_PATH=your-path\bist100_prices.db"

REM Log folder
set "LOG_DIR=%PROJECT_DIR%\logs"


if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"


REM -------------------------------
REM Timestamped log
REM -------------------------------

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "RUN_TS=%%i"

set "LOG_FILE=%LOG_DIR%\bist_daily_ingest_%RUN_TS%.log"


echo START %DATE% %TIME% > "%LOG_FILE%"
echo PROJECT_DIR=%PROJECT_DIR% >> "%LOG_FILE%"
echo BIST_DB_PATH=%BIST_DB_PATH% >> "%LOG_FILE%"
echo -------------------------------- >> "%LOG_FILE%"


REM -------------------------------
REM Environment
REM -------------------------------

call C:\Users\your-path\anaconda3\Scripts\activate.bat bist100

if errorlevel 1 (
    echo Conda activation failed >> "%LOG_FILE%"
    exit /b 1
)


cd /d "%PROJECT_DIR%"

if errorlevel 1 (
    echo Project directory not found >> "%LOG_FILE%"
    exit /b 1
)


REM -------------------------------
REM Run daily ingestion
REM -------------------------------

python -u src\bist_extractor\daily_ingest.py >> "%LOG_FILE%" 2>&1


set EXITCODE=%ERRORLEVEL%


echo -------------------------------- >> "%LOG_FILE%"
echo END %DATE% %TIME% >> "%LOG_FILE%"
echo EXIT_CODE=%EXITCODE% >> "%LOG_FILE%"


if not "%EXITCODE%"=="0" (
    echo JOB FAILED
    echo See log:
    echo %LOG_FILE%
    exit /b %EXITCODE%
)


echo JOB SUCCESS
echo Log:
echo %LOG_FILE%

endlocal & exit /b %EXITCODE%