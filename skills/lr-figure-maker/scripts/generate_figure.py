#!/usr/bin/env python3
"""
lr-figure-maker / 图表渲染工具库

提供出版级学术图表的配色方案、期刊尺寸模板、统计标注工具和输出函数。
供 AI/LLM 调用生成符合目标期刊规范的图表。

用法 (作为库):
    from generate_figure import colors, journal, stats, export

用法 (CLI 渲染配置):
    python generate_figure.py --config figure_config.json --outdir figures/

figure_config.json format:
{
    "type": "schematic|bar|box|violin|heatmap|timeline|prisma",
    "journal": "nature|cell|science|chinese_core",
    "width": "single|double",
    "color_scheme": "wong2011|okabe_ito|ibm|crc_specific",
    "panels": ["A", "B", "C"],
    "output_formats": ["svg", "png", "eps", "pdf"],
    "data": {...}
}
"""

import argparse
import json
import os
import sys

# ============================================================
# 第一部分: 配色方案
# ============================================================

class ColorScheme:
    """色盲友好配色方案集。"""

    # Wong 2011 (Nature Methods 推荐, 7色)
    WONG_2011 = {
        'black':   '#000000',
        'orange':  '#E69F00',
        'skyblue': '#56B4E9',
        'teal':    '#009E73',
        'yellow':  '#F0E442',
        'blue':    '#0072B2',
        'vermillion': '#D55E00',
        # 别名
        'colors': ['#000000', '#E69F00', '#56B4E9', '#009E73',
                   '#F0E442', '#0072B2', '#D55E00'],
        'names': ['Black', 'Orange', 'Sky Blue', 'Teal',
                  'Yellow', 'Blue', 'Vermillion'],
    }

    # Okabe-Ito (8色, 最广兼容性)
    OKABE_ITO = {
        'colors': ['#000000', '#E69F00', '#56B4E9', '#009E73',
                   '#F0E442', '#0072B2', '#D55E00', '#CC79A7'],
        'names': ['Black', 'Orange', 'Sky Blue', 'Teal',
                  'Yellow', 'Blue', 'Vermillion', 'Pink'],
    }

    # IBM Design Library (低饱和度专业风)
    IBM = {
        'colors': ['#648FFF', '#785EF0', '#DC267F', '#FE6100',
                   '#FFB000', '#009E73', '#56B4E9', '#E69F00',
                   '#F0E442', '#0072B2'],
    }

    # 灰度安全 (黑白印刷)
    GRAYSCALE = {
        'colors': ['#000000', '#404040', '#808080', '#BFBFBF', '#E6E6E6'],
        'hatches': ['/', '\\\\', '|', '-', '+', 'x', 'o', 'O', '.', '*'],
    }

    # CRC 综述专用配色 (免疫细胞类型)
    CRC_IMMUNE = {
        't_cell_cd8':   '#E41A1C',  # 红色 — CD8+ T 细胞
        't_cell_cd4':   '#FB8072',  # 浅红 — CD4+ T 细胞
        'treg':         '#FF7F00',  # 橙色 — Treg
        'nk_cell':      '#FDB462',  # 浅橙 — NK 细胞
        'b_cell':       '#377EB8',  # 蓝色 — B 细胞
        'plasma':       '#A6CEE3',  # 浅蓝 — 浆细胞
        'macrophage':   '#4DAF4A',  # 绿色 — 巨噬细胞
        'monocyte':     '#B2DF8A',  # 浅绿 — 单核细胞
        'dc':           '#33A02C',  # 深绿 — 树突状细胞
        'neutrophil':   '#984EA3',  # 紫色 — 中性粒细胞
        'mast':         '#CAB2D6',  # 浅紫 — 肥大细胞
        'fibroblast':   '#F781BF',  # 粉色 — 成纤维细胞/CAF
        'endothelial':  '#FFFF33',  # 黄色 — 内皮细胞
        'tumor':        '#A65628',  # 棕色 — 肿瘤细胞
        'other':        '#999999',  # 灰色 — 其他
        'colors': [
            '#E41A1C', '#FB8072', '#FF7F00', '#FDB462',
            '#377EB8', '#A6CEE3', '#4DAF4A', '#B2DF8A',
            '#33A02C', '#984EA3', '#CAB2D6', '#F781BF',
            '#FFFF33', '#A65628', '#999999',
        ],
        'names': [
            'CD8+ T', 'CD4+ T', 'Treg', 'NK',
            'B', 'Plasma', 'Macrophage', 'Monocyte',
            'DC', 'Neutrophil', 'Mast', 'Fibroblast/CAF',
            'Endothelial', 'Tumor', 'Other',
        ],
    }

    # 感知均匀连续色图
    SEQUENTIAL_CMAPS = ['viridis', 'plasma', 'inferno', 'magma', 'mako']
    DIVERGING_CMAPS = ['coolwarm', 'RdBu_r', 'BrBG', 'PRGn', 'vlag']

    @classmethod
    def get(cls, name='wong2011'):
        """获取配色方案。"""
        schemes = {
            'wong2011': cls.WONG_2011,
            'okabe_ito': cls.OKABE_ITO,
            'ibm': cls.IBM,
            'grayscale': cls.GRAYSCALE,
            'crc_immune': cls.CRC_IMMUNE,
        }
        return schemes.get(name, cls.WONG_2011)

    @classmethod
    def get_colors(cls, name='wong2011', n=None):
        """获取颜色列表 (可限制数量)。"""
        scheme = cls.get(name)
        colors = scheme.get('colors', [])
        if n and n <= len(colors):
            return colors[:n]
        return colors


# ============================================================
# 第二部分: 期刊尺寸模板
# ============================================================

class JournalTemplate:
    """SCI 期刊和中文核心期刊的图表尺寸规范。"""

    TEMPLATES = {
        'nature': {
            'single_mm': (89, 247),
            '1.5_mm': (120, 247),
            'double_mm': (183, 247),
            'single_inches': (3.50, 9.72),
            'double_inches': (7.20, 9.72),
            'format': 'EPS/PDF',
            'color_mode': 'CMYK',
            'dpi': 1200,
            'font': 'Arial/Helvetica',
            'panel_label': 'top-left',
            'panel_fontsize': 14,
        },
        'cell': {
            'single_mm': (85, 240),
            '1.5_mm': (114, 240),
            'double_mm': (174, 240),
            'single_inches': (3.35, 9.45),
            'double_inches': (6.85, 9.45),
            'format': 'EPS/PDF/TIFF',
            'color_mode': 'CMYK',
            'dpi': 1200,
            'font': 'Arial/Helvetica',
            'panel_label': 'top-left',
            'panel_fontsize': 14,
        },
        'science': {
            'single_mm': (56, 200),
            '1.5_mm': (121, 200),
            'double_mm': (178, 200),
            'single_inches': (2.20, 7.87),
            'double_inches': (7.00, 7.87),
            'format': 'EPS/PDF',
            'color_mode': 'CMYK',
            'dpi': 1200,
            'font': 'Arial/Helvetica',
            'panel_label': 'bottom-left',
            'panel_fontsize': 14,
        },
        'lancet': {
            'single_mm': (83, 220),
            'double_mm': (170, 220),
            'single_inches': (3.27, 8.66),
            'double_inches': (6.69, 8.66),
            'format': 'EPS/PDF/TIFF',
            'color_mode': 'CMYK',
            'dpi': 1200,
            'font': 'Arial/Helvetica',
            'panel_label': 'top-center',
            'panel_fontsize': 14,
        },
        'jama': {
            'single_mm': (60, 225),
            '1.5_mm': (120, 225),
            'double_mm': (175, 225),
            'single_inches': (2.36, 8.86),
            'double_inches': (6.89, 8.86),
            'format': 'EPS/PDF/TIFF',
            'color_mode': 'CMYK',
            'dpi': 1200,
            'font': 'Arial/Helvetica',
            'panel_label': 'top-left',
            'panel_fontsize': 14,
        },
        'chinese_core': {
            'single_mm': (80, 220),
            'double_mm': (160, 220),
            'single_inches': (3.15, 8.66),
            'double_inches': (6.30, 8.66),
            'format': 'TIFF/PNG/JPG',
            'color_mode': 'RGB',
            'dpi': 300,
            'font': 'SimSun/Arial',
            'panel_label': 'top-left',
            'panel_fontsize': 12,
        },
    }

    @classmethod
    def get(cls, journal='nature', width='single'):
        """获取期刊尺寸 (英寸, matplotlib 用)。"""
        t = cls.TEMPLATES.get(journal, cls.TEMPLATES['nature'])
        key = f'{width}_inches'
        return t.get(key, t['single_inches'])

    @classmethod
    def get_dpi(cls, journal='nature'):
        """获取目标 DPI。"""
        t = cls.TEMPLATES.get(journal, cls.TEMPLATES['nature'])
        return t.get('dpi', 300)

    @classmethod
    def get_panel_style(cls, journal='nature'):
        """获取面板标签样式。"""
        t = cls.TEMPLATES.get(journal, cls.TEMPLATES['nature'])
        return {
            'position': t.get('panel_label', 'top-left'),
            'fontsize': t.get('panel_fontsize', 14),
            'fontweight': 'bold',
        }

    @classmethod
    def list_journals(cls):
        """列出所有支持的期刊。"""
        return list(cls.TEMPLATES.keys())


# ============================================================
# 第三部分: Statistical Helpers
# ============================================================

class Stats:
    """统计标注辅助函数。"""

    @staticmethod
    def significance_stars(p_value):
        """将 p 值转为显著性星号。"""
        if p_value < 0.0001:
            return '****'
        elif p_value < 0.001:
            return '***'
        elif p_value < 0.01:
            return '**'
        elif p_value < 0.05:
            return '*'
        return 'ns'

    @staticmethod
    def add_significance_line(ax, x1, x2, y, h, p_value=None, text=None):
        """在两组之间画显著性标注线 (需 matplotlib axes)。"""
        if text is None and p_value is not None:
            text = Stats.significance_stars(p_value)
        if text is None:
            text = 'ns'

        ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y],
                lw=1, color='black', clip_on=False)
        ax.text((x1 + x2) / 2, y + h, text,
                ha='center', va='bottom', fontsize=10)
        return ax

    @staticmethod
    def add_panel_label(ax, label, journal='nature'):
        """添加面板标签 (A, B, C...)。"""
        style = JournalTemplate.get_panel_style(journal)
        pos = style['position']

        if pos == 'top-left':
            x, y = -0.10, 1.05
            va, ha = 'bottom', 'left'
        elif pos == 'bottom-left':
            x, y = -0.10, -0.15
            va, ha = 'top', 'left'
        elif pos == 'top-center':
            x, y = 0.5, 1.05
            va, ha = 'bottom', 'center'

        ax.text(x, y, label, transform=ax.transAxes,
                fontsize=style['fontsize'], fontweight=style['fontweight'],
                va=va, ha=ha)
        return ax


# ============================================================
# 第四部分: Export Helpers
# ============================================================

class Export:
    """图表导出辅助函数。"""

    @staticmethod
    def setup_matplotlib(journal='nature'):
        """设置 matplotlib 全局参数。"""
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        plt.rcParams.update({
            'font.family': 'sans-serif',
            'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
            'font.size': 8,
            'axes.labelsize': 9,
            'axes.titlesize': 10,
            'xtick.labelsize': 8,
            'ytick.labelsize': 8,
            'legend.fontsize': 8,
            'figure.dpi': JournalTemplate.get_dpi(journal),
            'savefig.dpi': JournalTemplate.get_dpi(journal),
            'savefig.bbox': 'tight',
            'savefig.pad_inches': 0.05,
            'pdf.fonttype': 42,    # 嵌入式 TrueType 字体
            'ps.fonttype': 42,      # 嵌入式 PostScript 字体
            'axes.spines.top': False,
            'axes.spines.right': False,
            'axes.linewidth': 0.8,
            'xtick.major.width': 0.8,
            'ytick.major.width': 0.8,
        })

    @staticmethod
    def save_figure(fig, basename, outdir, formats=None, journal='nature'):
        """保存图表为多种格式。"""
        if formats is None:
            formats = ['svg', 'png']

        dpi = JournalTemplate.get_dpi(journal)
        os.makedirs(outdir, exist_ok=True)

        saved = []
        for fmt in formats:
            fpath = os.path.join(outdir, f'{basename}.{fmt}')
            kwargs = {'dpi': dpi, 'bbox_inches': 'tight'}

            if fmt == 'eps':
                kwargs['format'] = 'eps'
                kwargs['dpi'] = dpi
            elif fmt == 'pdf':
                kwargs['format'] = 'pdf'
            elif fmt == 'svg':
                kwargs['format'] = 'svg'
            elif fmt == 'png':
                kwargs['dpi'] = 300  # PNG 预览用 300 DPI

            fig.savefig(fpath, **kwargs)
            saved.append(fpath)

        return saved

    @staticmethod
    def save_figure_cli(config_path, outdir):
        """CLI 入口: 读取配置并生成图表。"""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 用 subprocess 调用自身 + matplotlib
        import subprocess
        script_dir = os.path.dirname(os.path.abspath(__file__))
        render_script = os.path.join(script_dir, '_render_figure.py')

        cmd = [
            sys.executable, render_script,
            '--config', config_path,
            '--outdir', outdir,
        ]
        subprocess.run(cmd, check=True)


# ============================================================
# 第五部分: CLI 入口
# ============================================================

def cmd_list_colors():
    """列出所有配色方案。"""
    print("Available color schemes:")
    print()
    for name in ['wong2011', 'okabe_ito', 'ibm', 'grayscale', 'crc_immune']:
        scheme = ColorScheme.get(name)
        colors = scheme.get('colors', [])
        names = scheme.get('names', [])
        print(f"  {name}:")
        for i, c in enumerate(colors[:8]):
            label = names[i] if i < len(names) else ''
            print(f"    {c}  {label}")
        print()


def cmd_list_journals():
    """列出所有期刊模板。"""
    print("Available journal templates:")
    print()
    for name in JournalTemplate.list_journals():
        t = JournalTemplate.TEMPLATES[name]
        print(f"  {name}:")
        print(f"    Single: {t['single_mm'][0]} x {t['single_mm'][1]} mm")
        print(f"    Double: {t['double_mm'][0]} x {t['double_mm'][1]} mm")
        print(f"    Format: {t.get('format', 'N/A')}")
        print(f"    DPI:    {t.get('dpi', 'N/A')}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='图表渲染工具库 — 配色方案、期刊模板、统计标注、格式导出')
    sub = parser.add_subparsers(dest='command', help='Commands')

    # list-colors
    sub.add_parser('list-colors', help='列出所有配色方案')

    # list-journals
    sub.add_parser('list-journals', help='列出所有期刊尺寸模板')

    # render
    render_parser = sub.add_parser('render', help='根据配置 JSON 渲染图表')
    render_parser.add_argument('--config', required=True, help='图表配置 JSON')
    render_parser.add_argument('--outdir', default='figures', help='输出目录')

    args = parser.parse_args()

    if args.command == 'list-colors':
        cmd_list_colors()
    elif args.command == 'list-journals':
        cmd_list_journals()
    elif args.command == 'render':
        Export.save_figure_cli(args.config, args.outdir)
    else:
        parser.print_help()
        print()
        print("As a Python library, import from generate_figure:")
        print("  from generate_figure import ColorScheme, JournalTemplate, Stats, Export")
        print()
        print("  colors = ColorScheme.get_colors('crc_immune', n=8)")
        print("  size   = JournalTemplate.get('nature', 'single')")
        print("  Export.setup_matplotlib('nature')")


if __name__ == '__main__':
    main()
