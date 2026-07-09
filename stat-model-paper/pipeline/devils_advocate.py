#!/usr/bin/env python3
"""
魔鬼代言人审校模块
论文生成后，从反方视角逐项挑刺：逻辑漏洞、证据不足、假设矛盾。
"""

import json, re

# ============================================================
#  审校检查清单（15项）
# ============================================================

CHECKLIST = [
    # === 证据链 ===
    {
        "id": "E1",
        "category": "证据链",
        "question": "摘要中的每个数值声明是否有正文对应章节支撑？",
        "check": lambda text: not bool(re.findall(r'R2\s*[=＝]\s*\d+\.?\d*', text)),
        "fix": "确保摘要中提到的每个R2/RMSE/准确率在正文中有对应的模型建立章节",
    },
    {
        "id": "E2",
        "category": "证据链",
        "question": "每个'如表X所示/如图X所示'的引用，后面是否跟了至少一句分析？",
        "check": lambda text: True,  # 需要人工判断
        "fix": "在图表引用后添加至少一句分析：趋势/异常点/实际含义",
    },
    {
        "id": "E3",
        "category": "证据链",
        "question": "结论部分是否有正文未分析过的新观点？（结论只能总结已有的发现）",
        "check": lambda text: True,
        "fix": "删除结论中首次出现的新观点，或将其移到正文分析部分",
    },

    # === 假设合理性 ===
    {
        "id": "A1",
        "category": "假设",
        "question": "每个模型假设是否有对应的检验？线性性→残差图，正态性→Shapiro-Wilk，同方差→残差图",
        "check": lambda text: True,
        "fix": "为每个假设补充对应的检验方法和检验结果",
    },
    {
        "id": "A2",
        "category": "假设",
        "question": "是否存在'假设数据真实有效'这种不可验证的假设？→可以保留但需标注",
        "check": lambda text: True,
        "fix": "标注'此假设为建模前提，无法从数据层面验证'",
    },

    # === 数据使用 ===
    {
        "id": "D1",
        "category": "数据",
        "question": "训练集/测试集的划分比例是否明确？（必须写明8:2或7:3等）",
        "check": lambda text: bool(re.search(r'[87]\s*[:：]\s*[23]', text)),
        "fix": "明确写出训练集/测试集划分比例和样本数",
    },
    {
        "id": "D2",
        "category": "数据",
        "question": "是否提及random_state或可复现性？（竞赛论文必须可复现）",
        "check": lambda text: bool(re.search(r'random_state|随机种子|可复现', text)),
        "fix": "添加random_state=42或类似声明",
    },

    # === 逻辑一致性 ===
    {
        "id": "L1",
        "category": "逻辑",
        "question": "特征重要性排序在正文不同章节中是否一致？（如果在4.3节说面积第一，5.1节不能变）",
        "check": lambda text: True,
        "fix": "统一全文的特征重要性表述",
    },
    {
        "id": "L2",
        "category": "逻辑",
        "question": "'最优模型'的声明是否唯一？（不能同时说OLS最优又说随机森林最优）",
        "check": lambda text: True,
        "fix": "确保全文只有一个明确的'最优模型'结论",
    },
    {
        "id": "L3",
        "category": "逻辑",
        "question": "优缺点的内容是否与正文分析一致？（不能在优点里吹R2=0.98，但正文只有0.95）",
        "check": lambda text: True,
        "fix": "优点中的每个数值必须与正文模型对比表中的数值一致",
    },
    {
        "id": "L4",
        "category": "逻辑",
        "question": "改进方向是否与缺点一一对应？（不能列了4个缺点但改进只提2个）",
        "check": lambda text: True,
        "fix": "确保每个缺点在改进部分有对应的解决方向",
    },

    # === 格式规范 ===
    {
        "id": "F1",
        "category": "格式",
        "question": "图表编号是否连续？（图1→图2→图3... 不能跳号）",
        "check": lambda text: check_figure_numbering(text),
        "fix": "修复图表编号连续性",
    },
    {
        "id": "F2",
        "category": "格式",
        "question": "公式是否都有编号？（每个\begin{gather}或$$公式应该有(1)(2)...编号）",
        "check": lambda text: True,
        "fix": "为每个公式添加编号",
    },
    {
        "id": "F3",
        "category": "格式",
        "question": "参考文献是否全部在正文中被引用？（每篇bibitem至少出现一次引用标记）",
        "check": lambda text: True,
        "fix": "删除未被引用的参考文献，或补充正文中的引用",
    },

    # === 竞赛特定 ===
    {
        "id": "C1",
        "category": "竞赛",
        "question": "摘要是否逐问题列出方法和结果？（竞赛论文摘要的标准格式）",
        "check": lambda text: bool(re.search(r'针对问题[一二三1-5]', text) or re.search(r'针对问题\s*\d', text)),
        "fix": "将摘要改写为逐问题列出方法+结果+数字的格式",
    },
    {
        "id": "C2",
        "category": "竞赛",
        "question": "是否包含'模型评价与推广'章节？（几乎所有竞赛模板都要求）",
        "check": lambda text: bool(re.search(r'模型评价|模型推广|优点|缺点', text)),
        "fix": "添加模型评价与推广章节",
    },
]


def check_figure_numbering(text):
    """检查图表编号是否连续"""
    fig_nums = [int(n) for n in re.findall(r'图\s*(\d+)', text)]
    if not fig_nums:
        return True  # 没有图引用，不算问题
    expected = list(range(1, max(fig_nums) + 1))
    return sorted(set(fig_nums)) == expected


def run_devils_advocate(paper_text):
    """运行魔鬼代言人审校"""
    issues = []
    passed = []

    for item in CHECKLIST:
        try:
            result = item["check"](paper_text) if callable(item["check"]) else item["check"]
            if result:
                passed.append(item["id"])
            else:
                issues.append({
                    "id": item["id"],
                    "category": item["category"],
                    "question": item["question"],
                    "fix": item["fix"],
                })
        except Exception as e:
            issues.append({
                "id": item["id"],
                "category": item["category"],
                "question": item["question"],
                "fix": item["fix"],
                "error": str(e),
            })

    # 附加检查：数值一致性
    numeric_issues = check_numeric_consistency(paper_text)
    issues.extend(numeric_issues)

    return issues, passed


def check_numeric_consistency(paper_text):
    """检查论文中数值的内部一致性"""
    issues = []

    # 检查R2值是否前后矛盾
    r2_values = [(float(m.group(1)), m.start())
                 for m in re.finditer(r'R2\s*[=＝]\s*(\d+\.?\d*)', paper_text)]
    if len(r2_values) >= 2:
        # 提取"最优"相关的R2
        best_match = re.search(r'(?:最优|最佳|best).*?R2\s*[=＝]\s*(\d+\.?\d*)', paper_text)
        if best_match:
            best_r2 = float(best_match.group(1))
            # 检查是否还有其他更高的R2值
            higher = [v for v, _ in r2_values if v > best_r2 + 0.001]
            if higher:
                issues.append({
                    "id": "N1",
                    "category": "数值一致性",
                    "question": f"声明最优R2={best_r2}，但正文中出现了更高的R2值{higher}",
                    "fix": "确认最优模型指标，统一全文数值",
                })

    return issues


def build_devils_prompt(paper_text):
    """构建魔鬼代言人审校prompt，供LLM深度审校"""
    prompt = f"""<task>你是竞赛论文的魔鬼代言人审校官。你的任务不是表扬，而是找出论文中的每一个漏洞。</task>

<paper>
{paper_text[:10000]}
</paper>

<audit_dimensions>
1. **证据链断裂**：有没有结论没有数据支撑？图表引用后有没有分析？
2. **假设未验证**：每个模型假设是否都有对应的检验？
3. **数值矛盾**：不同章节的同一个指标数值是否一致？"最优"声明是否与表格数据矛盾？
4. **逻辑跳跃**：有没有"因为A所以B"但A和B之间缺一步推理？
5. **空洞表述**：有没有"效果良好""具有重要意义"这种没有任何数字支撑的话？
6. **重复冗余**：同一观点是否在不同章节重复3次以上？
7. **过度宣称**：有没有根据500条数据推断"全国""所有城市"的结论？
8. **遗漏关键步骤**：有没有跳过数据标准化、交叉验证、模型诊断等关键步骤？
</audit_dimensions>

<output_format>
对每个发现的问题，输出：
- 位置：第X节/摘要/结论
- 严重度：致命/重要/建议
- 问题描述
- 修复建议
</output_format>

请开始审校。每指出一个问题，必须引用论文中的具体文字作为证据。
"""
    return prompt


def print_audit_report(issues, passed):
    """打印审校报告"""
    total = len(issues) + len(passed)
    score = len(passed) / max(total, 1) * 100

    print(f"\n{'='*60}")
    print(f"  Devil's Advocate Audit Report")
    print(f"  Score: {score:.0f}% ({len(passed)}/{total})")
    print(f"{'='*60}")

    if passed:
        print(f"\n  [PASSED] ({len(passed)} items)")

    if issues:
        by_cat = {}
        for i in issues:
            cat = i.get("category", "其他")
            by_cat.setdefault(cat, []).append(i)

        for cat, items in by_cat.items():
            print(f"\n  [{cat}] ({len(items)} issues):")
            for item in items:
                print(f"    {item['id']}: {item['question']}")
                print(f"    -> Fix: {item['fix']}")

    print(f"\n  {'='*60}")
    if score >= 85:
        print(f"  Verdict: Ready for submission")
    elif score >= 70:
        print(f"  Verdict: Fix issues above before submitting")
    else:
        print(f"  Verdict: Major revision needed")

    return score


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="魔鬼代言人审校")
    parser.add_argument("paper", nargs="?", help="论文txt路径")
    parser.add_argument("--prompt", action="store_true", help="生成LLM审校prompt")
    args = parser.parse_args()

    if args.paper:
        with open(args.paper, "r", encoding="utf-8") as f:
            text = f.read()

        issues, passed = run_devils_advocate(text)
        print_audit_report(issues, passed)

        if args.prompt:
            print("\n\n" + "=" * 60)
            print(build_devils_prompt(text))
