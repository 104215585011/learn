const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("floatVocab", {
  showFloatingCard: () => ipcRenderer.invoke("floating-card:show"),
  hideFloatingCard: () => ipcRenderer.invoke("floating-card:hide"),
  setFloatingCardAlwaysOnTop: (enabled) => ipcRenderer.invoke("floating-card:set-always-on-top", enabled),
  applyFloatingCardStyle: (style) => ipcRenderer.invoke("floating-card:apply-style", style),
  minimize: () => ipcRenderer.invoke("window:minimize"),
  toggleMaximize: () => ipcRenderer.invoke("window:toggle-maximize"),
  close: () => ipcRenderer.invoke("window:close"),
});
