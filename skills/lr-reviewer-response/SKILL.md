---
name: lr-reviewer-response
description: 文献综述审稿意见回复器。当收到（真实或模拟的）审稿意见后，需要逐条回复时触发。生成模拟审稿意见、逐条回复策略模板、修改记录追踪、拒稿改投预案。支持中英文审稿意见回复。当用户说"回复审稿意见""审稿人意见回复""rebuttal""模拟审稿"时触发。
agent_created: true
---

# 文献综述 — Step 12: 审稿意见回复器

## 概述

收到审稿意见后，逐条分析并撰写专业、有说服力的回复信。同时为拒稿场景准备改投预案。支持真实审稿意见（用户提供）和模拟审稿（AI 生成）。

## 前置条件

- 已有投稿就绪稿件 `submission_ready.docx` 或 `polished_draft.md`
- 已有审稿意见（真实或模拟）

## 产出文件

- `reviewer_comments.md`：整理后的审稿意见（如使用模拟审稿）
- `rebuttal_letter.md`：逐条回复信
- `revised_manuscript.docx`：修订稿（含修改痕迹）

## 执行步骤

### 1. 接收审稿意见

**两种模式：**

**模式 A：模拟审稿（投稿前预演）**
- AI 以审稿人视角审读稿件
- 生成 2-3 位模拟审稿人的意见
- 覆盖：方法学审稿人、领域专家、语言编辑

**模式 B：真实审稿（投稿后收到意见）**
- 用户提供审稿意见原文
- AI 逐条分析并撰写回复

### 2. 分析审稿意见

将每条审稿意见分类：

| 类别 | 含义 | 处理策略 |
|------|------|----------|
| 方法学问题 | 对方法/流程的质疑 | 补充说明或承认局限性 |
| 内容补缺 | 要求补充讨论/引用 | 能补则补，不能补说明原因 |
| 语言/格式 | 语言表达或格式问题 | 逐条修改 |
| 创新性疑问 | 质疑综述的新颖性 | 用对标对比来回应 |
| 误解 | 审稿人可能误读了某部分 | 礼貌澄清（注意措辞） |
| 无理要求 | scope 之外的要求 | 礼貌解释为何不做 |

### 3. 撰写逐条回复信

**SCI 审稿回复信模板：**

```markdown
[Date]

Dear Editor [Name],

We sincerely thank you and the reviewers for the careful evaluation of our manuscript entitled "[Title]" (Manuscript ID: [ID]). The constructive comments have significantly improved the quality of our review. We have addressed all comments point by point as detailed below. All changes in the revised manuscript are highlighted in [blue/tracked changes].

Sincerely,

[Author Name]
[Affiliation]

---

**Response to Reviewers**

**Reviewer #1**

**Comment 1:** [Reviewer's original comment]

*Response:* We thank the reviewer for this insightful comment. [Explain what was done — modified text, added reference, clarified point]. The following changes have been made:

[Quote modified text from the revised manuscript, with line numbers]

**Comment 2:** [Reviewer's original comment]

*Response:* ...

---

**Reviewer #2**

...

---

**Summary of Changes**
| Section | Change | Reviewer |
|---------|--------|----------|
| Introduction | Added discussion of... | R1, C1 |
| Ch3 | Clarified methodology for... | R2, C3 |
| ... | ... | ... |
```

**中文审稿回复信模板：**

```markdown
尊敬的《[期刊名]》编辑部/审稿专家：

感谢您对稿件的细致评审。我们已逐条认真修改，以下为逐条回复说明。修改处在修订稿中以[蓝色/修订模式]标注。

此致
敬礼

[作者姓名]
[单位]
[日期]

---

**逐条回复**

**审稿人 1**

**意见 1：** [审稿人原文]

**回复：** 感谢审稿专家的宝贵意见。[说明做了什么修改]。具体修改如下：

[引用修订稿中的修改内容]

**意见 2：** ...

---

**审稿人 2**

...

---

**修改汇总**
| 位置 | 修改内容 | 对应意见 |
|------|----------|----------|
| 引言 | 补充了... | R1-1 |
| 第3章 | 澄清了... | R2-3 |
| ... | ... | ... |
```

### 4. 回复策略

**Do（应该做的）：**
- 每条开头感谢审稿人
- 明确说明做了什么修改
- 引用修改后的文本（标注行号）
- 即使不同意，也要保持尊重
- 承认局限性（如无法修改，说明原因）
- 使用具体语言（而非模糊承诺）

**Don't（不应该做的）：**
- 与审稿人争论（永远不要！）
- 回复太简短（如"已修改"）
- 直接拒绝（用"We acknowledge this limitation"替代）
- 声称修改了但实际没改
- 对不同审稿人的同一问题给出不同回复
- 忽略审稿人提到的任何问题

### 5. 复杂意见处理策略

**当审稿人要求增加不在 scope 内的内容时：**
> "We appreciate the reviewer's suggestion. While a comprehensive discussion of [topic] is beyond the scope of this review, we have added a brief mention in [section] and cited key references for interested readers."

**当多位审稿人意见冲突时：**
> "We note that Reviewer 1 suggested [A] while Reviewer 2 suggested [B]. We have adopted a balanced approach by [compromise solution], which we believe addresses both concerns."

**当审稿人误读时（最危险的回复类型）：**
> "We apologize for the lack of clarity in the original manuscript. We have revised [section] to better convey that [correct meaning]."

### 6. 生成修订稿

根据所有接受的修改建议，生成修订稿 `revised_manuscript.docx`：
- 使用修订模式（Track Changes）或蓝色高亮标注修改处
- 注明版本号
- 更新参考文献

### 7. 生成拒稿改投预案（如需）

如果审稿意见是 Major Revision 且难度较大，或担心被拒稿：

```markdown
## 拒稿改投预案

| 场景 | 概率估计 | 行动计划 |
|------|----------|----------|
| 接收 / Minor Revision | 30% | 按审稿意见修改后提交 |
| Major Revision → 接收 | 40% | 全力修改，重点回应方法学和创新性质疑 |
| 拒稿 | 30% | → 根据 journal_match.md 投备选期刊 |

**被拒后 48h 行动清单：**
1. 冷静分析拒稿理由
2. 能改的修改，不改稿直接转投
3. 更新 Cover Letter 的期刊名
4. 检查备选期刊的格式要求
5. 一周内转投下一个期刊
```

## 模拟审稿意见生成（模式 A）

当用户选择"模拟审稿"时，按以下模板生成：

### Reviewer 1: 方法学审稿人
- 关注检索策略是否全面
- 文献纳入/排除是否合理
- 是否有系统偏倚
- 参考文献是否覆盖全面

### Reviewer 2: 领域专家
- 关注内容是否准确
- 是否有遗漏的重要研究
- 对新进展的覆盖是否及时
- 论点是否有充分支撑

### Reviewer 3: 语言/综合审稿人
- 关注语言表达
- 图表质量
- 结构逻辑
- 总体推荐意见

## 质量检查

- [ ] 每条审稿意见是否有针对性回复？
- [ ] 每条回复是否以"感谢"开头？
- [ ] 修改是否在修订稿中可追溯？
- [ ] 是否有修改汇总表？
- [ ] 回复语气是否礼貌且专业？
- [ ] 是否有拒稿改投预案？
- [ ] 模拟审稿：是否覆盖了方法学/内容/语言三个维度？

## 更新状态

```json
{
  "current_skill": "12_reviewer_response",
  "phases": {"6_submission": {"status": "completed", "skills": {"12_reviewer_response": "completed"}}},
  "status": "completed"
}
```
