---
name: lr-search-strategy
description: 文献综述多数据库检索式生成 v2。当用户已有 project_brief.md，需要设计 PubMed/Web of Science/Scopus/CNKI 检索式时触发。根据 PICO 框架和章节大纲，为每个目标数据库设计分主题的多条检索式，确保每条叙事线都有专属文献池。覆盖英文（SCI）和中文双轨检索策略。当用户说"设计检索式""生成检索策略""写检索式"时触发。
agent_created: true
---

# 文献综述 — Step 2: 多数据库检索式生成 v2

## 概述

根据 PICO 框架，为多个数据库（PubMed / Web of Science / Scopus / CNKI）设计分主题检索式。覆盖所有章节，每条检索式针对一个叙事线，避免单条检索式过于宽泛或遗漏。

**v2 新特性：**
- 支持 Web of Science 和 Scopus 数据库检索语法
- 支持 SCI 英文综述的检索策略
- 每个数据库提供最适合的检索语法变体
- 数据库优先级根据语言自动调整

## 前置条件

- 已完成 `lr-project-init`，存在 `project_brief.md`
- PICO 框架、章节大纲、纳入排除标准已确认
- 目标语言已确定（zh_CN / en_US）

## 产出文件

### search_strategy.md

```markdown
# 多数据库检索策略

## 检索概况
- 目标语言: [zh_CN / en_US]
- 时间范围: [YYYY-MM 至 YYYY-MM]
- 拟检索数据库: [按优先级排列]

## 数据库优先级矩阵

| 优先级 | zh_CN 项目 | en_US 项目 |
|--------|-----------|-----------|
| 主力 | PubMed | PubMed |
| 主力 | CNKI / 万方 | Web of Science |
| 补充 | 万方医学 | Scopus |
| 补充 | — | Google Scholar (引文追溯) |

---

## 一、PubMed 检索式

### Q1: [主题名，如"TME 全景覆盖"]
```
(Colorectal Neoplasms[MeSH] OR "colorectal cancer"[tiab] OR "colon cancer"[tiab] OR "rectal cancer"[tiab] OR CRC[tiab])
AND
("single-cell RNA sequencing"[tiab] OR "scRNA-seq"[tiab] OR "single-cell transcriptom*"[tiab])
AND
("tumor microenvironment"[MeSH] OR "tumor immune microenvironment"[tiab] OR "TME"[tiab])
AND
("2020/01/01"[Date - Publication] : "2026/06/30"[Date - Publication])
```
预期命中: 200-400 篇
目标章节: Ch2, Ch3

### Q2: [主题名，如"耐药专项"]
...
```

## 执行步骤

### 1. 确定数据库清单

根据 `project_status.json` 中的 `language` 参数：

**zh_CN 项目：**
- 主力：PubMed（英文文献为主）+ CNKI（中文文献补充）
- 补充：万方医学（中文学位论文和会议论文）

**en_US 项目：**
- 主力：PubMed + Web of Science Core Collection
- 补充：Scopus（覆盖更广，含预印本）+ Google Scholar（引文追溯）

### 2. 从 PICO 提取检索维度

将 PICO/PICOS/PEO 的每个元素转化为检索词组。

### 3. 按目标数据库构建检索式

#### PubMed 检索式语法

```
- MeSH 词: Term[MeSH]（推荐，自动包含下位词）
- MeSH 主要主题: Term[MeSH Major Topic]（更精确）
- 标题/摘要自由词: Term[tiab]
- 标题词: Term[ti]（更精确）
- 作者关键词: Term[ot]
- 时间限制: "YYYY/MM/DD"[Date - Publication] : "YYYY/MM/DD"[Date - Publication]
- 文献类型: review[pt] / "Journal Article"[pt]
- 语言: english[la] / chinese[la]
- 布尔逻辑: AND / OR / NOT（大写）
- 截词符: * （如 transcriptom* → transcriptome/transcriptomics/transcriptomic）
- 精确短语: 用双引号
```

#### Web of Science 检索式语法

```
- 主题字段: TS=(...)
- 标题字段: TI=(...)
- 摘要字段: AB=(...)
- 作者关键词: AK=(...)
- 出版年: PY=(2020-2026)
- 文献类型: DT=(Review OR Article)
- 语言: LA=(English)
- 期刊名: SO=(...)
- 布尔逻辑: AND / OR / NOT
- 截词符: *（同 PubMed）
- 邻近检索: NEAR/n
- 与 PubMed 不同: 无 MeSH 词表，所有检索均为自由词
```

#### Scopus 检索式语法

```
- 标题/摘要/关键词: TITLE-ABS-KEY(...)
- 仅标题: TITLE(...)
- 仅摘要: ABS(...)
- 仅关键词: KEY(...)
- 出版年: PUBYEAR > 2019 AND PUBYEAR < 2027
- 文献类型: DOCTYPE(re) OR DOCTYPE(ar)
- 语言: LANGUAGE(english)
- 期刊名: SRCTITLE(...)
- 布尔逻辑: AND / OR / AND NOT
- 截词符: *（同 PubMed）
- 邻近检索: W/n（Within n words）
- 与 PubMed 不同: 无 MeSH 词表，但有 Emtree（Embase 词表）
```

#### CNKI 检索式语法

```
- 主题字段: SU='...'（覆盖标题+摘要+关键词）
- 标题: TI='...'
- 摘要: AB='...'
- 关键词: KY='...'
- 发表时间: YE FROM 2020 TO 2026
- 文献类型: DB='期刊' / '博士' / '硕士'
- 布尔逻辑: AND / OR / NOT
- 截词符: %（注意不是 *）
```

### 4. 按章节设计多条检索式

**原则：** 不要用一条超级检索式覆盖所有内容，而是按章节/主题拆分。

| 检索式 | 覆盖范围 | 章节目标 | 数据库 |
|--------|----------|----------|--------|
| Q1 全景覆盖 | P + I/E + O(TME) | Ch1-Ch3 | PubMed, WoS |
| Q2 专项 A | P + I/E + O(子主题A) | Ch4 | PubMed, Scopus |
| Q3 专项 B | P + I/E + O(子主题B) | Ch5 | PubMed, WoS |
| Q4 方法学 | I/E(技术) + review/methods filter | Ch2-Ch3 | PubMed, Scopus |
| Q5 补充检索 | 针对缺口章节 | 按需 | 所有数据库 |

### 5. 跨数据库检索式适配

同一条检索逻辑在不同数据库中的语法不同。例如"单细胞 + CRC + TME"：

**PubMed 版：**
```
("single-cell RNA sequencing"[tiab] OR "scRNA-seq"[tiab]) AND (CRC[tiab] OR "colorectal cancer"[tiab]) AND ("tumor microenvironment"[tiab] OR TME[tiab])
```

**WoS 版（自由词为主）：**
```
TS=("single-cell RNA sequencing" OR "scRNA-seq") AND TS=(CRC OR "colorectal cancer") AND TS=("tumor microenvironment" OR TME)
```

**Scopus 版（用 TITLE-ABS-KEY 覆盖更广）：**
```
TITLE-ABS-KEY("single-cell RNA sequencing" OR "scRNA-seq") AND TITLE-ABS-KEY(crc OR "colorectal cancer") AND TITLE-ABS-KEY("tumor microenvironment" OR tme)
```

### 6. 设定补充检索预案

预估每条检索式的命中量，对可能不足的章节预先设计补充检索式。

**常见缺口预案：**
- 引言章节：补充流行病学/背景检索（不加技术关键词）
- 方法学章节：补充 computational/bioinformatics 专项检索
- 边缘主题：放宽研究对象限制（如从 CRC → gastrointestinal cancers）

### 7. 生成 search_strategy.md

包含所有数据库、所有检索式的完整文档。

## 质量检查

- [ ] 每个章节至少被一条检索式覆盖？
- [ ] 是否覆盖了所有目标数据库？
- [ ] 每条检索式是否包含数据库特定的语法（MeSH/WoS TS/Scopus TITLE-ABS-KEY）？
- [ ] 同义词是否充分（技术名词的缩写、全称、变体）？
- [ ] 时间范围是否与 project_brief.md 一致？
- [ ] 跨数据库检索式是否逻辑一致？
- [ ] 是否预留了补充检索预案？

## Python 脚本

| 脚本 | 功能 | 用法 |
|------|------|------|
| `scripts/build_strategy.py` | 基于预置关键词库自动生成 PubMed/Web of Science/Scopus/CNKI 四数据库检索式 | `python build_strategy.py project_brief.md --outdir ./` |

该脚本内置 6 组主题关键词（癌种/技术/生物学/临床/方法学/排除），为每个数据库生成多条符合其语法的检索式（MeSH/WoS TS/Scopus 字段限定），输出 search_strategy.md。

## 更新状态

完成后更新 `project_status.json`：
```json
{"current_skill": "02_search_strategy", "phases": {"2_evidence": {"status": "in_progress", "skills": {"02_search_strategy": "completed"}}}, "files": {"search_strategy": "literature-review/search_strategy.md"}}
```
