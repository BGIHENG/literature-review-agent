---
name: lr-reading-notes
description: 文献综述核心文献精读笔记 v3。当用户已有 screened_literature.csv（精读清单），需要对每篇核心文献做结构化精读时触发。v3 新增全文 PDF 阅读模式——先通过 download_oa_pdfs.py 下载 OA PDF，再通过 pdf_reader.py 提取正文，最后用 batch_enrich.py 自动补全 Methods/Figures/Limitations 等摘要缺失字段。支持中英双语文献的精读模板。当用户说"精读文献""做阅读笔记""提取文献信息""升级全文阅读"时触发。
agent_created: true
---

# 文献综述 — Step 5: 核心文献精读笔记 v3

## 概述

对精读清单中的 50-80 篇文献逐篇做结构化精读，提取可直接用于写作的信息。每篇一个 Markdown 笔记文件，格式统一。

**v3 新特性（全文阅读升级）：**
- **全文 PDF 阅读**：通过 `download_oa_pdfs.py` → `pdf_reader.py` → `batch_enrich.py` 三阶段流水线，自动下载 OA PDF、提取正文、补全精读笔记
- **字段数据来源标注**：每个字段标记 `[来源: abstract]` / `[来源: fulltext]`，明确信息层级
- **自动提取**：从 Methods 提取技术平台/样本处理/测序参数，从 Results 提取图表亮点，从 Discussion 提取局限性

**v2 已有特性：**
- 英文文献精读模板（SCI 项目导向）
- 中英双语笔记格式（中文项目仍需提取英文术语）
- "可用于 SCI 写作的关键句式"提取
- "与其他综述的差异点"标注（结合 benchmark_report.md）

## 前置条件

- 已完成 `lr-literature-screen`，存在 `screened_literature.csv`
- 精读清单已确定（50-80 篇）
- SCI 项目：推荐先完成 `lr-benchmark`

## v3 全文阅读流水线（可选但推荐）

当需要从"摘要级"升级到"全文级"精读时，按以下顺序执行：

```
                     screened_literature.csv
                            │
   Step A: download_oa_pdfs.py ───→  pdfs/ (OA PDF 下载)
     (lr-zotero-import/scripts/)       └─ pdf_download_report.csv
                            │
   Step B: pdf_reader.py ────────→  fulltext/PMID_xxxxx.md (结构化全文)
     (lr-zotero-import/scripts/)       └─ pdf_reader_report.csv
                            │
   Step C: batch_enrich.py ──────→  reading_notes_v2/PMID_xxxxx.md
     (lr-reading-notes/scripts/)       └─ enrich_report.json
```

| 步骤 | 脚本位置 | 输入 | 输出 | 预期覆盖率 |
|------|---------|------|------|:--:|
| A | `lr-zotero-import/scripts/download_oa_pdfs.py` | CSV | `pdfs/` | 40-60% 英文文献 |
| B | `lr-zotero-import/scripts/pdf_reader.py` | `pdfs/` + CSV | `fulltext/PMID_*.md` | 与 A 相同 |
| C | `lr-reading-notes/scripts/batch_enrich.py` | `reading_notes/` + `fulltext/` | `reading_notes_v2/` | 有全文的笔记 |

**注意**：中文文献（CNKI/万方）和付费墙后英文文献无法自动获取 PDF，此类文献保持"摘要级"精读。

## 产出文件

### reading_notes/PMID_xxxxx.md

**中文项目模板（与 v1 相同，微调）：**

```markdown
# [文献标题]

## 基本信息
- **PMID:** xxxxx
- **DOI:** 10.xxxx/xxxxx
- **作者:** FirstAuthor et al.
- **期刊:** Journal Name (Year) | IF: xx.x | JCR: Qx
- **文献类型:** Research Article / Review
- **所属章节:** Ch2_scRNA; Ch3_ST

## 研究设计
- **研究类型:** [队列研究 / 病例对照 / 横断面 / 方法学 / 综述]
- **样本量:** [n=xx]
- **技术平台:** [10x / Visium / Stereo-seq...]
- **分析方法:** [Seurat / Harmony / CellChat...]

## 核心发现（3-5 条，含具体数据）
1. [发现1：一句话 + 数据]
2. [发现2]
3. ...

## 技术细节
- **样本处理:** [...]
- **测序深度:** [...]
- **关键参数:** [...]

## 图表亮点
- **Fig. 1:** [...]
- **Fig. 3:** [...]

## 与本综述的关联
- **支撑论点:** [...]
- **可引用数据:** [...]
- **差异化价值:** [与对标综述相比，此文献能提供什么独特内容]

## 局限性
- [...]

## 关键引文
- [该文引用的重要参考文献]
```

**SCI 项目模板（新增）：**

```markdown
# [Title]

## Basic Info
- **PMID:** xxxxx | **WoS_ID:** xxxxx | **DOI:** 10.xxxx/xxxxx
- **Authors:** FirstAuthor et al.
- **Journal:** Journal Name (Year) | IF: xx.x | JCR: Qx
- **Type:** Research Article / Review
- **Chapter:** Ch2_scRNA; Ch3_ST

## Study Design
- **Design:** [cohort / case-control / cross-sectional / methods / review]
- **Sample size:** [n=xx]
- **Platform:** [10x / Visium / Stereo-seq...]
- **Analysis:** [Seurat / Harmony / CellChat...]

## Key Findings (3-5 items with data)
1. [Finding + specific data (gene names, p-values, HR, etc.)]
2. ...
3. ...

## Technical Details
- **Sample processing:** [...]
- **Sequencing depth:** [...]
- **Key parameters:** [...]

## Highlight Figures
- **Fig. 1:** [...]
- **Fig. 3:** [...]

## Relevance to Our Review
- **Arguments supported:** [...]
- **Citable data:** [...]
- **Differentiation value:** [What unique content this paper adds vs. benchmark reviews]

## Key Sentences for Writing (SCI mode)
- "This study demonstrates that ... (p < 0.001), highlighting the role of ..."
- "Notably, ... was identified as ..., providing a potential ..."

## Limitations
- [...]

## Key References Cited
- [...]
```

## 执行步骤

### 1. 选择精读模板

根据 `project_status.json` 中的 `language` 字段选择：

- `zh_CN` → 中文模板（术语标注英文）
- `en_US` → 英文模板（增加 Key Sentences for Writing）

### 2. 批量处理策略

| 优先级 | 策略 | 笔记详细度 |
|--------|------|-----------|
| P1/Q1 high (~30 篇) | 逐篇精读 | 最详细 |
| P2/Q2 medium (~30 篇) | 精读摘要+关键数据 | 中等 |
| P3/Q3-Q4 low | 快速浏览 | 提取 1-2 条核心发现 |

### 3. 英文精读额外维度（SCI 项目）

除 v1 的 6 个维度外，增加：

**Key Sentences for Writing：**
从文献中提取 2-3 个高质量英文学术句式，在写作时可直接改编使用。这是 SCI 写作的重要助力——不是抄袭原句，而是学习地道的学术表达。

**Differentiation Value：**
结合 benchmark_report.md，标注该文献与对标综述的差异——它提供什么独特内容？

### 4. 生成 INDEX.md

中英双语索引：

```markdown
# 精读笔记索引 / Reading Notes Index

## Ch2: scRNA-seq in CRC TME (15 篇)
| PMID | Author | Year | Key Finding | Key Data | Sentences |
|------|--------|------|-------------|----------|-----------|
| xxxxx | Zhang | 2024 | Identified 12 TME subtypes | 50k cells, 12 types | ✅ extracted |
```

## 质量检查

- [ ] 每篇笔记是否有"核心发现"（≥3 条，含具体数据）？
- [ ] "与本综述的关联"是否关联到具体章节？
- [ ] 技术细节是否完整？
- [ ] SCI 项目：是否提取了 Key Sentences for Writing？
- [ ] SCI 项目：是否标注了 Differentiation Value？
- [ ] 不确定信息是否标注"需人工核查"？
- [ ] 是否生成了 INDEX.md？

**v3 全文增强质量检查：**
- [ ] 是否尝试了 OA PDF 下载（`download_oa_pdfs.py`）？
- [ ] 是否运行了 PDF 正文提取（`pdf_reader.py`）？
- [ ] 是否运行了批量增强（`batch_enrich.py`）？
- [ ] 增强后的笔记中，技术平台/样本处理/测序深度是否非空？
- [ ] 增强后的笔记中，图表亮点和局限性是否补全？
- [ ] 每个字段是否标注了 `[来源: abstract/fulltext/inferred]`？
- [ ] 是否有 `enrich_report.json` 记录了增强效果？

## 涉及脚本

| 脚本 | 用途 | 位置 |
|------|------|------|
| `download_oa_pdfs.py` | 通过 Unpaywall+PMC 下载 OA PDF | `lr-zotero-import/scripts/` |
| `pdf_reader.py` | 用 PyMuPDF 提取 PDF 正文为结构化 Markdown | `lr-zotero-import/scripts/` |
| `batch_enrich.py` | 用全文补全现有精读笔记 | `lr-reading-notes/scripts/` |

## 更新状态

```json
{
  "current_skill": "05_reading_notes",
  "phases": {"2_evidence": {"status": "completed", "skills": {"05_reading_notes": "completed"}}, "3_framework": {"status": "in_progress"}}
}
```
