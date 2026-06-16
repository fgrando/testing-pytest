# tiboot3 signing demo

A self-contained version of the CI pipeline: mount a fixed drive, build a
dummy "first-stage bootloader" from `main.c`, write a deterministic build log,
and sign it with a dummy certificate using the same prepend-cert-to-binary
mechanic that TI K3 / Jacinto secure boot uses.

Runs entirely on your Windows PC. No SVN, no network, no TI SDK required.

## Prerequisites

Cygwin (assumed at `C:\cygwin64`) with these packages:
`gcc-core`, `make`, `openssl`, `coreutils` (for `cat`/`tee`), `cygutils`.

If Cygwin is elsewhere, set `CYGWIN_ROOT` before running, e.g.
`set CYGWIN_ROOT=D:\cygwin64`.

## Run it

Open `cmd.exe`, then:

    cd C:\path\to\demo
    ci\mount.bat            REM maps this folder to X:
    X:\ci\ci.bat            REM fetch_deps (no-op) -> build -> sign

Outputs:

    X:\out\tiboot3.raw      compiled image (unsigned)
    X:\out\cert.der         dummy signing certificate
    X:\out\tiboot3.bin      signed image  = cert.der + tiboot3.raw
    X:\logs\build.log       deterministic build log

Inspect the cert straight from the front of the signed image (same as a real
tiboot3.bin):

    X:
    openssl x509 -in X:\out\tiboot3.bin -inform DER -text -noout

Clean up the drive mapping when done:

    subst X: /D

## Files

    Makefile            builds main.c -> out/tiboot3.raw
    main.c              dummy bootloader source
    keys/custMpk.pem    DUMMY signing key (throwaway — do NOT use in production)
    ci/mount.bat        subst <folder> -> X:   (bootstrap, no drive guard)
    ci/deps.txt         dependency manifest (all commented for the demo)
    ci/fetch_deps.bat   svn export of pinned deps (no-op here)
    ci/build.bat        make + deterministic, diff-able log
    ci/sign.bat         dummy cert sign (prepend cert to raw)
    ci/x509template.txt openssl cert config
    ci/ci.bat           single entry point: fetch_deps + build + sign

## Notes / honest caveats

- This is a DUMMY. The cert has none of the TI OID extensions
  (`1.3.6.1.4.1.294.*` image-integrity hash, boot core, load address) that
  ROM actually checks, so the result will NOT boot on real hardware. For a
  bootable HS image, sign with your SDK's `gen_x509_cert.sh` +
  `k3_x509template.txt` and your own root-of-trust key.

- The signed image is NOT byte-reproducible as shipped: `openssl req -x509`
  stamps `notBefore`/`notAfter` with the current time and a random serial.
  To make `tiboot3.bin` diff-clean across runs/machines, pin them in
  `ci/sign.bat` (OpenSSL >= 3.2):

      -set_serial 1 -not_before 20250101000000Z -not_after 20990101000000Z

  Keep PKCS#1 v1.5 (the default) rather than PSS — PSS padding is randomized.
  On older OpenSSL without the date flags, run the openssl call under
  `faketime`, or just diff the unsigned `tiboot3.raw` instead.

- `keys/custMpk.pem` is a 2048-bit throwaway included so the demo runs out of
  the box. Real keys are 4096-bit and live on the node/HSM, never in SVN.
