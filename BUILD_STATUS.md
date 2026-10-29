# TNxIDM v1.1 — Build Status (honest)

## What changed in v1.1
- Browser extension (Chrome/Edge, Manifest V3, 100% original code) in
  `browser-extension/`: auto-intercepts downloads of common file types,
  cancels the browser's own download, sends the URL to TNxIDM; popup with
  on/off toggles and a connection test; options page for the extension list;
  right-click any link > "Download with TNxIDM".
- New localhost bridge in the TNxIDM app (`tnxidm/bridge.py`, stdlib only):
  the GUI serves 127.0.0.1:8765 (tries 8765-8769), the extension POSTs to
  /add, /ping answers for the popup's connection test. Loopback only.
- GUI picks up bridge items on the Qt thread, creates the download with the
  page's Referer/User-Agent, auto-starts per queue rules, tray notification.
- Settings: "Browser extension bridge" toggle + bridge port (restart needed).
- Release zip now bundles the `browser-extension` folder next to `TNxIDM/`.

## Tested and passing on this Linux VM
- `python3 main.py --self-test` — PASS, exit 0 (unchanged engine).
- Bridge self-test (`tnxidm/bridge.py::self_test`) — PASS: ping ok, /add ok,
  ftp:// and oversized URLs rejected with 400, bad JSON rejected.
- GUI + bridge integration (offscreen Qt) — PASS: MainWindow starts the
  bridge on 127.0.0.1:8765, a simulated extension POST /add returns
  {"ok": true}, and the GUI creates the download task from the queue.
- Extension files: manifest.json valid JSON; background.js, popup.js,
  options.js pass `node --check`; icons present (16/48/128 PNG, original).
- `python3 -m py_compile main.py tnxidm/*.py` — PASS.
- i18n check: 65/65 keys present in both বাংলা and English.
- Windows build (GitHub Actions, windows-latest): full workflow including
  console `--self-test` AND the bridge self-test must pass before packaging;
  release v1.1 publishes TNxIDM-PC-Windows-v1.1.zip + TNxIDM-Setup-v1.1.exe.

## Honest v1.1 limits (also in README)
- The extension needs TNxIDM running (tray counts). If TNxIDM is closed,
  the extension cannot reach it and the popup test says "not connected".
- Chrome/Edge only in v1.1; Firefox is untested with this extension.
- Extension is loaded unpacked via chrome://extensions > Developer mode
  (no Chrome Web Store listing in v1.1).
- Direct file links only — YouTube/streaming downloading is not supported.
- No-Range servers: pause/resume restarts that single-connection file.
- Apple-style real-time refraction is not possible in Qt; the UI is an
  RGBA/shadow/gradient approximation.
- All code in this project is original; no proprietary IDM code, assets,
  icons or branding were copied or bundled.
