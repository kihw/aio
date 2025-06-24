#!/bin/bash
# Script de développement pour Unix/Linux/macOS

# Couleurs pour la sortie terminal
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages avec couleurs
function log {
  case "$1" in
    "info")
      echo -e "${BLUE}[INFO]${NC} $2"
      ;;
    "success")
      echo -e "${GREEN}[SUCCESS]${NC} $2"
      ;;
    "warning")
      echo -e "${YELLOW}[WARNING]${NC} $2"
      ;;
    "error")
      echo -e "${RED}[ERROR]${NC} $2"
      ;;
    *)
      echo "$2"
      ;;
  esac
}

# Vérifier si Python est installé
if ! command -v python3 &> /dev/null; then
  log "error" "Python 3 n'est pas installé. Veuillez l'installer avant de continuer."
  exit 1
fi

# Vérifier si Node.js est installé
if ! command -v node &> /dev/null; then
  log "error" "Node.js n'est pas installé. Veuillez l'installer avant de continuer."
  exit 1
fi

# Vérifier si npm est installé
if ! command -v npm &> /dev/null; then
  log "error" "npm n'est pas installé. Veuillez l'installer avant de continuer."
  exit 1
fi

# Répertoire racine du projet
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/main"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Fonction pour installer les dépendances Python
function setup_python {
  log "info" "Installation des dépendances Python..."
  
  # Créer un environnement virtuel s'il n'existe pas
  if [ ! -d "$PROJECT_ROOT/venv" ]; then
    log "info" "Création de l'environnement virtuel Python..."
    python3 -m venv "$PROJECT_ROOT/venv"
  fi
  
  # Activer l'environnement virtuel
  source "$PROJECT_ROOT/venv/bin/activate"
  
  # Installer les dépendances
  pip install -r "$BACKEND_DIR/requirements.txt"
  
  if [ $? -eq 0 ]; then
    log "success" "Dépendances Python installées avec succès."
  else
    log "error" "Erreur lors de l'installation des dépendances Python."
    exit 1
  fi
}

# Fonction pour installer les dépendances Node.js
function setup_node {
  log "info" "Installation des dépendances Node.js..."
  
  cd "$FRONTEND_DIR" || exit
  npm install
  
  if [ $? -eq 0 ]; then
    log "success" "Dépendances Node.js installées avec succès."
  else
    log "error" "Erreur lors de l'installation des dépendances Node.js."
    exit 1
  fi
  
  cd "$PROJECT_ROOT" || exit
}

# Fonction pour démarrer le backend
function start_backend {
  log "info" "Démarrage du backend Python..."
  
  # Activer l'environnement virtuel
  source "$PROJECT_ROOT/venv/bin/activate"
  
  # Démarrer le serveur Flask en arrière-plan
  python "$BACKEND_DIR/appflow.py" --server --debug &
  BACKEND_PID=$!
  
  log "success" "Backend démarré (PID: $BACKEND_PID)"
}

# Fonction pour démarrer le frontend
function start_frontend {
  log "info" "Démarrage du frontend Electron/React..."
  
  cd "$FRONTEND_DIR" || exit
  npm run dev &
  FRONTEND_PID=$!
  
  log "success" "Frontend démarré (PID: $FRONTEND_PID)"
  
  cd "$PROJECT_ROOT" || exit
}

# Fonction pour nettoyer les processus à la sortie
function cleanup {
  log "info" "Arrêt des processus..."
  
  # Arrêter le frontend
  if [ -n "$FRONTEND_PID" ]; then
    kill $FRONTEND_PID 2>/dev/null
  fi
  
  # Arrêter le backend
  if [ -n "$BACKEND_PID" ]; then
    kill $BACKEND_PID 2>/dev/null
  fi
  
  log "success" "Processus arrêtés. Au revoir !"
  
  exit 0
}

# Enregistrer la fonction de nettoyage pour SIGINT et SIGTERM
trap cleanup SIGINT SIGTERM

# Fonction principale
function main {
  log "info" "====== AppFlow - Mode Développement ======"
  
  # Vérifier les arguments
  case "$1" in
    "--backend")
      setup_python
      start_backend
      ;;
    "--frontend")
      setup_node
      start_frontend
      ;;
    "--install")
      setup_python
      setup_node
      log "success" "Installation des dépendances terminée."
      exit 0
      ;;
    *)
      # Par défaut, démarrer le backend et le frontend
      setup_python
      setup_node
      start_backend
      start_frontend
      ;;
  esac
  
  log "info" "AppFlow est en cours d'exécution. Pressez Ctrl+C pour arrêter."
  
  # Attendre indéfiniment (jusqu'à SIGINT)
  while true; do
    sleep 1
  done
}

# Exécuter la fonction principale avec les arguments
main "$@"
