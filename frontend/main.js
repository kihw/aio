const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const yaml = require('js-yaml');

// Try to pick a suitable Python executable on all platforms
const PYTHON_BIN = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const RULES_DIR = path.join(__dirname, 'public', 'rules');

function createWindow() {
  const win = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      nodeIntegration: true
    }
  });

  win.loadFile(path.join(__dirname, 'public/index.html'));
}

let engineProcess = null;

ipcMain.on('run-rule', (event, ruleName) => {
  const script = path.join(__dirname, '../main/appflow.py');
  const child = spawn(PYTHON_BIN, [script, '--run', ruleName, '--rules-dir', RULES_DIR], {
    detached: true,
    stdio: 'ignore'
  });
  child.unref();
});

ipcMain.handle('start-engine', (event) => {
  if (engineProcess) {
    return;
  }
  const script = path.join(__dirname, '../main/appflow.py');
  engineProcess = spawn(PYTHON_BIN, [
    script,
    '--log',
    path.join(__dirname, '../appflow.log'),
    '--rules-dir',
    RULES_DIR,
  ]);
  engineProcess.on('exit', () => {
    engineProcess = null;
    event.sender.send('engine-status-changed', false);
  });
  event.sender.send('engine-status-changed', true);
});

ipcMain.handle('stop-engine', (event) => {
  if (engineProcess) {
    engineProcess.kill();
    engineProcess = null;
  }
  event.sender.send('engine-status-changed', false);
});

ipcMain.handle('engine-status', () => {
  return Boolean(engineProcess);
});

ipcMain.on('save-rule', (event, rule) => {
  const rulesDir = path.join(__dirname, '../rules');
  const file = path.join(rulesDir, 'custom.yaml');
  let data = [];
  if (fs.existsSync(file)) {
    try {
      const content = fs.readFileSync(file, 'utf8');
      const parsed = yaml.load(content);
      if (Array.isArray(parsed)) data = parsed;
    } catch (e) {
      // ignore
    }
  }
  data.push(rule);
  fs.writeFileSync(file, yaml.dump(data), 'utf8');
  event.sender.send('rule-saved');
});

app.whenReady().then(createWindow);
