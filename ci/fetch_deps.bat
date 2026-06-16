@echo off
setlocal enabledelayedexpansion

REM Enforce the fixed drive so dependencies land at an identical path everywhere.
if /I not "%~d0"=="X:" (
    echo [%~n0] ERROR: run from X: ^(subst^). Invoked from %~d0 . Use ci\mount.bat first.
    exit /b 2
)

if not defined CYGWIN_ROOT set "CYGWIN_ROOT=C:\cygwin64"
set "PATH=%CYGWIN_ROOT%\bin;%PATH%"

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%~d0\"
set "MANIFEST=%SCRIPT_DIR%deps.txt"
set "DEPS_ROOT=%ROOT_DIR%deps"

if not exist "%MANIFEST%" (
    echo [fetch_deps] ERROR: manifest not found: %MANIFEST%
    exit /b 1
)

echo [fetch_deps] cleaning %DEPS_ROOT%
if exist "%DEPS_ROOT%" rmdir /s /q "%DEPS_ROOT%"

for /f "usebackq tokens=1-4 delims=|" %%a in ("%MANIFEST%") do (
    set "name=%%a"
    set "url=%%b"
    set "rev=%%c"
    set "dest=%%d"

    REM skip comment lines
    if not "!name:~0,1!"=="#" (
        echo [fetch_deps] !name!  rev !rev!  -^> !dest!
        svn export --non-interactive -r !rev! "!url!" "%ROOT_DIR%!dest!"
        if errorlevel 1 (
            echo [fetch_deps] ERROR exporting !name!
            exit /b 1
        )
    )
)

echo [fetch_deps] done
exit /b 0