#!/usr/bin/env python3
"""
lr-search-strategy / 检索式生成器

根据 PICO 框架参数和章节大纲，为各数据库生成结构化的检索策略 JSON。
支持 PubMed、Web of Science、Scopus、CNKI 四种数据库的语法差异。

用法:
    python build_strategy.py --pico pico.json --chapters chapters.json [--lang zh_CN|en_US]
"""

import argparse
import json
import os
import sys
from datetime import datetime

# ============================================================
# 数据库语法模板
# ============================================================

DATABASE_SYNTAX = {
    'pubmed': {
        'name': 'PubMed (NCBI E-utilities)',
        'field_tags': {
            'title_abstract': '[tiab]',
            'title': '[ti]',
            'abstract': '[ab]',
            'mesh': '[MeSH Terms]',
            'all': '[All Fields]',
        },
        'operators': {'AND': ' AND ', 'OR': ' OR ', 'NOT': ' NOT '},
        'group': '({})',
        'date_format': 'YYYY/MM/DD[dp]',
        'retmax_default': 200,
    },
    'wos': {
        'name': 'Web of Science Core Collection',
        'field_tags': {
            'title_abstract': 'TS=',
            'title': 'TI=',
            'abstract': 'AB=',
            'all': 'ALL=',
        },
        'operators': {'AND': ' AND ', 'OR': ' OR ', 'NOT': ' NOT '},
        'group': '({})',
        'date_format': 'YYYY-MM-DD',
        'retmax_default': 200,
    },
    'scopus': {
        'name': 'Scopus',
        'field_tags': {
            'title_abstract': 'TITLE-ABS-KEY()',
            'title': 'TITLE()',
            'abstract': 'ABS()',
            'all': 'ALL()',
        },
        'operators': {'AND': ' AND ', 'OR': ' OR ', 'NOT': ' AND NOT '},
        'group': '({})',
        'date_format': 'YYYY',
        'retmax_default': 200,
        'scopus_note': 'Use TITLE-ABS-KEY() wrapper for combined keyword search',
    },
    'cnki': {
        'name': 'CNKI / \u4e2d\u56fd\u77e5\u7f51',
        'field_tags': {
            'title_abstract': '\u4e3b\u9898=',  # 主题
            'title': '\u7bc7\u540d=',            # 篇名
            'abstract': '\u6458\u8981=',          # 摘要
            'keyword': '\u5173\u952e\u8bcd=',      # 关键词
        },
        'operators': {'AND': ' AND ', 'OR': ' OR ', 'NOT': ' NOT '},
        'group': '({})',
        'date_format': 'YYYY-MM-DD',
        'retmax_default': 100,
        'note': '\u4e13\u4e1a\u68c0\u7d22\u8bed\u6cd5\uff0c\u53ef\u5207\u6362\u5230\u4e13\u4e1a\u68c0\u7d22\u6a21\u5f0f\u590d\u5236\u7c98\u8d34',
    },
}


# ============================================================
# PICO 参数模板
# ============================================================

PICO_TEMPLATE = {
    'population': {
        'en': [], 'zh': [],
        'description': 'Target population (disease, species, demographics)',
    },
    'intervention': {
        'en': [], 'zh': [],
        'description': 'Intervention/technology of interest',
    },
    'comparison': {
        'en': [], 'zh': [],
        'description': 'Comparison (optional for reviews)',
    },
    'outcome': {
        'en': [], 'zh': [],
        'description': 'Outcomes of interest',
    },
}


# ============================================================
# 预置关键词库 (结直肠癌 / 单细胞 / 空间转录组 / 免疫微环境)
# ============================================================

PRESET_KEYWORDS = {
    'crc_population': {
        'en': [
            'colorectal cancer', 'colorectal carcinoma', 'colorectal tumor',
            'colorectal neoplasm', 'colorectal adenocarcinoma',
            'colon cancer', 'colon carcinoma', 'colon adenocarcinoma',
            'rectal cancer', 'rectal carcinoma', 'rectal adenocarcinoma',
            'CRC', 'COAD', 'READ',
        ],
        'zh': [
            '结直肠癌', '结肠癌', '直肠癌', '大肠癌',
            '结直肠肿瘤', '结直肠腺癌',
        ],
        'mesh': 'Colorectal Neoplasms[MeSH]',
    },
    'scrna_tech': {
        'en': [
            'single-cell RNA sequencing', 'scRNA-seq', 'single cell RNA seq',
            'single-cell transcriptomics', 'single cell transcriptome',
            'single-cell sequencing', 'single cell sequencing',
            'scATAC-seq', 'single-cell ATAC-seq',
            'CITE-seq', 'single-cell multiomics',
            'Smart-seq2', '10x Genomics', 'Drop-seq',
        ],
        'zh': [
            '单细胞RNA测序', '单细胞转录组', '单细胞测序',
            'scRNA-seq', '单细胞组学',
        ],
        'mesh': 'Single-Cell Analysis[MeSH] OR Single-Cell Gene Expression Analysis[MeSH]',
    },
    'spatial_tech': {
        'en': [
            'spatial transcriptomics', 'spatial transcriptomic',
            'spatial genomics', 'spatially resolved transcriptomics',
            'Visium', 'MERFISH', 'Slide-seq', 'Stereo-seq',
            'seqFISH', 'Xenium', 'CosMx',
            'spatial proteomics', 'imaging mass cytometry',
            'multiplexed imaging', 'CODEX', 'MIBI',
            'spatial multi-omics',
        ],
        'zh': [
            '空间转录组', '空间转录组学', '空间组学',
            '空间蛋白质组', '空间多组学',
        ],
        'mesh': '',
    },
    'tme_immune': {
        'en': [
            'tumor microenvironment', 'tumour microenvironment', 'TME',
            'immune microenvironment', 'immune infiltration',
            'immune landscape', 'immune cell', 'immune atlas',
            'T cell', 'CD8+ T', 'CD4+ T', 'regulatory T cell',
            'tumor-associated macrophage', 'myeloid cell',
            'dendritic cell', 'neutrophil', 'NK cell',
            'B cell', 'plasma cell',
            'cancer-associated fibroblast', 'CAF',
            'immune checkpoint', 'PD-1', 'PD-L1', 'CTLA-4',
            'immunotherapy response', 'immune evasion',
            'tertiary lymphoid structure', 'TLS',
        ],
        'zh': [
            '肿瘤微环境', '免疫微环境', '免疫浸润', '免疫景观',
            'T细胞', 'CD8', 'CD4', '巨噬细胞',
            '免疫检查点', '免疫治疗', '免疫逃逸',
        ],
        'mesh': 'Tumor Microenvironment[MeSH] OR Lymphocytes, Tumor-Infiltrating[MeSH]',
    },
    'drug_resistance': {
        'en': [
            'drug resistance', 'chemoresistance', 'therapy resistance',
            'chemotherapy resistance', 'immunotherapy resistance',
            '5-fluorouracil resistance', 'oxaliplatin resistance',
            'anti-EGFR resistance', 'cetuximab resistance',
            'anti-PD-1 resistance', 'immune checkpoint inhibitor resistance',
            'treatment refractory', 'refractory colorectal cancer',
        ],
        'zh': [
            '耐药', '化疗耐药', '免疫治疗耐药', '药物抵抗',
            '5-FU耐药', '奥沙利铂耐药', '西妥昔单抗耐药',
        ],
        'mesh': 'Drug Resistance, Neoplasm[MeSH]',
    },
    'prognosis': {
        'en': [
            'prognosis', 'prognostic', 'survival', 'outcome',
            'prognostic biomarker', 'prognostic signature',
            'prognostic model', 'risk score', 'nomogram',
            'overall survival', 'disease-free survival',
            'progression-free survival',
        ],
        'zh': [
            '预后', '生存', '预后标志物', '风险评分',
            '预后模型', '列线图', '总生存期',
        ],
        'mesh': '',
    },
    'methodology': {
        'en': [
            'computational method', 'bioinformatics', 'algorithm',
            'deconvolution', 'cell type annotation',
            'integration', 'multi-omics integration',
            'trajectory inference', 'cell-cell communication',
            'gene regulatory network', 'GRN',
            'machine learning', 'deep learning',
        ],
        'zh': [
            '计算方法', '生物信息学', '算法', '反卷积',
            '整合分析', '多组学整合', '轨迹推断', '细胞通讯',
        ],
        'mesh': '',
    },
}


# ============================================================
# 章节 → 关键词映射
# ============================================================

CHAPTER_KEYWORD_MAP = {
    'intro': ['crc_population', 'tme_immune'],
    'scrna_crc': ['crc_population', 'scrna_tech', 'tme_immune'],
    'spatial_crc': ['crc_population', 'spatial_tech', 'tme_immune'],
    'integration': ['scrna_tech', 'spatial_tech', 'tme_immune', 'methodology'],
    'drug_resistance': ['crc_population', 'drug_resistance', 'tme_immune', 'scrna_tech', 'spatial_tech'],
    'prognosis': ['crc_population', 'prognosis', 'tme_immune', 'scrna_tech', 'spatial_tech'],
    'methodology': ['scrna_tech', 'spatial_tech', 'methodology'],
    'future': ['crc_population', 'scrna_tech', 'spatial_tech', 'tme_immune'],
}


# ============================================================
# 检索式生成
# ============================================================

def build_query_terms(keyword_ids, lang='en'):
    """将关键词 ID 列表转为分组术语 {group_id: [terms]}。"""
    en_groups = {}
    zh_groups = {}
    for kid in keyword_ids:
        if kid in PRESET_KEYWORDS:
            kw = PRESET_KEYWORDS[kid]
            if kw.get('en'):
                en_groups[kid] = kw['en']
            if kw.get('zh'):
                zh_groups[kid] = kw['zh']
    return en_groups, zh_groups

def flatten_groups(groups):
    """展开分组为扁平列表 (向后兼容)。"""
    terms = []
    for g_terms in groups.values():
        terms.extend(g_terms)
    return terms


def terms_to_or(terms, field_tag, operators, wrapper=None):
    """将词列表转为 OR 连接的检索片段。"""
    if not terms:
        return ''

    if wrapper:
        # Scopus: TITLE-ABS-KEY(term1 OR term2)
        inner = operators['OR'].join(f'"{t}"' for t in terms)
        return f'{wrapper}({inner})'
    else:
        parts = [f'{t}{field_tag}' for t in terms]
        return operators['OR'].join(parts)


def build_pubmed_query(en_groups, date_range=''):
    """Build PubMed query (OR within groups, AND between groups)."""
    s = DATABASE_SYNTAX['pubmed']
    parts = []

    for group_id, terms in en_groups.items():
        if terms:
            parts.append(terms_to_or(terms, s['field_tags']['title_abstract'],
                                      s['operators']))

    query = s['operators']['AND'].join(f'({p})' for p in parts if p)

    if date_range:
        query += f' AND ({date_range})'

    return query


def build_wos_query(en_groups, date_range=''):
    """Build WoS query (OR within groups, AND between groups)."""
    s = DATABASE_SYNTAX['wos']
    parts = []

    for group_id, terms in en_groups.items():
        if terms:
            group_str = ' OR '.join(f'"{t}"' for t in terms)
            parts.append(f'{s["field_tags"]["title_abstract"]}=({group_str})')

    return s['operators']['AND'].join(parts)


def build_scopus_query(en_groups, date_range=''):
    """Build Scopus query (OR within groups, AND between groups)."""
    s = DATABASE_SYNTAX['scopus']
    group_queries = []
    for group_id, terms in en_groups.items():
        if terms:
            group_queries.append(terms_to_or(
                terms, '', s['operators'],
                wrapper=s['field_tags']['title_abstract']
            ))
    return s['operators']['AND'].join(f'({q})' for q in group_queries)


def build_cnki_query(zh_groups, date_range=''):
    """Build CNKI query (OR within groups, AND between groups)."""
    s = DATABASE_SYNTAX['cnki']
    group_queries = []
    for group_id, terms in zh_groups.items():
        if terms:
            parts = [f'{s["field_tags"]["title_abstract"]}\'{t}\'' for t in terms]
            group_queries.append(f'({s["operators"]["OR"].join(parts)})')
    return s['operators']['AND'].join(group_queries)


# ============================================================
# 主函数
# ============================================================

def generate_strategy(pico, chapters, language='en_US', date_range='2020-01-01:2026-06-30'):
    """生成完整的检索策略 JSON。"""
    strategy = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'language': language,
            'date_range': date_range,
        },
        'pico': pico,
        'keyword_groups': {},
        'queries': [],
    }

    # 构建 PICO 关键词组
    for domain in ['population', 'intervention', 'comparison', 'outcome']:
        if domain in pico:
            strategy['keyword_groups'][domain] = {
                'en': pico[domain].get('en', []),
                'zh': pico[domain].get('zh', []),
            }

    # 逐章生成检索式
    for ch_id, ch_info in chapters.items():
        chapter_title = ch_info.get('title', ch_id)
        keyword_ids = ch_info.get('keywords', [])

        # 如果没有指定关键词，使用默认映射
        if not keyword_ids:
            # 尝试从 CHAPTER_KEYWORD_MAP 匹配
            for map_key, map_ids in CHAPTER_KEYWORD_MAP.items():
                if map_key in ch_id.lower():
                    keyword_ids = map_ids
                    break

        en_groups, zh_groups = build_query_terms(keyword_ids, language)

        if not en_groups and not zh_groups:
            continue

        # 合并 PICO 关键词到对应分组
        pico_group_map = {
            'population': 'crc_population',
            'intervention': 'technology',
            'outcome': 'tme_immune',
        }
        for domain, group_key in pico_group_map.items():
            if domain in pico and pico[domain].get('en'):
                en_groups[group_key] = list(set(
                    en_groups.get(group_key, []) + pico[domain].get('en', [])
                ))
                if pico[domain].get('zh'):
                    zh_groups[group_key] = list(set(
                        zh_groups.get(group_key, []) + pico[domain].get('zh', [])
                    ))

        # 日期范围格式化
        parts = date_range.split(':')
        from_date = parts[0] if len(parts) > 0 else '2020-01-01'
        to_date = parts[1] if len(parts) > 1 else '2026-06-30'

        query_entry = {
            'id': f'Q_{ch_id}',
            'chapter': ch_id,
            'chapter_title': chapter_title,
            'keyword_groups': keyword_ids,
            'databases': {},
        }

        # PubMed
        pubmed_date = f'{from_date}[dp] : {to_date}[dp]'
        query_entry['databases']['pubmed'] = {
            'query': build_pubmed_query(en_groups, pubmed_date),
            'expected_hits': '50-200',
            'note': 'Copy-paste into PubMed Advanced Search',
        }

        # WoS
        wos_date = f'{from_date} to {to_date}'
        query_entry['databases']['wos'] = {
            'query': build_wos_query(en_groups, wos_date),
            'expected_hits': '50-200',
            'field': 'TS (Topic)',
        }

        # Scopus
        scopus_query = build_scopus_query(en_groups)
        query_entry['databases']['scopus'] = {
            'query': f'{scopus_query} AND PUBYEAR > {from_date[:4]} AND PUBYEAR < {to_date[:4]}',
            'expected_hits': '50-200',
        }

        # CNKI (only zh_CN projects)
        if language == 'zh_CN' and zh_groups:
            cnki_date = f'{from_date}-{to_date}'
            query_entry['databases']['cnki'] = {
                'query': build_cnki_query(zh_groups, cnki_date),
                'expected_hits': '20-80',
                'note': '使用专业检索模式，粘贴到CNKI高级检索中',
            }

        strategy['queries'].append(query_entry)

    return strategy


def main():
    parser = argparse.ArgumentParser(
        description='检索式生成器 — 根据 PICO 和章节大纲生成多数据库检索策略')
    parser.add_argument('--pico', default=None,
                        help='PICO 参数 JSON 文件 (可选，不提供则使用预置默认值)')
    parser.add_argument('--chapters', default=None,
                        help='章节大纲 JSON 文件 (可选)')
    parser.add_argument('--lang', default='en_US', choices=['zh_CN', 'en_US'],
                        help='目标语言 (默认 en_US)')
    parser.add_argument('--date-range', default='2020-01-01:2026-06-30',
                        help='日期范围 (格式: YYYY-MM-DD:YYYY-MM-DD)')
    parser.add_argument('--out', '-o', default='search_strategy.json',
                        help='输出 JSON 路径')
    args = parser.parse_args()

    # 加载 PICO
    pico = {}
    if args.pico and os.path.exists(args.pico):
        with open(args.pico, 'r', encoding='utf-8') as f:
            pico = json.load(f)
    else:
        # 默认 PICO (结直肠癌 + 单细胞/空间转录组 + 免疫微环境)
        pico = {
            'population': {
                'en': PRESET_KEYWORDS['crc_population']['en'],
                'zh': PRESET_KEYWORDS['crc_population']['zh'],
            },
            'intervention': {
                'en': (PRESET_KEYWORDS['scrna_tech']['en'] +
                       PRESET_KEYWORDS['spatial_tech']['en']),
                'zh': (PRESET_KEYWORDS['scrna_tech']['zh'] +
                       PRESET_KEYWORDS['spatial_tech']['zh']),
            },
            'outcome': {
                'en': PRESET_KEYWORDS['tme_immune']['en'],
                'zh': PRESET_KEYWORDS['tme_immune']['zh'],
            },
        }
        print('Using default PICO (colorectal cancer + sc/spatial + TME)')

    # 加载章节
    chapters = {}
    if args.chapters and os.path.exists(args.chapters):
        with open(args.chapters, 'r', encoding='utf-8') as f:
            chapters = json.load(f)
    else:
        # 默认章节 (6章标准结构)
        chapters = {
            'Ch1_Intro': {'title': 'Introduction / Background', 'keywords': ['crc_population', 'tme_immune']},
            'Ch2_scRNA': {'title': 'scRNA-seq in CRC TME', 'keywords': ['crc_population', 'scrna_tech', 'tme_immune']},
            'Ch3_ST': {'title': 'Spatial Transcriptomics in CRC TME', 'keywords': ['crc_population', 'spatial_tech', 'tme_immune']},
            'Ch4_Integration': {'title': 'Multi-omics Integration', 'keywords': ['scrna_tech', 'spatial_tech', 'methodology']},
            'Ch5_DrugResist': {'title': 'Drug Resistance Mechanisms', 'keywords': ['drug_resistance', 'scrna_tech', 'spatial_tech', 'tme_immune']},
            'Ch6_Prognosis': {'title': 'Prognostic Models and Biomarkers', 'keywords': ['prognosis', 'scrna_tech', 'tme_immune']},
        }
        print('Using default chapter structure (6 chapters)')

    # 生成策略
    print(f'\nGenerating search strategy...')
    print(f'  Language: {args.lang}')
    print(f'  Date range: {args.date_range}')

    strategy = generate_strategy(pico, chapters, args.lang, args.date_range)

    # 保存
    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(strategy, f, ensure_ascii=False, indent=2)

    print(f'\nStrategy saved to: {args.out}')
    print(f'  Chapters: {len(strategy["queries"])}')
    print(f'  Databases per chapter: {len(strategy["queries"][0]["databases"]) if strategy["queries"] else 0}')
    print()

    for q in strategy['queries']:
        print(f'  [{q["id"]}] {q["chapter_title"]}')
        for db, info in q['databases'].items():
            print(f'      {db}: {info["query"][:80]}...' if len(info['query']) > 80
                  else f'      {db}: {info["query"]}')


if __name__ == '__main__':
    main()
