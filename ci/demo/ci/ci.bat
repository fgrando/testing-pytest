@echo off
setlocal

REM Enforce the fixed drive so dev and CI do byte-identical work.
if /I not "%~d0"=="X:" (
    echo [%~n0] ERROR: run from X: ^(subst^). Invoked from %~d0 . Use ci\mount.bat first.
    exit /b 2
)

set "SCRIPT_DIR=%~dp0"

call "%SCRIPT_DIR%fetch_deps.bat"
if errorlevel 1 exit /b 1

call "%SCRIPT_DIR%build.bat"
if errorlevel 1 exit /b 1

call "%SCRIPT_DIR%sign.bat"
if errorlevel 1 exit /b 1

exit /b 0
