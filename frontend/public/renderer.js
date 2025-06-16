const fs = require('fs');
const path = require('path');
const { ipcRenderer } = require('electron');
const yaml = require('js-yaml');

function loadRules() {
  const rulesDir = path.resolve(__dirname, 'rules');
  const files = fs.readdirSync(rulesDir).filter(f => f.endsWith('.yaml'));
  const rules = [];
  for (const file of files) {
    const content = fs.readFileSync(path.join(rulesDir, file), 'utf8');
    try {
      const data = yaml.load(content);
      if (Array.isArray(data)) {
        rules.push(...data);
      }
    } catch (err) {
      console.error('Failed to parse', file, err);
    }
  }
  return rules;
}

function renderRules(rules) {
  const list = document.getElementById('rules');
  if (!list) return;
  list.innerHTML = '';
  for (const r of rules) {
    const li = document.createElement('li');
    const btn = document.createElement('button');
    btn.textContent = r.name || 'Unnamed rule';
    btn.addEventListener('click', () => {
      if (r.name) {
        ipcRenderer.send('run-rule', r.name);
      }
    });
    li.appendChild(btn);
    list.appendChild(li);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  refreshRules();
  renderLog();
  setInterval(renderLog, 2000);
  setInterval(refreshRules, 5000);
  const logBtn = document.getElementById('refresh-log');
  if (logBtn) {
    logBtn.addEventListener('click', renderLog);
  }
  const rulesBtn = document.getElementById('refresh-rules');
  if (rulesBtn) {
    rulesBtn.addEventListener('click', refreshRules);
  }
  const startBtn = document.getElementById('start-engine');
  const stopBtn = document.getElementById('stop-engine');
  if (startBtn) {
    startBtn.addEventListener('click', () => ipcRenderer.invoke('start-engine'));
  }
  if (stopBtn) {
    stopBtn.addEventListener('click', () => ipcRenderer.invoke('stop-engine'));
  }
  ipcRenderer.invoke('engine-status').then(updateEngineButtons);
  ipcRenderer.on('engine-status-changed', (_e, running) => updateEngineButtons(running));
  initEditor();
});

function refreshRules() {
  const rules = loadRules();
  renderRules(rules);
}

function updateEngineButtons(running) {
  const startBtn = document.getElementById('start-engine');
  const stopBtn = document.getElementById('stop-engine');
  if (startBtn) startBtn.disabled = running;
  if (stopBtn) stopBtn.disabled = !running;
  const stateEl = document.getElementById('engine-state');
  if (stateEl) stateEl.textContent = running ? ' (en cours)' : ' (arrêté)';
}

function loadLog() {
  const logPath = path.resolve(__dirname, '../../appflow.log');
  if (!fs.existsSync(logPath)) {
    return '';
  }
  return fs.readFileSync(logPath, 'utf8');
}

function renderLog() {
  const pre = document.getElementById('log');
  if (!pre) return;
  pre.textContent = loadLog();
}

// ---- Drag & drop rule editor ----
let editorTriggers = [];
let editorActions = [];

function initEditor() {
  const builder = document.getElementById('rule-builder');
  if (!builder) return;

  builder.addEventListener('dragover', (e) => e.preventDefault());
  builder.addEventListener('drop', (e) => {
    e.preventDefault();
    const type = e.dataTransfer.getData('text/plain');
    if (!type) return;
    const value = prompt('Valeur pour ' + type + ':');
    if (value === null) return;
    const obj = {};
    obj[type] = type === 'wait' ? parseFloat(value) : value;
    if (['app_start','app_exit','at_time','battery_below','cpu_above','network_above'].includes(type)) {
      editorTriggers.push(obj);
    } else {
      editorActions.push(obj);
    }
    renderBuilder();
  });

  document.querySelectorAll('.draggable').forEach(el => {
    el.addEventListener('dragstart', (e) => {
      e.dataTransfer.setData('text/plain', el.dataset.type);
    });
  });

  const saveBtn = document.getElementById('save-rule');
  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      const name = document.getElementById('rule-name').value || 'New Rule';
      const rule = { name, triggers: editorTriggers, actions: editorActions };
      ipcRenderer.send('save-rule', rule);
    });
  }

  ipcRenderer.on('rule-saved', () => {
    editorTriggers = [];
    editorActions = [];
    document.getElementById('rule-name').value = '';
    renderBuilder();
    refreshRules();
  });

  renderBuilder();
}

function renderBuilder() {
  const builder = document.getElementById('rule-builder');
  if (!builder) return;
  const parts = [];
  if (editorTriggers.length) {
    parts.push('Triggers: ' + editorTriggers.map(t => JSON.stringify(t)).join(', '));
  }
  if (editorActions.length) {
    parts.push('Actions: ' + editorActions.map(a => JSON.stringify(a)).join(', '));
  }
  builder.textContent = parts.join('\n') || 'Glissez les éléments ici';
}
