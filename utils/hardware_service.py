# utils/hardware_service.py
"""
Hardware monitoring service for Ticky:
- CPU load (overall and per-core), frequency, cores count.
- RAM usage (percentage, used / total GB).
- Network download and upload speed delta.
- Battery status (charging, remaining time, percentage).
- GPU model detection and safe 3D engine utilization sampling.
- Top consuming processes list (when enabled in settings).
- Runs on a dedicated background thread with zero UI lag,
  paused when notch is closed (0% background CPU impact).
"""

import os
import sys
import time
import threading
from PySide6.QtCore import QObject, Signal, QThread

try:
    import psutil
except ImportError:
    psutil = None


def format_speed(bytes_per_sec: float) -> str:
    """Format bytes/sec into a clean readable string (e.g. 3.2 MB/s, 450 KB/s)."""
    if bytes_per_sec < 1024:
        return f"{int(bytes_per_sec)} B/s"
    elif bytes_per_sec < 1024 * 1024:
        return f"{bytes_per_sec / 1024:.1f} KB/s"
    elif bytes_per_sec < 1024 * 1024 * 1024:
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
    else:
        return f"{bytes_per_sec / (1024 * 1024 * 1024):.2f} GB/s"


def get_gpu_model_cached():
    """Attempt fast zero-overhead GPU model detection on Windows."""
    if sys.platform != "win32":
        return "Standard Graphics"
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000"
        )
        desc, _ = winreg.QueryValueEx(key, "DriverDesc")
        winreg.CloseKey(key)
        return str(desc).strip()
    except Exception:
        pass
    return "Integrated / Discrete GPU"


class HardwareWorker(QThread):
    """Background worker that continuously samples system metrics and emits updates."""
    stats_updated = Signal(dict)

    def __init__(self, poll_interval_ms: int = 1000, parent=None):
        super().__init__(parent)
        self.poll_interval = max(0.5, poll_interval_ms / 1000.0)
        self._running = True
        self._active_event = threading.Event()
        self._gpu_model = get_gpu_model_cached()
        self._gpu_query = None
        self._gpu_counter = None
        self._gpu_disabled = False
        self._gpu_error_count = 0

    def pause(self):
        """Pause polling to burn 0% CPU in background."""
        self._active_event.clear()

    def resume(self):
        """Resume polling immediately."""
        self._active_event.set()

    def stop(self):
        """Signal thread to exit cleanly."""
        self._running = False
        self._active_event.set()

    def _init_gpu(self):
        if sys.platform != "win32" or self._gpu_disabled:
            return
        try:
            import win32pdh
            self._gpu_query = win32pdh.OpenQuery()
            self._gpu_counter = win32pdh.AddCounter(
                self._gpu_query, r'\GPU Engine(*engtype_3D)\Utilization Percentage'
            )
            win32pdh.CollectQueryData(self._gpu_query)
        except Exception:
            self._gpu_query = None
            self._gpu_counter = None

    def _close_gpu(self):
        if self._gpu_query:
            try:
                import win32pdh
                win32pdh.CloseQuery(self._gpu_query)
            except Exception:
                pass
            self._gpu_query = None
            self._gpu_counter = None

    def _sample_gpu(self) -> float:
        if self._gpu_disabled:
            return 0.0
        if not self._gpu_query or not self._gpu_counter:
            self._init_gpu()
            if not self._gpu_query or not self._gpu_counter:
                return 0.0

        try:
            import win32pdh
            win32pdh.CollectQueryData(self._gpu_query)
            res = win32pdh.GetFormattedCounterArray(self._gpu_counter, win32pdh.PDH_FMT_DOUBLE)
            if isinstance(res, dict):
                return min(100.0, max(0.0, sum(v for v in res.values() if v > 0)))
        except Exception:
            self._gpu_error_count += 1
            if self._gpu_error_count >= 3:
                self._gpu_disabled = True
            self._close_gpu()
        return 0.0

    def run(self):
        if not psutil:
            self.stats_updated.emit({"error": "psutil not installed"})
            return

        last_net = psutil.net_io_counters()
        last_time = time.time()
        psutil.cpu_percent(interval=None)

        while self._running:
            # Wait while paused without consuming CPU
            if not self._active_event.is_set():
                self._close_gpu()
                while self._running and not self._active_event.is_set():
                    self._active_event.wait(timeout=0.2)
                if not self._running:
                    break
                # Reset counters on wake so network deltas and CPU percentages start clean
                last_net = psutil.net_io_counters()
                last_time = time.time()
                psutil.cpu_percent(interval=None)

            try:
                # 1. CPU metrics
                cpu_total = psutil.cpu_percent(interval=None)
                per_cpu = psutil.cpu_percent(interval=None, percpu=True)
                freq = psutil.cpu_freq()
                freq_ghz = (freq.current / 1000.0) if freq and freq.current else None
                cores_phys = psutil.cpu_count(logical=False) or 1
                cores_log = psutil.cpu_count(logical=True) or 1

                # 2. RAM metrics
                mem = psutil.virtual_memory()
                mem_percent = mem.percent
                mem_used_gb = mem.used / (1024 ** 3)
                mem_total_gb = mem.total / (1024 ** 3)
                mem_free_gb = mem.available / (1024 ** 3)

                # 3. Network speed delta
                curr_net = psutil.net_io_counters()
                curr_time = time.time()
                dt = max(0.1, curr_time - last_time)

                bytes_recv_rate = max(0.0, (curr_net.bytes_recv - last_net.bytes_recv) / dt)
                bytes_sent_rate = max(0.0, (curr_net.bytes_sent - last_net.bytes_sent) / dt)
                total_speed_rate = bytes_recv_rate + bytes_sent_rate

                last_net = curr_net
                last_time = curr_time

                # 4. GPU %
                gpu_percent = self._sample_gpu()

                # 5. Battery metrics
                battery = psutil.sensors_battery()
                has_battery = battery is not None
                bat_percent = battery.percent if has_battery else None
                bat_plugged = battery.power_plugged if has_battery else False
                bat_status_str = ""
                if has_battery:
                    if bat_plugged:
                        bat_status_str = f"{bat_percent}% Charging" if bat_percent < 100 else "100% Fully Charged"
                    else:
                        bat_status_str = f"{bat_percent}% on Battery"

                # 6. Uptime
                boot_time = psutil.boot_time()
                uptime_sec = max(0, int(time.time() - boot_time))
                hours, rem = divmod(uptime_sec, 3600)
                minutes, _ = divmod(rem, 60)
                uptime_str = f"{hours}h {minutes}m"

                # 7. Top active processes (only query when enabled in settings)
                top_procs = []
                try:
                    from utils import config
                    if config.load_hardware_show_top_consumers(False):
                        for p in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
                            try:
                                info = p.info
                                name = info.get('name') or "Process"
                                if "idle" in name.lower():
                                    continue
                                cpu_p = info.get('cpu_percent') or 0.0
                                mem_p = info.get('memory_percent') or 0.0
                                top_procs.append({
                                    'name': name.replace('.exe', ''),
                                    'cpu_percent': round(cpu_p, 1),
                                    'memory_percent': round(mem_p, 1),
                                })
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue
                        top_procs.sort(key=lambda x: (x['cpu_percent'], x['memory_percent']), reverse=True)
                        top_procs = top_procs[:3]
                except Exception:
                    top_procs = []

                data = {
                    "cpu": {
                        "percent": round(cpu_total, 1),
                        "per_cpu": per_cpu,
                        "freq_ghz": round(freq_ghz, 2) if freq_ghz else None,
                        "cores_phys": cores_phys,
                        "cores_log": cores_log,
                    },
                    "memory": {
                        "percent": round(mem_percent, 1),
                        "used_gb": round(mem_used_gb, 1),
                        "total_gb": round(mem_total_gb, 1),
                        "free_gb": round(mem_free_gb, 1),
                    },
                    "network": {
                        "speed_str": format_speed(total_speed_rate),
                        "download_str": format_speed(bytes_recv_rate),
                        "upload_str": format_speed(bytes_sent_rate),
                        "bytes_recv_rate": bytes_recv_rate,
                        "bytes_sent_rate": bytes_sent_rate,
                        "total_speed_rate": total_speed_rate,
                    },
                    "battery": {
                        "has_battery": has_battery,
                        "percent": bat_percent,
                        "plugged": bat_plugged,
                        "status_str": bat_status_str,
                    },
                    "gpu": {
                        "percent": round(gpu_percent, 1),
                        "model": self._gpu_model,
                    },
                    "system": {
                        "uptime_str": uptime_str,
                    },
                    "top_processes": top_procs,
                    "timestamp": curr_time,
                }

                if self._running and self._active_event.is_set():
                    self.stats_updated.emit(data)

            except Exception:
                pass

            # Responsive sleep in small steps so pause() responds instantly
            elapsed = 0.0
            step = 0.05
            while self._running and self._active_event.is_set() and elapsed < self.poll_interval:
                time.sleep(step)
                elapsed += step

        self._close_gpu()


class HardwareService(QObject):
    """Manages system hardware monitoring lifecycle."""
    updated = Signal(dict)

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = HardwareService()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = HardwareWorker(poll_interval_ms=1000)
        self._worker.stats_updated.connect(self._on_stats_updated)
        self._worker.start()
        self.cached_stats = None

    def start_monitoring(self):
        """Resume background polling thread with zero UI freeze."""
        if self.cached_stats:
            self.updated.emit(self.cached_stats)
        if self._worker is not None:
            if not self._worker.isRunning():
                self._worker.start()
            self._worker.resume()

    def stop_monitoring(self):
        """Pause polling to preserve 0% background CPU usage."""
        if self._worker is not None:
            self._worker.pause()

    def shutdown(self):
        """Clean shutdown of background thread when app exits."""
        if self._worker is not None:
            self._worker.stop()
            self._worker.wait(1500)
            self._worker = None

    def _on_stats_updated(self, data: dict):
        self.cached_stats = data
        self.updated.emit(data)
