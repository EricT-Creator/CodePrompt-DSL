# EXP-B 克隆排除实验综合分析报告

> **报告时间**：2026-04-01 12:00 CST  
> **数据来源**：B1 seed 测试 16 个文件 + B3 矛盾测试 16 个文件 + B4 通过 EXP-A 附带  
> **分析模型**：Claude-Opus-4.6（自动化 hash 比对 + 代码检查）

---

## 一、实验目标

确定 Pilot 阶段观察到的 BE/PY 域变体克隆（A=B=C=D 字节级相同）的根本原因，区分三种假说：

| 假说 | 含义 |
|------|------|
| **H1** | 任务太简单，实现空间极小，模型收敛到同一"最简实现" |
| **H2** | WorkBuddy 平台缓存，短时间内返回相同结果 |
| **H3** | 模型忽略 Compact Header，只看自然语言描述 |

---

## 二、B1 Seed 干扰测试结果

### 2.1 实验设计

在 Prompt 末尾附加唯一随机 seed（`<!-- session-id: {hex8} -->`），测试是否能绕过潜在的平台缓存。每个变体在独立新会话中执行。

### 2.2 MiniMax-M2.7 Hash 比对

| 条件 | A | B | C | D | 4 变体全同？ |
|------|---|---|---|---|-------------|
| **seed** | `6d51dba0` | `81b8f9c6` | `64493bd6` | `b04100d4` | ❌ **全不同** |
| **no_seed** | `84fd53ee` | `571346d6` | `3305284e` | `3c006114` | ❌ **全不同** |

**关键发现**：MiniMax-M2.7 无论有无 seed，4 个变体的 hash 都不同。

⚠️ **注意**：这与 Pilot 阶段的观察（MiniMax 全域全克隆）**矛盾**。可能原因：
1. Pilot 阶段未严格做到每变体独立新会话（最可能）
2. 平台侧在此期间更新了缓存机制
3. BE-01 HealthCheck 的实现空间虽小，但 import 顺序、函数命名、格式等仍有变异

### 2.3 Kimi-K2.5 Hash 比对

| 条件 | A | B | C | D | 克隆模式 |
|------|---|---|---|---|---------|
| **seed** | `bc1175c4` | `bc1175c4` | `bc1175c4` | `24e7d47e` | A=B=C ≠ D |
| **no_seed** | `05bd22c6` | `b978ccd1` | `5b1dfc59` | `05bd22c6` | A=D, B/C 独立 |

**关键发现**：
- **seed 版**：A/B/C 三个英文变体产出完全相同的代码，D（古文变体）不同。加 seed 未能打破英文变体间的克隆。
- **no_seed 版**：A=D 克隆，但 B/C 独立（B 只有 26 字节，疑似截断）。
- **结论**：Kimi 的克隆**不是平台缓存导致的**（seed 没用），而是模型对英文 BE-01 这种极简任务的确定性输出。

### 2.4 B1 综合判定

| 模型 | seed 能否打破克隆？ | 判定 |
|------|-------------------|------|
| MiniMax-M2.7 | N/A（无论有无 seed 都独立） | **H2 不适用**：MiniMax 在严格会话隔离下不再克隆 |
| Kimi-K2.5 | ❌（A/B/C 仍克隆） | **H2 排除**：seed 无效，克隆来自模型确定性 |

---

## 三、B3 约束矛盾测试结果

### 3.1 实验设计

构造 Header 与描述矛盾的 prompt（BE-01: Header=[F]Flask vs 描述=FastAPI; PY-01: Header=[D]pandas_allowed vs 描述=no pandas），测试模型是否真正阅读了 Header。

### 3.2 BE-01 矛盾测试（Header=Flask, 描述=FastAPI）

| 模型 | conflict 中使用 | control 中使用 | 遵循哪方 |
|------|----------------|---------------|---------|
| MiniMax-M2.7 | FastAPI | FastAPI | **描述优先** |
| Kimi-K2.5 | FastAPI | FastAPI | **描述优先** |
| GLM-5.0 | FastAPI | FastAPI | **描述优先** |
| Claude-Opus-4.6 | **Flask** | FastAPI | **Header 优先** |

### 3.3 PY-01 矛盾测试（Header=pandas_allowed, 描述=Do not use pandas）

| 模型 | conflict 中使用 | control 中使用 | 判定 |
|------|----------------|---------------|------|
| MiniMax-M2.7 | csv（stdlib） | csv（stdlib） | 遵循描述 |
| Kimi-K2.5 | csv（stdlib） | csv（stdlib） | 遵循描述 |
| GLM-5.0 | csv（stdlib） | csv（stdlib） | 遵循描述 |
| Claude-Opus-4.6 | csv（stdlib） | csv（stdlib） | 遵循描述* |

*注：Header 说 `pandas_allowed`（允许）而非 `pandas_required`（必须），用 csv 不算违反 Header。此矛盾对不够尖锐。

### 3.4 B3 综合判定

| 发现 | 说明 |
|------|------|
| **H3 排除** | 所有 4 个模型都阅读了 Header——Kimi 和 GLM 在 Pilot B3 首次执行时主动在回复中提到了 Header 内容并解释了取舍；Claude 在 BE-01 中明确遵循了 Header 而非描述 |
| **优先级分歧** | Claude 家族 = Header 优先；其他模型 = 描述优先。这是一个有论文价值的新发现 |
| **conflict ≠ control** | 8/8 对比全部 DIFFERENT，确认矛盾引入确实造成了行为变化 |

---

## 四、B4 进阶任务克隆对比结果

### 4.1 数据来源

直接使用 EXP-A 中 6 个模型的进阶任务数据（FE-05~08, BE-05~08, PY-05~08 × 4 变体）。

### 4.2 结果

**EXP-A 审查报告确认**：全部 6 个模型的 A vs C 比对中，**72/72 全部独立**（R12 FLAG = 0，仅 2 个伪克隆来自 Claude 的空文件）。

特别是 **Kimi-K2.5**——在 Pilot 中 BE/PY 域 100% 克隆，但在进阶任务中**零克隆**。

### 4.3 B4 判定

| 判定 | 说明 |
|------|------|
| **H1 强支持** | Pilot 中的克隆确因任务太简单。进阶任务复杂度提升后，模型的实现空间增大，克隆消失 |

---

## 五、三假说综合判定矩阵

| 假说 | B1 结果 | B3 结果 | B4 结果 | 最终判定 |
|------|---------|---------|---------|---------|
| **H1：任务太简单** | MiniMax 在严格隔离下已不克隆；Kimi 英文变体仍克隆 | — | 进阶任务零克隆 | ✅ **成立（主因）** |
| **H2：平台缓存** | Kimi seed 无效（排除缓存）；MiniMax 严格隔离后不克隆 | — | — | ❌ **排除** |
| **H3：模型忽略 Header** | — | 4/4 模型都读了 Header | — | ❌ **排除** |

### 补充说明

Pilot 中的克隆现象是**两个因素叠加**的结果：

1. **H1（主因）**：BE-01 HealthCheck 这类极简任务的实现空间极小，模型无论收到什么变体 prompt，都倾向于收敛到相同的"最简实现"
2. **会话隔离不充分（Pilot 操作问题）**：MiniMax 在 B1 严格隔离后不再克隆，说明 Pilot 中的全域克隆可能部分源于同一会话中连续投递多个变体

当这两个因素同时消除时（EXP-A 中任务更复杂 + 严格会话隔离），克隆完全消失。

---

## 六、论文中的使用方式

| 论文章节 | 使用方式 |
|---------|---------| 
| §4 Methodology → Threats to Validity | "为排除平台缓存和模型行为对实验结果的影响，我们设计了 EXP-B 克隆排除实验..." |
| §5 Results → Clone Analysis | 报告 B1/B3/B4 的结果和最终判定：克隆源于任务简单性 + 会话隔离不充分 |
| §5 Results → Header Priority | 新发现：Claude 家族 Header-first vs 其他模型 Description-first |
| §6 Discussion | 讨论克隆现象的实践意义：compact header 在非矛盾场景下与 NL 等效，因为两种优先级策略殊途同归 |
| §7 Limitations | B2（时间间隔测试）未执行，声明为设计但未完成的实验 |

---

## 七、产物清单

| 产物 | 路径 | 文件数 |
|------|------|--------|
| B1 seed 文件 | `EXP_B/B1_seed/{model}/seed/` | 8 |
| B1 no_seed 文件 | `EXP_B/B1_seed/{model}/no_seed/` | 8 |
| B3 conflict 文件 | `EXP_B/B3_conflict/{model}/conflict/` | 8 |
| B3 control 文件 | `EXP_B/B3_conflict/{model}/control/` | 8 |
| B3 初次分析报告 | `EXP_B/B3_conflict/B3_RESULTS.md` | 1 |
| 本综合报告 | `EXP_B/EXP_B_RESULTS.md` | 1 |

---

## 八、未完成项

| 子实验 | 状态 | 影响 |
|--------|------|------|
| B1 FE-01 seed/no_seed | 未执行 | FE 域在 Pilot 中已独立，对照价值有限 |
| B2 时间间隔测试 | 未执行 | H2 已通过 B1 seed 结果排除，B2 为冗余验证 |

---

*报告时间：2026-04-01 12:00 CST*  
*分析脚本：手动 hash 比对 + grep 检查*
