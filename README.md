
# 🔄 AppFlow – Gestionnaire intelligent de lancement et d’arrêt d'applications

**AppFlow** est un gestionnaire d'applications intelligent pour Windows/Linux/MacOS. Il vous permet d'automatiser le lancement et l'arrêt de vos logiciels selon des règles définies, des workflows ou des scénarios personnalisés.

---

## 🧠 Fonctionnalités

- Création de **règles intelligentes** basées sur :
  - Heure, jour, batterie, activité réseau, ou lancement d'autres apps
- Détection et gestion des processus système
- Interface utilisateur en **Electron**
- Support des **profils d’usage** (travail, gaming, repos, etc.)
- Historique et logs d'exécution

---

## 🧱 Architecture du projet

```

appflow/
├── main/                   # Backend principal (Python)
│   ├── core/               # Gestion des règles, exécution des actions
│   ├── utils/              # Fonctions système, process, logs
│   └── appflow\.py          # Entrée principale du backend
│
├── frontend/               # Interface Electron
│   ├── public/             # Fichiers statiques
│   ├── src/                # App React/Vue/Svelte (selon choix)
│   └── main.js             # Processus principal Electron
│
├── rules/                  # Fichiers YAML de règles utilisateur
│   └── default.yaml
│
├── assets/                 # Icônes, images
├── README.md
└── package.json            # Config Electron

````

---

## 🚀 Développement local

### 1. Prérequis

- **Node.js** et **npm** (pour Electron)
- **Python 3.10+**
- Pipenv ou virtualenv recommandé pour l’environnement Python

---

### 2. Installer le backend Python

```bash
cd main
pip install -r requirements.txt
````

> Dépendances clés : `psutil`, `pyyaml`, `schedule`, `flask` (si API utilisée)

---

### 3. Installer l’interface Electron

```bash
cd frontend
npm install
npm run dev
```

L'interface est une app Electron avec React (ou Vue/Svelte selon choix). Elle communique avec le backend Python via :

* une API Flask locale
* ou une communication IPC via Node bindings (ex: `python-shell`, `zerorpc`, `child_process`)

---

## 🧪 Exemple de règle YAML

```yaml
- name: Dev Workflow
  triggers:
    - app_start: "code.exe"
  actions:
    - launch: "localhost_server.bat"
    - launch: "spotify.exe"
    - wait: 5
    - kill: "discord.exe"
```

---

## 🧰 Scripts de développement

| Commande                | Description                              |
| ----------------------- | ---------------------------------------- |
| `npm run dev`           | Lance l’interface Electron en mode dev   |
| `python appflow.py`     | Lance le backend Python                  |
| `npm run build`         | Build l’interface pour prod              |
| `npm run electron-pack` | Créer un exécutable desktop avec Electron |
| `python appflow.py --list` | Affiche les règles disponibles |
| `python appflow.py --run "Nom"` | Exécute une règle précise |

---

## 📦 Build & Distribution

Le projet peut être packagé en une seule application via :

* [`electron-builder`](https://www.electron.build/)
* ou [`pyinstaller`](https://pyinstaller.org/) pour le backend

### Exemple de packaging multiplateforme :

```bash
npm run build
pyinstaller --onefile appflow.py
electron-builder --win --x64
```

---

## ✅ À venir

* Interface drag & drop pour créer les règles
* Suggestions intelligentes de workflows
* Intégration avec les services cloud (OneDrive, Dropbox)

---

## 📄 Licence

Projet sous licence MIT.

---

## 👨‍💻 Contribuer

Les contributions sont les bienvenues ! Forkez, proposez une PR ou ouvrez une issue 🚀

