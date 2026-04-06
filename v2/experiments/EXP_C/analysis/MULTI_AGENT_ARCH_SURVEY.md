# Multi-Agent 架构调研 Memo

> 日期: 2026-04-03  
> 目的: 评估 EXP-C 线性链设计的外部效度，了解主流多 agent 架构

---

## 1. 主流架构分类

### A. Blackboard (共享画布) 架构

**代表**: LbMAS (Han & Zhang, 2025, arXiv:2507.01701)

```
     ┌──────────────────────────┐
     │       BLACKBOARD          │
     │  (公共空间 + 私有空间)      │
     │  所有 agent 读写同一个画布   │
     └──┬───┬───┬───┬───┬──────┘
        │   │   │   │   │
       A1  A2  A3  A4  A5  (任意数量 agent)
```

**核心机制**:
- 所有 agent 通过共享 blackboard 通信，**无点对点直连**
- 每个被选中的 agent 接收**整个 blackboard 的完整内容**作为 prompt
- 控制单元 (也是 LLM) 动态决定下一步谁行动
- 移除了 agent 独立内存，blackboard 就是唯一状态存储
- **约束传播方式**: 约束写入 blackboard → 所有 agent 都能看到

### B. 并行隔离 (Parallel Isolated) 架构

**代表**: Cursor 2.0 (2025-10)

```
  User Prompt
      │
      ├──→ Agent 1 (独立 git worktree)
      ├──→ Agent 2 (独立 git worktree)
      ├──→ ... (最多 8 个)
      └──→ Agent N
              │
         Aggregated Diff → 用户选择/合并
```

**核心机制**:
- 最多 8 个 agent 并行，每个在隔离环境中独立工作
- **不共享状态**，不通信
- 完成后通过 diff 对比合并
- 本质是 "多方案竞选"，不是协作

### C. Orchestrator-Worker 架构

**代表**: CrewAI, LangGraph

```
  Orchestrator (状态图/DAG)
      │
      ├──→ Worker A (角色: 研究员)
      ├──→ Worker B (角色: 开发者)
      └──→ Worker C (角色: 审核员)
           ↑
     共享的 State Graph / Message Queue
```

**核心机制**:
- Orchestrator 定义工作流（DAG/状态机）
- Worker 按编排顺序或条件执行
- 通过共享 state 或消息传递通信
- **CrewAI**: 角色驱动，支持顺序/并行/层级
- **LangGraph**: 状态图驱动，节点是 agent，边是状态转移

### D. 单 Agent 闭环 (Single Agent Loop)

**代表**: Copilot Agent, Windsurf/Cascade, 当前多数工具

```
  Agent ←→ 环境 (代码库/终端/浏览器)
    ↻ 分析→执行→验证→修复循环
```

**现实**: 截至 2025-2026，**绝大多数工业级代码生成工具仍是单 agent**。Copilot、Cursor (非2.0)、Windsurf 的 Cascade 都是单 agent 闭环。

---

## 2. 关键数据点

### 多 agent 的 token 成本
- UIUC 研究: 多 agent 消耗 **4-220×** 单 agent 的 token
- Anthropic 生产数据: agent ≈ 4× chat; multi-agent ≈ **15× chat**
- SWE-bench: 单 agent 48K tokens vs 多 agent 193K-10.6M tokens

### 多 agent 的性能
- **可并行任务**: 多 agent +81% (Google Research)
- **顺序任务**: 多 agent **-70%** (Google Research)
- **广度优先研究**: Opus+Sonnet multi-agent +90.2% (Anthropic)

---

## 3. 对 EXP-C 实验设计的评估

### 我们的设计

```
A (Architect) → B (Implementer) → C (Auditor)
每个 stage 都注入完整原始约束
```

### 与主流架构的对比

| 维度 | EXP-C | Blackboard | Cursor 2.0 | CrewAI/LangGraph | 现实工具 |
|------|-------|-----------|-----------|-----------------|---------|
| 拓扑 | 线性链 | 共享画布 | 并行隔离 | DAG/状态图 | 单 agent 循环 |
| 约束传递 | 每 stage copy-paste | 写入 blackboard，全员可见 | 每个 agent 独立拿到 | 通过 state 传递 | 在 prompt 或 rules 中 |
| Agent 间通信 | 无 (上游 output → 下游 input) | 全通过 blackboard | 无 (隔离) | 有 (state/message) | 无 (单 agent) |
| 是否模拟了真实场景 | ❌ 过于简化 | ✅ 前沿学术 | ✅ 工业前沿 | ✅ 开发框架主流 | ⚠️ 我们多了 agent |

### 核心问题

1. **约束注入方式不现实**: 我们在每个 stage 都 copy-paste 了原始约束。Blackboard 架构中约束也是全员可见的（写在 blackboard 上），但 blackboard 上的约束会被其他 agent 的 output 稀释——因为 blackboard 内容不断增长，约束信息的相对占比递减。

2. **线性链不是主流**: 学术前沿是 blackboard，工业前沿是并行隔离 (Cursor 2.0) 或单 agent 闭环。纯线性 A→B→C 在实践中没有代表性。

3. **但我们的发现仍有价值**:
   - Token 节省 ~25-30% 在**任何架构**下都成立（只要约束文本被注入 prompt）
   - Naturalization 现象在 blackboard 架构中更值得关注（因为所有 agent 读同一个画布）
   - 反直觉约束的系统性失败与架构无关（是模型能力问题）

---

## 4. 如果要做改进实验 (Future Work 建议)

### 最有价值的实验: Blackboard 架构模拟

```
Blackboard = shared markdown document
Agent A (Architect): 读 blackboard → 写入技术方案 → 约束以何种形式出现在方案中？
Agent B (Implementer): 读 blackboard（包含 A 的方案）→ 写入代码
                       注意: B 的 prompt 不再注入原始约束
                       B 只能从 blackboard 内容中理解约束
Agent C (Auditor): 读 blackboard（包含 A 方案 + B 代码）→ 写入审查
```

**关键变化**: 约束只在 A 的初始 prompt 中出现一次，后续 agent 必须从 blackboard 的累积内容中推断约束。

**预测**: 在这个设计下，编码方式**可能**会产生显著影响——因为 Header 被 A naturalize 后，B 从 blackboard 读到的约束信息会比 NLf 更弱。

*最后更新: 2026-04-03*
