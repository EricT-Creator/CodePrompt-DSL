import json, math

# 加载实验数据
with open("/Users/erichztang/Downloads/古文运动/experiment_data/token_count_results.json") as f:
    data = json.load(f)

tasks = data["tasks"]

# 提取各编码方式的 token 数
labels = {
    "A": "英文自然语言",
    "B": "中文自然语言", 
    "C": "英文DSL标签",
    "D": "英文极简DSL",
    "E": "古文DSL",
    "F": "极简古文"
}

vals = {}
for k in labels:
    vals[k] = [t[f"{k}_tokens"] for t in tasks]

# 配对 t-test（A vs 各组）
def paired_ttest(x, y):
    n = len(x)
    diffs = [a - b for a, b in zip(x, y)]
    mean_d = sum(diffs) / n
    ss = sum((d - mean_d)**2 for d in diffs)
    sd = math.sqrt(ss / (n - 1))
    se = sd / math.sqrt(n)
    if se == 0:
        return 0, 1.0
    t_stat = mean_d / se
    # 简化：用正态近似 p-value（n=10 自由度=9，t 分布近似）
    # 实际论文中应用 scipy，这里做近似
    df = n - 1
    # 使用近似公式
    p_approx = 2 * (1 - _norm_cdf(abs(t_stat)))
    return t_stat, p_approx

def _norm_cdf(x):
    """标准正态分布 CDF 近似"""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

print("=" * 70)
print("配对 t-test：各编码方式 vs 英文自然语言 (A)")
print("H0: 两组 token 数无差异")
print("=" * 70)

for k in ["B", "C", "D", "E", "F"]:
    t_stat, p_val = paired_ttest(vals["A"], vals[k])
    mean_a = sum(vals["A"]) / len(vals["A"])
    mean_k = sum(vals[k]) / len(vals[k])
    saving = (mean_a - mean_k) / mean_a * 100
    sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"
    print(f"\nA vs {k} ({labels[k]}):")
    print(f"  均值差: {mean_a:.1f} → {mean_k:.1f} (节省 {saving:.1f}%)")
    print(f"  t = {t_stat:.3f}, p ≈ {p_val:.6f} [{sig}]")

# Cohen's d 效应量
print("\n" + "=" * 70)
print("效应量 (Cohen's d)")
print("=" * 70)

for k in ["D", "E", "F"]:
    diffs = [a - b for a, b in zip(vals["A"], vals[k])]
    mean_d = sum(diffs) / len(diffs)
    sd = math.sqrt(sum((d - mean_d)**2 for d in diffs) / (len(diffs) - 1))
    d = mean_d / sd if sd > 0 else 0
    size = "大" if abs(d) > 0.8 else "中" if abs(d) > 0.5 else "小"
    print(f"A vs {k} ({labels[k]}): d = {d:.2f} ({size}效应)")

# 输出表格数据供报告使用
print("\n" + "=" * 70)
print("Markdown 表格输出")
print("=" * 70)

print("\n| 对比组 | 均值(A) | 均值(X) | 节省率 | t 值 | p 值 | 显著性 | Cohen's d |")
print("|--------|---------|---------|--------|------|------|--------|-----------|")

for k in ["B", "C", "D", "E", "F"]:
    t_stat, p_val = paired_ttest(vals["A"], vals[k])
    mean_a = sum(vals["A"]) / len(vals["A"])
    mean_k = sum(vals[k]) / len(vals[k])
    saving = (mean_a - mean_k) / mean_a * 100
    sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"
    diffs = [a - b for a, b in zip(vals["A"], vals[k])]
    mean_d = sum(diffs) / len(diffs)
    sd = math.sqrt(sum((d - mean_d)**2 for d in diffs) / (len(diffs) - 1))
    d_val = mean_d / sd if sd > 0 else 0
    print(f"| A vs {labels[k]} | {mean_a:.1f} | {mean_k:.1f} | {saving:.1f}% | {t_stat:.2f} | {p_val:.4f} | {sig} | {d_val:.2f} |")
