---
name: lr-figure-maker
description: 文献综述图表生成器 v2。当框架搭建完成后（或写作完成后），需要根据 framework.md 中的图表规划，自动生成符合目标期刊规范的示意图、数据整合图、汇总对比表等。v2 新增：色盲友好配色、多面板组图、EPS/PDF 矢量输出、统计图表规范、感知均匀色图、期刊专属尺寸模板、可访问性要求。支持 SCI 期刊的全部出版级要求（≥1200 DPI 线条图、CMYK、嵌入式字体、alt text）和中文核心期刊的通用要求。产出 SVG/PNG/EPS/PDF 图和 Markdown 表格。当用户说"画综述图""生成图表""做Figure""做示意图"时触发。
agent_created: true
---

# 文献综述 — Step 8: 图表生成器 v2 (SCI-Ready)

## 概述

根据 framework.md 的图表规划，生成**出版级**学术图表。v2 以 SCI 顶级期刊（Nature / Cell / Science / Lancet 系列）的图表规范为基准，覆盖从配色、排版、多面板组图到矢量输出的完整生产链。

**支持的图表类型：**
- 机制/流程示意图（手写 SVG，出版级排版）
- 文献数据整合图（Matplotlib，含统计标注）
- 多面板组图（A-F 统一风格，出版级分辨率）
- 对比汇总表（Markdown 表格，可嵌入 Word/LaTeX）
- PRISMA 2020 流程图（系统综述专用）
- Graphical Abstract（图形摘要，1200×600 px）
- Timeline（领域发展时间线）
- 热图/相关矩阵（感知均匀色图）

## 前置条件

- 已完成 `lr-framework`，存在 `framework.md`（含图表规划）
- 推荐：已完成写作，了解所有需要图示化的内容
- `project_brief.md` 中有目标期刊/语言信息

## 产出文件

```
figures/
├── figure_01.svg          # 矢量原图
├── figure_01.png          # 预览用 PNG（300 DPI）
├── figure_01.eps          # 出版用 EPS（SCI 项目）
├── figure_01.pdf          # 出版用 PDF（SCI 项目，嵌入式字体）
├── figure_02_*.{svg,png,eps,pdf}
├── ...
├── graphical_abstract.svg # 图形摘要（SCI 项目）
├── graphical_abstract.png # 图形摘要 PNG（1200 DPI）
└── figure_captions.md     # 全部图注汇总

manuscript/
└── tables.md              # 汇总表（Markdown 格式）
```

---

## 第一部分：SCI 出版级规范速查

### 1.1 顶级期刊尺寸模板

| 期刊系列 | 单栏宽 | 1.5 栏宽 | 双栏宽 | 最大高度 | 首选格式 | 色彩模式 |
|----------|--------|----------|--------|----------|----------|----------|
| Nature 系列 | 89 mm | 120 mm | 183 mm | 247 mm | EPS/PDF | CMYK |
| Cell 系列 | 85 mm | 114 mm | 174 mm | 240 mm | EPS/PDF/TIFF | CMYK |
| Science 系列 | 56 mm | 121 mm | 178 mm | 200 mm | EPS/PDF | CMYK |
| Lancet 系列 | 83 mm | — | 170 mm | 220 mm | EPS/PDF/TIFF | CMYK |
| JAMA 系列 | 60 mm | 120 mm | 175 mm | 225 mm | EPS/PDF/TIFF | CMYK |
| 中文核心 | 80 mm | — | 160 mm | 220 mm | TIFF/PNG/JPG | RGB |

**使用规则：**
- 优先使用**单栏**（大部分综述示意图适合单栏排版）
- 只有数据密集的多面板对比图使用双栏
- 高度不得超过最大高度（否则出版社会要求拆分）

### 1.2 分辨率要求（按图类型）

| 图类型 | 最低 DPI | 推荐 DPI | 说明 |
|--------|----------|----------|------|
| 彩色照片/渲染图 | 300 | 600 | TIFF, LZW 压缩 |
| 灰度图 | 300 | 600 | TIFF |
| 线条图（纯矢量） | 600 | 1200 | 矢量格式无分辨率概念，但光栅化预览用此 DPI |
| 含文字的线条图 | 1200 | 1200 | 文字在缩放时仍需可读 |
| 组合图（矢量+数据） | 600 | 1200 | EPS/PDF 矢量优先 |

### 1.3 字体规范

| 规范项 | 要求 |
|--------|------|
| **字体族** | Arial / Helvetica（无衬线），Times New Roman（仅在图表中引用物种名时使用斜体） |
| **最小字号** | **8pt**（低于此值印刷时不可读） |
| **推荐字号** | 坐标轴标签 8-10pt，图内标注 10-12pt，面板标签(A,B,C) 14-16pt bold |
| **嵌入式字体** | EPS/PDF 必须嵌入全部字体（matplotlib: `pdf.fonttype=42, ps.fonttype=42`） |
| **基因/蛋白命名** | 人类基因大写斜体（TP53），小鼠首字母大写斜体（Tp53），蛋白正体大写（TP53） |
| **数学符号** | 使用 TeX/LaTeX 渲染（matplotlib: `rcParams['text.usetex'] = False` 用内置 mathtext） |

---

## 第二部分：配色体系

### 2.1 色盲友好配色（SCI 强制/强烈推荐）

> Nature Methods 和 eLife 自 2022 年起要求所有投稿使用色盲友好配色。

**方案 A: Wong 2011（Nature Methods 推荐，7 色）**
```
#000000  #E69F00  #56B4E9  #009E73  #F0E442  #0072B2  #D55E00
 黑        橙      天蓝     蓝绿      黄       蓝       朱红
```

**方案 B: Okabe-Ito（8 色，最广兼容性）**
```
#000000  #E69F00  #56B4E9  #009E73  #F0E442  #0072B2  #D55E00  #CC79A7
 黑        橙      天蓝     蓝绿      黄       蓝       朱红      粉
```

**方案 C: IBM Design Library（低饱和度专业风，10 色）**
```
#648FFF  #785EF0  #DC267F  #FE6100  #FFB000  #009E73  #56B4E9  #E69F00  #F0E442  #0072B2
```

**方案 D: 灰度安全（适合黑白印刷，5 级灰度）**
```
#000000  #404040  #808080  #BFBFBF  #E6E6E6
 纯黑     深灰     中灰     浅灰     极浅灰
```

**选择建议：**
- 3-5 类比色 → 方案 A 或 C
- 6-8 类 → 方案 B
- 对黑白印刷友好 → 方案 D 叠加不同的填充纹理（// \\\\ :: ##）
- 叠加纹理方法：matplotlib `hatch` 参数 (`'/'`, `'\\'`, `'|'`, `'-'`, `'+'`, `'x'`, `'o'`, `'O'`, `'.'`, `'*'`)

### 2.2 感知均匀连续色图（热图/表达矩阵专用）

**禁止使用：** jet / rainbow / hsv colormap（已被 Nature Methods 2015 和 eLife 2020 社论明确警告，会导致伪影和色盲者完全无法辨识）

**必须使用 perceptual 色图（matplotlib 内置）：**

```python
# 顺序数据（0→max）
'viridis'   # 蓝绿→黄（最通用，推荐）
'plasma'    # 紫→黄
'inferno'   # 黑→红→黄
'magma'     # 黑→粉→黄
'mako'      # 深海绿→浅绿→黄（seaborn）

# 发散数据（-N→0→+N）
'coolwarm'  # 蓝→白→红（注意：中间白色在白色背景下消失，加黑色描边）
'RdBu_r'    # 红→白→蓝（更安全）
'BrBG'      # 棕→白→绿
'PRGn'      # 紫→白→绿（色盲安全）
'vlag'      # 蓝→白→红

# 循环数据
'twilight'  # 白→蓝→红→棕→白
```

### 2.3 配色验证工具

生成图表后，用以下工具验证色盲友好性：
- Coblis (https://www.color-blindness.com/coblis-color-blindness-simulator/) — 上传截图模拟 Deuteranopia/Protanopia/Tritanopia
- 灰度测试：`Image → Mode → Grayscale`（确保所有类别在灰度下可区分）

---

## 第三部分：多面板组图规范

### 3.1 面板标签

```python
# 标准面板标签格式
labels = ['A', 'B', 'C', 'D', 'E', 'F']  # 大写粗体, 14-16pt

# 放置位置：左上角，padding 适当
ax.text(-0.1, 1.05, 'A', transform=ax.transAxes,
        fontsize=14, fontweight='bold', va='bottom', ha='left')
```

**SCI 标准规则：**
- 只用大写字母（A B C ...），不用小写
- 标签置于面板**左上角**（Cell/Nature 偏好）或**左下角**（Science 偏好）→ 查阅目标期刊近期论文确定
- 面板之间间距 `wspace=0.25, hspace=0.3`（英寸）
- 如果某一面板是照片，使用黑色描边边框区分背景

### 3.2 matplotlib 多面板布局方案

**方案 1: `subplot_mosaic`（推荐，Python ≥3.7）**
```python
fig, axes = plt.subplot_mosaic([
    ['A', 'A', 'B'],
    ['A', 'A', 'C'],
    ['D', 'E', 'F'],
], figsize=(7, 7))
```

**方案 2: `GridSpec`（精确控制宽高比）**
```python
gs = fig.add_gridspec(3, 3, width_ratios=[1, 1, 1.2], height_ratios=[1, 0.8, 1])
ax_a = fig.add_subplot(gs[0, :2])
```

**方案 3: `plt.subplots`（规整网格）**
```python
fig, axes = plt.subplots(2, 3, figsize=(12, 8))
```

### 3.3 统一风格

整个多面板图中，所有子图共用：
- 同一配色方案（色盲友好）
- 同一字体和字号
- 同一线宽（`lw=1.5` 或 `lw=2.0`）
- 同一标记大小（`ms=6`）
- 如果多个面板共享坐标轴含义，使用 `sharex=True, sharey=True`

---

## 第四部分：统计图表规范

### 4.1 箱线图标准

```python
# SCI 标准箱线图
bp = ax.boxplot(data,
    patch_artist=True,       # 填充颜色
    widths=0.6,
    flierprops={'marker': 'o', 'markersize': 4, 'markerfacecolor': 'gray'},
    medianprops={'color': 'black', 'linewidth': 1.5},
    whiskerprops={'linewidth': 1},
    capprops={'linewidth': 1})
```

**关键规范：**
- 须线 (whiskers) = 1.5×IQR（标准）或 5-95 百分位（标注说明）
- 离群值单独绘制为小圆点
- 箱体使用 ≤ 30% 透明度的浅色填充
- **务必在 caption 中说明箱线图的定义**（Nature 强制要求）

### 4.2 小提琴图

```python
# 推荐用 seaborn 或手动
import seaborn as sns
sns.violinplot(data=df, inner='quartile', cut=0, bw=0.2)
```

- `inner='quartile'` 比默认的 box 更清晰
- 叠加 `stripplot` 显示个体数据点（N<100 时推荐，N<30 时强制）
- 颜色透明度 `alpha=0.7`

### 4.3 柱状图 + 误差线

```python
ax.bar(x, height, yerr=error, capsize=4, width=0.6,
       color='#648FFF', edgecolor='black', linewidth=0.5)
```

**必须满足（Nature/Cell 强制）：**
- 误差线标注 SEM 还是 SD → 必须写在 caption 中
- 柱状图**上方叠加所有个体数据点**（N<50 时强制，N≥50 可选）
- 统计显著性的标注行：
  ```python
  # *p<0.05, **p<0.01, ***p<0.001, ****p<0.0001, ns=不显著
  ```

### 4.4 统计显著性标注

```python
def add_significance(ax, x1, x2, y, h, p_value, text=None):
    """在两组之间画显著性线"""
    if text is None:
        if p_value < 0.0001: text = '****'
        elif p_value < 0.001: text = '***'
        elif p_value < 0.01: text = '**'
        elif p_value < 0.05: text = '*'
        else: text = 'ns'
    ax.plot([x1, x1, x2, x2], [y, y+h, y+h, y], lw=1, color='black')
    ax.text((x1+x2)/2, y+h, text, ha='center', va='bottom', fontsize=10)
```

---

## 第五部分：执行步骤

### 1. 读取图表规划

从 `framework.md` 读取图表数量、类型、主题、章节归属、数据来源。检查 `project_brief.md` → 获取语言和目标期刊。

### 2. 确定输出规范

| 判断项 | SCI (en_US) | 中文核心 (zh_CN) |
|--------|------------|-----------------|
| 矢量格式 | EPS + PDF（嵌入式字体） | SVG |
| 色图 | 色盲友好 + 感知均匀 | 经典学术配色 |
| 分辨率 | ≥1200 DPI（线条图） | ≥300 DPI |
| 多面板 | 标准 A-F 标签 | 可选 |
| 字体嵌入 | 强制 | 不强制 |
| 统计标注 | 强制（N, SEM/SD, p值） | 可选 |
| 色图类型 | 仅限 perceptual | 灵活 |
| 可访问性 | alt text | 可选 |

### 3. 逐张生成

按 framework.md 图表规划顺序逐张生成。每张图的流程：

1. **确定画布尺寸**：查 1.1 节期刊尺寸表，选单栏/双栏
2. **选择配色方案**：查 2.1/2.2 节，选对应色板
3. **生成矢量图**：手写 SVG（机制图）或 Matplotlib（数据图）
4. **添加面板标签**（多面板）：A/B/C 14pt bold 左上角
5. **添加统计标注**（数据图）：误差线 + 显著性线
6. **写图注**：写入 `figure_captions.md`

### 4. 渲染输出

```python
# SCI 项目——出版级输出
fig.savefig('figure_01.eps', format='eps', dpi=1200, bbox_inches='tight')
fig.savefig('figure_01.pdf', format='pdf', dpi=1200, bbox_inches='tight',
            pdf.fonttype=42, ps.fonttype=42)  # 嵌入式字体

# 预览版 PNG
fig.savefig('figure_01.png', format='png', dpi=300, bbox_inches='tight')

# 矢量图保真验证：用 AI/Inkscape 打开 EPS/PDF，确认字体为嵌入式、
# 颜色为 CMYK、无缺失元素
```

### 5. 生成汇总对比表

（同 v1，略）生成 Markdown 表格 → `manuscript/tables.md`

### 6. 生成 Graphical Abstract（SCI 项目）

- 尺寸：1200×600 px（横向，Elsevier/Cell 偏好）
- 或 531×1328 px（纵向，Nature 偏好）
- 2-4 个核心元素 + 极简文字
- 2-3 种主色调 + 色盲友好
- 配合 50-100 words 描述（放在 article 正文中）
- 字体 ≥ 14pt（缩略图下可读）

### 7. 可访问性检查

对每张图生成 alt text：

```markdown
<!-- Alt text for Figure 1 -->
Figure 1: Schematic overview of the single-cell and spatial transcriptomics
workflow for CRC TME characterization. Panel A shows the experimental pipeline
from tissue collection to data analysis. Panel B compares scRNA-seq (n=12
studies) and spatial transcriptomics (n=8 studies) in terms of cell throughput
and spatial resolution. Panel C summarizes the cellular composition of CRC TME
identified by these technologies. Color coding: blue = T cells, orange =
myeloid cells, green = B cells, red = stromal cells. Statistical tests:
two-sided Wilcoxon rank-sum, *p<0.05, **p<0.01.
```

---

## 第六部分：常见 SCI 期刊图表风格速查

| 特征 | Nature | Cell | Science | Lancet | Gut |
|------|--------|------|---------|--------|-----|
| 面板标签 | 左上 bold | 左上 bold | 左下 bold | 顶部居中 | 左上 |
| 配色偏好 | 低饱和 | 中饱和 | 克制 | 灰调为主 | 蓝色系 |
| 图注位置 | 图下方 | 图下方 | 图下方 | 图下方 | 图下方 |
| 坐标轴线 | 下+左 | 下+左 | 全部 | 下+左 | 下+左 |
| 网格线 | 无 | 无 | 浅灰 dashed | 无 | 浅灰 |
| error bar | SEM | SEM | SD 或 SEM | SD 或 SEM | SEM |
| N 标注 | 必须 | 必须 | 必须 | 必须 | 必须 |

---

## 第七部分：质量检查清单

### 基础检查（v1 保留）
- [ ] 每张图有 caption（含缩写解释）？
- [ ] 配色符合目标期刊风格？
- [ ] 分辨率 ≥ 300 DPI？
- [ ] 字体大小 ≥ 8pt？
- [ ] 无软件/工具水印？
- [ ] 图表数量与 framework.md 一致？
- [ ] SCI 项目：有 Graphical Abstract？

### SCI 专项检查（v2 新增）
- [ ] **色盲友好**：用 Coblis 模拟器验证了 Deuteranopia/Protanopia/Tritanopia？
- [ ] **灰度测试**：转为灰度后所有类别仍可区分？
- [ ] **色图类型**：热图使用了 perceptually uniform colormap（非 jet）？
- [ ] **字体嵌入**：EPS/PDF 中字体为嵌入式字体（不是系统字体引用）？
- [ ] **面板标签**：多面板图有 A/B/C 标签（14pt bold，位置一致）？
- [ ] **统计标注**：有误差线定义（SEM/SD）、N 值、显著性标注？
- [ ] **尺寸正确**：符合目标期刊的单栏/双栏宽度？
- [ ] **矢量输出**：SCI 项目有 EPS 或 PDF 矢量文件？
- [ ] **CMYK 色彩**：印刷图色彩空间为 CMYK（非 RGB）？
- [ ] **可访问性**：每张图有 alt text 描述？
- [ ] **期刊风格**：面板标签位置、坐标轴样式、配色符合目标期刊惯例？

---

## Python 脚本

| 脚本 | 功能 | 用法 |
|------|------|------|
| `scripts/generate_figure.py` | 图表渲染工具库：色盲友好配色方案 + 期刊专属尺寸模板 + 统计标注工具 + 多格式导出（SVG/PNG/PDF/EPS） | `from generate_figure import ColorScheme, JournalTemplate, render_figure` |

该工具库供 AI 在生成图表代码时 import 使用，提供感知均匀色图（viridis/cividas）、双层色盲安全调色板、Nature/PNAS/Science 等期刊尺寸模板。

### 第三方增强工具（2026-08-11 安装）

安装于 Python 3.13 venv `~/.workbuddy/binaries/python/envs/default/`，与 generate_figure.py 搭配使用：

| 工具 | 版本 | 用途 | 典型用法 |
|------|------|------|---------|
| **SciencePlots** | 2.2.2 | 一行代码切换 Nature/Cell/IEEE/AAAS 期刊风格 | `plt.style.use(["science", "nature", "no-latex"])` |
| **Great Tables** | 0.23.0 | 出版级学术表格：标题/副标题/spanner/脚注/数据着色 | `GT(df).tab_header(...).fmt_number(...).data_color(...)` |
| **schemdraw** | 0.23 | 程序化绘制信号通路/流程图/机制示意图 | `from schemdraw import flow; flow.Box("EGFR")` |

**与 generate_figure.py 的关系：**
- `generate_figure.py` 提供配色模板（ColorScheme）和期刊尺寸（JournalTemplate）——**数据来源**
- SciencePlots 提供全局样式（字体/刻度/网格线）——**视觉渲染层**
- schemdraw 提供程序化机制图绘制——**示意图层**（替代手写 SVG）
- Great Tables 提供出版级表格——**表格层**（替代 Markdown 表格）

四者完全兼容，可在一个脚本中同时使用。运行脚本时需指定 venv Python 路径。

## 更新状态

```json
{
  "current_skill": "08_figure_maker",
  "version": "v2",
  "phases": {"5_journal": {"skills": {"08_figure_maker": "completed"}}},
  "files": {"figures": "literature-review/figures/"}
}
```
