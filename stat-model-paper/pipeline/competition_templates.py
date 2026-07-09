#!/usr/bin/env python3
"""
竞赛模板适配器
根据竞赛类型返回对应的论文结构、写作风格指令和必含元素。
"""
import json

TEMPLATES = {
    # ==================== 国际竞赛 ====================
    "美赛": {
        "name": "MCM/ICM (Mathematical/Interdisciplinary Contest in Modeling)",
        "aliases": ["MCM", "ICM", "美赛", "美国大学生数学建模竞赛"],
        "language": "en",
        "sections": [
            "Summary",
            "Table of Contents",
            "1. Introduction (Background + Literature Review + Our Work)",
            "2. Assumptions and Justifications",
            "3. Notations",
            "4. Model 1: [Name] (Model Setup + Solution + Validation)",
            "5. Model 2: [Name] (Model Setup + Solution + Validation)",
            "6. Model 3: [Name] (Model Setup + Solution + Validation)",
            "7. Sensitivity Analysis",
            "8. Model Evaluation (Strengths + Weaknesses)",
            "9. Conclusions",
            "10. Letter to Director (if applicable)",
            "References",
            "Appendices (Code + Extra Figures)",
        ],
        "must_have": [
            "Letter to Director/Manager",
            "Sensitivity Analysis section",
            "Strengths and Weaknesses explicitly labeled",
            "Summary Sheet (separate page, 1 page max)",
        ],
        "style_notes": [
            "12pt Times New Roman, double-spaced",
            "Active voice preferred: 'We developed...' not 'A model was developed...'",
            "Summary page must fit on one page",
            "Executive summary style: problem → approach → results → implications",
            "Direct, concise. No filler sentences.",
        ],
        "forbidden_phrases": [
            "With the development of...",
            "In modern society...",
            "It is worth noting that...",
            "To sum up...",
            "Has important theoretical and practical significance...",
        ],
        "section_prompts": {
            "Summary": "Write a one-page executive summary. State the problem, your approach (model names), key numerical results, and practical recommendations. Do NOT use filler phrases. Every sentence must carry information. Max 400 words.",
            "Introduction": "Start with the specific real-world problem. Quote the problem statement directly. Briefly review 3-4 most relevant prior approaches and state what's different about your approach. End with a bullet list of your team's specific contributions.",
            "Sensitivity Analysis": "Vary key parameters by +/-20% and show how model output changes. Include at least one sensitivity table and one sensitivity plot. Comment on which parameters the model is most sensitive to.",
        },
    },

    "国赛": {
        "name": "全国大学生数学建模竞赛 (CUMCM)",
        "language": "zh",
        "sections": [
            "摘要",
            "一、问题重述 (1.1 问题背景 + 1.2 本文拟解决的问题)",
            "二、模型假设与符号说明",
            "三、问题一的模型的建立与求解",
            "四、问题二的模型的建立与求解",
            "五、问题三的模型的建立与求解",
            "六、问题四的模型的建立与求解",
            "七、模型评价与推广",
            "参考文献",
            "附录 (核心代码 + 补充图表)",
        ],
        "must_have": [
            "逐题求解结构（每个问题独立成章）",
            "每个问题章节包含：问题分析 + 模型建立 + 模型求解 + 结果分析 + 模型小结",
            "符号说明表（所有符号集中说明）",
            "技术路线图（流程图）",
            "模型假设逐条列出并编号",
            "附录含Python/MATLAB核心代码",
        ],
        "style_notes": [
            "宋体正文，黑体标题，小四号字(12pt)",
            "1.5倍行距",
            "每个结论后面跟表号或图号作为证据",
            "数值精确到小数点后3-4位",
            "公式居中，编号右对齐 (1)(2)(3)...",
            "三线表，表头加粗",
            "不写'随着...的发展''综上所述'等套话",
        ],
        "forbidden_phrases": [
            "随着...的发展/到来",
            "综上所述",
            "值得注意的是",
            "具有重要的理论意义和现实意义",
            "在一定程度上",
            "首先...其次...再次...最后...",
            "一方面...另一方面...",
            "未来将进一步研究...",
        ],
    },

    "研究生数学建模": {
        "name": "中国研究生数学建模竞赛 (华为杯)",
        "language": "zh",
        "sections": [
            "摘要",
            "目录",
            "一、问题重述 (1.1 问题背景 + 1.2 本文拟解决的问题)",
            "二、模型假设与符号说明 (2.1 基本假设 + 2.2 符号说明)",
            "三、技术路线图",
            "四、问题一的模型的建立与求解 (4.1 问题分析 + 4.2 模型建立与求解 + 4.3 本章小结)",
            "五、问题二的模型的建立与求解",
            "六、问题三的模型的建立与求解",
            "七、问题四的模型的建立与求解",
            "八、问题五的模型的建立与求解",
            "九、模型评价与推广 (9.1 优点 + 9.2 缺点 + 9.3 改进与推广)",
            "参考文献",
            "附录：Python代码",
        ],
        "must_have": [
            "封面（学校 + 参赛队号 + 队员姓名）",
            "摘要逐问题列出方法+结果+数字",
            "目录",
            "每个问题3个子章节（问题分析→模型建立→模型小结）",
            "符号说明表",
            "至少5个模型对比表",
            "附录含完整代码",
        ],
        "style_notes": [
            "使用'本文'而非'我们'",
            "每个问题开头用'针对问题X中...的问题'",
            "公式必须编号，表格必须有三线表格式",
            "模型对比必须有定量指标（R²/RMSE/准确率等）",
            "优缺点每条约30字，说具体不说空话",
        ],
        "forbidden_phrases": [
            "值得注意的是",
            "综上所述",
            "具有重要意义",
            "在一定程度上",
        ],
    },

    "统计建模": {
        "name": "全国大学生统计建模大赛",
        "aliases": ["统计建模", "统计建模大赛"],
        "language": "zh",
        "sections": [
            "摘要",
            "一、引言 (研究背景 + 文献综述 + 研究问题与创新点)",
            "二、数据说明与预处理 (数据来源 + 变量说明 + 预处理步骤)",
            "三、方法论 (3.1 研究框架 + 3.2 模型设定 + 3.3 估计方法 + 3.4 诊断检验)",
            "四、实证分析 (4.1 描述性统计 + 4.2 模型估计结果 + 4.3 稳健性检验 + 4.4 进一步讨论)",
            "五、结论与政策建议",
            "参考文献",
            "附录（代码 + 补充结果）",
        ],
        "must_have": [
            "文献综述（15-25篇，中英文混合）",
            "内生性讨论（工具变量/固定效应/匹配方法）",
            "稳健性检验（替换变量/替换样本/替换方法）",
            "异方差和自相关检验",
            "VIF多重共线性诊断",
            "政策建议章节",
        ],
        "style_notes": [
            "更偏向经济学/社会学论文写法",
            "必须引用经典计量文献（Wooldridge, Angrist等）",
            "因果推断优先于预测精度",
            "p值和标准误必须报告",
            "脚注可用于补充说明",
        ],
        "forbidden_phrases": [
            "随着...的发展",
            "具有重要的理论意义",
        ],
    },

    # ==================== 企业冠名竞赛 ====================
    "MathorCup": {
        "name": "MathorCup高校数学建模挑战赛",
        "aliases": ["mathorcup", "MathorCup", "mathorcup高校数学建模挑战赛"],
        "language": "zh",
        "sections": [
            "摘要",
            "一、问题重述与分析",
            "二、模型假设与符号说明",
            "三、模型的建立与求解（逐题）",
            "四、灵敏度分析",
            "五、模型评价与改进",
            "六、参考文献",
            "附录",
        ],
        "must_have": [
            "企业应用背景分析（该竞赛题目来自企业实际问题）",
            "灵敏度分析章节",
            "模型实用性讨论（能否落地）",
            "成本/效率分析（如果有）",
        ],
        "style_notes": [
            "比国赛更强调实际应用价值",
            "鼓励讨论模型的商业落地可行性",
            "不追求复杂公式堆砌，实用优先",
            "摘要需突出解决了什么实际问题",
        ],
        "forbidden_phrases": [
            "随着...的发展",
            "综上所述",
            "具有重要意义",
        ],
    },
    "APMCM": {
        "name": "APMCM 亚太地区大学生数学建模竞赛",
        "aliases": ["apmcm", "APMCM", "亚太赛", "亚太数学建模"],
        "language": "en",
        "sections": [
            "Summary",
            "Table of Contents",
            "1. Introduction (Background + Problem Restatement + Our Work)",
            "2. Assumptions and Notations",
            "3. Model Development (3.1-3.N per question)",
            "4. Sensitivity Analysis",
            "5. Model Evaluation (Strengths + Weaknesses)",
            "6. Conclusions",
            "References",
            "Appendices",
        ],
        "must_have": [
            "Summary Sheet (separate page)",
            "Sensitivity Analysis",
            "至少3个模型（鼓励多角度建模）",
            "比较不同方法的优劣",
        ],
        "style_notes": [
            "英文写作，类似美赛但篇幅可稍短",
            "鼓励图表和可视化",
            "简洁直接，不需要过多文献综述",
        ],
        "forbidden_phrases": [
            "With the development of...",
            "In modern society...",
            "It is worth noting that...",
        ],
    },

    # ==================== 行业专题竞赛 ====================
    "电工杯": {
        "name": "全国大学生电工数学建模竞赛",
        "aliases": ["电工杯", "电工数学建模"],
        "language": "zh",
        "sections": [
            "摘要",
            "一、问题重述",
            "二、模型假设",
            "三、符号说明",
            "四、问题一的模型建立与求解",
            "五、问题二的模型建立与求解",
            "六、问题三的模型建立与求解",
            "七、模型评价与推广",
            "参考文献",
            "附录",
        ],
        "must_have": [
            "电气工程背景分析",
            "物理模型或电路模型的推导过程",
            "参数的实际物理意义说明",
            "仿真验证（MATLAB/Simulink）",
        ],
        "style_notes": [
            "偏工程应用，公式推导要完整",
            "物理意义解释比数学证明更重要",
            "鼓励使用电路图、框图等工程图表",
            "结果必须与实际工程数据对比验证",
        ],
        "forbidden_phrases": [
            "随着...的发展",
            "综上所述",
            "值得注意的是",
        ],
    },
    "深圳杯": {
        "name": "深圳杯数学建模挑战赛",
        "aliases": ["深圳杯", "深圳杯数学建模"],
        "language": "zh",
        "sections": [
            "摘要",
            "一、问题背景与分析",
            "二、数据探索与预处理",
            "三、模型建立与求解",
            "四、结果分析与讨论",
            "五、结论与政策建议",
            "参考文献",
            "附录",
        ],
        "must_have": [
            "数据驱动的深度分析（深圳杯数据量通常较大）",
            "政策建议或管理建议（面向实际问题）",
            "模型的可操作性和落地性讨论",
            "数据可视化（地图/热力图等）",
        ],
        "style_notes": [
            "开放题，不限定方法，鼓励创新",
            "数据量通常较大，强调数据驱动的分析过程",
            "可写成报告/白皮书风格",
            "强调结论的实际指导意义",
        ],
        "forbidden_phrases": [
            "随着大数据时代的发展",
            "综上所述",
            "具有重要意义",
        ],
    },

    # ==================== 区域/省级竞赛 ====================
    "华中杯": {
        "name": "华中杯大学生数学建模竞赛",
        "aliases": ["华中杯", "华中赛"],
        "language": "zh",
        "sections": [
            "摘要",
            "一、问题重述",
            "二、模型假设与符号说明",
            "三、模型的建立与求解（逐题）",
            "四、模型评价",
            "参考文献",
            "附录",
        ],
        "must_have": [
            "逐题求解结构",
            "模型对比分析",
            "结果验证",
        ],
        "style_notes": [
            "格式参考国赛，要求略低",
            "鼓励图表可视化",
            "代码附录非必需但加分",
        ],
        "forbidden_phrases": [
            "随着...的发展",
            "综上所述",
        ],
    },
    "东三省": {
        "name": "东三省数学建模联赛",
        "aliases": ["东三省", "东三省数学建模"],
        "language": "zh",
        "sections": [
            "摘要",
            "一、问题重述",
            "二、模型假设",
            "三、符号说明",
            "四、问题一的求解",
            "五、问题二的求解",
            "六、问题三的求解",
            "七、模型评价与推广",
            "参考文献",
        ],
        "must_have": [
            "逐题求解结构",
            "每个问题至少一种方法",
            "结果分析",
        ],
        "style_notes": [
            "格式参考国赛",
            "可适当简化格式要求",
        ],
        "forbidden_phrases": [
            "随着...的发展",
        ],
    },

    # ==================== 特色竞赛 ====================
    "数维杯": {
        "name": "数维杯国际大学生数学建模挑战赛",
        "aliases": ["数维杯", "数维杯国际赛"],
        "language": "en",
        "sections": [
            "Summary",
            "1. Introduction",
            "2. Assumptions and Notations",
            "3. Model Establishment and Solution",
            "4. Model Evaluation",
            "5. Conclusions",
            "References",
            "Appendices",
        ],
        "must_have": [
            "英文写作",
            "Summary Sheet",
            "至少2个不同角度的模型",
            "模型对比",
        ],
        "style_notes": [
            "英文，类似简化版美赛",
            "鼓励使用多种方法对比",
            "图表要求较高（国际赛水准）",
        ],
        "forbidden_phrases": [
            "With the development of...",
        ],
    },
    "五一杯": {
        "name": "五一杯数学建模竞赛",
        "aliases": ["五一杯", "五一数学建模"],
        "language": "zh",
        "sections": [
            "摘要",
            "一、问题重述",
            "二、模型假设与符号",
            "三、模型的建立与求解",
            "四、模型评价",
            "参考文献",
            "附录",
        ],
        "must_have": [
            "逐题求解",
            "代码附录",
        ],
        "style_notes": [
            "格式参考国赛",
            "时间较短(3天)，允许简便解法",
            "强调思路清晰而非复杂度",
        ],
        "forbidden_phrases": [
            "随着...的发展",
        ],
    },
    "认证杯": {
        "name": "认证杯数学建模国际赛",
        "aliases": ["认证杯", "认证杯数学建模"],
        "language": "zh",
        "sections": [
            "摘要",
            "一、问题重述",
            "二、模型假设与符号说明",
            "三、模型建立与求解（逐题）",
            "四、灵敏度分析",
            "五、模型评价与改进",
            "参考文献",
            "附录",
        ],
        "must_have": [
            "逐题求解结构",
            "灵敏度分析",
            "中英文标题和摘要（部分阶段要求）",
        ],
        "style_notes": [
            "第一阶段：中文；第二阶段：英文摘要",
            "鼓励模型创新",
        ],
        "forbidden_phrases": [
            "随着...的发展",
        ],
    },
    "中青杯": {
        "name": "中青杯全国大学生数学建模竞赛",
        "aliases": ["中青杯", "中青杯数学建模"],
        "language": "zh",
        "sections": [
            "摘要",
            "一、问题重述",
            "二、模型假设",
            "三、符号说明",
            "四、模型的建立与求解",
            "五、模型评价与推广",
            "参考文献",
        ],
        "must_have": [
            "逐题求解",
            "模型对比",
        ],
        "style_notes": [
            "格式参考国赛",
            "鼓励创新方法",
        ],
        "forbidden_phrases": [
            "随着...的发展",
        ],
    },
}


def get_template(competition_type):
    """根据竞赛类型获取模板（支持名称/别名模糊匹配）"""
    ct_lower = competition_type.lower().replace(" ", "").replace("_", "").replace("-", "")

    for key, t in TEMPLATES.items():
        # 精确匹配key
        if ct_lower == key.lower().replace(" ", ""):
            return t
        # 别名匹配
        aliases = t.get("aliases", [])
        for alias in aliases:
            alias_clean = alias.lower().replace(" ", "").replace("_", "").replace("-", "")
            if ct_lower == alias_clean or ct_lower in alias_clean or alias_clean in ct_lower:
                return t
        # 名称包含匹配
        name_clean = t["name"].lower().replace(" ", "").replace("_", "").replace("-", "")
        if ct_lower in name_clean or name_clean in ct_lower:
            return t

    # 默认返回国赛模板
    return TEMPLATES["国赛"]


def list_all_competitions():
    """列出所有支持的竞赛模板"""
    result = []
    for key, t in TEMPLATES.items():
        result.append({
            "key": key,
            "name": t["name"],
            "language": t["language"],
            "aliases": t.get("aliases", []),
            "n_sections": len(t["sections"]),
        })
    return result


COMPETITION_LIST = list_all_competitions()


def build_system_prompt(competition_type, problem_title, n_questions=3):
    """根据竞赛类型构建完整的 system prompt"""
    t = get_template(competition_type)

    sections_str = "\n".join(f"    {s}" for s in t["sections"])
    must_str = "\n".join(f"  - {m}" for m in t["must_have"])
    style_str = "\n".join(f"  - {s}" for s in t["style_notes"])
    forbidden_str = "\n".join(f"  - {f}" for f in t["forbidden_phrases"])

    prompt = f"""你正在撰写一篇{t['name']}的参赛论文。

论文题目：{problem_title}
论文语言：{t['language']}
问题数量：{n_questions} 个

## 论文结构（严格遵循）

{sections_str}

## 必须包含的元素
{must_str}

## 写作风格
{style_str}

## 绝对禁止的套话
{forbidden_str}

## 核心原则
- 每个结论后面跟具体的数值证据
- 不要写"随着...的发展""综上所述""值得注意的是"
- 直接说问题、说方法、说结果、说数字
- 语言密度：每200字至少一个数值引用
- 不做空洞总结，不做无数据支撑的推论
"""
    return prompt


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--competition', default='国赛',
                        help='竞赛类型（支持名称或别名模糊匹配）')
    parser.add_argument('--title', default='数据分析与建模', help='论文题目')
    parser.add_argument('--questions', type=int, default=3, help='问题数量')
    parser.add_argument('--list', action='store_true', help='列出所有支持的竞赛')
    args = parser.parse_args()

    if args.list:
        print(f"\n{'='*60}")
        print(f"  支持的竞赛模板 ({len(COMPETITION_LIST)} 种)")
        print(f"{'='*60}\n")
        for c in COMPETITION_LIST:
            aliases = ', '.join(c['aliases'][:4]) if c['aliases'] else '-'
            print(f"  {c['key']:<10s} | {c['language']:2s} | {c['n_sections']}节 | {c['name']}")
            print(f"  {'':10s} | 别名: {aliases}")
            print()
        exit(0)

    prompt = build_system_prompt(args.competition, args.title, args.questions)
    print(prompt)

    # 同时输出JSON格式的模板数据
    t = get_template(args.competition)
    print('\n---TEMPLATE JSON---')
    print(json.dumps(t, ensure_ascii=False, indent=2))
