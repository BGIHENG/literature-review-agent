---
name: lr-zotero-import
description: 文献综述 Zotero 文献导入器。当用户已有 screened_literature.csv（精读清单），需要将文献批量导入 Zotero、创建分层集合、获取 PDF 全文、校验题录完整性时触发。支持中文核心和 SCI 项目，生成 RIS 通用导入文件，支持 Zotero Web API 自动导入（推荐）、Better BibTeX 本地导入、手动 RIS 导入三种方式。当用户说"导入Zotero""导入文献管理器""获取PDF""Zotero集成""同步到Zotero"时触发。
agent_created: true
---

# 文献综述 — Zotero 文献导入

## 概述

将 `screened_literature.csv` 中纳入的文献（ScreenStatus = included）批量导入 Zotero，自动创建按章节分层的集合结构，尝试获取 PDF 全文，输出题录完整性校验报告。

## 在 Pipeline 中的位置

```
lr-literature-screen (04)
    ↓
lr-zotero-import (04B)  ← 可选步骤，SCI 项目推荐
    ↓
lr-reading-notes (05)
```

**路由规则：**
- SCI 项目（en_US）：推荐执行，PDF 全文对英文精读不可或缺
- 中文核心（zh_CN）：可选执行，中文文献 PDF 获取可能受限

**执行时机：** 精读笔记之前。先有 PDF 全文再做精读，比"看摘要猜全文"可靠得多。

## 前置条件

- 已完成 `lr-literature-screen`，存在 `screened_literature.csv`
- 确认 `screened_literature.csv` 中 ScreenStatus = included 的文献数量（目标 50-80 篇）
- Zotero 客户端已安装（桌面版 v6/v7），建议安装 Better BibTeX 插件
- 如需自动导入，Zotero 需在运行状态且开启"允许其他应用访问"（Preferences → Advanced → Allow）

## 产出文件

| 文件 | 说明 |
|------|------|
| `zotero_import.ris` | 通用 RIS 导入文件，可直接拖入 Zotero |
| `zotero_collections.md` | Zotero 集合结构说明 + 手动导入操作指南 |
| `zotero_metadata_report.md` | 题录完整性校验报告（缺失 DOI/摘要/卷期的条目清单） |
| `zotero_pdf_status.csv` | PDF 获取状态追踪（已获取/未获取/无权限/无全文） |

## 执行步骤

### 1. 读取精读清单

从 `screened_literature.csv` 中取出所有 `ScreenStatus = included` 的条目。

### 2. 生成 RIS 导入文件

RIS (Research Information Systems) 是 Zotero 最稳定的通用导入格式。按以下规范生成：

```
TY  - JOUR
TI  - {完整标题}
AU  - LastName, FirstName
PY  - 2024
JO  - Journal Full Name
VL  - 12
IS  - 3
SP  - 456
EP  - 467
DO  - 10.xxxx/xxxxx
UR  - https://doi.org/10.xxxx/xxxxx
AB  - {完整摘要}
N1  - Priority: P1 | Chapter: Ch2_scRNA | SourceDB: PubMed
KW  - keyword1; keyword2
ER  - 

```

**字段映射表（screened_literature.csv → RIS）：**

| CSV 字段 | RIS 标签 | 说明 |
|----------|----------|------|
| Title | `TI` | 花括号包裹防转义 |
| FirstAuthor | `AU` | 需补全全名（CSV 可能只存姓）；缺全名时用 "Unknown, A." 占位 |
| Year | `PY` | 年份 |
| Journal | `JO` | 期刊全称 |
| Volume / Issue | `VL` / `IS` | 卷期 |
| Pages | `SP` – `EP` | 页起止（如 CSV 仅有单值则只填 SP） |
| DOI | `DO` | 同时生成 `UR` 字段（https://doi.org/{DOI}） |
| Abstract | `AB` | 完整摘要 |
| Priority + Chapter + SourceDB | `N1` | 合并为 Zotero 笔记，便于在 Zotero 内看到章节归属 |

**作者字段处理：**

如果 CSV 中只有 FirstAuthor（姓），用 Zotero 的默认格式：
```
AU  - {FirstAuthor}
```
Zotero 会在导入时尝试从 DOI / PMID 补全完整作者列表。

**注意事项：**
- 文件编码：UTF-8（不带 BOM），Zotero 能正确识别中文标题
- 标签：`KW` 字段可选，填入章节关键词便于 Zotero 内搜索
- PMID 处理：如果 CSV 有 PMID，RIS 标准中可放入 `M1` 字段，或通过 `UR` 提供 PubMed 链接

### 3. 设计 Zotero 集合结构

基于 `project_brief.md` 的章节大纲，建议以下集合层级：

```
{项目名}/
├── 01_精读_High/          ← ReadPriority = high 的文献
│   ├── Ch2_XXX主题/
│   ├── Ch3_XXX主题/
│   └── ...
├── 02_精读_Medium/        ← ReadPriority = medium 的文献
│   ├── Ch2_XXX主题/
│   └── ...
├── 03_补充_Low/           ← ReadPriority = low 的文献
└── 04_方法学参考/
```

**分层原因：**
- 精读时按优先级递减，先啃高优先级的
- 按章节分组，写作时快速召回对应论点的支撑文献
- 方法学参考独立一区，不用打散到各章

### 4. 尝试自动导入（如果 Zotero API 可用）

如果 Zotero 本地 HTTP 服务在运行（默认端口 23119），可通过以下方式尝试自动导入：

#### 4.1 检测 Zotero 是否运行

```
GET http://localhost:23119/connector/ping
```
若返回 200，说明 Zotero 在线且允许外部访问。

#### 4.2 使用 Better BibTeX 自动导入

如果安装了 Better BibTeX 插件：
```
POST http://localhost:23119/better-bibtex/import
Content-Type: application/x-research-info-systems
Body: RIS 文件内容
```

#### 4.3 使用 Zotero Web API（推荐自动导入方案）

**脚本：** `scripts/zotero_web_import.py`

通过 Zotero Web API v3 批量导入，无需安装任何插件，只需 API Key。

**凭证获取：**
1. 前往 https://www.zotero.org/settings/keys
2. 页面顶部显示 User ID
3. 点击 "Create new private key"
   - 勾选 Allow library access + Allow write access
4. 将 User ID 和 API Key 传入脚本

**用法：**
```bash
# 交互式输入凭证（推荐，API Key 不会留在 shell 历史中）：
python scripts/zotero_web_import.py screened_literature.csv \
    --collection-name "CRC scRNA Review"

# 传参方式（不推荐，API Key 会留在 shell 历史）：
python scripts/zotero_web_import.py screened_literature.csv \
    --user-id 12345678 \
    --api-key AbCdEfGhIjKlMnOp \
    --collection-name "CRC scRNA Review"

# 预览模式（无需凭证）：
python scripts/zotero_web_import.py screened_literature.csv --dry-run
```

**脚本能力：**
- 自动验证 API Key 权限（write access 检查）
- 创建 Zotero 集合（含同名去重）
- CSV → Zotero Item JSON 格式转换（含作者/DOI/PMID/章节标签）
- 批量上传（每批 50 条，符合 Zotero API 限制）
- 可选附加 PDF（三步上传：注册→S3→完成确认）
- 429/502/503 自动重试 + backoff 处理
- 输出导入报告 Markdown + Zotero 集合链接
- 支持 `--dry-run` 预览模式

**Web API v3 实战要点（2026-09 实测踩坑记录）：**

1. **写接口响应格式**：POST /collections、POST /items 返回 **HTTP 200** + `{"successful": {"0": {"key": "XXXX", "version": N, ...}}, "failed": {...}}`，**不是** 201 + 裸数组。解析必须按 `successful`/`failed` 两个 map 处理（旧版客户端/文档示例常写 201+数组，会误判失败）。
2. **API Key 权限**：未勾选 "Allow write access" 时，GET 一切正常但任何 POST/PATCH 返回 **403 "Write access denied"**（此前极易被误诊为"凭证无效"）。必须先做一次轻量写探测（如 POST 空集合或检查 key 权限）。
3. **PATCH /items/<key> 更新字段（如 collections）**：必须带 **`If-Unmodified-Since-Version: <version>` 请求头**（或 body 带 version），否则返回 **428**。先 `GET /items?itemKey=k1,k2,...&format=json` 批量取 version 再逐个 PATCH。
4. **不要把条目只放进叶子集合**：Zotero 集合层级**不自动传递条目**——条目放进子集合后，父集合/顶层点击显示 0 条，用户会误以为导入失败。若需顶层可见，把父集合 key 一并写入该条目的 `collections` 数组（条目可属多个集合，互不排斥）。
5. **POST /collections/<key>/items**（批量加条目到集合的快捷接口）在个人用户库上实测返回 **500**，不可依赖；改用方案 3 的逐条 PATCH。
6. **幂等设计**：重跑前先 GET 全库分页收集 DOI → 与待导入条目比对去重；GET collections 按 `parentCollection + '/' + name` 建 key 映射，已存在则复用（同一 name 允许出现在不同父级下，勿只按 name 匹配）。
7. 每次写操作间 sleep ≥ 0.3–0.6 s，避免触发限流（429 时按 Retry-After/退避重试 ≤3 次）。

#### 4.4 降级策略

| 情况 | 操作 |
|------|------|
| 无 Zotero API Key | 生成 RIS 文件，用户手动 File → Import |
| API Key 无 write 权限 | 提示用户重新创建 Key 并勾选 write access |
| Zotero 未运行 | Web API 导入后，下次打开 Zotero 自动同步 |
| API 限流 (429) | 脚本自动等待重试（最多 3 次） |

**安全提示：** 不存储 API Key 到文件。如果用户提供 Key，只在本次对话中使用。

### 5. PDF 全文获取

#### 5.1 Zotero 内置 PDF 获取

导入文献后，Zotero 支持"Find Available PDF"功能：
- 选中文献 → 右键 → Find Available PDF
- Zotero 会通过 Unpaywall、机构代理、开放获取等渠道尝试获取

**限制：**
- 需要机构订阅或开放获取（OA）
- 中文文献 PDF 获取成功率较低
- 付费墙后的全文通常无法自动获取

#### 5.2 辅助策略

| 策略 | 适用场景 | 说明 |
|------|----------|------|
| Unpaywall API | 英文文献 | 通过 unpaywall.org 查询 OA 版本 |
| PubMed Central | 英文文献 | PMID 对应 PMC ID，PMC 全文免费 |
| Sci-Hub（提示） | 英文文献 | 告知用户可手动访问（AI 不直接调用） |
| CNKI 下载 | 中文文献 | 需机构订阅或个人账号，AI 无法自动获取 |
| Google Scholar | 通用 | 搜索 DOI 可能找到 PDF 链接 |

#### 5.3 输出 PDF 状态报告

在 `zotero_pdf_status.csv` 中记录每篇文献的 PDF 获取状态：

```csv
PMID,DOI,Title,PDF_Status,Note
12345678,10.xxx/xxx,Single-cell atlas of...,auto_found,PMC free
23456789,10.xxx/yyy,Another paper...,manual_needed,付费墙 - 可尝试Sci-Hub
```

**状态值：** `auto_found` / `manual_needed` / `no_fulltext` / `oa_available`

### 6. 题录完整性校验

检查以下字段的缺失情况，生成 `zotero_metadata_report.md`：

| 检查项 | 严重程度 | 修复建议 |
|--------|----------|----------|
| DOI 缺失 | ⚠️ 高 | 通过 PMID → PubMed 搜索补全；或用 Crossref API 匹配 |
| 摘要缺失 | ⚠️ 中 | 通过 PMID → PubMed efetch 补全 |
| 期刊全称缺失 | ⚠️ 中 | 通过 ISSN/缩写 → NLM Catalog 补全 |
| 卷/期/页缺失 | 🔵 低 | 导入 Zotero 后用 DOI 自动补全 |
| 作者仅 FirstAuthor | 🔵 低 | Zotero 导入后通过 DOI 自动补全 |
| 章节归属为空 | 🔵 低 | 根据标题关键词自动补标 |

### 7. 生成操作指南

为每个场景生成清晰的指令，放在 `zotero_collections.md`：

**手动导入流程（标准路径）：**
1. 打开 Zotero → File → Import
2. 选择 `zotero_import.ris`，文件类型选 "RIS"
3. 勾选 "Place imported collections and items into new collection"
4. 导入后按章节创建子集合，拖入对应文献

**自动导入流程（如果 Zotero API 可用）：**
1. 确认 Zotero 正在运行
2. (自动执行) 通过 API 批量导入 RIS
3. (自动执行) 创建集合结构
4. 用户验证：在 Zotero 中检查导入结果

## 质量检查

- [ ] RIS 文件是否包含所有 ScreenStatus = included 的条目？
- [ ] DOI/PMID 缺失量是否可接受（< 5%）？
- [ ] 是否有条目无法生成有效的 RIS 记录？
- [ ] 集合结构是否与 project_brief.md 的章节大纲对应？
- [ ] PDF 获取状态是否已记录？
- [ ] 题录完整性报告是否列出了所有有问题的条目？
- [ ] Web API 导入后，Zotero 集合链接是否可访问？

## Python 脚本

| 脚本 | 功能 | 用法 |
|------|------|------|
| `scripts/generate_ris.py` | CSV → RIS 格式转换 | `python generate_ris.py screened.csv --outdir ./` |
| `scripts/download_oa_pdfs.py` | Unpaywall + PMC 自动下载 OA PDF | `python download_oa_pdfs.py screened.csv --email your@email.com` |
| `scripts/zotero_web_import.py` | Zotero Web API 批量导入（推荐） | `python zotero_web_import.py screened.csv --user-id ID --api-key KEY` |
| `scripts/pdf_reader.py` | PDF 正文提取（IMRaD 结构化） | `python pdf_reader.py --pdf-dir pdfs/ --csv screened.csv` |

## 更新项目状态

完成后更新 `project_status.json`：

```json
{
  "current_skill": "04B_zotero_import",
  "phases": {
    "2_evidence": {
      "skills": {
        "04_literature_screen": "completed",
        "04B_zotero_import": "completed"
      }
    }
  },
  "files": {
    "zotero_import_ris": "literature-review/zotero_import.ris",
    "zotero_collections": "literature-review/zotero_collections.md",
    "zotero_metadata_report": "literature-review/zotero_metadata_report.md",
    "zotero_pdf_status": "literature-review/zotero_pdf_status.csv"
  }
}
```

## 注意事项

1. **版权合规：** 不绕过付费墙获取论文（Sci-Hub 仅提示，不自动调用）
2. **信息安全：** Zotero API Key 不在文件系统中持久化
3. **中文文献 PDF：** 告知用户需自行通过 CNKI/万方/机构图书馆下载，AI 无权限获取
4. **PII 不推荐批量：** Zotero "Find Available PDF" 功能批量执行可能触发出版社反爬，建议每次 10-20 篇分批
5. **机构代理：** 在校外访问付费期刊需先连接 VPN，Zotero 才能通过机构订阅获取 PDF
