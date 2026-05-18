"""数据监控模块 - 管理监控点列表，后台周期性刷新"""

import time
import threading
from dataclasses import dataclass, field
from typing import Any, Optional, Callable

from plc_client import PlcClient, parse_address, AddressInfo


@dataclass
class MonitorPoint:
    address: str = ""
    name: str = ""
    data_type: str = "Bool"
    area_code: int = 0
    db_number: int = 0
    byte_offset: int = 0
    bit_offset: int = -1
    size: int = 1
    current_value: Any = None
    unit: str = ""              # 工程单位，如 °C, MPa
    scale: float = 1.0          # 比例系数
    decimal_places: int = 1     # 显示小数点位数
    history: list = field(default_factory=list)  # 用于波形显示的历史数据

    @classmethod
    def from_address(cls, address: str, name: str = "", data_type: str = "",
                     unit: str = "", scale: float = 1.0, decimal_places: int = 1) -> Optional["MonitorPoint"]:
        info = parse_address(address)
        if info is None:
            return None
        # data_type 可由用户覆盖，否则从地址自动推断
        dt = data_type or info.data_type
        return cls(
            address=address.upper(),
            name=name or address.upper(),
            data_type=dt,
            area_code=info.area_code,
            db_number=info.db_number,
            byte_offset=info.byte_offset,
            bit_offset=info.bit_offset,
            size=info.size,
            unit=unit,
            scale=scale,
            decimal_places=decimal_places,
        )


class PlcMonitor:
    def __init__(self):
        self.points: list[MonitorPoint] = []
        self._running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._interval = 0.5  # 刷新间隔（秒）
        self._last_refresh_time = ""
        self._on_data_changed: Optional[Callable] = None  # 数据变更回调
        self._history_len = 120  # 波形历史数据点数（60秒/0.5秒间隔）

    @property
    def interval(self) -> float:
        return self._interval

    @interval.setter
    def interval(self, value: float):
        self._interval = max(0.1, min(value, 60.0))

    @property
    def last_refresh_time(self) -> str:
        return self._last_refresh_time

    def set_on_data_changed(self, callback: Callable):
        self._on_data_changed = callback

    def add_point(self, address: str, name: str = "", data_type: str = "",
                  unit: str = "", scale: float = 1.0, decimal_places: int = 1) -> Optional[MonitorPoint]:
        point = MonitorPoint.from_address(address, name, data_type=data_type,
                                           unit=unit, scale=scale, decimal_places=decimal_places)
        if point is None:
            return None
        with self._lock:
            self.points.append(point)
        return point

    def remove_point(self, index: int) -> bool:
        with self._lock:
            if 0 <= index < len(self.points):
                self.points.pop(index)
                return True
        return False

    def clear_points(self):
        with self._lock:
            self.points.clear()

    def get_points(self) -> list[MonitorPoint]:
        with self._lock:
            return list(self.points)

    def refresh(self, client: PlcClient):
        if not client.is_connected():
            return

        with self._lock:
            points_snapshot = list(self.points)

        changed = False
        for point in points_snapshot:
            try:
                if point.data_type == "Bool":
                    val = client.read_bool(point.area_code, point.db_number, point.byte_offset, point.bit_offset)
                elif point.data_type == "Byte":
                    data = client.read_bytes(point.area_code, point.db_number, point.byte_offset, 1)
                    val = data[0] if data else None
                elif point.data_type == "Word":
                    val = client.read_word(point.area_code, point.db_number, point.byte_offset)
                elif point.data_type == "DWord":
                    val = client.read_dword(point.area_code, point.db_number, point.byte_offset)
                elif point.data_type == "Real":
                    val = client.read_real(point.area_code, point.db_number, point.byte_offset)
                else:
                    val = None
            except Exception:
                val = None

            if val is not None:
                point.current_value = val
                # 维护历史数据缓冲
                point.history.append((time.time(), val))
                if len(point.history) > self._history_len:
                    point.history = point.history[-self._history_len:]
                changed = True

        self._last_refresh_time = time.strftime("%H:%M:%S")

        if changed and self._on_data_changed:
            self._on_data_changed()

    def _run_loop(self, client: PlcClient):
        while not self._stop_event.is_set():
            self.refresh(client)
            self._stop_event.wait(self._interval)

    def start(self, client: PlcClient):
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, args=(client,), daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
