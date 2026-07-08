#!/usr/bin/env python3
"""
自评打分模块
按竞赛评阅标准对论文自动打分。
"""

import re

# ============================================================
#  竞赛评阅标准（各竞赛权重不同）
# ============================================================

SCORING_RUBRIC = {
    "国赛": {
        "weights": {
            "摘要": 0.10,
            "问题重述与模型假设": 0.10,
            "模型建立与求解": 0.35,
            "结果分析与模型检验": 0.20,
            "模型评价与推广": 0.10,
            "论文规范与可读性": 0.10,
            "创新性": 0.05,
        },
    },
    "研究生数学建模": {
        "weights": {
            "摘要": 0.10,
            "问题重述与模型假设": 0.10,
            "模型建立与求解": 0.30,
            "结果分析与模型检验": 0.20,
            "模型评价与推广": 0.10,
            "论文规范与可读性": 0.10,
            "创新性": 0.05,
            "代码与数据": 0.05,
        },
    },
    "美赛": {
        "weights": {
            "Summary": 0.15,
            "Problem Restatement & Assumptions": 0.10,
            "Model Development & Solution": 0.30,
            "Sensitivity Analysis": 0.15,
            "Strengths & Weaknesses": 0.10,
            "Conclusions & Letter": 0.10,
            "Clarity & Organization": 0.10,
        },
    },
}


def score_dimension(text, dimension, max_score=100):
    """对单个维度打分"""
    checks = {
        "摘要": [
            (r'.{200,}', 20, "长度>200字"),
            (r'R2\s*[=＝]\s*\d|准确率\s*[=＝达]*\s*\d|RMSE\s*[=＝]\s*\d', 25, "包含具体数值"),
            (r'针对问题', 15, "逐问题列出"),
            (r'关键词', 10, "有关键词"),
            (r'[。；]\s*\n\s*[^关键词]', 10, "分段合理"),
        ],
        "问题重述与模型假设": [
            (r'问题背景|问题重述', 15, "有问题重述"),
            (r'假设.*\n.*假设', 25, "假设逐条列出"),
            (r'符号说明|符号表|Nomenclature', 20, "有符号表"),
            (r'.{200,}', 20, "内容充实"),
        ],
        "模型建立与求解": [
            (r'模型.*建立|模型.*构建|model.*setup', 15, "有模型建立"),
            (r'[Rr]2\s*[=＝]\s*\d|准确率\s*[=＝达]*\s*\d|RMSE\s*[=＝]\s*\d', 20, "有量化结果"),
            (r'表\s*\d|Table\s*\d', 15, "有数据表"),
            (r'图\s*\d|Figure\s*\d', 15, "有图表"),
            (r'交叉验证|cross.validation|CV', 15, "有交叉验证"),
            (r'对比|优于|comparison|better.than', 10, "有模型对比"),
        ],
        "结果分析与模型检验": [
            (r'残差|诊断|检验|test|diagnostic', 20, "有模型诊断"),
            (r'灵敏度|敏感性|sensitivity', 15, "有灵敏度分析"),
            (r'表\s*\d|Table\s*\d', 15, "有结果表"),
            (r'图\s*\d|Figure\s*\d', 15, "有结果图"),
            (r'%|百分点|percent', 10, "有数值分析"),
        ],
        "模型评价与推广": [
            (r'优点|strength|优势', 20, "有优点"),
            (r'缺点|不足|weakness|limitation', 20, "有缺点"),
            (r'改进|推广|improve|future', 20, "有改进方向"),
            (r'.{80,}', 15, "内容充实"),
        ],
        "论文规范与可读性": [
            (r'参考文献|reference|bibliograph', 15, "有参考文献"),
            (r'\[\d+\]', 15, "引用格式正确"),
            (r'目录|contents|toc', 10, "有目录"),
            (r'表\s*\d|Table\s*\d', 10, "表格编号"),
            (r'图\s*\d|Figure\s*\d', 10, "图表编号"),
            (r'公式.*\d|equation.*\d', 10, "公式编号"),
            (r'.{5000,}', 15, "总字数>5000"),
        ],
        "创新性": [
            (r'改进|提出|设计|novel|propose|design', 20, "有新方法"),
            (r'对比|优于|outperforms|better.than', 20, "有创新性对比"),
            (r'首次|第一个|first', 15, "首次声明"),
        ],
        "代码与数据": [
            (r'附录.*代码|appendix.*code|Python|MATLAB', 25, "有代码附录"),
            (r'github|repository|仓库', 20, "有开源仓库"),
            (r'random_state|可复现|reproducible', 20, "可复现性"),
        ],
    }

    dim_checks = checks.get(dimension, [])
    if not dim_checks:
        return max_score * 0.5  # 未知维度给中等分

    total = 0
    max_possible = sum(w for _, w, _ in dim_checks)
    for pattern, weight, desc in dim_checks:
        if re.search(pattern, text, re.IGNORECASE):
            total += weight

    score = (total / max_possible) * max_score
    return round(score, 1)


def score_paper(paper_path, competition_type="国赛"):
    """对论文综合打分"""
    with open(paper_path, "r", encoding="utf-8") as f:
        text = f.read()

    rubric = SCORING_RUBRIC.get(competition_type, SCORING_RUBRIC["国赛"])
    weights = rubric["weights"]

    dimensions = {}
    weighted_total = 0
    total_weight = 0

    print(f"\n{'='*60}")
    print(f"  Self-Scoring Report")
    print(f"  Competition: {competition_type}")
    print(f"{'='*60}")

    for dim, weight in weights.items():
        score = score_dimension(text, dim)
        dimensions[dim] = {"score": score, "weight": weight}
        weighted_total += score * weight
        total_weight += weight

        # 评级
        if score >= 85:
            grade = "A"
        elif score >= 70:
            grade = "B"
        elif score >= 55:
            grade = "C"
        else:
            grade = "D"

        bar = "#" * int(score / 5) + "-" * (20 - int(score / 5))
        print(f"\n  {dim:<20s} [{bar}] {score:.0f}/100 [{grade}] (权重{weight*100:.0f}%)")

        # 关键指标反馈
        if dim == "摘要" and score < 70:
            print(f"    -> 建议：补齐具体数值，用'针对问题X'格式逐题列出")
        if dim == "模型建立与求解" and score < 70:
            print(f"    -> 建议：补充模型对比表、交叉验证、量化指标")
        if dim == "结果分析与模型检验" and score < 70:
            print(f"    -> 建议：补充残差诊断、灵敏度分析")
        if dim == "创新性" and score < 50:
            print(f"    -> 建议：明确写出与已有方法的差异和改进点")
        if dim == "代码与数据" and score < 50:
            print(f"    -> 建议：补充代码附录、标注random_state")

    overall = weighted_total / total_weight if total_weight > 0 else 0

    if overall >= 85:
        verdict = "PASS - Ready for submission"
    elif overall >= 70:
        verdict = "WARN - Fix high-weight low-score items first"
    elif overall >= 60:
        verdict = "FAIL - Revision needed"
    else:
        verdict = "FAIL - Major revision needed"

    print(f"\n  {'='*60}")
    print(f"  Overall Score: {overall:.1f}/100")
    print(f"  Verdict: {verdict}")
    print(f"  {'='*60}")

    return dimensions, overall, verdict


def build_scorer_prompt(paper_text, competition_type):
    """生成LLM评阅prompt"""
    prompt = f"""<task>你是{competition_type}的评阅专家。请按以下标准对论文打分。</task>

<rubric>
{json.dumps(SCORING_RUBRIC.get(competition_type, SCORING_RUBRIC['国赛']), ensure_ascii=False, indent=2)}
</rubric>

<paper>
{paper_text[:8000]}
</paper>

<instructions>
对每个维度打分(0-100)，并给出简短理由（引用论文中的具体文字）。
最后给出总分和改进建议（按重要性排序，每条建议对应论文中具体位置）。
</instructions>
"""
    return prompt


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="论文自评打分")
    parser.add_argument("paper", help="论文txt路径")
    parser.add_argument("--competition", "-c", default="国算",
                        choices=["国赛", "研究生数学建模", "美赛"])
    parser.add_argument("--prompt", action="store_true", help="生成LLM评阅prompt")
    args = parser.parse_args()

    dims, overall, verdict = score_paper(args.paper, args.competition)

    if args.prompt:
        with open(args.paper, "r", encoding="utf-8") as f:
            text = f.read()
        print("\n\n" + "=" * 60)
        print(build_scorer_prompt(text, args.competition))
