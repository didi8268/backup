"""波形输出模块 - 正弦波/方波/三角波/锯齿波生成与写入"""

import time
import math
import threading
from enum import Enum
from typing import Optional

from plc_client import PlcClient, parse_address, AddressInfo


class WaveformType(Enum):
    SINE = "正弦波"
    SQUARE = "方波"
    TRIANGLE = "三角波"
    SAWTOOTH = "锯齿波"


class WaveformOutput:
    def __init__(self):
        self.target_address = ""
        self.waveform_type = WaveformType.SINE
        self.amplitude = 100.0
        self.offset = 0.0
        self.period_sec = 5.0
        self._running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._address_info: Optional[AddressInfo] = None

    def configure(self, address: str, wave_type: WaveformType,
                  amplitude: float, offset: float, period_sec: float) -> bool:
        info = parse_address(address)
        if info is None or info.data_type == "Bool":
            return False
        self.target_address = address
        self._address_info = info
        self.waveform_type = wave_type
        self.amplitude = amplitude
        self.offset = offset
        self.period_sec = max(0.1, period_sec)
        return True

    def _calc_value(self, t: float) -> float:
        """根据时间和波形参数计算当前输出值"""
        phase = (t % self.period_sec) / self.period_sec  # 0~1

        if self.waveform_type == WaveformType.SINE:
            raw = math.sin(phase * 2 * math.pi)
        elif self.waveform_type == WaveformType.SQUARE:
            raw = 1.0 if phase < 0.5 else -1.0
        elif self.waveform_type == WaveformType.TRIANGLE:
            if phase < 0.5:
                raw = 4.0 * phase - 1.0
            else:
                raw = 3.0 - 4.0 * phase
        elif self.waveform_type == WaveformType.SAWTOOTH:
            raw = 2.0 * phase - 1.0
        else:
            raw = 0.0

        return self.offset + self.amplitude * raw

    def _run_loop(self, client: PlcClient):
        info = self._address_info
        if info is None:
            return

        start_time = time.time()
        cycle_interval = 0.05  # 50ms 写入间隔

        while not self._stop_event.is_set():
            t = time.time() - start_time
            value = self._calc_value(t)

            try:
                if info.data_type == "Byte":
                    client.write_bytes(info.area_code, info.db_number, info.byte_offset,
                                       bytearray([max(0, min(255, int(value)))]))
                elif info.data_type == "Word":
                    client.write_word(info.area_code, info.db_number, info.byte_offset,
                                      max(0, min(65535, int(value))))
                elif info.data_type == "DWord":
                    client.write_dword(info.area_code, info.db_number, info.byte_offset,
                                       max(-2147483648, min(2147483647, int(value))))
            except Exception:
                pass

            self._stop_event.wait(cycle_interval)

    def start(self, client: PlcClient) -> bool:
        if self._running or self._address_info is None:
            return False
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, args=(client,), daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
