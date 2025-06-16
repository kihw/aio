from __future__ import annotations

import argparse
import os
from pathlib import Path
import yaml

from core.rule_engine import RuleEngine


DEFAULT_RULES_DIR = Path(__file__).resolve().parent.parent / "rules"


def load_rules(profile: str | None = None, rules_dir: Path | None = None) -> list[dict]:
    """Load YAML rule files from *rules_dir*.

    Always load ``default.yaml`` if present. When ``profile`` is specified,
    additional files from ``<rules_dir>/<profile>.yaml`` and ``<rules_dir>/<profile>/``
    are loaded if they exist.
    """

    if rules_dir is None:
        env_dir = os.getenv("APPFLOW_RULES_DIR")
        rules_dir = Path(env_dir) if env_dir else DEFAULT_RULES_DIR

    files: list[Path] = []

    default_file = rules_dir / "default.yaml"
    if default_file.exists():
        files.append(default_file)

    if profile:
        profile_file = rules_dir / f"{profile}.yaml"
        if profile_file.exists():
            files.append(profile_file)
        profile_dir = rules_dir / profile
        if profile_dir.is_dir():
            files.extend(sorted(profile_dir.glob("*.yaml")))

    if not files:
        return []

    rules: list[dict] = []

    for rule_file in files:
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
    parser.add_argument(
        "--profile",
        "-p",
        metavar="NAME",
        help="Also load default.yaml then rules for profile NAME",
    )
    parser.add_argument(
        "--rules-dir",
        "-d",
        metavar="DIR",
        help="Load rules from DIR instead of the default rules directory",
        type=Path,
    )
    parser.add_argument(
        "--interval",
        "-i",
        metavar="SEC",
        type=float,
        default=2.0,
        help="Polling interval in seconds",
    )
    parser.add_argument(
        "--once",
        "-1",
        action="store_true",
        help="Check rules once and exit",
    )
    args = parser.parse_args(argv)

    rules = load_rules(profile=args.profile, rules_dir=args.rules_dir)

    if args.list:
        for r in rules:
            print(r.get("name", "Unnamed"))
        return

    if args.run:
        rules = [r for r in rules if r.get("name") == args.run]

    engine = RuleEngine(
        rules,
        poll_interval=args.interval,
        log_path=args.log,
        run_once=args.once,
    )
    engine.run()


if __name__ == "__main__":
    main()

