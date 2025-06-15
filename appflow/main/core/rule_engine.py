import subprocess
import time
import psutil


class RuleEngine:
    def __init__(self, rules):
        self.rules = [Rule(r) for r in rules]

    def run(self):
        for rule in self.rules:
            rule.execute()


class Rule:
    def __init__(self, data):
        self.name = data.get('name', 'Unnamed')
        self.triggers = data.get('triggers', [])
        self.actions = data.get('actions', [])

    def execute(self):
        # For simplicity, execute all actions sequentially without triggers
        for action in self.actions:
            if 'launch' in action:
                subprocess.Popen(action['launch'], shell=True)
            elif 'kill' in action:
                for p in psutil.process_iter(['name']):
                    if p.info['name'] == action['kill']:
                        p.terminate()
            elif 'wait' in action:
                time.sleep(action['wait'])
