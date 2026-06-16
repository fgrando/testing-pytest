@echo off
setlocal

REM Enforce the fixed drive so dev and CI logs are byte-identical.
if /I not "%~d0"=="X:" (
    echo [build] ERROR: run from X: ^(subst^). Invoked from %~d0 . Use ci\mount.bat, then X:\ci\build.bat
    exit /b 2
)

if not defined CYGWIN_ROOT set "CYGWIN_ROOT=C:\cygwin64"
set "PATH=%CYGWIN_ROOT%\bin;%PATH%"

set "SCRIPT_DIR=%~dp0"
set "BUILD_DIR=%~d0\"
set "LOG_DIR=%BUILD_DIR%logs"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\build.log"

for /f "usebackq delims=" %%i in (`cygpath -u "%BUILD_DIR%"`) do set "CYG_BUILD=%%i"
for /f "usebackq delims=" %%i in (`cygpath -u "%LOG_FILE%"`) do set "CYG_LOG=%%i"

echo [build] logging to %LOG_FILE%

REM Path is a constant /cygdrive/x/... on every machine, so no normalization needed.
REM tee inside bash keeps console + file output; PIPESTATUS[0] preserves make's exit code.
bash -c "cd '%CYG_BUILD%' && { make clean && make all; } 2>&1 | tee '%CYG_LOG%'; exit ${PIPESTATUS[0]}"
exit /b %ERRORLEVEL%
