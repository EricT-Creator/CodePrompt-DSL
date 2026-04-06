# EXP-B3 约束矛盾测试结果

> **执行时间**：2026-03-31 22:33-22:48 CST  
> **执行方式**：用户在独立新会话中投递 prompt，砚归档和判定

---

## 测试矩阵

### BE-01 矛盾测试（Header=[F]Flask, 描述=FastAPI）

| 模型 | 遵循哪方 | 是否识别矛盾 | 具体行为 |
|------|---------|-------------|---------|
| **MiniMax-M2.7** | **描述**（FastAPI） | 未提及 | 默默生成 FastAPI 代码 |
| **Kimi-K2.5** | **描述**（FastAPI） | ✅ 主动识别 | "我会按照你的实际需求（FastAPI）来生成代码，而不是 Flask" |
| **GLM-5.0** | **描述**（FastAPI） | ✅ 主动识别 | "编码说 Flask 但任务要求 FastAPI...按实际任务需求执行" |
| **Claude-Opus-4.6** | **Header**（Flask） | ✅ 主动识别 | "我遵守了 Header（Flask）。如果你确实需要 FastAPI，把 Header 改成 [F]FastAPI" |

### PY-01 矛盾测试（Header=[D]pandas_allowed, 描述=Do not use pandas）

| 模型 | 使用的库 | 判定 |
|------|---------|------|
| MiniMax-M2.7 | csv（内置） | 遵循描述 |
| Kimi-K2.5 | csv（内置） | 遵循描述 |
| GLM-5.0 | csv（内置） | 遵循描述 |
| Claude-Opus-4.6 | csv（内置） | 遵循描述（但 Header 说 "allowed" 不等于 "must use"，矛盾不够尖锐） |

---

## 关键发现

### 发现 B3-1：模型对 Compact Header 的优先级处理存在根本性分歧

- **Claude-Opus-4.6**：Header 优先。当 Header 和描述矛盾时，遵循 Header 的约束
- **Kimi-K2.5 / GLM-5.0 / MiniMax-M2.7**：描述优先。当矛盾出现时，遵循自然语言描述

这对 CodePrompt-DSL 的实用意义是：**Compact Header 在 Claude 上具有真正的约束力，但在其他模型上更像是"参考信息"，描述中的自然语言具有更高优先级。**

### 发现 B3-2：所有被测模型都阅读了 Header

- Kimi 和 GLM 都在回复中明确提到了 Header 的内容并解释了自己的取舍
- 即使 MiniMax 没有明确提及，它生成的代码也正确实现了所有功能
- **H3（模型忽略 Header）被排除**——模型不是没读 Header，而是在矛盾场景下有不同的优先级策略

### 发现 B3-3：PY-01 矛盾设计不够尖锐

`[D]pandas_allowed` 是"允许"而非"必须"，所以用 csv 模块不算违反 Header。BE-01 的 Flask vs FastAPI 矛盾更有效。未来如果需要更尖锐的 PY 矛盾，应改为 `[D]pandas_required`。

---

## 对论文的影响

| 论文位置 | 使用方式 |
|---------|---------|
| §5 Results | 报告模型对 Header 的优先级分歧：Claude 家族 Header-first，其他模型 Description-first |
| §6 Discussion | 这解释了为什么 Compact Header 在所有模型上都"不降低准确度"——因为当 Header 正确编码了需求时，两种策略殊途同归；只有矛盾场景才暴露差异 |
| Contribution | 新增发现：LLM 对结构化约束前缀的优先级处理策略不统一，这是 prompt engineering 实践中需要注意的 |

---

*分析时间：2026-03-31 22:48 CST*
