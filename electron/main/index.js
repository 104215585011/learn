import { app, BrowserWindow, ipcMain, Menu, screen } from "electron";
import { spawn } from "node:child_process";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import Store from "electron-store";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const electronRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(electronRoot, "..");
const isDev = !app.isPackaged;

let mainWindow;
let floatingWindow;
let apiProcess;
let store;

function settingsStore() {
  if (!store) {
    store = new Store();
  }
  return store;
}

function pythonCommand() {
  if (process.env.FLOATVOCAB_PYTHON) {
    return process.env.FLOATVOCAB_PYTHON;
  }
  return process.platform === "win32" ? "python" : "python3";
}

function startApiProcess() {
  if (apiProcess) {
    return;
  }
  apiProcess = spawn(
    pythonCommand(),
    ["-m", "uvicorn", "floatvocab.api.main:app", "--host", "127.0.0.1", "--port", "8000"],
    {
      cwd: repoRoot,
      stdio: "inherit",
      env: {
        ...process.env,
        PYTHONPATH: repoRoot,
      },
      windowsHide: true,
    },
  );
  apiProcess.on("exit", () => {
    apiProcess = undefined;
  });
}

function checkApiHealth() {
  return new Promise((resolve, reject) => {
    const request = http.get("http://127.0.0.1:8000/health", (response) => {
      response.resume();
      if (response.statusCode === 200) {
        resolve();
        return;
      }
      reject(new Error(`FastAPI health check returned ${response.statusCode}`));
    });
    request.setTimeout(800, () => {
      request.destroy(new Error("FastAPI health check timed out"));
    });
    request.on("error", reject);
  });
}

async function waitForApiReady(timeoutMs = 15000) {
  const startedAt = Date.now();
  let lastError;
  while (Date.now() - startedAt < timeoutMs) {
    try {
      await checkApiHealth();
      return;
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 300));
    }
  }
  throw lastError || new Error("FastAPI did not become ready");
}

function rendererUrl(route = "") {
  if (isDev) {
    return `http://127.0.0.1:5173${route}`;
  }
  return `file://${path.join(electronRoot, "dist", "index.html")}${route}`;
}

function savedFloatingPosition() {
  const fallback = { x: 100, y: 100 };
  const saved = settingsStore().get("floatWin.position", fallback);
  if (!Number.isInteger(saved?.x) || !Number.isInteger(saved?.y)) {
    return fallback;
  }
  const isOnScreen = screen.getAllDisplays().some(({ workArea }) => (
    saved.x >= workArea.x - 320
    && saved.x <= workArea.x + workArea.width - 40
    && saved.y >= workArea.y - 320
    && saved.y <= workArea.y + workArea.height - 40
  ));
  if (!isOnScreen) {
    return fallback;
  }
  return { x: saved.x, y: saved.y };
}

function saveFloatingPosition() {
  if (!floatingWindow || floatingWindow.isDestroyed()) {
    return;
  }
  const [x, y] = floatingWindow.getPosition();
  settingsStore().set("floatWin.position", { x, y });
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 760,
    minWidth: 980,
    minHeight: 640,
    title: "FloatVocab",
    frame: false,
    titleBarStyle: "hidden",
    backgroundColor: "#F8F9FB",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.on("closed", () => {
    mainWindow = undefined;
  });
  mainWindow.loadURL(rendererUrl());
}

function createFloatingWindow() {
  if (floatingWindow && !floatingWindow.isDestroyed()) {
    return floatingWindow;
  }
  const position = savedFloatingPosition();
  floatingWindow = new BrowserWindow({
    x: position.x,
    y: position.y,
    width: 360,
    height: 360,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: true,
    minWidth: 300,
    minHeight: 320,
    skipTaskbar: true,
    show: false,
    backgroundColor: "#00000000",
    vibrancy: "under-window",
    backgroundMaterial: "acrylic",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  floatingWindow.on("move", saveFloatingPosition);
  floatingWindow.on("close", saveFloatingPosition);
  floatingWindow.on("closed", () => {
    floatingWindow = undefined;
  });
  floatingWindow.webContents.on("before-input-event", (event, input) => {
    if (input.key === "Escape") {
      floatingWindow?.hide();
      event.preventDefault();
    }
  });
  floatingWindow.loadURL(rendererUrl("#/floating-card"));
  return floatingWindow;
}

app.whenReady().then(async () => {
  Menu.setApplicationMenu(null);
  startApiProcess();
  try {
    await waitForApiReady();
  } catch (error) {
    console.error("[FloatVocab] FastAPI failed to become ready:", error);
  }
  createMainWindow();
  createFloatingWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
      createFloatingWindow();
    }
  });
});

ipcMain.handle("floating-card:show", () => {
  const window = createFloatingWindow();
  if (!window.isVisible()) {
    window.show();
  }
  window.setAlwaysOnTop(true);
  window.focus();
  return { ok: true };
});

ipcMain.handle("floating-card:hide", () => {
  floatingWindow?.hide();
});

ipcMain.handle("floating-card:set-always-on-top", (_event, enabled) => {
  floatingWindow?.setAlwaysOnTop(Boolean(enabled));
});

ipcMain.handle("floating-card:apply-style", (_event, style = {}) => {
  const window = createFloatingWindow();
  const opacity = Number(style.opacity ?? 0.95);
  const width = Number(style.width ?? 360);
  const height = Number(style.height ?? 360);
  window.setOpacity(Math.min(1, Math.max(0.35, opacity)));
  window.setMinimumSize(300, 320);
  window.setSize(
    Math.max(300, Math.round(width)),
    Math.max(320, Math.round(height)),
  );
  return { ok: true };
});

ipcMain.handle("window:minimize", () => {
  mainWindow?.minimize();
});

ipcMain.handle("window:toggle-maximize", () => {
  if (!mainWindow) {
    return;
  }
  if (mainWindow.isMaximized()) {
    mainWindow.unmaximize();
    return;
  }
  mainWindow.maximize();
});

ipcMain.handle("window:close", () => {
  mainWindow?.close();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  if (apiProcess) {
    apiProcess.kill();
    apiProcess = undefined;
  }
});
