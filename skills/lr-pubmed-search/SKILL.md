---
name: lr-pubmed-search
description: 多数据库文献检索执行 v2。当用户已有 search_strategy.md，需要实际执行多数据库检索并构建文献库时触发。使用各数据库 API 批量检索、跨库去重、获取文献详情，自动标注优先级和章节。支持 PubMed (E-utilities)、Web of Science、Scopus、CNKI。产出 literature_db.csv。当用户说"执行检索""搜文献""跑检索式"时触发。
agent_created: true
---

# 文献综述 — Step 3: 多数据库检索执行 v2

## 概述

根据 search_strategy.md 中的多数据库检索式，实际执行检索、批量获取文献详情、跨库去重后入库，并自动标注优先级和所属章节。

**v2 新特性：**
- 支持 Web of Science 和 Scopus 检索（除 PubMed 外）
- 跨数据库去重（DOI 为主键，PMID/WoS ID/Scopus ID 辅助）
- SCI 期刊分层体系（JCR 分区替代简单的 P1/P2/P3）
- 数据库来源标注（SourceDB 字段）

## 前置条件

- 已完成 `lr-search-strategy`，存在 `search_strategy.md`
- 可访问 PubMed E-utilities API
- SCI 项目：需有 WoS/Scopus 机构访问权限（或使用免费替代方案）

## 产出文件

### literature_db.csv

| 字段 | 说明 |
|------|------|
| PMID | PubMed 唯一标识（如来源为 PubMed） |
| WoS_ID | Web of Science 入藏号（如来源为 WoS） |
| Scopus_ID | Scopus EID（如来源为 Scopus） |
| DOI | 数字对象标识符（跨库去重主键） |
| Title | 文献标题（原始语言） |
| FirstAuthor | 第一作者姓 |
| Year | 发表年份 |
| Journal | 期刊全称 |
| JCR_Quartile | JCR 分区（Q1/Q2/Q3/Q4，SCI项目关注） |
| IF | 最新影响因子（如有） |
| Volume / Issue / Pages | 卷期页 |
| PublicationType | 文献类型（Review / Research Article 等） |
| Abstract | 摘要（完整，不截断） |
| SourceDB | 来源数据库（PubMed / WoS / Scopus / CNKI） |
| SourceQuery | 命中的检索式编号（如 Q1_TME;Q2_DrugResist） |
| Priority | P1(顶刊) / P2(权威) / P3(补充) |
| Chapter | 所属章节（如 Ch2_scRNA;Ch3_ST） |
| Note | 备注 |

## 执行步骤

### 1. 按数据库并行检索

#### PubMed（主力，所有项目）

使用 E-utilities `esearch` + `efetch` API：

```
# 检索获取 PMID 列表
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
  ?db=pubmed
  &retmax=50
  &retmode=json
  &sort=relevance
  &term=[URL编码的检索式]

# 批量获取详情
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi
  ?db=pubmed
  &id=[逗号分隔PMID列表]
  &retmode=xml
  &rettype=abstract
```

注意事项：
- `retmax` 默认 50，可根据命中量调整（最多 10000）
- 批次间隔 0.5-1s，避免触发速率限制
- 摘要不要截断，保存完整内容

#### Web of Science（SCI 项目主力）

WoS 没有免费 API，有以下替代方案：

**方案 A（有机构订阅）：** 使用 WoS API / WoS Starter API
**方案 B（无机构订阅）：** 通过 Google Scholar 或 Dimensions.ai 替代
**方案 C（推荐）：** 在 PubMed 检索中以 `journal` 字段过滤高影响力期刊，弥补 WoS 的作用

```
# 在 PubMed 中用期刊过滤来模拟 WoS 核心合集
AND ("Nature"[Journal] OR "Science"[Journal] OR "Cell"[Journal] OR ...)
```

#### Scopus（SCI 项目补充）

同样需要机构订阅。替代方案同 WoS。

**推荐策略：SCI 项目以 PubMed 为主，通过期刊过滤和引用追踪来弥补 WoS/Scopus 覆盖。**

#### CNKI（中文项目）

通过 CNKI 高级检索页面或 API。

### 2. 跨数据库去重

以 DOI 为主键去重，保留 SourceDB 为多值字段：

```python
# 按 DOI 去重，合并来源数据库信息
seen_doi = {}
for record in all_records:
    doi = record['DOI']
    if doi in seen_doi:
        # 合并 SourceDB 和 SourceQuery
        seen_doi[doi]['SourceDB'] += ';' + record['SourceDB']
        seen_doi[doi]['SourceQuery'] += ';' + record['SourceQuery']
    else:
        seen_doi[doi] = record
```

### 3. 自动标注优先级

**中文项目：** 使用期刊名匹配（与 v1 相同）

**SCI 项目：** 使用 JCR 分区 + 影响因子双维度

```python
# SCI 项目优先级规则
def assign_priority_scsi(journal, if_score, jcr_q):
    if jcr_q == 'Q1' and if_score >= 10:
        return 'P1'
    elif jcr_q == 'Q1' or if_score >= 5:
        return 'P2'
    else:
        return 'P3'

# 中文项目优先级规则（与 v1 相同，期刊名匹配）
def assign_priority_zh(journal):
    if journal in TOP_JOURNALS_ZH:
        return 'P1'
    elif journal in GOOD_JOURNALS_ZH:
        return 'P2'
    else:
        return 'P3'
```

### 4. 自动标注章节

根据标题+摘要的关键词匹配（与 v1 相同逻辑，章节关键词从 project_brief.md 的大纲提取）。

**v2 改进：** 关键词从 project_brief.md 的章节大纲中动态提取，而非硬编码。

### 5. 缺口检测与补充检索

统计每章的核心文献数（P1+P2），如果某章 < 10 篇（中文）/ < 8 篇（SCI，因文献总量可能较少），触发补充检索。

### 6. 写入 CSV

使用 `utf-8-sig` 编码（带 BOM），确保 Excel 正确显示。

## 数据库不可用时的降级策略

| 场景 | 降级方案 |
|------|----------|
| WoS 不可用 | PubMed + 高影响力期刊过滤 + Google Scholar 引文追溯 |
| Scopus 不可用 | PubMed + Dimensions.ai 免费版本 |
| CNKI 不可用 | 万方医学或维普替代 |
| 全部不可用 | 仅用 PubMed（对多数生物医学选题已足够） |

## 质量检查

- [ ] 去重后文献总数是否合理（100-400 篇）？
- [ ] 每章核心文献（P1+P2）是否 >= 10 篇（中文）/ >= 8 篇（SCI）？
- [ ] 跨数据库去重是否正确（相同 DOI 不重复）？
- [ ] SourceDB 字段是否正确标注了来源？
- [ ] 摘要字段是否完整（非空率 > 90%）？
- [ ] 是否检测了章节缺口并提供了补充检索建议？

## Python 脚本

| 脚本 | 功能 | 用法 |
|------|------|------|
| `scripts/fetch_pubmed.py` | PubMed E-utilities 批量检索：ESearch → ESummary → EFetch，自动去重、标注优先级和章节归属 | `python fetch_pubmed.py search_strategy.md --outdir ./ --output literature_db.csv` |

该脚本自动化多数据库检索流程（PubMed/WoS/Scopus API 调用），生成 literature_db.csv 并自动标注 Priority 和 Chapter 字段。

## 更新状态

```json
{
  "current_skill": "03_pubmed_search",
  "phases": {
    "2_evidence": {"status": "in_progress", "skills": {"02_search_strategy": "completed", "03_pubmed_search": "completed"}}
  },
  "files": {"literature_db": "literature-review/literature_db.csv"}
}
```
