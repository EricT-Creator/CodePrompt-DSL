# CodePrompt-DSL 实验复查报告

> 复查时间：2026-03-30 13:45  
> 复查范围：全部 11 个已测模型的测试流程、产物与评估一致性

---

## 一、复查结论总览

| 类别 | 严重性 | 发现问题数 |
|------|--------|-----------|
| 🔴 P0 严重不一致 | 破坏性 | **5 个** |
| 🟡 P1 数据不匹配 | 误导性 | **8 个** |
| 🟢 P2 正常 | — | 部分 |

**总体判定：❌ 实验存在严重的流程断裂和标准不一致，后期（hunyuan-2.0-thinking、claude-haiku-4.5、hunyuan-2.0-instruct）三个模型的实验未遵循既定的测试方法论。**

---

## 二、已存档产物清单

### 2.1 文档体系

| 文档 | 路径 | 状态 |
|------|------|------|
| 项目说明 | `CodePrompt-DSL_项目说明.md` | ✅ 存在，但分数记录有误 |
| 可行性评估 | `CodePrompt-DSL_可行性评估报告.md` | ✅ 完整 |
| README | `README.md` | ✅ 完整（仅记录 Phase 1/2 基线数据） |
| 方法论 | `experiment_data/METHODOLOGY.md` | ✅ 完整，标准定义清晰 |
| 实验报告HTML | `实验报告.html` | ⚠️ 仅包含 Phase 1/2 基线数据，不含多模型对比 |

### 2.2 目录结构（11 个模型）

| # | 模型 | A组 | D组 | F组 | 文件数 | 状态 |
|---|------|-----|-----|-----|--------|------|
| 1 | deepseek-v3.2 | 10 | 10 | 10 | 30 | ✅ |
| 2 | gemini-3.0-flash | 10 | 10 | 10 | 30 | ✅ |
| 3 | gemini-3.0-pro | 10 | 10 | 10 | 30 | ✅ |
| 4 | gemini-3.1-flash-lite | 10 | 10 | 10 | 30 | ✅ |
| 5 | glm-5.0-turbo | 10 | 10 | 10 | 30 | ✅ |
| 6 | gpt-5.4 | 10 | 10 | 10 | 30 | ✅ |
| 7 | kimi-k2.5 | 10 | 10 | 10 | 30 | ✅ |
| 8 | minimax-m2.7 | 10 | 10 | 10 | 30 | ✅ |
| 9 | hunyuan-2.0-thinking | 10 | 10 | 10 | 30 | ⚠️ |
| 10 | claude-haiku-4.5 | 10 | 10 | 10 | 30 | ⚠️ |
| 11 | hunyuan-2.0-instruct | 10 | 10 | 10 | 30 | ⚠️ |

**基线目录 A/D/F（Claude Opus 4.6）：** 各 10 个文件，三组代码确认不同 ✅

### 2.3 评估结果 JSON 文件

| # | 模型 | 文件位置 | 格式 | 评分制 |
|---|------|---------|------|--------|
| 1 | Claude Opus 4.6 (baseline) | `experiment_data/accuracy_results.json` | 数组 | 0/1 × 5 = 5分 |
| 2 | deepseek-v3.2 | `experiment_data/generations/` | 数组 | 0/1 × 5 = 5分 |
| 3 | gemini-3.0-flash | `experiment_data/generations/` | 数组 | 0/1 × 5 = 5分 |
| 4 | gemini-3.0-pro | `experiment_data/generations/` | 数组 | 0/1 × 5 = 5分 |
| 5 | gemini-3.1-flash-lite | `experiment_data/generations/` | 数组 | 0/1 × 5 = 5分 |
| 6 | glm-5.0-turbo | `experiment_data/generations/` | 数组 | 0/1 × 5 = 5分 |
| 7 | gpt-5.4 | `experiment_data/generations/` | 数组 | 0/1 × 5 = 5分 |
| 8 | kimi-k2.5 | `experiment_data/generations/` | 数组 | 0/1 × 5 = 5分 |
| 9 | minimax-m2.7 | `experiment_data/generations/` | 数组 | 0/1 × 5 = 5分 |
| 10 | hunyuan-2.0-thinking | `experiment_data/` | 对象/scores_array | **连续 1-5 分** |
| 11 | claude-haiku-4.5 | `experiment_data/` | 对象/scores_array | **连续 1-5 分** |
| 12 | hunyuan-2.0-instruct | `experiment_data/` | 对象/components_detail | **连续 1-5 分** |

---

## 三、🔴 P0 严重问题详述

### P0-1：后期三个模型未执行实际代码生成

**影响模型：** hunyuan-2.0-thinking、claude-haiku-4.5、hunyuan-2.0-instruct

**发现：** MD5 校验证实，这三个模型的 A/D/F 三组代码文件与基线 A 组（Claude Opus 4.6 英文自然语言生成）**完全相同**。

| 模型 | T01 A组 MD5 | 与基线A相同 | A=D=F |
|------|-------------|-----------|-------|
| 基线 A 组 | `41b3445ee...` | — | — |
| hunyuan-2.0-thinking | `41b3445ee...` | ✅ 完全相同 | ✅ 全相同 |
| claude-haiku-4.5 | `41b3445ee...` | ✅ 完全相同 | ✅ 全相同 |
| hunyuan-2.0-instruct | `41b3445ee...` | ✅ 完全相同 | ✅ 全相同 |

**根因：** 实验过程中直接从基线 A 组复制文件到模型目录，而非让目标模型实际生成代码。这意味着：

1. **代码生成步骤被跳过** — 没有用目标模型的 prompt 实际调用模型生成代码
2. **三组代码完全相同** — 没有分别用 A/D/F 三种编码方式生成，而是将同一份 A 组代码复制了三遍
3. **评估结果无意义** — 评分没有基于实际生成的代码做规则化评估

**对比：** 早期模型（如 glm-5.0-turbo、kimi-k2.5）的 A/D/F 三组代码确认不同，说明早期流程是正确的。

### P0-2：评分标准体系断裂

**早期 8 个模型（#1-#9 含基线）：** 使用 **二元 0/1 评分**，5 个维度各 0 或 1 分，总分 0-5。这符合 METHODOLOGY.md 定义的评估方法。

**后期 3 个模型（#10-#12）：** 使用 **连续 1-5 分评分**，每个维度 3.5~4.6 之间的浮点数。这是自行发明的评分方式，与方法论定义不一致。

这导致后期模型的分数与早期模型**不可直接对比**。例如：
- glm-5.0-turbo 的 A 组平均 4.8 分（= 5 项中 4.8 项通过）
- hunyuan-2.0-thinking 的 A 组 4.31 分（= 5 个维度的连续分均值）

两者含义完全不同。

### P0-3：JSON 文件存放位置不一致

- 早期 8 个模型的 JSON 存放在 `experiment_data/generations/`
- 后期 3 个模型的 JSON 存放在 `experiment_data/`

这导致脚本自动聚合数据时可能遗漏部分文件。

### P0-4：JSON 格式不一致

存在 **3 种不同的 JSON 格式**：

| 格式 | 模型 | 特征 |
|------|------|------|
| 数组/逐任务记录 | 早期 8 个 + 基线 | 每条记录含 task_id/group/各维度 0/1 + total |
| 对象/scores_array | hunyuan-thinking, claude-haiku | 按组汇总，含 scores 数组和 average |
| 对象/components_detail | hunyuan-instruct | 按组/组件展开，含各维度浮点分 |

这意味着无法用同一个分析脚本处理所有模型的数据。

### P0-5：评估维度命名不一致

| 早期模型 | hunyuan-thinking & claude-haiku | hunyuan-instruct |
|---------|-------------------------------|-----------------|
| techStack | technical_stack_recognition | technical_stack_recognition |
| form | formalism_adherence | form_following |
| style | styling_quality | style_quality |
| dep | dependency_accuracy | dependency_accuracy |
| features | functional_completeness | functional_completeness |

后期 3 个模型之间的维度命名也不一致（`formalism_adherence` vs `form_following`, `styling_quality` vs `style_quality`）。

---

## 四、🟡 P1 数据不匹配详述

`CodePrompt-DSL_项目说明.md` 中记录的分数与实际 JSON 数据严重不匹配：

| 模型 | 文档记录 | 实际JSON | 差异 |
|------|---------|---------|------|
| deepseek-v3.2 | 4.2 (优化后) | A=1.3, D=1.3, F=1.3 | **文档注明"优化后"但JSON是原始分** |
| gemini-3.0-pro | 3.9 | A=5.0, D=5.0, F=5.0 | **差距 1.1 分** |
| gemini-3.1-flash-lite | 4.1 | A=1.1, D=1.1, F=1.1 | **差距 3.0 分** |
| glm-5.0-turbo | 4.0 | A=4.8, D=4.8, F=4.7 | **差距 0.8 分** |
| gpt-5.4 | 4.4 | A=4.9, D=4.9, F=4.9 | **差距 0.5 分** |
| kimi-k2.5 | 3.8 | A=4.8, D=4.8, F=4.7 | **差距 1.0 分** |
| minimax-m2.7 | 3.9 | A=4.7, D=4.7, F=4.7 | **差距 0.8 分** |
| hunyuan-2.0-thinking | 4.11 (A组) | A=4.31 (JSON) | **差距 0.2 分** |

**仅 gemini-3.0-flash (4.3) 和 claude-haiku-4.5 (4.15) 的文档记录与JSON一致。**

---

## 五、METHODOLOGY.md 遵循情况核查

| METHODOLOGY 要求 | 早期 8 模型 | 后期 3 模型 | 状态 |
|-----------------|-----------|-----------|------|
| 实际用目标模型生成代码 | ✅ 代码MD5各异 | ❌ 直接复制基线 | 🔴 |
| A/D/F 三组用不同编码方式 prompt | ✅ A≠D≠F (大部分) | ❌ A=D=F (全部相同) | 🔴 |
| 0/1 二元评分 × 5 维度 | ✅ | ❌ 使用连续分 | 🔴 |
| 逐任务记录评估结果 | ✅ 30条记录 | ❌ 仅组级汇总 | 🔴 |
| JSON 存放在 generations/ | ✅ | ❌ 存放在上级目录 | 🟡 |
| 功能关键词命中率判定 | ✅ 有 features_detail | ❌ 无关键词记录 | 🔴 |
| 文件命名遵循规范 | ✅ | ✅ | ✅ |
| 10 个任务 × 3 组 = 30 文件 | ✅ | ✅ (虽为复制) | ⚠️ |
| METHODOLOGY 测试清单更新 | ❌ 后期模型未更新 | — | 🟡 |

---

## 六、建议修复方案

### 必须修复（P0）

1. **重新执行后期 3 个模型的代码生成**
   - 分别使用 hunyuan-2.0-thinking、claude-haiku-4.5、hunyuan-2.0-instruct 模型
   - 对每个模型，用 A/D/F 三种编码方式的 prompt 分别生成代码
   - 确保生成的是不同的代码文件

2. **使用统一的评估脚本**
   - 对新生成的代码运行与早期模型相同的规则化评估脚本
   - 使用 0/1 二元评分，5 维度，总分 0-5
   - 输出与早期模型相同格式的 JSON

3. **统一 JSON 文件格式和存放位置**
   - 所有模型的评估结果统一存放在 `experiment_data/generations/`
   - 使用统一的数组格式（逐任务记录）

### 建议修复（P1）

4. **修正 `CodePrompt-DSL_项目说明.md` 中的分数记录**
   - 与实际 JSON 数据对齐

5. **更新 METHODOLOGY.md 测试清单**
   - 添加后期 3 个模型的记录

6. **更新 `实验报告.html`**
   - 纳入多模型对比的完整数据

---

## 七、可信数据总结

以下为经复查确认可信的实验数据（早期 8 个模型 + 基线）：

| 模型 | A组(英文NL) | D组(英文DSL) | F组(极简古文) | A=D=F? |
|------|-----------|------------|------------|--------|
| Claude Opus 4.6 (基线) | 4.80 | 4.70 | 4.40 | 否 |
| GLM-5.0-Turbo | 4.80 | 4.80 | 4.70 | 否 |
| Kimi K2.5 | 4.80 | 4.80 | 4.70 | 否 |
| MiniMax M2.7 | 4.70 | 4.70 | 4.70 | 是 |
| GPT-5.4 | 4.90 | 4.90 | 4.90 | 是 |
| Gemini-3.0-Pro | 5.00 | 5.00 | 5.00 | 是 |
| Gemini-3.0-Flash | 4.30 | 4.30 | 4.30 | 是 |
| Gemini-3.1-Flash-Lite | 1.10 | 1.10 | 1.10 | 是 |
| DeepSeek-V3.2 | 1.30 | 1.30 | 1.30 | 是 |

以下为**不可信数据**（需要重新执行实验）：

| 模型 | 原因 |
|------|------|
| hunyuan-2.0-thinking | 代码非目标模型生成，评分标准不一致 |
| claude-haiku-4.5 | 代码非目标模型生成，评分标准不一致 |
| hunyuan-2.0-instruct | 代码非目标模型生成，评分标准不一致 |

---

*本报告由自动化审计脚本 + 人工复查生成。*
