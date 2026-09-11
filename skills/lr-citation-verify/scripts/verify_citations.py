#!/usr/bin/env python3
"""
lr-citation-verify / 引用验证器

对 full_draft.md 中的引用执行 7 层验证中的 5 层自动化检查：
  Layer 1: 证据库交叉比对 —— 引用是否在 reading_notes/ 中有精读笔记
  Layer 2: PubMed esummary —— PMID 是否真实存在
  Layer 3: Crossref DOI —— DOI 是否有效
  Layer 4: Google Scholar 搜索 —— 标题是否可检索到
  Layer 6: 参考文献完整性 —— 缺失字段 / 重复项 / 格式一致性

Layer 5 (数据点溯源) 和 Layer 7 (幻觉标记扫描) 需要 LLM 语义判断，不在本脚本范围。

用法:
    python verify_citations.py full_draft.md --notes-dir reading_notes/ [--outdir .]
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter


# ============================================================
# Layer 1: 证据库交叉比对
# ============================================================

def extract_citations_from_draft(draft_path):
    """Extract citation references from full_draft.md.
    
    Supports patterns:
        [1], [2,3], [4-6]
        (Author, Year)
        PMID: 12345678
        DOI: 10.xxxx/xxxxx
    """
    with open(draft_path, 'r', encoding='utf-8') as f:
        text = f.read()

    citations = []

    # Pattern 1: bracketed numbers [1], [2,3], [4-6]
    for m in re.finditer(r'\[(\d+(?:[, -]\d+)*)\]', text):
        nums = []
        for part in re.split(r'[,;]', m.group(1)):
            part = part.strip()
            if '-' in part:
                a, b = part.split('-', 1)
                nums.extend(range(int(a.strip()), int(b.strip()) + 1))
            else:
                nums.append(int(part))
        for n in nums:
            citations.append({'ref_num': n, 'raw': m.group(0), 'pos': m.start()})

    # Pattern 2: PMID references
    for m in re.finditer(r'PMID[:\s]*(\d{7,8})', text, re.IGNORECASE):
        citations.append({
            'ref_num': None, 'raw': m.group(0), 'pos': m.start(),
            'pmid': m.group(1)
        })

    # Pattern 3: DOI references
    for m in re.finditer(r'DOI[:\s]*(10\.\d{4,}/[^\s,;.]+)', text, re.IGNORECASE):
        citations.append({
            'ref_num': None, 'raw': m.group(0), 'pos': m.start(),
            'doi': m.group(1).rstrip('.')
        })

    return citations


def scan_reading_notes(notes_dir):
    """Scan all reading notes and build an evidence index."""
    evidence = {}
    if not os.path.isdir(notes_dir):
        print(f"  ! reading_notes/ not found: {notes_dir}", file=sys.stderr)
        return evidence

    for fname in os.listdir(notes_dir):
        if not fname.endswith('.md'):
            continue
        fpath = os.path.join(notes_dir, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()

        pmid_match = re.search(r'PMID[:\s]*(\d+)', content, re.IGNORECASE)
        doi_match = re.search(r'DOI[:\s]*(10\.\d{4,}/[^\s]+)', content, re.IGNORECASE)
        title_match = re.search(r'^#\s*(.+)', content, re.MULTILINE)

        pmid = pmid_match.group(1) if pmid_match else None
        doi = doi_match.group(1).rstrip('.') if doi_match else None
        title = title_match.group(1).strip() if title_match else fname.replace('.md', '')

        evidence[fname] = {
            'file': fname, 'title': title, 'pmid': pmid, 'doi': doi, 'path': fpath
        }

    return evidence


def crosscheck_layer1(citations, evidence, ref_list):
    """Layer 1: Check each reference against reading notes evidence.
    
    Returns list of dicts with verdict and details.
    """
    results = []
    for i, cit in enumerate(citations):
        verdict = 'WARN'
        detail = ''
        matched_notes = []

        ref_num = cit.get('ref_num')
        if ref_num is not None:
            # Look up in reference list
            if ref_num in ref_list:
                ref_entry = ref_list[ref_num]
                ref_title = ref_entry.get('title', '')
                ref_pmid = ref_entry.get('pmid', '')
                ref_doi = ref_entry.get('doi', '')

                # Try to match against reading notes
                for key, ev in evidence.items():
                    matched = False
                    if ref_pmid and ev.get('pmid') == ref_pmid:
                        matched = True
                    elif ref_doi and ev.get('doi') == ref_doi:
                        matched = True
                    elif ref_title and _title_similarity(ref_title, ev.get('title', '')) > 0.7:
                        matched = True
                    if matched:
                        matched_notes.append(key)
                        break

        if matched_notes:
            verdict = 'PASS'
            detail = f"Found in reading notes: {', '.join(matched_notes[:3])}"
        elif ref_num is not None:
            detail = f"Reference [{ref_num}] not found in reading_notes/ — may need new note"
        else:
            detail = "Inline citation not linked to reference list"

        results.append({
            'index': i, 'ref_num': ref_num,
            'raw': cit.get('raw', '')[:60],
            'verdict': verdict, 'layer': 'L1_evidence',
            'detail': detail, 'matched_notes': matched_notes
        })

    return results


# ============================================================
# Layer 2: PubMed esummary 验证
# ============================================================

def pubmed_esummary(pmid):
    """Verify a PMID exists via PubMed esummary API."""
    url = (f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
           f'?db=pubmed&id={pmid}&retmode=json')
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        result = data.get('result', {})
        if str(pmid) in result:
            article = result[str(pmid)]
            return {
                'exists': True,
                'title': article.get('title', ''),
                'pubdate': article.get('pubdate', ''),
                'source': article.get('source', ''),
                'doi': article.get('elocationid', '').replace('doi: ', ''),
            }
        return {'exists': False}
    except Exception as e:
        return {'exists': False, 'error': str(e)}


def verify_layer2(ref_list):
    """Layer 2: Verify all PMIDs in reference list via PubMed API."""
    results = []
    count = 0
    for ref_num, ref in sorted(ref_list.items()):
        pmid = ref.get('pmid', '')
        if not pmid:
            results.append({
                'ref_num': ref_num, 'pmid': '', 'verdict': 'WARN',
                'layer': 'L2_pubmed', 'detail': 'No PMID to verify'
            })
            continue

        count += 1
        info = pubmed_esummary(pmid)
        if info['exists']:
            results.append({
                'ref_num': ref_num, 'pmid': pmid, 'verdict': 'PASS',
                'layer': 'L2_pubmed',
                'detail': f"Confirmed: {info.get('title', '')[:80]}",
                'pubmed_title': info.get('title', '')
            })
        else:
            results.append({
                'ref_num': ref_num, 'pmid': pmid, 'verdict': 'FAIL',
                'layer': 'L2_pubmed',
                'detail': f"PMID {pmid} not found in PubMed"
            })

        if count % 3 == 0:
            time.sleep(0.5)  # Rate limit

    return results


# ============================================================
# Layer 3: Crossref DOI 验证
# ============================================================

def crossref_verify(doi):
    """Verify a DOI via Crossref API."""
    url = f'https://api.crossref.org/works/{urllib.parse.quote(doi)}'
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'LiteratureReviewPipeline/1.0 (mailto:researcher@example.com)'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        msg = data.get('message', {})
        titles = msg.get('title', [])
        return {
            'valid': True,
            'title': titles[0] if titles else '',
            'container': msg.get('container-title', [''])[0] if msg.get('container-title') else '',
        }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {'valid': False, 'error': 'DOI not found (404)'}
        return {'valid': False, 'error': f'HTTP {e.code}'}
    except Exception as e:
        return {'valid': False, 'error': str(e)}


def verify_layer3(ref_list):
    """Layer 3: Verify all DOIs in reference list via Crossref API."""
    results = []
    count = 0
    for ref_num, ref in sorted(ref_list.items()):
        doi = ref.get('doi', '')
        if not doi:
            results.append({
                'ref_num': ref_num, 'doi': '', 'verdict': 'WARN',
                'layer': 'L3_crossref', 'detail': 'No DOI to verify'
            })
            continue

        count += 1
        info = crossref_verify(doi)
        if info['valid']:
            results.append({
                'ref_num': ref_num, 'doi': doi, 'verdict': 'PASS',
                'layer': 'L3_crossref',
                'detail': f"Confirmed: {info.get('title', '')[:80]}"
            })
        else:
            results.append({
                'ref_num': ref_num, 'doi': doi, 'verdict': 'FAIL',
                'layer': 'L3_crossref',
                'detail': f"DOI verification failed: {info.get('error', 'unknown')}"
            })

        if count % 3 == 0:
            time.sleep(0.3)

    return results


# ============================================================
# Layer 4: Google Scholar 搜索
# ============================================================

def scholar_search_title(title):
    """Check if a paper title is findable via Google Scholar.
    
    Uses a simple HTTP HEAD request to scholar.google.com with the title as query.
    Returns whether results were returned (non-empty page).
    """
    query = urllib.parse.quote(title[:200])
    url = f'https://scholar.google.com/scholar?q={query}&hl=en&as_sdt=0%2C5'
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/120.0.0.0 Safari/537.36')
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode('utf-8', errors='ignore')
        # Check if results exist (not a "no results" or CAPTCHA page)
        has_results = ('gs_ri' in body or 'gs_rt' in body) and 'did not match any articles' not in body
        if 'sorry' in body.lower() and 'captcha' in body.lower():
            return {'findable': None, 'detail': 'CAPTCHA blocked'}
        return {'findable': has_results, 'detail': 'Results found' if has_results else 'No results'}
    except Exception as e:
        return {'findable': None, 'detail': f'Network error: {e}'}


def verify_layer4(ref_list):
    """Layer 4: Verify reference titles are searchable on Google Scholar."""
    results = []
    count = 0
    for ref_num, ref in sorted(ref_list.items()):
        title = ref.get('title', '')
        if not title:
            results.append({
                'ref_num': ref_num, 'verdict': 'WARN',
                'layer': 'L4_scholar', 'detail': 'No title to search'
            })
            continue

        count += 1
        info = scholar_search_title(title)
        if info['findable'] is True:
            results.append({
                'ref_num': ref_num, 'verdict': 'PASS',
                'layer': 'L4_scholar', 'detail': info['detail']
            })
        elif info['findable'] is None:
            results.append({
                'ref_num': ref_num, 'verdict': 'WARN',
                'layer': 'L4_scholar', 'detail': info['detail']
            })
        else:
            results.append({
                'ref_num': ref_num, 'verdict': 'FAIL',
                'layer': 'L4_scholar', 'detail': info['detail']
            })

        time.sleep(2.0)  # Heavy rate limit for Scholar

    return results


# ============================================================
# Layer 6: 参考文献完整性
# ============================================================

def verify_layer6(ref_list):
    """Layer 6: Check reference list for completeness issues."""
    issues = []

    # Check each reference
    for ref_num, ref in sorted(ref_list.items()):
        missing = []
        if not ref.get('author', '').strip():
            missing.append('author')
        if not ref.get('title', '').strip():
            missing.append('title')
        if not ref.get('journal', '').strip():
            missing.append('journal')
        if not ref.get('year', '').strip():
            missing.append('year')
        if not ref.get('volume', '').strip() and not ref.get('doi', '').strip():
            missing.append('volume')
        if not ref.get('pages', '').strip() and not ref.get('doi', '').strip():
            missing.append('pages')

        if missing:
            issues.append({
                'ref_num': ref_num, 'issue': 'missing_fields',
                'detail': f"Missing: {', '.join(missing)}",
                'severity': 'high' if 'title' in missing or 'pmid' in missing else 'medium'
            })

    # Check for duplicates
    titles_seen = defaultdict(list)
    dois_seen = defaultdict(list)
    for ref_num, ref in sorted(ref_list.items()):
        title = ref.get('title', '').strip().lower()
        doi = ref.get('doi', '').strip().lower()
        if title:
            titles_seen[title].append(ref_num)
        if doi:
            dois_seen[doi].append(ref_num)

    for title, nums in titles_seen.items():
        if len(nums) > 1 and len(title) > 10:
            issues.append({
                'ref_num': nums[0], 'issue': 'duplicate_title',
                'detail': f"Duplicate of ref [{', '.join(str(n) for n in nums[1:])}]: {title[:60]}",
                'severity': 'high'
            })

    for doi, nums in dois_seen.items():
        if len(nums) > 1:
            issues.append({
                'ref_num': nums[0], 'issue': 'duplicate_doi',
                'detail': f"Same DOI as ref [{', '.join(str(n) for n in nums[1:])}]",
                'severity': 'high'
            })

    # Format consistency check (GB/T 7714)
    # Count refs with/without DOI
    with_doi = sum(1 for r in ref_list.values() if r.get('doi', '').strip())
    without_doi = len(ref_list) - with_doi
    if without_doi > len(ref_list) * 0.3:
        issues.append({
            'ref_num': 0, 'issue': 'doi_coverage',
            'detail': f"Only {with_doi}/{len(ref_list)} refs have DOI ({with_doi/len(ref_list)*100:.0f}%)",
            'severity': 'medium'
        })

    return issues


# ============================================================
# Reference List Parser
# ============================================================

def parse_reference_list(draft_path):
    """Parse the numbered reference list from the end of full_draft.md.
    
    Returns dict: {ref_num: {author, title, journal, year, volume, pages, doi, pmid}}
    """
    with open(draft_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # Find reference section
    ref_section_match = re.search(
        r'(?:##\s*参考文献|##\s*References|#\s*参考文献|#\s*References)\s*\n+(.*)',
        text, re.DOTALL | re.IGNORECASE
    )
    if not ref_section_match:
        print("  ! Could not find references section", file=sys.stderr)
        return {}

    ref_text = ref_section_match.group(1)
    ref_list = {}

    # Match each numbered entry: [1] ... or 1. ...
    pattern = r'(?:^|\n)\[?(\d+)\]?[.\s]+(.+?)(?=\n\[?\d+\]?[.\s]|\Z)'
    for m in re.finditer(pattern, ref_text, re.DOTALL):
        num = int(m.group(1))
        entry = m.group(2).strip()

        ref = {'raw': entry[:300]}

        # Extract DOI
        doi_m = re.search(r'(?:doi|DOI)[:\s]*(10\.\d{4,}/[^\s]+)', entry)
        ref['doi'] = doi_m.group(1).rstrip('.') if doi_m else ''

        # Extract PMID
        pmid_m = re.search(r'(?:PMID|pmid)[:\s]*(\d{7,8})', entry)
        ref['pmid'] = pmid_m.group(1) if pmid_m else ''

        # Extract year
        year_m = re.search(r'(\d{4})', entry)
        ref['year'] = year_m.group(1) if year_m else ''

        # Extract volume/pages
        vol_m = re.search(r'(\d+)\((\d+)\)[:\s]*(\d+[-–]\d+)', entry)
        if vol_m:
            ref['volume'] = vol_m.group(1)
            ref['issue'] = vol_m.group(2)
            ref['pages'] = vol_m.group(3)

        # First author (first word before comma or period)
        ref['author'] = entry.split(',')[0].split('.')[0].strip() if entry else ''

        # Title (between first period and journal marker)
        parts = re.split(r'[.。]\s*', entry)
        if len(parts) >= 2:
            ref['title'] = parts[1].strip()[:200]

        # Journal (after title/punctuation, before year)
        ref['journal'] = parts[2].strip()[:100] if len(parts) >= 3 else ''

        ref_list[num] = ref

    return ref_list


# ============================================================
# Report Generation
# ============================================================

def _title_similarity(t1, t2):
    """Simple word overlap similarity for title matching."""
    if not t1 or not t2:
        return 0.0
    w1 = set(t1.lower().split())
    w2 = set(t2.lower().split())
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / min(len(w1), len(w2))


def generate_report(l1, l2, l3, l4, l6_issues, ref_count, out_dir):
    """Generate verification_report.md with all layer results."""

    # Count verdicts
    verdicts = Counter()
    for r in l1 + l2 + l3 + l4:
        verdicts[r['verdict']] += 1
    for issue in l6_issues:
        verdicts['WARN' if issue['severity'] == 'high' else 'WARN'] += 1

    report_path = os.path.join(out_dir, 'verification_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('# 引用验证报告 / Citation Verification Report\n\n')
        f.write(f'**总参考文献数:** {ref_count}\n')
        f.write(f'**验证时间:** {time.strftime("%Y-%m-%d %H:%M:%S")}\n\n')

        f.write('## 总览 / Overview\n\n')
        f.write('| 判定 | 数量 | 说明 |\n')
        f.write('|------|------|------|\n')
        f.write(f'| PASS | {verdicts.get("PASS", 0)} | 验证通过 |\n')
        f.write(f'| WARN | {verdicts.get("WARN", 0)} | 需人工确认 |\n')
        f.write(f'| FAIL | {verdicts.get("FAIL", 0)} | 验证失败，必须修复 |\n')

        overall = 'PASS' if verdicts.get('FAIL', 0) == 0 else 'FAIL'
        f.write(f'\n**最终判定:** {overall}\n')

        if verdicts.get('FAIL', 0) > 0:
            f.write('\n> [!CAUTION]\n')
            f.write(f'> 发现 {verdicts["FAIL"]} 条 FAIL 项，必须修复后方可进入润色阶段。\n\n')

        # Layer 1
        f.write('\n---\n\n## Layer 1: 证据库交叉比对\n\n')
        fails_l1 = [r for r in l1 if r['verdict'] == 'FAIL']
        warns_l1 = [r for r in l1 if r['verdict'] == 'WARN']
        if fails_l1:
            f.write('\n### FAIL 项\n\n')
            for r in fails_l1:
                f.write(f"- [{r.get('ref_num', '?')}] {r['detail']}\n")
        if warns_l1:
            f.write('\n### WARN 项\n\n')
            for r in warns_l1[:10]:
                f.write(f"- [{r.get('ref_num', '?')}] {r['detail']}\n")

        # Layer 2
        f.write('\n---\n\n## Layer 2: PubMed esummary 验证\n\n')
        fails_l2 = [r for r in l2 if r['verdict'] == 'FAIL']
        if fails_l2:
            f.write('\n### FAIL 项 (PMID 不存在)\n\n')
            for r in fails_l2:
                f.write(f"- [{r['ref_num']}] PMID {r['pmid']}: {r['detail']}\n")
        else:
            f.write('全部 PMID 通过 PubMed API 验证。\n')

        # Layer 3
        f.write('\n---\n\n## Layer 3: Crossref DOI 验证\n\n')
        fails_l3 = [r for r in l3 if r['verdict'] == 'FAIL']
        if fails_l3:
            f.write('\n### FAIL 项 (DOI 无效)\n\n')
            for r in fails_l3:
                f.write(f"- [{r['ref_num']}] DOI {r['doi']}: {r['detail']}\n")
        else:
            f.write('全部 DOI 通过 Crossref API 验证。\n')

        # Layer 4
        f.write('\n---\n\n## Layer 4: Google Scholar 可检索性\n\n')
        fails_l4 = [r for r in l4 if r['verdict'] == 'FAIL']
        warns_l4 = [r for r in l4 if r['verdict'] == 'WARN']
        passes_l4 = [r for r in l4 if r['verdict'] == 'PASS']
        f.write(f'可检索: {len(passes_l4)} | 不可检索: {len(fails_l4)} | 跳過: {len(warns_l4)}\n')
        if fails_l4:
            f.write('\n### 不可检索的文献 (疑似幻觉)\n\n')
            for r in fails_l4:
                f.write(f"- [{r['ref_num']}] {r['detail']}\n")

        # Layer 6
        f.write('\n---\n\n## Layer 6: 参考文献完整性\n\n')
        if l6_issues:
            f.write('| 编号 | 问题类型 | 详情 | 严重度 |\n')
            f.write('|------|----------|------|--------|\n')
            for issue in l6_issues:
                f.write(f"| [{issue['ref_num']}] | {issue['issue']} | {issue['detail']} | {issue['severity']} |\n")
        else:
            f.write('未发现完整性问题。\n')

        # Recommendation
        f.write('\n---\n\n## 建议 / Recommendations\n\n')
        if verdicts.get('FAIL', 0) > 0:
            f.write('1. **优先修复 FAIL 项**: Layer 2 和 Layer 3 的 FAIL 项意味着引用文献不存在，请回退到 `lr-chapter-writing` 替换引用。\n')
            f.write('2. **逐个确认 WARN 项**: 在继续前人工审查所有 WARN 项。\n')
        else:
            f.write('1. 所有自动化检查通过。可以进入 Layer 5 (数据点溯源) 和 Layer 7 (幻觉标记扫描) 的 LLM 审查。\n')

    return report_path


def generate_results_csv(l1, l2, l3, l4, l6_issues, out_dir):
    """Generate verification_results.csv with per-reference status."""
    csv_path = os.path.join(out_dir, 'verification_results.csv')

    # Consolidate by ref_num
    ref_status = defaultdict(lambda: {
        'L1': 'SKIP', 'L2': 'SKIP', 'L3': 'SKIP', 'L4': 'SKIP', 'L6': 'PASS',
        'detail': ''
    })

    for r in l1:
        num = r.get('ref_num', '?')
        ref_status[num]['L1'] = r['verdict']
        ref_status[num]['detail'] += f"[L1] {r['detail']}; "

    for r in l2:
        num = r['ref_num']
        ref_status[num]['L2'] = r['verdict']
        ref_status[num]['detail'] += f"[L2] {r['detail']}; "

    for r in l3:
        num = r['ref_num']
        ref_status[num]['L3'] = r['verdict']
        ref_status[num]['detail'] += f"[L3] {r['detail']}; "

    for r in l4:
        num = r['ref_num']
        ref_status[num]['L4'] = r['verdict']
        ref_status[num]['detail'] += f"[L4] {r['detail']}; "

    for issue in l6_issues:
        num = issue['ref_num']
        ref_status[num]['L6'] = issue['severity'].upper() if issue['severity'] == 'high' else 'WARN'
        ref_status[num]['detail'] += f"[L6] {issue['detail']}; "

    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['RefNum', 'L1_Evidence', 'L2_PubMed', 'L3_Crossref', 'L4_Scholar', 'L6_Completeness', 'Details'])
        for ref_num in sorted(ref_status.keys(), key=lambda x: (isinstance(x, int), x)):
            s = ref_status[ref_num]
            writer.writerow([ref_num, s['L1'], s['L2'], s['L3'], s['L4'], s['L6'], s['detail'].rstrip('; ')])

    return csv_path


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='引用验证器 — 对文献综述初稿执行 5 层自动化引用验证')
    parser.add_argument('draft', help='full_draft.md 路径')
    parser.add_argument('--notes-dir', default='reading_notes',
                        help='精读笔记目录 (默认 reading_notes/)')
    parser.add_argument('--outdir', '-o', default='.',
                        help='输出目录 (默认当前目录)')
    parser.add_argument('--skip-scholar', action='store_true',
                        help='跳过 Layer 4 Google Scholar 搜索 (慢)')
    parser.add_argument('--skip-crossref', action='store_true',
                        help='跳过 Layer 3 Crossref DOI 验证')
    args = parser.parse_args()

    if not os.path.exists(args.draft):
        print(f"Error: file not found: {args.draft}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.outdir, exist_ok=True)

    print('=' * 60)
    print('  文献综述引用验证器 v1.0')
    print('=' * 60)

    # Parse reference list
    print(f'\nParsing reference list from {args.draft}...')
    ref_list = parse_reference_list(args.draft)
    print(f'  Found {len(ref_list)} references')

    if not ref_list:
        print('  ! No references found — check draft format', file=sys.stderr)
        sys.exit(1)

    # Extract inline citations
    citations = extract_citations_from_draft(args.draft)
    print(f'  Found {len(citations)} inline citation instances')

    # Layer 1: Evidence DB cross-check
    print('\n--- Layer 1: Evidence DB Cross-check ---')
    evidence = scan_reading_notes(args.notes_dir)
    print(f'  Scanned {len(evidence)} reading notes')
    l1_results = crosscheck_layer1(citations, evidence, ref_list)
    l1_stats = Counter(r['verdict'] for r in l1_results)
    print(f'  PASS={l1_stats.get("PASS", 0)} WARN={l1_stats.get("WARN", 0)} FAIL={l1_stats.get("FAIL", 0)}')

    # Layer 2: PubMed esummary
    print('\n--- Layer 2: PubMed esummary ---')
    l2_results = verify_layer2(ref_list)
    l2_stats = Counter(r['verdict'] for r in l2_results)
    print(f'  PASS={l2_stats.get("PASS", 0)} WARN={l2_stats.get("WARN", 0)} FAIL={l2_stats.get("FAIL", 0)}')

    # Layer 3: Crossref DOI
    l3_results = []
    if not args.skip_crossref:
        print('\n--- Layer 3: Crossref DOI ---')
        l3_results = verify_layer3(ref_list)
        l3_stats = Counter(r['verdict'] for r in l3_results)
        print(f'  PASS={l3_stats.get("PASS", 0)} WARN={l3_stats.get("WARN", 0)} FAIL={l3_stats.get("FAIL", 0)}')

    # Layer 4: Google Scholar
    l4_results = []
    if not args.skip_scholar:
        print('\n--- Layer 4: Google Scholar ---')
        print('  (This may take a while due to rate limiting...)')
        l4_results = verify_layer4(ref_list)
        l4_stats = Counter(r['verdict'] for r in l4_results)
        print(f'  PASS={l4_stats.get("PASS", 0)} WARN={l4_stats.get("WARN", 0)} FAIL={l4_stats.get("FAIL", 0)}')

    # Layer 6: Reference completeness
    print('\n--- Layer 6: Reference Completeness ---')
    l6_issues = verify_layer6(ref_list)
    print(f'  Issues found: {len(l6_issues)}')
    for issue in l6_issues:
        severity_flag = '!' if issue['severity'] == 'high' else '-'
        print(f'  [{severity_flag}] [{issue["ref_num"]}] {issue["issue"]}: {issue["detail"]}')

    # Generate reports
    print('\n--- Generating Reports ---')
    report_path = generate_report(l1_results, l2_results, l3_results, l4_results, l6_issues,
                                  len(ref_list), args.outdir)
    print(f'  Report: {report_path}')

    csv_path = generate_results_csv(l1_results, l2_results, l3_results, l4_results, l6_issues,
                                    args.outdir)
    print(f'  CSV:    {csv_path}')

    # Final verdict
    all_fails = [r for r in l2_results if r['verdict'] == 'FAIL'] + \
                [r for r in l3_results if r['verdict'] == 'FAIL']
    print(f'\n{"=" * 60}')
    if all_fails:
        print(f'  VERDICT: FAIL ({len(all_fails)} failures)')
        print(f'  Action: Fix FAIL items, then re-run verification.')
    else:
        print(f'  VERDICT: PASS')
        print(f'  Action: Proceed to Layer 5 & Layer 7 (LLM review).')
    print(f'{"=" * 60}')


if __name__ == '__main__':
    main()
