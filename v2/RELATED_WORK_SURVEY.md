# CodePrompt-DSL v2 Related Work 调研报告

> **调研时间**：2026-03-31  
> **调研范围**：2024–2026 年，涉及 Prompt 压缩/格式/编码对代码生成影响的论文  
> **目的**：确认是否有人做过类似 benchmark，以及我们的定位在现有文献中的空白

---

## 一、核心结论

**好消息：没有人做过和你完全一样的事。**

具体来说：

- 没有人专门研究过"**用紧凑 DSL Header 压缩显式工程约束**"对代码生成的影响
- 没有人做过"**NL vs JSON vs Compact Header vs 古文**"的四组 prompt 变体对比
- 没有人在"**前端 + 后端 + Python**"三类任务上做过 prompt 编码方式的跨域对比
- "**古文/高密度中文编码作为 tokenizer 经济学负对照**"这个角度是独特的

**但有几篇相关工作你必须在论文里引用和讨论**，否则 reviewer 会觉得你没做文献调研。

---

## 二、最相关的 6 篇论文

### 论文 1（最相关 ⭐⭐⭐⭐⭐）
**"Does Prompt Formatting Have Any Impact on LLM Performance?"**  
Microsoft & MIT, 2024.11 | arXiv:2411.10541

| 维度 | 内容 |
|------|------|
| 做了什么 | 测试了 Plain text / Markdown / JSON / YAML 四种 prompt 格式对 LLM 表现的影响 |
| 涉及代码生成 | ✅ 有，包含代码翻译任务 |
| 涉及 token 成本 | ❌ 没有 |
| 核心发现 | 小模型（GPT-3.5）对格式非常敏感（最高 40% 差异）；大模型（GPT-4）更鲁棒 |
| 和我们的关系 | **高度相关**。他们测了格式差异，但没有测"紧凑压缩"的成本收益。我们的 C 组（Compact Header）是他们没有涵盖的变体。我们可以说："他们证明了格式 matters，我们进一步问：如果把格式压缩到极致，成本和准确度之间的权衡是什么？" |
| 引用必要性 | **必须引用** |

### 论文 2（很相关 ⭐⭐⭐⭐）
**"The Impact of Prompt Programming on Function-Level Code Generation"**  
TSE 2025 (accepted) | arXiv:2412.20545

| 维度 | 内容 |
|------|------|
| 做了什么 | 建了 **CodePromptEval** 数据集（7072 个 prompt），测试了 few-shot / persona / chain-of-thought / 函数签名 / 包列表 5 种 prompt 技术对代码生成的影响 |
| 模型 | GPT-4o, Llama3, Mistral |
| 核心发现 | 不同 prompt 技术有显著影响；多技术组合不一定更好；正确性和质量之间存在权衡 |
| 和我们的关系 | **方法论相关**。他们做的是 prompt 技术（few-shot、CoT 等），我们做的是 prompt 编码格式（NL vs DSL vs JSON）。两者互补，不冲突。我们可以说："他们研究了 prompt 内容的技术选择，我们研究的是 prompt 中工程约束部分的编码压缩。" |
| 引用必要性 | **应该引用** |

### 论文 3（很相关 ⭐⭐⭐⭐）
**"Compression Method Matters: Benchmark-Dependent Output Dynamics in LLM Prompt Compression"**  
Warren Johnson, 2026.03 | arXiv:2603.23527

| 维度 | 内容 |
|------|------|
| 做了什么 | 5400 次 API 调用，测试 prompt 压缩对不同 benchmark（包括 MBPP、HumanEval）的影响 |
| 核心发现 | 压缩效果高度依赖 benchmark；DeepSeek 在 MBPP 上压缩后输出膨胀 56 倍，但 HumanEval 上只有 5 倍；提出了"指令存活概率"(Ψ) 和"压缩稳健性指数"(CRI) |
| 和我们的关系 | **非常相关但角度不同**。他们研究的是"自动压缩"（token-level truncation），我们研究的是"人为设计的紧凑编码"（hand-crafted compact header）。我们可以说："他们的自动压缩方法有指令丢失风险（Ψ 问题），而我们的方法是手工设计的等价表达，理论上 Ψ=1（所有约束都被保留，只是换了写法）。" |
| 引用必要性 | **必须引用** |

### 论文 4（相关 ⭐⭐⭐）
**"More Than a Score: Probing the Impact of Prompt Specificity on LLM Code Generation"**  
PartialOrderEval, 2025.08 | arXiv:2508.03678

| 维度 | 内容 |
|------|------|
| 做了什么 | 提出 PartialOrderEval 框架，研究 prompt 的"具体程度"（从最简到最详细）对代码生成 Pass@1 的影响 |
| 基准 | HumanEval, ParEval |
| 核心发现 | 提高 prompt 具体性通常提升性能；显式 I/O 规范、边界情况、逐步分解是关键 |
| 和我们的关系 | **角度互补**。他们研究的是 prompt 的"详细程度"（从少到多），我们研究的是"同等信息量下的编码效率"（同样的约束，NL 写法 vs 压缩写法）。我们的问题不是"写多少"，而是"同样的信息能不能写得更短"。 |
| 引用必要性 | **建议引用** |

### 论文 5（背景相关 ⭐⭐⭐）
**"AutoDSL: Automated Domain-Specific Language Design for Structural Representation of Procedures with Constraints"**  
ACL 2024 | aclanthology.org/2024.acl-long.659

| 维度 | 内容 |
|------|------|
| 做了什么 | 自动从语料库中推导出 DSL 语法和语义，用于结构化表示带约束的程序 |
| 核心发现 | DSL 作为约束的形式化表示，可以辅助 LLM 的程序规划 |
| 和我们的关系 | **概念相关但应用场景不同**。他们的 DSL 是自动生成的、用于程序规划的中间表示；我们的 DSL 是手工设计的、用于 prompt 输入端的约束压缩。方向不同，但"DSL 作为 LLM 的结构化约束工具"这个概念是共享的。 |
| 引用必要性 | **建议引用**（作为 DSL + LLM 的背景） |

### 论文 6（背景相关 ⭐⭐）
**"Prompt Compression for Large Language Models: A Survey"**  
NAACL 2025 | arXiv:2410.12388

| 维度 | 内容 |
|------|------|
| 做了什么 | 综述了 prompt 压缩技术：hard prompt（删词/摘要）和 soft prompt（向量压缩） |
| 和我们的关系 | **作为背景综述引用**。我们的方法属于"hard prompt"大类，但不是"自动删词"，而是"手工等价重编码"。可以在 Related Work 里说："现有压缩方法主要是自动化的（LLMLingua、Selective Context 等），我们探索的是一种互补的手工编码方案。" |
| 引用必要性 | **应该引用**（综述类） |

---

## 三、现有文献的空白——我们的定位

整理下来，现有工作的分布是这样的：

```
             自动压缩 ←────────→ 手工编码
                 │                   │
  LLMLingua      │    ← 空白 →      │  CodePrompt-DSL (ours)
  Selective Ctx  │                   │
  2603.23527     │                   │
                 │                   │
         ─── 通用 NLP ─────── 代码生成 ───
                 │                   │
  2410.12388综述 │                   │  2411.10541 (格式)
                 │                   │  2412.20545 (技术)
                 │                   │  2508.03678 (具体性)
```

**我们独占的空白位置**：

1. **手工设计的等价压缩编码**——不是自动删词，是人为设计的紧凑 Header
2. **专门针对工程约束**——不是压缩整个 prompt，是只压缩"闭集显式约束"部分
3. **跨编码风格对比**——NL / JSON / Compact / Classical 四组
4. **跨任务域**——前端 + 后端 + Python（如果 v2 做到的话）
5. **跨模型 tier**——Lite / Mid / Pro 分层分析
6. **古文作为 tokenizer 经济学负对照**——这个角度完全没人做过

---

## 四、对 v2 设计的直接启示

### 4.1 必须在 Related Work 里讨论的对比

| 我们的方法 vs | 关键区别 | 我们的优势叙事 |
|--------------|---------|---------------|
| 自动压缩（LLMLingua 等） | 自动删词 vs 手工等价重编码 | 我们的方法 Ψ=1（约束信息零丢失） |
| 格式对比（2411.10541） | 他们测格式，没测成本 | 我们同时测格式 + token 成本 + 成功率 |
| Prompt 技术（2412.20545） | 他们测 few-shot/CoT 等内容技术 | 我们测约束部分的编码形式 |
| Prompt 具体性（2508.03678） | 他们测"写多少信息" | 我们测"同等信息下能否更紧凑" |
| AutoDSL（ACL 2024） | 他们自动设计 DSL 用于程序规划 | 我们手工设计 DSL 用于 prompt 输入端约束压缩 |

### 4.2 可以直接借鉴的

1. **CodePromptEval 的评估维度**（正确性 / 相似性 / 质量三维）——可以参考，但我们的 Pass@1 更简洁
2. **Compression Method Matters 的 Ψ 和 CRI 指标**——我们可以引用 Ψ 概念来论证 compact header 的优势：手工编码 Ψ=1
3. **PartialOrderEval 的 specificity 梯度思路**——如果我们想做"不同压缩程度"的梯度实验，可以参考

### 4.3 不需要担心的

- **没有人做过完全一样的 benchmark**——所以你不会遇到"别人已经做了，你在重复"的质疑
- **古文角度没有人碰过**——这是独特卖点，但要注意不要把它写成主贡献，而是写成"负对照 + tokenizer 经济学探针"

---

## 五、建议的 Related Work 章节结构

```
2. Related Work

2.1 Prompt Engineering for Code Generation
    - CodePromptEval (2412.20545): prompt 技术对代码生成的影响
    - PartialOrderEval (2508.03678): prompt 具体性与代码质量
    - SCoT (ACL 2025): 结构化 CoT 对代码生成的影响

2.2 Prompt Compression
    - Prompt Compression Survey (2410.12388): hard/soft prompt 压缩方法综述
    - Compression Method Matters (2603.23527): 压缩的 benchmark 依赖性
    - 我们的定位：不是自动压缩，而是手工等价重编码

2.3 Prompt Format and Structured Specification
    - Does Prompt Formatting Matter (2411.10541): 格式对 LLM 的影响
    - AutoDSL (ACL 2024): DSL 作为 LLM 约束的结构化表示
    - 我们的定位：专门针对代码生成中的显式工程约束

2.4 Code Generation Benchmarks
    - HumanEval / MBPP / HumanEval Pro
    - 我们的定位：不是新的代码能力 benchmark，
      而是评估"同一代码任务在不同 prompt 编码下的成功率和成本"
```

---

*调研完成时间：2026-03-31 10:37*
