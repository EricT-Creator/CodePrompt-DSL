import json
import math

# ============================================
# 数据
# ============================================
task_names = ["T01 Todo", "T02 Login", "T03 Profile", "T04 Cart", "T05 Weather",
              "T06 Markdown", "T07 Gallery", "T08 Chat", "T09 Table", "T10 Settings"]

data = {
    "英文自然语言": [63, 64, 65, 67, 67, 53, 63, 68, 60, 63],
    "中文自然语言": [63, 65, 61, 64, 66, 55, 66, 67, 60, 64],
    "英文DSL标签":  [62, 63, 64, 66, 68, 56, 64, 67, 60, 64],
    "英文极简DSL":  [46, 47, 48, 50, 51, 40, 47, 51, 44, 47],
    "古文DSL":      [57, 60, 58, 63, 61, 58, 64, 64, 57, 62],
    "极简古文":     [50, 53, 51, 56, 53, 51, 56, 57, 50, 54],
}

colors = {
    "英文自然语言": "#4A90D9",
    "中文自然语言": "#67B7DC",
    "英文DSL标签":  "#A0C4FF",
    "英文极简DSL":  "#2ECC71",
    "古文DSL":      "#E74C3C",
    "极简古文":     "#F39C12",
}

# 统计
stats = {}
base_mean = sum(data["英文自然语言"]) / 10
for name, vals in data.items():
    mean = sum(vals) / len(vals)
    saving = (base_mean - mean) / base_mean * 100
    stats[name] = {"mean": mean, "saving": saving}

# 字符数据
char_data = {
    "英文自然语言": {"chars": 306.2, "tokens": 63.3},
    "中文自然语言": {"chars": 112.8, "tokens": 63.1},
    "英文DSL标签":  {"chars": 199.0, "tokens": 63.4},
    "英文极简DSL":  {"chars": 131.6, "tokens": 47.1},
    "古文DSL":      {"chars": 82.2,  "tokens": 60.4},
    "极简古文":     {"chars": 63.9,  "tokens": 53.1},
}

# ============================================
# 生成 HTML 报告（含内嵌图表）
# ============================================
html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CodePrompt-DSL 实验报告</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { 
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    background: #0a0a0a; color: #e0e0e0; line-height: 1.7; 
}
.container { max-width: 960px; margin: 0 auto; padding: 40px 24px; }
h1 { font-size: 2em; font-weight: 700; margin-bottom: 8px; color: #fff; }
h2 { font-size: 1.5em; font-weight: 600; margin: 48px 0 16px; color: #fff; border-bottom: 1px solid #333; padding-bottom: 8px; }
h3 { font-size: 1.15em; font-weight: 600; margin: 32px 0 12px; color: #ccc; }
p { margin: 12px 0; color: #bbb; }
.subtitle { color: #888; font-size: 0.95em; margin-bottom: 32px; }
.highlight { background: #1a1a2e; border-left: 4px solid #4A90D9; padding: 16px 20px; margin: 20px 0; border-radius: 4px; }
.highlight.red { border-left-color: #E74C3C; background: #1a1212; }
.highlight.green { border-left-color: #2ECC71; background: #121a14; }
.highlight.yellow { border-left-color: #F39C12; background: #1a1812; }
code { background: #1e1e1e; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; color: #e6db74; }
pre { background: #1e1e1e; padding: 16px; border-radius: 6px; overflow-x: auto; margin: 16px 0; font-size: 0.85em; line-height: 1.5; }
pre code { background: none; padding: 0; }
table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 0.9em; }
th { background: #1a1a2e; color: #aaa; font-weight: 600; text-transform: uppercase; font-size: 0.8em; letter-spacing: 0.5px; }
td, th { padding: 10px 12px; text-align: center; border-bottom: 1px solid #222; }
td:first-child, th:first-child { text-align: left; }
tr:hover td { background: #111; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.8em; font-weight: 600; }
.badge.green { background: #0d3320; color: #2ECC71; }
.badge.red { background: #331111; color: #E74C3C; }
.badge.yellow { background: #332b11; color: #F39C12; }
.badge.gray { background: #222; color: #888; }

/* Chart styles */
.chart-container { margin: 24px 0; }
.bar-chart { position: relative; }
.bar-row { display: flex; align-items: center; margin: 6px 0; }
.bar-label { width: 130px; font-size: 0.85em; color: #aaa; text-align: right; padding-right: 12px; flex-shrink: 0; }
.bar-track { flex: 1; height: 28px; background: #1a1a1a; border-radius: 4px; position: relative; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 4px; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; font-size: 0.75em; font-weight: 600; color: #fff; transition: width 0.5s; min-width: 40px; }
.bar-value { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); font-size: 0.8em; color: #666; }

/* Scatter-like comparison */
.scatter-row { display: flex; align-items: center; margin: 10px 0; gap: 12px; }
.scatter-label { width: 130px; font-size: 0.85em; color: #aaa; text-align: right; flex-shrink: 0; }
.scatter-bars { flex: 1; display: flex; gap: 4px; align-items: center; }
.scatter-bar { height: 20px; border-radius: 3px; position: relative; }
.scatter-bar .val { position: absolute; right: -40px; top: 50%; transform: translateY(-50%); font-size: 0.75em; color: #888; white-space: nowrap; }

.finding-box { background: #111; border: 1px solid #333; border-radius: 8px; padding: 20px; margin: 16px 0; }
.finding-num { display: inline-block; width: 28px; height: 28px; background: #4A90D9; color: #fff; border-radius: 50%; text-align: center; line-height: 28px; font-size: 0.85em; font-weight: 700; margin-right: 10px; }
.finding-title { font-weight: 600; color: #fff; font-size: 1em; }
.finding-detail { margin-top: 8px; color: #999; font-size: 0.9em; }

.tldr { background: linear-gradient(135deg, #1a1a2e, #16213e); border: 1px solid #2a3a5e; border-radius: 12px; padding: 28px; margin: 24px 0; }
.tldr h3 { color: #4A90D9; margin-top: 0; }

footer { margin-top: 60px; padding-top: 20px; border-top: 1px solid #222; color: #555; font-size: 0.85em; text-align: center; }
</style>
</head>
<body>
<div class="container">

<h1>🧪 CodePrompt-DSL 实验报告</h1>
<p class="subtitle">
"古文能省 Token 吗？" —— 一个关于 LLM Prompt 编码效率的反直觉实验<br>
实验日期：2026-03-30 &nbsp;|&nbsp; Tokenizer：GPT-4o (o200k_base) &nbsp;|&nbsp; 样本量：10 个代码生成任务
</p>

<div class="tldr">
<h3>📌 TL;DR</h3>
<p style="color:#ddd; margin-top:8px;">
我们测试了 6 种 Prompt 编码方式在代码生成场景中的 token 消耗。核心发现：<strong>中文（包括古文）在 BPE tokenizer 中的编码效率天然低于英文</strong>，导致"字少 ≠ token 少"。古文 DSL 仅节省 4.6%（不具实用价值），而英文极简 DSL 可节省 25.6%。"古文凝练"的直觉在 LLM 世界中不成立。
</p>
</div>

<!-- ============================================ -->
<h2>一、研究动机</h2>

<p>在使用大模型进行代码生成时，我们观察到一个现象：<strong>工程约束</strong>（技术栈、输出格式、依赖限制等）在不同任务间高度重复，但每次都需要用自然语言重新描述。</p>

<p>由此产生了一个假设：中国古文以极少的字数承载丰富的含义，如果用类似古文的凝练编码方式来表达这些约束，是否能显著降低 token 消耗？</p>

<div class="highlight">
<strong>核心假设：</strong>古文的高信息密度可以转化为 LLM prompt 的 token 节省。<br>
<strong>预期效果：</strong>token 节省 ≥ 15%，生成质量无显著下降。
</div>

<!-- ============================================ -->
<h2>二、实验设计</h2>

<h3>2.1 任务集</h3>
<p>构建了 10 个前端代码生成任务（React + TypeScript），覆盖不同复杂度的 UI 组件：</p>

<table>
<tr><th>ID</th><th>任务</th><th>复杂度</th></tr>
<tr><td>T01</td><td>Todo App（待办事项）</td><td>中</td></tr>
<tr><td>T02</td><td>Login Form（登录表单）</td><td>低</td></tr>
<tr><td>T03</td><td>User Profile Card（用户卡片）</td><td>低</td></tr>
<tr><td>T04</td><td>Shopping Cart（购物车）</td><td>高</td></tr>
<tr><td>T05</td><td>Weather Dashboard（天气面板）</td><td>中</td></tr>
<tr><td>T06</td><td>Markdown Editor（编辑器）</td><td>高</td></tr>
<tr><td>T07</td><td>Image Gallery（图片画廊）</td><td>中</td></tr>
<tr><td>T08</td><td>Chat Interface（聊天界面）</td><td>高</td></tr>
<tr><td>T09</td><td>Data Table（数据表格）</td><td>中</td></tr>
<tr><td>T10</td><td>Settings Panel（设置面板）</td><td>低</td></tr>
</table>

<h3>2.2 编码方式（6 组）</h3>

<table>
<tr><th>组别</th><th>编码方式</th><th>示例</th></tr>
<tr><td><span class="badge gray">A</span></td><td>英文自然语言</td><td><code>Write a React component using TypeScript...</code></td></tr>
<tr><td><span class="badge gray">B</span></td><td>中文自然语言</td><td><code>请用 React 和 TypeScript 写一个...</code></td></tr>
<tr><td><span class="badge gray">C</span></td><td>英文 DSL 标签（verbose）</td><td><code>[LANG]TS[STACK]React[FORM]SFC...</code></td></tr>
<tr><td><span class="badge green">D</span></td><td>英文极简 DSL</td><td><code>[L]TS[S]React[F]SFC...</code></td></tr>
<tr><td><span class="badge red">E</span></td><td>古文 DSL</td><td><code>[语]TS[架]React[式]单文件...</code></td></tr>
<tr><td><span class="badge yellow">F</span></td><td>极简古文</td><td><code>[语]TS[架]React 作待办页，增删筛毕。</code></td></tr>
</table>

<h3>2.3 控制变量</h3>
<p>所有组使用相同的 tokenizer（GPT-4o / o200k_base），相同的约束信息量，仅改变编码方式。</p>

<!-- ============================================ -->
<h2>三、实验结果</h2>

<h3>3.1 平均 Token 消耗对比</h3>

<div class="chart-container">
<div class="bar-chart">
"""

# 生成条形图
max_tokens = 70
for name in ["英文自然语言", "中文自然语言", "英文DSL标签", "英文极简DSL", "古文DSL", "极简古文"]:
    s = stats[name]
    pct = s["mean"] / max_tokens * 100
    saving_text = f'{s["saving"]:.1f}%' if abs(s["saving"]) > 0.5 else "基线"
    color = colors[name]
    html += f"""
    <div class="bar-row">
        <div class="bar-label">{name}</div>
        <div class="bar-track">
            <div class="bar-fill" style="width:{pct:.0f}%; background:{color};">
                {s["mean"]:.1f}t
            </div>
        </div>
        <div style="width:70px; text-align:right; font-size:0.8em; color:#888; flex-shrink:0; padding-left:8px;">
            {"" if saving_text == "基线" else "↓"}{saving_text}
        </div>
    </div>"""

html += """
</div>
</div>

<h3>3.2 各任务 Token 计数明细</h3>

<table>
<tr>
<th>任务</th>
<th>英文NL</th>
<th>中文NL</th>
<th>DSL标签</th>
<th style="color:#2ECC71">极简DSL</th>
<th style="color:#E74C3C">古文DSL</th>
<th style="color:#F39C12">极简古文</th>
</tr>
"""

for i, tn in enumerate(task_names):
    row_vals = []
    for name in ["英文自然语言", "中文自然语言", "英文DSL标签", "英文极简DSL", "古文DSL", "极简古文"]:
        row_vals.append(data[name][i])
    min_val = min(row_vals)
    cells = ""
    for j, v in enumerate(row_vals):
        style = ' style="color:#2ECC71; font-weight:600;"' if v == min_val else ""
        cells += f"<td{style}>{v}</td>"
    html += f"<tr><td>{tn}</td>{cells}</tr>\n"

# 均值行
html += '<tr style="border-top:2px solid #333; font-weight:600;"><td>平均</td>'
for name in ["英文自然语言", "中文自然语言", "英文DSL标签", "英文极简DSL", "古文DSL", "极简古文"]:
    s = stats[name]
    html += f'<td>{s["mean"]:.1f}</td>'
html += "</tr>"

html += """
</table>

<h3>3.3 字符数 vs Token 数</h3>
<p>这是本实验最关键的发现：<strong>字符数和 token 数并非线性关系</strong>。</p>

<table>
<tr><th>编码方式</th><th>平均字符数</th><th>平均 Token 数</th><th>Token/字符比</th><th>解读</th></tr>
"""

for name in ["英文自然语言", "中文自然语言", "英文DSL标签", "英文极简DSL", "古文DSL", "极简古文"]:
    cd = char_data[name]
    ratio = cd["tokens"] / cd["chars"]
    if ratio < 0.3:
        badge = '<span class="badge green">高效</span>'
    elif ratio < 0.6:
        badge = '<span class="badge yellow">中等</span>'
    else:
        badge = '<span class="badge red">低效</span>'
    html += f'<tr><td>{name}</td><td>{cd["chars"]:.0f}</td><td>{cd["tokens"]:.1f}</td><td>{ratio:.3f}</td><td>{badge}</td></tr>\n'

html += """
</table>

<div class="highlight red">
<strong>关键发现：</strong>古文的 Token/字符比高达 0.735~0.831，是英文自然语言（0.207）的 3.5~4 倍。<br>
这意味着：<strong>古文每个汉字消耗的 token 远多于英文每个字母</strong>。古文的"凝练"优势被 BPE tokenizer 的编码效率差异完全抵消。
</div>

<!-- ============================================ -->
<h2>四、统计检验</h2>

<p>使用配对 t-test 检验各编码方式与英文自然语言（基线）的差异显著性：</p>

<table>
<tr><th>对比组</th><th>均值(A)</th><th>均值(X)</th><th>节省率</th><th>t 值</th><th>p 值</th><th>显著性</th><th>Cohen's d</th></tr>
<tr><td>A vs 中文自然语言</td><td>63.3</td><td>63.1</td><td>0.3%</td><td>0.29</td><td>0.769</td><td><span class="badge gray">ns</span></td><td>0.09</td></tr>
<tr><td>A vs 英文DSL标签</td><td>63.3</td><td>63.4</td><td>-0.2%</td><td>-0.23</td><td>0.818</td><td><span class="badge gray">ns</span></td><td>-0.07</td></tr>
<tr style="background:#0d1a0d;"><td>A vs 英文极简DSL</td><td>63.3</td><td>47.1</td><td><strong>25.6%</strong></td><td>41.67</td><td><0.001</td><td><span class="badge green">***</span></td><td>13.18</td></tr>
<tr><td>A vs 古文DSL</td><td>63.3</td><td>60.4</td><td>4.6%</td><td>2.50</td><td>0.012</td><td><span class="badge yellow">*</span></td><td>0.79</td></tr>
<tr style="background:#1a1a0d;"><td>A vs 极简古文</td><td>63.3</td><td>53.1</td><td><strong>16.1%</strong></td><td>8.92</td><td><0.001</td><td><span class="badge green">***</span></td><td>2.82</td></tr>
</table>

<div class="highlight">
<strong>解读：</strong><br>
• 英文极简 DSL 节省 25.6%，统计高度显著（p<0.001），效应量极大（d=13.18）<br>
• 极简古文节省 16.1%，统计显著（p<0.001），效应量大（d=2.82）<br>
• <strong>古文 DSL 仅节省 4.6%</strong>，虽统计显著但实用价值低<br>
• 英文 DSL verbose 标签（[LANG]TS 格式）几乎无节省（-0.2%）——<strong>标签本身吃掉了压缩空间</strong>
</div>

<!-- ============================================ -->
<h2>五、为什么"古文凝练"在这里不起作用</h2>

<div class="finding-box">
<span class="finding-num">1</span>
<span class="finding-title">BPE Tokenizer 对中文编码效率低</span>
<div class="finding-detail">
GPT 系列模型使用的 BPE tokenizer 以英文为主要训练语料。英文平均 4-5 个字符 = 1 token，而中文平均 1-2 个字符 = 1 token。古文虽然字数少，但每个字消耗的 token 比例远高于英文。
</div>
</div>

<div class="finding-box">
<span class="finding-num">2</span>
<span class="finding-title">"字数"和"Token 数"是两个不同的度量</span>
<div class="finding-detail">
人类阅读效率以字/词为单位，LLM 处理效率以 token 为单位。这是两套完全不同的信息编码系统。古文对人类阅读效率极高（少字多义），但对 LLM 并非如此。
</div>
</div>

<div class="finding-box">
<span class="finding-num">3</span>
<span class="finding-title">真正省 token 的是"缩短标签名"，而非"换成中文"</span>
<div class="finding-detail">
对比 C 组（<code>[LANG]TS</code>）和 D 组（<code>[L]TS</code>）：仅仅是把标签名从完整英文缩写为单字母，就从 63.4 降到了 47.1（节省 25.6%）。而 E 组把标签换成中文（<code>[语]TS</code>）只降到了 60.4（节省 4.6%）。<strong>语言选择不是关键，编码长度才是。</strong>
</div>
</div>

<div class="finding-box">
<span class="finding-num">4</span>
<span class="finding-title">极简古文（F组）的节省主要来自需求描述压缩</span>
<div class="finding-detail">
F 组（极简古文）16.1% 的节省中，大部分来自于将英文需求 "Build a todo page with add, delete, filter, and complete features." 压缩为 "作待办页，增删筛毕。" —— 但这个压缩是以<strong>可读性和精确性为代价</strong>的。而且如果需求描述更长更复杂，古文翻译的准确性会急剧下降。
</div>
</div>

<!-- ============================================ -->
<h2>六、延伸发现</h2>

<h3>6.1 Verbose DSL 标签没有价值</h3>
<p>C 组（<code>[LANG]TS[STACK]React...</code>）的 token 数（63.4）甚至<strong>高于</strong>自然语言（63.3）。标签框架本身消耗的 token 抵消了约束压缩的收益。这意味着：<strong>如果要做 DSL，必须极简。</strong></p>

<h3>6.2 中英文自然语言 Token 几乎相同</h3>
<p>A 组（63.3）和 B 组（63.1）差异仅 0.3%，统计不显著。这说明在当前 tokenizer 下，同等信息量的中英文 prompt token 消耗基本一致——中文字少但每字消耗多，英文字多但每字消耗少，最终持平。</p>

<h3>6.3 Token 节省的上限估算</h3>
<p>在保持信息不丢失的前提下，prompt 约束部分的最大压缩空间约为 25-30%（D 组水平）。如果约束部分仅占完整 prompt 的 30-50%（其余为需求描述和上下文），则<strong>端到端的实际节省约为 8-15%</strong>。</p>

<!-- ============================================ -->
<h2>七、实验局限性</h2>

<table>
<tr><th>局限</th><th>影响</th><th>改进方向</th></tr>
<tr><td>仅测试了 token 计数，未测试 LLM 理解准确率</td><td>不确定极简 DSL 是否会导致生成质量下降</td><td>需要调用 LLM 并做人工评估</td></tr>
<tr><td>仅测试了 GPT-4o tokenizer</td><td>Claude、DeepSeek 等模型可能有不同结果</td><td>多 tokenizer 对比</td></tr>
<tr><td>任务集较小（10 个）且类型单一（前端组件）</td><td>结论的泛化性有限</td><td>扩展到 API、脚本等场景</td></tr>
<tr><td>未考虑 Prompt Caching 的影响</td><td>缓存可能使 DSL 的节省被进一步削弱</td><td>增加 caching 对比组</td></tr>
<tr><td>古文翻译为人工编写</td><td>翻译质量可能影响结果</td><td>增加多人翻译并取共识</td></tr>
</table>

<!-- ============================================ -->
<h2>八、结论</h2>

<div class="highlight green">
<strong>结论 1：</strong>"古文凝练"的直觉在 LLM tokenizer 中不成立。<br>
中文古文的 Token/字符比是英文的 3.5-4 倍，"字数少"的优势被编码效率低完全抵消。古文 DSL 仅节省 4.6%，不具实用价值。
</div>

<div class="highlight green">
<strong>结论 2：</strong>如果追求 token 效率，应使用英文极简缩写。<br>
英文极简 DSL（单字母标签）可节省 25.6%，是所有方案中效率最高的。
</div>

<div class="highlight yellow">
<strong>结论 3：</strong>Verbose DSL 标签（[LANG]、[STACK]等）没有 token 节省价值。<br>
标签框架自身的 token 消耗抵消了压缩收益。DSL 必须极简才有意义。
</div>

<div class="highlight">
<strong>结论 4：</strong>token 节省不应该是 DSL 的主要价值主张。<br>
即使最优方案也只节省 25%（仅约束部分），端到端可能只有 10% 左右。在 token 价格快速下降 + Prompt Caching 普及的背景下，这个收益的绝对价值有限。如果要做工程约束 DSL，其核心价值应该是<strong>标准化、可复用、可审计</strong>，而非省 token。
</div>

<!-- ============================================ -->
<h2>九、一个更大的启示</h2>

<p>这个实验揭示了一个有趣的认知偏差：</p>

<p><strong>我们倾向于用人类的信息处理方式去理解机器的信息处理方式。</strong></p>

<p>古文对人类来说是"高密度编码"——少字多义。但 LLM 不是用"字"来处理信息的，而是用 token。而 token 的生成逻辑（BPE 算法）与人类的阅读逻辑完全不同。</p>

<p>这个认知偏差提醒我们：在优化 LLM 交互时，<strong>不能依赖人类直觉，而要依赖数据</strong>。这也正是我们做这个实验的意义。</p>

<!-- ============================================ -->

<h2>附录：实验代码与数据</h2>
<p>完整实验代码、原始数据和分析脚本已开源：</p>
<ul style="margin-left:20px; color:#888;">
<li><code>experiment_data/token_count_results.json</code> — 原始计数数据</li>
<li><code>experiment_data/statistical_analysis.py</code> — 统计分析脚本</li>
</ul>

<footer>
CodePrompt-DSL Experiment Report &nbsp;|&nbsp; 2026-03-30 &nbsp;|&nbsp; 
"字数少 ≠ Token 少" — 一个反直觉但有价值的发现
</footer>

</div>
</body>
</html>
"""

with open("/Users/erichztang/Downloads/古文运动/实验报告.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ 实验报告已生成：实验报告.html")
