"""
Action Executor - Exécuteur d'actions
-------------------------------------
Ce module est responsable de l'exécution des actions demandées par le moteur de règles,
comme le lancement ou l'arrêt d'applications, l'envoi de notifications, etc.
"""

import logging
import time
import subprocess
import platform
from typing import Dict, Any, List, Union, Optional, Callable

logger = logging.getLogger(__name__)

class ActionExecutor:
    """
    Classe responsable de l'exécution des actions définies dans les règles.
    """
    
    def __init__(self):
        self._process_manager = None  # Sera défini lors de l'intégration
        self._notification_manager = None  # Pour les notifications futures
        self._custom_actions: Dict[str, Callable] = {}
        self._os_type = platform.system().lower()  # 'windows', 'linux', 'darwin'
    
    def set_process_manager(self, process_manager) -> None:
        """
        Associe un gestionnaire de processus à l'exécuteur d'actions.
        
        Args:
            process_manager: Instance de ProcessManager
        """
        self._process_manager = process_manager
    
    def set_notification_manager(self, notification_manager) -> None:
        """
        Associe un gestionnaire de notifications à l'exécuteur d'actions.
        
        Args:
            notification_manager: Instance de NotificationManager
        """
        self._notification_manager = notification_manager
    
    def register_custom_action(self, action_name: str, action_function: Callable) -> None:
        """
        Enregistre une fonction personnalisée pour un type d'action.
        
        Args:
            action_name: Nom de l'action personnalisée
            action_function: Fonction à exécuter pour cette action
        """
        self._custom_actions[action_name] = action_function
        logger.info(f"Action personnalisée enregistrée: {action_name}")
    
    def execute(self, action: Dict[str, Any], rule_id: str = "") -> bool:
        """
        Exécute une action selon sa définition.
        
        Args:
            action: Dictionnaire définissant l'action à exécuter
            rule_id: Identifiant de la règle qui a déclenché l'action (pour le logging)
            
        Returns:
            bool: True si l'action a été exécutée avec succès, False sinon
        """
        if not isinstance(action, dict) or 'type' not in action:
            logger.error("Format d'action invalide")
            return False
        
        action_type = action['type']
        params = action.get('params', {})
        
        rule_info = f" pour la règle {rule_id}" if rule_id else ""
        logger.info(f"Exécution de l'action {action_type}{rule_info}")
        
        try:
            # Actions intégrées
            if action_type == 'launch':
                return self._launch_application(params)
            elif action_type == 'kill':
                return self._kill_application(params)
            elif action_type == 'wait':
                return self._wait(params)
            elif action_type == 'notify':
                return self._notify(params)
            elif action_type == 'execute_command':
                return self._execute_command(params)
            # Actions personnalisées
            elif action_type in self._custom_actions:
                return self._custom_actions[action_type](params)
            else:
                logger.error(f"Type d'action non supporté: {action_type}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de l'action {action_type}: {e}")
            return False
    
    def _launch_application(self, params: Dict[str, Any]) -> bool:
        """
        Lance une application.
        
        Args:
            params: Paramètres de l'action avec au moins 'path'
            
        Returns:
            bool: True si l'application a été lancée avec succès
        """
        if self._process_manager is None:
            logger.error("ProcessManager non défini, impossible de lancer l'application")
            return False
            
        app_path = params.get('path')
        if not app_path:
            logger.error("Chemin d'application non spécifié")
            return False
            
        args = params.get('args', [])
        working_dir = params.get('working_dir')
        as_admin = params.get('as_admin', False)
        
        return self._process_manager.launch_process(
            app_path, 
            args=args,
            working_dir=working_dir,
            as_admin=as_admin
        )
    
    def _kill_application(self, params: Dict[str, Any]) -> bool:
        """
        Arrête une application.
        
        Args:
            params: Paramètres de l'action avec 'name', 'pid' ou 'window_title'
            
        Returns:
            bool: True si l'application a été arrêtée avec succès
        """
        if self._process_manager is None:
            logger.error("ProcessManager non défini, impossible d'arrêter l'application")
            return False
        
        # Différentes méthodes pour identifier le processus à arrêter
        pid = params.get('pid')
        if pid:
            return self._process_manager.kill_process_by_pid(pid)
            
        name = params.get('name')
        if name:
            return self._process_manager.kill_process_by_name(name)
            
        window_title = params.get('window_title')
        if window_title:
            return self._process_manager.kill_process_by_window_title(window_title)
        
        logger.error("Paramètres insuffisants pour identifier le processus à arrêter")
        return False
    
    def _wait(self, params: Dict[str, Any]) -> bool:
        """
        Attend pendant une durée spécifiée.
        
        Args:
            params: Paramètres avec 'seconds' ou 'milliseconds'
            
        Returns:
            bool: Toujours True après l'attente
        """
        seconds = params.get('seconds', 0)
        milliseconds = params.get('milliseconds', 0)
        
        total_seconds = seconds + (milliseconds / 1000)
        if total_seconds > 0:
            time.sleep(total_seconds)
            logger.debug(f"Attente de {total_seconds} secondes terminée")
        return True
    
    def _notify(self, params: Dict[str, Any]) -> bool:
        """
        Envoie une notification.
        
        Args:
            params: Paramètres avec 'title' et 'message'
            
        Returns:
            bool: True si la notification a été envoyée avec succès
        """
        if self._notification_manager:
            title = params.get('title', 'AppFlow')
            message = params.get('message', '')
            level = params.get('level', 'info')
            timeout = params.get('timeout', 5)
            return self._notification_manager.send_notification(
                title=title,
                message=message,
                level=level,
                timeout=timeout
            )
        else:
            # Implémentation de base si pas de gestionnaire de notifications
            title = params.get('title', 'AppFlow')
            message = params.get('message', '')
            logger.info(f"Notification: {title} - {message}")
            
            # Notification native basique selon OS
            try:
                if self._os_type == 'windows':
                    from win10toast import ToastNotifier
                    toaster = ToastNotifier()
                    toaster.show_toast(title, message, duration=params.get('timeout', 5))
                    return True
                elif self._os_type == 'darwin':  # macOS
                    subprocess.run(['osascript', '-e', f'display notification "{message}" with title "{title}"'])
                    return True
                elif self._os_type == 'linux':
                    subprocess.run(['notify-send', title, message])
                    return True
            except Exception as e:
                logger.warning(f"Impossible d'envoyer une notification native: {e}")
            
            return False
    
    def _execute_command(self, params: Dict[str, Any]) -> bool:
        """
        Exécute une commande shell.
        
        Args:
            params: Paramètres avec 'command'
            
        Returns:
            bool: True si la commande a été exécutée avec succès
        """
        if 'command' not in params:
            logger.error("Commande non spécifiée")
            return False
        
        command = params['command']
        shell = params.get('shell', True)
        working_dir = params.get('working_dir')
        
        try:
            process = subprocess.run(
                command,
                shell=shell,
                cwd=working_dir,
                check=False,
                capture_output=params.get('capture_output', False),
                text=True
            )
            if params.get('require_success', True) and process.returncode != 0:
                logger.error(f"La commande a échoué avec le code {process.returncode}")
                if process.stderr:
                    logger.error(f"Erreur: {process.stderr}")
                return False
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la commande: {e}")
            return False
