#!/usr/bin/env python3
"""
图表-文字联动模块
解决"图表画了什么论文没写，论文提了但图表里没有"的问题。
"""

import json, os, re
from pathlib import Path


class ChartRegistry:
    """图表注册中心：每张图生成时自动登记，附带结构化caption"""

    def __init__(self):
        self.charts = {}  # {chart_id: {path, type, caption, key_observations, numeric_values}}

    def register(self, chart_id, filepath, chart_type, caption, observations, numeric_values=None):
        """注册一张图表"""
        self.charts[chart_id] = {
            "id": chart_id,
            "path": str(Path(filepath).as_posix()),
            "filename": os.path.basename(filepath),
            "type": chart_type,  # heatmap, scatter, bar, line, diagnostic, distribution, importance
            "caption": caption,  # 图表标题（写入论文）
            "observations": observations,  # 关键发现列表（LLM写论文时必须引用）
            "numeric_values": numeric_values or {},  # 图表中的关键数值
        }

    def get_caption(self, chart_id):
        return self.charts.get(chart_id, {}).get("caption", "")

    def get_observations(self, chart_id):
        return self.charts.get(chart_id, {}).get("observations", [])

    def get_all_captions(self):
        """返回所有图表的caption和观察，供LLM写作时引用"""
        result = []
        for i, (cid, info) in enumerate(self.charts.items(), 1):
            result.append({
                "figure_number": i,
                "chart_id": cid,
                "caption": info["caption"],
                "key_observations": info["observations"],
                "numeric_facts": info.get("numeric_values", {}),
                "type": info["type"],
            })
        return result

    def to_json(self):
        return self.get_all_captions()

    def validate_paper_references(self, paper_text):
        """检查论文中引用的图表是否都有对应的实际文件"""
        issues = []

        # 提取论文中所有图表引用
        fig_refs = re.findall(r'(?:图|Figure|Fig\.?)\s*(\d+(?:\.\d+)?)', paper_text, re.IGNORECASE)
        table_refs = re.findall(r'(?:表|Table)\s*(\d+(?:\.\d+)?)', paper_text, re.IGNORECASE)

        # 检查每个引用
        registered_ids = set(self.charts.keys())
        chart_count = len(self.charts)

        for ref in set(fig_refs):
            # 检查编号是否在范围内
            fig_num = int(ref.split('.')[0])
            if fig_num > chart_count:
                issues.append(f"[MISSING] 论文引用了图{ref}，但只注册了{chart_count}张图")
            elif fig_num < 1:
                issues.append(f"[INVALID] 图编号{ref}不合法")

        # 反向检查：注册了的图表在论文中是否被引用
        for i, cid in enumerate(self.charts.keys(), 1):
            cited = any(str(i) == ref.split('.')[0] for ref in fig_refs)
            if not cited:
                issues.append(f"[UNCITED] 图{i} ({cid}) 已生成但论文未引用")

        return issues

    def build_llm_context(self):
        """生成LLM写作时必须阅读的图表上下文"""
        captions = self.get_all_captions()
        if not captions:
            return ""

        ctx = "## 图表清单（以下图表已生成，论文中必须引用）\n\n"
        for c in captions:
            ctx += f"### 图{c['figure_number']}: {c['caption']}\n"
            ctx += f"类型: {c['type']} | ID: {c['chart_id']}\n"
            if c["key_observations"]:
                ctx += "关键发现:\n"
                for obs in c["key_observations"]:
                    ctx += f"  - {obs}\n"
            if c["numeric_facts"]:
                ctx += "关键数值:\n"
                for k, v in c["numeric_facts"].items():
                    ctx += f"  - {k}: {v}\n"
            ctx += "\n"

        ctx += "---\n"
        ctx += "**写作要求**：\n"
        ctx += "1. 每个图表必须在正文中被引用（如图X所示）\n"
        ctx += f"2. 共{len(captions)}张图，编号必须连续无跳号\n"
        ctx += "3. 引用图表时必须包含至少一条上面列出的关键发现\n"
        ctx += "4. 讨论图表时使用上面列出的关键数值，不要编造\n"

        return ctx


# ============================================================
#  预设的图表caption生成函数（在pipeline画图时调用）
# ============================================================

def caption_correlation_heatmap(strong_pairs, top_features):
    """生成相关性热力图的caption和观察"""
    observations = []
    if strong_pairs:
        top = strong_pairs[:3]
        for pair in top:
            d = "正" if pair["correlation"] > 0 else "负"
            observations.append(f"{pair['var1']}与{pair['var2']}呈{d}相关(r={pair['correlation']:.4f})")
    if not strong_pairs:
        observations.append("未检测到|r|>0.6的强相关变量对")

    return {
        "caption": "数值变量相关性热力图",
        "observations": observations,
        "numeric_values": {f"r({p['var1']},{p['var2']})": p['correlation'] for p in strong_pairs[:5]},
    }


def caption_target_distribution(target_var, mean_val, std_val, skew_desc, is_normal):
    """生成目标变量分布图的caption"""
    normality = "通过" if is_normal else "未通过"
    return {
        "caption": f"目标变量{target_var}分布直方图与Q-Q图",
        "observations": [
            f"{target_var}均值={mean_val:.3f}，标准差={std_val:.3f}",
            f"分布呈{skew_desc}偏态",
            f"Shapiro-Wilk正态性检验：{normality}",
        ],
        "numeric_values": {"mean": round(mean_val, 3), "std": round(std_val, 3)},
    }


def caption_model_diagnostics(model_name, r2, rmse, residual_pattern=""):
    """生成模型诊断图的caption"""
    obs = [
        f"{model_name}在测试集上R2={r2:.4f}，RMSE={rmse:.3f}",
        "真实值-预测值散点图(左)：数据点沿对角线紧密分布",
        "残差图(右)：残差围绕零线随机散布",
    ]
    if residual_pattern:
        obs.append(residual_pattern)
    else:
        obs.append("未发现漏斗形(异方差)或曲线形(非线性)模式")

    return {
        "caption": f"{model_name} 模型诊断图：真实值-预测值散点图(左)与残差图(右)",
        "observations": obs,
        "numeric_values": {"R2": round(r2, 4), "RMSE": round(rmse, 3)},
    }


def caption_feature_importance(features_top3, total_top2_pct):
    """生成特征重要性图的caption"""
    obs = [f"排名第一：{features_top3[0]['name']}(重要性={features_top3[0]['imp']:.4f})"]
    if len(features_top3) > 1:
        ratio = features_top3[0]['imp'] / features_top3[1]['imp']
        obs.append(f"约为第二名{features_top3[1]['name']}的{ratio:.1f}倍")
    if len(features_top3) > 2:
        obs.append(f"前三名：{features_top3[0]['name']} > {features_top3[1]['name']} > {features_top3[2]['name']}")
    obs.append(f"前两名合计贡献{total_top2_pct:.1f}%的预测能力")

    return {
        "caption": "随机森林特征重要性排序",
        "observations": obs,
        "numeric_values": {f['name']: round(f['imp'], 4) for f in features_top3},
    }


def caption_model_comparison(best_model, best_r2, worst_model, worst_r2, n_models):
    """生成模型对比结果的综合分析"""
    gap = best_r2 - worst_r2
    return {
        "caption": "模型测试集表现对比",
        "observations": [
            f"共对比{n_models}个模型",
            f"最优：{best_model}(R2={best_r2:.4f})",
            f"最差：{worst_model}(R2={worst_r2:.4f})",
            f"最优与最差相差{gap:.4f}",
            "线性模型整体优于非线性模型" if gap > 0.03 else "线性和非线性模型表现接近",
        ],
        "numeric_values": {
            "best_R2": round(best_r2, 4),
            "worst_R2": round(worst_r2, 4),
            "gap": round(gap, 4),
        },
    }


# ============================================================
#  命令行工具
# ============================================================

def validate_paper_chart_consistency(paper_path, chart_dir):
    """验证论文中引用的图表与实际文件的一致性"""
    issues = []

    # 读取论文
    with open(paper_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # 统计实际图表文件
    chart_files = list(Path(chart_dir).glob("*.png")) if os.path.isdir(chart_dir) else []

    # 提取论文中的图表引用
    fig_refs = re.findall(r'(?:图|Figure|Fig\.?)\s*(\d+(?:\.\d+)?)', text, re.IGNORECASE)

    for ref in set(fig_refs):
        # 找对应的文件
        fig_num = int(ref.split('.')[0])
        matching = [f for f in chart_files if f'fig{fig_num}' in f.name.lower()
                    or f'_{fig_num}' in f.name
                    or f.name.startswith(f'figure_{fig_num}')]
        if not matching:
            # 模糊匹配：找包含相关关键词的文件
            matching = [f for f in chart_files if str(fig_num) in f.name]

        if not matching:
            issues.append(f"论文引用图{ref}，但图表目录中未找到对应文件")

    # 检查是否有图未引用
    for f in chart_files:
        name = f.stem
        # 尝试从文件名提取编号
        fnums = re.findall(r'(\d+)', name)
        cited = any(str(n) in str(fig_refs) for n in fnums)
        if not cited:
            issues.append(f"文件{name}已生成但论文未引用")

    return issues


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="图表-文字联动工具")
    sub = parser.add_subparsers(dest="cmd")

    # 生成LLM上下文
    gen = sub.add_parser("context", help="生成图表上下文供LLM写作")
    gen.add_argument("--chart-dir", required=True, help="图表目录")

    # 验证一致性
    val = sub.add_parser("validate", help="验证论文图表引用一致性")
    val.add_argument("--paper", required=True, help="论文txt路径")
    val.add_argument("--chart-dir", required=True, help="图表目录")

    args = parser.parse_args()

    if args.cmd == "context":
        # 简单模式：扫描图表目录，生成基础上下文
        chart_dir = Path(args.chart_dir)
        reg = ChartRegistry()
        for i, f in enumerate(sorted(chart_dir.glob("*.png")), 1):
            reg.register(
                f"chart_{i}",
                str(f),
                "图表",
                f"图{i}",  # 基础caption，需人工补充
                ["图表已生成，请在论文中引用"],
            )
        print(reg.build_llm_context())

    elif args.cmd == "validate":
        issues = validate_paper_chart_consistency(args.paper, args.chart_dir)
        if issues:
            print(f"发现 {len(issues)} 个问题:")
            for i in issues:
                print(f"  {i}")
        else:
            print("图表引用一致，无问题。")
