# CodePrompt-DSL 项目说明

## 项目定位
一个**面向代码生成显式工程约束的紧凑型 Prompt Header 编码实验**。

核心目标：
- 压缩高频重复工程约束
- 降低输入 token 成本
- 不显著降低代码准确度
- 提升约束遵循稳定性

## 核心边界
仅处理**显式约束**：
- LANG / STACK / FORM
- LAYOUT / DEP / OUT
- DATA

不处理隐含意图：
- 尽量轻一点
- 高级一点
- 偏运营
- 不要太复杂

## 推荐 Header
```text
===CODE_SPEC===
[LANG] TS
[STACK] React
[FORM] SFC
[LAYOUT] MOBILE
[DEP] NO_EXT_LIB
[DATA] MOCK
[OUT] CODE_ONLY
```

```text
===REQ===
Build a todo page with add, delete, filter, and complete features.
```

### 当前更稳妥的实践建议

- **Header 负责压缩显式工程约束**，例如语言、框架、组件形式、布局、依赖、数据来源、输出要求
- **正文保留自然语言业务需求**，不要把开放式功能描述也过度压缩
- 这意味着 CodePrompt-DSL 的最佳定位不是“替代自然语言”，而是“给自然语言前面加一个紧凑、可复用、可审计的约束层”

## 系统流程
用户自然语言 → 显式约束提取 → Header Builder → LLM → 代码输出

## Benchmark
A组：纯自然语言  
B组：自然语言 + Header

样本：20 条 React + TS 页面任务

## 统计验收
- token 节省 ≥ 15%
- paired t-test
- p > 0.05 视为准确度无显著下降
- 显式约束遵循率持平或提升

## 实验结果

### 当前结果口径（2026-03-30 质检修订）

**可纳入正式比较的模型**
- **gemini-3.0-pro**: A=5.0, D=5.0, F=5.0
- **gpt-5.4**: A=4.9, D=4.9, F=4.9
- **glm-5.0-turbo**: A=4.8, D=4.8, F=4.7
- **kimi-k2.5**: A=4.8, D=4.8, F=4.7
- **minimax-m2.7**: A=4.7, D=4.7, F=4.7
- **gemini-3.0-flash**: A=4.3, D=4.3, F=4.3
- **deepseek-v3.2**: A=1.3, D=1.3, F=1.3
- **gemini-3.1-flash-lite**: A=1.1, D=1.1, F=1.1

**单独保留但需谨慎解读**
- **hunyuan-2.0-instruct**: A=4.70, D=4.70, F=4.50；已重跑一遍，当前更倾向于视为模型基础指令理解能力偏弱，而非单纯流程污染导致

**当前标记为不可信 / 不纳入正式结论**
- **claude-haiku-4.5**：流程一致性质检未通过
- **hunyuan-2.0-thinking**：流程一致性质检未通过

## 后续优化
1. Header 字段顺序搜索
2. 编码长度优化
3. 模型特定 Header
4. 自动排列重组搜索
5. 自动评估（LLM judge / 静态分析）
