"""
Trigger Manager - Gestionnaire de triggers
-----------------------------------------
Ce module gère les déclencheurs d'événements qui activent l'évaluation des règles,
comme les changements d'état du système, les horaires, ou d'autres conditions.
"""

import logging
import time
import threading
import schedule
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TriggerManager:
    """
    Gestionnaire des différents types de déclencheurs (triggers) pour l'évaluation des règles.
    """
    
    def __init__(self):
        self._rule_engine = None
        self._system_monitor = None
        self._running = False
        self._scheduler_thread = None
        self._custom_triggers: Dict[str, Callable] = {}
        self._user_activity_lock = threading.Lock()
        self._last_user_activity = datetime.now()
    
    def set_rule_engine(self, rule_engine) -> None:
        """
        Associe un moteur de règles au gestionnaire de triggers.
        
        Args:
            rule_engine: Instance de RuleEngine
        """
        self._rule_engine = rule_engine
    
    def set_system_monitor(self, system_monitor) -> None:
        """
        Associe un moniteur système au gestionnaire de triggers.
        
        Args:
            system_monitor: Instance de SystemMonitor
        """
        self._system_monitor = system_monitor
    
    def register_custom_trigger(self, trigger_name: str, trigger_function: Callable) -> None:
        """
        Enregistre une fonction de déclenchement personnalisée.
        
        Args:
            trigger_name: Nom du trigger personnalisé
            trigger_function: Fonction à exécuter pour vérifier ce trigger
        """
        self._custom_triggers[trigger_name] = trigger_function
        logger.info(f"Trigger personnalisé enregistré: {trigger_name}")
    
    def start(self) -> None:
        """
        Démarre le gestionnaire de triggers.
        """
        if self._running:
            logger.warning("Le gestionnaire de triggers est déjà en cours d'exécution")
            return
        
        if not self._rule_engine:
            logger.error("Aucun moteur de règles défini, impossible de démarrer")
            return
        
        self._running = True
        
        # Démarrage du thread de planification
        self._scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._scheduler_thread.start()
        
        logger.info("Gestionnaire de triggers démarré")
    
    def stop(self) -> None:
        """
        Arrête le gestionnaire de triggers.
        """
        if not self._running:
            logger.warning("Le gestionnaire de triggers n'est pas en cours d'exécution")
            return
        
        self._running = False
        
        # Attendre que le thread de planification s'arrête
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=2.0)
        
        # Effacer toutes les tâches planifiées
        schedule.clear()
        
        logger.info("Gestionnaire de triggers arrêté")
    
    def _run_scheduler(self) -> None:
        """
        Fonction exécutée dans un thread séparé pour gérer les triggers planifiés.
        """
        # Planification des vérifications de triggers récurrentes
        schedule.every(5).seconds.do(self._check_system_triggers)
        schedule.every(1).minutes.do(self._check_idle_triggers)
        
        while self._running:
            schedule.run_pending()
            time.sleep(1)
    
    def update_user_activity(self) -> None:
        """
        Met à jour le timestamp de la dernière activité utilisateur.
        À appeler lors de la détection d'activité (clavier, souris, etc.)
        """
        with self._user_activity_lock:
            self._last_user_activity = datetime.now()
    
    def get_idle_time(self) -> float:
        """
        Calcule le temps d'inactivité de l'utilisateur en secondes.
        
        Returns:
            float: Temps d'inactivité en secondes
        """
        with self._user_activity_lock:
            return (datetime.now() - self._last_user_activity).total_seconds()
    
    def add_time_trigger(self, time_spec: str, trigger_id: str = None) -> Optional[str]:
        """
        Ajoute un trigger basé sur l'heure.
        
        Args:
            time_spec: Spécification de l'heure au format cron ou naturel
            trigger_id: Identifiant optionnel du trigger
            
        Returns:
            str: Identifiant du trigger
        """
        if not self._rule_engine:
            logger.error("Aucun moteur de règles défini, impossible d'ajouter un trigger temporel")
            return None
        
        trigger_id = trigger_id or f"time_{int(time.time())}"
        
        try:
            # Syntaxe cron (at() avec chaîne) ou naturel (every() avec intervalle)
            if ' ' in time_spec:
                # Format cron: "* * * * *"
                schedule.every().day.at(time_spec).do(
                    self._execute_time_trigger, trigger_id=trigger_id
                ).tag(trigger_id)
            else:
                # Format naturel: "10m", "1h", etc.
                value = int(time_spec[:-1])
                unit = time_spec[-1].lower()
                
                if unit == 's':
                    schedule.every(value).seconds.do(
                        self._execute_time_trigger, trigger_id=trigger_id
                    ).tag(trigger_id)
                elif unit == 'm':
                    schedule.every(value).minutes.do(
                        self._execute_time_trigger, trigger_id=trigger_id
                    ).tag(trigger_id)
                elif unit == 'h':
                    schedule.every(value).hours.do(
                        self._execute_time_trigger, trigger_id=trigger_id
                    ).tag(trigger_id)
                else:
                    logger.error(f"Unité de temps non reconnue: {unit}")
                    return None
            
            logger.info(f"Trigger temporel ajouté: {trigger_id} ({time_spec})")
            return trigger_id
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du trigger temporel: {e}")
            return None
    
    def remove_time_trigger(self, trigger_id: str) -> bool:
        """
        Supprime un trigger basé sur l'heure.
        
        Args:
            trigger_id: Identifiant du trigger
            
        Returns:
            bool: True si le trigger a été supprimé
        """
        try:
            schedule.clear(tag=trigger_id)
            logger.info(f"Trigger temporel supprimé: {trigger_id}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du trigger temporel: {e}")
            return False
    
    def _execute_time_trigger(self, trigger_id: str) -> None:
        """
        Exécute l'évaluation des règles suite à un trigger temporel.
        
        Args:
            trigger_id: Identifiant du trigger
        """
        logger.debug(f"Trigger temporel déclenché: {trigger_id}")
        if self._rule_engine and self._running:
            self._rule_engine.execute_matched_rules()
    
    def _check_system_triggers(self) -> None:
        """
        Vérifie les triggers système (CPU, mémoire, batterie, réseau).
        """
        if not self._system_monitor or not self._rule_engine or not self._running:
            return
        
        try:
            # Récupérer les métriques système actuelles
            cpu_usage = self._system_monitor.get_cpu_usage()
            memory_usage = self._system_monitor.get_memory_usage()
            battery_info = self._system_monitor.get_battery_info()
            network_info = self._system_monitor.get_network_info()
            
            # Vérifier si des seuils sont dépassés
            thresholds_exceeded = False
            
            # CPU
            if cpu_usage > 80:  # Exemple de seuil
                logger.debug(f"Seuil CPU dépassé: {cpu_usage}%")
                thresholds_exceeded = True
            
            # Mémoire
            if memory_usage['percent'] > 85:  # Exemple de seuil
                logger.debug(f"Seuil mémoire dépassé: {memory_usage['percent']}%")
                thresholds_exceeded = True
            
            # Batterie
            if battery_info and battery_info['percent'] < 20 and not battery_info['power_plugged']:
                logger.debug(f"Seuil batterie dépassé: {battery_info['percent']}%")
                thresholds_exceeded = True
            
            # Exécuter les règles si nécessaire
            if thresholds_exceeded:
                self._rule_engine.execute_matched_rules()
            
            # Vérifier les triggers personnalisés
            for trigger_name, trigger_func in self._custom_triggers.items():
                try:
                    if trigger_func():
                        logger.debug(f"Trigger personnalisé déclenché: {trigger_name}")
                        self._rule_engine.execute_matched_rules()
                        break  # Éviter de multiples exécutions consécutives
                except Exception as e:
                    logger.error(f"Erreur lors de la vérification du trigger personnalisé {trigger_name}: {e}")
        
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des triggers système: {e}")
    
    def _check_idle_triggers(self) -> None:
        """
        Vérifie les triggers liés à l'inactivité de l'utilisateur.
        """
        if not self._rule_engine or not self._running:
            return
        
        try:
            idle_time = self.get_idle_time()
            
            # Exemple: déclencher après 5 minutes d'inactivité
            if idle_time > 300:  # 5 minutes en secondes
                logger.debug(f"Trigger d'inactivité déclenché: {idle_time:.1f} secondes")
                self._rule_engine.execute_matched_rules()
        
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des triggers d'inactivité: {e}")
    
    def add_process_trigger(self, process_name: str, trigger_type: str = 'any',
                           trigger_id: str = None) -> Optional[str]:
        """
        Ajoute un trigger lié à un processus (démarrage/fermeture).
        
        Args:
            process_name: Nom du processus à surveiller
            trigger_type: 'start', 'end', ou 'any'
            trigger_id: Identifiant optionnel du trigger
            
        Returns:
            str: Identifiant du trigger
        """
        if not self._system_monitor:
            logger.error("Aucun moniteur système défini, impossible d'ajouter un trigger de processus")
            return None
        
        trigger_id = trigger_id or f"process_{process_name}_{int(time.time())}"
        
        # La logique réelle de surveillance serait implémentée dans SystemMonitor
        # Ici, on indique simplement au moniteur de surveiller ce processus
        if hasattr(self._system_monitor, 'watch_process'):
            self._system_monitor.watch_process(
                process_name=process_name,
                trigger_type=trigger_type,
                callback=lambda event: self._execute_process_trigger(trigger_id, event)
            )
            logger.info(f"Trigger de processus ajouté: {trigger_id} ({process_name}, {trigger_type})")
            return trigger_id
        else:
            logger.error("Le moniteur système ne prend pas en charge la surveillance des processus")
            return None
    
    def _execute_process_trigger(self, trigger_id: str, event_data: Dict[str, Any]) -> None:
        """
        Exécute l'évaluation des règles suite à un trigger de processus.
        
        Args:
            trigger_id: Identifiant du trigger
            event_data: Données sur l'événement (type, processus, etc.)
        """
        logger.debug(f"Trigger de processus déclenché: {trigger_id}, {event_data}")
        if self._rule_engine and self._running:
            self._rule_engine.execute_matched_rules()
