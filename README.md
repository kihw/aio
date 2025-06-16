
# 🔄 AppFlow – Gestionnaire intelligent de lancement et d’arrêt d'applications

**AppFlow** est un gestionnaire d'applications intelligent pour Windows/Linux/MacOS. Il vous permet d'automatiser le lancement et l'arrêt de vos logiciels selon des règles définies, des workflows ou des scénarios personnalisés.

---

## 🧠 Fonctionnalités

- Création de **règles intelligentes** basées sur :
  - Heure, jour, batterie, **usage CPU**, **trafic réseau**, ou lancement d'autres apps
- Détection et gestion des processus système
- Interface utilisateur en **Electron**
- Support des **profils d’usage** (travail, gaming, repos, etc.)
- Historique et logs d'exécution
- Consultation des logs dans l'interface (rafraîchissement auto)
- Lancement manuel des règles depuis l'interface
- Démarrage et arrêt du moteur depuis l'interface
- Affichage de l'état du moteur dans l'interface
- Rafraîchissement de la liste des règles depuis l'interface

---

## 🧱 Architecture du projet

```

appflow/
├── main/                   # Backend principal (Python)
│   ├── core/               # Gestion des règles, exécution des actions
│   ├── utils/              # Fonctions système, process, logs
│   └── appflow.py          # Entrée principale du backend
│
├── frontend/               # Interface Electron
│   ├── public/
│   │   ├── rules/          # Fichiers YAML de règles utilisateur
│   │   │   └── default.yaml
│   │   └── index.html
│   ├── src/                # App React/Vue/Svelte (selon choix)
│   └── main.js             # Processus principal Electron
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

Une fois l'application Electron lancée, cliquez sur une règle pour l'exécuter manuellement.
Utilisez les boutons **Démarrer** et **Arrêter** pour contrôler le moteur.
La zone de logs se met à jour automatiquement, et le bouton "Actualiser la liste" permet de recharger les règles depuis les fichiers YAML.

---

### Variables d'environnement utiles

- `APPFLOW_RULES_DIR` : chemin vers le répertoire de règles par défaut.

---

## 🧪 Exemple de règle YAML

```yaml
- name: Dev Workflow
  triggers:
    - app_start: "code.exe"
    - battery_below: 20
    - cpu_above: 80
    - network_above: 100
    - at_time: "22:00"
  actions:
    - launch: "localhost_server.bat"
    - wait: 5
    - notify: "Server launched"
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
| `python appflow.py --log appflow.log` | Enregistre l'exécution dans un fichier |
| `python appflow.py --profile work` | Charge aussi `default.yaml` puis les fichiers du profil `work` (alias `-p`) |
| `python appflow.py --rules-dir ~/my_rules` | Charge les règles depuis un répertoire personnalisé (alias `-d`) |
| `python appflow.py --interval 5` | Définit l'intervalle de polling en secondes (alias `-i`) |
| `python appflow.py --once` | Exécute les règles une seule fois puis quitte (alias `-1`) |

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

