---
name: lr-chapter-writing
description: 文献综述分章写作 v2。当用户已有 framework.md（综述框架），需要逐章撰写初稿时触发。基于框架的论点树和精读笔记，逐章生成结构化的学术综述初稿。支持中英双语写作——中文项目使用中文学术规范（术语首次注英文），SCI 项目使用英文学术规范（被动语态、地道表达、SCI 惯用句式）。当用户说"写初稿""开始写作""写第X章"时触发。
agent_created: true
---

# 文献综述 — Step 7: 分章写作 v2

## 概述

基于 framework.md 的论点树和 reading_notes/ 中的精读笔记，逐章撰写综述初稿。每章独立成文，章内按子论点组织段落，每段有明确论点 + 文献支撑 + 过渡句。

**v2 新特性：**
- SCI 英文写作规范（被动语态、地道学术表达、段落节奏）
- 引用格式切换（GB/T 7714-2015 ↔ Vancouver/APA/期刊指定格式）
- 英文学术写作质量自查清单
- 结合精读笔记中的 "Key Sentences for Writing" 提升语言质感
- 支持 Graphical Abstract 描述文字撰写

## 前置条件

- 已完成 `lr-framework`，存在 `framework.md`
- `reading_notes/` 目录完整，含 INDEX.md
- `project_brief.md` 中有目标语言和字数要求

## 产出文件

### manuscript/full_draft.md（所有章节合并的完整初稿）

## 写作规范

### 中文项目规范（与 v1 相同）

- 术语首次出现标注英文：如"肿瘤微环境（tumor microenvironment, TME）"
- 避免口语化表达
- 被动语态与主动语态交替使用
- 段落长度 150-300 字
- 引用格式：GB/T 7714-2015

### SCI 英文项目规范（新增）

**学术写作风格：**
- 以被动语态为主（"It has been demonstrated that..."而非"We demonstrate..."）
- 但适当使用主动语态增强可读性（特别是总结和展望部分）
- 避免口语化缩写（don't → do not, can't → cannot）
- 使用精确动词（demonstrate > show, elucidate > explain, underscore > emphasize）

**段落结构：**
- Topic sentence（论点句）→ Supporting evidence（证据，含引用和数据）→ Concluding/transition sentence（过渡句）
- 每段 100-200 words
- 通过 subheading 组织内容，避免过长的文字墙

**常用句式库：**

| 功能 | 句式 | 使用场景 |
|------|------|----------|
| 指出空白 | "However, ... remains poorly understood / has not been systematically investigated" | Introduction / 每章开头 |
| 建立联系 | "Building on these findings, recent studies have ..." | 章节过渡 |
| 呈现证据 | "Consistent with this notion, [Author] et al. demonstrated that ..." | 主体段落 |
| 批评估价 | "While these studies provide valuable insights, they are limited by ..." | Discussion |
| 总结展望 | "Future studies integrating ... will be essential to ..." | 每章小结 / 全文结论 |
| 突出创新 | "A landmark study by [Author] et al. first revealed that ..." | 里程碑工作 |

**引用格式：**
- 默认：Vancouver 编号制 [1], [2], [3-5]
- 备选：APA（Author, Year）或期刊指定格式
- 在 framework.md 中标注引用的 PMID 或编号

**术语规范：**
- 基因名：斜体（如 *KRAS*, *TP53*）
- 蛋白名：正体（如 KRAS, TP53）
- 物种名：斜体（如 *Homo sapiens*, *Mus musculus*）
- 首次使用的缩写标全称

**SCI 综述特有元素：**
- Structured Abstract（结构式摘要，通常 200-300 words）
- Key Points Box（核心要点框）
- Graphical Abstract 描述（50-100 words）
- 每个主要章节末可加 Summary Box

## 执行步骤

### 1. 选择写作模板

- `zh_CN` → 中文模板（与 v1 相同）
- `en_US` → 英文模板

### 2. 确定写作顺序

（与 v1 相同：先主体章 → 引言 → 未来方向）

### 3. 逐章写作

**中文 Prompt 模板（与 v1 相同）：**

```
你是临床科研文献综述的写作助手。请基于以下信息撰写第 X 章初稿。

## 章节框架
[从 framework.md 提取该章的论点树]

## 可用精读笔记
[列出该章关联的精读笔记 PMID 和核心发现]

## 写作要求
1. 每段以论点句开头，后接文献支撑（含具体数据）
2. 引用格式：[作者 et al., 年份, 期刊] 或 [编号]
3. 段落间有过渡句，形成逻辑递进
4. 字数目标：[X 字]
5. 语言：中文
6. 术语首次出现标注英文
7. 不要编造数据——如果没有的数据，标注[需核查]
```

**英文 Prompt 模板（新增）：**

```
You are an academic writing assistant for SCI review articles. Write Chapter X based on the following framework.

## Chapter Framework
[Extracted from framework.md]

## Available Reading Notes
[List of PMIDs with key findings and Key Sentences for Writing]

## Writing Requirements
1. Each paragraph opens with a topic sentence, followed by supporting evidence with specific data
2. Citation format: Vancouver numbered [1], [2], or [Author, Year]
3. Use passive voice dominantly, active voice sparingly for conclusions
4. Paragraph length: 100-200 words
5. Target word count: [X words]
6. Language: English (academic, precise, concise)
7. Gene names in italics (*KRAS*), protein names in regular (KRAS)
8. Do NOT fabricate data — mark uncertain information as [To be verified]
9. Use precise verbs (demonstrate, elucidate, underscore) rather than vague ones (show, tell)
10. Incorporate Key Sentences for Writing from the reading notes where applicable

## Output Format
Organize by subheadings (from the argument tree). End each major section with a brief "Summary" box (3-4 bullet points).
Include relevant citations as [PMID: xxxxx].
```

### 4. 写作质量自检

**中文项目自查 (与 v1 相同)。**

**SCI 英文项目自查（新增）：**
```
□ 每段是否有明确的 topic sentence？
□ 是否以被动语态为主？（check: 不要出现过多 "We found..."）
□ 引用是否可追溯到精读笔记？
□ 基因名是否斜体、蛋白名是否正体？
□ 数据是否精确（具体数字而非模糊描述）？
□ 是否有编造的数据？
□ 段落长度是否在 100-200 words？
□ 术语缩写是否首次出现时标全称？
□ 是否使用了 SCI 惯用句式？
□ 是否避免了口语化表达？
```

### 5. 全文整合

- 合并为 `manuscript/full_draft.md`
- 检查章节间过渡
- 生成 Abstract（Structured for SCI）
- 生成 Key Points Box（SCI）
- 生成参考文献列表

## 质量检查

- [ ] 每章是否都有论点句开头的段落？
- [ ] 引用是否可追溯到精读笔记？
- [ ] 是否有未标注的编造数据？
- [ ] 章节间过渡是否流畅？
- [ ] 字数是否在目标范围内？
- [ ] SCI 项目：是否使用了被动语态和地道表达？
- [ ] SCI 项目：基因/蛋白命名是否符合规范？
- [ ] 参考文献列表是否完整且格式统一？
- [ ] **写完后必须进入 lr-citation-verify 做引用验证**：初稿完成后，下一步不是润色，而是引用验证（7 层防幻觉门禁）。只有验证通过才可进入 lr-polish。

## 更新状态

```json
{
  "current_skill": "07_chapter_writing",
  "phases": {"4_writing": {"status": "completed", "skills": {"07_chapter_writing": "completed"}}, "5_journal": {"status": "in_progress"}}
}
```
