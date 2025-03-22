@echo off
setlocal enabledelayedexpansion

:: ANSI support.
chcp 65001 > nul

:: Options
set REQUIRE_VENV=1

:: ANSI Color Codes
set "ESC="
set "RESET=%ESC%[0m"
set "YELLOW=%ESC%[33m"
set "RED=%ESC%[31m"
set "CYAN=%ESC%[36m"
set "GREEN=%ESC%[32m"

:: Setup paths
set "ROOT_DIR=%cd%\.."

:: Detect virtual environment
set "VENV_PYTHON=%ROOT_DIR%\venv\Scripts\python.exe"
set REQUIRE_VENV_FLAG=

if exist "%VENV_PYTHON%" (
    echo %CYAN%[INFO]%RESET% Using virtual environment Python: %CYAN%%VENV_PYTHON%%RESET%
    set REQUIRE_VENV_FLAG=--require-virtualenv
) else (
    if "%REQUIRE_VENV%"=="1" (
        echo %RED%[ERROR]%RESET% Virtual environment not found.
        pause
        exit /b 1
    ) else (
        echo %YELLOW%[WARNING]%RESET% Virtual environment not found. Falling back to system Python.
        set VENV_PYTHON=python
    )
)

:: Check localizations
call :print_header "Checking localizations..."
cd "%ROOT_DIR%"
%VENV_PYTHON% "%ROOT_DIR%\tools\check_localizations.py" --batch
if errorlevel 1 (
    echo %RED%[ERROR]%RESET% Localizations are incomplete.
    pause
    exit /b %errorlevel%
)

call :mark_done

:: Build the project
cd "%ROOT_DIR%"
%VENV_PYTHON% "%ROOT_DIR%\tools\build.py"
if errorlevel 1 (
    echo %RED%[ERROR]%RESET% Project build failed.
    pause
    exit /b %errorlevel%
)
echo.

pause
exit /b 0

:print_header
    setlocal
    set "MESSAGE=%~1"

    :: Print header without newline
    <nul set /p="%CYAN%[INFO]%RESET% %MESSAGE%"
    endlocal & set "LAST_MESSAGE=%MESSAGE%"
    goto :eof

:mark_done
    :: Move to beginning of line, clear it, and reprint
    <nul set /p=[2K[0G%CYAN%[INFO]%RESET% %GREEN%[DONE] %LAST_MESSAGE%%RESET%
    echo.
    goto :eof