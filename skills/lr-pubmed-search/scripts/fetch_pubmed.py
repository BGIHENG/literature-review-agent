#!/usr/bin/env python3
"""
PubMed Literature Fetcher for Literature Review Pipeline
=========================================================
Executes PubMed searches via NCBI E-utilities API, deduplicates results,
fetches article details, auto-tags priority and chapter, outputs literature_db.csv.

Usage:
    python fetch_pubmed.py --queries queries.json --output literature_db.csv
    python fetch_pubmed.py --queries queries.json --output literature_db.csv --retmax 50

queries.json format:
[
    {"id": "Q1_TME", "term": "(colorectal cancer[tiab]) AND (scRNA-seq[tiab]) AND (tumor microenvironment[tiab]) AND (2020/01/01[dp] : 2026/06/30[dp])"},
    {"id": "Q2_DrugResist", "term": "..."},
    ...
]
"""
import urllib.request
import xml.etree.ElementTree as ET
import csv
import json
import time
import os
import argparse
import sys
from collections import Counter

# === Journal tier lists (extend as needed) ===
TOP_JOURNALS = {
    'Cell', 'Nature', 'Science', 'Cancer Cell', 'Cancer Discovery',
    'Nature Medicine', 'Nature Genetics', 'Nature Methods', 'Nature Biotechnology',
    'Gut', 'Gastroenterology', 'Immunity', 'Lancet', 'Lancet Oncol',
    'J Clin Oncol', 'JAMA Oncol', 'Nat Rev Clin Oncol', 'Nat Rev Cancer',
    'Nat Rev Immunol', 'Nat Rev Genet', 'Nat Rev Gastroenterol Hepatol',
    'Lancet Gastroenterol Hepatol', 'Cell Metab', 'Cell Syst',
}

GOOD_JOURNALS = {
    'Nat Commun', 'Cancer Res', 'Clin Cancer Res', 'Genome Biol',
    'Cell Rep', 'J Immunother Cancer', 'J Clin Invest', 'Cancer Lett',
    'Theranostics', 'J Exp Clin Cancer Res', 'Oncogene', 'Cancer Immunol Res',
    'Genome Med', 'Brief Bioinform', 'Bioinformatics', 'Nucleic Acids Res',
    'Genome Res', 'PLoS Comput Biol', 'Cell Rep Methods', 'Int J Cancer',
    'Br J Cancer', 'Front Immunol', 'Front Oncol', 'Cancers',
}

# === Chapter keyword mapping (customize per project) ===
CHAPTER_KEYWORDS = {
    'Ch1_Intro': ['review', 'overview', 'landscape', 'epidemiology', 'incidence', 'mortality', 'global burden', 'challenge', 'future direction', 'limitation'],
    'Ch2_scRNA': ['single-cell', 'single cell', 'scrna', 'transcriptom', 'heterogeneity', 'clone', 'lineage', 'cell type', 'cell atlas', 'immune cell', 'subpopulation', 'subset'],
    'Ch3_ST': ['spatial', 'visium', 'slide-seq', 'merfish', 'stereo-seq', 'niche', 'organization', 'architecture', 'tls', 'tertiary lymphoid', 'ligand', 'receptor', 'cell communication', 'cell-cell interaction'],
    'Ch4_Integration': ['integration', 'integrat', 'multi-omics', 'multiomics', 'multi omics', 'deconvolution', 'joint analysis', 'combined analysis', 'multimodal', 'computational', 'algorithm', 'benchmarking'],
    'Ch5_DrugResist': ['resistance', 'chemoresistance', 'resistant', 'refractory', 'immune evasion', 't cell exhaustion', 'exhaustion', 'metabolic reprogramming', '5-fu', 'oxaliplatin', 'anti-pd', 'anti-egfr', 'immunotherapy', 'checkpoint'],
    'Ch6_Prognosis': ['prognosis', 'prognostic', 'survival', 'prediction', 'predictive', 'model', 'signature', 'risk score', 'nomogram', 'biomarker', 'outcome'],
    'Ch7_Future': ['perspective', 'future', 'challenge', 'frontier'],
}


def esearch(term, retmax=50):
    """Execute PubMed esearch and return (total_count, pmid_list)."""
    base_url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
    params = f'?db=pubmed&retmax={retmax}&retmode=json&sort=relevance&term={urllib.parse.quote(term)}'
    url = base_url + params
    
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        result = data.get('esearchresult', {})
        count = int(result.get('count', 0))
        pmids = result.get('idlist', [])
        return count, [int(p) for p in pmids]
    except Exception as e:
        print(f'  esearch error: {e}', file=sys.stderr)
        return 0, []


def efetch_batch(pmids):
    """Fetch article details for a batch of PMIDs. Returns list of dicts."""
    if not pmids:
        return []
    
    ids_str = ','.join(str(p) for p in pmids)
    url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={ids_str}&retmode=xml&rettype=abstract'
    
    papers = []
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            xml_data = resp.read().decode('utf-8')
        
        root = ET.fromstring(xml_data)
        
        for article in root.findall('.//PubmedArticle'):
            try:
                paper = parse_article(article)
                if paper:
                    papers.append(paper)
            except Exception as e:
                print(f'  parse error: {e}', file=sys.stderr)
                continue
    except Exception as e:
        print(f'  efetch error: {e}', file=sys.stderr)
    
    return papers


def parse_article(article):
    """Parse a single PubmedArticle XML element into a dict."""
    pmid_el = article.find('.//PMID')
    if pmid_el is None:
        return None
    pmid = pmid_el.text
    
    art = article.find('.//MedlineCitation/Article')
    if art is None:
        return None
    
    # Title
    title_el = art.find('.//ArticleTitle')
    title = title_el.text if title_el is not None and title_el.text else ''
    
    # First author
    authors = []
    for author in art.findall('.//Author'):
        last = author.find('LastName')
        if last is not None and last.text:
            authors.append(last.text)
    first_author = authors[0] if authors else ''
    
    # Journal
    journal_el = art.find('.//Journal')
    journal = ''
    if journal_el is not None:
        iso = journal_el.find('ISOAbbreviation')
        if iso is not None and iso.text:
            journal = iso.text
        else:
            jt = journal_el.find('Title')
            if jt is not None and jt.text:
                journal = jt.text
    
    # Year
    year = ''
    ji = art.find('.//JournalIssue')
    if ji is not None:
        pub_date = ji.find('PubDate')
        if pub_date is not None:
            y = pub_date.find('Year')
            if y is not None and y.text:
                year = y.text
            else:
                md = pub_date.find('MedlineDate')
                year = md.text[:4] if md is not None and md.text else ''
    
    # Volume / Issue / Pages
    vol = ''
    issue = ''
    if ji is not None:
        v = ji.find('Volume')
        vol = v.text if v is not None and v.text else ''
        iss = ji.find('Issue')
        issue = iss.text if iss is not None and iss.text else ''
    
    pages = ''
    pag = art.find('.//Pagination/MedlinePgn')
    if pag is not None and pag.text:
        pages = pag.text
    
    # DOI
    doi = ''
    for eid in art.findall('.//ELocationID'):
        if eid.get('EIdType') == 'doi':
            doi = eid.text or ''
            break
    
    # Abstract
    abstract_parts = []
    for ab in art.findall('.//AbstractText'):
        label = ab.get('Label', '')
        text = ab.text or ''
        tail = ab.tail or ''
        if label:
            abstract_parts.append(f'{label}: {text}{tail}')
        else:
            abstract_parts.append(f'{text}{tail}')
    abstract = ' '.join(abstract_parts).strip()
    
    # Publication types
    pub_types = []
    pt_list = art.find('.//PublicationTypeList')
    if pt_list is not None:
        for pt in pt_list.findall('PublicationType'):
            if pt.text:
                pub_types.append(pt.text)
    pub_type_str = '; '.join(pub_types)
    
    return {
        'PMID': pmid,
        'Title': title,
        'FirstAuthor': first_author,
        'Year': year,
        'Journal': journal,
        'Volume': vol,
        'Issue': issue,
        'Pages': pages,
        'DOI': doi,
        'PublicationType': pub_type_str,
        'Abstract': abstract[:600],
    }


def tag_priority(journal):
    """Tag priority based on journal name."""
    if journal in TOP_JOURNALS:
        return '1'
    elif journal in GOOD_JOURNALS:
        return '2'
    return '3'


def tag_chapters(title, abstract, source_queries):
    """Tag chapters based on keyword matching and source query."""
    text = (title + ' ' + abstract).lower()
    chapters = set()
    
    # Keyword-based
    for ch, kws in CHAPTER_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in text)
        if score >= 2:
            chapters.add(ch)
    
    # Source query-based (customize mapping per project)
    for sq in source_queries:
        if 'TME' in sq or 'Methods' in sq:
            chapters.add('Ch2_scRNA')
            chapters.add('Ch3_ST')
        if 'DrugResist' in sq:
            chapters.add('Ch5_DrugResist')
        if 'Prognosis' in sq:
            chapters.add('Ch6_Prognosis')
        if 'Integration' in sq:
            chapters.add('Ch4_Integration')
        if 'Epi' in sq:
            chapters.add('Ch1_Intro')
    
    return '; '.join(sorted(chapters)) if chapters else 'Unassigned'


def main():
    parser = argparse.ArgumentParser(description='Fetch PubMed literature for review pipeline')
    parser.add_argument('--queries', required=True, help='JSON file with search queries')
    parser.add_argument('--output', default='literature_db.csv', help='Output CSV path')
    parser.add_argument('--retmax', type=int, default=50, help='Max results per query')
    args = parser.parse_args()
    
    # Load queries
    with open(args.queries, 'r', encoding='utf-8') as f:
        queries = json.load(f)
    
    print(f'Loaded {len(queries)} search queries')
    
    # Execute esearch for each query
    all_pmids = {}  # pmid -> set of query IDs
    for q in queries:
        qid = q['id']
        term = q['term']
        print(f'\n[{qid}] Searching...')
        count, pmids = esearch(term, args.retmax)
        print(f'  Total hits: {count}, fetched: {len(pmids)}')
        
        for p in pmids:
            if p not in all_pmids:
                all_pmids[p] = set()
            all_pmids[p].add(qid)
        
        time.sleep(0.5)
    
    unique_pmids = list(all_pmids.keys())
    print(f'\n=== {len(unique_pmids)} unique PMIDs after dedup ===')
    
    # Fetch details in batches
    BATCH_SIZE = 50
    papers = []
    
    for i in range(0, len(unique_pmids), BATCH_SIZE):
        batch = unique_pmids[i:i+BATCH_SIZE]
        print(f'Fetching batch {i//BATCH_SIZE + 1}/{(len(unique_pmids)+BATCH_SIZE-1)//BATCH_SIZE}...')
        batch_papers = efetch_batch(batch)
        
        for paper in batch_papers:
            pmid_int = int(paper['PMID'])
            sources = all_pmids.get(pmid_int, set())
            paper['SourceQuery'] = '; '.join(sorted(sources))
            paper['Priority'] = tag_priority(paper['Journal'])
            paper['Chapter'] = tag_chapters(paper['Title'], paper['Abstract'], sources)
            paper['Note'] = ''
            papers.append(paper)
        
        time.sleep(0.5)
    
    print(f'\nFetched {len(papers)} papers')
    
    # Write CSV
    fieldnames = ['PMID', 'Title', 'FirstAuthor', 'Year', 'Journal', 'Volume', 'Issue',
                  'Pages', 'DOI', 'PublicationType', 'Abstract', 'SourceQuery', 'Priority', 'Chapter', 'Note']
    
    out_dir = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(out_dir, exist_ok=True)
    
    with open(args.output, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for paper in papers:
            writer.writerow(paper)
    
    print(f'CSV saved to: {args.output}')
    
    # Summary stats
    print(f'\n=== Summary ===')
    pri = Counter(p['Priority'] for p in papers)
    print(f'Priority: P1={pri.get("1",0)}, P2={pri.get("2",0)}, P3={pri.get("3",0)}')
    
    print(f'\n=== Chapter coverage (P1+P2 only) ===')
    ch_counter = Counter()
    for p in papers:
        if p['Priority'] in ('1', '2'):
            for ch in p['Chapter'].split('; '):
                ch = ch.strip()
                if ch:
                    ch_counter[ch] += 1
    for ch, c in ch_counter.most_common():
        flag = ' ⚠️' if c < 10 else ' ✅'
        print(f'  {ch}: {c}{flag}')


if __name__ == '__main__':
    import urllib.parse
    main()
