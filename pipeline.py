#!/usr/bin/env python3
"""
数学建模竞赛论文 - 数据自动分析管线
=====================================
输入：CSV/Excel 数据集
输出：结构化 JSON 分析报告（直接喂给 math-model-paper skill）

用法：
    python pipeline.py data.csv --target y_col --type regression
    python pipeline.py data.csv --target y_col --type classification
    python pipeline.py data.csv --type clustering
"""

import argparse, json, os, sys, warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

# ============================================================
#  0. 配置
# ============================================================

OUTPUT_DIR = None  # 图表输出目录，运行时设置


def ensure_output_dir(base_dir, problem_name):
    """创建输出目录"""
    global OUTPUT_DIR
    OUTPUT_DIR = Path(base_dir) / f"output_{problem_name}"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


# ============================================================
#  1. 数据加载与预处理
# ============================================================

def to_native(obj):
    """递归转换 numpy 类型为 Python 原生类型"""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: to_native(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [to_native(i) for i in obj]
    return obj


def load_data(file_path):
    """自动识别格式加载数据"""
    ext = Path(file_path).suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(file_path)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")
    return df


def preprocess(df, target_col=None):
    """基础预处理"""
    report = {}
    original_shape = df.shape

    # 缺失值统计
    missing = df.isnull().sum()
    report["missing_values"] = {
        col: int(cnt)
        for col, cnt in missing[missing > 0].to_dict().items()
    }

    # 删除全空列
    df = df.dropna(axis=1, how="all")

    # 数值列填充中位数
    num_cols = df.select_dtypes(include=[np.number]).columns
    for col in num_cols:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].median())

    # 分类列填充众数
    cat_cols = df.select_dtypes(exclude=[np.number]).columns
    for col in cat_cols:
        if df[col].isnull().sum() > 0:
            df[col] = df[col].fillna(df[col].mode()[0] if len(df[col].mode()) > 0 else "Unknown")

    report["original_shape"] = list(original_shape)
    report["cleaned_shape"] = list(df.shape)
    report["removed_cols"] = original_shape[1] - df.shape[1]

    return df, report


# ============================================================
#  2. 探索性数据分析 (EDA)
# ============================================================

def run_eda(df, target_col=None):
    """完整的探索性数据分析"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    # 中文字体设置
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    results = {}
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()

    # --- 2.1 数据概览 ---
    results["overview"] = {
        "total_samples": len(df),
        "total_features": len(df.columns),
        "numeric_features": len(num_cols),
        "categorical_features": len(cat_cols),
        "columns": df.columns.tolist(),
        "dtypes": {col: str(dt) for col, dt in df.dtypes.to_dict().items()},
    }

    # --- 2.2 描述性统计 ---
    if num_cols:
        desc = df[num_cols].describe()
        results["descriptive_stats"] = {
            col: {
                "mean": round(float(desc[col]["mean"]), 6),
                "std": round(float(desc[col]["std"]), 6),
                "min": round(float(desc[col]["min"]), 6),
                "25%": round(float(desc[col]["25%"]), 6),
                "50%": round(float(desc[col]["50%"]), 6),
                "75%": round(float(desc[col]["75%"]), 6),
                "max": round(float(desc[col]["max"]), 6),
            }
            for col in num_cols[:20]  # 限制前20列
        }

    # --- 2.3 正态性检验 ---
    normality_results = {}
    for col in num_cols[:15]:
        sample = df[col].dropna()
        if len(sample) > 3 and len(sample) < 5000:
            # 抽样
            if len(sample) > 2000:
                sample = sample.sample(2000, random_state=42)
            # Shapiro-Wilk
            try:
                stat_val, p_val = stats.shapiro(sample)
                normality_results[col] = {
                    "test": "Shapiro-Wilk",
                    "statistic": round(float(stat_val), 6),
                    "p_value": round(float(p_val), 6),
                    "is_normal": p_val > 0.05,
                }
            except:
                pass
    results["normality_tests"] = normality_results

    # --- 2.4 相关性矩阵 + 热力图 ---
    if len(num_cols) >= 2:
        corr_cols = num_cols[:15]
        corr_matrix = df[corr_cols].corr()

        # 找出强相关对 (|r| > 0.6)
        strong_corr = []
        for i in range(len(corr_cols)):
            for j in range(i + 1, len(corr_cols)):
                r = corr_matrix.iloc[i, j]
                if abs(r) > 0.6:
                    strong_corr.append(
                        {
                            "var1": corr_cols[i],
                            "var2": corr_cols[j],
                            "correlation": round(float(r), 4),
                        }
                    )
        results["correlation"] = {
            "strong_pairs": strong_corr[:30],
            "matrix_snippet": {
                col: {
                    col2: round(float(corr_matrix[col][col2]), 4)
                    for col2 in corr_cols[:8]
                }
                for col in corr_cols[:8]
            },
        }

        # 热力图
        fig, ax = plt.subplots(figsize=(12, 10))
        mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
        sns.heatmap(
            corr_matrix, mask=mask, annot=True, fmt=".2f",
            cmap="RdBu_r", center=0, square=True,
            linewidths=0.5, ax=ax,
        )
        ax.set_title("Correlation Heatmap of Numeric Features", fontsize=14)
        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / "correlation_heatmap.png", dpi=150)
        plt.close(fig)

    # --- 2.5 目标变量分布 (如果有) ---
    if target_col and target_col in df.columns:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        # 直方图 + KDE
        if target_col in num_cols:
            df[target_col].dropna().hist(bins=50, ax=axes[0], edgecolor="white")
            axes[0].set_title(f"Distribution of {target_col}", fontsize=12)
            axes[0].set_xlabel(target_col)
            axes[0].set_ylabel("Frequency")

            # QQ plot
            stats.probplot(df[target_col].dropna(), dist="norm", plot=axes[1])
            axes[1].set_title(f"Q-Q Plot of {target_col}", fontsize=12)
        else:
            value_counts = df[target_col].value_counts().head(15)
            axes[0].bar(range(len(value_counts)), value_counts.values)
            axes[0].set_xticks(range(len(value_counts)))
            axes[0].set_xticklabels(value_counts.index, rotation=45, ha="right")
            axes[0].set_title(f"Distribution of {target_col}", fontsize=12)
        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / "target_distribution.png", dpi=150)
        plt.close(fig)

    results["figures"] = [
        {"path": str(OUTPUT_DIR / "correlation_heatmap.png"), "caption": "变量相关性热力图"},
    ]
    if target_col and target_col in df.columns:
        results["figures"].append(
            {"path": str(OUTPUT_DIR / "target_distribution.png"), "caption": f"目标变量 {target_col} 分布图"}
        )

    return results


# ============================================================
#  3. 建模分析
# ============================================================

def run_modeling(df, target_col, problem_type):
    """
    根据问题类型跑相应模型。
    返回：模型名称、评估指标、特征重要性、对比结果
    """
    from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import (
        r2_score, mean_squared_error, mean_absolute_error,
        accuracy_score, precision_score, recall_score, f1_score,
        confusion_matrix, roc_auc_score, silhouette_score,
    )
    from sklearn.linear_model import LinearRegression, Ridge, Lasso, LogisticRegression
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, GradientBoostingRegressor, GradientBoostingClassifier
    from sklearn.svm import SVR, SVC
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.decomposition import PCA

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    results = {"problem_type": problem_type}

    # 预处理
    df_model = df.copy()
    num_cols = df_model.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df_model.select_dtypes(exclude=[np.number]).columns.tolist()

    # 编码分类变量
    for col in cat_cols:
        if col != target_col:
            try:
                le = LabelEncoder()
                df_model[col] = le.fit_transform(df_model[col].astype(str))
            except:
                df_model = df_model.drop(columns=[col])

    # --- 回归任务 ---
    if problem_type == "regression" and target_col and target_col in num_cols:
        # 特征和目标
        feature_cols = [c for c in df_model.columns if c != target_col and c in num_cols]
        if not feature_cols:
            feature_cols = [c for c in df_model.columns if c != target_col]

        X = df_model[feature_cols].fillna(0).values
        y = df_model[target_col].fillna(0).values

        # 去除 y 中的极端异常值
        q1, q3 = np.percentile(y, [1, 99])
        mask = (y >= q1) & (y <= q3)
        X, y = X[mask], y[mask]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        models = {
            "LinearRegression": LinearRegression(),
            "Ridge": Ridge(alpha=1.0),
            "Lasso": Lasso(alpha=0.01, max_iter=5000),
            "RandomForest": RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42),
            "GradientBoosting": GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42),
        }

        model_results = {}
        best_model = None
        best_r2 = -999

        for name, model in models.items():
            try:
                model.fit(X_train_s, y_train)
                y_pred = model.predict(X_test_s)
                r2 = r2_score(y_test, y_pred)
                rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                mae = mean_absolute_error(y_test, y_pred)

                # 交叉验证
                try:
                    cv_scores = cross_val_score(model, X_train_s[:min(5000, len(X_train_s))], y_train[:min(5000, len(y_train))], cv=5, scoring="r2")
                    cv_mean = float(np.mean(cv_scores))
                    cv_std = float(np.std(cv_scores))
                except:
                    cv_mean, cv_std = None, None

                model_results[name] = {
                    "R2": round(float(r2), 6),
                    "RMSE": round(float(rmse), 6),
                    "MAE": round(float(mae), 6),
                    "CV_R2_mean": round(cv_mean, 6) if cv_mean else None,
                    "CV_R2_std": round(cv_std, 6) if cv_std else None,
                }

                if r2 > best_r2:
                    best_r2 = r2
                    best_model = name

                # 残差图 (前三个模型)
                if name in ["LinearRegression", "RandomForest", "GradientBoosting"]:
                    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
                    axes[0].scatter(y_test, y_pred, alpha=0.5, s=10)
                    axes[0].plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], "r--", lw=1)
                    axes[0].set_xlabel("True")
                    axes[0].set_ylabel("Predicted")
                    axes[0].set_title(f"{name}: True vs Predicted (R²={r2:.4f})")

                    residuals = y_test - y_pred
                    axes[1].scatter(y_pred, residuals, alpha=0.5, s=10)
                    axes[1].axhline(y=0, color="r", linestyle="--", lw=1)
                    axes[1].set_xlabel("Predicted")
                    axes[1].set_ylabel("Residuals")
                    axes[1].set_title(f"{name}: Residual Plot")
                    fig.tight_layout()
                    fig.savefig(OUTPUT_DIR / f"regression_{name}_diagnostics.png", dpi=150)
                    plt.close(fig)
            except Exception as e:
                model_results[name] = {"error": str(e)}

        # 特征重要性 (RandomForest)
        try:
            rf = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
            rf.fit(X_train_s, y_train)
            importances = rf.feature_importances_
            indices = np.argsort(importances)[::-1][:15]
            feature_importance = [
                {"feature": feature_cols[i], "importance": round(float(importances[i]), 6)}
                for i in indices
            ]
            results["feature_importance"] = feature_importance

            # 特征重要性图
            fig, ax = plt.subplots(figsize=(10, 6))
            top_features = feature_importance[:12]
            ax.barh(
                [f["feature"] for f in reversed(top_features)],
                [f["importance"] for f in reversed(top_features)],
            )
            ax.set_xlabel("Importance")
            ax.set_title("Feature Importance (Random Forest)", fontsize=13)
            fig.tight_layout()
            fig.savefig(OUTPUT_DIR / "feature_importance.png", dpi=150)
            plt.close(fig)
        except:
            pass

        results["models"] = model_results
        results["best_model"] = best_model
        results["best_r2"] = round(float(best_r2), 6)
        results["feature_columns"] = feature_cols[:20]
        results["sample_size"] = {"train": len(X_train), "test": len(X_test)}
        results["figures"] = [
            {"path": str(OUTPUT_DIR / f"regression_{m}_diagnostics.png"), "caption": f"{m} 回归诊断图"}
            for m in ["LinearRegression", "RandomForest", "GradientBoosting"]
            if m in model_results and "error" not in model_results[m]
        ]
        results["figures"].append(
            {"path": str(OUTPUT_DIR / "feature_importance.png"), "caption": "随机森林特征重要性排序"}
        )

    # --- 分类任务 ---
    elif problem_type == "classification" and target_col and target_col in df.columns:
        feature_cols = [c for c in df_model.columns if c != target_col]
        X = df_model[feature_cols].fillna(0).values
        y_raw = df_model[target_col].fillna(df_model[target_col].mode()[0]).values

        # 标签编码
        le = LabelEncoder()
        y = le.fit_transform(y_raw.astype(str))
        classes = le.classes_.tolist()

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        scaler = StandardScaler()
        X_train_s = scaler.fit_transform(X_train)
        X_test_s = scaler.transform(X_test)

        models = {
            "LogisticRegression": LogisticRegression(max_iter=2000, random_state=42),
            "RandomForest": RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42),
            "GradientBoosting": GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42),
        }
        # SVM only for smaller datasets
        if len(X_train) < 10000:
            models["SVM"] = SVC(kernel="rbf", probability=True, random_state=42)

        model_results = {}
        best_model = None
        best_acc = -1

        for name, model in models.items():
            try:
                model.fit(X_train_s, y_train)
                y_pred = model.predict(X_test_s)
                acc = accuracy_score(y_test, y_pred)
                prec = precision_score(y_test, y_pred, average="weighted", zero_division=0)
                rec = recall_score(y_test, y_pred, average="weighted", zero_division=0)
                f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)

                model_results[name] = {
                    "Accuracy": round(float(acc), 6),
                    "Precision": round(float(prec), 6),
                    "Recall": round(float(rec), 6),
                    "F1_Score": round(float(f1), 6),
                }

                if acc > best_acc:
                    best_acc = acc
                    best_model = name

                # 混淆矩阵图
                fig, ax = plt.subplots(figsize=(8, 6))
                cm = confusion_matrix(y_test, y_pred)
                sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax)
                ax.set_xlabel("Predicted")
                ax.set_ylabel("True")
                ax.set_title(f"{name}: Confusion Matrix (Acc={acc:.4f})")
                fig.tight_layout()
                fig.savefig(OUTPUT_DIR / f"classification_{name}_cm.png", dpi=150)
                plt.close(fig)
            except Exception as e:
                model_results[name] = {"error": str(e)}

        results["models"] = model_results
        results["best_model"] = best_model
        results["best_accuracy"] = round(float(best_acc), 6)
        results["num_classes"] = len(classes)
        results["classes"] = classes[:20]
        results["sample_size"] = {"train": len(X_train), "test": len(X_test)}
        results["figures"] = [
            {"path": str(OUTPUT_DIR / f"classification_{m}_cm.png"), "caption": f"{m} 混淆矩阵"}
            for m in model_results if "error" not in model_results[m]
        ]

    # --- 聚类任务 ---
    elif problem_type == "clustering":
        feature_cols = num_cols[:20]
        X = df[feature_cols].fillna(0).values
        scaler = StandardScaler()
        X_s = scaler.fit_transform(X)

        # PCA 降维可视化
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_s)
        pca_var = pca.explained_variance_ratio_

        # KMeans 聚类
        from sklearn.metrics import silhouette_score as sil_score
        k_values = range(2, min(11, len(df) // 10))
        silhouette_scores = []
        inertia_values = []
        best_k, best_sil = 2, -1

        for k in k_values:
            km = KMeans(n_clusters=k, n_init=10, random_state=42)
            labels = km.fit_predict(X_s[:5000])
            sil = sil_score(X_s[:5000], labels)
            inertia_values.append(float(km.inertia_))
            silhouette_scores.append({"k": k, "silhouette_score": round(float(sil), 6)})
            if sil > best_sil:
                best_sil = sil
                best_k = k

        # 最佳 K 聚类结果
        km_best = KMeans(n_clusters=best_k, n_init=10, random_state=42)
        cluster_labels = km_best.fit_predict(X_s)
        results["clustering"] = {
            "best_k": best_k,
            "best_silhouette": round(float(best_sil), 6),
            "silhouette_scores": silhouette_scores,
            "cluster_sizes": {
                int(k): int((cluster_labels == k).sum())
                for k in range(best_k)
            },
            "pca_variance_ratio": [round(float(v), 6) for v in pca_var],
        }

        # 肘部法则图 + 轮廓系数图
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        axes[0].plot(list(k_values), inertia_values, "bo-")
        axes[0].set_xlabel("K")
        axes[0].set_ylabel("Inertia")
        axes[0].set_title("Elbow Method", fontsize=12)
        sil_vals = [s["silhouette_score"] for s in silhouette_scores]
        axes[1].plot(list(k_values), sil_vals, "ro-")
        axes[1].set_xlabel("K")
        axes[1].set_ylabel("Silhouette Score")
        axes[1].set_title(f"Silhouette Analysis (Best K={best_k})", fontsize=12)
        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / "clustering_k_selection.png", dpi=150)
        plt.close(fig)

        # PCA 散点图
        fig, ax = plt.subplots(figsize=(10, 8))
        scatter = ax.scatter(X_pca[:5000, 0], X_pca[:5000, 1], c=cluster_labels[:5000], cmap="tab10", alpha=0.6, s=10)
        ax.set_xlabel(f"PC1 ({pca_var[0]*100:.1f}%)")
        ax.set_ylabel(f"PC2 ({pca_var[1]*100:.1f}%)")
        ax.set_title(f"PCA Visualization with K-Means Clusters (K={best_k})")
        plt.colorbar(scatter, ax=ax)
        fig.tight_layout()
        fig.savefig(OUTPUT_DIR / "clustering_pca.png", dpi=150)
        plt.close(fig)

        results["figures"] = [
            {"path": str(OUTPUT_DIR / "clustering_k_selection.png"), "caption": "K值选择：肘部法则与轮廓系数"},
            {"path": str(OUTPUT_DIR / "clustering_pca.png"), "caption": f"PCA降维后的 K-Means(K={best_k})聚类结果"},
        ]

    return results


# ============================================================
#  4. 组装最终 JSON 报告
# ============================================================

def build_report(df, target_col, problem_type, problem_title, file_path):
    """组装完整分析报告 JSON"""
    print("=" * 60)
    print(f"  数据分析管线启动")
    print(f"  数据: {file_path}")
    print(f"  问题类型: {problem_type}")
    print(f"  目标变量: {target_col}")
    print("=" * 60)

    # EDA
    print("\n[1/3] Running EDA...")
    eda_results = run_eda(df, target_col)
    print(f"  -> Shape: {eda_results['overview']['total_samples']} rows x {eda_results['overview']['total_features']} cols")
    normality_normal = sum(1 for v in eda_results.get("normality_tests", {}).values() if v.get("is_normal"))
    print(f"  -> Normal: {normality_normal}/{len(eda_results.get('normality_tests', {}))} passed")
    if "correlation" in eda_results:
        print(f"  -> Strong corr (|r|>0.6): {len(eda_results['correlation']['strong_pairs'])} pairs")

    # 建模
    print("\n[2/3] Running models...")
    model_results = run_modeling(df, target_col, problem_type)
    if problem_type == "regression":
        print(f"  -> Best model: {model_results.get('best_model')} (R2={model_results.get('best_r2')})")
        for m, r in model_results.get("models", {}).items():
            if "R2" in r:
                print(f"     {m}: R2={r['R2']}, RMSE={r['RMSE']}")
    elif problem_type == "classification":
        print(f"  -> Best model: {model_results.get('best_model')} (Acc={model_results.get('best_accuracy')})")
    elif problem_type == "clustering":
        c = model_results.get("clustering", {})
        print(f"  -> Best K: {c.get('best_k')}, Silhouette: {c.get('best_silhouette')}")

    # 组装
    print("\n[3/3] Building report...")
    report = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "data_file": str(Path(file_path).name),
            "competition_type": "研究生数学建模" if "研究生" in problem_title else "全国大学生数学建模竞赛",
            "problem_title": problem_title,
            "problem_type": problem_type,
            "target_variable": target_col,
        },
        "data_overview": eda_results["overview"],
        "descriptive_stats": eda_results.get("descriptive_stats", {}),
        "normality_tests": eda_results.get("normality_tests", {}),
        "correlation": eda_results.get("correlation", {}),
        "modeling": model_results,
        "all_figures": (eda_results.get("figures", []) + model_results.get("figures", [])),
    }

    return report


# ============================================================
#  5. 命令行入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="数学建模竞赛论文 - 数据自动分析管线")
    parser.add_argument("data_file", help="数据集文件路径 (CSV/Excel)")
    parser.add_argument("--target", "-t", default=None, help="目标变量列名")
    parser.add_argument("--type", "-p", default="regression",
                        choices=["regression", "classification", "clustering", "time_series"],
                        help="问题类型")
    parser.add_argument("--title", default="数据分析与建模研究", help="论文题目")
    parser.add_argument("--output", "-o", default=None, help="输出 JSON 路径 (默认自动生成)")
    parser.add_argument("--output-dir", "-d", default="./output", help="图表输出目录")

    args = parser.parse_args()

    # 验证文件存在
    if not os.path.exists(args.data_file):
        print(f"错误: 找不到文件 {args.data_file}")
        sys.exit(1)

    # 输出目录
    problem_name = Path(args.data_file).stem
    out_dir = ensure_output_dir(args.output_dir or ".", problem_name)

    # 加载数据
    print(f"\n加载数据: {args.data_file}")
    df = load_data(args.data_file)
    print(f"原始形状: {df.shape}")

    # 预处理
    df_clean, preproc_report = preprocess(df, args.target)
    print(f"清洗后形状: {df_clean.shape}")

    # 自动检测目标列
    target_col = args.target
    if target_col is None and args.type in ("regression", "classification"):
        # 选择最后一列作为默认目标
        target_col = df_clean.columns[-1]
        print(f"未指定目标变量，自动选择最后一列: {target_col}")

    if args.type == "clustering":
        target_col = None

    # 运行分析
    report = build_report(df_clean, target_col, args.type, args.title, args.data_file)
    report["preprocessing"] = preproc_report

    # 输出
    output_path = args.output or str(out_dir / "analysis_report.json")
    # 把绝对路径转相对，方便跨平台
    for f in report["all_figures"]:
        f["path"] = str(Path(f["path"]).as_posix())

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(to_native(report), f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"  Done!")
    print(f"  Report: {output_path}")
    print(f"  Charts: {out_dir}")
    print(f"{'='*60}")
    return report


if __name__ == "__main__":
    main()
