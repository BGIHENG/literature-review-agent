---
name: lr-journal-select
description: 文献综述期刊选择器。当综述初稿完成后，需要根据主题、方法严谨度、创新程度和目标层次系统匹配投稿期刊时触发。支持 SCI 期刊（基于影响因子、JCR 分区、审稿周期、接受率、APC）和中文核心期刊双轨匹配。产出 journal_match.md（含 3-5 个目标期刊的详细分析）。当用户说"选期刊""匹配期刊""投什么期刊"时触发。
agent_created: true
---

# 文献综述 — Step 9: 期刊选择器

## 概述

综述完成后，选择最合适的投稿期刊。不是"投最高的"，而是"投最匹配的"——综合考虑主题契合度、期刊对综述的偏好、审稿周期、接受率和发表成本。

## 前置条件

- 已完成初稿 `full_draft.md`（或至少完成框架和主要章节）
- `project_brief.md` 中有综述类型和主题
- `project_status.json` 中有目标语言

## 产出文件

### journal_match.md

```markdown
# 期刊匹配报告

## 综述画像
- 主题: [综述标题]
- 类型: [叙述性综述 / 系统综述 / 范围综述]
- 学科领域: [肿瘤学 / 免疫学 / 方法学...]
- 创新度: [高 / 中 / 一般]（与对标综述对比）
- 参考文献数: [X 篇]
- 图表数: [X 图 + Y 表]

## 推荐期刊排名

### 🥇 首选: [Journal Name]
| 维度 | 详情 |
|------|------|
| 影响因子 | xx.x |
| JCR 分区 | Qx |
| 学科排名 | x/xxx |
| 综述接受率 | xx%（估） |
| 审稿周期 | 平均 x 周 |
| APC / 版面费 | $xxxx / 免费 |
| 是否 OA | 是 / 否 / 混合 |
| 对综述的偏好 | 约稿为主 / 接受自由投稿 / 综述友好型 |
| 主题契合度 | ⭐⭐⭐⭐⭐ |
| 近期同类综述 | [引用 2-3 篇该刊近年发表的相关综述] |

**投稿策略:**
- 创新点如何包装：[具体建议]
- 需要特别注意的格式要求：[具体列出]
- 与该刊已发综述的差异化定位：[具体说明]

### 🥈 备选 1: [Journal Name]
（同上结构）

### 🥉 备选 2: [Journal Name]
（同上结构）

### 🏅 保底: [Journal Name]
（同上结构）

## 中文核心期刊对比（zh_CN 项目专属）
| 期刊 | 级别 | 审稿周期 | 版面费 | 主题契合度 | 推荐 |
|------|------|----------|--------|-----------|------|
| 中华胃肠外科杂志 | 北大核心/CSCD | 2-4月 | 中等 | ⭐⭐⭐⭐⭐ | 🥇 |
| 中国肿瘤临床 | 北大核心 | 1-3月 | 较低 | ⭐⭐⭐⭐ | 🥈 |
| ... | ... | ... | ... | ... | ... |

## 决策建议
- 推荐投稿顺序: [期刊A] → 如被拒 → [期刊B] → [期刊C]
- 预计时间线: [投稿→一审→修回→接收 = X个月]
- 投稿前检查清单: [格式/图表/摘要/字数/参考文献]
```

## 执行步骤

### 1. 提取综述画像

从 project_brief.md 和 full_draft.md 中提取：
- 核心主题和关键词
- 综述类型
- 方法学严谨程度（系统综述 > 叙述性综述）
- 创新程度（与对标综述对比）
- 图表质量
- 参考文献数量

### 2. 搜索候选期刊

**SCI 期刊搜索来源：**
- Journal Citation Reports (JCR)
- PubMed 同类综述的发表期刊
- 对标综述的发表期刊
- Master Journal List (Web of Science)
- DOAJ（OA 期刊目录）

**中文核心期刊搜索来源：**
- 中国科学引文数据库 (CSCD)
- 北大核心期刊目录
- CNKI 同类综述的发表期刊
- 中信所统计源期刊

### 3. 评估匹配度

为每个候选期刊评估：

**硬性门槛（不满足直接排除）：**
- 是否接受该类型综述的投稿？
- 综述是否是自由投稿可接受的（非约稿制）？
- 主题是否在期刊 scope 内？
- 字数/图表数是否在期刊限制内？

**加分项：**
- 近期是否发表过类似主题的综述？
- 综述友好型期刊
- 审稿周期短
- APC 可接受 / 免费
- 高接受率

### 4. 生成推荐排名

按照"匹配度 > 影响因子"的原则排序：
1. 首选：主题最匹配、接受率最高的合理目标
2. 备选 1：稍低 IF 但审稿快
3. 备选 2：同级别期刊的不同选择
4. 保底：接受率高的期刊

### 5. 撰写投稿策略

对每个推荐期刊，说明：
- 如何包装创新点
- 格式要求的注意事项
- 与已发综述的差异化定位

## SCI 综述期刊分类参考

### 综述友好型顶级期刊
- Nature Reviews xxx 系列（约稿为主，自由投稿极少）
- Trends in xxx 系列（Cell Press，接受自由投稿）
- Annual Review of xxx（约稿）
- Current Opinion in xxx（约稿为主）

### 临床/转化肿瘤学综述友好型
- Cancer Discovery（IF ~30）
- Cancer Cell（IF ~48）
- Journal of Hematology & Oncology（IF ~23，综述友好）
- Cancer Treatment Reviews（IF ~13，综述专门期刊）
- Seminars in Cancer Biology（IF ~17，综述专门期刊）
- Critical Reviews in Oncology/Hematology（IF ~6，综述专门期刊）

### 方法学综述友好型
- Nature Methods（IF ~48）
- Nature Biotechnology（IF ~55）
- Genome Biology（IF ~12）
- Briefings in Bioinformatics（IF ~9，方法学综述友好）
- Bioinformatics（IF ~5）
- BMC Bioinformatics（IF ~3）

## 质量检查

- [ ] 是否覆盖了 4-5 个候选期刊？
- [ ] 每个期刊是否评估了综述投稿可行性（非约稿 vs 约稿）？
- [ ] 是否考虑了审稿周期和 APC？
- [ ] 是否查看了目标期刊近期发表的相关综述？
- [ ] 投稿策略是否切实可行而非空泛建议？
- [ ] 是否有明确的投稿顺序建议？

## 更新状态

```json
{
  "current_skill": "09_journal_select",
  "phases": {"5_journal": {"skills": {"09_journal_select": "completed"}}},
  "files": {"journal_match": "literature-review/journal_match.md"}
}
```
