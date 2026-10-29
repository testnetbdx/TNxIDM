"use strict";
const $ = (id) => document.getElementById(id);

chrome.runtime.sendMessage({ type: "tnxidm-get" }, (res) => {
  if (res && res.ok) $("exts").value = res.cfg.exts || "";
});

$("save").addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "tnxidm-set",
    cfg: { exts: $("exts").value.trim().toLowerCase() } }, () => {
    $("msg").textContent = "Saved.";
    setTimeout(() => { $("msg").textContent = ""; }, 1500);
  });
});
