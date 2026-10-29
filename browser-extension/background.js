/* TNxIDM Browser Integration - background service worker (original code).
 * Intercepts browser downloads and hands them to the TNxIDM desktop app
 * through its localhost bridge (127.0.0.1). Nothing is uploaded anywhere;
 * the bridge only listens on loopback.
 */
"use strict";

const PORTS = [8765, 8766, 8767, 8768, 8769];
const DEFAULTS = {
  enabled: true,
  interceptAll: false,
  exts: "zip rar 7z tar gz bz2 xz exe msi apk dmg pkg mp4 mkv webm avi mov mp3 wav flac ogg m4a pdf epub doc docx xls xlsx ppt pptx txt csv jpg jpeg png gif webp bmp svg ico iso bin dat"
};

async function getCfg() {
  return await chrome.storage.sync.get(DEFAULTS);
}

/* Try each bridge port in turn. Returns the parsed JSON or throws. */
async function bridge(path, body) {
  let lastErr = null;
  for (const p of PORTS) {
    try {
      const res = await fetch(`http://127.0.0.1:${p}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {})
      });
      if (res.ok) return await res.json();
      lastErr = new Error("bridge error " + res.status);
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error("TNxIDM is not running");
}

async function bridgePing() {
  for (const p of PORTS) {
    try {
      const res = await fetch(`http://127.0.0.1:${p}/ping`, { method: "GET" });
      if (res.ok) return await res.json();
    } catch (e) { /* try next port */ }
  }
  throw new Error("TNxIDM is not running");
}

function extOf(name) {
  const clean = (name || "").split("?")[0].split("#")[0];
  const i = clean.lastIndexOf(".");
  return i > 0 ? clean.slice(i + 1).toLowerCase() : "";
}

async function maybeIntercept(item) {
  const cfg = await getCfg();
  if (!cfg.enabled) return;
  const url = item.url || "";
  if (!/^https?:\/\//i.test(url)) return;
  if (!cfg.interceptAll) {
    const list = (cfg.exts || "").split(/\s+/).filter(Boolean);
    const ext = extOf(item.filename || url);
    if (!list.includes(ext)) return;
  }
  // Take over the download: cancel the browser's own download first.
  try { await chrome.downloads.cancel(item.id); } catch (e) { /* already gone */ }
  try { await chrome.downloads.erase({ id: item.id }); } catch (e) { /* ignore */ }
  const filename = (item.filename || "").split(/[\\/]/).pop() || "";
  try {
    await bridge("/add", {
      url,
      filename,
      referrer: item.referrer || "",
      user_agent: navigator.userAgent || "",
      page_url: ""
    });
  } catch (e) {
    console.warn("[TNxIDM] bridge unreachable:", e.message);
  }
}

chrome.downloads.onCreated.addListener((item) => {
  maybeIntercept(item).catch((e) => console.warn("[TNxIDM]", e));
});

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.sync.get(DEFAULTS, (cur) => {
    const missing = {};
    for (const k of Object.keys(DEFAULTS)) {
      if (!(k in cur)) missing[k] = DEFAULTS[k];
    }
    if (Object.keys(missing).length) chrome.storage.sync.set(missing);
  });
  chrome.contextMenus.create({
    id: "tnxidm-send",
    title: "Download with TNxIDM",
    contexts: ["link"]
  });
});

chrome.contextMenus.onClicked.addListener((info) => {
  if (info.menuItemId !== "tnxidm-send" || !info.linkUrl) return;
  getCfg().then((cfg) => {
    if (!cfg.enabled) return;
    return bridge("/add", {
      url: info.linkUrl,
      filename: "",
      referrer: "",
      user_agent: navigator.userAgent || "",
      page_url: info.pageUrl || ""
    });
  }).catch((e) => console.warn("[TNxIDM]", e.message));
});

// Popup asks for these via messages.
chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (msg && msg.type === "tnxidm-ping") {
    bridgePing().then((r) => reply({ ok: true, version: r.version }))
                  .catch((e) => reply({ ok: false, error: e.message }));
    return true;
  }
  if (msg && msg.type === "tnxidm-get") {
    getCfg().then((cfg) => reply({ ok: true, cfg })).catch((e) => reply({ ok: false }));
    return true;
  }
  if (msg && msg.type === "tnxidm-set") {
    chrome.storage.sync.set(msg.cfg || {}, () => reply({ ok: true }));
    return true;
  }
});
