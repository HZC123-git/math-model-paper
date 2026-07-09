#!/usr/bin/env python3
"""
模型反省模块
如果最优模型表现不达标，自动触发替代策略。
"""

import json

# ============================================================
#  质量阈值
# ============================================================

QUALITY_THRESHOLDS = {
    "regression": {
        "excellent": 0.90,  # R2 >= 0.90: 直接通过
        "acceptable": 0.70,  # R2 >= 0.70: 可用但建议优化
        "poor": 0.50,  # R2 < 0.50: 必须换方法
    },
    "classification": {
        "excellent": 0.85,
        "acceptable": 0.70,
        "poor": 0.60,
    },
    "clustering": {
        "excellent": 0.50,  # silhouette
        "acceptable": 0.30,
        "poor": 0.15,
    },
}

# ============================================================
#  替代策略
# ============================================================

FALLBACK_STRATEGIES = {
    "regression": [
        {
            "name": "特征工程",
            "description": "当前特征可能不足以解释目标变量。尝试：多项式特征(degree=2)、交互项(面积*学区)、对数变换(log(y))",
            "trigger": "R2 < 0.70",
            "actions": ["添加x1*x4交互项", "对y做log变换", "添加x1^2多项式项"],
        },
        {
            "name": "换模型族",
            "description": "线性假设可能不成立。切换到：XGBoost、LightGBM、KNN回归、高斯过程回归",
            "trigger": "线性模型R2 < 0.50 且 非线性模型R2也 < 0.60",
            "actions": ["增加XGBoost(n=200,d=6)", "尝试KNeighborsRegressor(k=5,10,20)", "尝试GaussianProcessRegressor"],
        },
        {
            "name": "异常值处理",
            "description": "极端值可能扭曲回归。尝试：IQR法剔除异常值、Huber回归(Robust regression)、分位数回归",
            "trigger": "R2 < 0.60 且 RMSE/MAE > 2.0",
            "actions": ["IQR剔除异常值后重跑", "使用HuberRegressor", "使用QuantileRegressor"],
        },
        {
            "name": "数据增广",
            "description": "样本量不足导致过拟合。如果n<200，尝试：Bootstrap重采样、交叉验证集成",
            "trigger": "n < 200 且 CV标准差 > 0.05",
            "actions": ["Bootstrap重采样到500条", "BaggingRegressor集成"],
        },
    ],
    "classification": [
        {
            "name": "类别不平衡处理",
            "description": "检查类别分布，如果不均衡：SMOTE过采样、class_weight='balanced'",
            "trigger": "Accuracy > 0.80 但 F1 < 0.50",
            "actions": ["SMOTE过采样", "设置class_weight=balanced", "调整决策阈值"],
        },
        {
            "name": "换模型族",
            "description": "当前分类器不适用。尝试：XGBoost、LightGBM、KNN、高斯朴素贝叶斯",
            "trigger": "Accuracy < 0.60",
            "actions": ["XGBoostClassifier", "LightGBM", "VotingClassifier集成"],
        },
    ],
    "clustering": [
        {
            "name": "换聚类方法",
            "description": "KMeans假设球形聚类，数据可能不符合。尝试：DBSCAN、谱聚类、高斯混合模型",
            "trigger": "Silhouette < 0.20",
            "actions": ["DBSCAN(调整eps)", "谱聚类", "GaussianMixture"],
        },
        {
            "name": "降维后再聚类",
            "description": "高维数据聚类效果差。先PCA降到2-5维再聚类",
            "trigger": "特征数 > 10 且 Silhouette < 0.30",
            "actions": ["PCA(n_components=3)→KMeans", "t-SNE→KMeans"],
        },
    ],
}


def evaluate_quality(results, problem_type):
    """评估模型质量并返回评级和建议"""
    thresholds = QUALITY_THRESHOLDS.get(problem_type, QUALITY_THRESHOLDS["regression"])
    strategies = FALLBACK_STRATEGIES.get(problem_type, [])

    # 获取最优指标
    best_metric = None
    if problem_type == "regression":
        gb = results.get("global_best", {})
        best_metric = gb.get("R2")
    elif problem_type == "classification":
        gb = results.get("global_best", {})
        best_metric = gb.get("Accuracy")
    elif problem_type == "clustering":
        clust = results.get("clustering", {})
        best_metric = clust.get("best_silhouette")

    if best_metric is None:
        return {"grade": "unknown", "message": "无法确定模型质量", "suggestions": []}

    # 评级
    if best_metric >= thresholds["excellent"]:
        grade = "excellent"
        msg = f"模型质量优秀(R2/AUC={best_metric:.4f})，无需优化。直接进入论文写作。"
        suggestions = []
    elif best_metric >= thresholds["acceptable"]:
        grade = "acceptable"
        msg = f"模型质量可接受(R2/AUC={best_metric:.4f})，建议尝试以下优化后择最优："
        suggestions = [s for s in strategies if best_metric < 0.85]
    else:
        grade = "poor"
        msg = f"模型质量不达标(R2/AUC={best_metric:.4f})，必须采取替代策略："
        suggestions = strategies  # 全部建议

    # 检查是否需要特征工程（RMSE/MAE比值判断异常值影响）
    if problem_type == "regression":
        models = results.get("models_used", {})
        for cat_models in models.values():
            for name, m in cat_models.items():
                if isinstance(m, dict) and "RMSE" in m and "MAE" in m:
                    if m["RMSE"] / max(m["MAE"], 0.001) > 2.5:
                        suggestions.insert(0, strategies[2])  # 异常值处理优先
                        break

    return {
        "grade": grade,
        "best_metric": round(best_metric, 6),
        "threshold_excellent": thresholds["excellent"],
        "threshold_acceptable": thresholds["acceptable"],
        "message": msg,
        "suggestions": [
            {"name": s["name"], "description": s["description"], "actions": s["actions"]}
            for s in suggestions[:4]
        ],
    }


def print_reflection_report(reflection):
    """打印反省报告"""
    grade_icons = {"excellent": "[PASS]", "acceptable": "[WARN]", "poor": "[FAIL]", "unknown": "[???]"}
    icon = grade_icons.get(reflection.get("grade", "unknown"), "[???]")

    print(f"\n{'='*60}")
    print(f"  Model Reflection Report")
    print(f"{'='*60}")
    print(f"  {icon} Grade: {reflection.get('grade', 'N/A')}")
    print(f"  Metric: {reflection.get('best_metric', 'N/A')}")
    print(f"  Thresholds: excellent>{reflection.get('threshold_excellent', '?')} "
          f"acceptable>{reflection.get('threshold_acceptable', '?')}")
    print(f"  {reflection.get('message', '')}")

    suggestions = reflection.get("suggestions", [])
    if suggestions:
        print(f"\n  Suggested improvements ({len(suggestions)}):")
        for i, s in enumerate(suggestions, 1):
            print(f"  {i}. [{s['name']}] {s['description']}")
            for a in s["actions"]:
                print(f"     -> {a}")

    print(f"  {'='*60}")

    return reflection["grade"] == "excellent"


if __name__ == "__main__":
    import argparse, json

    parser = argparse.ArgumentParser(description="模型反省：自动评估质量并建议优化")
    parser.add_argument("results_json", help="smart_model_pool输出的JSON")
    parser.add_argument("--auto-fix", action="store_true", help="自动应用优化建议")
    args = parser.parse_args()

    with open(args.results_json, "r", encoding="utf-8") as f:
        results = json.load(f)

    problem_type = results.get("problem_type", "regression")
    reflection = evaluate_quality(results, problem_type)
    passed = print_reflection_report(reflection)

    if args.auto_fix and not passed:
        print("\n[AUTO-FIX] 自动优化模式暂需人工确认，请根据上述建议手动调整后重新运行。")
