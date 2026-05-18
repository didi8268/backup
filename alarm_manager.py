"""报警管理模块"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable

from plc_monitor import PlcMonitor


class CompareOp(Enum):
    GT = ">"
    LT = "<"
    GE = ">="
    LE = "<="
    EQ = "=="


@dataclass
class AlarmRule:
    point_index: int = 0
    point_name: str = ""
    op: CompareOp = CompareOp.GT
    threshold: float = 0.0
    message: str = ""
    enabled: bool = True


@dataclass
class AlarmEvent:
    rule: AlarmRule
    value: float
    timestamp: str = ""
    active: bool = True

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")


class AlarmManager:
    def __init__(self):
        self.rules: list[AlarmRule] = []
        self._events: list[AlarmEvent] = []
        self._active_rule_keys: set[tuple[int, CompareOp, float]] = set()
        self._on_alarm: Optional[Callable] = None

    def set_on_alarm(self, callback: Callable):
        self._on_alarm = callback

    def add_rule(self, point_index: int, point_name: str, op: CompareOp,
                 threshold: float, message: str = "") -> AlarmRule:
        rule = AlarmRule(
            point_index=point_index,
            point_name=point_name,
            op=op,
            threshold=threshold,
            message=message or f"{point_name} {op.value} {threshold}",
        )
        self.rules.append(rule)
        return rule

    def remove_rule(self, index: int) -> bool:
        if 0 <= index < len(self.rules):
            rule = self.rules.pop(index)
            self._active_rule_keys.discard(self._rule_key(rule))
            return True
        return False

    def remap_after_point_delete(self, deleted_index: int):
        new_rules = []
        for rule in self.rules:
            if rule.point_index == deleted_index:
                continue
            if rule.point_index > deleted_index:
                rule.point_index -= 1
            new_rules.append(rule)
        self.rules = new_rules
        self._active_rule_keys = {
            self._rule_key(rule)
            for rule in self.rules
            if self._rule_key(rule) in self._active_rule_keys
        }

    def get_events(self) -> list[AlarmEvent]:
        return list(self._events)

    def _rule_key(self, rule: AlarmRule) -> tuple[int, CompareOp, float]:
        return (rule.point_index, rule.op, rule.threshold)

    def check(self, monitor: PlcMonitor):
        points = monitor.get_points()
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        for rule in self.rules:
            if not rule.enabled:
                continue
            if rule.point_index >= len(points):
                continue

            point = points[rule.point_index]
            val = point.current_value
            if val is None:
                continue

            try:
                val_num = float(val)
            except (TypeError, ValueError):
                continue

            triggered = False
            if rule.op == CompareOp.GT:
                triggered = val_num > rule.threshold
            elif rule.op == CompareOp.LT:
                triggered = val_num < rule.threshold
            elif rule.op == CompareOp.GE:
                triggered = val_num >= rule.threshold
            elif rule.op == CompareOp.LE:
                triggered = val_num <= rule.threshold
            elif rule.op == CompareOp.EQ:
                triggered = val_num == rule.threshold

            rule_key = self._rule_key(rule)
            if triggered:
                if rule_key in self._active_rule_keys:
                    continue
                self._active_rule_keys.add(rule_key)
                event = AlarmEvent(rule=rule, value=val_num, timestamp=now)
                self._events.append(event)
                # 保持最近 1000 条报警
                if len(self._events) > 1000:
                    self._events = self._events[-500:]
                if self._on_alarm:
                    self._on_alarm(event)
            else:
                self._active_rule_keys.discard(rule_key)

    def clear_events(self):
        self._events.clear()
