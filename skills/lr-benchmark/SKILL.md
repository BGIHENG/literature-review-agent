---
name: lr-benchmark
description: 文献综述对标库学习。当 SCI 综述项目初始化后，需要学习高水平同类综述的框架、语言、图表策略时触发。搜索 3-5 篇最相关的高影响力综述，深度分析其结构/论证/图表/语言特点，产出 benchmark_report.md。对 SCI 综述为强制步骤，对中文核心综述为可选步骤。当用户说"对标学习""学高水平综述""找参考综述"时触发。
agent_created: true
---

# 文献综述 — Step 1B: 对标库学习

## 概述

"写综述之前，先读最好的综述。" 搜索 3-5 篇与你的选题最相关、发表在目标期刊级别或更高水平上的综述文章，深度学习：

1. **框架策略**：它们如何组织章节、论证逻辑如何演进
2. **语言质感**：SCI 综述的惯用句式、术语密度、段落节奏
3. **图表策略**：用了什么类型的图表、图表如何与文字互动
4. **论证深度**：是综述文献还是提出批判性观点
5. **创新模式**：这些综述在哪些维度上做了创新

这一步的目的不是抄袭，而是建立"好的综述长什么样"的认知基准。

## 前置条件

- 已完成 `lr-project-init`，存在 `project_brief.md`
- `project_status.json` 中 `language = "en_US"`（SCI 模式必走，中文可选）
- 已知选题关键词和研究范围

## 产出文件

### benchmark_report.md

```markdown
# 对标库学习报告

## 检索策略
- 数据库: [PubMed / Web of Science / Google Scholar]
- 检索词: [关键词组合]
- 筛选标准: [影响因子 > X / 近 3 年 / 综述类型]

## 对标文献清单

| # | 标题 | 期刊/IF | 年份 | 引用数 | 入选理由 |
|---|------|---------|------|--------|----------|
| 1 | ... | Nature Reviews Cancer / 78.5 | 2025 | 340 | 最全面的 CRC TME 综述 |
| 2 | ... | Cancer Cell / 48.8 | 2024 | 210 | 技术视角，与你角度最接近 |
| 3 | ... | Trends in Cancer / 14.3 | 2025 | 85 | 图表策略最佳 |
| 4 | ... | Journal of Hematology & Oncology / 23.4 | 2024 | 150 | 机制讨论最深入 |
| 5 | ... | Signal Transduction and Targeted Therapy / 39.3 | 2026 | 60 | 最新发表，时效性最强 |

## 框架分析

### 对标综述 1 的章节结构
1. Introduction (800 words)
2. Cellular landscape of CRC TME (2500 words)
3. Spatial architecture and immune niches (2500 words)
4. TME reprogramming in drug resistance (2000 words)
5. Therapeutic implications (1500 words)
6. Concluding remarks (500 words)

**可借鉴之处：**
- 每章以 2-3 个关键问题开篇
- 每章末有 Box（Key Points）
- 第 3 章和第 4 章之间有逻辑递进（空间→功能→转化）

### 对标综述 2 的论证策略
...

## 语言分析

### 常用句式提炼

| 功能 | 对标句式 | 可复用度 |
|------|----------|----------|
| 指出空白 | "However, the spatial organization of ... remains poorly characterized." | ⭐⭐⭐ |
| 过渡 | "Building on these single-cell insights, recent advances in ... have enabled ..." | ⭐⭐⭐ |
| 批判 | "While these studies provide valuable ..., they are limited by ..." | ⭐⭐ |
| 展望 | "Future studies integrating ... with ... will be critical to ..." | ⭐⭐⭐ |

### 术语密度分析
- 对标 1: 每千字引入 ~15 个专业术语（缩写+全称）
- 对标 2: 每千字引入 ~12 个专业术语
- **建议:** 控制在每千字 12-18 个术语

## 图表策略分析

| 图表类型 | 对标 1 | 对标 2 | 对标 3 | 使用建议 |
|----------|--------|--------|--------|----------|
| 机制示意图 | ✅ 2 张 | ✅ 3 张 | ✅ 1 张 | 核心工具，必须画 |
| 对比表 | ✅ 3 张 | ✅ 1 张 | ✅ 4 张 | 汇总文献极佳 |
| 数据整合图 | ✅ 1 张 | ✅ 0 | ✅ 1 张 | 可选项 |
| Timeline | ✅ 1 张 | ✅ 0 | ✅ 1 张 | 展示领域进展 |
| Graphical Abstract | ✅ | ✅ | ❌ | SCI 期刊普遍要求 |

## 差异化空间确认

| 维度 | 对标覆盖情况 | 本综述差异化策略 |
|------|-------------|------------------|
| scRNA-seq CRC 细胞图谱 | 全覆盖 | 聚焦 2024-2026 最新发现 |
| 空间组学 CRC 应用 | 部分覆盖 | **主攻方向 — 最新 ST 技术** |
| 耐药机制 | 覆盖但浅 | **深度整合 scRNA-seq + ST 联合分析** |
| 免疫治疗预测 | 几乎未覆盖 | **新增独立章节** |

## 行动清单
- [ ] 采用"Key Questions"开篇策略（对标 1）
- [ ] 每章增加一个 Summary Box
- [ ] 设计 6-7 张示意图（对标平均 5 张基础上 +1）
- [ ] 准备 Graphical Abstract 草图
- [ ] 避免仅罗列文献——加入批判性讨论（对标 2 策略）
- [ ] 参考文献目标 100-150 篇（对标平均水平）
```

## 执行步骤

### 1. 搜索对标文献

在 PubMed / Web of Science / Google Scholar 中搜索：

**搜索策略：**
```
(核心关键词) AND (review[pt] OR "review"[ti])
Filters: 近 3 年, English
排序: 引用次数 或 相关性
```

**筛选标准：**
- 期刊影响因子 ≥ 目标期刊水平
- 主题重叠度 > 50%
- 优先选择 Nature Reviews / Trends in / Annual Review 系列
- 选择 3-5 篇（覆盖不同侧重点）

### 2. 深度阅读对标文献

对每篇对标文献：
- 阅读全文（不仅是摘要）
- 绘制其章节结构图
- 标注关键论点和论据
- 记录图表使用情况
- 提取有代表性的句式

### 3. 框架分析

对比多篇对标文献的章节结构：
- 找出共同模式（如 Introduction → Landscape → Mechanisms → Clinical → Future）
- 标注每篇的独特之处（如 Box、Timeline）
- 提炼可借鉴的结构元素

### 4. 语言分析

提取对标文献中的高频句式：
- **指出空白**：However, ... remains poorly understood / ... has not been systematically investigated
- **过渡句**：Building on ..., ... have recently ...
- **批判句**：Although ..., these studies are limited by ...
- **展望句**：Future studies ... will be essential to ...

### 5. 图表策略分析

统计对标文献的图表使用：
- 图的数量和类型（示意图/数据图/流程图）
- 表的数量和使用方式
- 评估哪些图表策略适合你的综述

### 6. 差异化空间确认

这是最关键的一步——确认你的综述能提供什么新价值：
- 列出对标综述已覆盖的主题
- 找出未覆盖或覆盖不足的主题
- 确认你的差异化策略

**如果没有明显差异化空间**：回到 Step 01 调整选题角度。

### 7. 生成行动清单

将对标学习的结果转化为具体的写作行动清单，指导后续的框架搭建和写作。

## 质量检查

- [ ] 是否搜索了至少 2 个数据库？
- [ ] 是否选择了 3-5 篇高水平对标综述？
- [ ] 对标综述的期刊水平是否 ≥ 目标期刊？
- [ ] 是否分析了框架/语言/图表三个维度？
- [ ] 是否确认了差异化空间？
- [ ] 是否生成了可执行的行动清单？
- [ ] 如果没有差异化空间，是否已回溯到选题阶段调整？

## 更新状态

完成后更新 `project_status.json`：
```json
{
  "current_skill": "01B_benchmark",
  "phases": {
    "1_protocol": {
      "skills": {"01_project_init": "completed", "01B_benchmark": "completed"}
    }
  },
  "files": {
    "benchmark_report": "literature-review/benchmark_report.md"
  }
}
```
