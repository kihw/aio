"""
System Monitor - Monitoring système
----------------------------------
Ce module surveille les ressources système comme le CPU, la RAM,
la batterie et le réseau pour fournir ces informations au moteur de règles.
"""

import psutil
import logging
import platform
import time
import threading
from typing import Dict, Any, Optional, List, Callable, Set

logger = logging.getLogger(__name__)

class SystemMonitor:
    """
    Moniteur des ressources système fournissant les métriques pour les triggers et les conditions.
    """
    
    def __init__(self):
        """
        Initialise le moniteur système.
        """
        self._running = False
        self._monitor_thread = None
        self._metrics: Dict[str, Any] = {
            'cpu': {'usage': 0, 'per_cpu': [], 'history': []},
            'memory': {'total': 0, 'available': 0, 'used': 0, 'percent': 0},
            'battery': None,
            'network': {'sent_bytes': 0, 'recv_bytes': 0, 'sent_rate': 0, 'recv_rate': 0},
            'disk': {}
        }
        self._metrics_lock = threading.Lock()
        self._metric_callbacks: Dict[str, List[Callable]] = {}
        self._network_last = {'time': 0, 'sent': 0, 'recv': 0}
        self._watched_processes: Dict[str, Dict[str, Any]] = {}
        self._process_manager = None
        self._os_type = platform.system().lower()  # 'windows', 'linux', 'darwin'
    
    def set_process_manager(self, process_manager) -> None:
        """
        Associe un gestionnaire de processus au moniteur système.
        
        Args:
            process_manager: Instance de ProcessManager
        """
        self._process_manager = process_manager
    
    def start_monitoring(self, interval: float = 1.0) -> None:
        """
        Démarre le monitoring des ressources système dans un thread séparé.
        
        Args:
            interval: Intervalle entre les mesures en secondes
        """
        if self._running:
            logger.warning("Le monitoring système est déjà en cours d'exécution")
            return
        
        self._running = True
        
        def monitoring_loop():
            while self._running:
                try:
                    self._update_metrics()
                    time.sleep(interval)
                except Exception as e:
                    logger.error(f"Erreur dans la boucle de monitoring: {e}")
        
        self._monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info(f"Monitoring système démarré (intervalle: {interval}s)")
    
    def stop_monitoring(self) -> None:
        """
        Arrête le monitoring des ressources système.
        """
        if not self._running:
            logger.warning("Le monitoring système n'est pas en cours d'exécution")
            return
        
        self._running = False
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)
        
        logger.info("Monitoring système arrêté")
    
    def _update_metrics(self) -> None:
        """
        Met à jour les métriques système.
        """
        try:
            # CPU
            cpu_usage = psutil.cpu_percent(interval=None)
            per_cpu = psutil.cpu_percent(interval=None, percpu=True)
            
            # Mémoire
            memory = psutil.virtual_memory()
            
            # Batterie
            battery = None
            if hasattr(psutil, 'sensors_battery'):
                battery_info = psutil.sensors_battery()
                if battery_info:
                    battery = {
                        'percent': battery_info.percent,
                        'power_plugged': battery_info.power_plugged,
                        'time_left': battery_info.secsleft if battery_info.secsleft != -1 else None
                    }
            
            # Réseau
            network_io = psutil.net_io_counters()
            current_time = time.time()
            
            network_rate = {'sent_rate': 0, 'recv_rate': 0}
            if self._network_last['time'] > 0:
                time_diff = current_time - self._network_last['time']
                if time_diff > 0:
                    sent_diff = network_io.bytes_sent - self._network_last['sent']
                    recv_diff = network_io.bytes_recv - self._network_last['recv']
                    network_rate = {
                        'sent_rate': sent_diff / time_diff,
                        'recv_rate': recv_diff / time_diff
                    }
            
            self._network_last = {
                'time': current_time,
                'sent': network_io.bytes_sent,
                'recv': network_io.bytes_recv
            }
            
            # Disque
            disk_usage = {}
            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disk_usage[part.mountpoint] = {
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': usage.percent
                    }
                except (PermissionError, FileNotFoundError):
                    pass
            
            # Mettre à jour les métriques
            with self._metrics_lock:
                self._metrics['cpu']['usage'] = cpu_usage
                self._metrics['cpu']['per_cpu'] = per_cpu
                self._metrics['cpu']['history'].append(cpu_usage)
                
                # Limiter l'historique à 60 valeurs (1 minute à intervalle de 1s)
                if len(self._metrics['cpu']['history']) > 60:
                    self._metrics['cpu']['history'].pop(0)
                
                self._metrics['memory'] = {
                    'total': memory.total,
                    'available': memory.available,
                    'used': memory.used,
                    'percent': memory.percent
                }
                
                self._metrics['battery'] = battery
                
                self._metrics['network'] = {
                    'sent_bytes': network_io.bytes_sent,
                    'recv_bytes': network_io.bytes_recv,
                    'sent_rate': network_rate['sent_rate'],
                    'recv_rate': network_rate['recv_rate']
                }
                
                self._metrics['disk'] = disk_usage
                
            # Déclencher les callbacks
            self._trigger_metric_callbacks()
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des métriques: {e}")
    
    def register_metric_callback(self, metric_name: str, callback: Callable, threshold: Any = None) -> None:
        """
        Enregistre une fonction de rappel pour une métrique spécifique.
        
        Args:
            metric_name: Nom de la métrique (cpu, memory, battery, network, disk)
            callback: Fonction à appeler quand la métrique est mise à jour
            threshold: Seuil optionnel pour déclencher le callback seulement au-dessus/en dessous
        """
        if metric_name not in self._metric_callbacks:
            self._metric_callbacks[metric_name] = []
        
        self._metric_callbacks[metric_name].append({
            'callback': callback,
            'threshold': threshold
        })
        
        logger.debug(f"Callback enregistré pour la métrique {metric_name}")
    
    def unregister_metric_callback(self, metric_name: str, callback: Callable) -> None:
        """
        Désenregistre une fonction de rappel pour une métrique.
        
        Args:
            metric_name: Nom de la métrique
            callback: Fonction à désenregistrer
        """
        if metric_name in self._metric_callbacks:
            self._metric_callbacks[metric_name] = [
                cb for cb in self._metric_callbacks[metric_name]
                if cb['callback'] != callback
            ]
            logger.debug(f"Callback désenregistré pour la métrique {metric_name}")
    
    def _trigger_metric_callbacks(self) -> None:
        """
        Déclenche les callbacks pour les métriques qui ont été mises à jour.
        """
        with self._metrics_lock:
            metrics_copy = self._metrics.copy()
        
        for metric_name, callbacks in self._metric_callbacks.items():
            if metric_name in metrics_copy:
                metric_value = metrics_copy[metric_name]
                
                for cb_info in callbacks:
                    try:
                        # Vérifier le seuil si spécifié
                        threshold = cb_info['threshold']
                        should_call = True
                        
                        if threshold is not None:
                            if metric_name == 'cpu':
                                should_call = metrics_copy['cpu']['usage'] > threshold
                            elif metric_name == 'memory':
                                should_call = metrics_copy['memory']['percent'] > threshold
                            elif metric_name == 'battery' and metrics_copy['battery']:
                                # Seuil pour batterie faible
                                should_call = metrics_copy['battery']['percent'] < threshold
                            elif metric_name == 'network':
                                # Seuil pour débit réseau élevé (en bytes/s)
                                should_call = (
                                    metrics_copy['network']['sent_rate'] > threshold or
                                    metrics_copy['network']['recv_rate'] > threshold
                                )
                            elif metric_name == 'disk':
                                # Seuil pour espace disque faible (sur n'importe quelle partition)
                                should_call = any(
                                    disk_info['percent'] > threshold
                                    for disk_info in metrics_copy['disk'].values()
                                )
                                
                        if should_call:
                            cb_info['callback'](metric_value)
                            
                    except Exception as e:
                        logger.error(f"Erreur dans le callback pour {metric_name}: {e}")
    
    def get_cpu_usage(self) -> float:
        """
        Récupère l'utilisation actuelle du CPU.
        
        Returns:
            float: Pourcentage d'utilisation du CPU
        """
        with self._metrics_lock:
            return self._metrics['cpu']['usage']
    
    def get_cpu_history(self) -> List[float]:
        """
        Récupère l'historique d'utilisation du CPU.
        
        Returns:
            List[float]: Liste des pourcentages d'utilisation du CPU
        """
        with self._metrics_lock:
            return self._metrics['cpu']['history'].copy()
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Récupère les informations d'utilisation de la mémoire.
        
        Returns:
            Dict: Informations sur l'utilisation de la mémoire
        """
        with self._metrics_lock:
            return self._metrics['memory'].copy()
    
    def get_battery_info(self) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations sur la batterie.
        
        Returns:
            Dict ou None: Informations sur la batterie ou None si non disponible
        """
        with self._metrics_lock:
            return self._metrics['battery']
    
    def get_network_info(self) -> Dict[str, Any]:
        """
        Récupère les informations sur l'utilisation du réseau.
        
        Returns:
            Dict: Informations sur l'utilisation du réseau
        """
        with self._metrics_lock:
            return self._metrics['network'].copy()
    
    def get_disk_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Récupère les informations sur l'utilisation des disques.
        
        Returns:
            Dict: Informations sur l'utilisation des disques par point de montage
        """
        with self._metrics_lock:
            return self._metrics['disk'].copy()
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Récupère les informations générales sur le système.
        
        Returns:
            Dict: Informations sur le système
        """
        system_info = {
            'os': {
                'name': platform.system(),
                'version': platform.version(),
                'platform': platform.platform()
            },
            'python': {
                'version': platform.python_version(),
                'implementation': platform.python_implementation()
            },
            'cpu': {
                'count': psutil.cpu_count(logical=True),
                'physical_count': psutil.cpu_count(logical=False),
                'freq': None
            },
            'boot_time': psutil.boot_time()
        }
        
        try:
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                system_info['cpu']['freq'] = {
                    'current': cpu_freq.current,
                    'min': cpu_freq.min,
                    'max': cpu_freq.max
                }
        except Exception:
            pass
        
        return system_info
    
    def watch_process(self, process_name: str, trigger_type: str = 'any',
                     callback: Callable = None) -> None:
        """
        Surveille un processus spécifique pour les événements de démarrage/arrêt.
        
        Args:
            process_name: Nom du processus à surveiller
            trigger_type: 'start', 'end', ou 'any'
            callback: Fonction à appeler lors d'un événement
        """
        if self._process_manager is None:
            logger.error("ProcessManager non défini, impossible de surveiller le processus")
            return
        
        # Vérifier si le processus est déjà surveillé
        if process_name not in self._watched_processes:
            # Déterminer l'état initial
            currently_running = self._process_manager.find_processes_by_name(process_name)
            
            self._watched_processes[process_name] = {
                'trigger_type': trigger_type,
                'callback': callback,
                'running': len(currently_running) > 0,
                'pids': {proc['pid'] for proc in currently_running}
            }
            
            logger.info(f"Surveillance démarrée pour le processus: {process_name}")
        else:
            # Mettre à jour la configuration
            self._watched_processes[process_name]['trigger_type'] = trigger_type
            if callback:
                self._watched_processes[process_name]['callback'] = callback
    
    def unwatch_process(self, process_name: str) -> None:
        """
        Arrête la surveillance d'un processus.
        
        Args:
            process_name: Nom du processus à ne plus surveiller
        """
        if process_name in self._watched_processes:
            del self._watched_processes[process_name]
            logger.info(f"Surveillance arrêtée pour le processus: {process_name}")
    
    def check_watched_processes(self) -> None:
        """
        Vérifie les changements d'état des processus surveillés.
        """
        if not self._process_manager:
            return
        
        for proc_name, config in list(self._watched_processes.items()):
            try:
                current_procs = self._process_manager.find_processes_by_name(proc_name)
                current_pids = {proc['pid'] for proc in current_procs}
                
                was_running = config['running']
                now_running = len(current_procs) > 0
                
                # Détecter les changements
                if was_running != now_running:
                    event_type = 'start' if now_running else 'end'
                    
                    # Vérifier si le type d'événement correspond au trigger configuré
                    if config['trigger_type'] in ('any', event_type):
                        logger.debug(f"Événement de processus détecté: {proc_name} - {event_type}")
                        
                        # Appeler le callback si défini
                        if config['callback']:
                            try:
                                config['callback']({
                                    'process_name': proc_name,
                                    'event_type': event_type,
                                    'new_pids': current_pids
                                })
                            except Exception as e:
                                logger.error(f"Erreur dans le callback de processus pour {proc_name}: {e}")
                
                # Mettre à jour l'état
                config['running'] = now_running
                config['pids'] = current_pids
                
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du processus {proc_name}: {e}")
    
    def get_system_uptime(self) -> float:
        """
        Récupère le temps écoulé depuis le démarrage du système en secondes.
        
        Returns:
            float: Uptime en secondes
        """
        return time.time() - psutil.boot_time()
