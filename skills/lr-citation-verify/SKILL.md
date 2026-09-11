---
name: lr-citation-verify
description: 文献综述引用验证器 v1。当初稿完成后（full_draft.md），需要系统验证全文所有引用文献真实存在、可在 Google/PubMed 检索到、数据点可追溯到精读笔记时触发。通过 7 层验证（证据库交叉比对、PubMed API 验证、Crossref DOI 解析、Google Scholar 搜索验证、数据点溯源、参考文献完整性、幻觉标记扫描），生成 citation_verification_report.md。当用户说"验证引用""查幻觉""核查文献""防幻觉"时触发。
agent_created: true
---

# 文献综述 — Step 07B: 引用验证器 v1

## 概述

在初稿完成后、润色前，对全文所有引用进行系统性验证，确保每条引用真实存在、可检索、数据可追溯。这是 Pipeline 的**防幻觉硬门禁**——通过即放行，不通过则回退修复。

**核心价值：**
- 从终稿提取全部引用 → 逐条验证真实性
- 7 层验证覆盖"引用存在性""引用准确性""数据可追溯性"三个维度
- 利用 PubMed E-utilities API、Crossref API、Google Scholar 搜索三重交叉验证
- 生成结构化验证报告，标注通过/警告/失败

## 前置条件

- 已完成 `lr-chapter-writing`，存在 `manuscript/full_draft.md`
- 存在 `literature_db.csv`（文献库）
- 存在 `reading_notes/` 目录（精读笔记）
- 存在 `screened_literature.csv`（精读清单）

## 产出文件

### citation_verification_report.md

```markdown
# 引用验证报告 / Citation Verification Report

## 验证概况
- 验证日期: YYYY-MM-DD
- 初稿文件: manuscript/full_draft.md
- 全文引用总数: N 条
- 参考文献列表条目: M 条
- 验证通过: X 条 (XX%)
- 警告（需人工确认）: Y 条
- 失败（疑似幻觉）: Z 条

## 七层验证结果

### Layer 1: 证据库交叉比对
| 引用编号 | 终稿标注 | literature_db 匹配 | 状态 |
|----------|----------|-------------------|------|
| [1] | Zhang et al., 2024, Cancer Cell | PMID: 12345 ✓ | PASS |
| [5] | Wang et al., 2023, Nature | 未找到匹配 | FAIL |

### Layer 2: PubMed API 验证
| 引用编号 | PMID | esummary 返回 | 标题匹配 | 状态 |
|----------|------|--------------|----------|------|
| [1] | 12345 | 正常返回 | 完全匹配 | PASS |
| [3] | 67890 | 正常返回 | 部分匹配（年份不符） | WARN |

### Layer 3: Crossref DOI 解析
| 引用编号 | DOI | Crossref 返回 | 状态 |
|----------|-----|--------------|------|
| [1] | 10.1016/j.ccell.2024.01.001 | 正常解析 | PASS |
| [5] | 无 DOI | — | SKIP |

### Layer 4: Google Scholar 搜索验证
| 引用编号 | 搜索关键词 | Google 命中 | 状态 |
|----------|-----------|------------|------|
| [1] | "Zhang" "single-cell" "colorectal" 2024 | 首条命中 | PASS |
| [5] | "Wang" "spatial" "CRC" 2023 | 未命中 | FAIL |

### Layer 5: 数据点溯源
| 终稿数据 | 引用编号 | 精读笔记匹配 | 状态 |
|----------|----------|-------------|------|
| "50,000 cells, 12 subtypes" | [1] | reading_notes/PMID_12345 ✓ | PASS |
| "HR=2.3, p<0.001" | [7] | 未在精读笔记中找到 | WARN |

### Layer 6: 参考文献列表完整性
| 检查项 | 结果 |
|--------|------|
| 正文引用 [1]-[N] 与参考文献列表条目 1:1 对应 | PASS / FAIL |
| 是否存在正文引用了但参考文献列表缺失 | [列出缺失编号] |
| 是否存在参考文献列表有但正文未引用 | [列出多余编号] |

### Layer 7: 幻觉标记扫描
| 检查项 | 命中数 | 详情 |
|--------|--------|------|
| [需核查] / [To be verified] 标记 | N 处 | [列出位置] |
| [TODO] / [补充] / [待确认] 标记 | N 处 | [列出位置] |
| 模糊数据（"研究表明""大量数据"无引用） | N 处 | [列出位置] |

## 验证结论
- [ ] 全部通过 → 放行进入 lr-polish
- [ ] 存在 WARN → 人工确认后放行
- [ ] 存在 FAIL → 回退到 lr-chapter-writing 修复

## 修复清单（如有 FAIL）
| 编号 | 问题类型 | 当前标注 | 建议修复 |
|------|----------|----------|----------|
| [5] | 文献不存在 | Wang et al., 2023, Nature | 删除或替换为真实文献 |
| [7] | 数据无法追溯 | HR=2.3 | 核查原文或标注为推测 |
```

## 七层验证详解

### Layer 1: 证据库交叉比对

**目标：** 确保终稿中每条引用都能在 `literature_db.csv` 或 `screened_literature.csv` 中找到对应记录。

**方法：**
```
对终稿中每个引用 [N]:
  1. 提取引用标注信息（作者、年份、期刊）
  2. 在 literature_db.csv 中搜索匹配记录
     - 优先匹配 PMID（如有）
     - 其次匹配 DOI
     - 最后匹配 标题相似度 > 80%
  3. 记录匹配状态
```

**状态判定：**
- PASS: 精确匹配（PMID 或 DOI 一致）
- PASS: 高相似度匹配（标题相似度 > 90%）
- WARN: 部分匹配（作者/年份/期刊有 1 项不符）
- FAIL: 无匹配（引用不在文献库中）

### Layer 2: PubMed API 验证

**目标：** 对有 PMID 的引用，通过 PubMed E-utilities 验证 PMID 真实有效。

**方法：**
```
对每个有 PMID 的引用:
  1. 调用 esummary API:
     https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi
       ?db=pubmed
       &id={PMID}
       &retmode=json
  2. 检查返回结果:
     - PMID 是否存在（非空返回）
     - 标题是否匹配（终稿标注 vs PubMed 记录）
     - 作者是否匹配（第一作者姓）
     - 年份是否匹配
     - 期刊是否匹配
  3. 记录验证状态
```

**注意事项：**
- 批量查询：一次最多 200 个 PMID
- 请求间隔 0.34s（PubMed 建议每秒不超过 3 次）
- 无 PMID 的引用标记为 SKIP，不视为失败

### Layer 3: Crossref DOI 解析

**目标：** 对有 DOI 的引用，验证 DOI 可解析且元数据匹配。

**方法：**
```
对每个有 DOI 的引用:
  1. 调用 Crossref API:
     https://api.crossref.org/works/{DOI}
  2. 检查返回结果:
     - DOI 是否可解析（HTTP 200）
     - 标题是否匹配
     - 作者是否匹配
     - 发表年份是否匹配
  3. 记录验证状态
```

**备用方案：** 如果 Crossref 不可用，尝试 `https://doi.org/{DOI}` 重定向验证。

### Layer 4: Google Scholar 搜索验证

**目标：** 验证每条引用可通过 Google 搜索检索到，这是防止幻觉的最终防线。

**方法：**
```
对每条引用（尤其是 Layer 1-3 中 SKIP 或 WARN 的引用）:
  1. 构造搜索关键词:
     - 第一作者姓 + 标题关键词 + 年份
     - 示例: "Zhang" "single-cell atlas colorectal" 2024
  2. 使用 WebSearch 工具搜索
  3. 检查搜索结果:
     - 首条结果是否匹配（高度置信）
     - 前 5 条中是否有匹配（中等置信）
     - 无匹配结果（FAIL: 疑似幻觉）
  4. 记录搜索关键词和命中状态
```

**优先级：**
- 对 Layer 1 FAIL 的引用：必须执行 Google 搜索
- 对无 PMID/DOI 的引用：必须执行 Google 搜索
- 对有 PMID 且 Layer 2 PASS 的引用：可跳过（已验证）

### Layer 5: 数据点溯源

**目标：** 验证终稿中引用的具体数据（样本量、p 值、HR、百分比等）可追溯到精读笔记。

**方法：**
```
1. 从终稿中提取所有带引用的数据点:
   - 数字 + 单位/指标 + 引用编号
   - 示例: "50,000 cells [1]", "HR=2.3 (95% CI 1.5-3.5) [7]"
   
2. 对每个数据点:
   a. 找到对应引用的精读笔记 reading_notes/PMID_xxxxx.md
   b. 在精读笔记中搜索该数据点
   c. 判定:
      - 精确匹配: 数据点在精读笔记中找到
      - 近似匹配: 数据点存在但数值略有差异（可能是四舍五入）
      - 未找到: 数据点不在精读笔记中（可能是幻觉或未精读到的细节）
   
3. 对未找到的数据点:
   - 标注 [需核查原文]
   - 在验证报告中列出
```

**数据点提取正则（参考）：**
```
# 带引用的数字数据
(?:[≥≤~]?\d[\d,]*\.?\d*)\s*(?:%|cells?|samples?|patients?|HR|OR|RR|p\s*[<>=]|CI|fold|n=)
```

### Layer 6: 参考文献列表完整性

**目标：** 确保正文引用与参考文献列表 1:1 对应。

**检查项：**
1. 正文每个 `[N]` 都在参考文献列表中有对应条目
2. 参考文献列表每条都在正文中被引用至少一次
3. 编号连续性（无跳号、无重复）
4. 格式统一性（所有条目格式一致）

### Layer 7: 幻觉标记扫描

**目标：** 扫描终稿中的不确定标记和模糊表述。

**扫描模式：**
```
# 不确定标记
\[需核查\]|\[To be verified\]|\[TODO\]|\[补充\]|\[待确认\]|\[核查\]

# 模糊表述（无引用的论断）
"研究表明"|"大量数据"|"多项研究"|"普遍认为"  # 后面没有引用编号
```

**处理：**
- 不确定标记 → 在验证报告中列出位置，提醒后续处理
- 模糊表述 → 标注 WARN，建议补充具体引用

## 验证流程

```
full_draft.md
    │
    ▼
Layer 1: 提取引用 → 交叉比对 literature_db.csv
    │           ↓ FAIL
    │           → 标记疑似幻觉
    ▼
Layer 2: 有 PMID → PubMed esummary 验证
    │           ↓ FAIL (PMID 不存在)
    │           → 标记疑似幻觉
    ▼
Layer 3: 有 DOI → Crossref 验证
    │           ↓ FAIL (DOI 不可解析)
    │           → 标记疑似幻觉
    ▼
Layer 4: 全部引用 → Google Scholar 搜索验证
    │           ↓ FAIL (搜索不到)
    │           → 确认幻觉，标记 FAIL
    ▼
Layer 5: 提取数据点 → 精读笔记溯源
    │           ↓ 未找到
    │           → 标记 WARN [需核查原文]
    ▼
Layer 6: 正文引用 ↔ 参考文献列表 1:1 检查
    │           ↓ 不一致
    │           → 标记 FAIL
    ▼
Layer 7: 幻觉标记扫描 → 列出所有 [需核查] 等标记
    │
    ▼
生成 citation_verification_report.md
    │
    ▼
判定: 全 PASS → 放行 lr-polish
      有 WARN → 人工确认后放行
      有 FAIL → 回退 lr-chapter-writing 修复
```

## 回退修复规则

| FAIL 类型 | 回退到 | 修复范围 |
|-----------|--------|----------|
| 引用不在文献库中 | lr-chapter-writing | 删除该引用或从 literature_db 中补充真实文献 |
| PMID 不存在 | lr-chapter-writing | 核查 PMID，修正或删除 |
| DOI 不可解析 | lr-chapter-writing | 核查 DOI，修正或删除 |
| Google 搜索不到 | lr-chapter-writing | 确认幻觉，删除或替换为真实文献 |
| 参考文献列表缺失 | lr-chapter-writing | 补充参考文献列表条目 |
| 数据点无法追溯 | lr-reading-notes | 回去精读原文核实数据 |

## 质量检查

- [ ] 全文引用是否 100% 经过至少 3 层验证？
- [ ] 所有有 PMID 的引用是否经过 PubMed API 验证？
- [ ] 所有有 DOI 的引用是否经过 Crossref 验证？
- [ ] Layer 1 FAIL 的引用是否全部经过 Google Scholar 搜索？
- [ ] 数据点溯源是否覆盖了终稿中所有带引用的数字？
- [ ] 参考文献列表是否与正文引用 1:1 对应？
- [ ] 幻觉标记扫描是否覆盖全文？
- [ ] 验证报告是否完整记录了每条引用的验证状态？
- [ ] FAIL 项是否有明确的修复建议？

## Python 脚本

| 脚本 | 功能 | 用法 |
|------|------|------|
| `scripts/verify_citations.py` | 自动化 7 层引用验证（L1-L4 机械操作），含 PubMed API/Crossref DOI 验证、证据库交叉比对 | `python verify_citations.py full_draft.md --db literature_db.csv --notes-dir reading_notes/` |

该脚本自动化验证流程中可机械执行的层级（证据库交叉比对、PubMed/Crossref API 验证、参考文献完整性检查），将人工审核范围缩小到 WARN/FAIL 项。

## 更新状态

```json
{
  "current_skill": "07B_citation_verify",
  "phases": {
    "4_writing": {"status": "completed", "skills": {"07_chapter_writing": "completed", "07B_citation_verify": "completed"}},
    "5_journal": {"status": "in_progress"}
  },
  "files": {
    "citation_verification_report": "literature-review/citation_verification_report.md"
  },
  "verification_summary": {
    "total_citations": N,
    "passed": X,
    "warned": Y,
    "failed": Z,
    "verdict": "pass|conditional_pass|fail"
  }
}
```
