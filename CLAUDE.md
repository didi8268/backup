# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 环境要求

- **必须使用 Python 3.12 或 3.13**。dearpygui 2.3.1 的 `.pyd` 与 Python 3.14 ABI 不兼容，导入时会 segfault。
- 启动命令：`py -3.13 main.py` 或 `python main.py`（确保 python 指向 3.12/3.13）

## 依赖

| 包 | 版本 | 用途 |
|---|---|---|
| dearpygui | 2.3.1 | GUI 框架，C++ 扩展，API 为 `import dearpygui.dearpygui as dpg` |
| python-snap7 | 3.0.0 | Siemens PLC 通讯，封装 S7 协议 |

```bash
pip install dearpygui==2.3.1 python-snap7
```

## 架构

```
main.py              ← 入口，GUI 布局 (dpg.tab_bar 三页卡) + 渲染循环，所有功能整合
plc_client.py        ← snap7 封装层，地址解析 + 读写
plc_monitor.py       ← MonitorPoint 数据模型 + PlcMonitor 批量刷新（后台线程）
waveform_output.py   ← 波形生成器（正弦/方波/三角/锯齿），后台线程写入 PLC
data_logger.py       ← CSV 记录，后台线程定时写入
alarm_manager.py     ← 阈值比较报警，记录报警事件
```

**数据流**：渲染循环 → `monitor.refresh(plc)` → snap7 读取 PLC → 更新 `MonitorPoint.current_value` → 刷新表格/波形图。波形输出和 CSV 记录使用独立 daemon 线程。

**dearpygui 关键约束**：导入 `dearpygui.dearpygui` 前必须调用 `os.add_dll_directory()` 指向 site-packages 下的 dearpygui 目录（含 `vcruntime140_1.dll`）。

**中文字体**：`dpg.create_context()` 之后、`dpg.create_viewport()` 之前加载 simhei.ttf 或 msyh.ttc，通过 `dpg.font_registry()` + `dpg.add_font(f, 20)` + `dpg.bind_font()` 设置。当前字体大小 20px，视口 1280×850。

## SMART200 PLC 内存区域

| 区域 | 标识 | snap7 area code | 地址示例 |
|------|------|-----------------|----------|
| 输入 | I | 0x81 | `I0.0`, `I1.7` |
| 输出 | Q | 0x82 | `Q0.0` |
| 存储 | M | 0x83 | `M10.3` |
| 变量 | V | 0x84 | `VB100`, `VW200`, `VD300` |

地址解析 `plc_client.py:parse_address()`，支持 `I0.0`, `Q1.7`, `M3.2`, `VB100`, `VW200`, `VD300`。multi-byte 使用 big-endian。`VDxxx` 解析为 `DWord`；Real 类型需用户在添加监控点时手动选择，`PlcMonitor.refresh()` 会走 `struct.unpack(">f")` 分支。

## 后台线程生命周期

`waveform_output.py`、`data_logger.py`、`plc_monitor.py` 使用相同的 daemon 线程模式：
- `start(plc_or_monitor)` — 清除 `_stop_event`，创建 daemon 线程
- `stop()` — 设置 `_stop_event`，`join(timeout=2.0)`
- `_run_loop()` — `while not _stop_event.is_set(): ...; _stop_event.wait(interval)`
- `WaveformOutput.configure()` 必须在 `start()` 之前调用，目标地址不能是 Bool 类型

## 界面结构

使用 `dpg.tab_bar()` 三页卡，无手动切换逻辑：

| 页卡 | 内容 |
|------|------|
| 实时监控 | 多 Y 轴波形图（3 Y 轴 / 共享 X 轴）+ 监控数据表（含写入/删除） |
| 控制设置 | 波形输出配置 + 报警规则管理 |
| 系统设置 | PLC 连接 + 刷新间隔 + 监控点添加表单/管理表格 + 报警历史 |

顶部工具栏：连接状态指示灯 + CSV 记录按钮。底部状态栏：最后刷新时间 / CSV 状态 / 报警计数。

## 波形显示（动态通道）

波形图不再使用固定 4 通道下拉框，而是由「系统设置」页的监控点表格动态决定：

- `wave_visible: dict[int, tuple]` — `{point_index: (visible: bool, y_axis: "left"/"right")}`，由表格中的"波形"复选框和"Y轴"下拉控制
- `wave_series_created: set` — 跟踪已创建的 `wave_series_{idx}` widget
- `wave_buffers: dict[int, deque]` — 每个监控点的历史数据缓冲（已乘比例系数）
- `refresh_waveform_plot()` 比较 `wave_visible` 和 `wave_series_created`，增量创建/删除 line series
- 颜色从 `WAVE_PALETTE`（8 色调色板）按 `idx % 8` 轮转
- 3 个 Y 轴：左(`wave_y_axis_0`)、右(`wave_y_axis_1`)、左2(`wave_y_axis_2`)，用户可选左/右
- 监控点删除时需同步清理 `wave_buffers`、`wave_visible`、`wave_series_created` 并重映射 key

## MonitorPoint 字段

`plc_monitor.py:MonitorPoint` dataclass，关键字段：
- `address`, `name`, `data_type`, `current_value` — 基础信息
- `unit: str` — 工程单位（°C, MPa 等）
- `scale: float` — 比例系数（默认 1.0，显示值 = 原始值 × scale）
- `decimal_places: int` — 小数点位数（0-6）
- `history: list` — 波形历史数据（仅在 `PlcMonitor.refresh()` 中维护，GUI 用 `wave_buffers` 替代）

`MonitorPoint.from_address()` 根据地址自动推断 `data_type`，用户可在添加时覆盖。

## dpg widget tag 命名

| 前缀/标签 | 用途 |
|-----------|------|
| `ip_input`, `rack_input`, `slot_input` | PLC 连接配置 |
| `conn_indicator`, `status_text` | 连接状态 |
| `refresh_interval` | 刷新间隔 (ms) |
| `csv_btn` | CSV 记录开关 |
| `wave_plot`, `wave_x_axis`, `wave_y_axis_{0-2}` | 波形图及坐标轴 |
| `wave_series_{idx}` | 动态线系列（idx=监控点索引） |
| `monitor_table` | 实时监控数据表 |
| `waveout_addr`, `waveout_type`, `waveout_amp`, `waveout_offset`, `waveout_period` | 波形输出配置 |
| `wave_start_btn`, `wave_stop_btn` | 波形输出控制 |
| `alarm_point_combo`, `alarm_op`, `alarm_threshold`, `alarm_msg`, `alarm_table` | 报警 |
| `alarm_history_table` | 报警历史（系统设置页） |
| `new_addr_input`, `new_name_input`, `new_dtype_input`, `new_unit_input`, `new_scale_input`, `new_dec_input` | 添加监控点表单 |
| `points_mgmt_table`, `points_table_container` | 监控点管理表格 |
| `wave_vis_{i}`, `wave_axis_{i}` | 表格中的波形复选框和 Y 轴选择 |
| `status_refresh`, `status_csv`, `status_alarm` | 底部状态栏 |
| `write_val_{i}`, `write_btn_{i}`, `del_btn_{i}` | 数据表中的写入/删除控件 |

## dpg combo 值解析

dpg combo 的 `get_value()` 返回展示字符串 `"名称 (VW100)"`，不是索引。两个辅助函数：
- `_combo_value_to_index(combo_tag)` — 遍历 `monitor.get_points()` 匹配，返回 `int` 索引（-1 无效）
- `_combo_value_to_address(combo_tag)` — 从括号提取地址 `"VW100"`

当前仅 `alarm_point_combo` 和 `waveout_addr` 仍使用 combo。

## 表格刷新模式

两种表格刷新模式，不可混用：

1. **children_only 模式**（`monitor_table`, `alarm_table`, `alarm_history_table`）：
   表在 GUI 构建时定义列，刷新时 `dpg.delete_item(table, children_only=True)` + `dpg.table_row(parent=table)` 重建行。**注意：`children_only=True` 可能在某些 dearpygui 版本删除列定义。**

2. **完全重建模式**（`points_mgmt_table`）：
   表通过 `_refresh_points_table()` 完全删除 (`dpg.delete_item`) 并用 `parent=` 重建，包括列定义。容器为 `points_table_container` (dpg.group)。

## 监控点删除重映射

删除监控点后，`wave_buffers`、`wave_visible` 的 key 需要重映射（> 删除索引的减 1）。`wave_series_created` 用 set 的 `difference_update` + `update` 原地变异（避免闭包内的变量作用域问题）。
