"""
Logger - Système de journalisation
--------------------------------
Ce module configure et fournit un système de journalisation centralisé pour AppFlow.
"""

import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Dict, Any, Optional, List
import json

class AppFlowLogger:
    """
    Gestionnaire de logging pour AppFlow.
    """
    
    DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    def __init__(self, app_name: str = "AppFlow"):
        """
        Initialise le gestionnaire de logging.
        
        Args:
            app_name: Nom de l'application pour les logs
        """
        self.app_name = app_name
        self.default_logger = logging.getLogger(app_name)
        self.log_level = logging.INFO
        self.log_dir = None
        self.log_file = None
        self.handlers = []
        self._log_history: List[Dict[str, Any]] = []
        self._max_history_size = 1000
    
    def setup(self, log_level: int = logging.INFO, log_dir: Optional[str] = None, 
              console: bool = True, file: bool = True, max_file_size_mb: int = 10, 
              backup_count: int = 5, format_str: Optional[str] = None) -> None:
        """
        Configure le système de logging.
        
        Args:
            log_level: Niveau de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Répertoire pour les fichiers de logs
            console: Activer le logging vers la console
            file: Activer le logging vers un fichier
            max_file_size_mb: Taille maximale du fichier de log en Mo
            backup_count: Nombre de fichiers de backup à conserver
            format_str: Format de log personnalisé
        """
        self.log_level = log_level
        
        # Configurer le logger racine
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Supprimer les handlers existants
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        
        self.handlers = []
        
        # Format de log
        format_str = format_str or self.DEFAULT_FORMAT
        formatter = logging.Formatter(format_str)
        
        # Handler console
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(log_level)
            root_logger.addHandler(console_handler)
            self.handlers.append(console_handler)
        
        # Handler fichier
        if file:
            if log_dir:
                self.log_dir = log_dir
                os.makedirs(log_dir, exist_ok=True)
            else:
                # Répertoire par défaut
                self.log_dir = os.path.join(os.path.expanduser('~'), f".{self.app_name.lower()}", "logs")
                os.makedirs(self.log_dir, exist_ok=True)
                
            self.log_file = os.path.join(self.log_dir, f"{self.app_name.lower()}.log")
            
            # RotatingFileHandler pour limiter la taille
            file_handler = RotatingFileHandler(
                self.log_file, 
                maxBytes=max_file_size_mb * 1024 * 1024,
                backupCount=backup_count
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
            root_logger.addHandler(file_handler)
            self.handlers.append(file_handler)
            
            # Aussi un TimedRotatingFileHandler pour les logs journaliers
            daily_log = os.path.join(self.log_dir, f"{self.app_name.lower()}_daily.log")
            daily_handler = TimedRotatingFileHandler(
                daily_log,
                when='midnight',
                interval=1,
                backupCount=30  # Garder un mois de logs
            )
            daily_handler.setFormatter(formatter)
            daily_handler.setLevel(log_level)
            root_logger.addHandler(daily_handler)
            self.handlers.append(daily_handler)
        
        self.default_logger.info(f"Système de logging configuré (niveau: {logging.getLevelName(log_level)})")
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Récupère un logger configuré pour un module spécifique.
        
        Args:
            name: Nom du module
            
        Returns:
            logging.Logger: Logger configuré
        """
        return logging.getLogger(f"{self.app_name}.{name}")
    
    def set_level(self, level: int) -> None:
        """
        Modifie le niveau de logging.
        
        Args:
            level: Nouveau niveau de logging
        """
        self.log_level = level
        
        # Mettre à jour le niveau pour tous les handlers
        for handler in self.handlers:
            handler.setLevel(level)
        
        # Mettre à jour le niveau pour le logger racine
        logging.getLogger().setLevel(level)
        
        self.default_logger.info(f"Niveau de logging modifié: {logging.getLevelName(level)}")
    
    def capture_log(self, record: logging.LogRecord) -> None:
        """
        Capture un enregistrement de log dans l'historique interne.
        
        Args:
            record: Enregistrement de log à capturer
        """
        log_entry = {
            'timestamp': time.time(),
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'pathname': record.pathname,
            'lineno': record.lineno,
            'thread': record.thread,
            'threadName': record.threadName
        }
        
        self._log_history.append(log_entry)
        
        # Limiter la taille de l'historique
        if len(self._log_history) > self._max_history_size:
            self._log_history.pop(0)
    
    def setup_log_capture(self) -> None:
        """
        Configure la capture des logs pour l'historique interne.
        """
        class LogHistoryHandler(logging.Handler):
            def __init__(self, logger_instance):
                super().__init__()
                self.logger_instance = logger_instance
                
            def emit(self, record):
                self.logger_instance.capture_log(record)
        
        # Ajouter le handler de capture
        handler = LogHistoryHandler(self)
        handler.setLevel(logging.DEBUG)  # Capturer tous les niveaux
        logging.getLogger().addHandler(handler)
        self.handlers.append(handler)
        
        self.default_logger.info("Capture de l'historique des logs configurée")
    
    def get_log_history(self, level: Optional[int] = None, 
                       count: Optional[int] = None, 
                       start_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Récupère l'historique des logs avec filtrage optionnel.
        
        Args:
            level: Filtrer par niveau de log minimum
            count: Nombre maximum d'entrées à retourner
            start_time: Timestamp Unix de début
            
        Returns:
            List[Dict]: Historique des logs filtré
        """
        filtered_history = self._log_history
        
        # Filtrer par niveau
        if level is not None:
            filtered_history = [
                entry for entry in filtered_history
                if logging.getLevelName(entry['level']) >= level
            ]
        
        # Filtrer par timestamp
        if start_time is not None:
            filtered_history = [
                entry for entry in filtered_history
                if entry['timestamp'] >= start_time
            ]
        
        # Limiter le nombre d'entrées
        if count is not None:
            filtered_history = filtered_history[-count:]
        
        return filtered_history.copy()
    
    def export_logs_to_json(self, output_path: str, 
                          level: Optional[int] = None,
                          start_time: Optional[float] = None) -> bool:
        """
        Exporte l'historique des logs au format JSON.
        
        Args:
            output_path: Chemin du fichier de sortie
            level: Filtrer par niveau de log minimum
            start_time: Timestamp Unix de début
            
        Returns:
            bool: True si l'export a réussi
        """
        try:
            logs_to_export = self.get_log_history(level=level, start_time=start_time)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(logs_to_export, f, indent=2)
                
            self.default_logger.info(f"Logs exportés vers {output_path}")
            return True
            
        except Exception as e:
            self.default_logger.error(f"Erreur lors de l'export des logs: {e}")
            return False
    
    def rotate_logs(self) -> None:
        """
        Force la rotation des fichiers de logs.
        """
        for handler in self.handlers:
            if isinstance(handler, (RotatingFileHandler, TimedRotatingFileHandler)):
                handler.doRollover()
                
        self.default_logger.info("Rotation des logs effectuée")
        

# Instance par défaut pour l'accès global
appflow_logger = AppFlowLogger()


def setup_logging(log_level: int = logging.INFO, log_dir: Optional[str] = None, 
                 console: bool = True, file: bool = True) -> AppFlowLogger:
    """
    Configure le système de logging pour AppFlow (fonction de commodité).
    
    Args:
        log_level: Niveau de logging
        log_dir: Répertoire pour les fichiers de logs
        console: Activer le logging vers la console
        file: Activer le logging vers un fichier
        
    Returns:
        AppFlowLogger: Instance du logger
    """
    appflow_logger.setup(
        log_level=log_level,
        log_dir=log_dir,
        console=console,
        file=file
    )
    appflow_logger.setup_log_capture()
    return appflow_logger
