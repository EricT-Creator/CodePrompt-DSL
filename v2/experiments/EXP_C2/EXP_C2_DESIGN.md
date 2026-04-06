# Mini EXP-C2: Propagation-Mode 对照实验设计

> 日期: 2026-04-03  
> 状态: 设计稿，待确认后执行

---

## 1. 研究问题

**RQ**: 当约束通过不同方式传递给下游 agent 时，编码方式（Header vs NL）是否影响约束遵循率？

## 2. 实验变量

### 自变量 1: Propagation Mode (4 levels)

| Mode | S1 要求 | S2 prompt 内容 | 测试什么 |
|------|--------|---------------|---------|
| **R (Reinjection)** | 普通 S1 | S1 output + 原始约束文本 | 基线（复现 EXP-C 核心条件） |
| **H (Handoff-only)** | 普通 S1 | 仅 S1 output，不注入原始约束 | 约束能否通过上游 output 自然传递 |
| **S (Structured-relay)** | S1 额外输出结构化 checklist | S1 output（含结构化 checklist） | 结构化中继能否保持保真度 |
| **SN (NL-checklist relay)** | S1 额外输出自然语言 checklist | S1 output（含 NL checklist） | 区分 "checklist effect" vs "structured effect" |

**关键对照**:
- R vs H → 传递衰减是否存在
- H vs S → 结构化 checklist 能否修复衰减
- H vs SN → NL checklist 能否修复衰减
- S vs SN → 结构化 vs NL 形式的差异（如果有的话）

### 自变量 2: Encoding (2 levels)

| 编码 | 说明 |
|------|------|
| **H** (Header) | 紧凑 DSL 编码 |
| **NLf** (NL-full) | 完整自然语言 |

（去掉 NLc——两个极端足以检测效应）

### 控制变量

| 变量 | 值 | 理由 |
|------|---|------|
| S1 模型 | Opus | 100% naturalize，放大效应 |
| S2 模型 | Opus | 保持一致 |
| S3 | **不做** | 评审建议把 auditor 剥离，只看 S2 raw compliance |

## 3. 任务选择 (3 tasks)

选择标准：覆盖三个域，且至少包含一个反直觉约束。

| Task | 域 | 反直觉约束 | 选择理由 |
|------|---|-----------|---------|
| **MC-FE-01** | FE | C2: CSS Modules | EXP-C 中失败率最高的任务之一 |
| **MC-BE-03** | BE | C2: No asyncio.Queue | BE 中最有信号的约束 |
| **MC-PY-03** | PY | C3: No ast module | PY 中有一定失败率 |

## 4. 实验矩阵

3 tasks × 2 encodings × 4 modes = **24 条管线**

| | R (Reinjection) | H (Handoff) | S (Structured) | SN (NL-checklist) |
|---|---|---|---|---|
| **MC-FE-01 × H** | FE01_H_R | FE01_H_H | FE01_H_S | FE01_H_SN |
| **MC-FE-01 × NLf** | FE01_NLf_R | FE01_NLf_H | FE01_NLf_S | FE01_NLf_SN |
| **MC-BE-03 × H** | BE03_H_R | BE03_H_H | BE03_H_S | BE03_H_SN |
| **MC-BE-03 × NLf** | BE03_NLf_R | BE03_NLf_H | BE03_NLf_S | BE03_NLf_SN |
| **MC-PY-03 × H** | PY03_H_R | PY03_H_H | PY03_H_S | PY03_H_SN |
| **MC-PY-03 × NLf** | PY03_NLf_R | PY03_NLf_H | PY03_NLf_S | PY03_NLf_SN |

每条管线跑 **2 次** → 总计 **48 次 S2 调用**。

**S1 调用**:
- Normal S1 (供 R/H): 3 tasks × 2 enc = 6
- Structured S1 (供 S): 3 tasks × 2 enc = 6
- NL-checklist S1 (供 SN): 3 tasks × 2 enc = 6
- 总计 **18 个 S1 调用**

**总调用: 18 (S1) + 48 (S2) = 66 次**

## 5. Prompt 模板设计

### S1 Prompt (所有 mode 相同)

与 EXP-C 的 S1 prompt 完全一致——S1 必须知道约束才能做设计。

**新增要求** (仅 Structured-relay mode)：S1 prompt 末尾添加一句：
> "在方案最后，请输出一个 `## Constraint Checklist`，用编号列表逐条列出每个约束的具体实现要求。"

### S2 Prompt — 按 mode 分

**Mode R (Reinjection)**:
```
{原始约束文本}

You are a developer. Implement the technical design below as {file_type}.
Follow ALL engineering constraints above strictly. Output code only.

Technical Design:
---
{S1_OUTPUT}
---
```

**Mode H (Handoff-only)**:
```
You are a developer. Implement the technical design below as {file_type}.
Follow ALL engineering constraints mentioned in the design document strictly.
Output code only.

Technical Design:
---
{S1_OUTPUT}
---
```
（注意：无原始约束文本。S2 只能从 S1 output 中理解约束。）

**Mode S (Structured-relay)**:
```
You are a developer. Implement the technical design below as {file_type}.
Follow ALL constraints in the Constraint Checklist section strictly.
Output code only.

Technical Design:
---
{S1_OUTPUT}
---
```
（S1 output 中包含 Constraint Checklist 部分，S2 从中获取结构化约束。）

## 6. 评分方法

直接复用 EXP-C 的 `score_s2_binary.py` 评分脚本（L2 客观二值判定），不做 S3。

对每条管线计算 CSR-obj = 6 条约束中 PASS 的比例。

## 7. 预期结果与假设

| 假设 | 预期 | 如果成立的意义 |
|------|------|--------------|
| H1 | Mode R 下 H ≈ NLf (复现 EXP-C) | 确认静态注入下编码无差异 |
| H2 | Mode H 下 CSR < Mode R | 证明 handoff-only 导致约束衰减 |
| H3 | Mode H 下 H vs NLf 可能有差异 | naturalization 是否在 handoff 中造成差异 |
| H4 | Mode S 下 CSR ≈ Mode R | 结构化 checklist 恢复了保真度 |
| H5 | Mode SN 下 CSR ≈ Mode S 或 CSR ≈ Mode R | 区分 checklist effect vs structured effect |

**最有价值的对照组合**:
- H2 成立 + H4 成立 + H5 部分成立 → "handoff 会衰减，任何形式的 checklist 都能修复，结构化形式是否有额外优势取决于 S vs SN 差异"
- H2 不成立 → "Opus 足够强，从 NL 方案中也能提取约束"——这也是有价值的发现

## 8. 执行计划

### Phase 1: S1 生成 (18 条)
- 3 tasks × 2 encodings × 3 variants (normal, structured, nl_checklist) = 18 个 S1 调用
- 模型: Opus
- Normal S1 → 供 Mode R 和 H 共享
- Structured S1 → 供 Mode S
- NL-checklist S1 → 供 Mode SN

### Phase 2: S2 生成 (48 条)
- 24 条管线 × 2 次重复 = 48 个 S2 调用
- 模型: Opus

### Phase 3: 自动评分
- 复用 `score_s2_binary.py` 的规则
- 输出 `exp_c2_results.csv`

**总调用: 18 (S1) + 48 (S2) = 66 次**

## 9. 设计备注 (回应评审意见)

```
v2/experiments/EXP_C2/
├── EXP_C2_DESIGN.md          ← 本文档
├── prompts/                   ← 生成的 prompt 文件
│   ├── MC-FE-01/
│   │   ├── S1_header.md
│   │   ├── S1_header_structured.md    ← S mode 的 S1
│   │   ├── S1_nl_full.md
│   │   ├── S1_nl_full_structured.md
│   │   ├── S2_R_header.md             ← Reinjection
│   │   ├── S2_H_header.md             ← Handoff-only
│   │   ├── S2_S_header.md             ← Structured-relay
│   │   └── ...
│   ├── MC-BE-03/
│   └── MC-PY-03/
├── generations/
│   ├── MC-FE-01/
│   │   ├── H_R_run1/                  ← Header × Reinjection × run1
│   │   │   ├── S1_architect.md
│   │   │   └── S2_implementer.tsx
│   │   ├── H_R_run2/
│   │   ├── H_H_run1/                  ← Header × Handoff-only × run1
│   │   └── ...
│   └── ...
├── analysis/
│   └── exp_c2_results.csv
└── instructions/                       ← 批次执行指令
```

---

*待确认后开始生成 prompt 文件和执行指令。*
