---
name: lr-pipeline
description: 文献综述 Agent 总控调度器 v2。当用户需要撰写学术文献综述（中英文、SCI/中文核心，临床科研方向或基础科学方向）时触发此 skill。负责扫描项目目录判断当前进度、确定下一步应调用的子 skill、管理项目状态文件。覆盖从选题到投稿返修的完整 6 阶段流程，包含 16 个技能（lr-project-init / lr-benchmark / lr-search-strategy / lr-pubmed-search / lr-literature-screen / lr-zotero-import / lr-reading-notes / lr-framework / lr-chapter-writing / lr-citation-verify / lr-figure-maker / lr-journal-select / lr-polish / lr-cover-letter / lr-reviewer-response / 外加 lr-pipeline 自身）。支持中文核心期刊和 SCI 英文期刊双轨输出。当用户说"开始写综述""继续综述""下一步""写SCI综述"时触发。
agent_created: true
---

# 文献综述 Agent — 总控调度器 v2

## 概述

将文献综述拆解为 **16 个独立技能**，覆盖 **6 个阶段**（选题协议 → 对标学习 → 证据库构建 → 框架搭建 → 分章写作与引用验证 → 期刊适配与投稿返修）。步骤间通过项目文件（Markdown + CSV + JSON）传递产物，而非对话记忆。总控调度器负责判断当前进度、调度下一步。

**v2 新特性：**
- 支持中英双语综述（zh_CN / en_US），通过 `project_status.json` 中的 `language` 字段路由
- 新增 7 个扩展技能（对标学习、Zotero集成、期刊选择、图表生成、润色、投稿信、审稿回复）
- 阶段 5-6（期刊适配与投稿返修）固化为第一梯队技能，不再靠手工流程
- 支持多数据库检索（PubMed / Web of Science / Scopus / CNKI）
- 对标库学习环节提升写作起点质量
- Zotero 集成支持 RIS 批量导入、题录校验和 PDF 获取追踪

## 项目文件结构

```
literature-review/
├── project_brief.md          # Phase 1 产出：选题协议（PICO、大纲、纳入排除标准）
├── project_status.json       # 贯穿全程：项目状态跟踪
├── benchmark_report.md       # Phase 1B 产出：对标库学习报告（SCI模式推荐）
├── search_strategy.md        # Phase 2 产出：多数据库检索式文档
├── literature_db.csv         # Phase 2 产出：文献库（去重、标注优先级和章节）
├── screened_literature.csv   # Phase 2 产出：筛选后文献（纳入/排除判定）
├── zotero_import.ris         # Phase 2 产出：Zotero RIS 导入文件（可选）
├── zotero_collections.md     # Phase 2 产出：Zotero 集合结构说明
├── zotero_metadata_report.md # Phase 2 产出：题录完整性校验报告
├── zotero_pdf_status.csv     # Phase 2 产出：PDF 获取状态追踪
├── reading_notes/            # Phase 2 产出：精读笔记目录
│   ├── PMID_xxxxx.md
│   └── INDEX.md
├── framework.md              # Phase 3 产出：综述框架（章节结构 + 逻辑链 + 图表规划）
├── manuscript/               # Phase 4 产出：初稿
│   ├── full_draft.md         #   全文初稿
│   └── chX_xxx.md            #   分章文件
├── citation_verification_report.md  # Phase 4B 产出：引用验证报告（防幻觉门禁）
├── figures/                  # Phase 5 产出：图表文件
│   ├── figure_*.svg/png
│   └── table_*.md
├── polished/                 # Phase 5 产出：润色稿
│   └── polished_draft.md
├── cover_letter.md           # Phase 5 产出：投稿信
├── journal_match.md          # Phase 5 产出：期刊匹配报告
├── submission_ready.docx     # Phase 5 产出：投稿就绪稿
├── reviewer_comments.md      # Phase 6 产出：审稿意见（模拟或真实）
├── rebuttal_letter.md        # Phase 6 产出：回复信
└── revised_manuscript.docx   # Phase 6 产出：修订稿
```

## 6 阶段 15 技能完整流程

### 阶段 1：选题协议（Protocol Design）

| ID | Skill | 功能 | 输入 | 输出 | 中/英 |
|----|-------|------|------|------|-------|
| 01 | lr-project-init | 确定综述类型、选题、语言、PICO 框架、章节大纲、纳入排除标准 | 用户研究方向 | project_brief.md + project_status.json | 通用 |
| 01B | lr-benchmark | 搜索 3-5 篇高水平同类综述，深度学习其框架/语言/图表策略 | project_brief.md | benchmark_report.md | SCI 推荐，中文可选 |

### 阶段 2：证据库构建（Evidence Building）

| ID | Skill | 功能 | 输入 | 输出 | 中/英 |
|----|-------|------|------|------|-------|
| 02 | lr-search-strategy | 按 PICO 和章节设计多数据库检索式（PubMed/WoS/Scopus/CNKI） | project_brief.md | search_strategy.md | 通用 |
| 03 | lr-pubmed-search | 执行检索、去重、自动标注优先级和章节归属 | search_strategy.md | literature_db.csv | 通用（支持多DB） |
| 04 | lr-literature-screen | 两轮筛选：标题摘要筛选 + 精细筛选，收敛到 50-80 篇精读清单 | literature_db.csv | screened_literature.csv + reading_list.md | 通用 |
| 04B | lr-zotero-import | 将精读清单导入 Zotero，创建分层集合，获取 PDF 全文，校验题录完整性 | screened_literature.csv | zotero_import.ris + zotero_metadata_report.md + zotero_pdf_status.csv | SCI 推荐，中文可选 |
| 05 | lr-reading-notes | 结构化精读笔记，提取研究设计、核心发现、技术细节、与综述关联 | screened_literature.csv | reading_notes/PMID_*.md + INDEX.md | 通用 |

### 阶段 3：框架搭建（Framework）

| ID | Skill | 功能 | 输入 | 输出 | 中/英 |
|----|-------|------|------|------|-------|
| 06 | lr-framework | 提炼论点树、设计章间逻辑链、识别矛盾论点并预设讨论方案、规划图表和字数 | reading_notes/ + project_brief.md + benchmark_report.md | framework.md | 通用 |

### 阶段 4：分章写作（Chapter Writing）

| ID | Skill | 功能 | 输入 | 输出 | 中/英 |
|----|-------|------|------|------|-------|
| 07 | lr-chapter-writing | 按论点树逐章撰写初稿，支持中英双语 | framework.md + reading_notes/ | manuscript/*.md → full_draft.md | 通用 |
| 07B | lr-citation-verify | 7 层引用验证（证据库比对、PubMed API、Crossref DOI、Google 搜索、数据点溯源、参考文献完整性、幻觉标记扫描） | full_draft.md + literature_db.csv + reading_notes/ | citation_verification_report.md | 通用 |

### 阶段 5：期刊适配（Journal Adaptation）

| ID | Skill | 功能 | 输入 | 输出 | 中/英 |
|----|-------|------|------|------|-------|
| 08 | lr-figure-maker | 根据框架中的图表规划，自动生成符合目标期刊规范的示意图和汇总表 | framework.md + full_draft.md | figures/ + 嵌入表格 | SCI 必走，中文推荐 |
| 09 | lr-journal-select | 根据综述主题、方法严谨度、创新程度、语言，推荐目标期刊 | project_brief.md + full_draft.md | journal_match.md | SCI 必走，中文可选 |
| 10 | lr-polish | 语言流畅性优化、术语一致性检查、学术规范性提升 | full_draft.md + journal_match.md | polished/polished_draft.md | 通用 |
| 11 | lr-cover-letter | 根据目标期刊要求生成 Cover Letter / 投稿信 | polished_draft.md + journal_match.md | cover_letter.md | SCI 必走 |

### 阶段 6：投稿返修（Submission & Revision）

| ID | Skill | 功能 | 输入 | 输出 | 中/英 |
|----|-------|------|------|------|-------|
| 12 | lr-reviewer-response | 模拟审稿意见生成、逐条回复策略、修改记录追踪、拒稿改投预案 | submission_ready.docx | reviewer_comments.md + rebuttal_letter.md + revised_manuscript.docx | 通用 |

## 双语路由规则

Pipeline 通过 `project_status.json` 中的 `language` 字段自动适配：

| 参数 | zh_CN（中文核心） | en_US（SCI） |
|------|-------------------|--------------|
| 对标库学习 (01B) | 可选（通常跳过） | **强制** |
| 图表生成 (08) | 推荐但简化 | **强制**（需满足期刊分辨率/DOCX嵌入） |
| 期刊选择 (09) | 可选（手工选即可） | **强制**（需系统匹配 IF/分区/审稿周期） |
| 投稿信 (11) | 可选 | **强制** |
| 审稿回复 (12) | 走模拟审稿 | 走模拟审稿（可接真实审稿意见） |
| 引用格式 | GB/T 7714-2015 | Vancouver / APA / 期刊指定格式 |
| 写作风格 | 中文学术（术语首见注英文） | 英文学术（被动语态、SCI地道表达） |
| 数据库优先级 | PubMed + CNKI | PubMed + Web of Science + Scopus |

## 调度逻辑

### 判断当前进度

读取 `project_status.json`，确定下一步：

```json
{
  "project_name": "单细胞与空间转录组在CRC免疫微环境中的应用进展",
  "review_type": "narrative_review",
  "language": "zh_CN",
  "target_journal_type": "chinese_core",
  "current_phase": 2,
  "current_skill": "03_pubmed_search",
  "status": "in_progress",
  "created_at": "2026-07-28",
  "last_updated": "2026-07-28",
  "phases": {
    "1_protocol": {
      "status": "completed",
      "skills": {
        "01_project_init": "completed",
        "01B_benchmark": "skipped"
      }
    },
    "2_evidence": {
      "status": "in_progress",
      "skills": {
        "02_search_strategy": "completed",
        "03_pubmed_search": "in_progress"
      }
    },
    "3_framework": {"status": "pending", "skills": {}},
    "4_writing": {"status": "pending", "skills": {"07_chapter_writing": "pending", "07B_citation_verify": "pending"}},
    "5_journal": {"status": "pending", "skills": {}},
    "6_submission": {"status": "pending", "skills": {}}
  },
  "decision_log": [],
  "backtrack_log": [],
  "files": {
    "project_brief": "literature-review/project_brief.md",
    "benchmark_report": null,
    "search_strategy": "literature-review/search_strategy.md",
    "literature_db": null,
    "screened_literature": null,
    "zotero_import_ris": null,
    "zotero_metadata_report": null,
    "zotero_pdf_status": null,
    "reading_list": null,
    "reading_notes": null,
    "framework": null,
    "manuscript": null,
    "citation_verification_report": null,
    "figures": null,
    "polished": null,
    "cover_letter": null,
    "submission_ready": null,
    "reviewer_comments": null,
    "rebuttal_letter": null
  }
}
```

### 调度规则

1. 如果 `status` 为 `"completed"` → 综述已完成，询问用户是否需要修改
2. 找到 `current_skill` 在流程表中下一个步骤，考虑 `language` 路由规则（zh_CN 跳过 01B、09、11；en_US 走全流程）
3. 如果下一个 skill 的前置文件已存在 → 确认用户是否跳过
4. 如果当前 phase 的 status 为 `"in_progress"` 但所有 skills 已完成 → 自动推进到下一 phase

### 技能路由顺序

```
01_project_init
  ├─ en_US → 01B_benchmark (强制)
  └─ zh_CN → 跳过 01B → 02_search_strategy
02_search_strategy
03_pubmed_search
04_literature_screen
  ├─ en_US → 04B_zotero_import (推荐)
  └─ zh_CN → 04B_zotero_import (可选)
05_reading_notes
06_framework
07_chapter_writing
07B_citation_verify (防幻觉硬门禁)
  ├─ en_US → 08_figure_maker → 09_journal_select → 10_polish → 11_cover_letter → 12_reviewer_response
  └─ zh_CN → 08_figure_maker(可选) → 10_polish → 12_reviewer_response
```

### 从任意节点切入

如果用户已有部分产物，可跳过前置步骤：

| 已有产物 | 从何开始 | 需要什么 |
|----------|----------|----------|
| 已有明确选题+语言+期刊目标 | Step 01（项目初始化，补充缺失参数） | 无 |
| 已有 project_brief.md | Step 01B（SCI）或 Step 02（中文） | project_brief.md |
| 已有 literature_db.csv | Step 04（文献筛选） | literature_db.csv + project_brief.md |
| 已有 reading_notes/ | Step 06（框架搭建） | reading_notes/ + INDEX.md |
| 已有 full_draft.md | Step 07B（引用验证） | full_draft.md + literature_db.csv + reading_notes/ |
| 已有 full_draft.md 且验证通过 | Phase 5（期刊适配） | full_draft.md + project_brief.md |
| 已有完整稿件需润色 | Step 10（润色） | full_draft.md |
| 收到审稿意见需回复 | Step 12（审稿回复） | submission_ready.docx + reviewer comments |

### 回溯机制

回溯在 `project_status.json` 的 `backtrack_log` 中记录原因和范围，避免重复回溯：

| 触发场景 | 回退到 | 最小修复范围 |
|----------|--------|-------------|
| 引用验证发现幻觉引用（Google 搜不到） | Step 07（修复初稿） | 删除或替换虚假引用，仅修受影响段落 |
| 引用验证发现数据点无法追溯 | Step 05（精读笔记） | 回去精读原文核实数据 |
| 写作时发现论点缺支撑 | Step 06（调整框架） | 调整论点树，不盲目补充检索 |
| 框架时发现某章证据链断裂 | Step 05（补几篇精读） | 只补缺口章节的精读 |
| 精读时发现某章核心文献 < 5 篇 | Step 03（补充检索） | 新增补充检索式，不全量重搜 |
| 检索时发现选题过宽/过窄 | Step 01（重新收敛选题） | 修改 PICO 参数，不重做全流程 |
| 润色时发现语言/结构不符合期刊 | Step 09（重新匹配期刊） | 换刊或深度修改 |

## 综述类型与步骤裁剪

| 综述类型 | 必走步骤 | 可跳过 | 语言推荐 |
|----------|----------|--------|----------|
| 叙述性综述（初学者首选） | 全部核心步骤 | 质量评估（RoB）、GRADE 分级、01B(中文) | 中/英均可 |
| 系统综述 | 全部 14 步 + 质量评估 + 证据综合 | 无 | 英文(SCI)推荐 |
| 范围综述 | 01, 02-05, 06-07, 09-10 | 质量评估、01B(可选) | 中/英均可 |
| 伞形综述 | 01, 02-05, 06-07, 09-12 | 01B(可选) | 英文(SCI)推荐 |

## 质量底线（不可逾越）

1. **引用可验证**：每条引用必须经过 lr-citation-verify 验证，确保可在 PubMed/Google 检索到
2. **证据可追溯**：每条论断必须可回到具体文献和精读笔记
3. **缺失标记**：不确定的内容标注"需人工核查"
4. **动态核验**：临床指南、药物适应症等动态信息实时核验
5. **不改原意**：不改变文献的科学含义
6. **推测区分**：推测性内容不写成事实
7. **AI 边界**：AI 辅助写作，不代替作者承担学术责任
8. **语言适配**：中文综述术语首次出现标注英文；英文综述使用地道 SCI 表达
9. **防幻觉门禁**：初稿完成后必须通过 lr-citation-verify 7 层验证方可进入润色
10. **全文阅读升级**：推荐在精读阶段运行 download_oa_pdfs.py → pdf_reader.py → batch_enrich.py 三阶段流水线，将摘要级笔记升级为全文级笔记

## 使用方式

当用户开始或继续一篇文献综述时：

1. 读取 `project_status.json` 判断当前进度
2. 如果是新项目，询问用户目标语言（zh_CN / en_US），从 `lr-project-init` 开始
3. 如果是继续，根据 `language` 路由规则调用对应的子 skill
4. 每步完成后更新 `project_status.json`
5. 向用户报告进度并确认下一步

### 典型启动对话

**新项目（中文核心）：**
> 用户："帮我写一篇关于XXX的综述"
> Pipeline：加载 lr-project-init，询问语言→中文，走 zh_CN 路由

**新项目（SCI）：**
> 用户："帮我写一篇 SCI 综述，关于XXX"
> Pipeline：加载 lr-project-init，语言→en_US，走完整 14 步流程

**继续已有项目：**
> 用户："继续我的综述"
> Pipeline：读取 project_status.json，从 current_skill 的下一步继续
