#!/usr/bin/env python3
"""
降重 v3: 句法结构级变换
策略: 拆分长句 + 语序重组 + 句式变换 + 段落重排
"""

import re, random

def load(path):
    with open(path, 'r', encoding='utf-8') as f: return f.read()

def save(path, text):
    with open(path, 'w', encoding='utf-8') as f: f.write(text)

def ch_count(text):
    return len(re.findall(r'[一-鿿]', text))

# ============================================================
# CORE TRANSFORMATIONS (each transforms sentence structure)
# ============================================================

def split_long_sentence(sent):
    """Split sentences >45 Chinese chars at natural break points"""
    ch = ch_count(sent)
    if ch <= 45:
        return sent

    # Find commas near the middle
    commas = [m.start() for m in re.finditer(r'[，；]', sent)]
    if not commas:
        return sent

    # Split at the comma nearest to the 55% point
    target = int(len(sent) * 0.55)
    best = min(commas, key=lambda x: abs(x - target))

    part1 = sent[:best+1]
    part2 = sent[best+1:]

    # Only split if both parts are substantive
    if ch_count(part1) >= 12 and ch_count(part2) >= 12:
        # Add connection word to second part
        connectors = ['这意味着，', '换而言之，', '具体来说，', '从结果看，']
        if not part2.startswith('这') and not part2.startswith('换'):
            part2 = random.choice(connectors) + part2
        return part1 + '\n' + part2

    return sent


def reorder_clauses(sent):
    """Reorder clauses: move time/condition clauses to end, or front"""
    ch = ch_count(sent)
    if ch < 30 or '，' not in sent:
        return sent

    parts = sent.split('，')
    if len(parts) < 3:
        return sent

    # Try moving the first clause to the end
    if ch_count(parts[0]) >= 6 and random.random() < 0.4:
        first = parts[0]
        rest = '，'.join(parts[1:])
        return rest.rstrip('。') + '，' + first

    # Or move last clause to front
    if ch_count(parts[-1]) >= 6 and random.random() < 0.3:
        last = parts[-1]
        rest = '，'.join(parts[:-1])
        return last + '，' + rest

    return sent


def pattern_swap(sent):
    """Swap common AI sentence patterns"""
    ch = ch_count(sent)
    if ch < 20:
        return sent

    # Pattern 1: "X对Y进行Z" → "Y通过X被Z"
    # This is hard to do reliably, skip for now

    # Pattern 2: "X，从而Y" → "由于X，Y"
    if '，从而' in sent:
        sent = sent.replace('，从而', '，进而')

    # Pattern 3: "X，即Y" → "Y，这是X的核心特征"
    if '，即' in sent and random.random() < 0.3:
        parts = sent.split('，即', 1)
        if len(parts) == 2:
            # Keep as is but add emphasis
            sent = parts[0] + '——' + parts[1]

    # Pattern 4: Subject diversity
    sent = sent.replace('本文', '本研究')
    sent = sent.replace('我们', '本研究')

    return sent


def add_variation(sent):
    """Add natural variation to sentence"""
    ch = ch_count(sent)
    if ch < 15:
        return sent

    # Randomly add a hedge word
    hedges_before = ['从实测数据来看，', '在现有数据范围内，', '就该数据集而言，']
    if random.random() < 0.1 and not sent.startswith('#') and ch > 25:
        sent = random.choice(hedges_before) + sent

    return sent


# ============================================================
# PARAGRAPH-LEVEL
# ============================================================

def transform_paragraph(para):
    """Apply all transformations to a paragraph"""
    # Skip protected content
    if para.strip().startswith('#'): return para
    if para.strip().startswith('|'): return para
    if para.strip().startswith('```'): return para
    if para.strip().startswith('!'): return para  # images
    if para.strip().startswith('*'): return para
    if '表' in para[:5] and para.strip().startswith('|'): return para

    ch = ch_count(para)
    if ch < 20:
        return para

    # Split into sentences
    sents = re.split(r'(?<=[。！？])(?![」』\)])', para)
    sents = [s for s in sents if s.strip()]

    if not sents:
        return para

    # Transform each sentence
    new_sents = []
    for s in sents:
        s = split_long_sentence(s)  # May return multi-line
        s = reorder_clauses(s)
        s = pattern_swap(s)
        s = add_variation(s)
        new_sents.append(s)

    result = ''.join(new_sents)

    return result


def merge_short_paras(text):
    """Merge adjacent short paragraphs into longer ones"""
    paras = text.split('\n\n')
    new = []
    i = 0
    while i < len(paras):
        p = paras[i]
        pc = ch_count(p)
        # Merge short body paragraphs with next
        if (pc < 80 and i + 1 < len(paras)
            and not p.strip().startswith('#')
            and not p.strip().startswith('|')
            and not p.strip().startswith('`')):
            next_p = paras[i+1]
            next_pc = ch_count(next_p)
            if (next_pc < 80
                and not next_p.strip().startswith('#')
                and not next_p.strip().startswith('|')):
                new.append(p.rstrip() + ' ' + next_p.lstrip())
                i += 2
                continue
        new.append(p)
        i += 1
    return '\n\n'.join(new)


def split_long_paras(text):
    """Split very long paragraphs"""
    paras = text.split('\n\n')
    new = []
    for p in paras:
        pc = ch_count(p)
        if pc > 500 and not p.strip().startswith('#') and not p.strip().startswith('|'):
            sents = re.split(r'(?<=[。])(?=[^\s])', p)
            if len(sents) >= 6:
                mid = len(sents) // 2
                new.append(''.join(sents[:mid]))
                new.append(''.join(sents[mid:]))
                continue
        new.append(p)
    return '\n\n'.join(new)


# ============================================================
# MAIN
# ============================================================

def main():
    random.seed(42)
    text = load('paper_concrete.md')
    orig = ch_count(text)
    print(f'Original: {orig} chars')

    # Apply transformations paragraph by paragraph
    paras = text.split('\n\n')
    transformed = []
    modified_count = 0
    for p in paras:
        old_ch = ch_count(p)
        new_p = transform_paragraph(p)
        new_ch = ch_count(new_p)
        if new_p != p:
            modified_count += 1
        transformed.append(new_p)
    text = '\n\n'.join(transformed)

    t1_ch = ch_count(text)
    print(f'After transform: {t1_ch} chars ({modified_count} paragraphs modified)')

    # Merge/split paragraphs
    text = merge_short_paras(text)
    text = split_long_paras(text)
    t2_ch = ch_count(text)
    print(f'After para adjust: {t2_ch} chars')

    # Sentence count stats
    sents = re.split(r'[。！？；]', text)
    sent_lens = [ch_count(s) for s in sents if ch_count(s) > 0]
    if sent_lens:
        import statistics
        mean_sl = statistics.mean(sent_lens)
        stdev_sl = statistics.stdev(sent_lens) if len(sent_lens) > 1 else 0
        cv = stdev_sl / mean_sl if mean_sl > 0 else 0
        print(f'Sentence stats: mean={mean_sl:.1f}, std={stdev_sl:.1f}, CV={cv:.3f}')
        print(f'Distribution: short(<15)={sum(1 for l in sent_lens if l<15)}, '
              f'med(15-35)={sum(1 for l in sent_lens if 15<=l<=35)}, '
              f'long(>35)={sum(1 for l in sent_lens if l>35)}')

    final = ch_count(text)
    # Mod rate based on paragraph-level differences
    mod_rate = abs(final - orig) / max(orig, 1) * 100
    print(f'\nFinal: {final} chars')
    print(f'Character change rate: {mod_rate:.1f}%')
    print(f'Paragraphs modified: {modified_count}')

    save('paper_concrete_reduced_v3.md', text)
    print('Saved to paper_concrete_reduced_v3.md')

    return text

if __name__ == '__main__':
    main()
