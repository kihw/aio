import subprocess
import psutil
import sys
import time


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


def get_cpu_percent(interval: float = 0.0) -> float:
    """Return the system-wide CPU usage percentage."""
    # psutil.cpu_percent with interval=0.0 returns an instantly
    # computed value since the last call. A small interval can be
    # specified for a more accurate measurement.
    try:
        return psutil.cpu_percent(interval=interval)
    except Exception:
        return 0.0


_last_net = None
_last_net_time = None


def get_network_bytes_per_sec() -> float:
    """Return the total network throughput in bytes per second since last call."""
    global _last_net, _last_net_time
    now = time.time()
    net = psutil.net_io_counters()
    if _last_net is None:
        _last_net = net
        _last_net_time = now
        return 0.0
    elapsed = now - _last_net_time
    sent = net.bytes_sent - _last_net.bytes_sent
    recv = net.bytes_recv - _last_net.bytes_recv
    _last_net = net
    _last_net_time = now
    if elapsed <= 0:
        return 0.0
    return (sent + recv) / elapsed


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

