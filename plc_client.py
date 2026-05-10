"""SMART200 PLC 通讯模块 - 基于 snap7"""

import struct
import re
from dataclasses import dataclass
from typing import Optional

import snap7
from snap7 import client as snap7_client

# SMART200 (S7-200) 内存区域代码
AREA_MAP = {
    "I": 0x81,  # 输入
    "Q": 0x82,  # 输出
    "M": 0x83,  # 存储
    "V": 0x84,  # 变量
}

# 地址解析正则: I0.0, Q1.7, M3.2, VB100, VW100, VD200
ADDR_PATTERN = re.compile(
    r"^(?P<area>[IQM])(?P<byte>\d+)\.(?P<bit>[0-7])$|"
    r"^(?P<v_area>V)(?P<v_type>[BWD])(?P<v_offset>\d+)$"
)


@dataclass
class AddressInfo:
    area_code: int
    db_number: int = 0
    byte_offset: int = 0
    bit_offset: int = -1  # -1 表示非位类型
    data_type: str = ""   # Bool, Byte, Word, DWord, Real
    size: int = 1         # 读取字节数


def parse_address(address: str) -> Optional[AddressInfo]:
    """解析 PLC 地址字符串"""
    m = ADDR_PATTERN.match(address.strip().upper())
    if not m:
        return None

    if m.group("area"):
        # 位地址: I0.0, Q1.2, M3.7
        area = m.group("area")
        return AddressInfo(
            area_code=AREA_MAP[area],
            byte_offset=int(m.group("byte")),
            bit_offset=int(m.group("bit")),
            data_type="Bool",
            size=1,
        )
    else:
        # V 区地址: VB100, VW100, VD200
        v_type = m.group("v_type")
        offset = int(m.group("v_offset"))
        type_map = {"B": (1, "Byte"), "W": (2, "Word"), "D": (4, "DWord")}
        size, dtype = type_map[v_type]
        return AddressInfo(
            area_code=AREA_MAP["V"],
            byte_offset=offset,
            data_type=dtype,
            size=size,
        )


class PlcClient:
    def __init__(self):
        self._client = snap7_client.Client()
        self._connected = False

    def connect(self, ip: str, rack: int = 0, slot: int = 0) -> bool:
        try:
            if self._connected:
                self.disconnect()
            self._client.connect(ip, rack, slot)
            self._connected = self._client.get_connected()
            return self._connected
        except Exception:
            self._connected = False
            return False

    def disconnect(self):
        try:
            if self._connected:
                self._client.disconnect()
        except Exception:
            pass
        self._connected = False

    def is_connected(self) -> bool:
        if not self._connected:
            return False
        try:
            self._connected = self._client.get_connected()
            return self._connected
        except Exception:
            self._connected = False
            return False

    def read_bytes(self, area: int, db_number: int, start: int, size: int) -> Optional[bytearray]:
        try:
            return self._client.read_area(area, db_number, start, size)
        except Exception:
            return None

    def write_bytes(self, area: int, db_number: int, start: int, data: bytearray) -> bool:
        try:
            self._client.write_area(area, db_number, start, data)
            return True
        except Exception:
            return False

    def read_bool(self, area: int, db_number: int, byte_offset: int, bit_offset: int) -> Optional[bool]:
        data = self.read_bytes(area, db_number, byte_offset, 1)
        if data is None or len(data) == 0:
            return None
        return bool(data[0] & (1 << bit_offset))

    def write_bool(self, area: int, db_number: int, byte_offset: int, bit_offset: int, value: bool) -> bool:
        data = self.read_bytes(area, db_number, byte_offset, 1)
        if data is None or len(data) == 0:
            return False
        current = data[0]
        if value:
            current |= (1 << bit_offset)
        else:
            current &= ~(1 << bit_offset)
        return self.write_bytes(area, db_number, byte_offset, bytearray([current]))

    def read_word(self, area: int, db_number: int, start: int) -> Optional[int]:
        data = self.read_bytes(area, db_number, start, 2)
        if data is None or len(data) < 2:
            return None
        return struct.unpack(">H", bytes(data[:2]))[0]

    def write_word(self, area: int, db_number: int, start: int, value: int) -> bool:
        data = struct.pack(">H", value & 0xFFFF)
        return self.write_bytes(area, db_number, start, bytearray(data))

    def read_dword(self, area: int, db_number: int, start: int) -> Optional[int]:
        data = self.read_bytes(area, db_number, start, 4)
        if data is None or len(data) < 4:
            return None
        return struct.unpack(">I", bytes(data[:4]))[0]

    def write_dword(self, area: int, db_number: int, start: int, value: int) -> bool:
        data = struct.pack(">I", value & 0xFFFFFFFF)
        return self.write_bytes(area, db_number, start, bytearray(data))

    def read_real(self, area: int, db_number: int, start: int) -> Optional[float]:
        data = self.read_bytes(area, db_number, start, 4)
        if data is None or len(data) < 4:
            return None
        return struct.unpack(">f", bytes(data[:4]))[0]

    def write_real(self, area: int, db_number: int, start: int, value: float) -> bool:
        data = struct.pack(">f", value)
        return self.write_bytes(area, db_number, start, bytearray(data))

    def read_by_address(self, address: str) -> Optional:
        info = parse_address(address)
        if info is None:
            return None
        if info.data_type == "Bool":
            return self.read_bool(info.area_code, info.db_number, info.byte_offset, info.bit_offset)
        elif info.data_type == "Byte":
            data = self.read_bytes(info.area_code, info.db_number, info.byte_offset, 1)
            return data[0] if data else None
        elif info.data_type == "Word":
            return self.read_word(info.area_code, info.db_number, info.byte_offset)
        elif info.data_type == "DWord":
            return self.read_dword(info.area_code, info.db_number, info.byte_offset)
        return None

    def write_by_address(self, address: str, value) -> bool:
        info = parse_address(address)
        if info is None:
            return False
        if info.data_type == "Bool":
            return self.write_bool(info.area_code, info.db_number, info.byte_offset, info.bit_offset, bool(value))
        elif info.data_type == "Byte":
            return self.write_bytes(info.area_code, info.db_number, info.byte_offset, bytearray([int(value) & 0xFF]))
        elif info.data_type == "Word":
            return self.write_word(info.area_code, info.db_number, info.byte_offset, int(value))
        elif info.data_type == "DWord":
            return self.write_dword(info.area_code, info.db_number, info.byte_offset, int(value))
        return False
