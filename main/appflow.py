import argparse
from pathlib import Path
import yaml

from core.rule_engine import RuleEngine


RULES_DIR = Path(__file__).resolve().parent.parent / "rules"


def load_rules():
    """Load all YAML rule files from the rules directory."""
    rules = []
    for rule_file in RULES_DIR.glob("*.yaml"):
        with open(rule_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if isinstance(data, list):
                rules.extend(data)
    return rules


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run AppFlow rules")
    parser.add_argument("--list", action="store_true", help="List available rules")
    parser.add_argument("--run", metavar="RULE", help="Run a specific rule by name")
    parser.add_argument("--log", metavar="FILE", help="Write execution log to FILE")
    args = parser.parse_args(argv)

    rules = load_rules()

    if args.list:
        for r in rules:
            print(r.get("name", "Unnamed"))
        return

    if args.run:
        rules = [r for r in rules if r.get("name") == args.run]

    engine = RuleEngine(rules, log_path=args.log)
    engine.run()


if __name__ == "__main__":
    main()
