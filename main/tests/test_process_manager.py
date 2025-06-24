"""
Tests pour le gestionnaire de processus (process_manager.py)
"""

import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os
import psutil

# Ajout du chemin parent pour pouvoir importer les modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.process_manager import ProcessManager

class TestProcessManager(unittest.TestCase):
    def setUp(self):
        # Initialiser le gestionnaire de processus
        self.process_manager = ProcessManager()
        
        # Mock pour les processus
        self.mock_process = MagicMock()
        self.mock_process.name.return_value = "test_app.exe"
        self.mock_process.pid = 12345
        self.mock_process.create_time.return_value = 1622548800
        self.mock_process.cpu_percent.return_value = 5.0
        self.mock_process.memory_percent.return_value = 2.5
        self.mock_process.status.return_value = "running"
        self.mock_process.cmdline.return_value = ["test_app.exe", "--arg1", "--arg2"]

    @patch('psutil.process_iter')
    def test_get_running_processes(self, mock_process_iter):
        # Configurer le mock pour retourner une liste de processus
        mock_process_iter.return_value = [self.mock_process]
        
        # Tester la récupération des processus en cours d'exécution
        processes = self.process_manager.get_running_processes()
        
        # Vérifier que la liste contient un processus avec les informations correctes
        self.assertEqual(len(processes), 1)
        self.assertEqual(processes[0]['name'], "test_app.exe")
        self.assertEqual(processes[0]['pid'], 12345)
        self.assertEqual(processes[0]['cpu_percent'], 5.0)
        self.assertEqual(processes[0]['memory_percent'], 2.5)
        self.assertEqual(processes[0]['status'], "running")
    
    @patch('psutil.process_iter')
    def test_find_process_by_name(self, mock_process_iter):
        # Configurer le mock pour retourner une liste de processus
        mock_process_iter.return_value = [self.mock_process]
        
        # Tester la recherche de processus par nom
        process = self.process_manager.find_process_by_name("test_app")
        
        # Vérifier que le processus retourné a le bon pid
        self.assertIsNotNone(process)
        self.assertEqual(process.pid, 12345)
        
        # Tester avec un nom qui n'existe pas
        process = self.process_manager.find_process_by_name("nonexistent_app")
        self.assertIsNone(process)
    
    @patch('subprocess.Popen')
    def test_start_process(self, mock_popen):
        # Configurer le mock pour subprocess.Popen
        mock_process = MagicMock()
        mock_process.pid = 67890
        mock_popen.return_value = mock_process
        
        # Tester le démarrage d'un processus
        pid = self.process_manager.start_process("notepad.exe", ["file.txt"])
        
        # Vérifier que subprocess.Popen a été appelé correctement
        mock_popen.assert_called_once_with(["notepad.exe", "file.txt"], 
                                          shell=False, 
                                          stdout=unittest.mock.ANY, 
                                          stderr=unittest.mock.ANY)
        
        # Vérifier que le pid retourné est correct
        self.assertEqual(pid, 67890)
    
    @patch('psutil.Process')
    def test_kill_process_by_pid(self, mock_psutil_process):
        # Configurer le mock pour psutil.Process
        mock_process = MagicMock()
        mock_psutil_process.return_value = mock_process
        
        # Tester la fermeture d'un processus par pid
        self.process_manager.kill_process_by_pid(12345)
        
        # Vérifier que psutil.Process a été appelé avec le bon pid
        mock_psutil_process.assert_called_once_with(12345)
        
        # Vérifier que terminate() a été appelé sur le processus
        mock_process.terminate.assert_called_once()
    
    @patch('psutil.process_iter')
    @patch('utils.process_manager.ProcessManager.kill_process_by_pid')
    def test_kill_process_by_name(self, mock_kill_by_pid, mock_process_iter):
        # Configurer le mock pour process_iter
        mock_process_iter.return_value = [self.mock_process]
        
        # Tester la fermeture d'un processus par nom
        result = self.process_manager.kill_process_by_name("test_app")
        
        # Vérifier que kill_process_by_pid a été appelé avec le bon pid
        mock_kill_by_pid.assert_called_once_with(12345)
        
        # Vérifier que la fonction retourne True
        self.assertTrue(result)
        
        # Tester avec un nom qui n'existe pas
        mock_kill_by_pid.reset_mock()
        mock_process_iter.return_value = []
        result = self.process_manager.kill_process_by_name("nonexistent_app")
        
        # Vérifier que kill_process_by_pid n'a pas été appelé
        mock_kill_by_pid.assert_not_called()
        
        # Vérifier que la fonction retourne False
        self.assertFalse(result)
    
    @patch('psutil.process_iter')
    def test_get_process_info(self, mock_process_iter):
        # Configurer le mock pour retourner une liste de processus
        mock_process_iter.return_value = [self.mock_process]
        
        # Tester la récupération des informations d'un processus par pid
        info = self.process_manager.get_process_info(12345)
        
        # Vérifier que les informations sont correctes
        self.assertIsNotNone(info)
        self.assertEqual(info['name'], "test_app.exe")
        self.assertEqual(info['pid'], 12345)
        self.assertEqual(info['cpu_percent'], 5.0)
        self.assertEqual(info['memory_percent'], 2.5)
        self.assertEqual(info['status'], "running")
        self.assertEqual(info['command_line'], ["test_app.exe", "--arg1", "--arg2"])
        
        # Tester avec un pid qui n'existe pas
        # Configurer le mock pour lever une exception
        mock_process_iter.side_effect = lambda attrs: []
        
        info = self.process_manager.get_process_info(99999)
        self.assertIsNone(info)
    
    @patch('psutil.Process')
    def test_is_process_running(self, mock_psutil_process):
        # Test pour un processus en cours d'exécution
        mock_process = MagicMock()
        mock_psutil_process.return_value = mock_process
        
        self.assertTrue(self.process_manager.is_process_running(12345))
        
        # Test pour un processus qui n'existe plus
        mock_psutil_process.side_effect = psutil.NoSuchProcess(99999)
        
        self.assertFalse(self.process_manager.is_process_running(99999))
    
    @patch('utils.process_manager.ProcessManager.get_running_processes')
    def test_get_resource_usage(self, mock_get_running):
        # Configurer le mock pour retourner une liste de processus avec informations de ressources
        mock_get_running.return_value = [
            {
                'name': 'app1.exe',
                'pid': 1000,
                'cpu_percent': 10.0,
                'memory_percent': 5.0
            },
            {
                'name': 'app2.exe',
                'pid': 2000,
                'cpu_percent': 20.0,
                'memory_percent': 15.0
            }
        ]
        
        # Tester la récupération d'utilisation des ressources
        usage = self.process_manager.get_resource_usage()
        
        # Vérifier que les totaux sont corrects
        self.assertEqual(usage['total_cpu'], 30.0)
        self.assertEqual(usage['total_memory'], 20.0)
        self.assertEqual(len(usage['processes']), 2)
        
        # Vérifier que les processus sont triés par utilisation CPU
        self.assertEqual(usage['processes'][0]['pid'], 2000)  # app2 utilise plus de CPU
        self.assertEqual(usage['processes'][1]['pid'], 1000)  # app1 utilise moins de CPU
    
    def tearDown(self):
        # Nettoyage
        self.process_manager = None


if __name__ == '__main__':
    unittest.main()
