#!/usr/bin/env python3
"""
智能模型池
根据问题类型动态选择模型，不再固定5个回归模型。
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    r2_score, mean_squared_error, mean_absolute_error,
    accuracy_score, precision_score, recall_score, f1_score,
    silhouette_score,
)
from sklearn.linear_model import (
    LinearRegression, Ridge, Lasso, ElasticNet, LogisticRegression, SGDClassifier
)
from sklearn.ensemble import (
    RandomForestRegressor, RandomForestClassifier,
    GradientBoostingRegressor, GradientBoostingClassifier,
)
from sklearn.svm import SVR, SVC, LinearSVC
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.neural_network import MLPRegressor, MLPClassifier
from sklearn.decomposition import PCA
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

# ============================================================
#  模型池定义
# ============================================================

MODEL_POOL = {
    "regression": {
        "线性模型": [
            ("LinearRegression", LinearRegression()),
            ("Ridge(a=1.0)", Ridge(alpha=1.0)),
            ("Ridge(a=0.1)", Ridge(alpha=0.1)),
            ("Lasso(a=0.01)", Lasso(alpha=0.01, max_iter=5000)),
            ("ElasticNet", ElasticNet(alpha=0.01, l1_ratio=0.5, max_iter=5000)),
        ],
        "非线性树模型": [
            ("RandomForest(d=10)", RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)),
            ("RandomForest(d=None)", RandomForestRegressor(n_estimators=100, random_state=42)),
            ("GradientBoosting(d=5)", GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42)),
            ("GradientBoosting(d=3)", GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=42)),
        ],
        "支持向量机": [
            ("SVR(rbf)", SVR(kernel='rbf')),
            ("SVR(linear)", SVR(kernel='linear')),
        ],
        "神经网络": [
            ("MLP(100,50)", MLPRegressor(hidden_layer_sizes=(100, 50), max_iter=1000, random_state=42)),
        ],
    },
    "classification": {
        "线性分类器": [
            ("LogisticRegression", LogisticRegression(max_iter=2000, random_state=42)),
            ("SGDClassifier", SGDClassifier(max_iter=2000, random_state=42)),
        ],
        "树模型": [
            ("RandomForest(d=10)", RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)),
            ("GradientBoosting(d=5)", GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42)),
        ],
        "支持向量机": [
            ("SVC(rbf)", SVC(kernel='rbf', probability=True, random_state=42)),
            ("LinearSVC", LinearSVC(max_iter=2000, random_state=42)),
        ],
        "神经网络": [
            ("MLP(100,50)", MLPClassifier(hidden_layer_sizes=(100, 50), max_iter=1000, random_state=42)),
        ],
    },
    "clustering": {
        "基于质心": [
            ("KMeans(k=auto)", None),  # k will be auto-determined
        ],
        "基于密度": [
            ("DBSCAN", DBSCAN(eps=0.5, min_samples=5)),
        ],
        "层次聚类": [
            ("Agglomerative(k=auto)", None),
        ],
    },
}

# 小数据集的精简模型池（n<200时使用，避免过拟合）
SMALL_DATA_POOL = {
    "regression": {
        "线性模型": [
            ("LinearRegression", LinearRegression()),
            ("Ridge(a=1.0)", Ridge(alpha=1.0)),
        ],
        "非线性": [
            ("RandomForest(d=5)", RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42)),
        ],
    },
    "classification": {
        "线性": [
            ("LogisticRegression", LogisticRegression(max_iter=2000, random_state=42)),
        ],
        "非线性": [
            ("RandomForest(d=5)", RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)),
        ],
    },
}


def select_model_pool(problem_type, n_samples):
    """根据问题类型和样本量选择模型池"""
    # 小样本用精简池
    if n_samples < 200:
        pool = SMALL_DATA_POOL.get(problem_type)
        if pool:
            return pool, "精简池(样本量<200)"

    pool = MODEL_POOL.get(problem_type)
    if pool:
        return pool, f"标准池({len(pool)}类)"

    # fallback to regression
    return MODEL_POOL["regression"], "默认回归池"


def run_smart_modeling(df, target_col, problem_type, output_dir):
    """智能建模：按问题类型动态选择模型池"""

    results = {
        "problem_type": problem_type,
        "models_used": {},
        "best_per_category": {},
    }

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()

    # 编码分类变量
    df_model = df.copy()
    for col in cat_cols:
        if col != target_col:
            try:
                le = LabelEncoder()
                df_model[col] = le.fit_transform(df_model[col].astype(str))
            except:
                df_model.drop(columns=[col], inplace=True)

    # 选择模型池
    pool, pool_name = select_model_pool(problem_type, len(df_model))
    results["pool_name"] = pool_name

    # ====== 回归任务 ======
    if problem_type == "regression" and target_col and target_col in df_model.columns:
        feature_cols = [c for c in df_model.columns if c != target_col]
        X = df_model[feature_cols].fillna(0).values
        y = df_model[target_col].fillna(0).values

        # 去极端值
        q1, q3 = np.percentile(y, [1, 99])
        mask = (y >= q1) & (y <= q3)
        X, y = X[mask], y[mask]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        for category, models in pool.items():
            cat_results = {}
            best_model_name = None
            best_r2 = -999

            for name, model in models:
                try:
                    model.fit(X_train_s, y_train)
                    y_pred = model.predict(X_test_s)
                    r2 = r2_score(y_test, y_pred)
                    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                    mae = mean_absolute_error(y_test, y_pred)

                    # 交叉验证
                    try:
                        cv_scores = cross_val_score(
                            model, X_train_s[:min(5000, len(X_train_s))],
                            y_train[:min(5000, len(y_train))], cv=5, scoring="r2"
                        )
                        cv_mean, cv_std = float(np.mean(cv_scores)), float(np.std(cv_scores))
                    except:
                        cv_mean, cv_std = None, None

                    cat_results[name] = {
                        "R2": round(float(r2), 6), "RMSE": round(float(rmse), 6),
                        "MAE": round(float(mae), 6),
                        "CV_R2_mean": round(cv_mean, 6) if cv_mean else None,
                        "CV_R2_std": round(cv_std, 6) if cv_std else None,
                    }

                    if r2 > best_r2:
                        best_r2 = r2
                        best_model_name = name

                except Exception as e:
                    cat_results[name] = {"error": str(e)}

            results["models_used"][category] = cat_results
            if best_model_name:
                results["best_per_category"][category] = {
                    "model": best_model_name,
                    "R2": round(float(best_r2), 6),
                }

        # 全局最优
        all_r2 = [(mname, mdata.get("R2", -999), cat)
                  for cat, models in results["models_used"].items()
                  for mname, mdata in models.items()
                  if isinstance(mdata, dict) and "R2" in mdata]
        if all_r2:
            global_best = max(all_r2, key=lambda x: x[1])
            results["global_best"] = {
                "model": global_best[0], "category": global_best[2], "R2": global_best[1],
            }

        results["sample_size"] = {"train": len(X_train), "test": len(X_test)}
        results["feature_count"] = len(feature_cols)

    # ====== 分类任务 ======
    elif problem_type == "classification" and target_col and target_col in df_model.columns:
        feature_cols = [c for c in df_model.columns if c != target_col]
        X = df_model[feature_cols].fillna(0).values
        y_raw = df_model[target_col].fillna(df_model[target_col].mode()[0]).values
        le = LabelEncoder()
        y = le.fit_transform(y_raw.astype(str))

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        for category, models in pool.items():
            cat_results = {}
            best_acc = -1
            best_name = None

            for name, model in models:
                try:
                    model.fit(X_train_s, y_train)
                    y_pred = model.predict(X_test_s)
                    acc = accuracy_score(y_test, y_pred)
                    prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
                    rec = recall_score(y_test, y_pred, average="weighted", zero_division=0)
                    f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)

                    cat_results[name] = {
                        "Accuracy": round(float(acc), 6), "Precision": round(float(prec), 6),
                        "Recall": round(float(rec), 6), "F1": round(float(f1), 6),
                    }
                    if acc > best_acc:
                        best_acc = acc
                        best_name = name
                except Exception as e:
                    cat_results[name] = {"error": str(e)}

            results["models_used"][category] = cat_results
            if best_name:
                results["best_per_category"][category] = {
                    "model": best_name, "Accuracy": round(float(best_acc), 6),
                }

        all_acc = [(mname, mdata.get("Accuracy", -1), cat)
                   for cat, models in results["models_used"].items()
                   for mname, mdata in models.items()
                   if isinstance(mdata, dict) and "Accuracy" in mdata]
        if all_acc:
            global_best = max(all_acc, key=lambda x: x[1])
            results["global_best"] = {
                "model": global_best[0], "category": global_best[2],
                "Accuracy": global_best[1],
            }

        results["sample_size"] = {"train": len(X_train), "test": len(X_test)}
        results["num_classes"] = len(set(y))

    # ====== 聚类任务 ======
    elif problem_type == "clustering":
        feature_cols = num_cols[:min(20, len(num_cols))]
        X = df_model[feature_cols].fillna(0).values
        scaler = StandardScaler()
        X_s = scaler.fit_transform(X)

        # 自动确定最佳K值
        from sklearn.metrics import silhouette_score as sil_score
        k_range = range(2, min(11, max(3, len(df) // 20)))
        silhouette_scores = []
        for k in k_range:
            km = KMeans(n_clusters=k, n_init=10, random_state=42)
            labels = km.fit_predict(X_s[:min(5000, len(X_s))])
            sil = sil_score(X_s[:min(5000, len(X_s))], labels)
            silhouette_scores.append({"k": k, "silhouette": round(float(sil), 6)})

        if silhouette_scores:
            best_k_result = max(silhouette_scores, key=lambda x: x["silhouette"])
        else:
            best_k_result = {"k": 2, "silhouette": 0}

        # 最佳K聚类
        km_best = KMeans(n_clusters=best_k_result["k"], n_init=10, random_state=42)
        cluster_labels = km_best.fit_predict(X_s)

        results["clustering"] = {
            "best_k": best_k_result["k"],
            "best_silhouette": best_k_result["silhouette"],
            "all_k_scores": silhouette_scores,
            "cluster_sizes": {int(k): int((cluster_labels == k).sum())
                              for k in range(best_k_result["k"])},
        }

    return results


def print_model_report(results):
    """打印模型对比报告"""
    print(f"\n{'='*60}")
    print(f"  智能模型池报告")
    print(f"  问题类型: {results['problem_type']}")
    print(f"  模型池: {results.get('pool_name', 'N/A')}")
    print(f"{'='*60}")

    problem_type = results["problem_type"]

    if problem_type == "regression":
        print(f"\n  {'分类':<20s} {'模型':<25s} {'R2':>8s} {'RMSE':>10s} {'CV均值':>8s}")
        print(f"  {'-'*70}")
        for cat, models in results.get("models_used", {}).items():
            for name, m in models.items():
                if "R2" in m:
                    cv_val = m.get('CV_R2_mean', '-')
                    cv_str = f'{str(cv_val):>8s}'
                    print(f"  {cat:<20s} {name:<25s} {m['R2']:>8.4f} {m['RMSE']:>10.3f} {cv_str}")

        gb = results.get("global_best", {})
        if gb:
            print(f"\n  >>> 全局最优: {gb['model']} ({gb['category']}) R2={gb['R2']:.4f}")

    elif problem_type == "classification":
        print(f"\n  {'分类':<20s} {'模型':<25s} {'准确率':>8s} {'F1':>8s}")
        print(f"  {'-'*60}")
        for cat, models in results.get("models_used", {}).items():
            for name, m in models.items():
                if "Accuracy" in m:
                    print(f"  {cat:<20s} {name:<25s} {m['Accuracy']*100:>7.2f}% {m['F1']:>8.4f}")

        gb = results.get("global_best", {})
        if gb:
            print(f"\n  >>> 全局最优: {gb['model']} ({gb['category']}) Acc={gb['Accuracy']*100:.2f}%")

    print(f"\n  {'='*60}")


if __name__ == "__main__":
    import argparse, json, os

    parser = argparse.ArgumentParser(description="智能模型池")
    parser.add_argument("data_file", help="数据文件路径")
    parser.add_argument("--target", "-t", help="目标变量")
    parser.add_argument("--type", "-p", default="regression",
                        choices=["regression", "classification", "clustering"])
    parser.add_argument("--output", "-o", default=None, help="输出JSON路径")
    args = parser.parse_args()

    df = pd.read_csv(args.data_file) if args.data_file.endswith(".csv") else pd.read_excel(args.data_file)

    # 自动选目标列
    target = args.target or df.columns[-1]
    if args.type == "clustering":
        target = None

    results = run_smart_modeling(df, target, args.type, os.path.dirname(args.output or "."))
    print_model_report(results)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            # 清理不可序列化的对象
            clean = {k: v for k, v in results.items() if k != "figure_paths"}
            json.dump(clean, f, ensure_ascii=False, indent=2)
