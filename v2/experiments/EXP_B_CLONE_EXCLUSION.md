# EXP-B：克隆排除实验设计

> **实验编号**：EXP-B  
> **目的**：确定 Pilot 阶段观察到的 BE/PY 域变体克隆的根本原因，区分三种可能解释  
> **前提**：Pilot 分析发现 5/11 模型在 BE/PY 域产出了 A=B=C=D 的字节级克隆，但同一批模型在 FE 域却能产出独立变体  
> **设计时间**：2026-03-31  
> **状态**：待执行  
> **与 EXP-A 的关系**：独立实验，验证不同的问题。EXP-A 验证"增加难度能否产生区分度"，EXP-B 验证"克隆的原因是什么"

---

## 一、问题陈述

### 1.1 要解决的具体问题

Pilot 数据中观察到以下克隆模式：

| 模型 | FE 克隆率 | BE 克隆率 | PY 克隆率 | 模式 |
|------|----------|----------|----------|------|
| MiniMax-M2.7 | 100% | 100% | 100% | 全域全克隆 |
| GLM-5.0 | 0% | 100% | 100% | FE 独立，BE/PY 全克隆 |
| Kimi-K2.5 | 0% | 100% | 100% | FE 独立，BE/PY 全克隆 |
| Claude-Haiku-4.5 | 0% | 100% | 100% | FE 独立，BE/PY 全克隆 |
| GLM-5.0-Turbo | 0% | 25% | 0% | FE/PY 独立，BE-01 轻微克隆 |

### 1.2 三种互斥假说

| 假说 | 说明 | 预期实验结果 |
|------|------|-------------|
| **H1：任务太简单** | BE/PY 基础任务的实现空间极小，模型无论收到什么 prompt 都会收敛到同一"最简实现" | 进阶任务中克隆消失，简单任务中仍克隆 |
| **H2：平台缓存** | WorkBuddy 平台在短时间内对相同/相似 prompt 返回了缓存结果 | 同一任务加 seed 后输出改变，或间隔 30 分钟重跑后输出改变 |
| **H3：模型忽略 Header** | 模型根本没有阅读约束 Header，只看需求描述生成代码 | 矛盾约束测试中模型遵循描述而非 Header |

**关键**：这三种假说不完全互斥（可能同时成立），但实验需要区分各自的贡献程度。

---

## 二、实验设计

### 2.1 实验结构总览

| 子实验 | 验证假说 | 核心操作 | 数据点数 |
|--------|---------|---------|---------|
| **B1：Seed 干扰测试** | H2（平台缓存） | 在 prompt 末尾加随机 seed 字符串 | 32 |
| **B2：时间间隔测试** | H2（平台缓存） | 间隔 30 分钟对同一任务重跑 | 16 |
| **B3：约束矛盾测试** | H3（模型忽略 Header） | Header 与描述包含矛盾约束 | 16 |
| **B4：进阶任务克隆对比** | H1（任务太简单） | 用 EXP-A 进阶任务检查克隆状态 | 附带于 EXP-A |
| **总计** | — | — | **64 + EXP-A 附带** |

---

### 2.2 B1：Seed 干扰测试

#### 设计原理

如果克隆是由平台缓存引起的，那么在 prompt 中添加一个唯一的随机字符串（seed）应该绕过缓存，使模型产出不同的代码。如果添加 seed 后输出仍然克隆，则排除平台缓存假说。

#### 操作协议

**选择的模型**：MiniMax-M2.7（全域全克隆的极端案例）、Kimi-K2.5（FE 独立但 BE/PY 克隆）

**选择的任务**：BE-01（HealthCheck，最简任务，在两个模型上都是 100% 克隆）、FE-01（LoginForm，Kimi 在 FE 上独立，作为阳性对照）

**Seed 格式**：在 prompt 末尾附加一行：
```
<!-- session-id: {random_hex_8} -->
```

其中 `{random_hex_8}` 是 8 位随机十六进制字符串（如 `a7b3c9e1`），每个 (model, task, variant) 的 seed 都不同。

**执行矩阵**：

| 模型 | 任务 | 变体 | 有 Seed | 生成次数 |
|------|------|------|--------|---------|
| MiniMax-M2.7 | BE-01 | A, B, C, D | ✅ | 4 |
| MiniMax-M2.7 | BE-01 | A, B, C, D | ❌（重跑原始 prompt） | 4 |
| MiniMax-M2.7 | FE-01 | A, B, C, D | ✅ | 4 |
| MiniMax-M2.7 | FE-01 | A, B, C, D | ❌（重跑原始 prompt） | 4 |
| Kimi-K2.5 | BE-01 | A, B, C, D | ✅ | 4 |
| Kimi-K2.5 | BE-01 | A, B, C, D | ❌（重跑原始 prompt） | 4 |
| Kimi-K2.5 | FE-01 | A, B, C, D | ✅ | 4 |
| Kimi-K2.5 | FE-01 | A, B, C, D | ❌（重跑原始 prompt） | 4 |
| **合计** | | | | **32** |

#### 判定标准

| 结果 | 判定 |
|------|------|
| Seed 版本 A≠B≠C≠D，原始版本 A=B=C=D | **H2 成立**：平台缓存是克隆原因 |
| Seed 版本 A=B=C=D，原始版本 A=B=C=D | **H2 排除**：克隆不是缓存导致 |
| Seed 版本部分不同 | **H2 部分成立**：需要结合 B2 进一步确认 |

#### 比较方法

克隆判定使用**字节级比较**（`diff` 或 `sha256` hash）：

```bash
# 生成 hash
sha256sum v2/generations/{model}/A/BE-01_*.py
sha256sum v2/generations/{model}/B/BE-01_*.py
# 如果 hash 相同 → 克隆
```

---

### 2.3 B2：时间间隔测试

#### 设计原理

如果平台缓存有 TTL（生存时间），那么在不同时间段执行同一请求可能得到不同结果。这个测试用来验证缓存是否有时效性。

#### 操作协议

**选择的模型**：MiniMax-M2.7

**选择的任务**：BE-01（A 变体 only）

**执行方式**：
1. **T0**：执行 BE-01_A prompt，记录输出 hash
2. **T0 + 30min**：在新会话中执行完全相同的 prompt，记录输出 hash
3. **T0 + 60min**：再次在新会话中执行，记录输出 hash
4. **T0 + 24h**（如果前三次都相同）：次日执行

**同时做对照**：对 FE-01_A 做同样的时间间隔测试（FE 域在 Pilot 中独立，如果时间间隔测试也独立，则确认 FE 域的独立性不是缓存行为）

| 时间点 | 模型 | 任务变体 | 用途 |
|--------|------|---------|------|
| T0 | MiniMax-M2.7 | BE-01_A | 基线 |
| T0+30min | MiniMax-M2.7 | BE-01_A | 对比 |
| T0+60min | MiniMax-M2.7 | BE-01_A | 对比 |
| T0 | MiniMax-M2.7 | FE-01_A | 对照基线 |
| T0+30min | MiniMax-M2.7 | FE-01_A | 对照对比 |
| T0+60min | MiniMax-M2.7 | FE-01_A | 对照对比 |
| T0 | Kimi-K2.5 | BE-01_A | 验证 |
| T0+30min | Kimi-K2.5 | BE-01_A | 验证 |
| **合计** | | | **16 次**（含对照） |

#### 判定标准

| 结果 | 判定 |
|------|------|
| T0 和 T0+30min 输出不同 | **H2 强支持**：缓存有 TTL，失效后产出不同 |
| 所有时间点输出完全相同 | **H2 弱化**：即使有缓存也是长期的，或缓存不是主因 |
| BE-01 全相同但 FE-01 全不同 | 确认 FE 独立性是真实的模型行为 |

---

### 2.4 B3：约束矛盾测试

#### 设计原理

如果模型忽略了 Header（只看需求描述），那么当 Header 和描述中包含矛盾约束时，模型会遵循描述而非 Header。这个测试用来确认模型是否真正阅读了 Header。

#### 操作协议

**构造方式**：为 BE-01 和 PY-01 各设计一个矛盾版本：

**BE-01 矛盾版（C 变体模板）**：
```
[L]Python [F]Flask [S]N/A [D]flask_only [O]single_file [OUT]code_only
Build a FastAPI health-check endpoint at GET /health returning {"status": "ok"}.
```

注意：Header 说 `[F]Flask`，但描述说 `FastAPI`。如果模型遵循 Header → 用 Flask；如果模型遵循描述 → 用 FastAPI。

**PY-01 矛盾版（C 变体模板）**：
```
[L]Python [D]pandas_allowed [O]function [OUT]code_only
Write a CSV parser using only the built-in csv module. Do not use pandas.
```

注意：Header 说 `[D]pandas_allowed`，但描述说 `Do not use pandas`。

**执行矩阵**：

| 模型 | 任务 | 变体 | 矛盾方向 | 生成次数 |
|------|------|------|---------|---------|
| MiniMax-M2.7 | BE-01_conflict | C | Header=Flask, Desc=FastAPI | 1 |
| MiniMax-M2.7 | PY-01_conflict | C | Header=pandas_ok, Desc=no_pandas | 1 |
| Kimi-K2.5 | BE-01_conflict | C | Header=Flask, Desc=FastAPI | 1 |
| Kimi-K2.5 | PY-01_conflict | C | Header=pandas_ok, Desc=no_pandas | 1 |
| GLM-5.0 | BE-01_conflict | C | Header=Flask, Desc=FastAPI | 1 |
| GLM-5.0 | PY-01_conflict | C | Header=pandas_ok, Desc=no_pandas | 1 |
| Claude-Opus-4.6 | BE-01_conflict | C | Header=Flask, Desc=FastAPI | 1 |
| Claude-Opus-4.6 | PY-01_conflict | C | Header=pandas_ok, Desc=no_pandas | 1 |
| **合计** | | | | **8 次** |

同时做**无矛盾对照**（正常 C 变体 prompt），验证矛盾引入确实造成了行为变化：

| 模型 | 任务 | 变体 | 矛盾 | 生成次数 |
|------|------|------|------|---------|
| 同上 4 模型 | BE-01/PY-01 | C | ❌ 无矛盾 | 8 |
| **合计** | | | | **8 次对照** |

**总计 B3：16 次**

#### 判定标准

| 结果 | 判定 |
|------|------|
| 模型遵循 Header（Flask / 用 pandas） | **模型阅读了 Header**，H3 排除 |
| 模型遵循描述（FastAPI / 不用 pandas） | **模型忽略了 Header**，H3 成立 |
| 模型产出混合（如用 FastAPI 但导入了 pandas） | 模型部分阅读 Header，需逐案分析 |
| 克隆模型和非克隆模型在矛盾测试中表现不同 | 说明克隆与 Header 阅读能力有关 |

#### 重要：分析时需注意

Claude-Opus-4.6 是**非克隆模型的阳性对照**——如果 Opus 也遵循描述而非 Header，说明是 Compact Header 格式本身的问题（描述优先级 > Header 优先级），而非模型是否克隆。

---

### 2.5 B4：进阶任务克隆对比

#### 设计原理

EXP-A 的进阶任务如果在之前克隆的模型（Kimi-K2.5）上不再克隆，则 H1 成立。

#### 操作协议

**无需额外执行**——直接使用 EXP-A 中 Kimi-K2.5 的数据（BE-05~08, PY-05~08 × 4 变体 = 32 个文件），检查 R12 FLAG 率。

#### 判定标准

| Kimi 在 EXP-A 中的克隆率 | 判定 |
|-------------------------|------|
| 0%（全独立） | **H1 强支持**：Pilot 克隆确因任务太简单 |
| 50%（部分克隆） | H1 部分成立，可能还有其他因素 |
| 100%（全克隆） | **H1 排除**：不是任务简单的问题，是模型/平台行为 |

---

## 三、执行标准

### 3.1 会话隔离（严格要求）

**每个生成必须在独立的新会话中执行**。这是克隆排除实验的核心控制：

- 新建聊天会话 → 投递 prompt → 取结果 → 关闭会话
- **禁止**在同一会话中连续投递 A/B/C/D 四个变体
- **禁止**在同一会话中先投递无 seed 版再投递有 seed 版

### 3.2 时间记录

每次生成需记录：
- 精确执行时间（ISO 8601，精确到秒）
- 会话 ID（如平台可见）
- 是否在新会话中执行（手动确认）

### 3.3 产物保存

```
v2/experiments/EXP_B/
├── B1_seed/
│   ├── {model}/
│   │   ├── seed/{task}_{variant}.py        # 有 seed 版本
│   │   └── no_seed/{task}_{variant}.py     # 无 seed 版本（重跑）
│   └── hashes.json                          # 所有文件的 SHA256 hash
├── B2_interval/
│   ├── {model}/
│   │   ├── T0/{task}_{variant}.py
│   │   ├── T30/{task}_{variant}.py
│   │   └── T60/{task}_{variant}.py
│   └── hashes.json
├── B3_conflict/
│   ├── {model}/
│   │   ├── conflict/{task}_conflict_C.py    # 矛盾版本
│   │   └── control/{task}_C.py              # 无矛盾对照
│   └── analysis.json                        # 逐文件判定：遵循 Header / 遵循描述
└── EXP_B_RESULTS.md                         # 综合分析报告
```

---

## 四、分析协议

### 4.1 B1 分析

1. 对每个 (model, task, variant)，计算 seed 版和 no_seed 版的 SHA256 hash
2. 对每个 (model, task)，比较四个变体的 hash 是否全相同
3. 输出矩阵：

```
        | Seed A | Seed B | Seed C | Seed D | NoSeed A | NoSeed B | NoSeed C | NoSeed D |
BE-01   | hash1  | hash2  | hash3  | hash4  | hash5    | hash6    | hash7    | hash8    |
```

4. 判定逻辑：
   - 如果 NoSeed 全相同但 Seed 全不同 → 缓存
   - 如果 Seed 和 NoSeed 都全相同 → 模型行为
   - 如果 Seed 和 NoSeed 都全不同 → 模型每次都产出不同结果（高随机性）

### 4.2 B2 分析

1. 对同一 (model, task, variant)，比较 T0/T30/T60 的 hash
2. 计算"稳定性分数"：3 次中 unique hash 的数量（1 = 完全稳定，3 = 完全随机）

### 4.3 B3 分析

1. 对每个矛盾测试产出，人工判定模型遵循了哪一方：
   - `import flask` → 遵循 Header
   - `from fastapi import` → 遵循描述
   - `import pandas` → 遵循 Header
   - 无 pandas import → 遵循描述
2. 汇总为矩阵：

```
              | BE-01 (Header=Flask, Desc=FastAPI) | PY-01 (Header=pandas, Desc=no_pandas) |
MiniMax-M2.7  | 遵循描述                           | 遵循描述                               |
Kimi-K2.5     | 遵循描述                           | 遵循描述                               |
Opus-4.6      | 遵循Header                         | 遵循Header                             |
```

### 4.4 综合判定矩阵

| B1 结果 | B2 结果 | B3 结果 | B4 结果 | 最终判定 |
|---------|---------|---------|---------|---------|
| Seed 变了 | T30 变了 | — | — | **H2 确认：平台缓存** |
| Seed 没变 | T30 没变 | 遵循描述 | 仍克隆 | **H3 确认：模型忽略 Header** |
| Seed 没变 | T30 没变 | 遵循 Header | 不克隆 | **H1 确认：任务太简单** |
| Seed 没变 | T30 没变 | 遵循 Header | 仍克隆 | **模型固有行为**（在简单任务上确定性极高） |
| 混合结果 | 混合 | 混合 | 混合 | 多因素叠加，逐模型报告 |

---

## 五、成本估算

| 子实验 | 生成次数 | 模型数 | 预估时间 |
|--------|---------|--------|---------|
| B1 Seed | 32 | 2 | 60 分钟 |
| B2 Interval | 16 | 2 | 120 分钟（含等待间隔） |
| B3 Conflict | 16 | 4 | 30 分钟 |
| B4 | 0（附带 EXP-A） | 0 | 0 |
| **总计** | **64** | — | **约 3.5 小时** |

---

## 六、风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| WorkBuddy 平台无可见的会话 ID | 高 | 无法确认缓存机制 | 用时间戳 + seed 作为代理标识 |
| B1 结果不明确（部分变但部分不变） | 中 | 无法干净地确认/排除 H2 | 增加 seed 测试的 repeat 次数（改为 3 轮） |
| 矛盾测试中模型报错或拒绝生成 | 低 | B3 失效 | 准备备选矛盾对（如 Header=Express vs Desc=FastAPI） |
| B4 中 EXP-A 尚未执行 | 确定 | B4 数据缺失 | B4 等 EXP-A 完成后附带分析，不阻塞 B1/B2/B3 |

---

## 七、执行优先级与依赖

```
B1 (Seed) ─────→ ┐
B2 (Interval) ──→ ├→ 综合分析 → EXP_B_RESULTS.md
B3 (Conflict) ──→ ┘
EXP-A ──→ B4 (Clone Compare) ──→ 补充到综合分析
```

- B1、B2、B3 **可并行执行**（无相互依赖）
- B4 **依赖 EXP-A 完成**
- 综合分析在 B1+B2+B3 全部完成后执行，B4 结果后续补充

---

## 八、论文中的定位

无论 EXP-B 的结论如何，都在论文中以下位置使用：

| 论文章节 | 使用方式 |
|---------|---------|
| §4 Methodology → Threats | "为排除平台缓存对实验结果的影响，我们设计了 EXP-B..." |
| §5 Results → 克隆现象 | 报告 B1/B2/B3 的结果和最终判定 |
| §6 Discussion | 讨论克隆现象对 prompt variant comparison 的影响及处理方式 |
| §7 Limitations | 如果 H2 成立，声明平台中间层对实验的影响 |

---

*设计时间：2026-03-31 21:42 CST*  
*状态：待用户确认后执行*
