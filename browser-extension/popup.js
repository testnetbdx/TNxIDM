"use strict";
const $ = (id) => document.getElementById(id);

chrome.runtime.sendMessage({ type: "tnxidm-get" }, (res) => {
  if (res && res.ok) {
    $("enabled").checked = !!res.cfg.enabled;
    $("interceptAll").checked = !!res.cfg.interceptAll;
  }
});

function save() {
  chrome.runtime.sendMessage({ type: "tnxidm-set",
    cfg: { enabled: $("enabled").checked, interceptAll: $("interceptAll").checked } });
}
$("enabled").addEventListener("change", save);
$("interceptAll").addEventListener("change", save);

$("test").addEventListener("click", () => {
  const st = $("status");
  st.className = "";
  st.textContent = "Testing...";
  chrome.runtime.sendMessage({ type: "tnxidm-ping" }, (res) => {
    if (res && res.ok) {
      st.className = "ok";
      st.textContent = "Connected to TNxIDM v" + (res.version || "?");
    } else {
      st.className = "bad";
      st.textContent = "Not connected: " + ((res && res.error) || "unknown") +
        ". Start TNxIDM first.";
    }
  });
});

$("opts").addEventListener("click", (e) => {
  e.preventDefault();
  chrome.runtime.openOptionsPage();
});
