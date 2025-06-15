import subprocess
import time
import psutil

from utils.system import is_process_running


class RuleEngine:
    """Simple engine that evaluates rules and executes matching actions."""

    def __init__(self, rules, poll_interval: float = 2.0):
        self.rules = [Rule(r) for r in rules]
        self.poll_interval = poll_interval

    def run(self):
        """Continuously check rules and execute them when triggers match."""
        try:
            while True:
                for rule in self.rules:
                    if rule.check_triggers():
                        rule.execute()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("Rule engine stopped")


class Rule:
    def __init__(self, data):
        self.name = data.get('name', 'Unnamed')
        self.triggers = data.get('triggers', [])
        self.actions = data.get('actions', [])
        self.has_run = False

    def check_triggers(self) -> bool:
        """Return True if rule triggers are satisfied."""
        if not self.triggers:
            return not self.has_run

        for trig in self.triggers:
            if 'app_start' in trig:
                if is_process_running(trig['app_start']):
                    return True
            if 'app_exit' in trig:
                if not is_process_running(trig['app_exit']):
                    return True

        return False

    def execute(self):
        """Execute rule actions sequentially."""
        if self.has_run:
            return
        for action in self.actions:
            if 'launch' in action:
                subprocess.Popen(action['launch'], shell=True)
            elif 'kill' in action:
                for p in psutil.process_iter(['name']):
                    if p.info['name'] == action['kill']:
                        p.terminate()
            elif 'wait' in action:
                time.sleep(action['wait'])
        self.has_run = True
