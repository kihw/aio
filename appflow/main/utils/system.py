import subprocess
import psutil

def launch_process(cmd):
    return subprocess.Popen(cmd, shell=True)

def kill_process(name):
    for p in psutil.process_iter(['name']):
        if p.info['name'] == name:
            p.terminate()
            return True
    return False


def is_process_running(name: str) -> bool:
    """Check if a process with the given name is currently running."""
    for p in psutil.process_iter(['name']):
        if p.info['name'] == name:
            return True
    return False
