"""
Tests pour l'exécuteur d'actions
-----------------------------
Ces tests vérifient le fonctionnement de l'exécuteur d'actions.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, call
import time

# Ajouter le répertoire principal au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main.core.action_executor import ActionExecutor


class TestActionExecutor(unittest.TestCase):
    """Tests pour la classe ActionExecutor."""
    
    def setUp(self):
        """Configuration avant chaque test."""
        self.action_executor = ActionExecutor()
        
        # Mock pour ProcessManager
        self.process_manager = MagicMock()
        self.action_executor.set_process_manager(self.process_manager)
        
        # Mock pour NotificationManager
        self.notification_manager = MagicMock()
        self.action_executor.set_notification_manager(self.notification_manager)
    
    def test_launch_application(self):
        """Test du lancement d'une application."""
        # Configurer le mock pour retourner True (succès)
        self.process_manager.launch_process.return_value = True
        
        # Tester avec les paramètres minimum
        action = {
            'type': 'launch',
            'params': {
                'path': 'C:/test/app.exe'
            }
        }
        
        result = self.action_executor.execute(action)
        self.assertTrue(result)
        self.process_manager.launch_process.assert_called_once_with(
            'C:/test/app.exe', 
            args=[],
            working_dir=None,
            as_admin=False
        )
        
        # Réinitialiser le mock
        self.process_manager.launch_process.reset_mock()
        
        # Tester avec tous les paramètres
        action = {
            'type': 'launch',
            'params': {
                'path': 'C:/test/app.exe',
                'args': ['--arg1', '--arg2'],
                'working_dir': 'C:/test',
                'as_admin': True
            }
        }
        
        result = self.action_executor.execute(action)
        self.assertTrue(result)
        self.process_manager.launch_process.assert_called_once_with(
            'C:/test/app.exe', 
            args=['--arg1', '--arg2'],
            working_dir='C:/test',
            as_admin=True
        )
    
    def test_launch_without_process_manager(self):
        """Test du lancement sans ProcessManager configuré."""
        # Supprimer le ProcessManager
        self.action_executor._process_manager = None
        
        action = {
            'type': 'launch',
            'params': {
                'path': 'C:/test/app.exe'
            }
        }
        
        # Sans ProcessManager, l'action doit échouer
        result = self.action_executor.execute(action)
        self.assertFalse(result)
    
    def test_launch_without_path(self):
        """Test du lancement sans chemin d'application."""
        action = {
            'type': 'launch',
            'params': {}  # Pas de chemin
        }
        
        # Sans chemin, l'action doit échouer
        result = self.action_executor.execute(action)
        self.assertFalse(result)
    
    def test_kill_application_by_pid(self):
        """Test de l'arrêt d'une application par PID."""
        # Configurer le mock pour retourner True (succès)
        self.process_manager.kill_process_by_pid.return_value = True
        
        action = {
            'type': 'kill',
            'params': {
                'pid': 1234
            }
        }
        
        result = self.action_executor.execute(action)
        self.assertTrue(result)
        self.process_manager.kill_process_by_pid.assert_called_once_with(1234)
    
    def test_kill_application_by_name(self):
        """Test de l'arrêt d'une application par nom."""
        # Configurer le mock pour retourner True (succès)
        self.process_manager.kill_process_by_name.return_value = True
        
        action = {
            'type': 'kill',
            'params': {
                'name': 'app.exe'
            }
        }
        
        result = self.action_executor.execute(action)
        self.assertTrue(result)
        self.process_manager.kill_process_by_name.assert_called_once_with('app.exe')
    
    def test_kill_application_by_window_title(self):
        """Test de l'arrêt d'une application par titre de fenêtre."""
        # Configurer le mock pour retourner True (succès)
        self.process_manager.kill_process_by_window_title.return_value = True
        
        action = {
            'type': 'kill',
            'params': {
                'window_title': 'Application Title'
            }
        }
        
        result = self.action_executor.execute(action)
        self.assertTrue(result)
        self.process_manager.kill_process_by_window_title.assert_called_once_with('Application Title')
    
    def test_kill_without_params(self):
        """Test de l'arrêt sans paramètres d'identification."""
        action = {
            'type': 'kill',
            'params': {}  # Pas de paramètres pour identifier le processus
        }
        
        # Sans paramètres, l'action doit échouer
        result = self.action_executor.execute(action)
        self.assertFalse(result)
    
    def test_wait_action(self):
        """Test de l'action d'attente."""
        action = {
            'type': 'wait',
            'params': {
                'seconds': 0.1  # Courte attente pour le test
            }
        }
        
        start_time = time.time()
        result = self.action_executor.execute(action)
        elapsed_time = time.time() - start_time
        
        self.assertTrue(result)
        self.assertGreaterEqual(elapsed_time, 0.1)  # Vérifier que l'attente a bien eu lieu
    
    def test_wait_with_milliseconds(self):
        """Test de l'action d'attente avec millisecondes."""
        action = {
            'type': 'wait',
            'params': {
                'milliseconds': 100  # 0.1 seconde
            }
        }
        
        start_time = time.time()
        result = self.action_executor.execute(action)
        elapsed_time = time.time() - start_time
        
        self.assertTrue(result)
        self.assertGreaterEqual(elapsed_time, 0.1)
    
    def test_notify_with_notification_manager(self):
        """Test de l'action de notification avec NotificationManager."""
        # Configurer le mock pour retourner True (succès)
        self.notification_manager.send_notification.return_value = True
        
        action = {
            'type': 'notify',
            'params': {
                'title': 'Test Title',
                'message': 'Test Message',
                'level': 'warning',
                'timeout': 10
            }
        }
        
        result = self.action_executor.execute(action)
        self.assertTrue(result)
        self.notification_manager.send_notification.assert_called_once_with(
            title='Test Title',
            message='Test Message',
            level='warning',
            timeout=10
        )
    
    @patch('subprocess.run')
    def test_execute_command(self, mock_run):
        """Test de l'exécution d'une commande shell."""
        # Configurer le mock pour retourner un objet avec returncode=0 (succès)
        mock_run.return_value.returncode = 0
        
        action = {
            'type': 'execute_command',
            'params': {
                'command': 'echo test',
                'shell': True,
                'working_dir': '/tmp'
            }
        }
        
        result = self.action_executor.execute(action)
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            'echo test',
            shell=True,
            cwd='/tmp',
            check=False,
            capture_output=False,
            text=True
        )
    
    @patch('subprocess.run')
    def test_execute_command_failure(self, mock_run):
        """Test de l'échec d'une commande shell."""
        # Configurer le mock pour retourner un objet avec returncode=1 (échec)
        mock_run.return_value.returncode = 1
        
        action = {
            'type': 'execute_command',
            'params': {
                'command': 'invalid_command',
                'require_success': True  # Exiger la réussite
            }
        }
        
        result = self.action_executor.execute(action)
        self.assertFalse(result)  # L'action doit échouer
    
    def test_custom_action(self):
        """Test d'une action personnalisée."""
        # Créer une fonction mock pour l'action personnalisée
        mock_action = MagicMock(return_value=True)
        
        # Enregistrer l'action personnalisée
        self.action_executor.register_custom_action('custom', mock_action)
        
        # Tester l'action
        action = {
            'type': 'custom',
            'params': {
                'arg1': 'value1',
                'arg2': 'value2'
            }
        }
        
        result = self.action_executor.execute(action)
        self.assertTrue(result)
        mock_action.assert_called_once_with({'arg1': 'value1', 'arg2': 'value2'})
    
    def test_unsupported_action(self):
        """Test d'une action non supportée."""
        action = {
            'type': 'unsupported_action',
            'params': {}
        }
        
        result = self.action_executor.execute(action)
        self.assertFalse(result)
    
    def test_invalid_action_format(self):
        """Test avec un format d'action invalide."""
        # Sans type
        action = {'params': {}}
        result = self.action_executor.execute(action)
        self.assertFalse(result)
        
        # Non dictionnaire
        action = "not a dict"
        result = self.action_executor.execute(action)
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
