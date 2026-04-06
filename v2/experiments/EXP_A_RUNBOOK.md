# EXP-A 执行操作手册

> **总任务量**：12 任务 × 4 变体 × 6 模型 = 288 个文件  
> **实际操作量**：24 个会话（每模型 4 个会话，每个会话 12 个任务）  
> **预估总时间**：4-6 小时（视模型响应速度）

---

## 操作流程

每个会话的操作步骤完全相同：

1. 在 WorkBuddy 中**切换到目标模型**
2. **新建对话**
3. 输入以下话术（复制粘贴即可）：

```
请阅读以下指令文档，按照文档中每个任务的 prompt 生成代码，并保存到文档中指定的路径。每个任务生成一个独立文件。
```

4. 然后在同一条消息中，附带指令文件：`@` 引用对应的 `.md` 文件
5. 等待模型完成全部 12 个文件
6. 如果模型中途停了，发送 `继续` 让它完成剩余任务
7. **关闭会话**，开下一个

---

## 24 个会话清单

按建议执行顺序排列（先跑 Pro 层，后跑 Lite 层）：

### 第 1 组：Claude-Opus-4.6（4 个会话）

| # | 模型 | 变体 | 指令文件路径 |
|---|------|------|------------|
| 1 | Claude-Opus-4.6 | A | `v2/experiments/EXP_A_instructions/Claude-Opus-4.6_variant_A.md` |
| 2 | Claude-Opus-4.6 | B | `v2/experiments/EXP_A_instructions/Claude-Opus-4.6_variant_B.md` |
| 3 | Claude-Opus-4.6 | C | `v2/experiments/EXP_A_instructions/Claude-Opus-4.6_variant_C.md` |
| 4 | Claude-Opus-4.6 | D | `v2/experiments/EXP_A_instructions/Claude-Opus-4.6_variant_D.md` |

### 第 2 组：GPT-5.4（4 个会话）

| # | 模型 | 变体 | 指令文件路径 |
|---|------|------|------------|
| 5 | GPT-5.4 | A | `v2/experiments/EXP_A_instructions/GPT-5.4_variant_A.md` |
| 6 | GPT-5.4 | B | `v2/experiments/EXP_A_instructions/GPT-5.4_variant_B.md` |
| 7 | GPT-5.4 | C | `v2/experiments/EXP_A_instructions/GPT-5.4_variant_C.md` |
| 8 | GPT-5.4 | D | `v2/experiments/EXP_A_instructions/GPT-5.4_variant_D.md` |

### 第 3 组：GLM-5.0-Turbo（4 个会话）

| # | 模型 | 变体 | 指令文件路径 |
|---|------|------|------------|
| 9 | GLM-5.0-Turbo | A | `v2/experiments/EXP_A_instructions/GLM-5.0-Turbo_variant_A.md` |
| 10 | GLM-5.0-Turbo | B | `v2/experiments/EXP_A_instructions/GLM-5.0-Turbo_variant_B.md` |
| 11 | GLM-5.0-Turbo | C | `v2/experiments/EXP_A_instructions/GLM-5.0-Turbo_variant_C.md` |
| 12 | GLM-5.0-Turbo | D | `v2/experiments/EXP_A_instructions/GLM-5.0-Turbo_variant_D.md` |

### 第 4 组：Kimi-K2.5（4 个会话）

| # | 模型 | 变体 | 指令文件路径 |
|---|------|------|------------|
| 13 | Kimi-K2.5 | A | `v2/experiments/EXP_A_instructions/Kimi-K2.5_variant_A.md` |
| 14 | Kimi-K2.5 | B | `v2/experiments/EXP_A_instructions/Kimi-K2.5_variant_B.md` |
| 15 | Kimi-K2.5 | C | `v2/experiments/EXP_A_instructions/Kimi-K2.5_variant_C.md` |
| 16 | Kimi-K2.5 | D | `v2/experiments/EXP_A_instructions/Kimi-K2.5_variant_D.md` |

### 第 5 组：DeepSeek-V3.2（4 个会话）

| # | 模型 | 变体 | 指令文件路径 |
|---|------|------|------------|
| 17 | DeepSeek-V3.2 | A | `v2/experiments/EXP_A_instructions/DeepSeek-V3.2_variant_A.md` |
| 18 | DeepSeek-V3.2 | B | `v2/experiments/EXP_A_instructions/DeepSeek-V3.2_variant_B.md` |
| 19 | DeepSeek-V3.2 | C | `v2/experiments/EXP_A_instructions/DeepSeek-V3.2_variant_C.md` |
| 20 | DeepSeek-V3.2 | D | `v2/experiments/EXP_A_instructions/DeepSeek-V3.2_variant_D.md` |

### 第 6 组：Gemini-3.1-flash-lite（4 个会话）

| # | 模型 | 变体 | 指令文件路径 |
|---|------|------|------------|
| 21 | Gemini-3.1-flash-lite | A | `v2/experiments/EXP_A_instructions/Gemini-3.1-flash-lite_variant_A.md` |
| 22 | Gemini-3.1-flash-lite | B | `v2/experiments/EXP_A_instructions/Gemini-3.1-flash-lite_variant_B.md` |
| 23 | Gemini-3.1-flash-lite | C | `v2/experiments/EXP_A_instructions/Gemini-3.1-flash-lite_variant_C.md` |
| 24 | Gemini-3.1-flash-lite | D | `v2/experiments/EXP_A_instructions/Gemini-3.1-flash-lite_variant_D.md` |

---

## 进度追踪

每完成一组（4 个会话），回到主对话（与砚的对话）报告：
- "第 X 组完成"
- 如有异常（模型拒绝、部分文件未生成、生成了错误格式的文件等），一并说明

砚会：
1. 检查产物完整性（12 个文件 × 4 变体 = 48 个文件/模型）
2. 执行交叉审查
3. 更新分析数据

---

## 常见问题

**Q: 模型没有生成文件怎么办？**  
A: 有些模型会直接在聊天中输出代码而不是创建文件。追问一句"请把代码保存到指定路径"即可。

**Q: 模型只完成了部分任务就停了？**  
A: 发送"继续完成剩余任务"让它继续。

**Q: 模型修改了工作记忆或其他文件？**  
A: 无需担心，砚会在审查时清理。

**Q: 可以暂停后继续吗？**  
A: 可以。每个会话是独立的，你可以跑完一组后休息，下次继续。

---

*生成时间：2026-03-31 22:55 CST*
