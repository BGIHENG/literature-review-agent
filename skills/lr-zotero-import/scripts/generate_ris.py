#!/usr/bin/env python3
"""
lr-zotero-import / RIS 生成器

从 screened_literature.csv 生成 Zotero 兼容的 RIS 导入文件。
同时输出题录完整性统计和 PDF 状态骨架 CSV。

用法：
    python generate_ris.py <screened_literature.csv> [--outdir <dir>]
"""

import csv
import os
import sys
import argparse
from collections import defaultdict


def safe_val(row, key, default=""):
    """安全获取 CSV 字段值，去除首尾空白"""
    v = row.get(key, "").strip()
    return v if v else default


def format_au(row):
    """格式化作者字段 —— Zotero 格式: LastName, FirstName"""
    first_author = safe_val(row, "FirstAuthor")
    if first_author:
        return first_author
    # 尝试 Authors 字段（如存在）
    authors = safe_val(row, "Authors")
    if authors:
        # 取第一作者
        return authors.split(";")[0].strip().split(",")[0].strip()
    return ""


def format_pages(row):
    """格式化页码：SP-EP 或 SP"""
    pages = safe_val(row, "Pages")
    if not pages:
        return "", ""
    if "-" in pages:
        sp, ep = pages.split("-", 1)
        return sp.strip(), ep.strip()
    # 单个页码
    return pages.strip(), ""


def ris_escape(text):
    """RIS 文本转义：用花括号包裹防止 Zotero 误解析"""
    return "{" + text + "}" if text else ""


def generate_ris(csv_path, out_dir):
    """主函数：读取 CSV → 生成 RIS 文件 → 生成报告"""

    included = []
    stats = {
        "total_included": 0,
        "missing_doi": 0,
        "missing_abstract": 0,
        "missing_journal": 0,
        "missing_volume": 0,
        "missing_issue": 0,
        "missing_pages": 0,
        "missing_author": 0,
        "missing_chapter": 0,
        "missing_year": 0,
    }

    # --- 读取 CSV ---
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            status = safe_val(row, "ScreenStatus")
            if status == "included":
                included.append(row)

    stats["total_included"] = len(included)

    if len(included) == 0:
        print("⚠️  没有找到 ScreenStatus = included 的文献，请先运行 lr-literature-screen")
        return

    # --- 生成 RIS ---
    ris_path = os.path.join(out_dir, "zotero_import.ris")
    ris_lines = []

    # 元数据条目（供 Zotero 内部使用的自定义字段）
    metadata_entries = []

    for i, row in enumerate(included, 1):
        title = safe_val(row, "Title")
        doi = safe_val(row, "DOI")
        pmid = safe_val(row, "PMID")
        year = safe_val(row, "Year")
        journal = safe_val(row, "Journal")
        volume = safe_val(row, "Volume")
        issue = safe_val(row, "Issue")
        abstract = safe_val(row, "Abstract")
        priority = safe_val(row, "ReadPriority", safe_val(row, "Priority"))
        chapter = safe_val(row, "Chapter")
        sourcedb = safe_val(row, "SourceDB", "")
        author = format_au(row)
        sp, ep = format_pages(row)

        # --- 统计缺失 ---
        if not doi:
            stats["missing_doi"] += 1
        if not abstract:
            stats["missing_abstract"] += 1
        if not journal:
            stats["missing_journal"] += 1
        if not author:
            stats["missing_author"] += 1
        if not volume:
            stats["missing_volume"] += 1
        if not issue:
            stats["missing_issue"] += 1
        if not sp:
            stats["missing_pages"] += 1
        if not chapter:
            stats["missing_chapter"] += 1
        if not year:
            stats["missing_year"] += 1

        # --- 构建 RIS 条目 ---
        lines = []
        lines.append("TY  - JOUR")
        lines.append(f"TI  - {ris_escape(title)}" if title else "TI  - {Unknown Title}")
        lines.append(f"AU  - {author}" if author else "AU  - Unknown, A.")
        if year:
            lines.append(f"PY  - {year}")
        if journal:
            lines.append(f"JO  - {journal}")
        if volume:
            lines.append(f"VL  - {volume}")
        if issue:
            lines.append(f"IS  - {issue}")
        if sp:
            lines.append(f"SP  - {sp}")
        if ep:
            lines.append(f"EP  - {ep}")
        if doi:
            lines.append(f"DO  - {doi}")
            lines.append(f"UR  - https://doi.org/{doi}")
        if pmid:
            lines.append(f"UR  - https://pubmed.ncbi.nlm.nih.gov/{pmid}")
        if abstract:
            lines.append(f"AB  - {abstract}")
        # 自定义笔记：优先级 + 章节 + 来源数据库
        note_parts = []
        if priority:
            note_parts.append(f"Priority: {priority}")
        if chapter:
            note_parts.append(f"Chapter: {chapter}")
        if sourcedb:
            note_parts.append(f"SourceDB: {sourcedb}")
        if note_parts:
            lines.append(f"N1  - {' | '.join(note_parts)}")
        lines.append("ER  - ")
        lines.append("")  # 空行分隔

        ris_lines.extend(lines)

        # 记录元数据
        metadata_entries.append({
            "index": i,
            "title": title[:60] + "..." if len(title) > 60 else title,
            "doi": doi,
            "pmid": pmid,
            "priority": priority,
            "chapter": chapter,
        })

    # --- 写入 RIS 文件 ---
    with open(ris_path, "w", encoding="utf-8") as f:
        f.write("\n".join(ris_lines))

    # --- 生成题录完整性报告 ---
    report_path = os.path.join(out_dir, "zotero_metadata_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Zotero 题录完整性校验报告\n\n")
        f.write(f"**文献总数 (included):** {stats['total_included']}\n\n")

        f.write("## 缺失统计\n\n")
        f.write("| 检查项 | 缺失数量 | 缺失比例 | 严重程度 |\n")
        f.write("|--------|----------|----------|----------|\n")

        checks = [
            ("DOI", stats["missing_doi"], "⚠️ 高"),
            ("摘要 (Abstract)", stats["missing_abstract"], "⚠️ 中"),
            ("期刊全称 (Journal)", stats["missing_journal"], "⚠️ 中"),
            ("第一作者 (FirstAuthor)", stats["missing_author"], "⚠️ 中"),
            ("年份 (Year)", stats["missing_year"], "⚠️ 中"),
            ("卷 (Volume)", stats["missing_volume"], "🔵 低"),
            ("期 (Issue)", stats["missing_issue"], "🔵 低"),
            ("页码 (Pages)", stats["missing_pages"], "🔵 低"),
            ("章节归属 (Chapter)", stats["missing_chapter"], "🔵 低"),
        ]

        for name, count, severity in checks:
            pct = f"{count / stats['total_included'] * 100:.1f}%" if stats["total_included"] > 0 else "0%"
            f.write(f"| {name} | {count} | {pct} | {severity} |\n")

        f.write("\n## 修复建议\n\n")
        if stats["missing_doi"] > 0:
            f.write("- **DOI 缺失的条目：** 导入 Zotero 后，通过 PMID 在 PubMed 补全 DOI；或使用 Crossref API (https://api.crossref.org/works) 按标题匹配\n")
        if stats["missing_abstract"] > 0:
            f.write("- **摘要缺失的条目：** 导入 Zotero 后，选中条目 → 右键 → 用PMID更新元数据；中文文献可通过CNKI/万方补全\n")
        if stats["missing_author"] > 0 or stats["missing_volume"] > 0 or stats["missing_issue"] > 0:
            f.write("- **作者/卷/期/页缺失：** Zotero 可通过 DOI 自动补全大部分元数据（右键 → Retrieve Metadata for PDF / Update Item）\n")
        if stats["missing_chapter"] > 0:
            f.write("- **章节归属为空：** 根据标题关键词在 `screened_literature.csv` 中自动补标章节\n")

    # --- 生成 PDF 状态骨架 CSV ---
    pdf_csv_path = os.path.join(out_dir, "zotero_pdf_status.csv")
    with open(pdf_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["PMID", "DOI", "Title", "PDF_Status", "Note"])
        for entry in metadata_entries:
            writer.writerow([
                entry["pmid"],
                entry["doi"],
                entry["title"],
                "",  # 留空，用户手动更新
                "",
            ])

    # --- 输出摘要 ---
    total = stats["total_included"]
    print(f"✓ RIS 文件已生成: {ris_path} ({total} 条记录)")
    print(f"✓ 题录完整性报告: {report_path}")
    print(f"✓ PDF 状态追踪表: {pdf_csv_path}")
    print(f"\n--- 统计摘要 ---")
    print(f"纳入文献: {total} 篇")
    print(f"DOI 缺失:  {stats['missing_doi']}/{total} ({stats['missing_doi']/total*100:.1f}%)")
    print(f"摘要缺失:  {stats['missing_abstract']}/{total} ({stats['missing_abstract']/total*100:.1f}%)")
    print(f"作者缺失:  {stats['missing_author']}/{total} ({stats['missing_author']/total*100:.1f}%)")
    print(f"期刊缺失:  {stats['missing_journal']}/{total} ({stats['missing_journal']/total*100:.1f}%)")
    print(f"卷缺失:    {stats['missing_volume']}/{total} ({stats['missing_volume']/total*100:.1f}%)")

    return ris_path, report_path, pdf_csv_path, stats


def main():
    parser = argparse.ArgumentParser(description="从 screened_literature.csv 生成 Zotero RIS 导入文件")
    parser.add_argument("csv", help="screened_literature.csv 路径")
    parser.add_argument("--outdir", "-o", default=".", help="输出目录 (默认当前目录)")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"❌ 文件不存在: {args.csv}")
        sys.exit(1)

    os.makedirs(args.outdir, exist_ok=True)
    generate_ris(args.csv, args.outdir)


if __name__ == "__main__":
    main()
