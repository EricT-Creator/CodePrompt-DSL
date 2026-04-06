# Compact Constraint Encoding for LLM Code Generation

**An Empirical Study of Token Economics and Constraint Compliance**

[English](#english) | [中文](#chinese)

---

<a name="english"></a>

## Overview

This repository contains the experimental data, scoring scripts, prompt templates, and supplementary materials for the paper:

> **Compact Constraint Encoding for LLM Code Generation: An Empirical Study of Token Economics and Constraint Compliance**
>
> Tang Hanzhang · Independent Researcher, Tencent · April 2026

### What We Studied

LLM-assisted code generation relies on engineering constraints (framework choices, dependency restrictions, architectural patterns) communicated through natural-language prompts. We investigated whether compact, structured constraint headers can reduce token consumption without degrading constraint compliance.

### Key Findings

Across 5 experimental rounds, 11 models, 12 benchmark tasks, and 800+ LLM invocations:

1. **Token savings are real.** Compact headers reduce constraint-portion tokens by ~71% and full-prompt tokens by 25–30%.
2. **Compliance improvement is not.** No statistically significant difference in Constraint Satisfaction Rate (CSR) was detected across three encoding forms (H/NLc/NLf) or four propagation modes. Effect sizes are negligible (Cliff's δ < 0.01).
3. **What actually matters.** Constraint type (normal vs. counter-intuitive: Δ = 9.3 pp) and task domain are the dominant variance sources—not encoding form.
4. **A practical null result.** Compact headers are a free optimization: save tokens with no detected compliance cost.

### Paper

- **arXiv preprint**: `v2/paper/PAPER_v4_EN.html` (English) and `PAPER_v4_CN.html` (Chinese)

---

## Repository Structure

```
.
├── README.md
│
├── v1/                          # Pilot experiments (EXP-v1, EXP-v2)
│   ├── experiment_data/         # Phase 1-3 results (11 models, single-agent)
│   └── ...                      # Pilot-phase prompts, reports, and data
│
├── v2/                          # Main experiments (EXP-C, C2, C2b)
│   ├── experiments/
│   │   ├── EXP_C/               # Multi-stage pipeline experiment
│   │   │   ├── analysis/        # master.csv, statistical results
│   │   │   ├── generations/     # Generated code files (247 pipelines)
│   │   │   ├── prompts/         # S1/S2/S3 prompt templates
│   │   │   ├── score_s2_binary.py  # CSR scoring script
│   │   │   └── EXP_C_SCORING_RULES.md
│   │   │
│   │   ├── EXP_C2/              # Propagation-mode experiments
│   │   │   ├── analysis/        # exp_c2b_results.csv
│   │   │   ├── generations/     # C2 (Opus) + C2b (DeepSeek) outputs
│   │   │   ├── prompts/         # Propagation-mode prompt variants
│   │   │   └── score_c2.py, score_c2b.py
│   │   │
│   │   ├── Human_review/        # Human-reviewed scoring validation
│   │   │   └── human_review_sample_v2_all_models.csv
│   │   └── MULTI_MODEL_REVIEW_ANALYSIS.md
│   │
│   ├── generations/             # Pilot v2 code outputs (11 models)
│   ├── prompts/                 # Pilot v2 prompt templates
│   ├── tasks/                   # 12 benchmark task definitions (JSON)
│   ├── analysis/                # Pilot-phase analysis scripts and reports
│   │
│   └── paper/                   # Paper (HTML, print to PDF for arXiv)
│       ├── PAPER_v4_EN.html
│       ├── PAPER_v4_CN.html
│       ├── PAPER_v4_EN.md
│       └── PAPER_v4_CN.md
│
└── experiment_data/             # Legacy v1 data (kept for reference)
```

### What's in v1 vs v2

| Phase | Directory | Scope | Role in paper |
|-------|-----------|-------|---------------|
| **v1** | `v1/`, `experiment_data/` | Pilot: 6 encoding forms × 10 tasks × 9+ models (single-agent) | EXP-v1 (Classical Chinese), EXP-v2 (token economics + single-agent CSR) |
| **v2** | `v2/experiments/EXP_C/` | Main: 3 encodings × 12 tasks × 7 model combos (3-stage pipeline, 252 pipelines) | EXP-C (core compliance analysis) |
| **v2** | `v2/experiments/EXP_C2/` | Probe: 4 propagation modes × 2 models × 3 rounds | EXP-C2/C2b (propagation-mode mechanism probes) |

---

## Reproducing Results

### CSR Scoring

```bash
cd v2/experiments/EXP_C
python3 score_s2_binary.py    # Scores all generated code files
```

The scoring rules are deterministic regex-based checks. See `EXP_C_SCORING_RULES.md` for the constraint definitions and `score_s2_binary.py` for the implementation.

### Human Review Audit

The `Human_review/human_review_sample.xlsx` file contains independent reviews by four people on all 67 flagged failures + 30 random PASS samples.

---

## License

MIT

---

<a name="chinese"></a>

## 概览

本仓库包含以下论文的实验数据、评分脚本、Prompt 模板和补充材料：

> **LLM 代码生成中的紧凑约束编码：Token 经济性与约束遵循率的实证研究**
>
> 唐含章 · 独立研究者，腾讯 · 2026 年 4 月

### 研究内容

LLM 辅助代码生成依赖通过自然语言 Prompt 传达的工程约束（技术选型、依赖限制、架构模式）。我们研究紧凑的结构化约束 Header 是否能在不降低约束遵循率的前提下减少 Token 消耗。

### 核心发现

在 5 轮实验、11 个模型、12 个 Benchmark 任务、800+ 次 LLM 调用中：

1. **Token 节省是真实的。** 紧凑 Header 将约束部分 Token 减少约 71%，完整 Prompt Token 减少 25–30%。
2. **遵循率提升是不存在的。** 三种编码形式（H/NLc/NLf）和四种传播模式之间均未检测到约束满足率（CSR）的统计显著差异。效应量可忽略（Cliff's δ < 0.01）。
3. **真正起作用的因素。** 约束类型（普通 vs 反直觉：Δ = 9.3 pp）和任务域是遵循率方差的主要来源——而非编码形式。
4. **一个有实践意义的零结果。** 紧凑 Header 是免费优化：节省 Token 且无检测到的遵循成本。

### 论文

- **arXiv 预印本**：`v2/paper/PAPER_v4_EN.html`（英文）和 `PAPER_v4_CN.html`（中文）

---

## 仓库结构

```
.
├── README.md
│
├── v1/                          # 先导实验（EXP-v1, EXP-v2）
│   ├── experiment_data/         # 第 1-3 阶段结果（11 个模型，单 Agent）
│   └── ...
│
├── v2/                          # 主实验（EXP-C, C2, C2b）
│   ├── experiments/
│   │   ├── EXP_C/               # 多阶段管线实验
│   │   │   ├── analysis/        # master.csv，统计结果
│   │   │   ├── generations/     # 生成的代码文件（247 条管线）
│   │   │   ├── prompts/         # S1/S2/S3 Prompt 模板
│   │   │   ├── score_s2_binary.py  # CSR 评分脚本
│   │   │   └── EXP_C_SCORING_RULES.md
│   │   │
│   │   ├── EXP_C2/              # 传播模式实验
│   │   │   ├── analysis/        # exp_c2b_results.csv
│   │   │   ├── generations/     # C2（Opus）+ C2b（DeepSeek）输出
│   │   │   └── prompts/
│   │   │
│   │   ├── Human_review/        # 人工审核评分验证
│   │   │   └── human_review_sample_v2_all_models.csv
│   │   └── MULTI_MODEL_REVIEW_ANALYSIS.md
│   │
│   ├── generations/             # 先导 v2 代码输出（11 个模型）
│   ├── prompts/                 # 先导 v2 Prompt 模板
│   ├── tasks/                   # 12 个 Benchmark 任务定义（JSON）
│   └── paper/                   # 论文（HTML 格式，浏览器打印为 PDF）
```

### v1 与 v2 的关系

| 阶段 | 目录 | 范围 | 在论文中的角色 |
|------|------|------|-------------|
| **v1** | `v1/`, `experiment_data/` | 先导：6 种编码 × 10 任务 × 9+ 模型（单 Agent） | EXP-v1（古文）、EXP-v2（Token 经济性 + 单 Agent CSR） |
| **v2** | `v2/experiments/EXP_C/` | 主体：3 种编码 × 12 任务 × 7 模型组合（三阶段管线，252 条管线） | EXP-C（核心遵循率分析） |
| **v2** | `v2/experiments/EXP_C2/` | 探针：4 种传播模式 × 2 模型 × 3 轮 | EXP-C2/C2b（传播模式机制探针） |

---

## 复现

### CSR 评分

```bash
cd v2/experiments/EXP_C
python3 score_s2_binary.py
```

评分规则为确定性的 Regex 检查。详见 `EXP_C_SCORING_RULES.md`（约束定义）和 `score_s2_binary.py`（实现）。

### 人类审计

`Human_review/human_review_sample.xlsx` 包含四个人类对全部 67 个标记失败 + 30 个随机 PASS 样本的独立审查。

---

## License

MIT

---

*A valuable experiment is not one that confirms what you hoped, but one that makes clear what doesn't work—and why.*

*有价值的实验不在于证实了你期望的结论，而在于让人清楚地看到什么不起作用——以及为什么。*
