#!/usr/bin/env python3
"""
图表审美模块
将 matplotlib 默认样式替换为竞赛论文级别的发表质量样式。
"""
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np


def apply_paper_style(style='cn'):
    """应用论文级图表样式

    Args:
        style: 'cn' 中文论文, 'en' 英文论文
    """
    # ---- 基础配置 ----
    plt.rcParams.update({
        # 图片质量
        'figure.dpi': 150,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.1,

        # 字体（中文论文）
        'font.sans-serif': ['SimHei', 'Microsoft YaHei', 'DejaVu Sans'],
        'axes.unicode_minus': False,

        # 字号
        'font.size': 11,
        'axes.titlesize': 13,
        'axes.labelsize': 12,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'legend.fontsize': 9,

        # 线条
        'lines.linewidth': 1.8,
        'lines.markersize': 6,
        'lines.markeredgewidth': 0.5,

        # 坐标轴
        'axes.linewidth': 0.8,
        'axes.spines.top': False,     # 去掉上边框
        'axes.spines.right': False,   # 去掉右边框
        'axes.grid': False,           # 默认不显示网格
        'axes.axisbelow': True,

        # 图例
        'legend.frameon': False,      # 无边框
        'legend.loc': 'best',

        # 刻度
        'xtick.major.width': 0.8,
        'ytick.major.width': 0.8,
        'xtick.direction': 'in',
        'ytick.direction': 'in',
        'xtick.major.size': 4,
        'ytick.major.size': 4,

        # 颜色循环（学术配色，色盲友好）
        'axes.prop_cycle': mpl.cycler(color=[
            '#2166AC',  # 蓝
            '#D6604D',  # 红
            '#4DAF4A',  # 绿
            '#FF7F00',  # 橙
            '#9467BD',  # 紫
            '#8C564B',  # 棕
            '#E377C2',  # 粉
            '#7F7F7F',  # 灰
        ]),
    })

    if style == 'cn':
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    else:
        plt.rcParams['font.family'] = 'serif'
        plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']

    return plt


def three_line_table_style(ax):
    """三线表风格应用到坐标轴（粗上下边，细内线）"""
    ax.spines['bottom'].set_linewidth(1.5)
    ax.spines['left'].set_linewidth(1.5)
    ax.tick_params(width=1.2)
    return ax


# ---- 预设图表模板 ----

def correlation_heatmap(corr_matrix, labels=None, figsize=(10, 8), title=None, save_path=None):
    """发表级相关性热力图"""
    import seaborn as sns
    apply_paper_style()

    fig, ax = plt.subplots(figsize=figsize)
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)

    cmap = sns.diverging_palette(250, 15, s=75, l=40, n=16, center='light')

    sns.heatmap(
        corr_matrix,
        mask=mask,
        annot=True,
        fmt='.2f' if corr_matrix.shape[0] <= 10 else '.1f',
        cmap=cmap,
        center=0,
        vmin=-1, vmax=1,
        square=True,
        linewidths=0.5,
        linecolor='white',
        cbar_kws={'shrink': 0.8, 'label': 'Pearson r'},
        annot_kws={'size': 9, 'fontweight': 'bold'},
        ax=ax,
    )

    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right', fontsize=9)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=9)

    if title:
        ax.set_title(title, fontsize=14, pad=15, fontweight='bold')

    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(fig)

    return fig, ax


def model_diagnostics(y_true, y_pred, model_name='Model', save_path=None):
    """发表级模型诊断图（真值-预测 + 残差）"""
    apply_paper_style()

    residuals = np.array(y_true) - np.array(y_pred)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # 左图：True vs Predicted
    ax = axes[0]
    ax.scatter(y_true, y_pred, alpha=0.5, s=20, c='#2166AC', edgecolors='white', linewidth=0.3)
    min_val = min(min(y_true), min(y_pred))
    max_val = max(max(y_true), max(y_pred))
    ax.plot([min_val, max_val], [min_val, max_val], '--', color='#D6604D', linewidth=1.5, alpha=0.8)
    ax.set_xlabel('True Values', fontsize=12)
    ax.set_ylabel('Predicted Values', fontsize=12)
    ax.set_title(f'{model_name}: True vs Predicted', fontsize=13, fontweight='bold')
    three_line_table_style(ax)

    # 右图：Residuals
    ax = axes[1]
    ax.scatter(y_pred, residuals, alpha=0.5, s=20, c='#4DAF4A', edgecolors='white', linewidth=0.3)
    ax.axhline(y=0, color='#D6604D', linestyle='--', linewidth=1.5, alpha=0.8)
    ax.set_xlabel('Predicted Values', fontsize=12)
    ax.set_ylabel('Residuals', fontsize=12)
    ax.set_title(f'{model_name}: Residual Plot', fontsize=13, fontweight='bold')
    three_line_table_style(ax)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(fig)

    return fig, axes


def feature_importance_bar(features, importances, top_n=12, title=None, save_path=None):
    """发表级特征重要性水平条形图"""
    apply_paper_style()

    indices = np.argsort(importances)[-top_n:]
    fig, ax = plt.subplots(figsize=(8, 0.5 * top_n))

    colors = plt.cm.Blues(np.linspace(0.4, 0.9, top_n))
    bars = ax.barh(
        range(top_n),
        [importances[i] for i in indices],
        color=colors,
        edgecolor='white',
        linewidth=0.5,
        height=0.7,
    )

    ax.set_yticks(range(top_n))
    ax.set_yticklabels([features[i] for i in indices], fontsize=11)
    ax.set_xlabel('Importance Score', fontsize=12)
    ax.invert_yaxis()

    # 在条形末端标注数值
    for i, (bar, idx) in enumerate(zip(bars, indices)):
        ax.text(
            bar.get_width() + 0.005, bar.get_y() + bar.get_height() / 2,
            f'{importances[idx]:.3f}',
            va='center', fontsize=9, fontweight='bold',
        )

    if title:
        ax.set_title(title, fontsize=14, pad=12, fontweight='bold')

    three_line_table_style(ax)
    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(fig)

    return fig, ax


def distribution_qq(data, var_name='Variable', save_path=None):
    """发表级分布图（直方图+Q-Q）"""
    from scipy import stats as sp_stats
    apply_paper_style()

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # 直方图 + KDE
    ax = axes[0]
    ax.hist(data, bins=30, density=True, alpha=0.6, color='#2166AC', edgecolor='white', linewidth=0.5)
    from scipy.stats import gaussian_kde
    kde = gaussian_kde(data)
    x_range = np.linspace(min(data), max(data), 200)
    ax.plot(x_range, kde(x_range), color='#D6604D', linewidth=2)
    ax.set_xlabel(var_name, fontsize=12)
    ax.set_ylabel('Density', fontsize=12)
    ax.set_title(f'Distribution of {var_name}', fontsize=13, fontweight='bold')
    three_line_table_style(ax)

    # Q-Q plot
    ax = axes[1]
    sp_stats.probplot(data, dist='norm', plot=ax)
    ax.get_lines()[0].set_markerfacecolor('#2166AC')
    ax.get_lines()[0].set_markeredgecolor('white')
    ax.get_lines()[0].set_markersize(4)
    ax.get_lines()[1].set_color('#D6604D')
    ax.get_lines()[1].set_linewidth(1.5)
    ax.set_title(f'Q-Q Plot of {var_name}', fontsize=13, fontweight='bold')
    three_line_table_style(ax)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(fig)

    return fig, axes


if __name__ == '__main__':
    # 测试：生成示例图
    apply_paper_style('cn')
    np.random.seed(42)

    # 生成示例数据
    y_true = np.random.normal(400, 70, 100)
    noise = np.random.normal(0, 15, 100)
    y_pred = y_true + noise

    model_diagnostics(y_true, y_pred, 'LinearRegression',
                       'C:/Users/HZC12/Desktop/test_chart_style.png')
    print("Test chart saved to desktop.")
