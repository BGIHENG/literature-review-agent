---
name: lr-cover-letter
description: 文献综述投稿信撰写器。当综述润色完成后，需要根据目标期刊要求生成 Cover Letter / 投稿信时触发。突出综述的创新点、与目标期刊的匹配度、作者背景。支持 SCI 英文 Cover Letter 和中文投稿信双格式。产出 cover_letter.md。当用户说"写投稿信""Cover Letter""投稿信"时触发。
agent_created: true
---

# 文献综述 — Step 11: 投稿信撰写器

## 概述

为综述撰写专业的投稿信（Cover Letter）。投稿信是编辑对你稿件的第一印象——一封好的投稿信能显著提升送审率。

## 前置条件

- 已完成润色稿 `polished/polished_draft.md`
- 已确定目标期刊（推荐：已完成 `lr-journal-select`）

## 产出文件

- `cover_letter.md`：投稿信全文

## SCI Cover Letter 模板

```markdown
[Date]

Dear Editor [or specific editor name if known],

We are pleased to submit our review manuscript entitled "[Title]" for consideration for publication in [Journal Name].

**[Paragraph 1: The Problem & Significance]**
[2-3 sentences setting the stage — what is the field, what gap exists, why it matters now.]

**[Paragraph 2: What This Review Does]**
[2-3 sentences summarizing the review's scope, methodology, and key contributions. Be specific — mention the number of studies reviewed, the analytical framework used, and 1-2 most important findings or insights.]

**[Paragraph 3: Fit with [Journal Name]]**
[2-3 sentences explaining why this review is a good fit for this specific journal. Reference the journal's scope, recent similar publications, or readership.]

**[Paragraph 4: Declarations]**
We confirm that this manuscript has not been published elsewhere and is not under consideration by another journal. All authors have approved the manuscript and agree with its submission to [Journal Name]. The authors declare no conflicts of interest. [Add funding info if applicable.]

We believe this review will be of significant interest to the readers of [Journal Name], and we look forward to your response.

Sincerely,

[Corresponding Author Name, Degree]
[Affiliation]
[Email]
[ORCID]
```

## 中文投稿信模板

```markdown
《[期刊名]》编辑部：

兹向贵刊投稿综述稿件《[标题]》，恳请审阅。

**[第一段：研究背景与意义]**
[2-3 句，说明领域背景、知识空白、本综述的意义]

**[第二段：综述内容与创新点]**
[2-3 句，概述综述的范围、方法、核心发现和创新贡献]

**[第三段：与贵刊的匹配度]**
[2-3 句，说明本文与贵刊办刊宗旨和读者群的契合之处]

**[第四段：声明]**
本稿件未一稿多投，全体作者已审阅并同意投稿。所有作者声明无利益冲突。[如有基金资助，注明]

恳请编辑部审阅。感谢！

此致
敬礼

[通信作者姓名、职称]
[单位]
[邮箱]
[日期]
```

## 执行步骤

### 1. 提取稿件信息

从 polished_draft.md 和 project_brief.md 中提取：
- 综述标题（中/英）
- 核心创新点（3-5 条）
- 综述类型和方法
- 关键发现或洞察
- 图表数量

### 2. 提取目标期刊信息

从 journal_match.md 或 project_brief.md 中提取：
- 期刊全名
- 期刊的 scope 和侧重点
- 期刊近期的相关发表
- 编辑名字（如有，建议查找）

### 3. 撰写各段落

**第一段（问题与意义）：**
- 不要用泛泛的"X is a hot topic"
- 指出具体的知识空白或临床需求
- 引用 1-2 个关键统计数据增强说服力

**第二段（综述做了什么）：**
- 明确范围（时间、数据库、纳入文献数）
- 突出 1-2 个最重要的发现/洞察
- 提到方法学严谨性（如果是系统综述）
- 提到创新点（与现有综述的差异）

**第三段（为什么选这个期刊）：**
- 引用该期刊的 scope statement
- 提到该期刊近期发表的 1-2 篇相关文章
- 说明读者群匹配

**第四段（声明）：**
- 无一稿多投
- 全体作者同意
- 利益冲突声明
- 基金资助信息

### 4. 个性化调整

为每个目标期刊调整 Cover Letter：
- 修改"Fit with Journal"段落的内容
- 调整语调以匹配期刊风格（Nature 类 vs. 专科期刊）
- 如果知道编辑名字，使用具体姓名

### 5. 质量检查

- 不要过长（一页 A4 纸以内）
- 不要重复摘要内容（Cover Letter 是写给编辑的，摘要是写给读者的）
- 不要过分夸大（避免"the first""the best""groundbreaking"）

## 常见错误

| 错误 | 修正 |
|------|------|
| 模板式开头 | 改为针对性的领域问题 |
| 只泛泛说"X is important" | 引用具体数据或研究空白 |
| 没有说明为什么选这个期刊 | 必须个性化匹配 |
| Cover Letter 太长（>500 words） | 精简到 300-400 words |
| 重复摘要全文 | Cover Letter 是 elevator pitch |
| 忘记声明无一稿多投 | 必须包含声明段 |

## 质量检查

- [ ] 是否有具体的问题陈述（而非泛泛而谈）？
- [ ] 是否说明了与目标期刊的匹配理由？
- [ ] 是否包含无一稿多投声明？
- [ ] 是否在 300-400 words（SCI）或一页内（中文）？
- [ ] 是否为每个目标期刊准备了个性化版本？

## 更新状态

```json
{
  "current_skill": "11_cover_letter",
  "phases": {"5_journal": {"skills": {"11_cover_letter": "completed"}}},
  "files": {"cover_letter": "literature-review/cover_letter.md"}
}
```
