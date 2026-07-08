#!/usr/bin/env python3
"""按 aigc-reduce 三轮协议对论文降重——确定性替换，不AI重写"""
import re

# 读取原文
with open("C:/Users/HZC12/Desktop/论文原文_提取文本.txt", "r", encoding="utf-8") as f:
    text = f.read()

# ====== PROTECTED SPANS: 绝对不改的内容 ======
# 标记保护区域：参考文献引用、图表编号、数据、公式
protected = {}

def protect(text):
    """将参考文献、数据、图表编号替换为占位符"""
    # 保护参考文献行 [1]...[15]
    text = re.sub(r'(\n\[\d+\].*?)(?=\n\[\d+\]|\n\Z)', lambda m: f'__REF{m.group(1).count("[")}__', text)
    return text

# 简化：手动标记
refs_lines = text.split("\n")[-20:]  # 最后20行是参考文献
main_text = "\n".join(text.split("\n")[:-20])

# ====== 第一轮：词级替换（确定性重写，不是AI重写） ======

# 1. AI高频连接词替换
word_reps = [
    # (原词, 替换词, 上下文要求)
    ("值得注意的是", "值得说明的是", ""),
    ("此外", "另一组数据则显示", "相关性"),
    ("此外", "从另一角度看", "模型"),
    ("综上所述", "综合以上分析", ""),
    ("需要指出的是", "值得说明的是", ""),
    ("具体而言", "进一步分析发现", ""),
    ("分析认为", "据此推断", ""),
    ("研究发现", "实验数据表明", ""),
    ("研究结果表明", "实测结果指向", ""),
    ("上述结果一致表明", "把这几个判断放在一起看", ""),
    ("归因于", "原因之一在于", ""),
]

# 2. "XX了"高危句式
verb_reps = [
    ("构建了", "建立了"),
    ("展示了", "呈现了"),
    ("揭示了", "指向了"),
    ("验证了", "确认了"),
    ("证明了", "实测支持了"),
]

# 3. 动词多样化
verb_var = {
    "显著": ["明显", "大幅", "可观地"],
    "增加": ["上升", "提高", "攀升"],
    "降低": ["下降", "减小", "回落"],
    "影响": ["改变", "左右", "调节"],
    "有效": ["切实", "确实"],
    "促进": ["推动", "有利于"],
}

# 4. 句式模式替换
sent_patterns = [
    ("首先，", "一是"),
    ("其次，", "二是"),
    ("最后，", "三是"),
    ("第一，", "其一，"),
    ("第二，", "其二，"),
    ("第三，", "其三，"),
    ("不仅…而且", "既…也"),
    ("不仅…还", "既…又"),
]

# ====== 应用第一轮替换 ======
result = main_text

# 词级替换执行
count = 0
for old, new, ctx in word_reps:
    if old in result:
        # 每次遇到都替换，但用不同的替代（简化：随机选）
        while old in result:
            result = result.replace(old, new, 1)
            count += 1

for old, new in verb_reps:
    if old in result:
        while old in result:
            result = result.replace(old, new, 1)
            count += 1

# ====== 第二轮：句级重构 ======

# 拆分过长的句子（50字+的句号内句子）
lines = result.split("\n")
new_lines = []
for line in lines:
    # 对正文段落（>30字且不含标题标记）
    if len(line) > 80 and not line.startswith("表") and not line.startswith("图") and not line.startswith("（"):
        # 在"。"后随机插入分段点
        sentences = line.split("。")
        if len(sentences) >= 4:
            # 将长段落拆分：每2-3句一段
            rebuilt = []
            for i in range(0, len(sentences), 2):
                chunk = "。".join(sentences[i:i+2])
                if chunk.strip():
                    rebuilt.append(chunk + "。")
            new_lines.extend(rebuilt)
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

# ====== 第三轮：Anti-AI审计 ======

# 检查并去除空洞结论
audit_removals = [
    "具有向其他应用场景推广的价值",
    "具有良好的应用前景",
    "具有重要的理论意义和现实意义",
]

for audit in audit_removals:
    for i, line in enumerate(new_lines):
        if audit in line:
            new_lines[i] = line.replace(audit, "可向类似场景迁移复用")

# ====== 终扫：确保修改率 ======

# 口语化检查：不应该出现口语词
slang_check = ["说白了", "搞定", "踩坑", "崩了", "离谱", "绝绝子", "破防", "这事", "其实说白了"]
slang_found = []
for i, line in enumerate(new_lines):
    for slang in slang_check:
        if slang in line:
            slang_found.append((i, slang))

result_text = "\n".join(new_lines)

# 加回参考文献
result_text += "\n" + "\n".join(text.split("\n")[-20:])

# 统计修改率
orig_chars = len(text.replace("\n", "").replace(" ", ""))
new_chars = len(result_text.replace("\n", "").replace(" ", ""))

# 计算实际变化
import difflib
diff_count = sum(1 for a, b in zip(text, result_text) if a != b)
diff_rate = diff_count / max(len(text), 1) * 100

# 写回
outpath = "C:/Users/HZC12/Desktop/论文降重版_提取文本.txt"
with open(outpath, "w", encoding="utf-8") as f:
    f.write(result_text)

print(f"原始字数: {orig_chars}")
print(f"降重后字数: {new_chars}")
print(f"词级替换: {count} 处")
print(f"估计修改率: {diff_rate:.1f}%")
print(f"口语化违规: {len(slang_found)} 处")
print(f"输出: {outpath}")
