"""CSV 数据记录模块"""

import csv
import time
import threading
import os
from typing import Optional

from plc_monitor import PlcMonitor


class DataLogger:
    def __init__(self, filepath: str = ""):
        self._filepath = filepath or self._default_path()
        self._running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._interval = 1.0  # 记录间隔（秒）

    @staticmethod
    def _default_path() -> str:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            f"plc_data_{time.strftime('%Y%m%d_%H%M%S')}.csv")

    @property
    def filepath(self) -> str:
        return self._filepath

    @property
    def interval(self) -> float:
        return self._interval

    @interval.setter
    def interval(self, value: float):
        self._interval = max(0.1, min(value, 3600.0))

    def _run_loop(self, monitor: PlcMonitor):
        with open(self._filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["时间戳", "监控点名称", "地址", "值"])

            while not self._stop_event.is_set():
                points = monitor.get_points()
                now = time.strftime("%Y-%m-%d %H:%M:%S")
                for p in points:
                    if p.current_value is not None:
                        writer.writerow([now, p.name, p.address, p.current_value])
                f.flush()
                self._stop_event.wait(self._interval)

    def start(self, monitor: PlcMonitor):
        if self._running:
            return
        self._filepath = self._default_path()
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, args=(monitor,), daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
