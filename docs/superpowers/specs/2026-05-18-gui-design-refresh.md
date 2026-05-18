# GUI 设计刷新规格说明

## 概述

在现有 Z-Monitor 工业深色主题基础上，深化设计语言。以**排版与空间优化**为核心，配合色彩体系精炼和组件细节打磨，打造有辨识度的现代工业监控界面。

**设计原则**：深化而非重写。保留 slate-950 + cyan-500 基调，提升层级感和呼吸感。

## 布局重构：大数字优先（Hero Metrics）

实时监控页从垂直三卡片堆叠改为 Hero 数字优先布局：

```
┌─ hero_row ───────────────────────────────────────────┐
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  │
│  │ 23.5°│  │ 0.82 │  │ 42.1 │  │ ...  │  │ ...  │  │
│  │ 温度 │  │ 压力 │  │ 流量 │  │      │  │      │  │
│  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘  │
├─ charts_row ─────────────────────────────────────────┤
│  ┌─────────────────┐  ┌────────────────────────────┐ │
│  │   柱状图        │  │   波形图                    │ │
│  └─────────────────┘  └────────────────────────────┘ │
├─ table_row ──────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────┐ │
│  │   数据表格（全宽）                               │ │
│  └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

- Hero 数字卡片：每个监控点一个，显示当前值（28px bold）+ 名称（13px）+ 单位
- 图表行：柱状图和波形图并排（各占约 50%）
- 表格行：全宽数据表格
- Bool 指示器移至 header_bar 保持现有位置

## 排版层级

### 字号体系（5 级）

| 层级 | 字号 | 字重 | 颜色 | 用途 |
|------|------|------|------|------|
| Hero | 28px | bold | 各点对应通道色 | 顶部指标卡片数值 |
| 标题 | 18px | bold | ACCENT | 卡片标题 |
| 正文 | 15px | normal | TEXT_PRIMARY | 表格数据、列表项 |
| 辅助 | 13px | normal | TEXT_SECONDARY | 状态栏、标签、描述 |
| 微标 | 11px | normal | TEXT_MUTED | 单位、坐标轴刻度 |

### 间距系统（8px 基准网格）

| 用途 | 值 | 倍数 |
|------|-----|------|
| 行内元素间距 | 8px | 1x |
| 卡片间距 | 12px | 1.5x |
| 区块间距（标题-内容） | 12px | 1.5x |
| 卡片内边距 | 16px | 2x |
| 表格单元格 padding | 8px 12px | - |
| 窗口 padding | 12px 10px | - |

## 色彩体系

### 背景层级（4 级，由浅到深）

| 名称 | 色值 | 用途 |
|------|------|------|
| BG_ELEVATED | #232a36 | 悬浮层（popup、tooltip） |
| BG_CARD | #1a2130 | 卡片面板（原 #181e28） |
| BG_INPUT | #141b26 | 输入框、表格表头 |
| BG_DARK | #0f172a | 主背景 |

### 强调色（Cyan 4 级梯度）

| 名称 | 色值 | 用途 |
|------|------|------|
| ACCENT_HOVER | #22d3ee | 悬停高亮 |
| ACCENT | #06b6d4 | 主强调、标题、选中 |
| ACCENT_DIM | #0891b2 | 暗强调、主按钮背景 |
| ACCENT_SOFT | #0e7490 | 弱强调、控件背景 |

### 语义色

| 语义 | 主色 | 用途 |
|------|------|------|
| 信息 | #06b6d4 (Cyan) | 标题、链接、选中态 |
| 成功 | #10b981 (Emerald) | 连接正常、Bool ON、CSV 记录中 |
| 警告 | #f59e0b (Amber) | 报警、阈值接近 |
| 危险 | #ef4444 (Red) | 断开、故障、超限 |

### 文字色

| 名称 | 色值 | 用途 |
|------|------|------|
| TEXT_PRIMARY | #e2e8f0 | 正文 |
| TEXT_SECONDARY | #94a3b8 | 辅助文字 |
| TEXT_MUTED | #64748b | 弱化文字、占位符 |

## 组件设计

### 卡片（Card）

- 背景 BG_CARD，圆角 8px
- 顶部 2px 青色细线 `border-top: 2px solid ACCENT`
- 去掉内部分隔线（`add_separator`），用 12px 间距替代
- padding 从 10px → 16px
- 边框 1px SUBTLE_BORDER

### 按钮（Button）

| 类型 | 背景 | 文字色 | 其他 |
|------|------|--------|------|
| 主要 | ACCENT_DIM | #ffffff | bold, padding 8×20 |
| 次要 | transparent | ACCENT | 1px ACCENT_DIM 边框 |
| 幽灵 | BG_INPUT | TEXT_PRIMARY | 无边框 |
| 危险 | #7f1d1d | #fca5a5 | bold |

- 统一 14px bold，圆角 6px
- 保留 btn_ghost_theme，新增 btn_outline_theme（描边次要按钮）

### 数据表格（Table）

- 表头：12px bold，ACCENT 颜色，背景 BG_CARD（不用 BG_INPUT 色块）
- 数据行：15px TEXT_PRIMARY，行高增加
- 交替行色改为底部细线分隔：`1px solid rgba(30,41,59,0.6)`
- 数值列用对应通道颜色或 ACCENT 突出
- 单元格 padding: 8px 12px

### Bool 指示灯（Bool Indicator）

- 从按钮色块改为 LED 圆点 + 文字标签
- ON 态：10px 绿圆点 (#10b981) + 发光效果（用亮色边框模拟）+ 白色文字
- OFF 态：10px 暗灰圆点 (#334155) + TEXT_SECONDARY 文字
- 保持可点击切换行为

### 输入框（Input）

- 背景 BG_INPUT，边框 BORDER
- focus 态边框变 ACCENT（利用 dearpygui FrameBgActive）
- 14px 文字，圆角 6px，padding 8×12

### Tab 导航

- 激活态：白色文字 + 底部 2px ACCENT 底划线
- 非激活态：TEXT_MUTED 文字，无底划线
- 字号 14px，间距 20px

### 状态栏（Status Bar）

- 背景 BG_CARD，顶部分隔线
- 13px 文字，状态值用语义色（连接=绿、报警=琥珀、CSV=绿）

## 字体

- 主字体：微软雅黑（C:/Windows/Fonts/msyh.ttc），16px 基准
- 辅助字体：12px（用于坐标轴、微型标注）
- 回退：SimHei（C:/Windows/Fonts/simhei.ttf）

## 实施注意事项（dearpygui 限制下的实现策略）

### Hero 指标卡片
- 仅非 Bool 类型监控点生成 Hero 卡片
- 使用 `child_window` + `add_text` 组合，横向排列在 `hero_row` 容器中
- 如点数过多（>8），hero_row 使用 `child_window` + 水平滚动条

### 卡片顶部强调线
- dearpygui child_window 不支持单边 border
- 方案：卡片标题下方用 `add_separator` 并绑定 ACCENT 颜色主题（预创建 `separator_accent` 主题）

### Bool LED 指示灯
- 使用 Unicode 字符 "●" (U+25CF) 作为指示点
- ON 态：`add_text("●", color=GREEN)` + 预创建 `led_on_theme`（亮色文字+发光效果模拟）
- OFF 态：`add_text("●", color=TEXT_MUTED)`
- 文字标签紧跟其后，可点击切换
- 参考现有 `conn_indicator` 用法（line 1056）

### Tab 底划线
- dearpygui tab_bar 样式受限
- 通过全局主题中的 `mvThemeCol_TabActive` 等颜色调整实现
- 如果无法实现底划线效果，用激活态背景色差异 + 文字颜色区分

### 表格表头
- dearpygui table header 行在 `children_only` 刷新模式下保留
- 表头样式通过全局主题的 `mvThemeCol_TableHeaderBg` 控制
- 设为 BG_CARD（与卡片背景统一）

## 实施范围

### 修改文件
- `main.py`：颜色常量、主题定义、布局重构、表格刷新逻辑

### 不变文件
- `plc_client.py`：通讯层
- `plc_monitor.py`：数据模型
- `waveform_output.py`：波形生成
- `data_logger.py`：CSV 记录
- `alarm_manager.py`：报警逻辑

### Backward Compatibility
- 所有 widget tag 保持不变
- 波形通道颜色索引预创建逻辑不变
- 表格 children_only 刷新模式不变
- wave_buffers / wave_visible / bar_history_max 数据流不变
