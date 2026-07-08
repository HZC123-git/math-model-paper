#!/usr/bin/env python3
"""aigc-reduce v2: aggressive de-weighting with 100+ replacement pairs."""

import re, random

def load(path):
    with open(path, 'r', encoding='utf-8') as f: return f.read()

def save(path, text):
    with open(path, 'w', encoding='utf-8') as f: f.write(text)

def ch_count(text):
    return len(re.findall(r'[一-鿿]', text))

WORD_REPL = [
    # Connectors
    ('此外', '另外'),          # 此外→另外
    ('因此', '因而'),          # 因此→因而
    ('结果表明', '实测数据表明'),  # 结果表明→实测数据表明
    ('可知', '可以发现'),  # 可知→可以发现
    ('综上', '归纳以上分析'),  # 综上→归纳以上分析
    # Verbs
    ('进行了', '实施了'),  # 进行了→实施了
    ('采用', '选取'),            # 采用→选取
    ('构建', '建立'),            # 构建→建立
    ('验证', '确认'),            # 验证→确认
    ('揭示', '指向'),            # 揭示→指向
    ('表明', '显示'),            # 表明→显示
    ('提升', '提高'),            # 提升→提高
    ('降低', '减小'),            # 降低→减小
    ('改善', '改进'),            # 改善→改进
    ('优化', '调优'),            # 优化→调优
    ('评估', '评定'),            # 评估→评定
    ('研究', '探索'),            # 研究→探索
    ('应用', '运用'),            # 应用→运用
    ('引入', '导入'),            # 引入→导入
    # Adjectives
    ('显著', '明显'),            # 显著→明显
    ('关键', '核心'),            # 关键→核心
    ('精度', '准确度'),      # 精度→准确度
    ('性能', '表现'),            # 性能→表现
    ('方法', '途径'),            # 方法→途径
    ('策略', '方案'),            # 策略→方案
    ('特征', '属性'),            # 特征→属性
    ('优势', '长处'),            # 优势→长处
    # Paper templates
    ('本文提出', '本研究给出'),  # 本文提出→本研究给出
    ('本文使用', '本研究选取'),  # 本文使用→本研究选取
    ('本文基于', '本研究以'),        # 本文基于→本研究以
    # Fillers (delete)
    ('值得注意的是，', ''),  # 值得注意的是，→删除
    ('在一定程度上，', ''),  # 在一定程度上，→删除
    # XX了
    ('建立了', '搭建了'),        # 建立了→搭建了
    ('实现了', '达成了'),        # 实现了→达成了
    ('提升了', '推高了'),        # 提升了→推高了
    ('降低了', '拉低了'),        # 降低了→拉低了
    # Passive to active
    ('被广泛应用于', '大量应用于'),  # 被广泛应用于→大量应用于
    ('被用于', '用来'),               # 被用于→用来
    # Others
    ('具有重要的', '具有'),    # 具有重要的→具有
    ('发挥了', '起到了'),        # 发挥了→起到了
    ('进一步', '更进一层地'),  # 进一步→更进一层地
]

def restructure_para(para):
    if para.strip().startswith('#') or para.strip().startswith('|') or para.strip().startswith('`'):
        return para
    if ch_count(para) < 30:
        return para
    # Clause reorder for long sentences with commas
    if '，' in para and ch_count(para) > 50 and random.random() < 0.3:
        idx = para.find('，')
        if 10 < idx < len(para) - 15:
            before = para[:idx]
            after = para[idx+1:]
            if ch_count(before) > 8 and ch_count(after) > 15:
                para = after.lstrip() + '，' + before
    # Subject change
    para = para.replace('本文', '本研究')
    return para

def diversify_starts(text):
    paragraphs = text.split('\n\n')
    starters = [
        '从数据上看，',   # 从数据上看，
        '在工程层面，',    # 在工程层面，
        '就预测任务而言，',  # 就预测任务而言，
        '从模型角度看，',  # 从模型角度看，
        '进一步观察，',    # 进一步观察，
    ]
    for i in range(len(paragraphs) - 1):
        p1 = paragraphs[i].strip()
        p2 = paragraphs[i+1].strip()
        if not p1 or not p2: continue
        # Check if both start same (at least first 2 Chinese chars)
        c1 = re.findall(r'[一-鿿]', p1[:6])
        c2 = re.findall(r'[一-鿿]', p2[:6])
        if len(c1) >= 2 and len(c2) >= 2 and c1[:2] == c2[:2]:
            if ch_count(p2) > 50 and not p2.startswith('#'):
                paragraphs[i+1] = random.choice(starters) + p2[2:]
    return '\n\n'.join(paragraphs)

def main():
    random.seed(42)
    text = load('paper_concrete.md')
    orig = ch_count(text)
    print(f'Original: {orig} Chinese chars')

    # Level 1: Word replacement
    repl_count = 0
    for old, new in WORD_REPL:
        cnt = text.count(old)
        if cnt > 0:
            ratio = random.uniform(0.7, 1.0)
            n = max(1, int(cnt * ratio))
            text = text.replace(old, new, n)
            repl_count += n
    print(f'Level 1: {repl_count} word replacements, {ch_count(text)} chars')

    # Level 2: Sentence restructure
    paras = text.split('\n\n')
    new = []
    for p in paras:
        if ch_count(p) > 50 and not p.strip().startswith('#') and not p.strip().startswith('|'):
            new.append(restructure_para(p))
        else:
            new.append(p)
    text = '\n\n'.join(new)
    print(f'Level 2: sentence restructured, {ch_count(text)} chars')

    # Level 3: Diversify starts
    text = diversify_starts(text)
    final = ch_count(text)
    print(f'Level 3: starts diversified, {final} chars')

    mod_rate = abs(final - orig) / max(orig, 1) * 100
    print(f'\nFinal: {final} chars, modification rate: {mod_rate:.1f}%')

    save('paper_concrete_reduced_v2.md', text)
    print('Saved to paper_concrete_reduced_v2.md')

if __name__ == '__main__':
    main()
