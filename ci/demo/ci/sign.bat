@echo off
setlocal

REM Enforce the fixed drive so the signed image is identical everywhere.
if /I not "%~d0"=="X:" (
    echo [%~n0] ERROR: run from X: ^(subst^). Use ci\mount.bat first.
    exit /b 2
)

if not defined CYGWIN_ROOT set "CYGWIN_ROOT=C:\cygwin64"
set "PATH=%CYGWIN_ROOT%\bin;%PATH%"

set "ROOT_DIR=%~d0\"
for /f "usebackq delims=" %%i in (`cygpath -u "%ROOT_DIR%"`) do set "CYG=%%i"

echo [sign] signing out/tiboot3.raw -^> out/tiboot3.bin

REM All logic in bash so cat/openssl behave consistently. One logical line.
REM Real TI flow: gen_x509_cert.sh populates 1.3.6.1.4.1.294.* OIDs, then
REM prepends the signed cert to the raw image. This dummy reproduces the
REM prepend mechanic with a throwaway self-signed cert.
bash -c "cd '%CYG%' && if [ ! -f keys/custMpk.pem ]; then mkdir -p keys && openssl genpkey -algorithm RSA -out keys/custMpk.pem -pkeyopt rsa_keygen_bits:2048 -pkeyopt rsa_keygen_pubexp:65537; fi && openssl dgst -sha512 -binary out/tiboot3.raw > out/tiboot3.sha512 && openssl req -new -x509 -sha512 -key keys/custMpk.pem -config ci/x509template.txt -days 36500 -out out/cert.der -outform DER && cat out/cert.der out/tiboot3.raw > out/tiboot3.bin && echo '[sign] cert subject:' && openssl x509 -in out/cert.der -inform DER -noout -subject && ls -l out/tiboot3.bin"
exit /b %ERRORLEVEL%
