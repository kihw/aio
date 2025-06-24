"""
Rule Engine - Moteur de règles
------------------------------
Ce module est responsable du parsing et de l'évaluation des règles définies au format YAML.
Il permet de déterminer quand et comment les actions doivent être exécutées.
"""

import yaml
import re
import logging
from typing import Dict, List, Any, Union, Optional, Callable

logger = logging.getLogger(__name__)

class Condition:
    """
    Représente une condition à évaluer dans le contexte du système.
    """
    
    def __init__(self, condition_data: Dict[str, Any]):
        """
        Initialise une condition depuis les données YAML.
        
        Args:
            condition_data: Dictionnaire contenant les paramètres de la condition
        """
        self.type = condition_data.get('type')
        self.params = condition_data.get('params', {})
        self.operator = condition_data.get('operator', '==')
        self.value = condition_data.get('value')
        self.negated = condition_data.get('not', False)
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Évalue la condition dans le contexte actuel du système.
        
        Args:
            context: Dictionnaire contenant les données du système actuel
            
        Returns:
            bool: Résultat de l'évaluation de la condition
        """
        # Récupérer la valeur actuelle depuis le contexte
        if self.type not in context:
            logger.warning(f"Type de condition {self.type} non présent dans le contexte")
            return False
        
        current_value = context[self.type]
        
        # Pour les conditions nécessitant des paramètres supplémentaires
        if isinstance(current_value, dict) and self.params:
            for key, value in self.params.items():
                if key in current_value:
                    current_value = current_value[key]
                else:
                    logger.warning(f"Paramètre {key} non trouvé dans le contexte {self.type}")
                    return False
        
        # Comparaison selon l'opérateur
        result = self._compare(current_value, self.value, self.operator)
        
        # Appliquer la négation si demandée
        return not result if self.negated else result
    
    def _compare(self, current: Any, target: Any, operator: str) -> bool:
        """
        Compare deux valeurs selon l'opérateur spécifié.
        
        Args:
            current: Valeur actuelle
            target: Valeur cible
            operator: Opérateur de comparaison ('==', '!=', '>', '<', '>=', '<=', 'contains', 'regex')
            
        Returns:
            bool: Résultat de la comparaison
        """
        if operator == '==':
            return current == target
        elif operator == '!=':
            return current != target
        elif operator == '>':
            return current > target
        elif operator == '<':
            return current < target
        elif operator == '>=':
            return current >= target
        elif operator == '<=':
            return current <= target
        elif operator == 'contains':
            return target in current
        elif operator == 'regex':
            return bool(re.search(target, str(current)))
        else:
            logger.error(f"Opérateur {operator} non supporté")
            return False
    
    def __str__(self) -> str:
        not_str = "NOT " if self.negated else ""
        params_str = f" with params {self.params}" if self.params else ""
        return f"{not_str}{self.type}{params_str} {self.operator} {self.value}"


class Rule:
    """
    Représente une règle complète avec conditions et actions à exécuter.
    """
    
    def __init__(self, rule_data: Dict[str, Any], rule_id: str):
        """
        Initialise une règle depuis les données YAML.
        
        Args:
            rule_data: Dictionnaire contenant la définition de la règle
            rule_id: Identifiant unique de la règle
        """
        self.id = rule_id
        self.name = rule_data.get('name', f'Rule {rule_id}')
        self.description = rule_data.get('description', '')
        self.enabled = rule_data.get('enabled', True)
        self.priority = rule_data.get('priority', 5)  # 1-10, 10 étant le plus prioritaire
        
        # Conditions
        conditions_data = rule_data.get('conditions', [])
        self.conditions = [Condition(cond) for cond in conditions_data]
        self.condition_logic = rule_data.get('condition_logic', 'all')  # 'all' ou 'any'
        
        # Actions
        self.actions = rule_data.get('actions', [])
        
        # Triggers
        self.triggers = rule_data.get('triggers', [])
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Évalue si la règle doit être exécutée selon le contexte actuel.
        
        Args:
            context: Dictionnaire contenant les données du système actuel
            
        Returns:
            bool: True si la règle doit être exécutée, False sinon
        """
        if not self.enabled:
            return False
        
        if not self.conditions:
            return True  # Une règle sans conditions s'applique toujours
        
        if self.condition_logic == 'all':
            return all(condition.evaluate(context) for condition in self.conditions)
        elif self.condition_logic == 'any':
            return any(condition.evaluate(context) for condition in self.conditions)
        else:
            logger.error(f"Logique de condition '{self.condition_logic}' non supportée")
            return False
    
    def __str__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"Rule '{self.name}' ({self.id}) - {status}, priority {self.priority}"


class RuleEngine:
    """
    Moteur principal pour le chargement, l'évaluation et l'exécution des règles.
    """
    
    def __init__(self):
        self.rules: Dict[str, Rule] = {}
        self.action_executor = None  # Sera défini lors de l'intégration
        self.context_providers: Dict[str, Callable] = {}
    
    def set_action_executor(self, executor) -> None:
        """
        Associe un exécuteur d'actions au moteur de règles.
        
        Args:
            executor: Instance de ActionExecutor
        """
        self.action_executor = executor
    
    def register_context_provider(self, key: str, provider_function: Callable) -> None:
        """
        Enregistre une fonction qui fournit des données contextuelles pour l'évaluation des règles.
        
        Args:
            key: Clé pour accéder aux données dans le contexte
            provider_function: Fonction retournant les données du contexte
        """
        self.context_providers[key] = provider_function
    
    def load_rules_from_yaml(self, yaml_content: str) -> None:
        """
        Charge les règles depuis une chaîne YAML.
        
        Args:
            yaml_content: Contenu YAML à analyser
        """
        try:
            data = yaml.safe_load(yaml_content)
            if not data or not isinstance(data, dict) or 'rules' not in data:
                logger.error("Format YAML invalide - section 'rules' manquante")
                return
            
            rules_data = data['rules']
            if not isinstance(rules_data, dict):
                logger.error("La section 'rules' doit être un dictionnaire")
                return
            
            # Réinitialiser les règles actuelles
            self.rules.clear()
            
            # Charger chaque règle
            for rule_id, rule_data in rules_data.items():
                self.rules[rule_id] = Rule(rule_data, rule_id)
                logger.info(f"Règle chargée: {self.rules[rule_id]}")
                
            logger.info(f"Chargement de {len(self.rules)} règles terminé")
            
        except yaml.YAMLError as e:
            logger.error(f"Erreur lors de l'analyse du YAML: {e}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement des règles: {e}")
    
    def load_rules_from_file(self, file_path: str) -> None:
        """
        Charge les règles depuis un fichier YAML.
        
        Args:
            file_path: Chemin vers le fichier YAML
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                self.load_rules_from_yaml(file.read())
        except FileNotFoundError:
            logger.error(f"Fichier de règles non trouvé: {file_path}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du fichier de règles: {e}")
    
    def get_current_context(self) -> Dict[str, Any]:
        """
        Construit le contexte actuel en appelant toutes les fonctions de contexte enregistrées.
        
        Returns:
            Dict: Le contexte actuel du système
        """
        context = {}
        for key, provider in self.context_providers.items():
            try:
                context[key] = provider()
            except Exception as e:
                logger.error(f"Erreur lors de la récupération du contexte '{key}': {e}")
                context[key] = None
        return context
    
    def evaluate_all_rules(self) -> List[Rule]:
        """
        Évalue toutes les règles avec le contexte actuel et retourne celles qui correspondent.
        
        Returns:
            List[Rule]: Liste des règles qui doivent être exécutées
        """
        if not self.rules:
            logger.warning("Aucune règle à évaluer")
            return []
        
        context = self.get_current_context()
        matched_rules = []
        
        for rule in self.rules.values():
            try:
                if rule.evaluate(context):
                    matched_rules.append(rule)
                    logger.debug(f"Règle correspondante: {rule}")
            except Exception as e:
                logger.error(f"Erreur lors de l'évaluation de la règle {rule.id}: {e}")
        
        # Trier les règles par priorité (ordre décroissant)
        matched_rules.sort(key=lambda r: r.priority, reverse=True)
        return matched_rules
    
    def execute_matched_rules(self) -> int:
        """
        Exécute les actions pour toutes les règles qui correspondent au contexte actuel.
        
        Returns:
            int: Nombre de règles exécutées
        """
        if not self.action_executor:
            logger.error("Aucun exécuteur d'actions défini")
            return 0
        
        matched_rules = self.evaluate_all_rules()
        executed_count = 0
        
        for rule in matched_rules:
            try:
                for action in rule.actions:
                    self.action_executor.execute(action, rule_id=rule.id)
                executed_count += 1
                logger.info(f"Actions exécutées pour la règle: {rule}")
            except Exception as e:
                logger.error(f"Erreur lors de l'exécution des actions pour la règle {rule.id}: {e}")
        
        return executed_count
    
    def get_rule_by_id(self, rule_id: str) -> Optional[Rule]:
        """
        Récupère une règle par son identifiant.
        
        Args:
            rule_id: Identifiant de la règle
            
        Returns:
            Rule ou None: La règle correspondante ou None si non trouvée
        """
        return self.rules.get(rule_id)
    
    def enable_rule(self, rule_id: str) -> bool:
        """
        Active une règle.
        
        Args:
            rule_id: Identifiant de la règle
            
        Returns:
            bool: True si la règle a été activée, False sinon
        """
        rule = self.get_rule_by_id(rule_id)
        if rule:
            rule.enabled = True
            logger.info(f"Règle {rule_id} activée")
            return True
        logger.warning(f"Impossible d'activer la règle {rule_id} - non trouvée")
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """
        Désactive une règle.
        
        Args:
            rule_id: Identifiant de la règle
            
        Returns:
            bool: True si la règle a été désactivée, False sinon
        """
        rule = self.get_rule_by_id(rule_id)
        if rule:
            rule.enabled = False
            logger.info(f"Règle {rule_id} désactivée")
            return True
        logger.warning(f"Impossible de désactiver la règle {rule_id} - non trouvée")
        return False
