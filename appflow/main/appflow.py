import yaml
import psutil
import subprocess
import time
from pathlib import Path

from core.rule_engine import RuleEngine


RULES_DIR = Path(__file__).resolve().parent.parent / "rules"


def load_rules():
    rules = []
    for rule_file in RULES_DIR.glob("*.yaml"):
        with open(rule_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            rules.extend(data)
    return rules


def main():
    rules = load_rules()
    engine = RuleEngine(rules)
    engine.run()


if __name__ == "__main__":
    main()
