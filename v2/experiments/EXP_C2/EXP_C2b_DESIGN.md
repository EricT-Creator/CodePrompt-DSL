# EXP-C2b: 弱模型 Propagation Probe

> 日期: 2026-04-04  
> 状态: 设计确认，待执行

## 设计

- **3 tasks**: MC-FE-01, MC-BE-03, MC-PY-03 (复用 C2 的任务)
- **3 modes**: R (Reinjection) / H (Handoff-only) / S (Structured-relay)
- **1 encoding**: H (Header) — 极端条件，naturalization 效应最大
- **S1 = Opus** (复用 C2 已有的 S1 output)
- **S2 = DeepSeek-V3.2** (弱模型)
- **不做 S3**
- **2 runs** per condition

## 矩阵

3 tasks × 3 modes × 1 enc × 2 runs = **18 次 S2 调用**

| | R | H | S |
|---|---|---|---|
| MC-FE-01 × H | ✓×2 | ✓×2 | ✓×2 |
| MC-BE-03 × H | ✓×2 | ✓×2 | ✓×2 |
| MC-PY-03 × H | ✓×2 | ✓×2 | ✓×2 |

## S1 复用

直接使用 EXP-C2 Phase 1 已生成的 Opus S1 output:
- R/H: `{task}/H_normal_S1/S1_architect.md`
- S: `{task}/H_structured_S1/S1_architect.md`

## S2 Prompt

与 C2 完全相同的 S2 prompt template，只是模型换成 DeepSeek。
Filled prompts 直接复用: `filled_prompts/{task}/S2_H_{R|H|S}_run{1|2}.md`

## 预期

| 结果 | 含义 |
|------|------|
| H 掉点 | propagation bottleneck is model-tier dependent |
| H 不掉 | propagation 不是这个任务族的主要矛盾 |
