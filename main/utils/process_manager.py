"""
Process Manager - Gestionnaire de processus
------------------------------------------
Ce module gère la détection, le lancement et l'arrêt des processus système.
Il fournit une abstraction pour interagir avec les processus de manière cohérente
sur différentes plateformes.
"""

import os
import sys
import psutil
import logging
import platform
import subprocess
import time
from typing import List, Dict, Any, Optional, Union, Tuple, Set
import re

logger = logging.getLogger(__name__)

class ProcessManager:
    """
    Gestionnaire de processus système multiplateforme.
    """
    
    def __init__(self):
        """
        Initialise le gestionnaire de processus.
        """
        self.os_type = platform.system().lower()  # 'windows', 'linux', 'darwin'
        self._watched_processes: Dict[str, Dict[str, Any]] = {}
        self._last_process_list: Dict[int, str] = {}  # PID -> nom
        self._process_change_callbacks: List = []
    
    def get_running_processes(self) -> List[Dict[str, Any]]:
        """
        Récupère la liste des processus en cours d'exécution.
        
        Returns:
            List[Dict]: Liste des processus avec leurs informations
        """
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_info', 'cpu_percent']):
                process_info = proc.info
                
                # Ajout d'informations supplémentaires
                try:
                    process_info['exe'] = proc.exe()
                except (psutil.AccessDenied, psutil.ZombieProcess, FileNotFoundError):
                    process_info['exe'] = ''
                
                try:
                    process_info['command_line'] = proc.cmdline()
                except (psutil.AccessDenied, psutil.ZombieProcess):
                    process_info['command_line'] = []
                
                try:
                    process_info['create_time'] = proc.create_time()
                except (psutil.AccessDenied, psutil.ZombieProcess):
                    process_info['create_time'] = 0
                
                processes.append(process_info)
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des processus: {e}")
            
        return processes
    
    def find_processes_by_name(self, name: str) -> List[Dict[str, Any]]:
        """
        Recherche des processus par leur nom.
        
        Args:
            name: Nom ou partie du nom du processus à rechercher (insensible à la casse)
            
        Returns:
            List[Dict]: Liste des processus correspondants
        """
        matches = []
        name_lower = name.lower()
        
        for proc in self.get_running_processes():
            proc_name = proc.get('name', '').lower()
            
            if name_lower in proc_name:
                matches.append(proc)
                
        return matches
    
    def find_process_by_pid(self, pid: int) -> Optional[Dict[str, Any]]:
        """
        Recherche un processus par son PID.
        
        Args:
            pid: PID du processus à rechercher
            
        Returns:
            Dict ou None: Informations sur le processus ou None si non trouvé
        """
        try:
            proc = psutil.Process(pid)
            
            process_info = {
                'pid': proc.pid,
                'name': proc.name(),
                'exe': '',
                'command_line': []
            }
            
            try:
                process_info['exe'] = proc.exe()
                process_info['command_line'] = proc.cmdline()
            except (psutil.AccessDenied, psutil.ZombieProcess, FileNotFoundError):
                pass
                
            return process_info
            
        except psutil.NoSuchProcess:
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la recherche du processus {pid}: {e}")
            return None
    
    def find_processes_by_window_title(self, title_pattern: str) -> List[Dict[str, Any]]:
        """
        Recherche des processus par le titre de leur fenêtre.
        
        Args:
            title_pattern: Motif à rechercher dans les titres de fenêtre
            
        Returns:
            List[Dict]: Liste des processus correspondants
        """
        matches = []
        
        try:
            # Windows
            if self.os_type == 'windows':
                import win32gui
                import win32process
                
                def enum_windows_callback(hwnd, results):
                    if win32gui.IsWindowVisible(hwnd):
                        window_title = win32gui.GetWindowText(hwnd)
                        if title_pattern.lower() in window_title.lower():
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            process = self.find_process_by_pid(pid)
                            if process:
                                process['window_title'] = window_title
                                results.append(process)
                
                win32gui.EnumWindows(enum_windows_callback, matches)
            
            # macOS
            elif self.os_type == 'darwin':
                # Utiliser AppleScript pour obtenir les fenêtres
                script = """
                tell application "System Events"
                    set allWindows to {}
                    repeat with proc in (every process whose background only is false)
                        set procName to name of proc
                        repeat with w in (every window of proc)
                            set windowTitle to ""
                            try
                                set windowTitle to name of w
                            end try
                            set end of allWindows to {procName, windowTitle}
                        end repeat
                    end repeat
                    return allWindows
                end tell
                """
                windows_info = subprocess.check_output(['osascript', '-e', script], text=True)
                
                for line in windows_info.splitlines():
                    if title_pattern.lower() in line.lower():
                        # Extraction du nom du processus
                        proc_name = line.split(',')[0].strip()
                        procs = self.find_processes_by_name(proc_name)
                        
                        for proc in procs:
                            if proc not in matches:  # Éviter les doublons
                                proc['window_title'] = line
                                matches.append(proc)
            
            # Linux (X11)
            elif self.os_type == 'linux':
                try:
                    # Nécessite xdotool
                    output = subprocess.check_output(['xdotool', 'search', '--name', title_pattern, 'getwindowpid'], text=True)
                    
                    for pid_str in output.splitlines():
                        try:
                            pid = int(pid_str.strip())
                            process = self.find_process_by_pid(pid)
                            if process:
                                # Obtenir le titre de la fenêtre
                                window_title = subprocess.check_output(
                                    ['xdotool', 'getwindowname', subprocess.check_output(['xdotool', 'search', '--pid', str(pid)], text=True).strip()],
                                    text=True
                                ).strip()
                                process['window_title'] = window_title
                                matches.append(process)
                        except (ValueError, subprocess.SubprocessError):
                            continue
                            
                except (FileNotFoundError, subprocess.SubprocessError):
                    logger.warning("xdotool non disponible pour la recherche de fenêtres sous Linux")
        
        except ImportError as e:
            logger.error(f"Bibliothèque manquante pour la recherche par titre de fenêtre: {e}")
        except Exception as e:
            logger.error(f"Erreur lors de la recherche par titre de fenêtre: {e}")
            
        return matches
    
    def launch_process(self, path: str, args: List[str] = None, 
                      working_dir: str = None, as_admin: bool = False) -> bool:
        """
        Lance un processus.
        
        Args:
            path: Chemin vers l'exécutable
            args: Arguments à passer au processus
            working_dir: Répertoire de travail
            as_admin: Lancer avec des droits administrateur
            
        Returns:
            bool: True si le processus a été lancé avec succès
        """
        if args is None:
            args = []
            
        try:
            cmd = [path] + args
            
            # Gérer le lancement avec droits administrateur
            if as_admin:
                if self.os_type == 'windows':
                    from subprocess import CREATE_NEW_CONSOLE
                    import ctypes
                    if ctypes.windll.shell32.IsUserAnAdmin():
                        # Déjà admin, lancer normalement
                        subprocess.Popen(cmd, cwd=working_dir, creationflags=CREATE_NEW_CONSOLE)
                    else:
                        # Utiliser ShellExecute pour demander l'élévation UAC
                        cmd_str = f'"{path}" ' + ' '.join(f'"{arg}"' for arg in args)
                        ctypes.windll.shell32.ShellExecuteW(None, "runas", path, ' '.join(args), working_dir, 1)
                elif self.os_type == 'linux':
                    if working_dir:
                        cmd = ['cd', working_dir, '&&', 'sudo'] + cmd
                    else:
                        cmd = ['sudo'] + cmd
                    subprocess.Popen(['xterm', '-e', ' '.join(cmd)])
                elif self.os_type == 'darwin':
                    cmd = ['osascript', '-e', f'do shell script "{path} {" ".join(args)}" with administrator privileges']
                    subprocess.Popen(cmd)
                else:
                    logger.error(f"Lancement avec droits admin non supporté sur {self.os_type}")
                    return False
            else:
                # Lancement normal
                subprocess.Popen(cmd, cwd=working_dir)
                
            logger.info(f"Processus lancé: {path} {' '.join(args)}")
            return True
            
        except FileNotFoundError:
            logger.error(f"Fichier non trouvé: {path}")
            return False
        except Exception as e:
            logger.error(f"Erreur lors du lancement du processus: {e}")
            return False
    
    def kill_process_by_pid(self, pid: int) -> bool:
        """
        Arrête un processus par son PID.
        
        Args:
            pid: PID du processus à arrêter
            
        Returns:
            bool: True si le processus a été arrêté avec succès
        """
        try:
            process = psutil.Process(pid)
            process.terminate()
            
            # Attendre que le processus se termine
            try:
                process.wait(timeout=3)
            except psutil.TimeoutExpired:
                # Si le processus ne se termine pas, le tuer
                process.kill()
            
            logger.info(f"Processus {pid} arrêté")
            return True
            
        except psutil.NoSuchProcess:
            logger.warning(f"Processus {pid} non trouvé")
            return False
        except psutil.AccessDenied:
            logger.error(f"Accès refusé pour arrêter le processus {pid}")
            return False
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du processus {pid}: {e}")
            return False
    
    def kill_process_by_name(self, name: str) -> bool:
        """
        Arrête tous les processus correspondant à un nom.
        
        Args:
            name: Nom du processus à arrêter
            
        Returns:
            bool: True si au moins un processus a été arrêté
        """
        processes = self.find_processes_by_name(name)
        
        if not processes:
            logger.warning(f"Aucun processus trouvé avec le nom {name}")
            return False
            
        success = False
        
        for proc in processes:
            if self.kill_process_by_pid(proc['pid']):
                success = True
                
        return success
    
    def kill_process_by_window_title(self, title_pattern: str) -> bool:
        """
        Arrête tous les processus ayant une fenêtre avec un titre correspondant.
        
        Args:
            title_pattern: Motif à rechercher dans les titres de fenêtre
            
        Returns:
            bool: True si au moins un processus a été arrêté
        """
        processes = self.find_processes_by_window_title(title_pattern)
        
        if not processes:
            logger.warning(f"Aucun processus trouvé avec une fenêtre contenant '{title_pattern}'")
            return False
            
        success = False
        
        for proc in processes:
            if self.kill_process_by_pid(proc['pid']):
                success = True
                
        return success
    
    def register_process_change_callback(self, callback) -> None:
        """
        Enregistre une fonction de rappel à appeler lors des changements de processus.
        
        Args:
            callback: Fonction à appeler avec les processus démarrés et arrêtés
        """
        if callback not in self._process_change_callbacks:
            self._process_change_callbacks.append(callback)
    
    def unregister_process_change_callback(self, callback) -> None:
        """
        Désenregistre une fonction de rappel.
        
        Args:
            callback: Fonction à supprimer
        """
        if callback in self._process_change_callbacks:
            self._process_change_callbacks.remove(callback)
    
    def watch_process_changes(self, interval: float = 2.0) -> None:
        """
        Démarre la surveillance des changements de processus dans un thread séparé.
        
        Args:
            interval: Intervalle entre les vérifications en secondes
        """
        import threading
        
        def watcher():
            while True:
                try:
                    current_processes = {}
                    
                    for proc in psutil.process_iter(['pid', 'name']):
                        current_processes[proc.info['pid']] = proc.info['name']
                    
                    # Détecter les processus démarrés et arrêtés
                    started = {}
                    ended = {}
                    
                    for pid, name in current_processes.items():
                        if pid not in self._last_process_list:
                            started[pid] = name
                    
                    for pid, name in self._last_process_list.items():
                        if pid not in current_processes:
                            ended[pid] = name
                    
                    # Notifier les changements
                    if started or ended:
                        for callback in self._process_change_callbacks:
                            try:
                                callback(started, ended)
                            except Exception as e:
                                logger.error(f"Erreur dans le callback de changement de processus: {e}")
                    
                    # Mettre à jour la liste
                    self._last_process_list = current_processes.copy()
                    
                except Exception as e:
                    logger.error(f"Erreur lors de la surveillance des processus: {e}")
                    
                time.sleep(interval)
        
        # Initialiser la liste des processus
        for proc in psutil.process_iter(['pid', 'name']):
            self._last_process_list[proc.info['pid']] = proc.info['name']
        
        # Démarrer le thread de surveillance
        watcher_thread = threading.Thread(target=watcher, daemon=True)
        watcher_thread.start()
        
        logger.info("Surveillance des changements de processus démarrée")
    
    def is_process_running(self, process_identifier: Union[int, str]) -> bool:
        """
        Vérifie si un processus est en cours d'exécution.
        
        Args:
            process_identifier: PID ou nom du processus
            
        Returns:
            bool: True si le processus est en cours d'exécution
        """
        if isinstance(process_identifier, int):
            # Vérifier par PID
            return self.find_process_by_pid(process_identifier) is not None
        else:
            # Vérifier par nom
            return len(self.find_processes_by_name(process_identifier)) > 0
