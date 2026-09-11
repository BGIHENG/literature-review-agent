#!/usr/bin/env python3
"""
Reading Notes Enricher - Phase C: 用全文补全精读笔记
====================================================
从 pdf_reader.py 生成的 fulltext/ 目录读取结构化全文，
自动补全原有精读笔记中缺失的字段。

增强字段:
  - 技术平台（摘要中常缺失）   → 从 Methods 提取
  - 样本处理细节               → 从 Methods 提取
  - 测序深度/关键参数           → 从 Methods 提取
  - 图表亮点                   → 从 Table/Figure captions
  - 局限性                     → 从 Discussion 提取
  - 补充发现                   → 从 Results 提取

用法:
    # 批量增强
    python batch_enrich.py reading_notes/ --fulltext-dir fulltext/ --outdir reading_notes_v2/

    # 增强单篇
    python batch_enrich.py reading_notes/PMID_33417940.md --fulltext-dir fulltext/
"""

import os
import sys
import re
import csv
import json
import argparse
import hashlib
from pathlib import Path
from collections import defaultdict


# ════════════════════════════════════════════════════════════════════
# 平台检测规则
# ════════════════════════════════════════════════════════════════════

PLATFORM_PATTERNS = {
    "10x Genomics scRNA-seq": [
        r"(?i)\b10x\s*genomics\b", r"(?i)\bchromium\b",
        r"(?i)\bsingle\s*cell\s*3['\u2019]\s*(?:v\d|prime)",
        r"(?i)\bGEM\s*(?:wells?|beads?)\b",
    ],
    "10x Visium": [
        r"(?i)\bvisium\b", r"(?i)\bspatial\s*transcriptomics?\b.*\b10x\b",
    ],
    "Stereo-seq": [
        r"(?i)\bstereo[\s-]*seq\b", r"(?i)\bDNB(?:SEQ)?\b",
    ],
    "Slide-seq": [
        r"(?i)\bslide[\s-]*seq\b",
    ],
    "MERFISH": [
        r"(?i)\bmerfish\b", r"(?i)\bmultiplexed\s*error[\s-]*robust\s*FISH\b",
    ],
    "seqFISH": [
        r"(?i)\bseq[\s-]*fish\b", r"(?i)\bsequential\s*FISH\b",
    ],
    "Smart-seq2": [
        r"(?i)\bsmart[\s-]*seq2?\b",
    ],
    "SMARTer/C1": [
        r"(?i)\bsmarter\b", r"(?i)\bC1\s*(?:system|platform|auto\s*prep)\b",
    ],
    "Nanopore sequencing": [
        r"(?i)\bnanopore\b", r"(?i)\bMinION\b", r"(?i)\bPromethION\b",
    ],
    "PacBio": [
        r"(?i)\bpacbio\b", r"(?i)\bSMRT\s*(?:sequencing|bell)\b",
    ],
    "CODEX/IMC": [
        r"(?i)\bcodex\b", r"(?i)\bimaging\s*mass\s*cytometry\b", r"(?i)\bIMC\b",
    ],
    "CyTOF": [
        r"(?i)\bcytof\b", r"(?i)\bmass\s*cytometry\b",
    ],
    "CITE-seq": [
        r"(?i)\bcite[\s-]*seq\b", r"(?i)\bcellular\s*indexing\b",
    ],
    "scATAC-seq": [
        r"(?i)\bsc[\s-]*?ATAC[\s-]*seq\b", r"(?i)\bsingle[\s-]*cell\s*ATAC\b",
    ],
}

ANALYSIS_PATTERNS = {
    "Seurat": [r"(?i)\bseurat\b"],
    "Scanpy": [r"(?i)\bscanpy\b"],
    "Harmony": [r"(?i)\bharmony\b"],
    "Monocle": [r"(?i)\bmonocle[23]?\b"],
    "CellChat": [r"(?i)\bcellchat\b"],
    "NicheNet": [r"(?i)\bnichenet\b"],
    "CellPhoneDB": [r"(?i)\bcellphonedb\b"],
    "GSEA": [r"(?i)\bGSEA\b", r"(?i)\bgene\s*set\s*enrichment\b"],
    "GSVA": [r"(?i)\bGSVA\b"],
    "AUCell": [r"(?i)\baucell\b"],
    "SCENIC": [r"(?i)\bscenic\b"],
    "pySCENIC": [r"(?i)\bpyscenic\b"],
    "SCENIC+": [r"(?i)\bscenic\+\b"],
    "ArchR": [r"(?i)\barchr\b"],
    "Signac": [r"(?i)\bsignac\b"],
    "Cicero": [r"(?i)\bcicero\b"],
    "WNN": [r"(?i)\bweighted[\s-]*nearest\s*neighbor\b"],
    "MOFA": [r"(?i)\bMOFA\b"],
    "totalVI": [r"(?i)\btotalvi\b"],
    "scVI": [r"(?i)\bscVI\b"],
    "InferCNV": [r"(?i)\binfercnv\b"],
    "CopyKAT": [r"(?i)\bcopykat\b"],
    "RNA velocity": [r"(?i)\bRNA\s*velocity\b", r"(?i)\bvelocyto\b", r"(?i)\bscvelo\b"],
    "CellRank": [r"(?i)\bcellrank\b"],
    "Slingshot": [r"(?i)\bslingshot\b"],
    "PAGA": [r"(?i)\bPAGA\b"],
    "CytoTRACE": [r"(?i)\bcytotrace\b"],
}

SAMPLE_SIZE_PATTERNS = [
    r"(?i)(?:n\s*=\s*|included\s+|enrolled\s+|collected\s+from\s+|from\s+a\s+total\s+of\s+|comprised\s+|consisted\s+of\s+)(\d+[\d,]*)\s*(?:patients?|samples?|specimens?|tumors?|tissues?|cells?)",
    r"(?i)(\d+[\d,]*)\s*(?:patients?|samples?|specimens?)\s*(?:were|was)\s*(?:included|enrolled|collected|analyzed|recruited|obtained)",
    r"(?i)(?:profiled|sequenced|analyzed)\s+(\d+[\d,]*)\s*(?:single\s*)?cells?",
]

CELL_COUNT_PATTERNS = [
    r"(?i)(\d+[\d,]*)\s*(?:single\s*)?cells?\s*(?:were|was)\s*(?:profiled|sequenced|captured|analyzed|obtained|recovered)",
    r"(?i)(?:yielded|produced|captured|obtained|recovered|generated)\s+(\d+[\d,]*)\s*(?:single\s*)?cells?",
    r"(?i)(?:total|overall)\s*(?:of\s*)?(\d+[\d,]*)\s*(?:single\s*)?cells?",
]


# ════════════════════════════════════════════════════════════════════
# 提取逻辑
# ════════════════════════════════════════════════════════════════════

def detect_platforms(text):
    """从文本中检测使用的技术平台。"""
    found = []
    for platform, patterns in PLATFORM_PATTERNS.items():
        if any(re.search(p, text) for p in patterns):
            found.append(platform)
    return list(set(found))


def detect_analyses(text):
    """从文本中检测使用的分析方法。"""
    found = []
    for method, patterns in ANALYSIS_PATTERNS.items():
        if any(re.search(p, text) for p in patterns):
            found.append(method)
    return list(set(found))


def detect_sample_size(text):
    """从文本中检测样本量。"""
    sizes = []
    for pattern in SAMPLE_SIZE_PATTERNS:
        matches = re.findall(pattern, text)
        for m in matches:
            try:
                sizes.append(int(m.replace(",", "")))
            except ValueError:
                pass
    return max(sizes) if sizes else None


def detect_cell_count(text):
    """从文本中检测单细胞数量。"""
    counts = []
    for pattern in CELL_COUNT_PATTERNS:
        matches = re.findall(pattern, text)
        for m in matches:
            try:
                counts.append(int(m.replace(",", "")))
            except ValueError:
                pass
    return max(counts) if counts else None


def extract_sample_processing(text, max_chars=500):
    """从 Methods 中提取样本处理细节。"""
    # 搜索 sample preparation / tissue processing 等段落
    patterns = [
        r"(?i)(?:sample|tissue|specimen)\s*(?:preparation|processing|collection|dissociation|digestion)",
        r"(?i)(?:fresh|frozen|FFPE|formalin)[\s\w]*(?:tissue|sample|specimen)",
        r"(?i)(?:single[\s-]*cell|single[\s-]*nuclei?)\s*(?:suspension|isolation|preparation|dissociation)",
    ]
    for pat in patterns:
        m = re.search(pat + r".{0," + str(max_chars) + r"}", text)
        if m:
            return m.group(0)[:max_chars].strip()
    return None


def detect_sequencing_params(text):
    """检测测序深度和关键参数。"""
    params = {}
    # Read depth
    depth_m = re.search(r"(?i)(\d+[\d,]*[KkMm]?)\s*(?:reads?|read\s*pairs?)\s*(?:per\s*cell|/cell)", text)
    if depth_m:
        params["reads_per_cell"] = depth_m.group(0)
    # Genes per cell
    genes_m = re.search(r"(?i)(\d+[\d,]*)\s*(?:genes?|features?)\s*(?:per\s*cell|/cell|detected)", text)
    if genes_m:
        params["genes_per_cell"] = genes_m.group(0)
    # UMI
    umi_m = re.search(r"(?i)(\d+[\d,]*[Kk]?)\s*UMIs?\s*(?:per\s*cell|/cell)", text)
    if umi_m:
        params["umi_per_cell"] = umi_m.group(0)
    return params if params else None


# ════════════════════════════════════════════════════════════════════
# Markdown 解析与增强
# ════════════════════════════════════════════════════════════════════

def parse_reading_note(md_text):
    """解析现有精读笔记，返回结构化数据。"""
    result = {
        "title": "",
        "pmid": "",
        "doi": "",
        "authors": "",
        "journal": "",
        "has_platform": False,
        "has_sample_processing": False,
        "has_sequencing": False,
        "has_highlights": False,
        "has_limitations": False,
        "needs_fulltext_sections": [],
    }

    # 提取标题
    title_m = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    if title_m:
        result["title"] = title_m.group(1).strip()

    # 提取 PMID
    pmid_m = re.search(r"\*\*PMID:\*\*\s*(\d+)", md_text)
    if pmid_m:
        result["pmid"] = pmid_m.group(1)

    # 提取 DOI
    doi_m = re.search(r"\*\*DOI:\*\*\s*(10\.\S+)", md_text)
    if doi_m:
        result["doi"] = doi_m.group(1).rstrip(".,;")

    # 检查哪些字段标记为"需查看全文"或缺失
    platform_section = re.search(r"技术平台.*?\n((?:.|\n)*?)(?=\n##|\Z)", md_text)
    if platform_section:
        pt = platform_section.group(1)
        if "需查看全文" in pt or "需人工" in pt or not pt.strip().lstrip("- ").strip():
            result["needs_fulltext_sections"].append("技术平台")
        elif len(pt.strip()) > 20:
            result["has_platform"] = True

    sample_section = re.search(r"样本处理.*?\n((?:.|\n)*?)(?=\n##|\Z)", md_text)
    if sample_section:
        sp = sample_section.group(1)
        if "需查看全文" in sp or "需人工" in sp or not sp.strip().lstrip("- ").strip():
            result["needs_fulltext_sections"].append("样本处理")
        elif len(sp.strip()) > 10:
            result["has_sample_processing"] = True

    seq_section = re.search(r"测序深度.*?\n((?:.|\n)*?)(?=\n##|\Z)", md_text)
    if seq_section:
        sq = seq_section.group(1)
        if "需查看全文" in sq or "需人工" in sq or not sq.strip().lstrip("- ").strip():
            result["needs_fulltext_sections"].append("测序深度")
        elif len(sq.strip()) > 10:
            result["has_sequencing"] = True

    fig_section = re.search(r"图表亮点.*?\n((?:.|\n)*?)(?=\n##|\Z)", md_text)
    if fig_section:
        fg = fig_section.group(1)
        if len(fg.strip()) < 30:
            result["needs_fulltext_sections"].append("图表亮点")
        else:
            result["has_highlights"] = True

    lim_section = re.search(r"局限性.*?\n((?:.|\n)*?)(?=\n##|\Z)", md_text)
    if lim_section:
        lm = lim_section.group(1)
        if "摘要中未提及" in lm or "需查看全文" in lm or not lm.strip().lstrip("- ").strip():
            result["needs_fulltext_sections"].append("局限性")
        elif len(lm.strip()) > 10:
            result["has_limitations"] = True

    return result


def enrich_reading_note(note_path, fulltext_path, out_path):
    """增强单篇精读笔记。

    返回 (enriched: bool, fields_added: list)
    """
    # 读取
    with open(note_path, "r", encoding="utf-8") as f:
        note_text = f.read()

    note_data = parse_reading_note(note_text)

    if not os.path.exists(fulltext_path):
        return False, []

    with open(fulltext_path, "r", encoding="utf-8") as f:
        fulltext_text = f.read()

    # 提取 Methods + Results + Discussion
    # 从全文 Markdown 中取 methods/results/discussion 段落
    methods_text = _extract_section(fulltext_text, "Methods Summary")
    results_text = _extract_section(fulltext_text, "Results Summary")
    discuss_text = _extract_section(fulltext_text, "Discussion Summary")
    combined = methods_text + " " + results_text + " " + discuss_text

    if not combined.strip():
        return False, []

    fields_added = []

    # Step 1: 补全平台信息
    if "技术平台" in note_data["needs_fulltext_sections"]:
        platforms = detect_platforms(combined)
        if platforms:
            platform_line = "- " + "; ".join(platforms)
            note_text = _replace_or_insert(
                note_text, "技术平台",
                f"**技术平台:** {platform_line}\n",
            )
            fields_added.append(f"技术平台: {', '.join(platforms)}")

    # Step 2: 补全分析方法
    analyses = detect_analyses(combined)
    if analyses:
        # 检查是否已有分析方法字段
        if "分析方法" in note_text:
            existing = re.search(r"\*\*分析方法:\*\*\s*(.+)", note_text)
            if existing and len(existing.group(1).strip()) < 5:
                note_text = note_text.replace(
                    existing.group(0),
                    f"**分析方法:** {', '.join(analyses)}"
                )
                fields_added.append(f"分析方法: {', '.join(analyses)}")
        else:
            # 插入到平台后面
            note_text = _insert_after_section(
                note_text, "技术平台",
                f"- **分析方法:** {', '.join(analyses)}\n"
            )
            fields_added.append(f"分析方法: {', '.join(analyses)}")

    # Step 3: 补全样本量
    sample_n = detect_sample_size(combined)
    if sample_n:
        existing_n = re.search(r"样本量.*?\n((?:.|\n)*?)(?=\n-|\n##|\Z)", note_text)
        if not existing_n or "n=" not in existing_n.group(0).lower():
            if "样本量" in note_text:
                note_text = _replace_or_insert(
                    note_text, "样本量",
                    f"**样本量:** n={sample_n}\n",
                )
                fields_added.append(f"样本量: n={sample_n}")

    # Step 4: 补全细胞数
    cell_n = detect_cell_count(combined)
    if cell_n and cell_n > 100:
        cell_line = f"- **单细胞数:** {cell_n:,} cells\n"
        if "单细胞数" not in note_text:
            note_text = _insert_after_section(note_text, "样本量", cell_line)
            fields_added.append(f"单细胞数: {cell_n:,}")

    # Step 5: 补全样本处理
    if "样本处理" in note_data["needs_fulltext_sections"]:
        processing = extract_sample_processing(combined)
        if processing:
            note_text = _replace_or_insert(
                note_text, "样本处理",
                f"**样本处理:** {processing[:300]}\n",
            )
            fields_added.append("样本处理")

    # Step 6: 补全测序参数
    if "测序深度" in note_data["needs_fulltext_sections"]:
        seq_params = detect_sequencing_params(combined)
        if seq_params:
            params_str = "; ".join(f"{k}: {v}" for k, v in seq_params.items())
            note_text = _replace_or_insert(
                note_text, "测序深度",
                f"**测序深度:** {params_str}\n",
            )
            fields_added.append(f"测序深度: {params_str}")

    # Step 7: 补全图表亮点
    if "图表亮点" in note_data["needs_fulltext_sections"]:
        tables = re.findall(r"\*\*(Table\s*\d+)\*\*:\s*(.+?)(?=\n|$)", fulltext_text)
        figures = re.findall(r"\*\*(Figure\s*\d+)\*\*:\s*(.+?)(?=\n|$)", fulltext_text)
        highlights = []
        for fid, cap in figures[:6]:
            highlights.append(f"- **{fid}**: {cap[:150].strip()}")
        for tid, cap in tables[:4]:
            highlights.append(f"- **{tid}**: {cap[:150].strip()}")
        if highlights:
            note_text = _replace_or_insert(
                note_text, "图表亮点",
                "**图表亮点:** \n" + "\n".join(highlights) + "\n",
            )
            fields_added.append(f"图表亮点: {len(highlights)} items")

    # Step 8: 补全局限性
    if "局限性" in note_data["needs_fulltext_sections"]:
        lims = re.findall(
            r"^\d+\.\s*(.+)$",
            _extract_section(fulltext_text, "Limitations"),
            re.MULTILINE,
        )
        if lims:
            lim_text = "**局限性:**\n" + "\n".join(f"- {l[:200]}" for l in lims[:6]) + "\n"
            note_text = _replace_or_insert(note_text, "局限性", lim_text)
            fields_added.append(f"局限性: {len(lims)} items")

    # 更新来源标注
    note_text = note_text.replace(
        "信息来源: PubMed 完整摘要",
        "信息来源: PubMed 完整摘要 + Full-Text PDF",
    )

    # 写入
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(note_text)

    return True, fields_added


def _extract_section(md_text, section_name):
    """从全文 Markdown 中提取指定段落。"""
    # 匹配 ## Section Name ... content until next ## or end
    pattern = rf"^##\s+{re.escape(section_name)}\s*\n((?:.|\n)*?)(?=\n##\s|\Z)"
    m = re.search(pattern, md_text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return ""


def _replace_or_insert(note_text, field_name, new_content):
    """替换现有字段内容，或插入到适当位置。"""
    # 尝试替换
    pattern = rf"\*\*{re.escape(field_name)}[：:]\*\*.*?(?=\n-|\n##|\Z)"
    m = re.search(pattern, note_text)
    if m:
        return note_text[:m.start()] + new_content.rstrip() + note_text[m.end():]
    return note_text


def _insert_after_section(note_text, after_field, new_content):
    """在指定字段之后插入新行。"""
    pattern = rf"(\*\*{re.escape(after_field)}[：:]\*\*.*?\n)"
    m = re.search(pattern, note_text)
    if m:
        idx = m.end()
        return note_text[:idx] + new_content + note_text[idx:]
    return note_text + "\n" + new_content


# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Reading Notes Enricher - 用全文补全精读笔记",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python batch_enrich.py reading_notes/ --fulltext-dir fulltext/ --outdir reading_notes_v2/
  python batch_enrich.py reading_notes/PMID_33417940.md --fulltext-dir fulltext/
        """,
    )
    parser.add_argument("input_path", help="精读笔记目录 或 单篇 .md 路径")
    parser.add_argument("--fulltext-dir", required=True, help="全文提取目录 (pdf_reader.py 输出)")
    parser.add_argument("--outdir", help="输出目录 (默认覆盖原文件，建议指定新目录)")
    parser.add_argument("--report", default="enrich_report.json", help="增强报告路径")
    args = parser.parse_args()

    # 收集待处理文件
    if os.path.isfile(args.input_path):
        note_files = [args.input_path]
    elif os.path.isdir(args.input_path):
        note_files = [
            os.path.join(args.input_path, f)
            for f in os.listdir(args.input_path)
            if f.startswith("PMID_") and f.endswith(".md")
        ]
    else:
        print(f"Error: {args.input_path} is not a file or directory", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(args.fulltext_dir):
        print(f"Error: fulltext directory not found: {args.fulltext_dir}", file=sys.stderr)
        print("Tip: Run pdf_reader.py first to extract full-text.", file=sys.stderr)
        sys.exit(1)

    # 构建全文索引
    fulltext_index = {}
    for fname in os.listdir(args.fulltext_dir):
        if fname.startswith("PMID_") and fname.endswith(".md"):
            pmid = fname.replace("PMID_", "").replace(".md", "")
            fulltext_index[pmid] = os.path.join(args.fulltext_dir, fname)

    print(f"Loaded {len(note_files)} reading notes")
    print(f"Found {len(fulltext_index)} full-text extractions")
    print(f"{'='*60}")

    report = {"total": len(note_files), "enriched": 0, "skipped": 0, "no_fulltext": 0, "details": []}
    outdir = args.outdir or os.path.dirname(args.input_path)

    for i, note_path in enumerate(note_files):
        fname = os.path.basename(note_path)
        pmid = fname.replace("PMID_", "").replace(".md", "")
        print(f"[{i+1}/{len(note_files)}] {fname} ... ", end="", flush=True)

        if pmid not in fulltext_index:
            print("SKIP (no full-text)")
            report["no_fulltext"] += 1
            report["details"].append({"file": fname, "status": "no_fulltext", "fields": []})
            continue

        out_path = os.path.join(outdir, fname) if args.outdir else note_path
        enriched, fields = enrich_reading_note(note_path, fulltext_index[pmid], out_path)

        if enriched and fields:
            report["enriched"] += 1
            print(f"ENRICHED ({len(fields)} fields: {', '.join(fields[:3])}{'...' if len(fields) > 3 else ''})")
            report["details"].append({"file": fname, "status": "enriched", "fields": fields})
        else:
            report["skipped"] += 1
            print("SKIP (no new data)")
            report["details"].append({"file": fname, "status": "skipped", "fields": []})

    # 输出报告
    report_path = os.path.join(outdir, args.report)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"  Total notes:      {report['total']}")
    print(f"  Enriched:         {report['enriched']}  (+ full-text fields)")
    print(f"  Skipped (no new): {report['skipped']}")
    print(f"  No full-text:     {report['no_fulltext']}  (PDF not available)")
    print(f"\n  Output: {os.path.abspath(outdir)}/")
    print(f"  Report: {os.path.abspath(report_path)}")


if __name__ == "__main__":
    main()
