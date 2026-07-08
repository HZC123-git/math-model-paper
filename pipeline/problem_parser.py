#!/usr/bin/env python3
"""
Step 0: 赛题解析器
输入：竞赛题目（PDF/文本）
输出：结构化的问题定义（类型、变量、推荐模型、评价指标）
"""

import json, os, re
from pathlib import Path

# ============================================================
#  问题类型识别规则
# ============================================================

PROBLEM_TYPE_KEYWORDS = {
    "regression": [
        "预测", "拟合", "估计", "回归", "计算.*值", "确定.*关系",
        "prediction", "forecast", "estimate", "regression", "fit",
        "损耗.*计算", "价格.*预测", "预测.*模型", "定量.*分析",
        "predict", "forecast", "estimate.*value", "calculate.*value",
    ],
    "classification": [
        "分类", "识别", "判别", "区分", "归类",
        "classification", "classify", "identify", "recognize", "discriminate",
        "波形.*分类", "故障.*诊断", "模式.*识别",
    ],
    "clustering": [
        "聚类", "分组", "划分", "分群", "归类.*无监督",
        "clustering", "cluster", "grouping", "segmentation",
    ],
    "optimization": [
        "优化", "最优", "最大化", "最小化", "最佳.*方案", "规划",
        "optimization", "optimal", "maximize", "minimize", "best.*strategy",
        "调度", "分配", "资源.*配置", "路径.*规划",
    ],
    "time_series": [
        "时间序列", "时序", "趋势", "周期", "动态.*变化", "随时间",
        "time series", "temporal", "trend", "dynamic",
        "波动", "演变", "propagation", "扩散",
    ],
    "evaluation": [
        "评价", "评估", "打分", "排名", "评分", "综合.*指标",
        "evaluation", "assessment", "rating", "ranking", "score",
        "评审", "评选", "择优",
    ],
    "simulation": [
        "仿真", "模拟", "蒙特卡洛", "离散事件",
        "simulation", "Monte Carlo", "discrete event",
        "随机.*过程", "退避", "信道.*接入",
    ],
}


def identify_problem_type(text):
    """根据关键词密度识别问题类型"""
    scores = {}
    for ptype, keywords in PROBLEM_TYPE_KEYWORDS.items():
        score = 0
        for kw in keywords:
            # 支持中英文关键词匹配
            matches = re.findall(kw, text, re.IGNORECASE)
            score += len(matches) * 2  # 每个匹配2分
        scores[ptype] = score

    # 返回得分最高的3个类型
    sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [t for t, s in sorted_types if s > 0][:3]


# ============================================================
#  推荐模型映射表
# ============================================================

MODEL_RECOMMENDATIONS = {
    "regression": {
        "linear": ["LinearRegression", "Ridge", "Lasso", "ElasticNet"],
        "nonlinear": ["RandomForestRegressor", "GradientBoostingRegressor", "XGBoost", "SVR"],
        "deep": ["MLPRegressor"],
        "with_feature_selection": ["LassoCV", "RidgeCV"],
    },
    "classification": {
        "linear": ["LogisticRegression", "SGDClassifier"],
        "tree": ["DecisionTreeClassifier", "RandomForestClassifier", "GradientBoostingClassifier"],
        "svm": ["SVC", "LinearSVC"],
        "ensemble": ["XGBoost", "LightGBM", "VotingClassifier"],
        "deep": ["MLPClassifier"],
    },
    "clustering": {
        "centroid": ["KMeans", "MiniBatchKMeans"],
        "density": ["DBSCAN", "OPTICS", "HDBSCAN"],
        "hierarchical": ["AgglomerativeClustering"],
        "mixture": ["GaussianMixture"],
    },
    "optimization": {
        "exact": ["线性规划(pulp/scipy)", "整数规划", "动态规划"],
        "heuristic": ["遗传算法(GA)", "粒子群算法(PSO)", "模拟退火(SA)", "蚁群算法(ACO)"],
        "multi_objective": ["NSGA-II", "MOPSO", "帕累托前沿"],
        "ml_based": ["强化学习(Q-Learning)", "贝叶斯优化"],
    },
    "time_series": {
        "statistical": ["ARIMA", "SARIMA", "Holt-Winters", "VAR"],
        "ml": ["RandomForest(时序特征)", "XGBoost(时序特征)", "LightGBM(时序特征)"],
        "deep": ["LSTM", "GRU", "BiLSTM", "Transformer", "CNN-LSTM"],
        "decomposition": ["Prophet", "STL分解"],
    },
    "evaluation": {
        "weight": ["AHP(层次分析法)", "熵权法", "TOPSIS(优劣解距离法)"],
        "comprehensive": ["模糊综合评价", "灰色关联分析", "主成分评价"],
        "ml_based": ["随机森林(特征重要性评价)", "XGBoost(特征重要性评价)"],
    },
    "simulation": {
        "event": ["离散事件仿真(DES)", "SimPy", "MATLAB Simulink"],
        "monte_carlo": ["蒙特卡洛模拟", "拉丁超立方采样"],
        "agent": ["Agent-Based Modeling(ABM)", "元胞自动机"],
    },
}

EVALUATION_METRICS = {
    "regression": ["R2", "RMSE", "MAE", "MAPE", "调整R2"],
    "classification": ["Accuracy", "Precision", "Recall", "F1-Score", "AUC-ROC", "混淆矩阵"],
    "clustering": ["轮廓系数(Silhouette)", "Calinski-Harabasz指数", "Davies-Bouldin指数"],
    "optimization": ["目标函数值", "收敛速度", "鲁棒性"],
    "time_series": ["RMSE", "MAE", "MAPE", "sMAPE"],
    "evaluation": ["区分度", "一致性(Kappa系数)", "公平性指标"],
    "simulation": ["置信区间", "方差", "收敛性"],
}


# ============================================================
#  结构化解析 Prompt
# ============================================================

def build_parse_prompt(problem_text):
    """构建让 LLM 解析赛题的 prompt"""

    prompt = f"""<task>你是数学建模竞赛的专家。请仔细阅读以下竞赛题目，输出结构化的分析结果。</task>

<problem>
{problem_text[:8000]}
</problem>

<instructions>
1. 识别这是一个什么类型的竞赛（国赛/研究生数学建模/美赛/统计建模）
2. 识别每个子问题的类型（回归/分类/聚类/优化/时间序列/评价/仿真）
3. 对每个子问题，列出：输入变量、输出变量、推荐模型（3-5个）、评价指标
4. 识别题目中的约束条件、假设条件
5. 给出整体的建模路线建议

输出JSON格式（严格按此结构）：

```json
{{
  "competition_type": "研究生数学建模",
  "problem_title": "从题目中提取",
  "problem_summary": "一句话概括",
  "questions": [
    {{
      "id": 1,
      "name": "问题简短名称",
      "type": "regression/classification/clustering/optimization/time_series/evaluation/simulation",
      "description": "问题描述(1-2句)",
      "input_variables": ["变量1", "变量2"],
      "output_variable": "目标变量",
      "recommended_models": ["模型1", "模型2", "模型3"],
      "evaluation_metrics": ["指标1", "指标2"],
      "data_requirements": ["需要的数据1", "需要的数据2"],
      "difficulty": "easy/medium/hard"
    }}
  ],
  "data_files": ["附件1名称", "附件2名称"],
  "constraints": ["约束1", "约束2"],
  "assumptions": ["假设1", "假设2"],
  "modeling_roadmap": "整体建模路线的简要描述"
}}
```
</instructions>

<rules>
- 每个问题的推荐模型必须是真实存在的算法/方法
- 评价指标必须与问题类型匹配
- 如果是回归问题，评价指标必须包含R2和RMSE
- 如果是分类问题，评价指标必须包含准确率和F1
- 不要编造题目中不存在的数据或变量
- 问题类型不要混用——如果主要是分类任务就只标classification
</rules>
"""
    return prompt


# ============================================================
#  命令行接口
# ============================================================

def parse_problem_text(problem_text):
    """使用关键词规则快速预判（不依赖LLM）"""
    lines = problem_text.strip().split('\n')[:50]
    header = '\n'.join(lines)

    # 尝试提取标题
    title_match = re.search(r'题\s*目[：:]\s*(.+?)(?:\n|$)', header)
    title = title_match.group(1).strip() if title_match else "未知题目"

    # 识别子问题
    questions = list(re.finditer(r'(?:问题|任务)\s*([一二三四五六七八九十\d]+)', header))
    n_questions = len(questions) if questions else 3

    # 识别问题类型
    types = identify_problem_type(header)

    # 识别数据文件
    attachments = re.findall(r'附件\s*[一二三四五六七八九十\d]*[：:\s]*(.+?)(?:\n|$)', header)
    if not attachments:
        attachments = re.findall(r'[Aa]ttachment\s*[：:\s]*(.+?)(?:\n|$)', header)

    # 识别约束条件
    constraints = []
    constraint_patterns = [
        (r'(?:要求|需满足|应|必须|不得|不能|在.*条件下).*?[。；\n]', 'zh'),
        (r'(?:require|must|should|need to|under.*condition).*?[.;\n]', 'en'),
    ]
    for pattern, _ in constraint_patterns:
        matches = re.findall(pattern, header, re.IGNORECASE)
        constraints.extend([m.strip() for m in matches[:5]])

    return {
        "problem_title": title,
        "problem_types_detected": types,
        "n_questions_estimated": n_questions,
        "data_files": attachments[:5],
        "constraints_found": constraints[:5],
        "first_50_lines": header[:2000],
    }


def recommend_models_for_types(problem_types, n_models=5):
    """根据问题类型推荐模型"""
    all_models = []
    seen = set()

    for ptype in problem_types:
        if ptype in MODEL_RECOMMENDATIONS:
            models = MODEL_RECOMMENDATIONS[ptype]
            for category, model_list in models.items():
                for m in model_list:
                    if m not in seen:
                        all_models.append({"type": ptype, "category": category, "model": m})
                        seen.add(m)

    return all_models[:n_models]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="赛题解析器 - 自动识别问题类型和推荐模型")
    parser.add_argument("problem_file", nargs="?", help="赛题文件路径 (PDF/TXT)")
    parser.add_argument("--text", "-t", help="直接提供赛题文本")

    args = parser.parse_args()

    text = ""
    if args.text:
        text = args.text
    elif args.problem_file:
        path = Path(args.problem_file)
        if path.suffix == ".pdf":
            try:
                import fitz
                doc = fitz.open(str(path))
                text = "\n".join(page.get_text() for page in doc)
                doc.close()
            except ImportError:
                print("需要安装 PyMuPDF: pip install PyMuPDF")
                exit(1)
        else:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()

    if not text:
        print("请提供赛题文件路径或 --text 参数")
        exit(1)

    # 解析
    result = parse_problem_text(text)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()

    # 推荐模型
    types = result.get("problem_types_detected", [])
    if types:
        print(f"\n检测到的问题类型: {types}")
        print("\n推荐模型:")
        models = recommend_models_for_types(types)
        for m in models:
            print(f"  [{m['type']}] {m['category']:20s} -> {m['model']}")

    # 输出LLM解析prompt（供skill调用）
    prompt = build_parse_prompt(text)
    print(f"\n\n{'='*60}")
    print("将此prompt发送给LLM以获取完整结构化解析结果")
    print(f"{'='*60}")
