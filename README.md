# Compact Constraint Encoding for LLM Code Generation

**An Empirical Study of Token Economics and Constraint Compliance**

[English](#english) | [中文](#chinese)

---

<a name="english"></a>

## Overview

This repository contains the experimental data, scoring scripts, prompt templates, and supplementary materials for the study of compact constraint encoding effects on LLM code generation compliance.

### What We Studied

LLM-assisted code generation relies on engineering constraints (framework choices, dependency restrictions, architectural patterns) communicated through natural-language prompts. We investigated whether compact, structured constraint headers can reduce token consumption without degrading constraint compliance.

### Key Findings

Across 6 experimental rounds, 11 models, 16 benchmark tasks, and 830+ LLM invocations:

1. **Token savings are real.** Compact headers reduce constraint-portion tokens by ~71% and full-prompt tokens by 25–30%.
2. **Compliance improvement is not.** No statistically significant difference in Constraint Satisfaction Rate (CSR) was detected across three encoding forms (H/NLc/NLf) or four propagation modes. Effect sizes are negligible (Cliff's δ < 0.01).
3. **What actually matters.** Constraint type (normal vs. counter-intuitive: Δ = 9.3 pp) and task domain are the dominant variance sources—not encoding form.
4. **Non-CSS default bias.** A supplementary experiment (EXP-D) with 4 non-CSS tasks provides supporting evidence that the encoding null result extends beyond CSS-related styling constraints.
5. **A practical null result.** Compact headers are a free optimization: save tokens with no detected compliance cost.

---

## Repository Structure

```
.
├── README.md
│
├── v2/                          # Main experiments
│   ├── experiments/
│   │   ├── EXP_C/               # Multi-stage pipeline experiment (main)
│   │   │   ├── analysis/        # master.csv, statistical results
│   │   │   ├── generations/     # Generated code files (247 pipelines)
│   │   │   ├── prompts/         # S1/S2/S3 prompt templates (12 tasks × 3 encodings)
│   │   │   ├── score_s2_binary.py  # CSR scoring script
│   │   │   └── EXP_C_SCORING_RULES.md
│   │   │
│   │   ├── EXP_C2/              # Propagation-mode experiments
│   │   │   ├── analysis/        # exp_c2b_results.csv
│   │   │   ├── generations/     # C2 (Opus) + C2b (DeepSeek) outputs
│   │   │   ├── prompts/         # Propagation-mode prompt variants
│   │   │   └── score_c2.py, score_c2b.py
│   │   │
│   │   ├── EXP_D/               # Non-CSS counter-intuitive constraint extension
│   │   │   ├── generations/     # 36 pipelines (4 tasks × 3 encodings × 3 runs)
│   │   │   ├── prompts/         # S1/S2/S3 prompt templates (4 tasks × 3 encodings)
│   │   │   ├── analysis/        # EXP_D_REPORT.md
│   │   │   ├── score_exp_d.py   # CSR scoring script
│   │   │   ├── exp_d_scores.csv # Scored results
│   │   │   └── EXP_D_DESIGN.md  # Experiment design document
│   │   │
│   │   └── Human_review/        # Human-reviewed scoring validation
│   │       └── human_review_sample_v2_all_models.csv
│   │
│   ├── generations/             # Pilot v2 code outputs (11 models)
│   ├── prompts/                 # Pilot v2 prompt templates
│   ├── tasks/                   # 12 benchmark task definitions (JSON)
│   └── analysis/                # Pilot-phase analysis scripts and reports
│
├── v1/                          # Pilot experiments (EXP-v1, EXP-v2)
│   └── experiment_data/         # Phase 1-3 results (11 models, single-agent)
│
└── experiment_data/             # Legacy v1 data (kept for reference)
```

### Experiment Overview

| Round | Directory | Scope | Purpose |
|-------|-----------|-------|---------|
| **EXP-v1** | `v1/` | 1 model, 12 tasks | Negative control (Classical Chinese encoding) |
| **EXP-v2** | `v2/generations/` | 11 models, 12 tasks | Single-agent token economics + CSR |
| **EXP-C** | `v2/experiments/EXP_C/` | 7 model combos, 247 pipelines | Multi-stage pipeline compliance (main experiment) |
| **EXP-C2/C2b** | `v2/experiments/EXP_C2/` | 4 modes × 2 models × 3 rounds | Propagation-mode mechanism probes |
| **EXP-D** | `v2/experiments/EXP_D/` | 1 model, 4 tasks, 36 pipelines | Non-CSS counter-intuitive constraint extension |

---

## Reproducing Results

### EXP-C Scoring

```bash
cd v2/experiments/EXP_C
python3 score_s2_binary.py    # Scores all 247 pipeline code files
```

### EXP-D Scoring

```bash
cd v2/experiments/EXP_D
python3 score_exp_d.py        # Scores all 36 EXP-D code files
```

Scoring rules are deterministic regex-based checks. See `EXP_C_SCORING_RULES.md` and `EXP_D_DESIGN.md` for constraint definitions.

### Human Review

`Human_review/human_review_sample_v2_all_models.csv` contains independent human reviews of all flagged failures + random PASS samples, validating the automated scoring.

---

## License

MIT

---

<a name="chinese"></a>

## 概览

本仓库包含紧凑约束编码对 LLM 代码生成遵循率影响的实验数据、评分脚本、Prompt 模板和补充材料。

### 研究内容

LLM 辅助代码生成依赖通过自然语言 Prompt 传达的工程约束（技术选型、依赖限制、架构模式）。我们研究紧凑的结构化约束 Header 是否能在不降低约束遵循率的前提下减少 Token 消耗。

### 核心发现

在 6 轮实验、11 个模型、16 个 Benchmark 任务、830+ 次 LLM 调用中：

1. **Token 节省是真实的。** 紧凑 Header 将约束部分 Token 减少约 71%，完整 Prompt Token 减少 25–30%。
2. **遵循率提升是不存在的。** 三种编码形式（H/NLc/NLf）和四种传播模式之间均未检测到约束满足率（CSR）的统计显著差异。效应量可忽略（Cliff's δ < 0.01）。
3. **真正起作用的因素。** 约束类型（普通 vs 反直觉：Δ = 9.3 pp）和任务域是遵循率方差的主要来源——而非编码形式。
4. **非 CSS 默认偏差。** 补充实验（EXP-D）使用 4 个非 CSS 任务提供了编码零效应超越 CSS 领域的支持证据。
5. **一个有实践意义的零结果。** 紧凑 Header 是免费优化：节省 Token 且无检测到的遵循成本。

---

## 实验概览

| 轮次 | 目录 | 范围 | 目的 |
|------|------|------|------|
| **EXP-v1** | `v1/` | 1 模型, 12 任务 | 负控制（古文编码） |
| **EXP-v2** | `v2/generations/` | 11 模型, 12 任务 | 单 Agent Token 经济性 + CSR |
| **EXP-C** | `v2/experiments/EXP_C/` | 7 模型组合, 247 管线 | 多阶段管线遵循率（主实验） |
| **EXP-C2/C2b** | `v2/experiments/EXP_C2/` | 4 模式 × 2 模型 × 3 轮 | 传播模式机制探针 |
| **EXP-D** | `v2/experiments/EXP_D/` | 1 模型, 4 任务, 36 管线 | 非 CSS 反直觉约束扩展 |

---

## 复现

### EXP-C 评分

```bash
cd v2/experiments/EXP_C
python3 score_s2_binary.py
```

### EXP-D 评分

```bash
cd v2/experiments/EXP_D
python3 score_exp_d.py
```

### 人工审核

`Human_review/human_review_sample_v2_all_models.csv` 包含人工对所有标记失败和随机 PASS 样本的独立审查，验证自动化评分的准确性。

---

## License

MIT

---

*A valuable experiment is not one that confirms what you hoped, but one that makes clear what doesn't work—and why.*

*有价值的实验不在于证实了你期望的结论，而在于让人清楚地看到什么不起作用——以及为什么。*
