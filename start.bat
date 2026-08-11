@echo off
setlocal EnableExtensions

cd /d "%~dp0"

title LLM Gateways - Development Stack

echo.
echo ============================================================
echo               LLM GATEWAYS DEVELOPMENT STACK
echo ============================================================
echo.

REM ------------------------------------------------------------
REM Configuration
REM ------------------------------------------------------------

set "PROJECT_ROOT=%~dp0"
set "PYTHON_EXE=%PROJECT_ROOT%.venv\Scripts\python.exe"

REM ------------------------------------------------------------
REM Validate Python environment
REM ------------------------------------------------------------

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python virtual environment not found.
    echo.
    echo Expected:
    echo %PYTHON_EXE%
    echo.
    echo Create it with:
    echo.
    echo     uv venv --python 3.13
    echo     uv sync
    echo.
    pause
    exit /b 1
)

echo [DEV] Project root:
echo       %PROJECT_ROOT%

echo.
echo [DEV] Python:
"%PYTHON_EXE%" --version

echo.
echo [DEV] Python executable:
echo       %PYTHON_EXE%

echo.
echo [DEV] Starting complete application...
echo.

REM ------------------------------------------------------------
REM Start development orchestrator
REM ------------------------------------------------------------

"%PYTHON_EXE%" "%PROJECT_ROOT%scripts\dev.py"

set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo ============================================================
echo               LLM GATEWAYS STACK STOPPED
echo ============================================================
echo.
echo Exit code: %EXIT_CODE%
echo.

pause

exit /b %EXIT_CODE%