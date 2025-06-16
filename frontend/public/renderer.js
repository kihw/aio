const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

function loadRules() {
  const rulesDir = path.resolve(__dirname, '../../rules');
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
    li.textContent = r.name || 'Unnamed rule';
    list.appendChild(li);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const rules = loadRules();
  renderRules(rules);
});
