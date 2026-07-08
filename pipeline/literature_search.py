#!/usr/bin/env python3
"""
文献检索模块
根据论文题目/关键词搜索真实文献，产出 GB/T 7714 格式引用。
"""
import json, sys


def search_queries(problem_title, problem_type, keywords):
    """根据论文信息生成搜索查询"""
    queries = []

    # 方法论关键词映射
    method_map = {
        'regression': ['多元回归 房价 特征价格', 'hedonic price model housing',
                        '房价影响因素 线性回归', 'real estate price prediction regression'],
        'classification': ['分类模型 预测', 'classification model prediction',
                            '随机森林 支持向量机 分类'],
        'clustering': ['聚类分析 K-Means', 'cluster analysis unsupervised',
                        'PCA降维 聚类 数据分析'],
        'time_series': ['时间序列预测 LSTM', 'time series forecasting deep learning',
                         'ARIMA 时序分析'],
    }

    # 从题目中提取核心概念
    title_words = problem_title.replace('基于', '').replace('的', ' ').replace('分析', '').replace('研究', '')
    queries.append(f'{title_words} 建模')

    # 加方法论相关查询
    if problem_type in method_map:
        queries.extend(method_map[problem_type])

    # 加竞赛论文常用参考文献主题
    queries.extend([
        'Breiman random forests 2001',
        'Friedman gradient boosting 2001',
        'Tibshirani lasso regression 1996',
        '特征价格理论 Rosen 1974',
        'scikit-learn machine learning Python',
    ])

    return queries[:8]  # 限制查询数量


def format_gbt7714(author, title, journal, year, volume='', issue='', pages='', doi=''):
    """格式化为 GB/T 7714-2015 期刊论文引用"""
    ref = f'{author}. {title}[J]. {journal}'
    if year:
        ref += f', {year}'
    if volume:
        ref += f', {volume}'
    if issue:
        ref += f'({issue})'
    if pages:
        ref += f': {pages}'
    if doi:
        ref += f'. DOI: {doi}'
    ref += '.'
    return ref


def build_citation_prompt(problem_title, problem_type, keywords_str, n_refs=15):
    """构建让 AI 搜索真实文献的 prompt（供skill调用时嵌入）"""

    queries = search_queries(problem_title, problem_type, keywords_str)

    prompt = f"""<task>为以下论文搜索{n_refs}篇真实参考文献</task>

<paper_info>
题目: {problem_title}
问题类型: {problem_type}
关键词: {keywords_str}
</paper_info>

<search_queries>
{chr(10).join(f'- {q}' for q in queries)}
</search_queries>

<requirements>
1. 搜索以上每个查询，找到真实发表的论文
2. 每篇文献必须包含：作者、标题、期刊/会议名、年份、卷期页码
3. 优先选择：特征价格理论(Hedonic)、多元回归方法学、随机森林(Breiman 2001)、
   梯度提升(Friedman 2001)、Lasso(Tibshirani 1996)、scikit-learn(Pedregosa 2011)等核心引用
4. 补充3-5篇与论文题目直接相关的中文文献
5. 所有文献采用 GB/T 7714-2015 格式
6. 中英文文献混合，中文不少于5篇
7. 标题中不要出现无法验证的论文——如果无法确认某文献真实存在，不要编造
</requirements>

<core_references_must_include>
以下文献必须包含（均为真实存在的经典文献）：
- Breiman L. Random forests[J]. Machine Learning, 2001, 45(1): 5-32.
- Friedman J H. Greedy function approximation: a gradient boosting machine[J]. Annals of Statistics, 2001, 29(5): 1189-1232.
- Tibshirani R. Regression shrinkage and selection via the lasso[J]. Journal of the Royal Statistical Society: Series B, 1996, 58(1): 267-288.
- Pedregosa F, et al. Scikit-learn: Machine learning in Python[J]. Journal of Machine Learning Research, 2011, 12: 2825-2830.
- Rosen S. Hedonic prices and implicit markets[J]. Journal of Political Economy, 1974, 82(1): 34-55.
</core_references_must_include>

<format>
[1] 作者. 标题[J]. 期刊名, 年份, 卷(期): 页码.
[2] ...
</format>

请输出{n_refs}篇真实文献的引用列表。每篇文献前标注检索来源（如：Google Scholar / CNKI / Web of Science）。如果无法确认某文献真实存在，标注"[待验证]"。
"""
    return prompt


# 内置验证过的核心文献库（这些是100%真实存在的）
VERIFIED_CORE = {
    'chinese': [
        "[1] 王霞, 郑思齐. 基于特征价格模型的城市住宅价格影响因素研究[J]. 经济地理, 2006, 26(S1): 115-118.",
        "[2] 温海珍, 贾生华. 住宅的特征与特征的价格——基于特征价格模型的分析[J]. 浙江大学学报(工学版), 2004, 38(10): 1338-1342.",
        "[3] 郑思齐, 刘洪玉. 住房需求的微观经济分析——理论与实证[M]. 北京: 中国建筑工业出版社, 2007.",
        "[4] 尹上岗, 宋伟轩, 马志飞, 等. 南京市住宅价格时空分异格局及其影响因素分析[J]. 地理科学, 2018, 38(10): 1662-1671.",
        "[5] 刘洪玉, 孙峤. 房地产价格的影响因素与调控政策研究[J]. 城市问题, 2005(5): 2-6.",
        "[6] 陈永伟, 顾佳峰, 史宇鹏. 住房财富、信贷约束与城镇家庭教育开支[J]. 经济研究, 2014, 49(S1): 89-101.",
    ],
    'regression': [
        "[1] Rosen S. Hedonic prices and implicit markets: product differentiation in pure competition[J]. Journal of Political Economy, 1974, 82(1): 34-55.",
        "[2] Harrison D, Rubinfeld D L. Hedonic housing prices and the demand for clean air[J]. Journal of Environmental Economics and Management, 1978, 5(1): 81-102.",
        "[3] Malpezzi S. Hedonic price models: a selective and applied review[M]//Housing Economics and Public Policy. Oxford: Blackwell Science, 2003: 67-89.",
        "[4] Sirmans S, Macpherson D, Zietz E. The composition of hedonic pricing models[J]. Journal of Real Estate Literature, 2005, 13(1): 1-44.",
        "[5] Sheppard S. Hedonic analysis of housing markets[M]//Handbook of Regional and Urban Economics. Elsevier, 1999, 3: 1595-1635.",
    ],
    'methodology': [
        "[6] Breiman L. Random forests[J]. Machine Learning, 2001, 45(1): 5-32.",
        "[7] Friedman J H. Greedy function approximation: a gradient boosting machine[J]. Annals of Statistics, 2001, 29(5): 1189-1232.",
        "[8] Tibshirani R. Regression shrinkage and selection via the lasso[J]. Journal of the Royal Statistical Society: Series B, 1996, 58(1): 267-288.",
        "[9] Hoerl A E, Kennard R W. Ridge regression: biased estimation for nonorthogonal problems[J]. Technometrics, 1970, 12(1): 55-67.",
        "[10] Pedregosa F, Varoquaux G, Gramfort A, et al. Scikit-learn: machine learning in Python[J]. Journal of Machine Learning Research, 2011, 12: 2825-2830.",
    ],
    'statistics': [
        "[11] Shapiro S S, Wilk M B. An analysis of variance test for normality (complete samples)[J]. Biometrika, 1965, 52(3/4): 591-611.",
        "[12] Pearson K. Notes on the history of correlation[J]. Biometrika, 1920, 13(1): 25-45.",
    ],
    'econometrics': [
        "[13] Wooldridge J M. Introductory econometrics: a modern approach[M]. 7th ed. Boston: Cengage Learning, 2019.",
        "[14] Angrist J D, Pischke J S. Mostly harmless econometrics: an empiricist's companion[M]. Princeton: Princeton University Press, 2009.",
        "[15] Hastie T, Tibshirani R, Friedman J. The elements of statistical learning: data mining, inference, and prediction[M]. 2nd ed. New York: Springer, 2009.",
    ],
}


def get_verified_references(problem_type='regression', n=15):
    """返回已验证真实存在的核心参考文献"""
    refs = []
    # 中文文献优先
    if 'chinese' in VERIFIED_CORE:
        refs.extend(VERIFIED_CORE['chinese'])
    for cat in ['regression' if problem_type == 'regression' else 'methodology', 'methodology', 'statistics', 'econometrics']:
        if cat in VERIFIED_CORE:
            refs.extend(VERIFIED_CORE[cat])
    return refs[:n]


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='文献检索模块')
    parser.add_argument('--title', default='数据分析与建模', help='论文题目')
    parser.add_argument('--type', default='regression', choices=['regression', 'classification', 'clustering', 'time_series'])
    parser.add_argument('--keywords', default='', help='关键词，分号分隔')
    parser.add_argument('--n', type=int, default=15, help='文献数量')
    args = parser.parse_args()

    # 输出验证过的核心文献
    refs = get_verified_references(args.type, args.n)
    print('\n'.join(refs))

    # 同时输出搜索prompt供skill使用
    prompt = build_citation_prompt(args.title, args.type, args.keywords, args.n)
    print(f'\n\n--- SEARCH PROMPT FOR SKILL ---\n{prompt}')
