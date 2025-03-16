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
set "PYINSTALLER_DIR=%ROOT_DIR%\..\pyinstaller" & :: PyInstaller repository path.
set "BOOTLOADER_DIR=%PYINSTALLER_DIR%\bootloader"
set "VOX_DIR=%ROOT_DIR%"

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

:: Update pip
call :print_header "Updating pip..."
%VENV_PYTHON% -m pip install --upgrade pip %REQUIRE_VENV_FLAG% > NUL
if errorlevel 1 (
    echo %RED%[ERROR]%RESET% Pip upgrade failed!
    pause
    exit /b %errorlevel%
)

call :mark_done

:: Uninstall existing pyinstaller
call :print_header "Uninstalling PyInstaller..."
%VENV_PYTHON% -m pip uninstall pyinstaller --yes %REQUIRE_VENV_FLAG% > NUL

call :mark_done

:: Build PyInstaller bootloader
call :print_header "Building PyInstaller Bootloader..."
cd "%BOOTLOADER_DIR%"
%VENV_PYTHON% waf all > NUL
if errorlevel 1 (
    echo %RED%[ERROR]%RESET% Bootloader build failed!
    pause
    exit /b %errorlevel%
)

call :mark_done

cd "%PYINSTALLER_DIR%"

:: Install freshly built PyInstaller
call :print_header "Installing Freshly Built PyInstaller..."
%VENV_PYTHON% -m pip install . %REQUIRE_VENV_FLAG% > NUL
if errorlevel 1 (
    echo %RED%[ERROR]%RESET% Installing PyInstaller failed!
    pause
    exit /b %errorlevel%
)

call :mark_done

:: Build the project
cd "%VOX_DIR%"
%VENV_PYTHON% "%VOX_DIR%\tools\build.py"
if errorlevel 1 (
    echo %RED%[ERROR]%RESET% Project build failed!
    pause
    exit /b %errorlevel%
)

pause
exit /b 0

:print_header
    setlocal
    set "MESSAGE=%~1"

    :: Print without newline
    <nul set /p="%CYAN%[INFO]%RESET% %MESSAGE%"
    endlocal & set "LAST_MESSAGE=%MESSAGE%"
    goto :eof

:mark_done
    echo [2K[0G%CYAN%[INFO]%RESET% %GREEN%[DONE] %LAST_MESSAGE%%RESET%
    goto :eof