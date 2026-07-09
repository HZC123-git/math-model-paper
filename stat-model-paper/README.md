# stat-model-paper：统计建模大赛论文生成器

全国大学生统计建模大赛专用。与 math-model-paper 共用底层管线，但在论文结构、写作风格和检验要求上有针对性优化。

## 与 math-model-paper 的区别

| 维度 | math-model-paper | stat-model-paper |
|------|-----------------|-----------------|
| 目标赛事 | 数学建模/美赛/国赛 | **统计建模大赛** |
| 论文风格 | 工程报告型 | **经济学/社会学学术论文** |
| 文献综述 | 可选 | **必需（15-25篇）** |
| 内生性讨论 | 不提 | **必须（IV/FE/DID/PSM）** |
| 稳健性检验 | 不提 | **必须（至少两种方法）** |
| 政策建议 | 不要求 | **必需章节** |
| 诊断检验 | 残差图 | **VIF + 异方差 + 自相关** |
| p值/标准误 | 不一定 | **必须报告** |

## 安装

```bash
git clone --depth 1 https://github.com/HZC123-git/math-model-paper.git ~/.claude/skills/stat-model-paper
```

## 使用

```
/stat-model-paper
数据: 教育回报.csv
因变量: wage
核心自变量: edu_year
控制变量: age, gender, exp, industry
```

## 复用模块

底层管线（pipeline/）与 math-model-paper 完全共用。
