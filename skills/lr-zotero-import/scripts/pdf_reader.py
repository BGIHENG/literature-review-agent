#!/usr/bin/env python3
"""
PDF Reader - Phase B: PDF 正文提取工具
=======================================
为文献综述 Pipeline 提供全文阅读能力。

输入: PDF 目录 + screened_literature.csv (PMID/DOI 映射)
输出: fulltext/PMID_xxxxx.md (结构化全文提取)

依赖: pip install pymupdf

用法:
    # 提取所有匹配的 PDF
    python pdf_reader.py screened_literature.csv --pdf-dir pdfs/ --outdir fulltext/

    # 指定单篇 PMID
    python pdf_reader.py screened_literature.csv --pdf-dir pdfs/ --pmid 33417940

    # 只统计不提取
    python pdf_reader.py screened_literature.csv --pdf-dir pdfs/ --dry-run
"""

import os
import sys
import re
import csv
import json
import argparse
import hashlib
import warnings
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ════════════════════════════════════════════════════════════════════
# PDF 提取器
# ════════════════════════════════════════════════════════════════════

def extract_pymupdf(pdf_path):
    """用 PyMuPDF 提取正文。

    Returns:
        (success: bool, full_text: str, metadata: dict)
    """
    try:
        import fitz
    except ImportError:
        print("[!] PyMuPDF not installed. Run: pip install pymupdf", file=sys.stderr)
        return False, "", {"error": "pymupdf_not_installed"}

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return False, "", {"error": f"open_failed: {e}"}

    meta = {
        "pages": len(doc),
        "title": doc.metadata.get("title", ""),
        "author": doc.metadata.get("author", ""),
        "subject": doc.metadata.get("subject", ""),
        "format": doc.metadata.get("format", "PDF"),
        "encrypted": doc.is_encrypted,
        "needs_pass": doc.needs_pass,
    }

    # 检查是否为扫描件（图片为主）
    text_sample = ""
    for page in doc:
        text_sample = page.get_text()
        if text_sample.strip():
            break
    if not text_sample.strip():
        doc.close()
        return False, "", {**meta, "error": "scanned_pdf_no_text"}

    # 提取所有页面文字
    all_pages = []
    for i, page in enumerate(doc):
        page_text = page.get_text("text")
        all_pages.append(f"<!-- PAGE {i+1} -->\n{page_text}")

    full_text = "\n\n".join(all_pages)
    meta["char_count"] = len(full_text)
    meta["word_count_est"] = len(full_text.split())

    doc.close()
    return True, full_text, meta


def extract_pdfplumber(pdf_path):
    """备用提取器：pdfplumber（需 Python 3.8+）"""
    try:
        import pdfplumber
    except ImportError:
        return False, "", {"error": "pdfplumber_not_installed"}

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_pages = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                all_pages.append(f"<!-- PAGE {i+1} -->\n{text}")
            full_text = "\n\n".join(all_pages)
            meta = {
                "pages": len(pdf.pages),
                "char_count": len(full_text),
                "word_count_est": len(full_text.split()),
                "extractor": "pdfplumber",
            }
            return bool(full_text.strip()), full_text, meta
    except Exception as e:
        return False, "", {"error": f"pdfplumber_failed: {e}"}


def extract_text(pdf_path):
    """综合提取：先 PyMuPDF，失败则 pdfplumber"""
    ok, text, meta = extract_pymupdf(pdf_path)
    if ok and text.strip():
        meta["extractor"] = "pymupdf"
        return ok, text, meta

    # 备用
    ok2, text2, meta2 = extract_pdfplumber(pdf_path)
    meta2["pages"] = meta.get("pages", 0)
    return ok2, text2, meta2


# ════════════════════════════════════════════════════════════════════
# IMRaD 段落识别
# ════════════════════════════════════════════════════════════════════

SECTION_PATTERNS = {
    "abstract": [
        r"(?i)^\s*abstract\s*$",
        r"(?i)^\s*summary\s*$",
    ],
    "introduction": [
        r"(?i)^\s*intro(?:duction)?\s*$",
        r"(?i)^\s*background\s*$",
    ],
    "methods": [
        r"(?i)^\s*(?:materials\s+(?:and|&)\s+)?methods?\s*$",
        r"(?i)^\s*experimental\s+(?:procedures?|design)\s*$",
        r"(?i)^\s*methodology\s*$",
    ],
    "results": [
        r"(?i)^\s*results?\s*$",
        r"(?i)^\s*findings\s*$",
    ],
    "discussion": [
        r"(?i)^\s*discussion\s*$",
        r"(?i)^\s*conclusions?\s*$",
    ],
    "references": [
        r"(?i)^\s*references?\s*$",
        r"(?i)^\s*bibliography\s*$",
        r"(?i)^\s*citations?\s*$",
    ],
    "supplementary": [
        r"(?i)^\s*supplementary\s+(?:materials?|data|information|figures?|tables?)\s*$",
        r"(?i)^\s*supplement(?:ary)?\s*$",
        r"(?i)^\s*appendix\s*$",
        r"(?i)^\s*supporting\s+information\s*$",
    ],
    "acknowledgments": [
        r"(?i)^\s*acknowledgments?\s*$",
        r"(?i)^\s*acknowledgements?\s*$",
        r"(?i)^\s*funding\s*$",
    ],
}


def identify_sections(text):
    """识别 IMRaD 段落边界，返回 {section_name: start_line}"""
    lines = text.split("\n")
    sections = {}
    for i, line in enumerate(lines):
        stripped = line.strip()
        for sec_name, patterns in SECTION_PATTERNS.items():
            if any(re.match(p, stripped) for p in patterns):
                if sec_name not in sections:  # 第一次出现
                    sections[sec_name] = i
    return dict(sorted(sections.items(), key=lambda x: x[1]))


def split_imrad(text):
    """将全文按 IMRaD 结构拆分。"""
    sections = identify_sections(text)
    if not sections:
        return {"full_body": text}

    lines = text.split("\n")
    result = {}
    sec_names = list(sections.keys())
    for idx, sec_name in enumerate(sec_names):
        start = sections[sec_name]
        end = sections[sec_names[idx + 1]] if idx + 1 < len(sec_names) else len(lines)
        result[sec_name] = "\n".join(lines[start:end])

    return result


# ════════════════════════════════════════════════════════════════════
# Table / Figure 提取
# ════════════════════════════════════════════════════════════════════

def extract_table_captions(text):
    """从正文中提取 Table 标题和 Figure 标题。"""
    table_caps = re.findall(
        r"(?i)^\s*(?:Table|Tab\.?)\s*(\d+[A-Za-z]?)\.?\s*(.+)$",
        text, re.MULTILINE
    )
    figure_caps = re.findall(
        r"(?i)^\s*(?:Figure|Fig\.?)\s*(\d+[A-Za-z]?)\.?\s*(.+)$",
        text, re.MULTILINE
    )
    return {
        "tables": [{"id": f"Table {t[0]}", "caption": t[1].strip().rstrip(".")}
                    for t in table_caps],
        "figures": [{"id": f"Figure {f[0]}", "caption": f[1].strip().rstrip(".")}
                     for f in figure_caps],
    }


# ════════════════════════════════════════════════════════════════════
# Limitations 提取
# ════════════════════════════════════════════════════════════════════

LIMITATION_KEYWORDS = [
    r"(?i)limitation",
    r"(?i)shortcoming",
    r"(?i)caveat",
    r"(?i)our study (?:is|was) limited",
    r"(?i)several limitations",
    r"(?i)should be interpreted with caution",
    r"(?i)further studies (?:are|is) (?:needed|required|warranted)",
    r"(?i)potential (?:bias|confound)",
    r"(?i)generalizability",
]


def extract_limitations(text):
    """从讨论部分提取局限性相关段落。"""
    discussion_start = -1
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if re.match(r"(?i)^\s*discussion\s*$", line.strip()):
            discussion_start = i
            break

    if discussion_start < 0:
        # 从后半部分搜索
        discussion_start = len(lines) // 2

    # 在讨论后半段搜索局限性关键词
    discussion_text = "\n".join(lines[discussion_start:])
    limitations = []
    for pattern in LIMITATION_KEYWORDS:
        for m in re.finditer(pattern, discussion_text):
            ctx_start = max(0, m.start() - 100)
            ctx_end = min(len(discussion_text), m.end() + 500)
            snippet = discussion_text[ctx_start:ctx_end].strip()
            # 按句号拆分，取包含关键词的句子及其上下文
            sentences = re.split(r"(?<=[.!?])\s+", snippet)
            relevant = [s for s in sentences if re.search(pattern, s)]
            if relevant:
                limitations.append(" ".join(relevant))

    # 去重
    seen = set()
    unique = []
    for lim in limitations:
        h = hashlib.md5(lim[:200].encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            unique.append(lim)
    return unique


# ════════════════════════════════════════════════════════════════════
# Markdown 输出
# ════════════════════════════════════════════════════════════════════

def generate_markdown(record, full_text, meta, imrad, tables_figures, limitations):
    """生成结构化的全文 Markdown 文件。"""

    pmid = record.get("PMID", "UNKNOWN")
    title = record.get("Title", "Unknown Title")
    doi = record.get("DOI", "")
    authors = record.get("Authors", record.get("Author", ""))
    journal = record.get("Journal", "")

    lines = []
    lines.append(f"# Full-Text Extraction: {title}")
    lines.append("")
    lines.append(f"> **Source**: Full-text PDF | **Word count**: ~{meta.get('word_count_est', 0):,}")
    lines.append(f"> **Extracted**: {datetime.now().strftime('%Y-%m-%d %H:%M')} | **Extractor**: {meta.get('extractor', 'unknown')}")
    lines.append("")

    # 基本信息
    lines.append("## Basic Info")
    lines.append(f"- **PMID**: {pmid}")
    if doi:
        lines.append(f"- **DOI**: {doi}")
    lines.append(f"- **Authors**: {authors}")
    lines.append(f"- **Journal**: {journal}")
    lines.append(f"- **Pages**: {meta.get('pages', '?')}")
    lines.append(f"- **Total chars**: {meta.get('char_count', 0):,}")
    lines.append("")

    # 段落结构概览
    if imrad and len(imrad) > 1:
        lines.append("## Section Map")
        for sec_name, sec_text in imrad.items():
            lines.append(f"- **{sec_name.title()}**: ~{len(sec_text.split()):,} words")
        lines.append("")

    # 表格/图表
    if tables_figures.get("tables"):
        lines.append("## Tables")
        for t in tables_figures["tables"][:20]:
            lines.append(f"- **{t['id']}**: {t['caption'][:200]}")
        lines.append("")

    if tables_figures.get("figures"):
        lines.append("## Figures")
        for f in tables_figures["figures"][:30]:
            lines.append(f"- **{f['id']}**: {f['caption'][:200]}")
        lines.append("")

    # 局限性（全文）
    if limitations:
        lines.append("## Limitations (from full text)")
        for i, lim in enumerate(limitations[:10], 1):
            lines.append(f"{i}. {lim}")
        lines.append("")

    # 全文 Abstract
    if imrad and "abstract" in imrad:
        lines.append("## Abstract (Full Text)")
        lines.append("")
        # 截取摘要（最多 5000 字符）
        abs_text = imrad["abstract"]
        if len(abs_text) > 5000:
            abs_text = abs_text[:5000] + "\n\n... (truncated)"
        lines.append(abs_text)
        lines.append("")

    # Methods 摘要
    if imrad and "methods" in imrad:
        lines.append("## Methods Summary")
        lines.append("")
        methods_text = imrad["methods"]
        if len(methods_text) > 8000:
            methods_text = methods_text[:8000] + "\n\n... (truncated)"
        lines.append(methods_text)
        lines.append("")

    # Results 摘要
    if imrad and "results" in imrad:
        lines.append("## Results Summary")
        lines.append("")
        results_text = imrad["results"]
        if len(results_text) > 8000:
            results_text = results_text[:8000] + "\n\n... (truncated)"
        lines.append(results_text)
        lines.append("")

    # Discussion 摘要
    if imrad and "discussion" in imrad:
        lines.append("## Discussion Summary")
        lines.append("")
        disc_text = imrad["discussion"]
        if len(disc_text) > 8000:
            disc_text = disc_text[:8000] + "\n\n... (truncated)"
        lines.append(disc_text)
        lines.append("")

    # Supplementary
    if imrad and "supplementary" in imrad:
        lines.append("## Supplementary Information")
        lines.append("")
        supp_text = imrad["supplementary"]
        if len(supp_text) > 5000:
            supp_text = supp_text[:5000] + "\n\n... (truncated)"
        lines.append(supp_text)
        lines.append("")

    # 全文（放最后，截断）
    lines.append("## Full Text (truncated)")
    lines.append("")
    if len(full_text) > 15000:
        lines.append(full_text[:15000])
        lines.append("")
        lines.append(f"... (total {meta.get('word_count_est', 0):,} words, {meta.get('char_count', 0):,} chars)")
    else:
        lines.append(full_text)
    lines.append("")

    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# PDF 文件匹配
# ════════════════════════════════════════════════════════════════════

def build_pdf_index(pdf_dir):
    """扫描 PDF 目录，建立文件名索引。"""
    pdf_files = {}
    if not os.path.isdir(pdf_dir):
        return pdf_files

    for fname in os.listdir(pdf_dir):
        if not fname.lower().endswith(".pdf"):
            continue
        fpath = os.path.join(pdf_dir, fname)
        fname_lower = fname.lower()
        pdf_files[fname] = fpath
    return pdf_files


def match_pdf(record, pdf_index):
    """为一条文献记录匹配最可能的 PDF 文件。

    匹配优先级:
    1. 文件名包含 PMID
    2. 文件名包含 DOI 后缀
    3. 文件名与标题关键词匹配
    """
    pmid = record.get("PMID", "").strip()
    doi = record.get("DOI", "").strip()
    title = record.get("Title", "").strip()

    # Priority 1: PMID match
    if pmid:
        for fname in pdf_index:
            if pmid in fname:
                return pdf_index[fname]

    # Priority 2: DOI suffix match (e.g., 10.xxxx/xxxx)
    if doi:
        doi_suffix = doi.replace("/", "_").replace(":", "_")
        for fname in pdf_index:
            if doi_suffix in fname or doi.replace("https://doi.org/", "") in fname:
                return pdf_index[fname]

    # Priority 3: Title keyword match (first 5 words)
    if title:
        title_words = re.findall(r"[A-Za-z]{4,}", title)[:5]
        for fname in pdf_index:
            match_count = sum(1 for w in title_words if w.lower() in fname.lower())
            if match_count >= 3:
                return pdf_index[fname]

    return None


# ════════════════════════════════════════════════════════════════════
# CSV 读取
# ════════════════════════════════════════════════════════════════════

def read_csv(csv_path):
    """读取 screened_literature.csv，返回记录列表。"""
    records = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return records


# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="PDF Reader - 为文献综述 Pipeline 提取全文",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python pdf_reader.py screened.csv --pdf-dir pdfs/ --outdir fulltext/
  python pdf_reader.py screened.csv --pdf-dir pdfs/ --pmid 33417940
  python pdf_reader.py screened.csv --pdf-dir pdfs/ --dry-run
        """,
    )
    parser.add_argument("csv_path", help="screened_literature.csv 路径")
    parser.add_argument("--pdf-dir", required=True, help="PDF 文件所在目录")
    parser.add_argument("--outdir", default="fulltext", help="输出目录 (default: fulltext/)")
    parser.add_argument("--pmid", help="仅处理指定 PMID")
    parser.add_argument("--max-papers", type=int, default=0, help="最大处理篇数 (0=全部)")
    parser.add_argument("--dry-run", action="store_true", help="仅统计匹配情况，不实际提取")
    parser.add_argument("--report", default="pdf_reader_report.csv", help="汇总报告路径")
    args = parser.parse_args()

    if not os.path.exists(args.csv_path):
        print(f"Error: CSV not found: {args.csv_path}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(args.pdf_dir):
        print(f"Error: PDF directory not found: {args.pdf_dir}", file=sys.stderr)
        print("Tip: Run download_oa_pdfs.py first to download PDFs.", file=sys.stderr)
        sys.exit(1)

    # 加载数据
    records = read_csv(args.csv_path)
    pdf_index = build_pdf_index(args.pdf_dir)
    print(f"Loaded {len(records)} records from CSV")
    print(f"Found {len(pdf_index)} PDF files in {args.pdf_dir}")
    print(f"{'='*60}")

    # 过滤
    if args.pmid:
        records = [r for r in records if r.get("PMID", "") == args.pmid]
        if not records:
            print(f"No record found for PMID: {args.pmid}", file=sys.stderr)
            sys.exit(1)

    # 创建输出目录
    if not args.dry_run:
        os.makedirs(args.outdir, exist_ok=True)

    # 处理
    report_rows = []
    stats = defaultdict(int)

    for i, record in enumerate(records):
        if args.max_papers and i >= args.max_papers:
            break

        pmid = record.get("PMID", f"RECORD_{i}")
        title = record.get("Title", "Unknown")[:80]
        doi = record.get("DOI", "")

        pdf_path = match_pdf(record, pdf_index)
        if not pdf_path:
            stats["no_pdf"] += 1
            report_rows.append({
                "PMID": pmid, "Title": title, "DOI": doi,
                "Status": "no_pdf",
                "PDF": "", "Pages": 0, "Words": 0, "Error": "",
                "Tables": 0, "Figures": 0, "Limitations": 0,
            })
            continue

        stats["matched"] += 1
        print(f"[{i+1}/{min(len(records), args.max_papers or len(records))}] {pmid}: {os.path.basename(pdf_path)} ... ", end="", flush=True)

        if args.dry_run:
            print("MATCHED (dry-run)")
            report_rows.append({
                "PMID": pmid, "Title": title, "DOI": doi,
                "Status": "matched_dryrun",
                "PDF": os.path.basename(pdf_path), "Pages": 0, "Words": 0, "Error": "",
                "Tables": 0, "Figures": 0, "Limitations": 0,
            })
            continue

        # 提取
        ok, full_text, meta = extract_text(pdf_path)

        if not ok:
            stats["extract_fail"] += 1
            error = meta.get("error", "unknown")
            print(f"FAILED ({error})")
            report_rows.append({
                "PMID": pmid, "Title": title, "DOI": doi,
                "Status": f"extract_failed:{error}",
                "PDF": os.path.basename(pdf_path), "Pages": meta.get("pages", 0),
                "Words": 0, "Error": error,
                "Tables": 0, "Figures": 0, "Limitations": 0,
            })
            continue

        # 分析
        imrad = split_imrad(full_text)
        tables_figures = extract_table_captions(full_text)
        limitations = extract_limitations(full_text)

        # 输出
        md_content = generate_markdown(record, full_text, meta, imrad, tables_figures, limitations)
        out_name = f"PMID_{pmid}.md"
        out_path = os.path.join(args.outdir, out_name)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        stats["success"] += 1
        word_count = meta.get("word_count_est", 0)
        n_tables = len(tables_figures.get("tables", []))
        n_figures = len(tables_figures.get("figures", []))
        n_limitations = len(limitations)

        print(f"OK ({word_count:,} words, {n_tables}T/{n_figures}F/{n_limitations}L)")

        report_rows.append({
            "PMID": pmid, "Title": title, "DOI": doi,
            "Status": "success",
            "PDF": os.path.basename(pdf_path),
            "Pages": meta.get("pages", 0),
            "Words": word_count,
            "Error": "",
            "Tables": n_tables,
            "Figures": n_figures,
            "Limitations": n_limitations,
        })

    # 输出报告
    report_path = os.path.join(args.outdir, args.report) if not args.dry_run else args.report
    if report_rows:
        fieldnames = ["PMID", "Title", "DOI", "Status", "PDF", "Pages", "Words", "Error", "Tables", "Figures", "Limitations"]
        with open(report_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(report_rows)

    # 总结
    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"  Total records:  {len(records)}")
    print(f"  PDFs found:     {stats['matched']}")
    if not args.dry_run:
        print(f"  Extracted OK:   {stats['success']}")
        print(f"  Extract failed: {stats['extract_fail']}")
    print(f"  No PDF match:   {stats['no_pdf']}")
    if not args.dry_run:
        print(f"\n  Output: {os.path.abspath(args.outdir)}/")
    print(f"  Report: {os.path.abspath(report_path)}")


if __name__ == "__main__":
    main()
