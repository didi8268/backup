"""SMART200 PLC 通讯软件 - GUI 主程序"""

import os
import sys
import time
import math
from collections import deque

# DLL 路径必须在 import dearpygui 之前设置
_dpg_dir = os.path.join(
    os.path.dirname(sys.executable), "Lib", "site-packages", "dearpygui"
)
if os.path.isdir(_dpg_dir):
    os.add_dll_directory(_dpg_dir)

import dearpygui.dearpygui as dpg

from plc_client import PlcClient, parse_address
from plc_monitor import PlcMonitor, MonitorPoint
from waveform_output import WaveformOutput, WaveformType
from data_logger import DataLogger
from alarm_manager import AlarmManager, CompareOp, AlarmEvent

# ── 全局状态 ──────────────────────────────────────────────
plc = PlcClient()
monitor = PlcMonitor()
wave_output = WaveformOutput()
data_logger = DataLogger()
alarm_mgr = AlarmManager()

last_refresh_time = 0
wave_buffers: dict[int, deque] = {}
WAVE_HISTORY_SEC = 60

# 波形显示状态: {point_index: (visible: bool, y_axis: str "left"/"right")}
wave_visible: dict[int, tuple] = {}
wave_series_created: set = set()  # 已创建的 series 对应的 point_index

# 预置示例监控点（方便测试）
_monitor_test_points = [
    ("VW100", "温度传感器", "Word", "°C", 0.1, 1),
    ("VW102", "压力传感器", "Word", "MPa", 0.01, 2),
    ("I0.0", "急停信号", "Bool", "", 1.0, 0),
]
for addr, name, dt, unit, scale, dec in _monitor_test_points:
    monitor.add_point(addr, name, data_type=dt, unit=unit, scale=scale, decimal_places=dec)

# ── 配色 ──────────────────────────────────────────────────
BG_DARK = (22, 22, 40)
BG_SIDEBAR = (16, 16, 32)
BG_CARD = (30, 30, 54)
BG_INPUT = (40, 40, 68)
ACCENT = (70, 140, 220)
ACCENT_HOVER = (95, 160, 235)
GREEN = (0, 210, 140)
RED = (255, 70, 70)
YELLOW = (255, 180, 0)
TEXT_PRIMARY = (220, 220, 225)
TEXT_SECONDARY = (140, 140, 160)
BORDER = (50, 50, 80)

# 波形颜色轮转 (支持无限通道)
WAVE_PALETTE = [
    (70, 140, 220),    # 蓝
    (0, 210, 140),     # 绿
    (255, 180, 0),     # 黄
    (255, 100, 100),   # 红
    (160, 100, 255),   # 紫
    (0, 200, 200),     # 青
    (255, 140, 60),    # 橙
    (180, 180, 220),   # 浅紫
]


# ── 辅助函数 ──────────────────────────────────────────────

def update_status(text: str, color=TEXT_SECONDARY):
    if dpg.does_item_exist("status_text"):
        dpg.set_value("status_text", text)
        dpg.configure_item("status_text", color=color)


def refresh_monitor_table():
    global last_refresh_time
    now = time.time()
    if not dpg.does_item_exist("refresh_interval"):
        return
    interval = dpg.get_value("refresh_interval")
    if now - last_refresh_time < interval / 1000.0:
        return
    last_refresh_time = now

    if not plc.is_connected():
        update_status("未连接", YELLOW)
        return

    monitor.refresh(plc)

    points = monitor.get_points()
    table_tag = "monitor_table"
    if not dpg.does_item_exist(table_tag):
        return

    dpg.delete_item(table_tag, children_only=True)

    for i, pt in enumerate(points):
        with dpg.table_row(parent=table_tag):
            dpg.add_text(str(i + 1))
            dpg.add_text(pt.address)
            dpg.add_text(pt.name)
            dpg.add_text(pt.data_type)
            # 应用比例系数和格式化显示
            if pt.current_value is not None:
                try:
                    display_val = float(pt.current_value) * pt.scale
                    val_str = f"{display_val:.{pt.decimal_places}f}"
                    if pt.unit:
                        val_str += f" {pt.unit}"
                except (TypeError, ValueError):
                    val_str = str(pt.current_value)
            else:
                val_str = "N/A"
            dpg.add_text(val_str, color=GREEN if pt.current_value is not None else TEXT_SECONDARY)

            with dpg.group(horizontal=True):
                dpg.add_input_text(
                    tag=f"write_val_{i}", width=80, default_value="",
                    hint="输入值"
                )
                dpg.add_button(
                    label="写入", tag=f"write_btn_{i}",
                    callback=on_write_value, user_data=i, width=50
                )

            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="删除", tag=f"del_btn_{i}",
                    callback=on_delete_point, user_data=i, width=40
                )

        if i % 2 == 1:
            dpg.highlight_table_row(table_tag, i, BG_CARD)

    for i, pt in enumerate(points):
        if pt.current_value is not None:
            if i not in wave_buffers:
                wave_buffers[i] = deque(maxlen=600)
            try:
                wave_buffers[i].append((now, float(pt.current_value) * pt.scale))
            except (TypeError, ValueError):
                pass

    refresh_waveform_plot()
    alarm_mgr.check(monitor)
    refresh_alarm_history_table()

    update_status(f"已连接 | 最后刷新: {monitor.last_refresh_time}", GREEN)
    if dpg.does_item_exist("status_refresh"):
        dpg.set_value("status_refresh", f"最后刷新: {monitor.last_refresh_time}")
    if dpg.does_item_exist("status_csv"):
        dpg.set_value("status_csv", f"CSV: {'记录中' if data_logger._running else '停止'}")
    if dpg.does_item_exist("status_alarm"):
        dpg.set_value("status_alarm", f"报警: {len(alarm_mgr._events)}条")


def _combo_value_to_index(combo_tag: str) -> int:
    val = dpg.get_value(combo_tag)
    if not val or val.startswith("(无"):
        return -1
    points = monitor.get_points()
    for i, p in enumerate(points):
        if val == f"{p.name} ({p.address})":
            return i
    return -1


def _combo_value_to_address(combo_tag: str) -> str:
    val = dpg.get_value(combo_tag)
    if not val or val.startswith("(无"):
        return ""
    if "(" in val and val.endswith(")"):
        return val[val.rindex("(") + 1:-1]
    return val


def refresh_waveform_plot():
    plot_tag = "wave_plot"
    if not dpg.does_item_exist(plot_tag):
        return

    points = monitor.get_points()
    now = time.time()

    # 收集需要显示的监控点 (visible + has buffer)
    desired = set()
    for idx, (visible, _) in wave_visible.items():
        if visible and idx < len(points) and idx in wave_buffers:
            desired.add(idx)

    # 移除不再需要的 series
    to_remove = wave_series_created - desired
    for idx in to_remove:
        tag = f"wave_series_{idx}"
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)
    wave_series_created.difference_update(to_remove)

    # 创建新增的 series
    for idx in desired - wave_series_created:
        if idx >= len(points):
            continue
        _, y_side = wave_visible.get(idx, (True, "left"))
        axis_tag = "wave_y_axis_0" if y_side == "left" else "wave_y_axis_1"
        if not dpg.does_item_exist(axis_tag):
            continue
        color = WAVE_PALETTE[idx % len(WAVE_PALETTE)]
        # 创建主题
        theme_tag = f"wave_theme_{idx}"
        if not dpg.does_item_exist(theme_tag):
            with dpg.theme(tag=theme_tag):
                with dpg.theme_component(dpg.mvLineSeries):
                    dpg.add_theme_color(dpg.mvPlotCol_Line, color)
        dpg.add_line_series(
            [], [], parent=axis_tag, tag=f"wave_series_{idx}",
            label=points[idx].name
        )
        dpg.bind_item_theme(f"wave_series_{idx}", theme_tag)
        wave_series_created.add(idx)

    # 更新数据
    for idx in wave_series_created:
        tag = f"wave_series_{idx}"
        if not dpg.does_item_exist(tag):
            wave_series_created.discard(idx)
            continue
        buf = wave_buffers.get(idx)
        if buf and buf:
            xs = [t - now for t, _ in buf]
            ys = [v for _, v in buf]
            dpg.set_value(tag, [xs, ys])
        else:
            dpg.set_value(tag, [[], []])

    # 更新 Y 轴标签
    left_names = []
    right_names = []
    for idx in sorted(wave_series_created):
        if idx < len(points):
            _, y_side = wave_visible.get(idx, (True, "left"))
            if y_side == "left":
                left_names.append(points[idx].name)
            else:
                right_names.append(points[idx].name)

    if dpg.does_item_exist("wave_y_axis_0"):
        dpg.configure_item("wave_y_axis_0", label=" / ".join(left_names[:3]) if left_names else "Y左")
    if dpg.does_item_exist("wave_y_axis_1"):
        dpg.configure_item("wave_y_axis_1", label=" / ".join(right_names[:3]) if right_names else "Y右")
    if dpg.does_item_exist("wave_y_axis_2"):
        dpg.configure_item("wave_y_axis_2", label="")


# ── 回调函数 ──────────────────────────────────────────────

def on_connect():
    ip = dpg.get_value("ip_input")
    rack = dpg.get_value("rack_input")
    slot = dpg.get_value("slot_input")
    if plc.connect(ip, rack, slot):
        update_status(f"已连接 {ip}", GREEN)
        if dpg.does_item_exist("conn_indicator"):
            dpg.configure_item("conn_indicator", color=GREEN)
    else:
        update_status(f"连接失败 {ip}", RED)
        if dpg.does_item_exist("conn_indicator"):
            dpg.configure_item("conn_indicator", color=RED)


def on_disconnect():
    monitor.stop()
    wave_output.stop()
    data_logger.stop()
    plc.disconnect()
    update_status("已断开", YELLOW)
    if dpg.does_item_exist("conn_indicator"):
        dpg.configure_item("conn_indicator", color=TEXT_SECONDARY)
    if dpg.does_item_exist("status_csv"):
        dpg.set_value("status_csv", "CSV: 停止")
    global last_refresh_time
    last_refresh_time = 0


def on_add_point():
    address = dpg.get_value("new_addr_input")
    name = dpg.get_value("new_name_input")
    data_type = dpg.get_value("new_dtype_input")
    unit = dpg.get_value("new_unit_input")
    scale = dpg.get_value("new_scale_input")
    decimal_places = dpg.get_value("new_dec_input")
    if not address.strip():
        return
    pt = monitor.add_point(address.strip(), name.strip(),
                           data_type=data_type, unit=unit.strip(),
                           scale=scale, decimal_places=decimal_places)
    if pt is None:
        update_status(f"地址格式无效: {address}", RED)
    else:
        update_status(f"已添加: {pt.address}", GREEN)
        dpg.set_value("new_addr_input", "")
        dpg.set_value("new_name_input", "")
        dpg.set_value("new_unit_input", "")
        dpg.set_value("new_scale_input", 1.0)
        dpg.set_value("new_dec_input", 1)
        _refresh_point_combos()


def on_delete_point(sender, app_data, user_data):
    idx = user_data
    if monitor.remove_point(idx):
        wave_buffers.pop(idx, None)
        wave_visible.pop(idx, None)
        wave_series_created.discard(idx)
        # 重映射 buffer / visible key（大于删除索引的 key 减 1）
        for src in [wave_buffers, wave_visible]:
            new_src = {}
            for old_k, v in src.items():
                if old_k > idx:
                    new_src[old_k - 1] = v
                elif old_k < idx:
                    new_src[old_k] = v
            src.clear()
            src.update(new_src)
        remap = {k - 1 for k in wave_series_created if k > idx}
        wave_series_created.difference_update({k for k in wave_series_created if k >= idx})
        wave_series_created.update(remap)
        _refresh_point_combos()
        update_status("监控点已删除", YELLOW)


def on_write_value(sender, app_data, user_data):
    idx = user_data
    val_str = dpg.get_value(f"write_val_{idx}")
    if not val_str.strip():
        return
    points = monitor.get_points()
    if idx >= len(points):
        return
    pt = points[idx]
    try:
        if pt.data_type == "Bool":
            val = val_str.lower() in ("true", "1", "yes", "on")
        elif pt.data_type in ("Byte", "Word", "DWord"):
            val = int(val_str)
        else:
            val = float(val_str)
    except ValueError:
        update_status(f"写入值格式错误: {val_str}", RED)
        return

    if plc.is_connected():
        if plc.write_by_address(pt.address, val):
            update_status(f"写入成功: {pt.address} = {val}", GREEN)
        else:
            update_status(f"写入失败: {pt.address}", RED)
    else:
        update_status("未连接 PLC", RED)


def on_start_csv():
    if not data_logger._running:
        data_logger.start(monitor)
        update_status(f"CSV 记录已开始: {data_logger.filepath}", GREEN)
        if dpg.does_item_exist("csv_btn"):
            dpg.configure_item("csv_btn", label="停止记录")


def on_stop_csv():
    if data_logger._running:
        data_logger.stop()
        update_status("CSV 记录已停止", YELLOW)
        if dpg.does_item_exist("csv_btn"):
            dpg.configure_item("csv_btn", label="开始记录CSV")


def on_csv_toggle():
    if data_logger._running:
        on_stop_csv()
    else:
        on_start_csv()


def on_wave_start():
    addr = _combo_value_to_address("waveout_addr")
    if not addr:
        update_status("请选择有效的目标地址", RED)
        return

    wtype_str = dpg.get_value("waveout_type")
    amp = dpg.get_value("waveout_amp")
    offset = dpg.get_value("waveout_offset")
    period = dpg.get_value("waveout_period")

    wtype_map = {
        "正弦波": WaveformType.SINE,
        "方波": WaveformType.SQUARE,
        "三角波": WaveformType.TRIANGLE,
        "锯齿波": WaveformType.SAWTOOTH,
    }
    wtype = wtype_map.get(wtype_str, WaveformType.SINE)

    if wave_output.configure(addr, wtype, amp, offset, period):
        if wave_output.start(plc):
            update_status(f"波形输出已开始: {addr}", GREEN)
            dpg.configure_item("wave_start_btn", label="输出中...", enabled=False)
            dpg.configure_item("wave_stop_btn", enabled=True)
    else:
        update_status("波形输出配置失败（地址无效或为位地址）", RED)


def on_wave_stop():
    wave_output.stop()
    update_status("波形输出已停止", YELLOW)
    dpg.configure_item("wave_start_btn", label="开始输出", enabled=True)
    dpg.configure_item("wave_stop_btn", enabled=False)


def on_add_alarm():
    combo_val = _combo_value_to_index("alarm_point_combo")
    if combo_val < 0:
        update_status("请先添加有效的监控点", RED)
        return

    op_str = dpg.get_value("alarm_op")
    threshold = dpg.get_value("alarm_threshold")
    msg = dpg.get_value("alarm_msg")

    op_map = {">": CompareOp.GT, "<": CompareOp.LT, ">=": CompareOp.GE,
              "<=": CompareOp.LE, "==": CompareOp.EQ}
    op = op_map.get(op_str, CompareOp.GT)

    points = monitor.get_points()
    if combo_val < len(points):
        alarm_mgr.add_rule(combo_val, points[combo_val].name, op, threshold, msg)
        update_status(f"报警规则已添加: {points[combo_val].name}", GREEN)
        refresh_alarm_table()


def refresh_alarm_table():
    table_tag = "alarm_table"
    if not dpg.does_item_exist(table_tag):
        return
    dpg.delete_item(table_tag, children_only=True)

    for i, rule in enumerate(alarm_mgr.rules):
        with dpg.table_row(parent=table_tag):
            dpg.add_text(rule.point_name)
            dpg.add_text(rule.op.value)
            dpg.add_text(str(rule.threshold))
            dpg.add_text("启用" if rule.enabled else "禁用")
            dpg.add_text(rule.message)
            dpg.add_button(label="删除", callback=lambda s, a, u: (
                alarm_mgr.remove_rule(u), refresh_alarm_table()
            ), user_data=i, width=40)


def refresh_alarm_history_table():
    table_tag = "alarm_history_table"
    if not dpg.does_item_exist(table_tag):
        return
    dpg.delete_item(table_tag, children_only=True)

    for i, event in enumerate(reversed(alarm_mgr._events)):
        with dpg.table_row(parent=table_tag):
            dpg.add_text(event.timestamp)
            dpg.add_text(event.rule.point_name)
            dpg.add_text(f"{event.value:.2f}" if isinstance(event.value, float) else str(event.value))
            dpg.add_text(event.rule.message)
        if i % 2 == 1:
            dpg.highlight_table_row(table_tag, i, BG_CARD)


def on_clear_alarm_history():
    alarm_mgr.clear_events()
    refresh_alarm_history_table()
    update_status("报警历史已清除", YELLOW)


def _refresh_point_combos():
    """刷新所有监控点下拉列表和点管理表格"""
    points = monitor.get_points()
    items = [f"{p.name} ({p.address})" for p in points]
    if not items:
        items = ["(无监控点)"]

    if dpg.does_item_exist("alarm_point_combo"):
        dpg.configure_item("alarm_point_combo", items=items)
        if items:
            dpg.set_value("alarm_point_combo", items[0])

    if dpg.does_item_exist("waveout_addr"):
        write_items = [f"{p.name} ({p.address})" for p in points if p.data_type != "Bool"]
        if not write_items:
            write_items = ["(无可写入的监控点)"]
        dpg.configure_item("waveout_addr", items=write_items)
        if write_items:
            dpg.set_value("waveout_addr", write_items[0])

    _refresh_points_table()


def _refresh_points_table():
    """完全重建监控点管理表格（删除旧表并新建）"""
    old_tag = "points_mgmt_table"
    if dpg.does_item_exist(old_tag):
        parent = dpg.get_item_parent(old_tag)
        dpg.delete_item(old_tag)
    else:
        # 如果旧表不存在（首次调用），从容器获取 parent
        if not dpg.does_item_exist("points_table_container"):
            return
        parent = "points_table_container"

    points = monitor.get_points()
    with dpg.table(
        tag="points_mgmt_table", parent=parent, header_row=True,
        borders_innerH=True, borders_outerH=True,
        borders_innerV=True, borders_outerV=True,
        policy=dpg.mvTable_SizingStretchProp,
    ):
        dpg.add_table_column(label="#", width_fixed=True, init_width_or_weight=25)
        dpg.add_table_column(label="地址", width_fixed=True, init_width_or_weight=75)
        dpg.add_table_column(label="名称", width_fixed=True, init_width_or_weight=80)
        dpg.add_table_column(label="类型", width_fixed=True, init_width_or_weight=50)
        dpg.add_table_column(label="单位", width_fixed=True, init_width_or_weight=45)
        dpg.add_table_column(label="比例", width_fixed=True, init_width_or_weight=55)
        dpg.add_table_column(label="小数", width_fixed=True, init_width_or_weight=40)
        dpg.add_table_column(label="波形")
        dpg.add_table_column(label="Y轴", width_fixed=True, init_width_or_weight=50)
        dpg.add_table_column(label="删除", width_fixed=True, init_width_or_weight=45)

        for i, pt in enumerate(points):
            with dpg.table_row():
                dpg.add_text(str(i + 1))
                dpg.add_text(pt.address)
                dpg.add_text(pt.name)
                dpg.add_text(pt.data_type)
                dpg.add_text(pt.unit)
                dpg.add_text(f"{pt.scale:.4g}")
                dpg.add_text(str(pt.decimal_places))
                visible, y_side = wave_visible.get(i, (False, "left"))
                dpg.add_checkbox(
                    tag=f"wave_vis_{i}", default_value=visible,
                    callback=lambda s, a, u: _on_wave_vis_toggle(u, a),
                    user_data=i
                )
                dpg.add_combo(
                    tag=f"wave_axis_{i}",
                    items=["左", "右"],
                    default_value="左" if y_side == "left" else "右",
                    width=50,
                    callback=lambda s, a, u: _on_wave_axis_change(u, a),
                    user_data=i
                )
                dpg.add_button(
                    label="删除",
                    callback=on_delete_point,
                    user_data=i, width=40
                )
            if i % 2 == 1:
                dpg.highlight_table_row("points_mgmt_table", i, BG_CARD)


def _on_wave_vis_toggle(idx: int, val: bool):
    """波形显示复选框切换"""
    if idx not in wave_visible:
        wave_visible[idx] = (val, "left")
    else:
        _, y_side = wave_visible[idx]
        wave_visible[idx] = (val, y_side)
    if not val:
        wave_series_created.discard(idx)


def _on_wave_axis_change(idx: int, val: str):
    """Y 轴选择变更"""
    side = "left" if val == "左" else "right"
    if idx not in wave_visible:
        wave_visible[idx] = (False, side)
    else:
        vis, _ = wave_visible[idx]
        wave_visible[idx] = (vis, side)
    # 轴变更后需要重建 series
    wave_series_created.discard(idx)


# ── 主函数 ──────────────────────────────────────────────

def main():
    dpg.create_context()

    # 加载中文字体
    for f in ["C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/msyh.ttc"]:
        if os.path.isfile(f):
            with dpg.font_registry():
                default_font = dpg.add_font(f, 20)
            dpg.bind_font(default_font)
            break

    # 深色主题
    with dpg.theme() as theme_id:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, BG_DARK)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, BG_CARD)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, BG_INPUT)
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT_PRIMARY)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, TEXT_SECONDARY)
            dpg.add_theme_color(dpg.mvThemeCol_Button, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_Header, BG_INPUT)
            dpg.add_theme_color(dpg.mvThemeCol_Separator, BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_TableBorderStrong, BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, BG_DARK)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, BG_INPUT)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, BG_DARK)
    dpg.bind_theme(theme_id)

    dpg.create_viewport(title="SMART200 PLC 通讯软件", width=1280, height=850,
                        min_width=1000, min_height=700)

    # ── 构建 GUI ──
    with dpg.window(label="SMART200 PLC 通讯软件", tag="main_window", no_close=True):
        # 顶部工具栏：状态 + 控制
        with dpg.group(horizontal=True):
            dpg.add_text("●", tag="conn_indicator", color=TEXT_SECONDARY)
            dpg.add_text("未连接", tag="status_text", color=TEXT_SECONDARY)
            dpg.add_text("|", color=BORDER)
            dpg.add_button(label="开始记录CSV", tag="csv_btn",
                           callback=on_csv_toggle, width=100)
        dpg.add_separator()

        # Tab 导航
        with dpg.tab_bar():
            with dpg.tab(label="实时监控"):
                # ── 实时监控模块 ──
                dpg.add_text("◆ 实时波形", color=ACCENT)
                dpg.add_separator()
                dpg.add_spacer(height=6)

                with dpg.plot(
                    tag="wave_plot", label="实时波形", height=380, width=-1,
                    anti_aliased=True,
                ):
                    dpg.add_plot_legend()
                    dpg.add_plot_axis(dpg.mvXAxis, label="时间 (秒)", tag="wave_x_axis")
                    # 3 个 Y 轴：左 / 右 / 左
                    dpg.add_plot_axis(dpg.mvYAxis, label="Y左", tag="wave_y_axis_0")
                    dpg.add_plot_axis(dpg.mvYAxis2, label="Y右", tag="wave_y_axis_1", opposite=True)
                    dpg.add_plot_axis(dpg.mvYAxis3, label="Y左2", tag="wave_y_axis_2")
                    dpg.set_axis_limits("wave_x_axis", -60, 0)
                    dpg.set_axis_limits_auto("wave_y_axis_0")
                    dpg.set_axis_limits_auto("wave_y_axis_1")
                    dpg.set_axis_limits_auto("wave_y_axis_2")

                dpg.add_text("在「系统设置」中勾选监控点的「显示波形」即可在此查看",
                             color=TEXT_SECONDARY)

                dpg.add_spacer(height=6)
                dpg.add_text("◆ 监控数据", color=ACCENT)
                dpg.add_separator()
                dpg.add_spacer(height=4)

                with dpg.table(
                    tag="monitor_table", header_row=True, borders_innerH=True,
                    borders_outerH=True, borders_innerV=True, borders_outerV=True,
                    policy=dpg.mvTable_SizingStretchProp,
                ):
                    dpg.add_table_column(label="序号", width_fixed=True, init_width_or_weight=40)
                    dpg.add_table_column(label="地址", width_fixed=True, init_width_or_weight=80)
                    dpg.add_table_column(label="名称", width_fixed=True, init_width_or_weight=80)
                    dpg.add_table_column(label="类型", width_fixed=True, init_width_or_weight=60)
                    dpg.add_table_column(label="当前值", width_fixed=True, init_width_or_weight=80)
                    dpg.add_table_column(label="写入值")
                    dpg.add_table_column(label="操作", width_fixed=True, init_width_or_weight=80)

            with dpg.tab(label="控制设置"):
                dpg.add_text("◆ 波形输出", color=ACCENT)
                dpg.add_separator()
                dpg.add_spacer(height=6)

                points = monitor.get_points()
                out_items = [f"{p.name} ({p.address})" for p in points if p.data_type != "Bool"]
                if not out_items:
                    out_items = ["(无可写入的监控点)"]

                with dpg.group(horizontal=True):
                    dpg.add_text("目标地址:")
                    dpg.add_combo(tag="waveout_addr", items=out_items, width=180)
                    dpg.add_spacer(width=20)
                    dpg.add_text("类型:")
                    dpg.add_combo(
                        tag="waveout_type",
                        items=["正弦波", "方波", "三角波", "锯齿波"],
                        default_value="正弦波", width=100
                    )

                dpg.add_spacer(height=6)

                with dpg.group(horizontal=True):
                    dpg.add_text("振幅:")
                    dpg.add_input_float(tag="waveout_amp", default_value=100.0, width=100, step=10)
                    dpg.add_spacer(width=15)
                    dpg.add_text("偏移:")
                    dpg.add_input_float(tag="waveout_offset", default_value=0.0, width=100, step=10)
                    dpg.add_spacer(width=15)
                    dpg.add_text("周期(秒):")
                    dpg.add_input_float(tag="waveout_period", default_value=5.0, width=100, step=0.5,
                                        min_value=0.1, max_value=3600.0)

                dpg.add_spacer(height=8)
                with dpg.group(horizontal=True):
                    dpg.add_button(label="开始输出", tag="wave_start_btn",
                                   callback=on_wave_start, width=100)
                    dpg.add_button(label="停止输出", tag="wave_stop_btn",
                                   callback=on_wave_stop, enabled=False, width=100)

                dpg.add_spacer(height=6)
                dpg.add_text("波形输出需要已连接 PLC，且目标地址为非 Bool 类型（VW/VD 等）",
                             color=TEXT_SECONDARY)

                dpg.add_spacer(height=16)
                dpg.add_text("◆ 报警规则", color=ACCENT)
                dpg.add_separator()
                dpg.add_spacer(height=6)

                alarm_items = [f"{p.name} ({p.address})" for p in monitor.get_points()] or ["(无监控点)"]

                with dpg.group(horizontal=True):
                    dpg.add_text("监控点:")
                    dpg.add_combo(tag="alarm_point_combo", items=alarm_items, width=180)
                    dpg.add_spacer(width=15)
                    dpg.add_text("条件:")
                    dpg.add_combo(tag="alarm_op", items=[">", "<", ">=", "<=", "=="],
                                  default_value=">", width=60)
                    dpg.add_spacer(width=15)
                    dpg.add_text("阈值:")
                    dpg.add_input_float(tag="alarm_threshold", default_value=100.0, width=100)
                    dpg.add_spacer(width=15)
                    dpg.add_text("描述:")
                    dpg.add_input_text(tag="alarm_msg", width=100, hint="报警描述")

                dpg.add_spacer(height=6)
                dpg.add_button(label="+ 添加规则", callback=on_add_alarm)

                dpg.add_spacer(height=8)

                with dpg.table(
                    tag="alarm_table", header_row=True, borders_innerH=True,
                    borders_outerH=True, borders_innerV=True, borders_outerV=True,
                ):
                    dpg.add_table_column(label="监控点")
                    dpg.add_table_column(label="条件")
                    dpg.add_table_column(label="阈值")
                    dpg.add_table_column(label="状态")
                    dpg.add_table_column(label="描述")
                    dpg.add_table_column(label="操作", width_fixed=True, init_width_or_weight=60)

            with dpg.tab(label="系统设置"):
                dpg.add_text("◆ PLC 连接", color=ACCENT)
                dpg.add_separator()
                dpg.add_spacer(height=6)

                with dpg.group(horizontal=True):
                    dpg.add_text("IP 地址:")
                    dpg.add_input_text(tag="ip_input", default_value="192.168.2.1", width=130)
                    dpg.add_spacer(width=15)
                    dpg.add_text("Rack:")
                    dpg.add_input_int(tag="rack_input", default_value=0, width=80)
                    dpg.add_spacer(width=15)
                    dpg.add_text("Slot:")
                    dpg.add_input_int(tag="slot_input", default_value=0, width=80)

                dpg.add_spacer(height=8)
                with dpg.group(horizontal=True):
                    dpg.add_button(label="连接 PLC", callback=on_connect, width=90)
                    dpg.add_button(label="断开连接", callback=on_disconnect, width=90)

                dpg.add_spacer(height=16)
                dpg.add_text("◆ 刷新设置", color=ACCENT)
                dpg.add_separator()
                dpg.add_spacer(height=6)
                with dpg.group(horizontal=True):
                    dpg.add_text("刷新间隔(ms):")
                    dpg.add_input_int(tag="refresh_interval", default_value=500, width=100,
                                      min_value=100, max_value=60000, step=100)
                    dpg.add_text("值越小刷新越快，对 PLC 负载越大", color=TEXT_SECONDARY)

                dpg.add_spacer(height=16)
                dpg.add_text("◆ 监控点管理", color=ACCENT)
                dpg.add_separator()
                dpg.add_spacer(height=6)

                with dpg.group(horizontal=True):
                    dpg.add_text("地址:")
                    dpg.add_input_text(tag="new_addr_input", width=110, hint="如 I0.0, VW100")
                    dpg.add_spacer(width=8)
                    dpg.add_text("名称:")
                    dpg.add_input_text(tag="new_name_input", width=100, hint="描述")
                    dpg.add_spacer(width=8)
                    dpg.add_text("类型:")
                    dpg.add_combo(tag="new_dtype_input",
                                  items=["Bool", "Byte", "Word", "DWord", "Real"],
                                  default_value="Word", width=70)
                dpg.add_spacer(height=4)
                with dpg.group(horizontal=True):
                    dpg.add_text("单位:")
                    dpg.add_input_text(tag="new_unit_input", width=60, hint="°C")
                    dpg.add_spacer(width=8)
                    dpg.add_text("比例:")
                    dpg.add_input_float(tag="new_scale_input", default_value=1.0, width=70,
                                        step=0.1, format="%.3f")
                    dpg.add_spacer(width=8)
                    dpg.add_text("小数:")
                    dpg.add_input_int(tag="new_dec_input", default_value=1, width=50,
                                      min_value=0, max_value=6)
                    dpg.add_spacer(width=8)
                    dpg.add_button(label="+ 添加", callback=on_add_point)

                dpg.add_spacer(height=8)

                dpg.add_group(tag="points_table_container")

                dpg.add_spacer(height=16)
                with dpg.group(horizontal=True):
                    dpg.add_text("◆ 报警历史", color=ACCENT)
                    dpg.add_spacer(width=400)
                    dpg.add_button(label="清除历史", callback=on_clear_alarm_history, width=80)
                dpg.add_separator()
                dpg.add_spacer(height=6)

                with dpg.table(
                    tag="alarm_history_table", header_row=True, borders_innerH=True,
                    borders_outerH=True, borders_innerV=True, borders_outerV=True,
                ):
                    dpg.add_table_column(label="时间", width_fixed=True, init_width_or_weight=150)
                    dpg.add_table_column(label="监控点")
                    dpg.add_table_column(label="触发值")
                    dpg.add_table_column(label="描述")

        # Status bar
        dpg.add_separator()
        with dpg.group(horizontal=True):
            dpg.add_text("", tag="status_refresh", color=TEXT_SECONDARY)
            dpg.add_text("| CSV: 停止", tag="status_csv", color=TEXT_SECONDARY)
            dpg.add_text("| 报警: 0条", tag="status_alarm", color=TEXT_SECONDARY)

    _refresh_points_table()

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main_window", True)

    while dpg.is_dearpygui_running():
        refresh_monitor_table()
        dpg.render_dearpygui_frame()

    dpg.destroy_context()


if __name__ == "__main__":
    main()
