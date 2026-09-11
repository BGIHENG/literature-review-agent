#!/usr/bin/env python3
"""
lr-literature-screen / 快速筛选器

对 literature_db.csv 执行第一轮快速筛选（标题 + 摘要关键词匹配），
输出 screened_literature.csv（ScreenStatus = included/excluded/maybe）。

纳入/排除关键词从 project_brief.md 提取，或使用默认的结直肠癌免疫微环境关键词表。

用法:
    python filter_quick.py literature_db.csv [--criteria project_brief.md] [--out screened_literature.csv]
"""

import argparse
import csv
import os
import re
import sys
from collections import Counter


# ============================================================
# 默认关键词表 (结直肠癌 / 单细胞 / 空间转录组 / 免疫微环境)
# ============================================================

INCLUDE_TERMS = {
    'cancer_type': [
        'colorectal cancer', 'colorectal carcinoma', 'crc',
        'colon cancer', 'colon carcinoma', 'rectal cancer', 'rectal carcinoma',
        'colorectal adenocarcinoma', 'colorectal tumor', 'colorectal tumour',
        'colorectal neoplasm', 'colorectal',
        'colorectal cancer', 'colorectal carcinoma', 'crc',
        'colorectal cancer', 'colorectal adenocarcinoma',
    ],
    'technology': [
        'single-cell', 'single cell', 'scrna-seq', 'scrna', 'scatac-seq',
        'spatial transcriptom', 'spatial proteom', 'visium', 'merfish',
        'slide-seq', 'stereo-seq', 'seqfish', 'xenium', 'cosmx',
        'multiplexed imaging', 'imaging mass cytometry', 'cytof',
        'nanostring', '10x genomics', 'smart-seq', 'drop-seq',
    ],
    'biology': [
        'tumor microenvironment', 'tumour microenvironment', 'tme',
        'immune microenvironment', 'immune infiltrat', 'immune cell',
        'immune landscape', 'immune atlas', 'immune profile',
        't cell', 'cd8', 'cd4', 'treg', 'regulatory t',
        'macrophage', 'myeloid', 'monocyte', 'dendritic cell',
        'neutrophil', 'nk cell', 'b cell', 'plasma cell', 'mast cell',
        'fibroblast', 'caf', 'endothelial', 'pericyte',
        'immune checkpoint', 'pd-1', 'pd-l1', 'ctla-4',
        'cytokine', 'chemokine',
        'tertiary lymphoid structure', 'tls',
    ],
}

EXCLUDE_TERMS = {
    'wrong_cancer': [
        'breast cancer', 'lung cancer', 'glioma', 'glioblastoma',
        'leukemia', 'lymphoma', 'myeloma', 'melanoma',
        'hepatocellular', 'pancreatic cancer', 'prostate cancer',
        'ovarian cancer', 'gastric cancer', 'bladder cancer',
        'thyroid cancer', 'renal cell carcinoma',
        'sarcoma', 'neuroblastoma',
    ],
    'wrong_species': [
        'mouse model', 'mice', 'murine', 'zebrafish', 'drosophila',
        'c. elegans', 'arabidopsis', 'yeast', 'rat model',
    ],
    'non_research': [
        'editorial', 'letter to the editor', 'book review', 'news',
        'conference abstract', 'meeting abstract', 'case report',
        'commentary', 'opinion', 'perspective', 'erratum',
        'corrigendum', 'retraction',
    ],
    'no_primary_data': [
        'withdrawn', 'retracted',
    ],
}

# 反排除保护：如果标题包含这些词，即使触发了排除规则也不排除
ANTI_EXCLUDE = [
    'colorectal', 'colon cancer', 'rectal cancer', 'crc',
]


# ============================================================
# 判定逻辑
# ============================================================

def tokenize(text):
    """将文本转为小写 token 集合，用于中文/英文混合匹配。"""
    if not text:
        return set()
    text = text.lower()
    # 英文单词 + 中文单字
    tokens = set(re.findall(r'[a-z0-9]+|[\u4e00-\u9fff]', text))
    # 同时保留 2-4 词短语用于多词匹配
    words = re.findall(r'[a-z]+', text)
    bigrams = {' '.join(words[i:i+2]) for i in range(len(words)-1)}
    trigrams = {' '.join(words[i:i+3]) for i in range(len(words)-2)}
    return tokens | bigrams | trigrams


def check_keywords(text, term_groups, mode='any_group'):
    """检查文本是否匹配关键词组。

    mode='any_group': 每个组至少命中 1 个关键词
    mode='any_term': 任意组命中任意关键词即可
    """
    text_tokens = tokenize(text)
    text_str = text.lower() if text else ''

    for group_name, terms in term_groups.items():
        for term in terms:
            if term in text_str:
                if mode == 'any_term':
                    return True
                break  # This group has a match, check next group
        else:
            if mode == 'any_group':
                return False  # This group had no match

    return True if mode == 'any_group' else False


def screen_paper(title, abstract, pub_type, journal, year):
    """判定单篇文献的纳入/排除状态。

    Returns: (status, reason, confidence)
        status: 'included' | 'excluded' | 'maybe'
        reason: 排除原因代码
    """
    title_lower = (title or '').lower()
    abstract_lower = (abstract or '').lower()
    pub_type_lower = (pub_type or '').lower()
    combined = title_lower + ' ' + abstract_lower

    # --- 排除判定 (先排后排) ---

    # 非研究性文章
    for term in EXCLUDE_TERMS['non_research']:
        if term in pub_type_lower:
            return ('excluded', f'non_research:{term}', 1.0)

    # 撤稿
    for term in EXCLUDE_TERMS['no_primary_data']:
        if term in title_lower:
            return ('excluded', f'{term}', 1.0)

    # 错误癌种 (检查 anti-exclude 保护)
    anti_flag = any(t in combined for t in ANTI_EXCLUDE)
    if not anti_flag:
        for term in EXCLUDE_TERMS['wrong_cancer']:
            if term in combined:
                # 如果标题同时提到结直肠癌 + 其他癌种(比较研究), 不排除
                if any(t in title_lower for t in ANTI_EXCLUDE):
                    break
                return ('excluded', f'wrong_cancer:{term}', 0.8)

    # 纯动物/模式生物研究
    species_score = 0
    animal_terms_hit = []
    for term in EXCLUDE_TERMS['wrong_species']:
        if term in combined:
            species_score += 1
            animal_terms_hit.append(term)
    # 人类研究相关的正向信号
    human_signals = ['patient', 'human', 'clinical', 'cohort', 'tissue', 'sample']
    human_score = sum(1 for t in human_signals if t in combined)
    if species_score >= 2 and human_score < 2:
        return ('excluded', f'wrong_species:{",".join(animal_terms_hit)}', 0.7)

    # --- 纳入判定 ---

    # 必须命中癌种
    cancer_hit = any(t in combined for t in INCLUDE_TERMS['cancer_type'])
    if not cancer_hit:
        # 检查是否是泛癌/pan-cancer 研究
        if 'pan-cancer' in combined or 'pan cancer' in combined:
            cancer_hit = True

    # 必须命中技术
    tech_hit = any(t in combined for t in INCLUDE_TERMS['technology'])
    # 放宽: 单细胞/空间方法学论文
    if not tech_hit:
        if any(t in combined for t in ['computational method', 'bioinformatics', 'tool']):
            tech_hit = True  # 方法学论文

    # 命中生物学 (加分项)
    bio_hit = any(t in combined for t in INCLUDE_TERMS['biology'])

    # 判定
    if cancer_hit and tech_hit and bio_hit:
        return ('included', '', 0.95)
    elif cancer_hit and tech_hit:
        return ('included', 'tech_only', 0.85)
    elif tech_hit and bio_hit:
        # 技术+免疫，但没明确提到结直肠癌 → maybe
        return ('maybe', 'no_cancer_term', 0.5)
    elif cancer_hit and bio_hit:
        # 结直肠癌免疫研究，但没提特定技术 → maybe (可能是用流式/组化的传统研究)
        return ('maybe', 'no_tech_term', 0.4)
    elif cancer_hit:
        return ('maybe', 'cancer_only', 0.3)
    else:
        return ('excluded', 'no_match', 0.9)


# ============================================================
# CSV 处理
# ============================================================

def filter_csv(input_path, output_path):
    """主筛选流程。"""
    if not os.path.exists(input_path):
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    stats = Counter()
    screened = []

    with open(input_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        # 确保输出字段
        extra_fields = ['ScreenStatus', 'ExcludeReason', 'ExcludeReason_EN', 'ScreenRound', 'ReadPriority']
        output_fields = list(fieldnames) + [f for f in extra_fields if f not in (fieldnames or [])]
        if 'ScreenStatus' not in (output_fields or []):
            output_fields = list(fieldnames) + extra_fields

        for row in reader:
            title = row.get('Title', row.get('TI', ''))
            abstract = row.get('Abstract', row.get('AB', ''))
            pub_type = row.get('PublicationType', row.get('PT', ''))
            journal = row.get('Journal', row.get('JO', row.get('SO', '')))
            year = row.get('Year', row.get('PY', row.get('DP', '')))

            status, reason, confidence = screen_paper(title, abstract, pub_type, journal, year)
            stats[status] += 1

            row['ScreenStatus'] = status
            row['ExcludeReason'] = reason
            row['ExcludeReason_EN'] = reason  # 中英文相同（关键词表可扩展）
            row['ScreenRound'] = '1'
            row['ReadPriority'] = ''

            screened.append(row)

    # 输出
    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=output_fields)
        writer.writeheader()
        for row in screened:
            writer.writerow(row)

    print(f"Output: {output_path}")
    print(f"\n=== 快速筛选统计 ===")
    print(f"Total:          {sum(stats.values())}")
    print(f"Included:       {stats.get('included', 0)}")
    print(f"Maybe:          {stats.get('maybe', 0)}")
    print(f"Excluded:       {stats.get('excluded', 0)}")

    # 排除原因分布
    print(f"\n--- 排除原因 Top 10 ---")
    exclude_reasons = Counter(
        r['ExcludeReason'] for r in screened if r['ScreenStatus'] == 'excluded'
    )
    for reason, count in exclude_reasons.most_common(10):
        print(f"  {reason}: {count}")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='文献快速筛选 — 基于标题/摘要关键词的第一轮纳入排除判定')
    parser.add_argument('input', help='literature_db.csv 路径')
    parser.add_argument('--out', '-o', default='screened_literature.csv',
                        help='输出 CSV 路径 (默认 screened_literature.csv)')
    args = parser.parse_args()

    print("=" * 50)
    print("  文献快速筛选器 v1.0")
    print("  Round 1: 标题 + 摘要关键词匹配")
    print("=" * 50)
    print()

    filter_csv(args.input, args.out)


if __name__ == '__main__':
    main()
