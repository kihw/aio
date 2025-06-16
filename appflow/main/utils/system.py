import subprocess
import psutil
import sys

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


def get_battery_percent() -> float | None:
    """Return the current battery percentage or None if unavailable."""
    batt = psutil.sensors_battery()
    if batt is not None:
        return batt.percent
    return None


def send_notification(message: str) -> None:
    """Display a simple notification to the user (fallback to stdout)."""
    try:
        if sys.platform.startswith("linux"):
            subprocess.run(["notify-send", message], check=False)
        elif sys.platform == "darwin":
            subprocess.run(["osascript", "-e", f'display notification "{message}"'], check=False)
        elif sys.platform == "win32":
            # Windows toast requires win10toast package; fallback to console
            try:
                from win10toast import ToastNotifier
                ToastNotifier().show_toast("AppFlow", message, duration=5)
            except Exception:
                print(f"[NOTIFY] {message}")
        else:
            print(f"[NOTIFY] {message}")
    except Exception:
        print(f"[NOTIFY] {message}")
