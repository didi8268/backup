# GUI 设计刷新 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Z-Monitor PLC 通讯软件 GUI 从基础深色主题升级为排版层次分明、空间节奏清晰、组件细节打磨的现代工业监控界面。

**Architecture:** 仅修改 `main.py` 单文件。从颜色常量 → 主题定义 → 布局重构 → 组件刷新，自上而下逐层替换。所有 widget tag 保持不变，数据流和回调逻辑不变。

**Tech Stack:** Python 3.13, dearpygui 2.3.1

---

### Task 0: 加载多级字号字体（排版层级基础）

**Files:**
- Modify: `main.py:832-840` (字体加载段)

- [ ] **Step 1: 替换字体加载逻辑，注册 28/18/16/13/11 五级字号**

将 `main.py:832-840` 替换：

```python
    # 加载中文字体 (多级字号)
    hero_font = None
    title_font = None
    body_font = None
    small_font = None
    tiny_font = None
    for f in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]:
        if os.path.isfile(f):
            with dpg.font_registry():
                hero_font = dpg.add_font(f, 28)     # Hero 数字
                title_font = dpg.add_font(f, 18)     # 卡片标题
                body_font = dpg.add_font(f, 16)      # 默认正文
                small_font = dpg.add_font(f, 13)     # 辅助文字/坐标轴
                tiny_font = dpg.add_font(f, 11)      # 微型标注
            dpg.bind_font(body_font)  # 全局默认 16px
            break

    # 如果找不到中文字体，回退默认字体（无多级字号）
    if body_font is None:
        with dpg.font_registry():
            body_font = dpg.add_font("", 16)
            small_font = dpg.add_font("", 12)
        dpg.bind_font(body_font)
```

注意：`small_font` 变量已在坐标轴绑定中使用。新增 `hero_font`、`title_font`、`tiny_font` 需要在模块顶部（约 line 33）声明为模块级变量：

```python
# 在 main.py:33 附近，small_font 声明后追加:
hero_font = None
title_font = None
tiny_font = None
```

然后在 `main()` 的字体加载段用 `global` 声明赋值。

- [ ] **Step 2: 运行验证字体加载**

```bash
py -3.13 main.py
```

确认无字体加载报错。

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: 加载五级字号字体 (28/18/16/13/11)"
```

---

### Task 1: 更新颜色常量

**Files:**
- Modify: `main.py:51-75`

- [ ] **Step 1: 替换颜色常量定义**

将 `main.py:50-75` 的颜色定义区替换为新的精炼调色板。

```python
# ── 配色（Z-Monitor 风格青色科技主题）──────────────────
# 背景层级 (4级，由浅到深)
BG_ELEVATED = (35, 42, 54)       # #232a36 悬浮层
BG_CARD = (26, 33, 48)           # #1a2130 卡片面板
BG_INPUT = (20, 27, 38)          # #141b26 输入框/表头
BG_DARK = (15, 23, 42)           # #0f172a 主背景
BG_SIDEBAR = (18, 26, 36)        # 顶栏背景

# 强调色 (Cyan 4 级梯度)
ACCENT_HOVER = (34, 211, 238)    # #22d3ee 悬停高亮
ACCENT = (6, 182, 212)           # #06b6d4 主强调
ACCENT_DIM = (8, 145, 178)       # #0891b2 暗强调/主按钮
ACCENT_SOFT = (14, 116, 144)     # #0e7490 弱强调

# 语义色
GREEN = (16, 185, 129)           # #10b981 成功
RED = (239, 68, 68)              # #ef4444 危险
YELLOW = (245, 158, 11)          # #f59e0b 警告

# 文字色
TEXT_PRIMARY = (226, 232, 240)   # #e2e8f0 正文
TEXT_SECONDARY = (148, 163, 184) # #94a3b8 辅助
TEXT_MUTED = (100, 116, 139)     # #64748b 弱化

# 边框/分隔
BORDER = (51, 65, 85)            # 边框
SUBTLE_BORDER = (38, 50, 64)     # 弱边框
SEPARATOR_COLOR = (71, 85, 105, 120)

# 图表
PLOT_GRID = (71, 85, 105, 70)
PLOT_BG = (17, 22, 30)

# 波形颜色轮转
WAVE_PALETTE = [
    (6, 182, 212),     # cyan
    (52, 211, 153),    # green-400
    (245, 158, 11),    # amber
    (239, 68, 68),     # red
    (167, 139, 250),   # purple-400
    (34, 211, 238),    # cyan-400
    (251, 146, 60),    # orange
    (148, 163, 184),   # slate-400
]
```

移除旧常量：`BG_CARD_ALT`, `BG_INPUT_ACTIVE`, `GREEN_GLOW`, `RED_GLOW`, `YELLOW_GLOW`, `BORDER_ACCENT`

- [ ] **Step 2: 全局替换旧常量引用**

将文件中所有 `BG_CARD_ALT` → `BG_ELEVATED`，`BG_INPUT_ACTIVE` → `ACCENT_SOFT`，`GREEN_GLOW` → `GREEN`，`RED_GLOW` → `RED`，`YELLOW_GLOW` → `YELLOW`。

```bash
# BG_CARD_ALT 用于表格交替行色和 TabUnfocusedActive
Edit: main.py — 替换所有 BG_CARD_ALT → BG_ELEVATED
Edit: main.py — 替换所有 BG_INPUT_ACTIVE → ACCENT_SOFT
Edit: main.py — 替换所有 GREEN_GLOW → GREEN  
Edit: main.py — 替换所有 RED_GLOW → RED
Edit: main.py — 替换所有 YELLOW_GLOW → YELLOW
```

- [ ] **Step 3: 运行程序验证颜色加载**

```bash
py -3.13 main.py
```

确认程序启动无报错，界面颜色正常加载。关闭窗口后继续。

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "refactor: 更新GUI颜色常量，精炼为4级背景+4级强调色+语义色"
```

---

### Task 2: 更新全局主题样式

**Files:**
- Modify: `main.py:860-921`

- [ ] **Step 1: 替换全局深色主题定义**

将 `main.py:860-921` 的全局主题定义替换（保留 `dpg.bind_theme(theme_id)`）：

```python
    # ── 全局深色主题 ──
    with dpg.theme() as theme_id:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, BG_DARK)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, BG_DARK)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, BG_INPUT)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, ACCENT_SOFT)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, BG_CARD)
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT_PRIMARY)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, TEXT_SECONDARY)
            dpg.add_theme_color(dpg.mvThemeCol_Button, ACCENT_SOFT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, ACCENT_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_Header, BG_INPUT)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, ACCENT_SOFT)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, ACCENT_DIM)
            dpg.add_theme_color(dpg.mvThemeCol_Separator, SEPARATOR_COLOR)
            dpg.add_theme_color(dpg.mvThemeCol_TableBorderStrong, BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_TableBorderLight, SUBTLE_BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_TableHeaderBg, BG_CARD)
            dpg.add_theme_color(dpg.mvThemeCol_TableRowBg, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_TableRowBgAlt, BG_ELEVATED)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, BG_DARK)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, ACCENT_SOFT)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, ACCENT_DIM)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, BG_SIDEBAR)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, BG_CARD)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, BG_ELEVATED)
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_Tab, BG_INPUT)
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, ACCENT_SOFT)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, BG_CARD)
            dpg.add_theme_color(dpg.mvThemeCol_TabUnfocused, BG_INPUT)
            dpg.add_theme_color(dpg.mvThemeCol_TabUnfocusedActive, BG_CARD)
            dpg.add_theme_color(dpg.mvThemeCol_DockingPreview, ACCENT_DIM)
            dpg.add_theme_color(dpg.mvThemeCol_Border, BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_PlotLines, ACCENT)
            dpg.add_theme_color(dpg.mvPlotCol_PlotBg, PLOT_BG)
            dpg.add_theme_color(dpg.mvPlotCol_FrameBg, BG_CARD)
            dpg.add_theme_color(dpg.mvPlotCol_AxisGrid, PLOT_GRID)
            dpg.add_theme_color(dpg.mvPlotCol_AxisText, TEXT_SECONDARY)
            dpg.add_theme_color(dpg.mvPlotCol_AxisTick, TEXT_MUTED)
            dpg.add_theme_color(dpg.mvPlotCol_LegendBg, BG_CARD)
            dpg.add_theme_color(dpg.mvPlotCol_LegendBorder, BORDER)
            dpg.add_theme_color(dpg.mvPlotCol_PlotBorder, SUBTLE_BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_NavHighlight, ACCENT_DIM)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_PopupRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_SelectableTextAlign, 0.5, 0.5)
            dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 8, 5)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 12, 10)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing, 6, 5)
    dpg.bind_theme(theme_id)
```

关键变化：
- `ChildRounding` 6→8, `FrameRounding` 4→6, `TabRounding` 4→6, `ScrollbarRounding` 4→6
- `WindowPadding` (10,8)→(12,10)
- `TabActive` 颜色: `ACCENT_DIM`→`BG_CARD`（去色块强调，用文字+底划线区分）
- `TableHeaderBg`: `BG_INPUT`→`BG_CARD`（表头与卡片同色）
- `PopupBg`: `BG_CARD`→`BG_ELEVATED`
- `FrameBgActive`: `BG_INPUT_ACTIVE`→`BG_CARD`

- [ ] **Step 2: 运行程序验证主题**

```bash
py -3.13 main.py
```

检查全局颜色、圆角、间距是否正确应用。关闭后继续。

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "refactor: 更新全局主题样式，优化圆角和间距"
```

---

### Task 3: 更新预创建主题

**Files:**
- Modify: `main.py:923-1030`

- [ ] **Step 1: 替换卡片+按钮+柱状图+复选框主题**

将 `main.py:923-1030` 的所有预创建主题替换：

```python
    # ── 卡片容器主题 ──
    with dpg.theme(tag="card_theme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, BG_CARD)
            dpg.add_theme_color(dpg.mvThemeCol_Border, SUBTLE_BORDER)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)

    # ── 按钮风格 ──
    with dpg.theme(tag="btn_primary_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, ACCENT_DIM)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, ACCENT_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 4)

    with dpg.theme(tag="btn_ghost_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, BG_INPUT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, ACCENT_SOFT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, ACCENT_DIM)
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT_PRIMARY)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 4)

    with dpg.theme(tag="btn_outline_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, ACCENT_SOFT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, ACCENT_DIM)
            dpg.add_theme_color(dpg.mvThemeCol_Text, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_Border, ACCENT_DIM)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 4)

    with dpg.theme(tag="btn_danger_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (127, 29, 29))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (185, 28, 28))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, RED)
            dpg.add_theme_color(dpg.mvThemeCol_Text, (252, 165, 165, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 4)

    # ── 柱状图主题 ──
    with dpg.theme(tag="bar_theme"):
        with dpg.theme_component(dpg.mvBarSeries):
            dpg.add_theme_color(dpg.mvPlotCol_Fill, ACCENT_DIM)
    with dpg.theme(tag="bar_max_theme"):
        with dpg.theme_component(dpg.mvScatterSeries):
            dpg.add_theme_color(dpg.mvPlotCol_Line, RED)
            dpg.add_theme_style(dpg.mvPlotStyleVar_Marker, dpg.mvPlotMarker_Diamond)
            dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 8)

    # ── 波形复选框颜色主题 ──
    with dpg.theme(tag="wave_cb_muted"):
        with dpg.theme_component(dpg.mvCheckbox):
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT_MUTED)
    for ci, cc in enumerate(WAVE_PALETTE):
        with dpg.theme(tag=f"wave_cb_c{ci}"):
            with dpg.theme_component(dpg.mvCheckbox):
                dpg.add_theme_color(dpg.mvThemeCol_Text, cc)

    # ── Bool LED 指示灯主题 ──
    with dpg.theme(tag="bool_on_theme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (5, 95, 72))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (5, 150, 105))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, GREEN)
            dpg.add_theme_color(dpg.mvThemeCol_Text, (209, 250, 229, 255))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 12)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 6, 3)

    with dpg.theme(tag="bool_off_theme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Button, BG_INPUT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, ACCENT_SOFT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, BG_INPUT)
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT_SECONDARY)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 12)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 6, 3)

    # ── 输入框风格 ──
    with dpg.theme(tag="input_theme"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, BG_INPUT)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, ACCENT_SOFT)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, BG_CARD)
            dpg.add_theme_color(dpg.mvThemeCol_Border, BORDER)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 5)

    # ── 强调色分隔线主题 ──
    with dpg.theme(tag="separator_accent"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Separator, ACCENT)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 2)

    # ── 文字主题 ──
    with dpg.theme(tag="section_header"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Text, ACCENT)
    with dpg.theme(tag="text_secondary"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT_SECONDARY)
    with dpg.theme(tag="text_muted"):
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT_MUTED)
```

关键变化：
- 所有按钮 `FramePadding` 从 `(11,6)` → `(8,4)` 更紧凑
- 新增 `btn_outline_theme`：透明背景+ACCENT文字+ACCENT_DIM边框
- `bool_on_theme`/`bool_off_theme`：`FrameRounding` 5→12 (圆角胶囊感)
- 新增 `separator_accent` 主题：青色2px分隔线
- `btn_danger_theme` 文字色: 白色 → `(252,165,165)` 淡红

- [ ] **Step 2: 运行验证**

```bash
py -3.13 main.py
```

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "refactor: 更新预创建主题，新增btn_outline和separator_accent"
```

---

### Task 4: 重构实时监控页布局（Hero + 图表并排）

**Files:**
- Modify: `main.py:1065-1149` (Tab 1 实时监控布局)
- Modify: `main.py:700-733` (`_refresh_bar_chart` 忽略，内部逻辑不变)

- [ ] **Step 1: 添加 Hero 指标刷新函数**

在 `_refresh_bar_chart` 函数之前（`main.py:700` 之前）插入新函数：

```python
def _refresh_hero_metrics():
    """刷新 Hero 指标卡片行"""
    if not dpg.does_item_exist("hero_row"):
        return
    points = monitor.get_points()
    non_bool = [(i, pt) for i, pt in enumerate(points) if pt.data_type != "Bool"]
    
    # 清除旧卡片
    dpg.delete_item("hero_row", children_only=True)
    
    for idx, pt in non_bool:
        tag = f"hero_card_{idx}"
        with dpg.child_window(tag=tag, parent="hero_row", width=140, height=72,
                              border=True):
            dpg.bind_item_theme(tag, "card_theme")
            # 数值
            if pt.current_value is not None:
                try:
                    v = float(pt.current_value) * pt.scale
                    val_str = f"{v:.{pt.decimal_places}f}"
                except (TypeError, ValueError):
                    val_str = str(pt.current_value)
            else:
                val_str = "—"
            color = WAVE_PALETTE[idx % len(WAVE_PALETTE)]
            val_text = dpg.add_text(val_str, color=color)
            if hero_font:
                dpg.bind_item_font(val_text, hero_font)
            # 名称 + 单位
            label = pt.name
            if pt.unit:
                label += f" ({pt.unit})"
            label_text = dpg.add_text(label, color=TEXT_SECONDARY)
            if tiny_font:
                dpg.bind_item_font(label_text, tiny_font)
        dpg.add_spacer(width=8, parent="hero_row")
    
    if not non_bool:
        dpg.add_text("(无监控数据)", color=TEXT_MUTED, parent="hero_row")
```

- [ ] **Step 2: 替换实时监控 Tab 布局**

将 `main.py:1066-1149`（从 `dpg.add_spacer(height=4)` 到 `dpg.bind_item_theme("data_card", "card_theme")`）替换为：

```python
                with dpg.tab(label="  实时监控  "):
                    dpg.add_spacer(height=4)
                    
                    # Hero 指标行
                    dpg.add_group(tag="hero_row", horizontal=True)
                    dpg.add_spacer(height=6)
                    
                    # 图表行：柱状图 + 波形图并排
                    with dpg.group(horizontal=True):
                        # 柱状图卡片 (左侧 ~35%)
                        with dpg.child_window(tag="bar_card", width=380, height=300, border=True):
                            with dpg.group(horizontal=True):
                                dpg.add_text("数值柱状图", color=ACCENT)
                                dpg.bind_item_theme(dpg.last_item(), "section_header")
                                dpg.add_spacer(width=12)
                                dpg.add_text("当前值", color=GREEN)
                                dpg.add_spacer(width=8)
                                dpg.add_text("◆ 历史最大", color=RED)
                            dpg.add_separator()
                            dpg.bind_item_theme(dpg.last_item(), "separator_accent")
                            dpg.add_spacer(height=4)
                            with dpg.plot(
                                tag="bar_plot", height=235, width=-1,
                                anti_aliased=True, no_menus=True,
                            ):
                                dpg.add_plot_axis(dpg.mvXAxis, label="", tag="bar_x_axis")
                                dpg.add_plot_axis(dpg.mvYAxis, label="", tag="bar_y_axis")
                                dpg.add_bar_series([], [], parent="bar_y_axis", tag="bar_series")
                                dpg.add_scatter_series([], [], parent="bar_y_axis", tag="bar_max_scatter")
                                dpg.bind_item_theme("bar_series", "bar_theme")
                                dpg.bind_item_theme("bar_max_scatter", "bar_max_theme")
                                if small_font:
                                    dpg.bind_item_font("bar_x_axis", small_font)
                                    dpg.bind_item_font("bar_y_axis", small_font)
                        dpg.bind_item_theme("bar_card", "card_theme")
                        
                        dpg.add_spacer(width=8)
                        
                        # 波形图卡片 (右侧 ~65%)
                        with dpg.child_window(tag="wave_card", height=300, border=True):
                            with dpg.group(horizontal=True):
                                dpg.add_text("实时波形", color=ACCENT)
                                dpg.bind_item_theme(dpg.last_item(), "section_header")
                                dpg.add_spacer(width=16)
                                dpg.add_text("窗口:", color=TEXT_SECONDARY)
                                dpg.add_input_int(tag="wave_time_window", default_value=60,
                                                  width=70, min_value=5, max_value=3600, step=5)
                                dpg.add_text("秒", color=TEXT_MUTED)
                            dpg.add_separator()
                            dpg.bind_item_theme(dpg.last_item(), "separator_accent")
                            dpg.add_spacer(height=4)
                            dpg.add_group(tag="wave_channel_container", horizontal=True)
                            dpg.add_spacer(height=2)
                            with dpg.plot(
                                tag="wave_plot", label="实时波形", height=200, width=-1,
                                anti_aliased=True, no_menus=True,
                            ):
                                dpg.add_plot_legend()
                                dpg.add_plot_axis(dpg.mvXAxis, label="时间 (秒)", tag="wave_x_axis")
                                dpg.add_plot_axis(dpg.mvYAxis, label="Y左", tag="wave_y_axis_0")
                                dpg.add_plot_axis(dpg.mvYAxis2, label="Y右", tag="wave_y_axis_1", opposite=True)
                                dpg.add_plot_axis(dpg.mvYAxis3, label="Y左2", tag="wave_y_axis_2")
                                dpg.set_axis_limits("wave_x_axis", 0, 60)
                                dpg.set_axis_limits_auto("wave_y_axis_0")
                                dpg.set_axis_limits_auto("wave_y_axis_1")
                                dpg.set_axis_limits_auto("wave_y_axis_2")
                                dpg.hide_item("wave_y_axis_2")
                                if small_font:
                                    for ax in ("wave_x_axis", "wave_y_axis_0", "wave_y_axis_1", "wave_y_axis_2"):
                                        dpg.bind_item_font(ax, small_font)
                        dpg.bind_item_theme("wave_card", "card_theme")
                    
                    dpg.add_spacer(height=6)
                    
                    # 数据表格卡片 (全宽)
                    with dpg.child_window(tag="data_card", height=340, border=True):
                        dpg.add_text("监控数据", color=ACCENT)
                        dpg.bind_item_theme(dpg.last_item(), "section_header")
                        dpg.add_separator()
                        dpg.bind_item_theme(dpg.last_item(), "separator_accent")
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
                            dpg.add_table_column(label="当前值", width_fixed=True, init_width_or_weight=90)
                            dpg.add_table_column(label="写入值")
                            dpg.add_table_column(label="操作", width_fixed=True, init_width_or_weight=80)
                    dpg.bind_item_theme("data_card", "card_theme")
```

关键变化：
- 顶部新增 `hero_row` 横向 group，显示各点当前值大数字
- 柱状图和波形图从垂直堆叠改为水平并排
- 柱状图宽度 380px、高度 300px（原 200px）
- 波形图高度从 480→300，内部图表从 370→200
- 分隔线绑定 `separator_accent` 主题（青色细线）
- 卡片内 `add_spacer(height=2)` → `add_spacer(height=4)`
- 每个卡片标题在 `bind_item_theme("section_header")` 后追加 `dpg.bind_item_font(dpg.last_item(), title_font)` 绑定 18px 标题字

- [ ] **Step 3: 更新主刷新循环，加入 Hero 刷新**

在 `refresh_monitor_table()` 中加入 Hero 刷新调用。修改 `main.py:169-170`：

```python
    refresh_waveform_plot()
    _refresh_bar_chart()
    _refresh_hero_metrics()          # ← 新增
    _update_bool_indicators()
```

- [ ] **Step 4: 运行验证布局**

```bash
py -3.13 main.py
```

检查实时监控页：Hero 行显示正确、柱状图和波形并排、表格全宽。

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: 重构实时监控页 — Hero指标+图表并排+全宽表格"
```

---

### Task 5: 更新 Bool 指示灯为 LED 风格

**Files:**
- Modify: `main.py:665-697` (`_refresh_bool_indicators` 和 `_update_bool_indicators`)

- [ ] **Step 1: 替换 Bool 指示器函数**

```python
def _refresh_bool_indicators():
    """在标题栏重建 Bool 型监控点的 LED 指示器"""
    if not dpg.does_item_exist("bool_indicators_group"):
        return

    dpg.delete_item("bool_indicators_group", children_only=True)

    points = monitor.get_points()
    bool_points = [(i, pt) for i, pt in enumerate(points) if pt.data_type == "Bool"]
    for i, pt in bool_points:
        val = pt.current_value
        with dpg.group(horizontal=True, parent="bool_indicators_group"):
            # LED 圆点 + 文字标签
            dot_color = GREEN if val else TEXT_MUTED
            dpg.add_text("●", color=dot_color)
            label = f"{pt.name}"
            label_color = TEXT_PRIMARY if val else TEXT_SECONDARY
            dpg.add_text(label, color=label_color)
            dpg.add_spacer(width=10)


def _update_bool_indicators():
    """更新 Bool 指示器显示（周期刷新，不重建 widget）"""
    points = monitor.get_points()
    bool_points = [(i, pt) for i, pt in enumerate(points) if pt.data_type == "Bool"]
    for bi, (i, pt) in enumerate(bool_points):
        # LED 圆点: 每组3个widget (dot, text, spacer)
        dot_tag = f"bool_dot_{i}"
        label_tag = f"bool_label_{i}"
        # 首次更新创建 tag 关联
        if not dpg.does_item_exist(dot_tag):
            # 通过遍历 bool_indicators_group children 获取对应 widget
            children = dpg.get_item_children("bool_indicators_group", 1)
            widget_idx = bi * 3  # 每组3个: dot, label, spacer
            if widget_idx < len(children):
                # 给已有 widget 打标（仅首次）
                dpg.configure_item(children[widget_idx], tag=dot_tag)
                dpg.configure_item(children[widget_idx + 1], tag=label_tag)
        
        if dpg.does_item_exist(dot_tag) and dpg.does_item_exist(label_tag):
            val = pt.current_value
            dpg.configure_item(dot_tag, color=GREEN if val else TEXT_MUTED)
            dpg.configure_item(label_tag, color=TEXT_PRIMARY if val else TEXT_SECONDARY)
```

注意：Bool 指示器从 `add_button` 改为 `add_text("●")` + `add_text(name)`，不再可点击切换。如需保留点击切换行为，改为用 `add_button` 包裹 LED 点或增加独立的切换按钮。

- [ ] **Step 2: 移除旧按钮回调**（如 Bool 指示器不再可点击）

如果选择保留点击切换行为，改为每个 Bool 组添加一个小切换按钮：

```python
# 在 _refresh_bool_indicators 的每组中增加:
dpg.add_button(label="切换", width=40, height=18,
               callback=lambda s, a, u: _on_bool_indicator_click(u),
               user_data=i)
dpg.bind_item_theme(dpg.last_item(), "btn_outline_theme")
```

- [ ] **Step 3: 运行验证**

```bash
py -3.13 main.py
```

检查 header bar 中 Bool 指示器显示为 LED 点+文字。

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: Bool指示灯改为LED圆点+文字标签风格"
```

---

### Task 6: 更新控制设置和系统设置页间距

**Files:**
- Modify: `main.py:1150-1368` (Tab 2 和 Tab 3 布局)

- [ ] **Step 1: 统一卡片间距和分隔线样式**

将所有卡片中的 `dpg.add_separator()` 后追加主题绑定。将各卡片间距从 4px 调整为 6px。

具体编辑：

1. `main.py:1153` — `dpg.add_spacer(height=4)` → `dpg.add_spacer(height=6)`
2. `main.py:1158` — 在 `dpg.add_separator()` 后加 `dpg.bind_item_theme(dpg.last_item(), "separator_accent")`
3. `main.py:1208` — `dpg.add_spacer(height=4)` → `dpg.add_spacer(height=6)`
4. `main.py:1213` — 在 `dpg.add_separator()` 后加 `dpg.bind_item_theme(dpg.last_item(), "separator_accent")`
5. `main.py:1252` → `main.py:1254` — `dpg.add_spacer(height=4)` → `dpg.add_spacer(height=6)`
6. `main.py:1259` — 在 `dpg.add_separator()` 后加 `dpg.bind_item_theme(dpg.last_item(), "separator_accent")`
7. `main.py:1281` — `dpg.add_spacer(height=8)` → `dpg.add_spacer(height=6)`（卡片间距）
8. `main.py:1298` — 在 `dpg.add_separator()` 后加 `dpg.bind_item_theme(dpg.last_item(), "separator_accent")`
9. `main.py:1337` — `dpg.add_spacer(height=8)` → `dpg.add_spacer(height=6)`
10. `main.py:1347` — 在 `dpg.add_separator()` 后加 `dpg.bind_item_theme(dpg.last_item(), "separator_accent")`

- [ ] **Step 2: 更新状态栏样式**

将 `main.py:1359-1368` 状态栏替换：

```python
        # ── 底部状态栏 ──
        with dpg.child_window(tag="status_bar", height=30, border=False):
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=12)
                dpg.add_text("", tag="status_refresh", color=TEXT_SECONDARY)
                dpg.add_text("|", color=TEXT_MUTED)
                dpg.add_text("CSV: 停止", tag="status_csv", color=TEXT_SECONDARY)
                dpg.add_text("|", color=TEXT_MUTED)
                dpg.add_text("报警: 0条", tag="status_alarm", color=TEXT_SECONDARY)
        dpg.bind_item_theme("status_bar", "card_theme")
```

变化：height 32→30, 首行 spacer 8→12

- [ ] **Step 3: 运行验证**

```bash
py -3.13 main.py
```

检查控制设置和系统设置页的卡片间距、分隔线。

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "refactor: 统一控制设置/系统设置页卡片间距和分隔线样式"
```

---

### Task 7: 更新表格数据行样式

**Files:**
- Modify: `main.py:118-158` (数据表格行构建)

- [ ] **Step 1: 更新监控数据表格行交替色逻辑**

将 `main.py:157-158` 的交替行处理替换：

```python
            # 当前值用通道颜色突出显示
            ci = i % len(WAVE_PALETTE)
            dpg.add_text(val_str, color=WAVE_PALETTE[ci] if pt.current_value is not None else TEXT_SECONDARY)
```

同时移除行 138 旧的 `color=GREEN` 逻辑：

```python
            # 旧: dpg.add_text(val_str, color=GREEN if pt.current_value is not None else TEXT_SECONDARY)
            # 新:
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
            ci = i % len(WAVE_PALETTE)
            dpg.add_text(val_str, color=WAVE_PALETTE[ci] if pt.current_value is not None else TEXT_SECONDARY)
```

- [ ] **Step 2: 运行验证**

```bash
py -3.13 main.py
```

检查表格当前值列颜色是否用通道色显示。

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "style: 数据表格当前值列使用通道颜色显示"
```

---

### Task 8: 全量验证和微调

**Files:**
- Modify: `main.py` (可能的微调)

- [ ] **Step 1: 完整功能测试**

```bash
py -3.13 main.py
```

逐项检查：
- [ ] 三页 tab 切换正常
- [ ] Hero 指标卡片正确显示当前值
- [ ] 柱状图和波形图并排显示
- [ ] 波形复选框可切换
- [ ] 数据表格显示、写入、删除功能正常
- [ ] Bool LED 指示灯正确显示 ON/OFF 状态
- [ ] 连接/断开 PLC 功能正常
- [ ] 报警规则添加/触发正常
- [ ] 导入导出监控点正常
- [ ] CSV 记录开关正常
- [ ] 状态栏信息正确

- [ ] **Step 2: 修复发现的问题**

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "fix: GUI设计刷新后的微调和问题修复"
```
