"""
AppFlow - Gestionnaire intelligent d'applications
----------------------------------------------
Point d'entrée principal de l'application avec CLI args.
"""

import os
import sys
import logging
import argparse
import time
import signal
import threading
from typing import Dict, Any, Optional, List

# Ajouter le répertoire parent au chemin Python pour les imports relatifs
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import des modules AppFlow
from main.utils.logger import setup_logging
from main.utils.config_loader import ConfigLoader
from main.utils.process_manager import ProcessManager
from main.utils.system_monitor import SystemMonitor
from main.core.rule_engine import RuleEngine
from main.core.action_executor import ActionExecutor
from main.core.trigger_manager import TriggerManager

# Configuration du logger
logger = logging.getLogger(__name__)

class AppFlow:
    """
    Classe principale de l'application AppFlow.
    """
    
    def __init__(self):
        """
        Initialise l'application AppFlow.
        """
        self.app_name = "AppFlow"
        self.version = "0.1.0"
        self.running = False
        self.config_loader = None
        self.config = {}
        self.rule_engine = None
        self.action_executor = None
        self.process_manager = None
        self.system_monitor = None
        self.trigger_manager = None
        self.flask_server = None
        self.api_thread = None
    
    def initialize(self, config_dir: Optional[str] = None,
                 rules_dir: Optional[str] = None,
                 log_level: int = logging.INFO) -> None:
        """
        Initialise l'application avec les composants nécessaires.
        
        Args:
            config_dir: Répertoire de configuration
            rules_dir: Répertoire des règles
            log_level: Niveau de logging
        """
        try:
            # Setup du logger
            setup_logging(log_level=log_level)
            logger.info(f"Initialisation de {self.app_name} v{self.version}")
            
            # Chargement de la configuration
            self.config_loader = ConfigLoader(app_name=self.app_name)
            self.config_loader.set_directories(config_dir=config_dir, rules_dir=rules_dir)
            self.config = self.config_loader.load_config()
            
            # Création des composants core
            self.process_manager = ProcessManager()
            self.system_monitor = SystemMonitor()
            self.rule_engine = RuleEngine()
            self.action_executor = ActionExecutor()
            self.trigger_manager = TriggerManager()
            
            # Association des composants
            self.system_monitor.set_process_manager(self.process_manager)
            self.action_executor.set_process_manager(self.process_manager)
            self.rule_engine.set_action_executor(self.action_executor)
            self.trigger_manager.set_rule_engine(self.rule_engine)
            self.trigger_manager.set_system_monitor(self.system_monitor)
            
            # Enregistrement des fournisseurs de contexte
            self._register_context_providers()
            
            # Chargement des règles par défaut
            default_rules_file = self.config.get('engine', {}).get('default_rules_file', 'default.yaml')
            try:
                # Vérifier si le fichier de règles existe
                rules_path = os.path.join(self.config_loader.rules_dir, default_rules_file)
                if not os.path.exists(rules_path):
                    # Si le fichier n'existe pas, créer un exemple
                    self.config_loader.create_example_rules_file(rules_path)
                
                # Charger les règles
                rules_content = self.config_loader.load_rules_file(default_rules_file)
                self.rule_engine.load_rules_from_yaml(yaml.dump(rules_content))
                logger.info(f"Règles chargées depuis {default_rules_file}")
            except Exception as e:
                logger.error(f"Erreur lors du chargement des règles: {e}")
            
            logger.info("Initialisation terminée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation: {e}")
            return False
    
    def _register_context_providers(self) -> None:
        """
        Enregistre les fournisseurs de contexte pour le moteur de règles.
        """
        # Contexte CPU
        self.rule_engine.register_context_provider('cpu', 
            lambda: self.system_monitor.get_cpu_usage())
        
        # Contexte mémoire
        self.rule_engine.register_context_provider('memory',
            lambda: self.system_monitor.get_memory_usage())
        
        # Contexte batterie
        self.rule_engine.register_context_provider('battery',
            lambda: self.system_monitor.get_battery_info())
        
        # Contexte réseau
        self.rule_engine.register_context_provider('network',
            lambda: self.system_monitor.get_network_info())
        
        # Contexte disque
        self.rule_engine.register_context_provider('disk',
            lambda: self.system_monitor.get_disk_info())
        
        # Contexte système
        self.rule_engine.register_context_provider('system',
            lambda: {'uptime': self.system_monitor.get_system_uptime()})
        
        logger.info("Fournisseurs de contexte enregistrés")
    
    def start(self) -> bool:
        """
        Démarre l'application.
        
        Returns:
            bool: True si le démarrage a réussi
        """
        if self.running:
            logger.warning("L'application est déjà en cours d'exécution")
            return False
        
        try:
            logger.info("Démarrage de l'application...")
            
            # Démarrer le monitoring système
            self.system_monitor.start_monitoring()
            
            # Démarrer la surveillance des processus
            self.process_manager.watch_process_changes()
            
            # Démarrer le gestionnaire de triggers
            self.trigger_manager.start()
            
            # Démarrer l'API Flask si configuré
            api_enabled = self.config.get('network', {}).get('api_enabled', True)
            if api_enabled:
                self._start_api_server()
            
            self.running = True
            logger.info("Application démarrée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du démarrage: {e}")
            return False
    
    def stop(self) -> bool:
        """
        Arrête l'application.
        
        Returns:
            bool: True si l'arrêt a réussi
        """
        if not self.running:
            logger.warning("L'application n'est pas en cours d'exécution")
            return False
        
        try:
            logger.info("Arrêt de l'application...")
            
            # Arrêter le gestionnaire de triggers
            if self.trigger_manager:
                self.trigger_manager.stop()
            
            # Arrêter le monitoring système
            if self.system_monitor:
                self.system_monitor.stop_monitoring()
            
            # Arrêter l'API Flask
            self._stop_api_server()
            
            self.running = False
            logger.info("Application arrêtée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt: {e}")
            return False
    
    def _start_api_server(self) -> None:
        """
        Démarre le serveur API Flask dans un thread séparé.
        """
        try:
            from main.api.flask_server import create_app
            
            api_port = self.config.get('network', {}).get('api_port', 5000)
            allow_remote = self.config.get('network', {}).get('allow_remote', False)
            
            app = create_app(self)
            
            # Lancer le serveur Flask dans un thread séparé
            self.api_thread = threading.Thread(
                target=app.run,
                kwargs={
                    'port': api_port,
                    'host': '0.0.0.0' if allow_remote else '127.0.0.1',
                    'debug': False,
                    'use_reloader': False
                },
                daemon=True
            )
            self.api_thread.start()
            
            logger.info(f"Serveur API démarré sur le port {api_port} (accès distant: {allow_remote})")
            
        except ImportError:
            logger.warning("Flask n'est pas disponible, l'API n'a pas été démarrée")
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du serveur API: {e}")
    
    def _stop_api_server(self) -> None:
        """
        Arrête le serveur API Flask.
        """
        # Flask arrêtera automatiquement quand le thread daemon se terminera
        self.api_thread = None
        logger.info("Serveur API arrêté")
    
    def run_cli(self) -> None:
        """
        Exécute l'application en mode CLI.
        """
        # Installer le gestionnaire de signal pour quitter proprement
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        if self.start():
            logger.info("AppFlow est en cours d'exécution. Appuyez sur Ctrl+C pour quitter.")
            
            # Boucle principale
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Interruption clavier détectée...")
            finally:
                self.stop()
    
    def _signal_handler(self, sig, frame) -> None:
        """
        Gestionnaire de signal pour quitter proprement.
        """
        logger.info(f"Signal {sig} reçu, arrêt en cours...")
        self.stop()
        sys.exit(0)


def parse_args():
    """
    Parse les arguments de ligne de commande.
    
    Returns:
        argparse.Namespace: Arguments parsés
    """
    parser = argparse.ArgumentParser(description='AppFlow - Gestionnaire intelligent d\'applications')
    
    parser.add_argument('--version', action='version', version=f'AppFlow v0.1.0')
    
    parser.add_argument('--config-dir',
                      help='Répertoire de configuration personnalisé')
                      
    parser.add_argument('--rules-dir',
                      help='Répertoire de règles personnalisé')
    
    parser.add_argument('--log-level',
                      choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                      default='INFO',
                      help='Niveau de journalisation')
    
    parser.add_argument('--no-api',
                      action='store_true',
                      help='Désactiver le serveur API')
    
    parser.add_argument('--validate-rules',
                      metavar='RULES_FILE',
                      help='Valider un fichier de règles sans démarrer l\'application')
    
    return parser.parse_args()


def main():
    """
    Point d'entrée principal de l'application.
    """
    # Parser les arguments
    args = parse_args()
    
    # Configurer le niveau de log
    log_level = getattr(logging, args.log_level)
    
    # Créer l'application
    app = AppFlow()
    
    # Mode validation de règles
    if args.validate_rules:
        config_loader = ConfigLoader(app_name='AppFlow')
        config_loader.set_directories()
        
        try:
            rules = config_loader.load_rules_file(args.validate_rules)
            errors = config_loader.validate_rules(rules)
            
            if errors:
                print(f"Erreurs de validation dans {args.validate_rules}:")
                for error in errors:
                    print(f"- {error}")
                sys.exit(1)
            else:
                print(f"Le fichier de règles {args.validate_rules} est valide.")
                sys.exit(0)
        except Exception as e:
            print(f"Erreur lors de la validation: {e}")
            sys.exit(1)
    
    # Mode normal
    if app.initialize(
        config_dir=args.config_dir,
        rules_dir=args.rules_dir,
        log_level=log_level
    ):
        # Désactiver l'API si demandé
        if args.no_api:
            app.config['network']['api_enabled'] = False
        
        app.run_cli()
    else:
        sys.exit(1)


if __name__ == "__main__":
    # Exécuter en tant que script
    main()
