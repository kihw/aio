"""
Tests pour le monitoring système (system_monitor.py)
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ajout du chemin parent pour pouvoir importer les modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.system_monitor import SystemMonitor

class TestSystemMonitor(unittest.TestCase):
    def setUp(self):
        # Créer l'instance du SystemMonitor
        self.system_monitor = SystemMonitor()

    @patch('psutil.cpu_percent')
    def test_get_cpu_usage(self, mock_cpu_percent):
        # Configurer le mock
        mock_cpu_percent.return_value = 45.5

        # Tester la fonction
        result = self.system_monitor.get_cpu_usage()
        
        # Vérifier les résultats
        self.assertEqual(result, 45.5)
        mock_cpu_percent.assert_called_once_with(interval=0.1)

    @patch('psutil.virtual_memory')
    def test_get_memory_usage(self, mock_virtual_memory):
        # Configurer le mock
        mock_memory = MagicMock()
        mock_memory.percent = 65.7
        mock_virtual_memory.return_value = mock_memory

        # Tester la fonction
        result = self.system_monitor.get_memory_usage()
        
        # Vérifier les résultats
        self.assertEqual(result, 65.7)
        mock_virtual_memory.assert_called_once()
    
    @patch('psutil.sensors_battery')
    def test_get_battery_level(self, mock_sensors_battery):
        # Cas avec batterie
        mock_battery = MagicMock()
        mock_battery.percent = 75
        mock_sensors_battery.return_value = mock_battery

        result = self.system_monitor.get_battery_level()
        self.assertEqual(result, 75)
        
        # Cas sans batterie
        mock_sensors_battery.return_value = None
        result = self.system_monitor.get_battery_level()
        self.assertEqual(result, 100)  # Devrait retourner 100% par défaut si pas de batterie
    
    @patch('psutil.sensors_battery')
    def test_is_power_connected(self, mock_sensors_battery):
        # Cas avec batterie branchée
        mock_battery = MagicMock()
        mock_battery.power_plugged = True
        mock_sensors_battery.return_value = mock_battery

        result = self.system_monitor.is_power_connected()
        self.assertTrue(result)
        
        # Cas avec batterie débranchée
        mock_battery.power_plugged = False
        result = self.system_monitor.is_power_connected()
        self.assertFalse(result)
        
        # Cas sans batterie
        mock_sensors_battery.return_value = None
        result = self.system_monitor.is_power_connected()
        self.assertTrue(result)  # Devrait retourner True par défaut si pas de batterie
    
    @patch('psutil.net_if_stats')
    def test_get_network_status(self, mock_net_if_stats):
        # Configurer le mock avec plusieurs interfaces
        mock_stats = {
            'eth0': MagicMock(isup=True),
            'wlan0': MagicMock(isup=False),
            'lo': MagicMock(isup=True)
        }
        mock_net_if_stats.return_value = mock_stats

        # Tester la fonction
        result = self.system_monitor.get_network_status()
        
        # Vérifier les résultats
        self.assertTrue(result['connected'])
        self.assertEqual(result['interfaces']['eth0'], True)
        self.assertEqual(result['interfaces']['wlan0'], False)
        self.assertEqual(result['interfaces']['lo'], True)
        
        # Cas où aucune interface n'est active
        mock_stats = {
            'eth0': MagicMock(isup=False),
            'wlan0': MagicMock(isup=False),
            'lo': MagicMock(isup=False)
        }
        mock_net_if_stats.return_value = mock_stats
        
        result = self.system_monitor.get_network_status()
        self.assertFalse(result['connected'])
    
    @patch('psutil.disk_usage')
    def test_get_disk_usage(self, mock_disk_usage):
        # Configurer le mock
        mock_usage = MagicMock()
        mock_usage.percent = 82.5
        mock_disk_usage.return_value = mock_usage

        # Tester la fonction
        result = self.system_monitor.get_disk_usage('/')
        
        # Vérifier les résultats
        self.assertEqual(result, 82.5)
        mock_disk_usage.assert_called_once_with('/')
    
    @patch('psutil.net_io_counters')
    def test_get_network_io(self, mock_net_io_counters):
        # Premier appel pour initialiser les compteurs
        mock_counters = MagicMock()
        mock_counters.bytes_sent = 1000
        mock_counters.bytes_recv = 2000
        mock_net_io_counters.return_value = mock_counters
        
        # Premier appel, devrait initialiser sans retourner de vitesse
        result = self.system_monitor.get_network_io()
        self.assertEqual(result, {'bytes_sent': 1000, 'bytes_recv': 2000, 'upload_speed': 0, 'download_speed': 0})
        
        # Simuler un passage du temps (1 seconde)
        self.system_monitor.last_net_io_time = self.system_monitor.last_net_io_time - 1
        
        # Deuxième appel avec nouvelles valeurs
        mock_counters.bytes_sent = 1500  # +500 bytes en 1 seconde
        mock_counters.bytes_recv = 4000  # +2000 bytes en 1 seconde
        result = self.system_monitor.get_network_io()
        
        # Vérifier les vitesses calculées
        self.assertEqual(result['bytes_sent'], 1500)
        self.assertEqual(result['bytes_recv'], 4000)
        self.assertEqual(result['upload_speed'], 500)  # 500 bytes/sec
        self.assertEqual(result['download_speed'], 2000)  # 2000 bytes/sec
    
    @patch('psutil.cpu_count')
    @patch('psutil.cpu_percent')
    def test_get_detailed_cpu_info(self, mock_cpu_percent, mock_cpu_count):
        # Configurer les mocks
        mock_cpu_count.return_value = 8
        mock_cpu_percent.return_value = [45.5, 25.3, 10.2, 60.7, 30.5, 15.8, 70.2, 5.6]

        # Tester la fonction
        result = self.system_monitor.get_detailed_cpu_info()
        
        # Vérifier les résultats
        self.assertEqual(result['total_cores'], 8)
        self.assertEqual(result['per_core_usage'][0], 45.5)
        self.assertEqual(result['per_core_usage'][7], 5.6)
        self.assertAlmostEqual(result['average_usage'], 33.0, places=1)  # Moyenne des 8 valeurs
        mock_cpu_count.assert_called_once_with(logical=True)
        mock_cpu_percent.assert_called_once_with(interval=0.1, percpu=True)
    
    @patch('psutil.process_iter')
    def test_get_top_processes(self, mock_process_iter):
        # Créer des mock de processus
        mock_processes = [
            MagicMock(info={'pid': 1, 'name': 'process1', 'cpu_percent': 20.0, 'memory_percent': 15.0}),
            MagicMock(info={'pid': 2, 'name': 'process2', 'cpu_percent': 50.0, 'memory_percent': 25.0}),
            MagicMock(info={'pid': 3, 'name': 'process3', 'cpu_percent': 10.0, 'memory_percent': 35.0}),
            MagicMock(info={'pid': 4, 'name': 'process4', 'cpu_percent': 30.0, 'memory_percent': 10.0}),
            MagicMock(info={'pid': 5, 'name': 'process5', 'cpu_percent': 5.0, 'memory_percent': 5.0})
        ]
        
        # Configurer le mock pour retourner les infos directement
        for proc in mock_processes:
            proc.as_dict.return_value = proc.info
        
        mock_process_iter.return_value = mock_processes
        
        # Tester la fonction avec tri par CPU
        result = self.system_monitor.get_top_processes(3, sort_by='cpu')
        
        # Vérifier les résultats
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['pid'], 2)  # Le plus grand CPU
        self.assertEqual(result[1]['pid'], 4)
        self.assertEqual(result[2]['pid'], 1)
        
        # Tester la fonction avec tri par mémoire
        result = self.system_monitor.get_top_processes(3, sort_by='memory')
        
        # Vérifier les résultats
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['pid'], 3)  # La plus grande mémoire
        self.assertEqual(result[1]['pid'], 2)
        self.assertEqual(result[2]['pid'], 1)
    
    def tearDown(self):
        # Nettoyage
        self.system_monitor = None


if __name__ == '__main__':
    unittest.main()
