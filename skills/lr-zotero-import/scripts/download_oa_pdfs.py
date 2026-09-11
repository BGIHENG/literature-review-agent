#!/usr/bin/env python3
"""
lr-zotero-import / OA PDF 批量下载器

通过 Unpaywall API + PubMed Central (PMC) API 检查文献的开放获取状态，
自动下载所有可用的 OA PDF 全文。

下载策略（按优先级）：
  1. PubMed Central (PMC) — 通过 PMID → PMC ID → 直接下载 PDF（最可靠）
  2. Unpaywall API — 通过 DOI 查询 OA 版本 URL
  3. 标题匹配 — 对 PMC 无 PMID 的文献用标题搜索（兜底）

输出：
  - pdfs/                       下载的 PDF 文件（仅 OA 可获取的）
  - pdf_download_report.csv     每篇文献的下载状态报告
  - pdf_download_summary.md     下载汇总（成功/失败/跳过统计）

用法：
  python download_oa_pdfs.py <literature.csv> [--outdir <dir>] [--email <email>]
      [--delay <seconds>] [--dry-run] [--max-pdfs <N>] [--pmid-col PMID]
      [--doi-col DOI] [--title-col Title] [--year-col Year]

参数：
  --outdir       PDF 输出目录（默认: ./pdfs）
  --email        Unpaywall/NCBI 要求的联系邮箱（默认: placeholder@example.com）
  --delay        API 请求间隔秒数（默认: 1.0，礼貌限速）
  --dry-run      仅检查状态，不实际下载
  --max-pdfs     最多下载 N 篇 PDF（默认: 全部），用于测试
  --pmid-col     PMID 列名（默认: PMID）
  --doi-col      DOI 列名（默认: DOI）
  --title-col    Title 列名（默认: Title）
  --year-col     Year 列名（默认: Year）
"""

import argparse
import csv
import os
import sys
import time
import json
import re
from datetime import datetime
from urllib.request import Request, urlopen, urlretrieve
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from pathlib import Path


# ─── 常量 ──────────────────────────────────────────────

UNPAYWALL_API = "https://api.unpaywall.org/v2/{doi}"
NCBI_EFETCH   = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
NCBI_ESEARCH  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

# PubMed Central 基础 URL
PMC_BASE = "https://www.ncbi.nlm.nih.gov/pmc/articles"

# 礼貌的 User-Agent
USER_AGENT = (
    "Mozilla/5.0 (compatible; LiteratureReviewBot/1.0; "
    "academic PDF download assistant; +mailto:{email})"
)

# 每篇文献的下载状态
STATUS_AUTO       = "auto_downloaded"    # 成功下载
STATUS_OA_NO_PDF  = "oa_no_pdf_found"    # OA 但无 PDF（仅 HTML 等）
STATUS_PAYWALL    = "paywall"            # 付费墙
STATUS_NO_FULLTEXT = "no_fulltext"       # 无全文（预印本/摘要 only）
STATUS_ERROR      = "error"              # 下载出错
STATUS_SKIPPED    = "skipped"            # 超过 max-pdfs 限制
STATUS_NO_DOI_PMID = "no_identifier"     # 无 DOI 也无 PMID


# ─── 工具函数 ──────────────────────────────────────────

def make_request(url, email, headers_extra=None):
    """创建带 User-Agent 的 Request 对象"""
    headers = {
        "User-Agent": USER_AGENT.format(email=email),
        "Accept": "application/json, application/pdf, text/xml, */*",
    }
    if headers_extra:
        headers.update(headers_extra)
    return Request(url, headers=headers)


def fetch_json(url, email, timeout=30):
    """GET JSON 响应"""
    req = make_request(url, email)
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except (HTTPError, URLError, json.JSONDecodeError) as e:
        print(f"    [!] JSON fetch failed: {e}")
        return None


def fetch_xml(url, email, timeout=30):
    """GET XML/文本响应"""
    req = make_request(url, email)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except (HTTPError, URLError) as e:
        print(f"    [!] XML fetch failed: {e}")
        return None


def safe_val(row, key, default=""):
    """安全获取 CSV 字段值"""
    v = row.get(key, "").strip()
    return v if v else default


def clean_doi(doi):
    """清理 DOI 字符串"""
    if not doi:
        return ""
    doi = doi.strip()
    # 去掉可能的 URL 前缀
    doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
    return doi


# ─── PMC 查询 ──────────────────────────────────────────

def search_pmcid_by_title(title, email, delay):
    """通过标题在 PMC 中搜索 PMC ID（兜底策略）"""
    query = quote(title, safe='')
    url = (f"{NCBI_ESEARCH}?db=pmc&term={query}&retmode=json&retmax=3"
           f"&email={quote(email, safe='')}&tool=litreview")
    time.sleep(delay)
    data = fetch_json(url, email)
    if not data or "esearchresult" not in data:
        return None
    id_list = data["esearchresult"].get("idlist", [])
    if not id_list:
        return None
    return id_list[0]  # 返回最佳匹配的 PMC ID


def get_pmc_pdf_url(pmcid, email, delay):
    """给定 PMC ID，返回 PDF 下载 URL"""
    url = (f"{NCBI_EFETCH}?db=pmc&id={pmcid}&rettype=xml"
           f"&email={quote(email, safe='')}&tool=litreview")
    time.sleep(delay)
    xml_text = fetch_xml(url, email)
    if not xml_text:
        return None
    # PMC 文章页面格式: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{id}/pdf/
    # 直接构造 PDF URL
    pdf_url = f"{PMC_BASE}/PMC{pmcid}/pdf/main.pdf"
    # 验证 PDF 是否可访问（HEAD 请求）
    time.sleep(delay)
    try:
        req = make_request(pdf_url, email, {"Accept": "application/pdf"})
        req.method = "HEAD"
        with urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if resp.status == 200 and ("pdf" in content_type.lower() or "octet-stream" in content_type.lower()):
                return pdf_url
    except HTTPError as e:
        if e.code == 403 or e.code == 404:
            pass  # 无 PDF
        else:
            print(f"    [!] PMC HEAD check for {pmcid}: HTTP {e.code}")
    return None


def check_pmc_via_pmid(pmid, email, delay):
    """通过 PMID 检查是否在 PMC 有全文，返回 (pmcid, pdf_url)"""
    url = (f"{NCBI_EFETCH}?db=pubmed&id={pmid}&retmode=xml"
           f"&email={quote(email, safe='')}&tool=litreview")
    time.sleep(delay)
    xml_text = fetch_xml(url, email)
    if not xml_text:
        return None, None

    # 从 XML 中提取 PMC ID
    match = re.search(r'<ArticleId IdType="pmc">PMC(\d+)</ArticleId>', xml_text)
    if match:
        pmcid = match.group(1)
        pdf_url = get_pmc_pdf_url(pmcid, email, delay)
        return pmcid, pdf_url

    return None, None


# ─── Unpaywall 查询 ────────────────────────────────────

def check_unpaywall(doi, email, delay):
    """通过 Unpaywall API 查询 OA 状态，返回 (is_oa, best_pdf_url, oa_status)"""
    if not email or "@" not in email or email.endswith("@example.com"):
        print(f"    [!] Unpaywall requires a real email address. Use --email your@email.com")
        return False, None, "no_email"
    url = UNPAYWALL_API.format(doi=quote(doi, safe='')) + f"?email={quote(email, safe='')}"
    time.sleep(delay)
    data = fetch_json(url, email)
    if not data:
        return False, None, "api_error"
    # Unpaywall 422 = invalid email
    if data.get("HTTP_status_code") == 422:
        print(f"    [!] Unpaywall: {data.get('message', 'Invalid request')}")
        print(f"    [!] Provide a real email with --email your@email.com")
        return False, None, "api_error"

    is_oa = data.get("is_oa", False)
    oa_status = data.get("oa_status", "closed")

    if not is_oa:
        return False, None, oa_status

    # 收集所有候选 PDF URL（按优先级排序）
    candidates = []

    for loc in data.get("oa_locations", []):
        pdf_url = loc.get("url_for_pdf", "")
        landing_url = loc.get("url_for_landing_page", "")
        host_type = loc.get("host_type", "")
        is_best = loc.get("is_best", False)

        # 跳过纯 DOI 重定向 URL（如 https://doi.org/10.xxx — 不是真正的 PDF）
        if pdf_url and not pdf_url.startswith("https://doi.org/"):
            score = 0
            # 直接 PDF 链接优先
            if pdf_url.lower().endswith(".pdf"):
                score += 100
            # PMC repository 优先
            if host_type == "repository" and "pmc" in landing_url.lower():
                score += 50
            # best_oa_location 优先
            if is_best:
                score += 20
            # 原始 PDF（非 HTML 页面）
            if "/pdf/" in pdf_url.lower():
                score += 10
            candidates.append((score, pdf_url, host_type))

    # 按分数降序排列
    candidates.sort(key=lambda x: x[0], reverse=True)

    if candidates:
        best_pdf_url = candidates[0][1]
        print(f"    Unpaywall: {len(candidates)} candidate(s), best: {best_pdf_url[:100]}")
        return True, best_pdf_url, oa_status

    # 降级：尝试 best_oa_location 的 landing page URL
    best_loc = data.get("best_oa_location", {})
    landing = best_loc.get("url_for_landing_page", "")
    if landing and not landing.startswith("https://doi.org/"):
        return True, landing, oa_status

    return True, None, oa_status


# ─── PDF 下载 ──────────────────────────────────────────

def download_pdf(url, dest_path, email, timeout=60):
    """下载 PDF 到指定路径，返回 True/False。跟随最多 5 次 HTTP 重定向。"""
    current_url = url
    for hop in range(5):
        req = make_request(current_url, email, {"Accept": "application/pdf"})
        try:
            with urlopen(req, timeout=timeout) as resp:
                # 处理重定向
                if resp.status in (301, 302, 303, 307, 308):
                    new_url = resp.headers.get("Location", "")
                    if new_url:
                        current_url = new_url
                        continue
                if resp.status == 200:
                    data = resp.read()
                    # 检查是否是有效的 PDF（以 %PDF 开头）
                    if data[:4] == b"%PDF":
                        with open(dest_path, "wb") as f:
                            f.write(data)
                        return True
                    else:
                        print(f"    [!] Response is not a PDF (starts with: {data[:50]})")
                        return False
                else:
                    if hop == 0:
                        print(f"    [!] HTTP {resp.status} for {current_url[:80]}")
                    return False
        except HTTPError as e:
            if hop == 0:
                print(f"    [!] Download error: HTTP {e.code}")
            return False
        except URLError as e:
            if hop == 0:
                print(f"    [!] Download error: {e.reason}")
            return False
    print(f"    [!] Too many redirects")
    return False


# ─── 主下载流程 ────────────────────────────────────────

def process_literature(csv_path, outdir, email, delay, dry_run, max_pdfs,
                       pmid_col, doi_col, title_col, year_col):
    """主流程：遍历文献 CSV，逐篇尝试下载 OA PDF"""
    rows = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    total = len(rows)
    print(f"\n{'='*60}")
    print(f"  OA PDF Downloader")
    print(f"  Total entries: {total}")
    print(f"  Dry run: {dry_run}")
    print(f"  Max PDFs: {max_pdfs if max_pdfs else 'unlimited'}")
    print(f"{'='*60}\n")

    # 创建输出目录
    pdf_dir = Path(outdir) / "pdfs"
    if not dry_run:
        pdf_dir.mkdir(parents=True, exist_ok=True)

    results = []
    stats = {
        "total": total,
        STATUS_AUTO: 0,
        STATUS_OA_NO_PDF: 0,
        STATUS_PAYWALL: 0,
        STATUS_NO_FULLTEXT: 0,
        STATUS_ERROR: 0,
        STATUS_SKIPPED: 0,
        STATUS_NO_DOI_PMID: 0,
    }
    downloaded_count = 0

    for idx, row in enumerate(rows):
        title   = safe_val(row, title_col)
        pmid    = safe_val(row, pmid_col)
        doi_raw = safe_val(row, doi_col)
        year    = safe_val(row, year_col, "?")
        doi     = clean_doi(doi_raw)

        print(f"[{idx+1}/{total}] {title[:70]}...")

        if max_pdfs and downloaded_count >= max_pdfs:
            stats[STATUS_SKIPPED] += 1
            results.append({
                "title": title, "pmid": pmid, "doi": doi, "year": year,
                "status": STATUS_SKIPPED, "source": "", "oa_status": "",
                "pdf_url": "", "local_path": "", "note": f"max_pdfs={max_pdfs} reached",
            })
            continue

        result = {
            "title": title,
            "pmid": pmid,
            "doi": doi,
            "year": year,
            "status": STATUS_NO_DOI_PMID,
            "source": "",
            "oa_status": "",
            "pdf_url": "",
            "local_path": "",
            "note": "",
        }

        pdf_url = None
        source  = ""

        # ── 策略 1: PMID → PMC ──
        if pmid:
            print(f"    Checking PMC via PMID {pmid}...")
            pmcid, pmc_pdf = check_pmc_via_pmid(pmid, email, delay)
            if pmc_pdf:
                pdf_url = pmc_pdf
                source = f"PMC:{pmcid}"
                print(f"    [OK] Found PMC PDF: {pmc_pdf}")

        # ── 策略 2: DOI → Unpaywall ──
        if not pdf_url and doi:
            print(f"    Checking Unpaywall via DOI {doi}...")
            is_oa, uw_pdf, oa_status = check_unpaywall(doi, email, delay)
            result["oa_status"] = oa_status
            if is_oa and uw_pdf:
                pdf_url = uw_pdf
                source = f"Unpaywall ({oa_status})"
                print(f"    [OK] Found OA PDF: {uw_pdf}")
            elif is_oa and not uw_pdf:
                result["status"] = STATUS_OA_NO_PDF
                result["note"] = f"OA ({oa_status}) but no PDF URL"
                print(f"    [WARN] OA ({oa_status}) but no PDF URL found")
            else:
                result["status"] = STATUS_PAYWALL
                result["note"] = f"Paywall ({oa_status})"
                print(f"    [SKIP] Paywall ({oa_status})")

        # ── 策略 3: 标题兜底 ──
        if not pdf_url and title and not pmid:
            print(f"    Searching PMC by title...")
            pmcid = search_pmcid_by_title(title, email, delay)
            if pmcid:
                pmc_pdf = get_pmc_pdf_url(pmcid, email, delay)
                if pmc_pdf:
                    pdf_url = pmc_pdf
                    source = f"PMC:{pmcid} (title match)"
                    print(f"    [OK] Found PMC PDF by title: {pmc_pdf}")

        # ── 下载 ──
        if pdf_url:
            safe_filename = re.sub(r'[<>:"/\\|?*]', '_', title[:80])
            local_path = pdf_dir / f"{safe_filename}.pdf"

            if not dry_run:
                print(f"    Downloading...")
                if download_pdf(pdf_url, str(local_path), email):
                    file_size = local_path.stat().st_size
                    result["status"] = STATUS_AUTO
                    result["source"] = source
                    result["pdf_url"] = pdf_url
                    result["local_path"] = str(local_path)
                    result["note"] = f"{file_size:,} bytes"
                    stats[STATUS_AUTO] += 1
                    downloaded_count += 1
                    print(f"    [SAVED] {local_path.name} ({file_size:,} bytes)")
                else:
                    result["status"] = STATUS_ERROR
                    result["source"] = source
                    result["pdf_url"] = pdf_url
                    result["note"] = "Download failed (not a PDF or network error)"
                    stats[STATUS_ERROR] += 1
            else:
                result["status"] = STATUS_AUTO
                result["source"] = source
                result["pdf_url"] = pdf_url
                result["note"] = "[DRY RUN] would download"
                stats[STATUS_AUTO] += 1
                downloaded_count += 1
                print(f"    [DRY RUN] Would download: {pdf_url}")

            result["oa_status"] = result.get("oa_status", "oa")
        elif result["status"] == STATUS_NO_DOI_PMID:
            result["note"] = "No DOI or PMID available"
            stats[STATUS_NO_DOI_PMID] += 1
            print(f"    [SKIP] No DOI or PMID")
        else:
            # 已有状态 (paywall / oa_no_pdf)
            current_status = result["status"]
            stats[current_status] += 1

        results.append(result)
        print()  # 空行分隔

    # ── 输出报告 ──
    _write_report_csv(results, outdir)
    _write_summary_md(stats, results, outdir, total)

    print(f"\n{'='*60}")
    print(f"  Summary")
    print(f"  Auto-downloaded:  {stats[STATUS_AUTO]:>3d}")
    print(f"  Paywall:          {stats[STATUS_PAYWALL]:>3d}")
    print(f"  OA (no PDF):      {stats[STATUS_OA_NO_PDF]:>3d}")
    print(f"  No fulltext:      {stats[STATUS_NO_FULLTEXT]:>3d}")
    print(f"  Error:            {stats[STATUS_ERROR]:>3d}")
    print(f"  No identifier:    {stats[STATUS_NO_DOI_PMID]:>3d}")
    print(f"  Skipped:          {stats[STATUS_SKIPPED]:>3d}")
    print(f"  {'─'*20}")
    print(f"  Total:            {total:>3d}")
    print(f"{'='*60}")

    return results, stats


def _write_report_csv(results, outdir):
    """写 CSV 详细报告"""
    report_path = Path(outdir) / "pdf_download_report.csv"
    fieldnames = ["title", "pmid", "doi", "year", "status", "source",
                  "oa_status", "pdf_url", "local_path", "note"]
    with open(report_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"[Report] {report_path}")


def _write_summary_md(stats, results, outdir, total):
    """写 Markdown 汇总"""
    summary_path = Path(outdir) / "pdf_download_summary.md"
    succeeded = stats[STATUS_AUTO]
    failed = total - succeeded - stats[STATUS_SKIPPED]
    pct = (succeeded / total * 100) if total > 0 else 0

    lines = [
        f"# PDF Download Summary",
        f"",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"## Overall Stats",
        f"",
        f"| Status | Count | % |",
        f"|--------|-------|---|",
        f"| Auto-downloaded | {succeeded} | {pct:.1f}% |",
        f"| Paywall | {stats[STATUS_PAYWALL]} | {stats[STATUS_PAYWALL]/total*100:.1f}% |",
        f"| OA (no PDF) | {stats[STATUS_OA_NO_PDF]} | {stats[STATUS_OA_NO_PDF]/total*100:.1f}% |",
        f"| No fulltext | {stats[STATUS_NO_FULLTEXT]} | {stats[STATUS_NO_FULLTEXT]/total*100:.1f}% |",
        f"| Error | {stats[STATUS_ERROR]} | {stats[STATUS_ERROR]/total*100:.1f}% |",
        f"| No identifier | {stats[STATUS_NO_DOI_PMID]} | {stats[STATUS_NO_DOI_PMID]/total*100:.1f}% |",
        f"| Skipped | {stats[STATUS_SKIPPED]} | {stats[STATUS_SKIPPED]/total*100:.1f}% |",
        f"| **Total** | **{total}** | **100%** |",
        f"",
        f"## Next Steps",
        f"",
        f"- **Downloaded PDFs** are in `pdfs/` directory",
        f"- **Paywall entries** require institutional access or manual retrieval:",
    ]

    # 列出付费墙文章
    paywall_entries = [r for r in results if r["status"] == STATUS_PAYWALL]
    if paywall_entries:
        for r in paywall_entries[:20]:
            lines.append(f"  - {r['title'][:80]} (DOI: {r['doi']})")
        if len(paywall_entries) > 20:
            lines.append(f"  - ... and {len(paywall_entries)-20} more")

    lines += [
        f"",
        f"## Tips for Paywall Papers",
        f"",
        f"1. **Institutional access**: Connect via university VPN, then retry",
        f"2. **Zotero Find Available PDF**: Import into Zotero first, right-click to search",
        f"3. **PubMed Central**: Check https://www.ncbi.nlm.nih.gov/pmc/ manually by PMID",
        f"4. **Google Scholar**: Search title on scholar.google.com — may find preprint/author copy",
        f"5. **ResearchGate**: Request directly from authors",
    ]

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[Report] {summary_path}")


# ─── CLI ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="OA PDF downloader for literature reviews",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("csv_path", help="Path to literature CSV file")
    parser.add_argument("--outdir", default=".", help="Output directory (default: .)")
    parser.add_argument("--email", default=None,
                        help="Your real email (required for Unpaywall API; e.g. name@qq.com)")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Delay between API requests in seconds (default: 1.0)")
    parser.add_argument("--dry-run", action="store_true", help="Only check availability, no download")
    parser.add_argument("--max-pdfs", type=int, default=None,
                        help="Max PDFs to download (for testing)")
    parser.add_argument("--pmid-col", default="PMID", help="CSV column name for PMID")
    parser.add_argument("--doi-col", default="DOI", help="CSV column name for DOI")
    parser.add_argument("--title-col", default="Title", help="CSV column name for Title")
    parser.add_argument("--year-col", default="Year", help="CSV column name for Year")

    args = parser.parse_args()

    if not os.path.exists(args.csv_path):
        print(f"Error: CSV file not found: {args.csv_path}", file=sys.stderr)
        sys.exit(1)

    if not args.email:
        print("Warning: --email not provided.", file=sys.stderr)
        print("  NCBI API calls will work without it (PMC check).", file=sys.stderr)
        print("  Unpaywall API REQUIRES a real email — will be skipped.", file=sys.stderr)
        print("  Usage: --email yourname@qq.com", file=sys.stderr)
        print("", file=sys.stderr)
        args.email = ""  # empty string = skip Unpaywall

    process_literature(
        csv_path=args.csv_path,
        outdir=args.outdir,
        email=args.email,
        delay=args.delay,
        dry_run=args.dry_run,
        max_pdfs=args.max_pdfs,
        pmid_col=args.pmid_col,
        doi_col=args.doi_col,
        title_col=args.title_col,
        year_col=args.year_col,
    )


if __name__ == "__main__":
    main()
