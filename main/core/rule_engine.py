import subprocess
import time

import datetime
import psutil

from utils.system import (
    is_process_running,
    get_battery_percent,
    get_cpu_percent,
    get_network_bytes_per_sec,
    send_notification,
)



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

        if self.has_run:
            return False
        if not self.triggers:
            return True


        for trig in self.triggers:
            if 'app_start' in trig:
                if is_process_running(trig['app_start']):
                    return True
            if 'app_exit' in trig:
                if not is_process_running(trig['app_exit']):
                    return True

            if 'at_time' in trig:
                target = trig['at_time']
                now = datetime.datetime.now().strftime('%H:%M')
                if now == target:
                    return True
            if 'battery_below' in trig:
                level = get_battery_percent()
                if level is not None and level < float(trig['battery_below']):
                    return True
            if 'cpu_above' in trig:
                cpu = get_cpu_percent(interval=0.1)
                if cpu > float(trig['cpu_above']):
                    return True
            if 'network_above' in trig:
                net = get_network_bytes_per_sec()
                if net > float(trig['network_above']) * 1024:
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

            elif 'notify' in action:
                send_notification(action['notify'])

        self.has_run = True
