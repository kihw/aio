"""
Config Loader - Chargeur de configuration
---------------------------------------
Ce module gère le chargement, la validation et l'enregistrement des fichiers
de configuration YAML pour AppFlow.
"""

import os
import yaml
import logging
import json
import time
from typing import Dict, Any, List, Optional, Union
import shutil

logger = logging.getLogger(__name__)

class ConfigValidationError(Exception):
    """Exception soulevée lors d'une erreur de validation de configuration."""
    pass

class ConfigLoader:
    """
    Chargeur de configuration pour AppFlow.
    """
    
    def __init__(self, app_name: str = "AppFlow"):
        """
        Initialise le chargeur de configuration.
        
        Args:
            app_name: Nom de l'application pour les chemins par défaut
        """
        self.app_name = app_name
        self.config_dir = None
        self.rules_dir = None
        self.config_file = None
        self.current_config = {}
        self.schema = {}
    
    def set_directories(self, config_dir: Optional[str] = None, 
                     rules_dir: Optional[str] = None) -> None:
        """
        Configure les répertoires pour les fichiers de configuration.
        
        Args:
            config_dir: Répertoire pour les fichiers de configuration
            rules_dir: Répertoire pour les fichiers de règles
        """
        # Répertoire de configuration
        if config_dir:
            self.config_dir = config_dir
        else:
            # Répertoire par défaut dans le home de l'utilisateur
            self.config_dir = os.path.join(os.path.expanduser('~'), f".{self.app_name.lower()}")
        
        # Répertoire des règles
        if rules_dir:
            self.rules_dir = rules_dir
        else:
            self.rules_dir = os.path.join(self.config_dir, "rules")
        
        # Fichier de configuration principal
        self.config_file = os.path.join(self.config_dir, "config.yaml")
        
        # Créer les répertoires s'ils n'existent pas
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.rules_dir, exist_ok=True)
        
        logger.info(f"Répertoires de configuration configurés: {self.config_dir}, {self.rules_dir}")
    
    def load_config(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Charge la configuration depuis un fichier.
        
        Args:
            config_file: Chemin vers le fichier de configuration (utilise le chemin par défaut si None)
            
        Returns:
            Dict: Configuration chargée
            
        Raises:
            FileNotFoundError: Si le fichier n'existe pas et qu'il n'y a pas de configuration par défaut
            yaml.YAMLError: Si le fichier n'est pas un YAML valide
        """
        file_to_load = config_file or self.config_file
        
        try:
            with open(file_to_load, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            if not config or not isinstance(config, dict):
                logger.warning(f"Configuration invalide dans {file_to_load}, utilisation de la configuration par défaut")
                config = self._get_default_config()
            
            self.current_config = config
            logger.info(f"Configuration chargée depuis {file_to_load}")
            return config
            
        except FileNotFoundError:
            logger.warning(f"Fichier de configuration {file_to_load} non trouvé, création d'une configuration par défaut")
            self.current_config = self._get_default_config()
            self.save_config(self.current_config, file_to_load)
            return self.current_config
            
        except yaml.YAMLError as e:
            logger.error(f"Erreur lors du chargement de la configuration YAML: {e}")
            raise
    
    def save_config(self, config: Dict[str, Any], config_file: Optional[str] = None) -> bool:
        """
        Enregistre la configuration dans un fichier.
        
        Args:
            config: Configuration à enregistrer
            config_file: Chemin vers le fichier de configuration (utilise le chemin par défaut si None)
            
        Returns:
            bool: True si l'enregistrement a réussi
        """
        file_to_save = config_file or self.config_file
        
        try:
            # Créer le répertoire parent si nécessaire
            os.makedirs(os.path.dirname(file_to_save), exist_ok=True)
            
            # Créer une sauvegarde si le fichier existe déjà
            if os.path.exists(file_to_save):
                backup_file = f"{file_to_save}.{int(time.time())}.bak"
                shutil.copy2(file_to_save, backup_file)
                logger.debug(f"Sauvegarde créée: {backup_file}")
            
            with open(file_to_save, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
                
            logger.info(f"Configuration enregistrée dans {file_to_save}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement de la configuration: {e}")
            return False
    
    def load_schema(self, schema_file: str) -> Dict[str, Any]:
        """
        Charge un schéma de validation pour la configuration.
        
        Args:
            schema_file: Chemin vers le fichier de schéma JSON Schema
            
        Returns:
            Dict: Schéma chargé
        """
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema = json.load(f)
                
            self.schema = schema
            logger.info(f"Schéma de validation chargé depuis {schema_file}")
            return schema
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement du schéma: {e}")
            raise
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Valide la configuration contre le schéma.
        
        Args:
            config: Configuration à valider
            
        Returns:
            bool: True si la configuration est valide
            
        Raises:
            ConfigValidationError: Si la configuration est invalide
            ImportError: Si la bibliothèque jsonschema n'est pas disponible
        """
        if not self.schema:
            logger.warning("Aucun schéma défini, validation impossible")
            return True
        
        try:
            import jsonschema
            
            try:
                jsonschema.validate(instance=config, schema=self.schema)
                logger.info("Configuration validée avec succès")
                return True
                
            except jsonschema.exceptions.ValidationError as e:
                logger.error(f"Erreur de validation de la configuration: {e}")
                raise ConfigValidationError(f"Configuration invalide: {e}")
                
        except ImportError:
            logger.warning("Bibliothèque jsonschema non disponible, validation ignorée")
            return True
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Crée une configuration par défaut.
        
        Returns:
            Dict: Configuration par défaut
        """
        return {
            'app': {
                'name': self.app_name,
                'version': '0.1.0',
                'start_with_os': False,
                'minimize_to_tray': True,
                'check_for_updates': True
            },
            'logging': {
                'level': 'INFO',
                'console': True,
                'file': True,
                'max_file_size_mb': 10,
                'rotate_count': 5
            },
            'engine': {
                'check_interval': 5,  # secondes
                'default_rules_file': 'default.yaml',
                'autostart': True
            },
            'ui': {
                'theme': 'system',
                'language': 'auto',
                'refresh_interval': 1000  # millisecondes
            },
            'network': {
                'api_port': 5000,
                'allow_remote': False,
                'require_auth': True,
                'api_key': self._generate_api_key()
            }
        }
    
    def _generate_api_key(self) -> str:
        """
        Génère une clé API aléatoire.
        
        Returns:
            str: Clé API
        """
        import secrets
        import string
        
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(32))
    
    def load_rules_file(self, rules_file: str) -> Dict[str, Any]:
        """
        Charge un fichier de règles YAML.
        
        Args:
            rules_file: Nom du fichier de règles (sera recherché dans le répertoire des règles)
            
        Returns:
            Dict: Règles chargées
            
        Raises:
            FileNotFoundError: Si le fichier n'existe pas
            yaml.YAMLError: Si le fichier n'est pas un YAML valide
        """
        # Si le chemin est relatif, l'interpréter par rapport au répertoire des règles
        if not os.path.isabs(rules_file):
            file_path = os.path.join(self.rules_dir, rules_file)
        else:
            file_path = rules_file
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                rules = yaml.safe_load(f)
                
            if not rules or not isinstance(rules, dict) or 'rules' not in rules:
                logger.warning(f"Format de règles invalide dans {file_path}")
                return {'rules': {}}
            
            logger.info(f"Règles chargées depuis {file_path}")
            return rules
            
        except FileNotFoundError:
            logger.error(f"Fichier de règles {file_path} non trouvé")
            raise
            
        except yaml.YAMLError as e:
            logger.error(f"Erreur lors du chargement des règles YAML: {e}")
            raise
    
    def save_rules_file(self, rules: Dict[str, Any], rules_file: str) -> bool:
        """
        Enregistre des règles dans un fichier.
        
        Args:
            rules: Règles à enregistrer
            rules_file: Nom du fichier de règles
            
        Returns:
            bool: True si l'enregistrement a réussi
        """
        # Si le chemin est relatif, l'interpréter par rapport au répertoire des règles
        if not os.path.isabs(rules_file):
            file_path = os.path.join(self.rules_dir, rules_file)
        else:
            file_path = rules_file
        
        try:
            # Créer le répertoire parent si nécessaire
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Créer une sauvegarde si le fichier existe déjà
            if os.path.exists(file_path):
                backup_file = f"{file_path}.{int(time.time())}.bak"
                shutil.copy2(file_path, backup_file)
                logger.debug(f"Sauvegarde créée: {backup_file}")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(rules, f, default_flow_style=False, sort_keys=False)
                
            logger.info(f"Règles enregistrées dans {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement des règles: {e}")
            return False
    
    def list_rules_files(self) -> List[str]:
        """
        Liste les fichiers de règles disponibles.
        
        Returns:
            List[str]: Liste des noms de fichiers de règles
        """
        if not self.rules_dir or not os.path.exists(self.rules_dir):
            return []
        
        try:
            # Filtrer pour ne garder que les fichiers YAML
            files = [
                f for f in os.listdir(self.rules_dir)
                if os.path.isfile(os.path.join(self.rules_dir, f)) and
                (f.endswith('.yaml') or f.endswith('.yml'))
            ]
            return files
        except Exception as e:
            logger.error(f"Erreur lors du listage des fichiers de règles: {e}")
            return []
    
    def validate_rules(self, rules: Dict[str, Any]) -> List[str]:
        """
        Valide un ensemble de règles pour détecter les erreurs.
        
        Args:
            rules: Règles à valider
            
        Returns:
            List[str]: Liste des erreurs (vide si aucune erreur)
        """
        errors = []
        
        if not isinstance(rules, dict):
            errors.append("Les règles doivent être un dictionnaire")
            return errors
        
        if 'rules' not in rules:
            errors.append("Le dictionnaire de règles doit contenir une clé 'rules'")
            return errors
        
        rules_dict = rules['rules']
        if not isinstance(rules_dict, dict):
            errors.append("La section 'rules' doit être un dictionnaire")
            return errors
        
        # Vérifier chaque règle
        for rule_id, rule in rules_dict.items():
            # Vérifier les champs obligatoires
            if not isinstance(rule, dict):
                errors.append(f"La règle '{rule_id}' doit être un dictionnaire")
                continue
                
            # Vérifier le nom
            if 'name' not in rule:
                errors.append(f"La règle '{rule_id}' n'a pas de nom")
            
            # Vérifier les conditions
            if 'conditions' in rule:
                if not isinstance(rule['conditions'], list):
                    errors.append(f"Les conditions de la règle '{rule_id}' doivent être une liste")
                else:
                    for i, condition in enumerate(rule['conditions']):
                        if not isinstance(condition, dict):
                            errors.append(f"La condition {i} de la règle '{rule_id}' doit être un dictionnaire")
                            continue
                            
                        if 'type' not in condition:
                            errors.append(f"La condition {i} de la règle '{rule_id}' n'a pas de type")
        
            # Vérifier les actions
            if 'actions' not in rule:
                errors.append(f"La règle '{rule_id}' n'a pas d'actions")
            elif not isinstance(rule['actions'], list):
                errors.append(f"Les actions de la règle '{rule_id}' doivent être une liste")
            else:
                for i, action in enumerate(rule['actions']):
                    if not isinstance(action, dict):
                        errors.append(f"L'action {i} de la règle '{rule_id}' doit être un dictionnaire")
                        continue
                        
                    if 'type' not in action:
                        errors.append(f"L'action {i} de la règle '{rule_id}' n'a pas de type")
        
        return errors
    
    def create_example_rules_file(self, file_path: Optional[str] = None) -> str:
        """
        Crée un fichier d'exemple de règles.
        
        Args:
            file_path: Chemin où créer le fichier (utilise 'default.yaml' dans le répertoire des règles si None)
            
        Returns:
            str: Chemin du fichier créé
        """
        if file_path is None:
            file_path = os.path.join(self.rules_dir, 'default.yaml')
        
        example_rules = {
            'meta': {
                'name': 'Règles par défaut',
                'description': 'Exemples de règles pour AppFlow',
                'version': '1.0',
                'author': 'AppFlow',
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
            },
            'rules': {
                'cpu_high_alert': {
                    'name': 'Alerte CPU élevé',
                    'description': 'Envoie une notification quand le CPU est à plus de 80%',
                    'enabled': True,
                    'priority': 8,
                    'conditions': [
                        {
                            'type': 'cpu',
                            'operator': '>',
                            'value': 80
                        }
                    ],
                    'actions': [
                        {
                            'type': 'notify',
                            'params': {
                                'title': 'CPU élevé',
                                'message': 'L\'utilisation du CPU dépasse 80%',
                                'level': 'warning'
                            }
                        }
                    ],
                    'triggers': [
                        {
                            'type': 'system',
                            'interval': '30s'
                        }
                    ]
                },
                'open_browser_morning': {
                    'name': 'Ouvrir le navigateur le matin',
                    'description': 'Ouvre le navigateur web automatiquement à 9h',
                    'enabled': True,
                    'priority': 5,
                    'actions': [
                        {
                            'type': 'launch',
                            'params': {
                                'path': 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
                                'args': ['--new-window', 'https://www.example.com']
                            }
                        },
                        {
                            'type': 'notify',
                            'params': {
                                'title': 'Bonjour!',
                                'message': 'Le navigateur a été lancé automatiquement'
                            }
                        }
                    ],
                    'triggers': [
                        {
                            'type': 'time',
                            'time': '09:00'
                        }
                    ]
                },
                'close_apps_battery_low': {
                    'name': 'Fermer apps quand batterie faible',
                    'description': 'Ferme certaines applications quand la batterie est faible',
                    'enabled': True,
                    'priority': 9,
                    'conditions': [
                        {
                            'type': 'battery',
                            'params': {
                                'percent': True
                            },
                            'operator': '<',
                            'value': 15
                        },
                        {
                            'type': 'battery',
                            'params': {
                                'power_plugged': True
                            },
                            'operator': '==',
                            'value': False
                        }
                    ],
                    'condition_logic': 'all',
                    'actions': [
                        {
                            'type': 'kill',
                            'params': {
                                'name': 'chrome.exe'
                            }
                        },
                        {
                            'type': 'notify',
                            'params': {
                                'title': 'Batterie faible',
                                'message': 'Applications fermées pour économiser la batterie',
                                'level': 'warning'
                            }
                        }
                    ],
                    'triggers': [
                        {
                            'type': 'system',
                            'interval': '1m'
                        }
                    ]
                }
            }
        }
        
        try:
            # Créer le répertoire parent si nécessaire
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(example_rules, f, default_flow_style=False, sort_keys=False)
                
            logger.info(f"Fichier d'exemple de règles créé: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du fichier d'exemple: {e}")
            raise
