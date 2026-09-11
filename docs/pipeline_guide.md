# Pipeline 完整流程指南

## 总览

```
阶段 1 选题协议       阶段 2 证据库构建          阶段 3 框架      阶段 4 写作        阶段 5 期刊适配     阶段 6 投稿返修
─────────────      ──────────────────       ──────────     ────────────     ─────────────     ─────────────
lr-project-init  →  lr-search-strategy    →  lr-framework → lr-chapter-    → lr-figure-maker → lr-reviewer-
lr-benchmark        lr-pubmed-search                      writing         lr-journal-select   response
                    lr-literature-screen               → lr-citation-    lr-polish
                    lr-zotero-import                      verify ★        lr-cover-letter
                    lr-reading-notes
                                                          ★ = 防幻觉硬门禁
```

---

## 阶段 1：选题协议

### lr-project-init

**目的**：在任何检索开始前，敲定 5 个必须拍板的决定。

| # | 决定 | 说明 |
|---|------|------|
| 1 | 癌种 / 研究对象范围 | 聚焦特定癌种，还是不限癌种？方法学文献是否跨癌种？ |
| 2 | 技术 / 方法范围 | 哪些是主线（必须覆盖），哪些是支线（展望提及） |
| 3 | 叙事权重 | 路径 A 技术驱动 / 路径 B 均衡 / 路径 C 临床转化驱动 |
| 4 | 目标语言与期刊 | `zh_CN` 中文核心 / `en_US` SCI；目标期刊类型 |
| 5 | 时间范围 | 近 3 年 / 5 年 / 10 年；检索截止日期 |

**硬门禁**：5 项未全部确认，不得进入下一步。

**产出**：
- `project_brief.md` — PICO/PICOS/PEO 框架、纳入排除标准、章节大纲、选题可行性评估
- `project_status.json` — 项目状态跟踪（贯穿全程）

### lr-benchmark

**目的**：搜索 3-5 篇最相关的高影响力同类综述，深度学习其框架、论证、图表、语言。

| 语言 | 是否必需 |
|------|---------|
| `zh_CN` | 可选 |
| `en_US` | **强制** |

**产出**：`benchmark_report.md`

---

## 阶段 2：证据库构建

### lr-search-strategy

按 PICO 框架和章节大纲，为每个目标数据库设计**分主题的多条检索式**，确保每条叙事线都有专属文献池。

**脚本**：`scripts/build_strategy.py` — 6 组预置关键词 × 4 数据库检索式生成

**产出**：`search_strategy.md`

### lr-pubmed-search

**脚本**：`scripts/fetch_pubmed.py`

- PubMed（E-utilities）：自动化批量检索
- Web of Science / Scopus / CNKI：无公开 API，需人工导出后合并
- 跨库去重、自动标注优先级和章节归属

**产出**：`literature_db.csv`

### lr-literature-screen

两轮筛选：

1. **快速筛选**（`scripts/filter_quick.py`）— 癌种 + 技术 + 生物学三维关键词判定
2. **精细筛选** — 逐篇读摘要，按纳入排除标准判定

**产出**：`screened_literature.csv` + `reading_list.md`（50-80 篇精读清单）

### lr-zotero-import

三种导入方式：

| 方式 | 脚本 | 需要 | 适合 |
|------|------|------|------|
| **Web API（推荐）** | `zotero_web_import.py` | User ID + API Key（一次性获取） | 每次都用 |
| RIS 手动 | `generate_ris.py` | 无需配置 | 临时使用 |
| Better BibTeX | — | BBT 插件 + Zotero 运行中 | 已配置 BBT |

**PDF 获取链路**：
```
download_oa_pdfs.py  →  pdf_reader.py  →  batch_enrich.py
   (Unpaywall +          (PyMuPDF 正文       (从全文补全
    PMC API 下载)         提取 + IMRaD)        精读笔记字段)
```

**API Key 交互输入**（不回显、不留 shell 历史）：
```bash
python scripts/zotero_web_import.py screened.csv --collection-name "My Review"
# 运行后提示输入 User ID 和 API Key
```

**凭证获取**：https://www.zotero.org/settings/keys
1. 页面顶部获取 User ID
2. Create new private key → 勾选 Allow library access + Allow write access

**产出**：`zotero_import.ris`、`zotero_metadata_report.md`、`zotero_pdf_status.csv`

### lr-reading-notes

**v3 全文阅读模式**：

| 层级 | 来源 | 能提取什么 |
|------|------|-----------|
| 摘要级 | PubMed abstract | 研究设计、核心发现 |
| **全文级** | OA PDF 正文 | + 技术平台、样本处理、测序参数、图表亮点、局限性 |

三阶段流水线可将 40-60% 的英文文献从摘要级升级到全文级。

**脚本**：`scripts/batch_enrich.py`

**产出**：`reading_notes/PMID_*.md` + `INDEX.md`

---

## 阶段 3：框架搭建

### lr-framework

基于精读笔记：

1. 提炼**论点树**（每章一个核心论点，下级是支撑证据）
2. 设计**章间逻辑链**（递进关系，不是平行罗列）
3. 识别**矛盾论点**并预设讨论方案
4. 规划**图表和字数分配**

**产出**：`framework.md`

---

## 阶段 4：分章写作

### lr-chapter-writing

按论点树逐章撰写。中文项目用中文学术规范（术语首见注英文），SCI 项目用英文学术规范（被动语态、SCI 惯用句式）。

**产出**：`manuscript/chX_*.md` → `manuscript/full_draft.md`

### lr-citation-verify ★ 防幻觉硬门禁

**7 层验证**：

| 层 | 验证内容 | 自动化 |
|----|---------|--------|
| L1 | 证据库交叉比对 | ✅ 脚本 |
| L2 | PubMed API 验证（PMID 存在性） | ✅ 脚本 |
| L3 | Crossref DOI 解析 | ✅ 脚本 |
| L4 | 期刊/年份/作者一致性 | ✅ 脚本 |
| L5 | Google Scholar 搜索验证 | ⚠️ 半自动 |
| L6 | 数据点溯源（回精读笔记） | ✅ 脚本 |
| L7 | 幻觉标记扫描 | ✅ 脚本 |

**脚本**：`scripts/verify_citations.py`（自动化 L1-L4, L6-L7）

**产出**：`citation_verification_report.md` + `verification_results.csv`

**未通过此门禁，不得进入润色阶段。**

---

## 阶段 5：期刊适配

### lr-figure-maker

**脚本**：`scripts/generate_figure.py`

提供：
- 色盲友好配色方案（Wong 2011 双层调色板）
- 期刊专属尺寸模板（Nature / PNAS / Science 单栏双栏）
- 统计标注工具
- 多格式导出（SVG / PNG / PDF / EPS）

**配套三方工具**：

| 工具 | 用途 |
|------|------|
| SciencePlots | 一行切换期刊风格 `plt.style.use(["science", "nature"])` |
| great_tables | 出版级表格（title / spanner / footnote / data_color） |
| schemdraw | 程序化绘制机制示意图 |

**产出**：`figures/figure_*.svg|png`、`figures/table_*.md`

### lr-journal-select

匹配 3-5 个目标期刊，含 IF / JCR 分区 / 审稿周期 / 接受率 / APC。

| 语言 | 是否必需 |
|------|---------|
| `zh_CN` | 可选 |
| `en_US` | **强制** |

**产出**：`journal_match.md`

### lr-polish

- 中文项目：优化中文表达（避免口语化、术语规范）
- SCI 项目：优化英文表达（去 AI 味、地道 SCI 句式、语法检查）

**产出**：`polished/polished_draft.md`

### lr-cover-letter

SCI 英文 Cover Letter / 中文投稿信。

**产出**：`cover_letter.md`

---

## 阶段 6：投稿返修

### lr-reviewer-response

1. 模拟审稿意见（3 位审稿人视角）
2. 逐条回复策略
3. 修改记录追踪
4. 拒稿改投预案

**产出**：`reviewer_comments.md` + `rebuttal_letter.md` + `revised_manuscript.docx`

---

## 回溯机制

任何阶段发现问题，都能回退到上游的**最小修复范围**，记录在 `project_status.json` 的 `backtrack_log`。

| 触发场景 | 回退到 | 最小修复范围 |
|----------|--------|-------------|
| 引用验证发现幻觉引用 | Step 07 写作 | 删除/替换虚假引用，仅修受影响段落 |
| 数据点无法追溯 | Step 05 精读 | 回原文核实数据 |
| 写作时论点缺支撑 | Step 06 框架 | 调整论点树 |
| 框架时证据链断裂 | Step 05 精读 | 只补缺口章节的精读 |
| 某章核心文献 < 5 篇 | Step 03 检索 | 新增补充检索式 |
| 选题过宽/过窄 | Step 01 协议 | 修改 PICO 参数 |
| 语言/结构不符期刊 | Step 09 选刊 | 换刊或深度修改 |

---

## 从任意节点切入

| 已有产物 | 从何开始 |
|----------|---------|
| 只有选题方向 | Step 01 项目初始化 |
| `project_brief.md` | Step 01B（SCI）/ Step 02（中文） |
| `literature_db.csv` | Step 04 文献筛选 |
| `reading_notes/` | Step 06 框架搭建 |
| `full_draft.md` | Step 07B 引用验证 |
| `full_draft.md` 已验证 | Phase 5 期刊适配 |
| 完整稿件需润色 | Step 10 润色 |
| 收到审稿意见 | Step 12 审稿回复 |

---

## 项目目录结构

```
literature-review/
├── project_brief.md                  # Phase 1
├── project_status.json               # 贯穿全程
├── benchmark_report.md               # Phase 1B
├── search_strategy.md                # Phase 2
├── literature_db.csv                 # Phase 2
├── screened_literature.csv           # Phase 2
├── zotero_import.ris                 # Phase 2
├── zotero_metadata_report.md         # Phase 2
├── zotero_pdf_status.csv             # Phase 2
├── pdfs/                             # Phase 2（OA PDF 存放）
├── reading_notes/                    # Phase 2
│   ├── PMID_xxxxx.md
│   └── INDEX.md
├── framework.md                      # Phase 3
├── manuscript/                       # Phase 4
│   ├── full_draft.md
│   └── chX_xxx.md
├── citation_verification_report.md   # Phase 4B ★
├── figures/                          # Phase 5
├── polished/polished_draft.md        # Phase 5
├── journal_match.md                  # Phase 5
├── cover_letter.md                   # Phase 5
├── submission_ready.docx             # Phase 5
├── reviewer_comments.md              # Phase 6
├── rebuttal_letter.md                # Phase 6
└── revised_manuscript.docx           # Phase 6
```
