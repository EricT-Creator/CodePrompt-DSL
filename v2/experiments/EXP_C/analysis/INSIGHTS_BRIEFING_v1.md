# EXP-C Phase 4 — Insights Briefing (v1)

> **生成时间**: 2026-04-03 17:10  
> **状态**: 初步发现，待深挖  
> **数据来源**: L2 constraint_binary_s2.csv + L1 s1_mention_repr.csv

---

## 1. Naturalization Rate — 论文核心证据

### 发现

Header 编码下，S1 阶段的 Naturalization Rate **因模型而异**：

| S1 模型 | H 编码 NatRate | 行为描述 |
|---------|---------------|---------|
| Opus (R) | **1.000** | 100% naturalize — 方案主体完全自然语言化，无结构化痕迹 |
| Kimi (C) | **1.000** | 同上 |
| DeepSeek (S) | **0.000** | 保留完整 header token 结构（约束映射表嵌入方案主体）|

NLc/NLf 编码：NatRate = 1.000（by definition，输入本身就是 NL）

### 论文意义

- **直接支持 H-C8**：compact header 的结构化优势在 S1 就被大多数模型 naturalize
- **但存在模型异质性**：DeepSeek（格式敏感型）保留了结构形式 → system-shape sensitivity 的微观证据
- **待深挖**：DeepSeek 保留 Str 形式是否导致其 S2 约束遵循率更高？（需交叉 L1 NatRate × L2 CSR）

---

## 2. S2 约束遵循率 (CSR-obj) — 总体格局

### 总体

| 指标 | 值 |
|------|---|
| Mean CSR-obj | **0.950** |
| Normal 约束 (C1/C4/C5/C6) | 0.991 |
| Counter-intuitive (C2/C3) | 0.870 |
| **Gap** | **+0.121** |

### 按编码

| 编码 | CSR-obj | n |
|------|---------|---|
| H | 0.951 | 82 |
| NLc | 0.944 | 81 |
| NLf | 0.956 | 83 |

差异 ~1.2%，**需要统计检验**（Kruskal-Wallis 或 bootstrap CI）。

### 按 combo

| Combo | CSR-obj | 差值 vs RRR |
|-------|---------|------------|
| RRR (baseline) | 0.954 | — |
| CRR (S1→C) | 0.958 | +0.004 |
| SRR (S1→S) | 0.954 | +0.000 |
| RCR (S2→C) | 0.948 | −0.006 |
| RSR (S2→S) | 0.935 | **−0.019** |
| RRC (S3→C) | 0.958 | +0.004 |
| RRS (S3→S) | 0.944 | −0.010 |

初步观察：
- **RSR 差值最大** (−0.019) → DeepSeek 作 S2 Implementer 时约束遵循最差（但 n 小，有 5 个 S2 缺失）
- S1 替换影响最小（CRR/SRR ≈ 基线）→ 初步支持 H-C5（S1 影响通过间接传播）
- S3 替换影响有限 → 初步支持 H-C6

### 按域

| 域 | CSR-obj |
|----|---------|
| Frontend | 0.907 |
| Backend | 0.970 |
| Python | 0.976 |

前端显著低于后端/Python — 失败集中在 CSS 相关约束。

---

## 3. 失败热点

| 排名 | Task × Constraint | 失败数 | 说明 |
|------|-------------------|--------|------|
| 1 | MC-FE-02 × C3 (CSS Modules) | 19/21 | 近乎系统性失败 |
| 2 | MC-FE-01 × C2 (CSS Modules) | 17/21 | 同上 |
| 3 | MC-FE-04 × C3 (plain CSS) | 11/21 | |
| 4 | MC-BE-03 × C2 (禁 asyncio.Queue) | 8/21 | |
| 5 | MC-BE-01 × C4 (append-only) | 6/21 | |

### 论文意义
- 反直觉约束的衰减集中在**特定任务**，不是均匀分布
- CSS Modules 是所有模型的"盲点"——inline style 对象被普遍误当作 CSS Modules
- **待深挖**：CSS Modules 失败率是否在不同编码间有差异？

---

## 4. Mention Rate — S1 覆盖度

| 编码 | Mention Rate |
|------|-------------|
| H | 1.000 |
| NLc | 1.000 |
| NLf | 0.958 |

| S1 模型 | Mention Rate |
|---------|-------------|
| Opus | 0.995 |
| Kimi | 0.991 |
| DeepSeek | 0.935 |

DeepSeek 的 Mention Rate 最低 (0.935) — 作为 S1 时有约束遗漏。
**待深挖**：DeepSeek S1 遗漏了哪些约束？是否集中在特定类型？

---

## 5. 待深挖清单

- [x] 编码条件差异统计检验 → **T1: KW H=0.60, ns（不显著）**
- [x] NatRate × CSR 交叉分析 → **H-C9 不成立，Δ=−0.008**
- [x] DeepSeek Str 保留 → **CSR=0.944 vs Nat=0.952，保留 Str 未提升 CSR**
- [x] CSS Modules 失败率 × 编码差异 → **NLf=64.3% > H=57.1% > NLc=46.4%**
- [x] DeepSeek S1 Mention 遗漏分析 → **仅 NLf 下遗漏 C4/C6，S1 遗漏不预测 S2 失败**
- [x] Layer 1 Pass 2: F + A 维度补充 → **Fidelity: 99.1% Exact, Actionability: 0.844（待人工抽检复核）**
- [x] 反直觉约束 × combo 交互效应 → **RSR C3 失败最高 (23%)，域效应 >> 编码/combo 效应**

---

*本 memo 为工作草稿，随 Phase 4 推进持续更新。*

---

## 6. P0 分析结果 (2026-04-03 18:50)

### H-C9 检验：NatRate × CSR

| 组 | n | NatRate | CSR-obj-S2 |
|---|---|---------|-----------|
| Str-dominant (DeepSeek S1) | 12 | 0.00 | 0.944 |
| Nat-dominant (Opus/Kimi S1) | 70 | 1.00 | 0.952 |
| **Δ (Str − Nat)** | | | **−0.008** |

**结论：H-C9 不成立**。保留结构化形式（DeepSeek）的 CSR 反而**略低于** naturalize 的管线（Opus/Kimi）。差值极小（0.8%），不显著。

**解读**：Naturalization 不是约束衰减的因。S1 将 header naturalize 后，S2 仍然能高度遵循约束——因为 S2 的 prompt 中也包含原始约束层。约束衰减的真正瓶颈不在 S1→S2 的传递，而在模型对特定约束类型（CSS Modules）的理解能力。

### 衰减曲线

```
S0=1.000 → S1=0.986 → S2=0.950 → S3=0.963
           (−1.4%)    (−3.6%)    (+1.3%)
```

- S1→S2 是主要衰减节点（约束从"被提及"到"被实现"损失 3.6%）
- S3 略高于 S2 → S3 auditor 比客观规则更宽松

### S3 Auditor 偏差

| S3 模型 | Lenient | Strict | 净偏差 |
|---------|---------|--------|--------|
| Opus | 29 | 11 | **偏宽松** |
| Kimi | 6 | 4 | 轻微宽松 |
| DeepSeek | 9 | 11 | **轻微偏严** |

### Per-Constraint 存活率

| 约束 | 存活率 | 类型 |
|------|--------|------|
| C6 | 1.000 | 常规 |
| C1 | 0.996 | 常规 |
| C5 | 0.996 | 常规 |
| C4 | 0.972 | 常规 |
| C2 | 0.894 | **反直觉** |
| C3 | 0.846 | **反直觉** |
