"""
Tests pour le gestionnaire de triggers (trigger_manager.py)
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import datetime

# Ajout du chemin parent pour pouvoir importer les modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.trigger_manager import TriggerManager
from utils.system_monitor import SystemMonitor

class TestTriggerManager(unittest.TestCase):
    def setUp(self):
        # Créer un mock pour SystemMonitor
        self.system_monitor_mock = MagicMock(spec=SystemMonitor)
        self.system_monitor_mock.get_cpu_usage.return_value = 30.0
        self.system_monitor_mock.get_memory_usage.return_value = 40.0
        self.system_monitor_mock.get_battery_level.return_value = 75
        self.system_monitor_mock.is_power_connected.return_value = True
        self.system_monitor_mock.get_network_status.return_value = {'connected': True, 'type': 'wifi'}
        
        # Initialiser le TriggerManager avec le mock
        self.trigger_manager = TriggerManager(self.system_monitor_mock)
        
        # Règle de test
        self.test_rule = {
            'name': 'Test Rule',
            'trigger': {
                'type': 'time',
                'schedule': '09:00'
            },
            'condition': {
                'weekday': [1, 2, 3, 4, 5]
            },
            'actions': {
                'launch': {
                    'app': 'notepad'
                }
            },
            'enabled': True
        }

    def test_initialize_time_triggers(self):
        # Test règle avec trigger de type 'time'
        self.trigger_manager.initialize_triggers([self.test_rule])
        self.assertEqual(len(self.trigger_manager.time_triggers), 1)
        
    def test_initialize_cpu_triggers(self):
        # Test règle avec trigger de type 'cpu'
        cpu_rule = {
            'name': 'CPU Rule',
            'trigger': {
                'type': 'cpu',
                'level': 'above',
                'threshold': 80,
                'duration': 10
            },
            'actions': {'notify': {'title': 'CPU Alert'}},
            'enabled': True
        }
        
        self.trigger_manager.initialize_triggers([cpu_rule])
        self.assertEqual(len(self.trigger_manager.system_triggers), 1)
    
    def test_initialize_battery_triggers(self):
        # Test règle avec trigger de type 'battery'
        battery_rule = {
            'name': 'Battery Rule',
            'trigger': {
                'type': 'battery',
                'level': 'below',
                'threshold': 20
            },
            'actions': {'notify': {'title': 'Battery Low'}},
            'enabled': True
        }
        
        self.trigger_manager.initialize_triggers([battery_rule])
        self.assertEqual(len(self.trigger_manager.system_triggers), 1)
    
    @patch('core.trigger_manager.datetime')
    def test_check_time_trigger(self, mock_datetime):
        # Mock pour tester le déclenchement d'un trigger temporel
        mock_now = MagicMock()
        mock_now.hour = 9
        mock_now.minute = 0
        mock_datetime.datetime.now.return_value = mock_now
        mock_datetime.datetime.strptime.return_value = datetime.datetime(2023, 1, 1, 9, 0)
        
        # Mock pour le jour de la semaine (Monday = 0)
        mock_now.weekday.return_value = 0
        
        self.trigger_manager.initialize_triggers([self.test_rule])
        triggered_rules = self.trigger_manager.check_time_triggers()
        
        self.assertEqual(len(triggered_rules), 1)
        self.assertEqual(triggered_rules[0]['name'], 'Test Rule')
    
    def test_check_cpu_trigger(self):
        # Test pour un déclencheur CPU
        cpu_rule = {
            'name': 'CPU Rule',
            'trigger': {
                'type': 'cpu',
                'level': 'above',
                'threshold': 20,  # Mettre à 20 pour que le test passe (CPU à 30%)
                'duration': 1
            },
            'actions': {'notify': {'title': 'CPU Alert'}},
            'enabled': True
        }
        
        self.trigger_manager.initialize_triggers([cpu_rule])
        
        # Premier appel devrait stocker l'heure de détection mais ne pas déclencher
        triggered_rules = self.trigger_manager.check_system_triggers()
        self.assertEqual(len(triggered_rules), 0)
        
        # Simulons le passage du temps pour dépasser la durée
        self.trigger_manager.triggers_detected_time[cpu_rule['name']] = datetime.datetime.now() - datetime.timedelta(seconds=5)
        
        # Deuxième appel devrait déclencher la règle
        triggered_rules = self.trigger_manager.check_system_triggers()
        self.assertEqual(len(triggered_rules), 1)
        
    def test_check_battery_trigger(self):
        # Test pour un déclencheur batterie
        battery_rule = {
            'name': 'Battery Rule',
            'trigger': {
                'type': 'battery',
                'level': 'below',
                'threshold': 80
            },
            'actions': {'notify': {'title': 'Battery Low'}},
            'enabled': True
        }
        
        self.trigger_manager.initialize_triggers([battery_rule])
        triggered_rules = self.trigger_manager.check_system_triggers()
        
        self.assertEqual(len(triggered_rules), 1)
        self.assertEqual(triggered_rules[0]['name'], 'Battery Rule')
    
    def test_disabled_rule_not_triggered(self):
        # Une règle désactivée ne devrait pas être déclenchée
        disabled_rule = dict(self.test_rule)
        disabled_rule['enabled'] = False
        
        self.trigger_manager.initialize_triggers([disabled_rule])
        triggered_rules = self.trigger_manager.check_time_triggers()
        
        self.assertEqual(len(triggered_rules), 0)
    
    @patch('core.trigger_manager.datetime')
    def test_check_condition_weekday(self, mock_datetime):
        # Mock pour tester une condition de jour de semaine
        mock_now = MagicMock()
        mock_now.weekday.return_value = 0  # Monday
        mock_datetime.datetime.now.return_value = mock_now
        
        # Règle avec condition de jour de semaine (Lundi à Vendredi)
        rule = {
            'name': 'Weekday Rule',
            'condition': {
                'weekday': [1, 2, 3, 4, 5]
            },
            'enabled': True
        }
        
        # Jour actuel non dans la condition (0=Lundi, mais la condition spécifie 1-5)
        self.assertFalse(self.trigger_manager.check_conditions(rule))
        
        # Changer le mock pour un jour dans la condition
        mock_now.weekday.return_value = 1  # Tuesday
        self.assertTrue(self.trigger_manager.check_conditions(rule))
    
    def test_check_condition_time_range(self):
        # Test pour une condition de plage horaire
        with patch('core.trigger_manager.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.hour = 10
            mock_now.minute = 30
            mock_datetime.datetime.now.return_value = mock_now
            mock_datetime.datetime.strptime.side_effect = lambda time_str, fmt: {
                '09:00': datetime.datetime(2023, 1, 1, 9, 0),
                '17:00': datetime.datetime(2023, 1, 1, 17, 0)
            }.get(time_str)
            
            rule = {
                'name': 'Time Range Rule',
                'condition': {
                    'time_range': {
                        'start': '09:00',
                        'end': '17:00'
                    }
                },
                'enabled': True
            }
            
            # Heure actuelle dans la plage
            self.assertTrue(self.trigger_manager.check_conditions(rule))
            
            # Changer l'heure à l'extérieur de la plage
            mock_now.hour = 8
            self.assertFalse(self.trigger_manager.check_conditions(rule))
    
    def test_check_condition_battery(self):
        # Test pour une condition de batterie
        rule = {
            'name': 'Battery Condition Rule',
            'condition': {
                'battery_level': {
                    'min': 50,
                    'max': 80
                },
                'power_connected': True
            },
            'enabled': True
        }
        
        # La batterie est à 75% et l'alimentation est connectée - devrait passer
        self.assertTrue(self.trigger_manager.check_conditions(rule))
        
        # Changer la condition d'alimentation
        rule['condition']['power_connected'] = False
        self.assertFalse(self.trigger_manager.check_conditions(rule))
    
    def tearDown(self):
        # Nettoyage
        self.trigger_manager = None
        self.system_monitor_mock = None


if __name__ == '__main__':
    unittest.main()
