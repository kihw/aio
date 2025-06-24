"""
Tests pour le moteur de règles
----------------------------
Ces tests vérifient le fonctionnement du moteur de règles.
"""

import os
import sys
import unittest
import yaml
from unittest.mock import MagicMock, patch

# Ajouter le répertoire principal au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main.core.rule_engine import RuleEngine, Rule, Condition


class TestCondition(unittest.TestCase):
    """Tests pour la classe Condition."""
    
    def test_condition_init(self):
        """Test de l'initialisation d'une condition."""
        condition_data = {
            'type': 'cpu',
            'operator': '>',
            'value': 80,
            'params': {'core': 0},
            'not': True
        }
        
        condition = Condition(condition_data)
        
        self.assertEqual(condition.type, 'cpu')
        self.assertEqual(condition.operator, '>')
        self.assertEqual(condition.value, 80)
        self.assertEqual(condition.params, {'core': 0})
        self.assertTrue(condition.negated)
    
    def test_condition_evaluate(self):
        """Test de l'évaluation d'une condition."""
        # Condition simple
        condition = Condition({
            'type': 'cpu',
            'operator': '>',
            'value': 80
        })
        
        # Contexte où la condition est vraie
        context = {'cpu': 90}
        self.assertTrue(condition.evaluate(context))
        
        # Contexte où la condition est fausse
        context = {'cpu': 70}
        self.assertFalse(condition.evaluate(context))
        
        # Condition avec négation
        condition_not = Condition({
            'type': 'cpu',
            'operator': '>',
            'value': 80,
            'not': True
        })
        
        # La négation inverse le résultat
        self.assertFalse(condition_not.evaluate({'cpu': 90}))
        self.assertTrue(condition_not.evaluate({'cpu': 70}))
    
    def test_condition_compare_operators(self):
        """Test des différents opérateurs de comparaison."""
        context = {'value': 50}
        
        # Égalité (==)
        self.assertTrue(Condition({'type': 'value', 'operator': '==', 'value': 50}).evaluate(context))
        self.assertFalse(Condition({'type': 'value', 'operator': '==', 'value': 51}).evaluate(context))
        
        # Différence (!=)
        self.assertTrue(Condition({'type': 'value', 'operator': '!=', 'value': 51}).evaluate(context))
        self.assertFalse(Condition({'type': 'value', 'operator': '!=', 'value': 50}).evaluate(context))
        
        # Supérieur (>)
        self.assertTrue(Condition({'type': 'value', 'operator': '>', 'value': 49}).evaluate(context))
        self.assertFalse(Condition({'type': 'value', 'operator': '>', 'value': 50}).evaluate(context))
        
        # Inférieur (<)
        self.assertTrue(Condition({'type': 'value', 'operator': '<', 'value': 51}).evaluate(context))
        self.assertFalse(Condition({'type': 'value', 'operator': '<', 'value': 50}).evaluate(context))
        
        # Supérieur ou égal (>=)
        self.assertTrue(Condition({'type': 'value', 'operator': '>=', 'value': 50}).evaluate(context))
        self.assertFalse(Condition({'type': 'value', 'operator': '>=', 'value': 51}).evaluate(context))
        
        # Inférieur ou égal (<=)
        self.assertTrue(Condition({'type': 'value', 'operator': '<=', 'value': 50}).evaluate(context))
        self.assertFalse(Condition({'type': 'value', 'operator': '<=', 'value': 49}).evaluate(context))
        
        # Contient (contains)
        self.assertTrue(Condition({'type': 'text', 'operator': 'contains', 'value': 'world'}).evaluate({'text': 'hello world'}))
        self.assertFalse(Condition({'type': 'text', 'operator': 'contains', 'value': 'universe'}).evaluate({'text': 'hello world'}))
        
        # Expression régulière (regex)
        self.assertTrue(Condition({'type': 'text', 'operator': 'regex', 'value': r'^hello'}).evaluate({'text': 'hello world'}))
        self.assertFalse(Condition({'type': 'text', 'operator': 'regex', 'value': r'^world'}).evaluate({'text': 'hello world'}))


class TestRule(unittest.TestCase):
    """Tests pour la classe Rule."""
    
    def test_rule_init(self):
        """Test de l'initialisation d'une règle."""
        rule_data = {
            'name': 'Test Rule',
            'description': 'A test rule',
            'enabled': True,
            'priority': 8,
            'conditions': [
                {'type': 'cpu', 'operator': '>', 'value': 80}
            ],
            'condition_logic': 'all',
            'actions': [
                {'type': 'notify', 'params': {'message': 'CPU high'}}
            ],
            'triggers': [
                {'type': 'time', 'interval': '10s'}
            ]
        }
        
        rule = Rule(rule_data, 'rule1')
        
        self.assertEqual(rule.id, 'rule1')
        self.assertEqual(rule.name, 'Test Rule')
        self.assertEqual(rule.description, 'A test rule')
        self.assertTrue(rule.enabled)
        self.assertEqual(rule.priority, 8)
        self.assertEqual(len(rule.conditions), 1)
        self.assertEqual(rule.condition_logic, 'all')
        self.assertEqual(rule.actions, [{'type': 'notify', 'params': {'message': 'CPU high'}}])
        self.assertEqual(rule.triggers, [{'type': 'time', 'interval': '10s'}])
    
    def test_rule_evaluate_all_logic(self):
        """Test de l'évaluation d'une règle avec logique 'all'."""
        rule = Rule({
            'name': 'All Test',
            'conditions': [
                {'type': 'cpu', 'operator': '>', 'value': 80},
                {'type': 'memory', 'operator': '>', 'value': 70}
            ],
            'condition_logic': 'all'
        }, 'rule_all')
        
        # Les deux conditions sont vraies
        context = {'cpu': 90, 'memory': 80}
        self.assertTrue(rule.evaluate(context))
        
        # Une condition est fausse
        context = {'cpu': 90, 'memory': 60}
        self.assertFalse(rule.evaluate(context))
        
        # Les deux conditions sont fausses
        context = {'cpu': 70, 'memory': 60}
        self.assertFalse(rule.evaluate(context))
    
    def test_rule_evaluate_any_logic(self):
        """Test de l'évaluation d'une règle avec logique 'any'."""
        rule = Rule({
            'name': 'Any Test',
            'conditions': [
                {'type': 'cpu', 'operator': '>', 'value': 80},
                {'type': 'memory', 'operator': '>', 'value': 70}
            ],
            'condition_logic': 'any'
        }, 'rule_any')
        
        # Les deux conditions sont vraies
        context = {'cpu': 90, 'memory': 80}
        self.assertTrue(rule.evaluate(context))
        
        # Une condition est vraie
        context = {'cpu': 90, 'memory': 60}
        self.assertTrue(rule.evaluate(context))
        
        # Les deux conditions sont fausses
        context = {'cpu': 70, 'memory': 60}
        self.assertFalse(rule.evaluate(context))
    
    def test_rule_evaluate_disabled(self):
        """Test d'une règle désactivée."""
        rule = Rule({
            'name': 'Disabled Test',
            'enabled': False,
            'conditions': [
                {'type': 'cpu', 'operator': '>', 'value': 80}
            ]
        }, 'rule_disabled')
        
        # Même si la condition est vraie, la règle ne s'applique pas car désactivée
        context = {'cpu': 90}
        self.assertFalse(rule.evaluate(context))
    
    def test_rule_without_conditions(self):
        """Test d'une règle sans conditions."""
        rule = Rule({
            'name': 'No Conditions',
            'enabled': True
        }, 'rule_no_cond')
        
        # Une règle sans conditions s'applique toujours si activée
        self.assertTrue(rule.evaluate({}))


class TestRuleEngine(unittest.TestCase):
    """Tests pour la classe RuleEngine."""
    
    def setUp(self):
        """Configuration avant chaque test."""
        self.engine = RuleEngine()
        self.action_executor = MagicMock()
        self.engine.set_action_executor(self.action_executor)
    
    def test_load_rules_from_yaml(self):
        """Test du chargement des règles depuis un YAML."""
        yaml_content = """
        rules:
          rule1:
            name: Rule 1
            enabled: true
            priority: 5
            conditions:
              - type: cpu
                operator: ">"
                value: 80
            actions:
              - type: notify
                params:
                  message: CPU alert
        """
        
        self.engine.load_rules_from_yaml(yaml_content)
        
        self.assertEqual(len(self.engine.rules), 1)
        self.assertIn('rule1', self.engine.rules)
        self.assertEqual(self.engine.rules['rule1'].name, 'Rule 1')
    
    def test_context_providers(self):
        """Test des fournisseurs de contexte."""
        cpu_provider = lambda: 90
        memory_provider = lambda: 70
        
        self.engine.register_context_provider('cpu', cpu_provider)
        self.engine.register_context_provider('memory', memory_provider)
        
        context = self.engine.get_current_context()
        
        self.assertEqual(context['cpu'], 90)
        self.assertEqual(context['memory'], 70)
    
    def test_evaluate_all_rules(self):
        """Test de l'évaluation de toutes les règles."""
        # Créer deux règles
        rule1_data = {
            'name': 'Rule 1',
            'enabled': True,
            'priority': 5,
            'conditions': [
                {'type': 'cpu', 'operator': '>', 'value': 80}
            ]
        }
        
        rule2_data = {
            'name': 'Rule 2',
            'enabled': True,
            'priority': 8,
            'conditions': [
                {'type': 'memory', 'operator': '>', 'value': 80}
            ]
        }
        
        self.engine.rules = {
            'rule1': Rule(rule1_data, 'rule1'),
            'rule2': Rule(rule2_data, 'rule2')
        }
        
        # Configurer le contexte où seule la première règle correspond
        self.engine.get_current_context = MagicMock(return_value={
            'cpu': 90,  # > 80 => rule1 = True
            'memory': 70  # < 80 => rule2 = False
        })
        
        matched_rules = self.engine.evaluate_all_rules()
        
        self.assertEqual(len(matched_rules), 1)
        self.assertEqual(matched_rules[0].id, 'rule1')
    
    def test_execute_matched_rules(self):
        """Test de l'exécution des règles correspondantes."""
        # Créer une règle avec des actions
        rule1_data = {
            'name': 'Rule 1',
            'enabled': True,
            'actions': [
                {'type': 'notify', 'params': {'message': 'Test'}},
                {'type': 'wait', 'params': {'seconds': 1}}
            ]
        }
        
        self.engine.rules = {
            'rule1': Rule(rule1_data, 'rule1')
        }
        
        # Simuler une évaluation qui retourne cette règle
        self.engine.evaluate_all_rules = MagicMock(return_value=[self.engine.rules['rule1']])
        
        # Exécuter les règles correspondantes
        executed_count = self.engine.execute_matched_rules()
        
        self.assertEqual(executed_count, 1)
        # Vérifier que l'exécuteur d'actions a été appelé pour chaque action
        self.assertEqual(self.action_executor.execute.call_count, 2)
    
    def test_rule_enable_disable(self):
        """Test de l'activation/désactivation d'une règle."""
        rule_data = {
            'name': 'Test Rule',
            'enabled': True
        }
        
        self.engine.rules = {
            'rule1': Rule(rule_data, 'rule1')
        }
        
        # Désactiver la règle
        self.assertTrue(self.engine.disable_rule('rule1'))
        self.assertFalse(self.engine.rules['rule1'].enabled)
        
        # Réactiver la règle
        self.assertTrue(self.engine.enable_rule('rule1'))
        self.assertTrue(self.engine.rules['rule1'].enabled)
        
        # Tester avec un ID inexistant
        self.assertFalse(self.engine.enable_rule('nonexistent'))
        self.assertFalse(self.engine.disable_rule('nonexistent'))


if __name__ == '__main__':
    unittest.main()
