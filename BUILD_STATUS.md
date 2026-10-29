# TNxIDM v1.0 — Build Status (honest)

## Tested and passing on this Linux VM
- `python3 main.py --self-test` — PASS, exit 0
  - Local Range server, 8-segment download of a 4 MiB file
  - Paused mid-download, resumed from segment offsets, merged file verified
  - Original SHA-256: 2d7569d2fc780b8aa7b39656e98dd699aba5e103ef7677b6d890fc08b149e390
  - Merged   SHA-256: 2d7569d2fc780b8aa7b39656e98dd699aba5e103ef7677b6d890fc08b149e390
- No-Range fallback — PASS: server returning 200 with no Accept-Ranges
  downloaded cleanly as a single connection, SHA-256 matched.
- Queue-state JSON round-trip — PASS: segment offsets, total, filename preserved.
- `python3 -m py_compile main.py tnxidm/*.py` — PASS.
- Qt GUI smoke (offscreen, Linux) — PASS: MainWindow constructs, 4 tabs,
  default language বাংলা, tab titles ডাউনলোড/সম্পন্ন/গ্র্যাবার/সেটিংস.
  i18n check: 61/61 keys present in both বাংলা and English, no missing keys.
  A full visual Windows run (tray icon rendering, SmartScreen) still needs Windows.

## Not tested on Windows (honest limitation)
- The packaged Windows `.exe` was NOT built or run on this machine.
  This VM runs Linux; PyInstaller on Linux builds a Linux binary, not a
  Windows exe, and Wine here lacks wine32, so a genuine Windows Python +
  PyInstaller build could not be run here.
- Therefore the zip in this delivery contains the complete source,
  `requirements.txt`, `build.bat` and README — NOT a tested TNxIDM.exe.
  Run `build.bat` on Windows 10/11 with Python 3.12 to produce
  `dist/TNxIDM/TNxIDM.exe` and `TNxIDM-PC-Windows-v1.0.zip`, then run
  `TNxIDM.exe --self-test` on Windows to confirm PASS there.
- The Qt GUI was syntax-checked; a full visual run on Windows (tray,
  clipboard prompt, SmartScreen flow, Liquid Glass rendering) was not
  tested here and needs a Windows check.

## Honest v1.0 limits (also in README)
- Direct file links only — YouTube/streaming downloading is not supported.
- No browser extension in v1.0; clipboard monitoring is the integration.
- No-Range servers: pause/resume restarts that single-connection file,
  because the server cannot resume it. Segmented downloads resume from offsets.
- Apple-style real-time refraction is not possible in Qt; the UI is an
  RGBA/shadow/gradient approximation.
- All code in this project is original; no proprietary IDM code, assets,
  icons or branding were copied or bundled.
