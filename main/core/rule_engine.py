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
from utils.logger import log_event



class RuleEngine:
    """Simple engine that evaluates rules and executes matching actions."""

    def __init__(self, rules, poll_interval: float = 2.0, log_path=None, run_once: bool = False):
        self.rules = [Rule(r) for r in rules]
        self.poll_interval = poll_interval
        self.log_path = log_path
        self.run_once = run_once

    def run(self):
        """Continuously check rules and execute them when triggers match."""
        log_event("Rule engine started", self.log_path)
        try:
            while True:
                for rule in self.rules:
                    if rule.check_triggers():
                        rule.execute(log_path=self.log_path)
                if self.run_once:
                    break
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("Rule engine stopped")
        finally:
            log_event("Rule engine stopped", self.log_path)


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

    def execute(self, log_path=None):
        """Execute rule actions sequentially."""
        if self.has_run:
            return
        log_event(f"Executing rule: {self.name}", log_path)
        for action in self.actions:
            if 'launch' in action:
                subprocess.Popen(action['launch'], shell=True)
                log_event(f"launch -> {action['launch']}", log_path)
            elif 'kill' in action:
                for p in psutil.process_iter(['name']):
                    if p.info['name'] == action['kill']:
                        p.terminate()
                log_event(f"kill -> {action['kill']}", log_path)
            elif 'wait' in action:
                time.sleep(action['wait'])
                log_event(f"wait -> {action['wait']}", log_path)

            elif 'notify' in action:
                send_notification(action['notify'])
                log_event(f"notify -> {action['notify']}", log_path)

        log_event(f"Finished rule: {self.name}", log_path)
        self.has_run = True
