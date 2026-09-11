---
name: lr-literature-screen
description: 文献综述文献筛选分类 v2。当用户已有 literature_db.csv（含自动标注的文献库），需要逐篇做纳入/排除判定时触发。基于标题和摘要按纳入排除标准筛选，将文献库收敛到 50-80 篇精读清单。支持中英文文献筛选，SCI 项目使用 JCR 分层。两轮筛选：快速筛选 + 精细筛选。当用户说"筛选文献""做纳入排除""精读清单"时触发。
agent_created: true
---

# 文献综述 — Step 4: 文献筛选分类 v2

## 概述

将自动检索入库的文献按 project_brief.md 中的纳入/排除标准逐篇判定，收敛到 50-80 篇核心精读清单。筛选分两轮：快速筛选（标题+摘要）→ 精细筛选（误排修正 + maybe 处理 + 收敛）。

**v2 新特性：**
- 语言无关筛选逻辑（中英文文献共用一套判定标准）
- SCI 项目使用 JCR 分区分层（Q1→Q2→Q3→Q4 对应优先级）
- 纳入排除原因支持中英双语标注
- 筛选 CSV 增加英文排除原因字段

## 前置条件

- 已完成 `lr-pubmed-search`，存在 `literature_db.csv`
- `project_brief.md` 中有明确的纳入/排除标准
- `project_status.json` 中有目标语言

## 产出文件

### screened_literature.csv

在 literature_db.csv 基础上增加字段：

| 字段 | 说明 |
|------|------|
| ScreenStatus | included / excluded / maybe |
| ExcludeReason | 中英双语排除原因（如"wrong_cancer / 非目标癌种"） |
| ScreenRound | 1（快速筛选）/ 2（精细筛选） |
| ReadPriority | high / medium / low |

### reading_list.md

按章节分组的精读清单，标注优先级（🔴 high / 🟡 medium），中英双语格式。

## 执行步骤

### 1. 加载纳入排除标准

从 `project_brief.md` 读取，注意语言相关的差异：

| 纳入标准 | 中文项目 | SCI 项目 |
|----------|----------|----------|
| 语言 | 中文 + 英文 | 英文为主 |
| 文献类型 | 研究性论文、综述、方法学 | 同左，+ Systematic Review |
| 时间范围 | 如 2020-2026 | 通常更短（2022-2026，突出新颖性） |
| 预印本 | 排除 | 可酌情纳入（标注 [Preprint]） |

### 2. 第一轮：快速筛选

基于 Title + Abstract 判定（与 v1 相同逻辑，但增加语言无关处理）。

**关键改进：**
- 中英文标题统一转小写后匹配关键词
- 技术关键词表需要同时包含中英文（如 "单细胞测序" / "single-cell"）
- 排除原因同时提供中英文，便于 SCI 项目后续使用

### 3. 第二轮：精细筛选

三步修正（与 v1 相同）：
1. 检查被误排的高优先级文献
2. 处理 maybe 文献
3. 收敛精读清单到 50-80 篇

### 4. SCI 项目特殊处理

**JCR 分层对应 ReadPriority：**
- Q1 + IF > 10 → high
- Q1 → high
- Q2 → medium
- Q3/Q4 → low

**SCI 综述文献量建议：**
- 叙述性综述：50-60 篇精读 + 补充引用至 100-150 篇终稿引用
- 系统综述：按 PRISMA 流程，最终纳入数量取决于证据基础

### 5. 生成 reading_list.md

中英双语格式：

```markdown
# 精读清单 / Reading List

## Ch2: scRNA-seq in CRC TME / scRNA-seq在CRC TME中的应用
| Priority | Author | Year | Title | Journal | PMID | DOI |
|----------|--------|------|-------|---------|------|-----|
| 🔴 high | Zhang | 2024 | Single-cell atlas of ... | Cancer Cell | 12345 | 10.xxx |
```

### 6. 章节覆盖核查

与 v1 相同逻辑。

## 质量检查

- [ ] 每篇 excluded 文献是否记录了双语排除原因？
- [ ] included 文献中 high+medium 数量是否在目标范围？
- [ ] 每章是否至少有 5 篇核心精读文献？
- [ ] SCI 项目：JCR 分层是否正确应用？
- [ ] 中英文关键词表是否覆盖完整？
- [ ] maybe 文献是否都经过了第二轮精细筛选？

## Python 脚本

| 脚本 | 功能 | 用法 |
|------|------|------|
| `scripts/filter_quick.py` | 第一轮关键词快速筛选：基于癌种+技术+生物学机制三维判定，自动标注 ScreenStatus 和 ExcludeReason | `python filter_quick.py literature_db.csv --outdir ./` |

该脚本自动化快速筛选阶段的机械匹配工作（关键词判定、三维打分），将筛选清单从百余篇收敛到 50-80 篇后进入精细筛选。

## 更新状态

```json
{
  "current_skill": "04_literature_screen",
  "phases": {"2_evidence": {"skills": {"04_literature_screen": "completed"}}},
  "files": {"screened_literature": "literature-review/screened_literature.csv", "reading_list": "literature-review/reading_list.md"}
}
```
