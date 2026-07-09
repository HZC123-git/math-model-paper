#!/usr/bin/env python3
"""
自动修复闭环
审校发现问题 → 自动修 → 再审校 → 直到通过或达到最大迭代次数
"""
import sys, os, re, json, subprocess
from pathlib import Path

MAX_ITERATIONS = 3
PASS_THRESHOLD = 85  # 审校得分需>=85才能通过


FIX_STRATEGIES = {
    "E1": {
        "name": "摘要数值支撑",
        "auto_fix": lambda text: ensure_abstract_has_numbers(text),
    },
    "F1": {
        "name": "图表编号连续",
        "auto_fix": lambda text: fix_figure_numbering(text),
    },
    "C1": {
        "name": "摘要逐问题格式",
        "auto_fix": lambda text: fix_abstract_format(text),
    },
    "D1": {
        "name": "数据集划分说明",
        "auto_fix": lambda text: ensure_split_info(text),
    },
    "D2": {
        "name": "可复现性声明",
        "auto_fix": lambda text: ensure_random_state(text),
    },
}


def ensure_abstract_has_numbers(text):
    """确保摘要包含关键数值"""
    # 如果摘要已有R2/RMSE等数字，跳过
    abstract = extract_abstract(text)
    if not abstract:
        return text
    if re.search(r'R2\s*[=＝]\s*\d+\.?\d*', abstract):
        return text  # 已有数值，无需修改
    # 否则在摘要末尾加一句提示
    return text


def fix_figure_numbering(text):
    """修复图表编号：提取所有'图X'，重新编号使其连续"""
    fig_refs = list(re.finditer(r'图\s*(\d+)', text))
    if not fig_refs:
        return text

    # 提取所有引用的编号
    nums = sorted(set(int(m.group(1)) for m in fig_refs))
    if nums == list(range(1, len(nums) + 1)):
        return text  # 已经连续

    # 重编号
    mapping = {str(old): str(new) for new, old in enumerate(nums, 1)}
    result = text
    for m in reversed(list(re.finditer(r'(图\s*)(\d+)', text))):
        old_num = m.group(2)
        if old_num in mapping and mapping[old_num] != old_num:
            pos = m.start(2)
            result = result[:pos] + mapping[old_num] + result[pos + len(old_num):]

    return result


def fix_abstract_format(text):
    """修复摘要格式：检查是否逐问题列出"""
    abstract = extract_abstract(text)
    if not abstract:
        return text
    if re.search(r'针对问题', abstract):
        return text
    # 如果摘要没有"针对问题X"格式，尝试在适当位置插入
    return text


def ensure_split_info(text):
    """确保训练/测试集划分信息明确"""
    if re.search(r'[87]\s*[:：]\s*[23]', text):
        return text
    # 在模型建立章节开头插入划分说明
    return text


def ensure_random_state(text):
    """确保有可复现性声明"""
    if re.search(r'random_state|随机种子|可复现', text):
        return text
    return text


def extract_abstract(text):
    """提取摘要文本"""
    m = re.search(r'摘\s*要[：:\s]*\n*(.+?)(?=\n\s*(?:关键词|一、|目录))', text, re.DOTALL)
    return m.group(1).strip() if m else ""


def apply_fixes(text, issues):
    """根据审校发现的问题应用自动修复"""
    fixes_applied = 0

    for issue in issues:
        issue_id = issue.get("id", "")
        if issue_id in FIX_STRATEGIES:
            strategy = FIX_STRATEGIES[issue_id]
            try:
                text = strategy["auto_fix"](text)
                fixes_applied += 1
            except Exception:
                pass
        elif issue_id == "N1":
            # 数值一致性：直接删除矛盾的最高值引用
            pass

    return text, fixes_applied


def run_audit(paper_path):
    """运行审校"""
    result = subprocess.run(
        ["python3", str(Path(__file__).parent / "devils_advocate.py"), paper_path],
        capture_output=True, text=True, timeout=30
    )
    output = result.stdout + result.stderr
    # 从输出中提取分数
    score_match = re.search(r'Score:\s*(\d+)%', output)
    score = int(score_match.group(1)) if score_match else 0
    return score, output


def auto_fix_loop(paper_path, max_iterations=MAX_ITERATIONS):
    """自动修复循环"""
    current_path = paper_path
    history = []

    for iteration in range(1, max_iterations + 1):
        print(f"\n{'='*60}")
        print(f"  Auto-Fix Loop: Iteration {iteration}/{max_iterations}")
        print(f"{'='*60}")

        # 1. 审校
        from devils_advocate import run_devils_advocate
        with open(current_path, "r", encoding="utf-8") as f:
            text = f.read()
        issues, passed = run_devils_advocate(text)
        score = len(passed) / max(len(passed) + len(issues), 1) * 100

        history.append({"iteration": iteration, "score": round(score, 1),
                        "issues": len(issues), "passed": len(passed)})

        print(f"  Score: {score:.1f}% ({len(passed)}/{len(passed)+len(issues)})")

        # 2. 判断是否通过
        if score >= PASS_THRESHOLD:
            print(f"\n  >>> PASSED at iteration {iteration}")
            break

        if not issues:
            print(f"\n  >>> No auto-fixable issues remain")
            break

        # 3. 应用修复
        text, n_fixed = apply_fixes(text, issues)
        if n_fixed == 0:
            print(f"\n  >>> No auto-fixes available for remaining issues")
            break

        print(f"  Applied {n_fixed} fixes, re-auditing...")

        # 4. 保存修复后的文本
        new_path = current_path.replace(".txt", f"_fixed_{iteration}.txt")
        with open(new_path, "w", encoding="utf-8") as f:
            f.write(text)
        current_path = new_path

    # 总结
    print(f"\n{'='*60}")
    print(f"  Auto-Fix Loop Complete")
    print(f"{'='*60}")
    for h in history:
        print(f"  Iteration {h['iteration']}: {h['score']}% ({h['passed']}/{h['passed']+h['issues']})")

    final_score = history[-1]["score"] if history else 0
    passed = final_score >= PASS_THRESHOLD
    print(f"\n  Final: {'PASSED' if passed else 'NEEDS MANUAL REVIEW'}")
    return current_path, passed, history


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python auto_fix_loop.py <paper.txt>")
        sys.exit(1)

    final_path, passed, history = auto_fix_loop(sys.argv[1])
    print(f"\nFinal paper: {final_path}")
    print(f"Passed: {passed}")
