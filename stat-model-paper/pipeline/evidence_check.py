#!/usr/bin/env python3
"""
证据校验模块
对比论文中所有数值声明与 JSON 分析报告，标记不一致项。
"""
import json, re, sys
from pathlib import Path

def extract_numbers_from_text(text):
    """从论文文本中提取所有数值声明及其上下文"""
    patterns = [
        # R²=数字
        (r'[Rr]2\s*[=＝]\s*(\d+\.?\d*)', 'R2'),
        # R²均值
        (r'[Rr]2\s*均值\s*[=＝]?\s*(\d+\.?\d*)', 'R2_mean'),
        # RMSE=数字 万
        (r'RMSE\s*[=＝]\s*(\d+\.?\d*)\s*万', 'RMSE'),
        # MAE=数字 万
        (r'MAE\s*[=＝]\s*(\d+\.?\d*)\s*万', 'MAE'),
        # 准确率=数字%
        (r'准确率\s*[=＝均达]*\s*(\d+\.?\d*)\s*%', 'accuracy'),
        # p=数字
        (r'[Pp]\s*[=＝]\s*(\d+\.?\d*)', 'p_value'),
        # r=数字 (相关系数)
        (r'[Rr]\s*[=＝]\s*(-?\d+\.?\d*)', 'correlation'),
        # 重要性=数字
        (r'重要性\s*[=＝得分]\s*(\d+\.?\d*)', 'importance'),
        # 标准差=数字
        (r'[Ss][Tt][Dd]\s*[=＝]?\s*(\d+\.?\d*)', 'std'),
        # CV=数字%
        (r'[Cc][Vv]\s*[=＝]?\s*(\d+\.?\d*)\s*%', 'cv'),
        # 均值=数字
        (r'均值\s*[=＝]?\s*(\d+\.?\d*)', 'mean'),
        # 样本量
        (r'(\d+)\s*条\s*(数据|记录|样本)', 'sample_count'),
        # 相对误差=数字%
        (r'相对误差\s*[=＝约]*\s*(\d+\.?\d*)\s*%', 'rel_error'),
    ]

    findings = []
    for pattern, label in patterns:
        for m in re.finditer(pattern, text):
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 30)
            context = text[start:end].replace('\n', ' ')
            findings.append({
                'type': label,
                'value': float(m.group(1)) if '.' in m.group(1) or m.group(1).isdigit() else m.group(1),
                'context': context.strip(),
                'position': m.start(),
            })
    return findings


def verify_against_json(findings, json_report):
    """对比论文数值与JSON数据源"""
    issues = []

    # 从JSON中提取参考值
    modeling = json_report.get('modeling', {})
    desc = json_report.get('descriptive_stats', {})
    eda = json_report.get('data_overview', {})
    normality = json_report.get('normality_tests', {})
    corr = json_report.get('correlation', {})
    meta = json_report.get('meta', {})

    # 构建参考值字典
    ref = {}

    # 模型指标
    models = modeling.get('models', {})
    best = modeling.get('best_model', '')
    if best and best in models:
        m = models[best]
        ref['R2'] = m.get('R2')
        ref['RMSE'] = m.get('RMSE')
        ref['MAE'] = m.get('MAE')

    # CV指标
    if best and best in models and 'CV_R2_mean' in models[best]:
        ref['R2_mean'] = models[best]['CV_R2_mean']

    # 样本量
    sample = modeling.get('sample_size', {})
    if sample:
        ref['sample_count'] = sample.get('train', 0) + sample.get('test', 0)

    # 特征重要性
    feats = modeling.get('feature_importance', [])
    for f in feats:
        ref[f"importance_{f['feature']}"] = f['importance']

    # 描述性统计
    target = meta.get('target_variable', '')
    if target and target in desc:
        ref['mean'] = desc[target].get('mean')
        ref['std'] = desc[target].get('std')

    # 正态性检验
    for col, vals in normality.items():
        ref[f"p_value_{col}"] = vals.get('p_value')

    # 相关性
    strong = corr.get('strong_pairs', [])
    for pair in strong:
        ref[f"correlation_{pair['var1']}_{pair['var2']}"] = pair['correlation']

    # 逐项检查
    tolerance = {
        'R2': 0.001, 'R2_mean': 0.001, 'RMSE': 0.5, 'MAE': 0.5,
        'accuracy': 0.5, 'p_value': 0.01, 'correlation': 0.01,
        'importance': 0.001, 'std': 0.5, 'cv': 0.5,
        'mean': 1.0, 'sample_count': 5, 'rel_error': 0.5,
    }

    for f in findings:
        ftype = f['type']
        fval = f['value']

        if ftype in ref and ref[ftype] is not None:
            ref_val = ref[ftype]
            tol = tolerance.get(ftype, 0.01)
            if isinstance(fval, (int, float)) and isinstance(ref_val, (int, float)):
                diff = abs(fval - ref_val)
                if diff > tol:
                    issues.append({
                        'severity': 'ERROR',
                        'type': ftype,
                        'paper_value': fval,
                        'source_value': ref_val,
                        'difference': round(diff, 6),
                        'context': f['context'],
                    })
                else:
                    issues.append({
                        'severity': 'OK',
                        'type': ftype,
                        'paper_value': fval,
                        'source_value': ref_val,
                        'difference': round(diff, 6),
                    })

    return issues


def run_check(paper_text_path, json_path):
    """运行完整证据校验"""
    # 读取论文
    with open(paper_text_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # 读取JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        report = json.load(f)

    findings = extract_numbers_from_text(text)
    issues = verify_against_json(findings, report)

    errors = [i for i in issues if i['severity'] == 'ERROR']
    oks = [i for i in issues if i['severity'] == 'OK']

    print(f"\n{'='*60}")
    print(f"  证据校验报告")
    print(f"{'='*60}")
    print(f"  论文路径: {paper_text_path}")
    print(f"  JSON路径: {json_path}")
    print(f"  提取数值声明: {len(findings)} 条")
    print(f"  通过校验: {len(oks)} 条")
    print(f"  数据不一致: {len(errors)} 条")
    print(f"{'='*60}")

    if errors:
        print(f"\n  ⚠️  以下数值与数据源不一致：\n")
        for e in errors:
            print(f"  [{e['type']}] 论文: {e['paper_value']}  |  数据源: {e['source_value']}  |  偏差: {e['difference']}")
            print(f"        上下文: ...{e['context']}...")
            print()
    else:
        print(f"\n  ✅ 所有数值声明与数据源一致。")

    return len(errors) == 0, issues


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法: python evidence_check.py <论文txt路径> <分析JSON路径>")
        sys.exit(1)

    passed, _ = run_check(sys.argv[1], sys.argv[2])
    sys.exit(0 if passed else 1)
