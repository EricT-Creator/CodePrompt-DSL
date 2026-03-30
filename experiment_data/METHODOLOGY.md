# CodePrompt-DSL 多模型对比实验 —— 标准化方法论

> **本文档定义了所有模型必须遵循的统一测试流程。**
> 每个模型的生成结果存放在 `generations/{模型标识}/` 目录下。

---

## 一、实验变量控制

| 变量 | 控制 |
|------|------|
| Prompt 内容 | 完全一致（3 种编码 × 10 任务 = 30 个 prompt） |
| 任务定义 | 完全一致（10 个 benchmark 任务） |
| 评估规则 | 完全一致（规则化自动评估脚本） |
| 生成次数 | 每组 1 次 |
| 唯一变量 | **LLM 模型**（不同模型在不同轮次中分别测试） |

---

## 二、Benchmark 任务集（10 个）

| ID | 任务名 | 约束 | 英文需求 | 古文需求 |
|----|--------|------|---------|---------|
| T01 | Todo App | TS/React/TW/无外库/移动/模拟 | Build a todo page with add, delete, filter, and complete features. | 作待办页，具增删筛毕之能。 |
| T02 | Login Form | TS/React/TW/无外库/移动/模拟 | Build a login form with email and password fields, validation, and error messages. | 作登入表，含邮密二栏、校验及误示。 |
| T03 | User Profile Card | TS/React/TW/无外库/移动/模拟 | Build a user profile card showing avatar, name, bio, and a follow button. | 作用户卡，示头像、名、简介与关注键。 |
| T04 | Shopping Cart | TS/React/TW/无外库/移动/模拟 | Build a shopping cart page with item list, quantity adjustment, price calculation, and checkout button. | 作购物车页，列商品、调数量、算价、具结算键。 |
| T05 | Weather Dashboard | TS/React/TW/无外库/适应/模拟 | Build a weather dashboard showing current temperature, humidity, wind speed, and a 5-day forecast. | 作天气板，示温湿风速及五日之报。 |
| T06 | Markdown Editor | TS/React/CSS/无外库/桌面/无 | Build a split-pane markdown editor with live preview. | 作左右分栏之 Markdown 编辑器，实时预览。 |
| T07 | Image Gallery | TS/React/TW/无外库/适应/模拟 | Build an image gallery with grid layout, lightbox preview, and lazy loading. | 作图廊，网格排列，点击可放大，惰加载。 |
| T08 | Chat Interface | TS/React/TW/无外库/移动/模拟 | Build a chat interface with message bubbles, input box, send button, and auto-scroll to bottom. | 作聊天界面，具消息泡、输入栏、发送键，自动滚至底。 |
| T09 | Data Table | TS/React/TW/无外库/桌面/模拟 | Build a data table with sorting, pagination, and search filtering. | 作数据表，可排序、分页、搜索筛选。 |
| T10 | Settings Panel | TS/React/TW/无外库/适应/模拟 | Build a settings panel with toggle switches, dropdown selectors, and a save button. | 作设置板，具开关、下拉选与存储键。 |

---

## 三、三种 Prompt 编码方式

### A 组（英文自然语言）
```
Write a React component using TypeScript. It should be a single file component. 
Use {Tailwind CSS | plain CSS} for styling but no other external libraries. 
The layout should be {mobile-first | responsive | desktop}. 
{Use mock data. | }Only output code, no explanations.
{英文需求}
```

### D 组（英文极简 DSL）
```
[L]TS[S]React[F]SFC[Y]{TW|CSS}[D]NOX[M]{MOB|RSP|DSK}[DT]{MOCK|NONE}[O]CODE
{英文需求}
```

### F 组（极简古文）
```
[语]TS[架]React[式]单件[样]{TW|CSS}[依]无外库[排]{移动|适应|桌面}[数]{模拟|无}[出]纯码
{古文需求}
```

---

## 四、代码生成流程

### Step 1：模型切换
用户在 WorkBuddy 中手动切换目标模型。

### Step 2：逐任务生成
对于每个任务（T01-T10），依次用 A/D/F 三种 prompt 生成代码。

**生成规则：**
- 模型直接根据 prompt 生成 React + TypeScript 代码
- 代码保存为 `.tsx` 文件
- 只输出代码，不输出解释

### Step 3：文件命名与存储
```
generations/
└── {模型标识}/          # 如 claude-opus-4.6, glm-5.0-turbo, gpt-4o
    ├── A/
    │   ├── T01_TodoApp.tsx
    │   ├── T02_LoginForm.tsx
    │   ├── ...
    │   └── T10_SettingsPanel.tsx
    ├── D/
    │   ├── T01_TodoApp.tsx
    │   ├── ...
    │   └── T10_SettingsPanel.tsx
    └── F/
        ├── T01_TodoApp.tsx
        ├── ...
        └── T10_SettingsPanel.tsx
```

**模型标识命名规范：** 使用 WorkBuddy 中显示的模型名称，小写 + 连字符。例如：
- `claude-opus-4.6`
- `glm-5.0-turbo`
- `gpt-4o`
- `deepseek-v3`
- `kimi-k2`
- `minimax-m1`
- `gemini-2.5-pro`
- `hunyuan`

---

## 五、评估方法

### 5.1 评估维度（规则化自动评估）

| # | 维度 | 分值 | 判定规则 |
|---|------|------|---------|
| 1 | 技术栈正确 | 0/1 | 检测 `import React` + TypeScript 类型注解 |
| 2 | 输出形式正确 | 0/1 | 检测 `export default` + 单组件结构 |
| 3 | 样式方案正确 | 0/1 | TW 任务：检测 Tailwind 类名；CSS 任务：检测 inline style |
| 4 | 依赖约束遵守 | 0/1 | 检测是否引入第三方库（排除 react） |
| 5 | 功能完整 | 0/1 | 关键功能词命中率 ≥75% |

**总分：0-5 分**

### 5.2 功能关键词列表

| 任务 | 关键词 |
|------|--------|
| T01 | add, delete, filter, complete |
| T02 | email, password, valid, error |
| T03 | avatar, name, bio, follow |
| T04 | item, quantity, price, checkout |
| T05 | temp, humid, wind, forecast |
| T06 | split, editor, preview, markdown |
| T07 | grid, lightbox, lazy |
| T08 | message, input, send, scroll |
| T09 | sort, paginat, search |
| T10 | toggle, select, save |

### 5.3 已知第三方库黑名单
axios, lodash, moment, dayjs, date-fns, react-router, redux, zustand, jotai, recoil, react-query, swr, framer-motion, react-spring, material-ui, @mui, antd, chakra-ui, react-icons, heroicons, lucide-react, marked, react-markdown, remark, react-table, tanstack, formik, react-hook-form, yup, zod

### 5.4 汇总指标

- **平均分**：每组 10 个任务的平均总分
- **维度通过率**：每维度 10 个任务中的通过比例
- **满分率**：10 个任务中得 5/5 的比例
- **配对比较**：A vs D, A vs F 的均值差、胜/平/负

---

## 六、分析流程

### 6.1 单模型分析
1. 运行评估脚本，生成各任务评分
2. 计算组内均值、通过率
3. 做 A vs D, A vs F 配对比较

### 6.2 多模型横比（所有模型完成后）
1. 各模型相同编码方式下的得分对比
2. 按类别分组分析：
   - **中国模型 vs 海外模型**
   - **闭源模型 vs 开源模型**
   - **不同编码方式的模型间一致性**
3. 进阶探索：
   - 哪些模型对极简 DSL 理解最好？
   - 哪些模型对古文编码最不敏感？
   - 模型规模是否与 DSL 理解能力正相关？
   - 中国模型是否在中文古文编码上有天然优势？

---

## 七、模型测试清单

| # | 模型 | 来源 | 类型 | 状态 |
|---|------|------|------|------|
| 1 | Claude Opus 4.6 | Anthropic | 闭源/海外 | ✅ 已完成 |
| 2 | GLM-5.0-Turbo | 智谱 | 闭源/中国 | ✅ 已完成 |
| 3 | Kimi K2.5 | Moonshot | 开源/中国 | ✅ 已完成 |
| 4 | MiniMax M2.7 | MiniMax | 闭源/中国 | ✅ 已完成 |
| 5 | GPT-5.4 | OpenAI | 闭源/海外 | ✅ 已完成 |
| 6 | Gemini-3.1-flash-lite | Google | 闭源/海外 | ✅ 已完成 |
| 6.1 | Gemini-3.0-Pro | Google | 闭源/海外 | ✅ 已完成 |
| 6.2 | Gemini-3.0-flash | Google | 闭源/海外 | ✅ 已完成 |
| 7 | DeepSeek-V3.2 | 深度求索 | 中国/开源 | ✅ 已完成 |
| 7 | DeepSeek V3 | DeepSeek | 开源/中国 | ⏳ 待测 |
| 8 | Hunyuan | 腾讯 | 闭源/中国 | ⏳ 待测 |
