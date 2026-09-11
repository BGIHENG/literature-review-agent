---
name: lr-framework
description: 文献综述框架搭建 v2。当用户已有 reading_notes/（精读笔记），需要搭建综述整体框架时触发。基于精读笔记提炼论点树、设计章节逻辑链、规划图表。支持中英双语框架模板，SCI 项目增加期刊特定结构要求（Graphical Abstract、Key Points Box、Conflict of Interest 等）。当用户说"搭框架""设计结构""理清逻辑线"时触发。
agent_created: true
---

# 文献综述 — Step 6: 综述框架搭建 v2

## 概述

将 50-80 篇精读笔记中的发现，组织成有逻辑递进的章节框架。每个章节有核心论点，每个论点有文献支撑，章节间有逻辑递进。

**v2 新特性：**
- SCI 综述框架模板（含 Graphical Abstract 规划、Key Points Box、结构化摘要）
- 图表规划细化到期刊要求（分辨率、配色、缩写规范）
- 结合 benchmark_report.md 的对标库分析来验证框架竞争力
- 中英双语框架均可产出

## 前置条件

- 已完成 `lr-reading-notes`，存在 `reading_notes/` 和 `INDEX.md`
- `project_brief.md` 中有章节大纲
- SCI 项目：推荐已有 `benchmark_report.md`

## 产出文件

### framework.md

**中文项目模板（与 v1 相同）：**

```markdown
# 综述框架

## 一、总体逻辑链
[一句话概括全文逻辑]

## 二、章节论点树
### 第 1 章：引言
- **核心论点:** ...
- **支撑文献:** [PMID xxxxx] ...
- **逻辑过渡:** → ...

### 第 2 章：...
...

## 三、图表规划
| 图表号 | 类型 | 主题 | 数据来源 | 章节 |
|--------|------|------|----------|------|
| Figure 1 | ... | ... | ... | ... |

## 四、矛盾论点处理
## 五、字数分配
```

**SCI 项目模板（新增）：**

```markdown
# Review Framework

## 一、Overall Logical Flow / 总体逻辑链
[One-sentence summary]

## 二、Chapter Argument Trees / 章节论点树

### Chapter 1: Introduction
- **Core Argument:** ...
- **Supporting Literature:** [PMID xxxxx] ...
- **Logical Transition:** → ...

[...chapters 2-N...]

## 三、Graphical Abstract Planning / 图形摘要规划
- **Concept:** [核心视觉概念]
- **Elements:** [需要呈现的关键元素]
- **Layout:** [版面布局草图描述]
- **Reference Style:** [对标哪些期刊的 GA 风格]

## 四、Figure & Table Plan / 图规划

| # | Type | Topic | Data Source | Suggested Caption | Chapter |
|---|------|-------|-------------|-------------------|---------|
| Fig 1 | Schematic | ... | Custom | "Fig 1. Overview of ..." | Ch1 |
| Fig 2 | Data integration | ... | Adapted from [PMID] | ... | Ch2 |
| Table 1 | Comparison | ... | Multiple refs | ... | Ch2 |
| ... | ... | ... | ... | ... | ... |

**Figure Requirements for [Target Journal]:**
- Resolution: ≥ 300 DPI (600 DPI for line art)
- Color mode: CMYK (print) / RGB (online)
- Font: Arial/Helvetica, min 8pt
- Abbreviations in caption footnotes

## 五、Key Points Box / 核心要点框
- **What is already known:** (3 bullet points)
- **What this review adds:** (3 bullet points)

## 六、Contradictory Findings / 矛盾论点处理
| Conflict | Study A | Study B | Resolution Strategy |
|----------|---------|---------|---------------------|
| ... | ... | ... | ... |

## 七、Word Count Allocation / 字数分配
| Chapter | Target (words) | % |
|---------|---------------|-----|
| Ch1 Introduction | 600-800 | 10% |
| Ch2 ... | 1500-2000 | 20% |
| ... | ... | ... |
| **Total** | **6000-8000** | 100% |

## 八、SCI-Specific Sections / SCI 特需部分
- **Structured Abstract:** Background / Methods / Results / Conclusions (250-300 words)
- **Keywords:** 5-8 keywords for indexing
- **Conflict of Interest:** [Plan]
- **Funding:** [Plan]
- **Author Contributions:** [Plan]
- **Data Availability:** [Plan]
- **Supplementary Materials:** [Plan: additional tables, search strategy, PRISMA checklist]

## 九、Competitiveness Check (vs Benchmark)
| Dimension | Benchmark Average | Our Plan | Edge? |
|-----------|-------------------|----------|-------|
| No. of figures | 5 | 6-7 | ✅ |
| Reference count | 120 | 120-150 | ✅ |
| Key Points Box | 3/5 have | Yes | ✅ |
| Graphical Abstract | 4/5 have | Yes | = |
| Critical discussion | Medium | Deep | ✅ |
```

## 执行步骤

### 1. 选择框架模板

- `zh_CN` → 中文模板（与 v1 相同流程）
- `en_US` → SCI 模板（增加 Graphical Abstract、Key Points、SCI 特需部分）

### 2. 提炼论点树

（与 v1 相同逻辑）

### 3. 设计逻辑递进

（与 v1 相同逻辑）

### 4. 规划图表（v2 增强）

**SCI 项目图表要求更高：**
- 每章 1-2 个图表（至少 1 个图）
- 总图表数建议 5-8 个（对标平均水平）
- 每个图需要预写 Caption（包含缩写说明）
- 标注"改编自 [PMID]"或"Original figure"
- 分辨率要求 ≥ 300 DPI
- 考虑 Graphical Abstract（越来越多的 SCI 期刊要求）

### 5. 识别矛盾论点

（与 v1 相同逻辑）

### 6. 字数分配（SCI 差异）

- SCI 综述通常 6000-8000 words（期刊差异大，需查目标期刊）
- 引言 5-10%，主体 70-80%，展望 10-15%
- 与中文综述不同，SCI 综述通常更紧凑

### 7. 对标竞争力检查（SCI 新增）

结合 benchmark_report.md，检查你的框架与对标综述相比是否有竞争力：
- 图表数量是否 ≥ 对标平均？
- 是否有 Graphical Abstract 和 Key Points Box？
- 参考文献数量是否足够？
- 批判性讨论深度是否足够？

**如果没有明显优势**：调整框架或回到对标学习补充分析。

### 8. SCI 特需部分规划

- Structured Abstract（结构式摘要）
- Key Points Box（核心要点框——越来越多 SCI 期刊要求）
- Graphical Abstract 概念方案
- 声明部分（Conflict of Interest、Funding、Author Contributions、Data Availability）

## 质量检查

- [ ] 每个子论点是否有至少 2 篇文献支撑？
- [ ] 章节间是否有明确的逻辑过渡？
- [ ] 矛盾论点是否已识别并规划了讨论方式？
- [ ] 图表规划是否覆盖所有章节？
- [ ] SCI 项目：是否规划了 Graphical Abstract？
- [ ] SCI 项目：是否有 Key Points Box？
- [ ] SCI 项目：是否与对标综述做了竞争力检查？
- [ ] 字数分配是否合理且符合目标期刊？

## 更新状态

```json
{
  "current_skill": "06_framework",
  "phases": {"3_framework": {"status": "completed", "skills": {"06_framework": "completed"}}, "4_writing": {"status": "in_progress"}}
}
```
