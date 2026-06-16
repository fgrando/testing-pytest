@echo off
REM Map a checkout root to X: so dev and CI build from identical paths.
setlocal
if not defined WORK_DRIVE set "WORK_DRIVE=X:"
set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=%CD%"

subst %WORK_DRIVE% /D >nul 2>&1
subst %WORK_DRIVE% "%TARGET%"
if errorlevel 1 (
    echo [mount] ERROR: subst %WORK_DRIVE% "%TARGET%" failed
    exit /b 1
)
echo [mount] %WORK_DRIVE% -^> %TARGET%
exit /b 0