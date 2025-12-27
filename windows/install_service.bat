@echo off
setlocal

set SERVICE_NAME=SingboxCrawler
set "BASE_DIR=%~dp0"
:: Remove trailing backslash
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"

:: Try to find Python
set "PYTHON_EXE=python.exe"
:: Check if venv exists
if exist "%BASE_DIR%\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%BASE_DIR%\venv\Scripts\python.exe"
)

set "SCRIPT_PATH=%BASE_DIR%\service_launcher.py"

echo Installing Service: %SERVICE_NAME%
echo Python Path: %PYTHON_EXE%
echo Script Path: %SCRIPT_PATH%

:: Create Service
nssm install %SERVICE_NAME% "%PYTHON_EXE%" "%SCRIPT_PATH%"
if %errorlevel% neq 0 (
    echo Failed to install service. Run as Administrator.
    pause
    exit /b %errorlevel%
)

:: Basic Configuration
nssm set %SERVICE_NAME% AppDirectory "%BASE_DIR%"
nssm set %SERVICE_NAME% Description "Singbox 7x24 Resource Crawler Service"
nssm set %SERVICE_NAME% Start SERVICE_AUTO_START

:: Logging (NSSM's own log of the stdout/stderr)
if not exist "%BASE_DIR%\logs" mkdir "%BASE_DIR%\logs"
nssm set %SERVICE_NAME% AppStdout "%BASE_DIR%\logs\service.log"
nssm set %SERVICE_NAME% AppStderr "%BASE_DIR%\logs\service_error.log"
nssm set %SERVICE_NAME% AppRotateFiles 1
nssm set %SERVICE_NAME% AppRotateOnline 1
nssm set %SERVICE_NAME% AppRotateSeconds 86400
nssm set %SERVICE_NAME% AppRotateBytes 104857600

:: Restart Policy
:: Delay 30 seconds (30000ms) before restarting if it crashes
nssm set %SERVICE_NAME% AppThrottle 30000

:: Performance (Priority)
nssm set %SERVICE_NAME% AppPriority BELOW_NORMAL_PRIORITY_CLASS

echo.
echo Service installed successfully!
echo To start the service, run: nssm start %SERVICE_NAME%
echo To stop the service, run: nssm stop %SERVICE_NAME%
echo.
pause
