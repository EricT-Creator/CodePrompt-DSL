#!/usr/bin/env python3
"""复查脚本：检查所有模型评估结果的一致性"""
import json
import os
import glob

base_dir = os.path.dirname(os.path.abspath(__file__))

print("=" * 70)
print("CodePrompt-DSL 实验复查报告")
print("=" * 70)

# 收集所有评估结果文件
json_files = {}

# 位于 experiment_data/ 根目录的
for f in sorted(glob.glob(os.path.join(base_dir, "accuracy_results_*.json"))):
    model = os.path.basename(f).replace("accuracy_results_", "").replace(".json", "")
    json_files[model] = {"path": f, "location": "experiment_data/"}

# 位于 experiment_data/generations/ 的
for f in sorted(glob.glob(os.path.join(base_dir, "generations", "accuracy_results_*.json"))):
    model = os.path.basename(f).replace("accuracy_results_", "").replace(".json", "")
    json_files[model] = {"path": f, "location": "experiment_data/generations/"}

# 原始baseline
baseline_path = os.path.join(base_dir, "accuracy_results.json")
if os.path.exists(baseline_path):
    json_files["_baseline_claude-opus-4.6"] = {"path": baseline_path, "location": "experiment_data/"}

print("\n## 1. 评估结果文件位置审计\n")
print(f"{'模型':<30} {'位置':<35} {'文件大小':<12}")
print("-" * 77)
for model, info in sorted(json_files.items()):
    size = os.path.getsize(info["path"])
    print(f"{model:<30} {info['location']:<35} {size:>8} bytes")

# 分析格式
print("\n## 2. JSON格式一致性审计\n")
formats = {}
for model, info in sorted(json_files.items()):
    with open(info["path"]) as fp:
        data = json.load(fp)
    
    if isinstance(data, list):
        # 数组格式 (早期模型)
        has_model_field = "model" in data[0] if data else False
        fields = list(data[0].keys()) if data else []
        n_records = len(data)
        groups = set(d.get("group", "?") for d in data)
        tasks = set(d.get("task_id", "?") for d in data)
        
        # 计算各组平均分
        group_avgs = {}
        for entry in data:
            g = entry.get("group", "?")
            if g not in group_avgs:
                group_avgs[g] = []
            group_avgs[g].append(entry.get("total", 0))
        
        avg_str = ", ".join(f"{g}={sum(v)/len(v):.2f}" for g, v in sorted(group_avgs.items()))
        
        formats[model] = {
            "type": "array",
            "n_records": n_records,
            "fields": fields,
            "groups": sorted(groups),
            "tasks": sorted(tasks),
            "has_model_field": has_model_field,
            "averages": {g: round(sum(v)/len(v), 2) for g, v in sorted(group_avgs.items())}
        }
        print(f"{model:<30} 格式=数组  记录数={n_records:>3}  组={sorted(groups)}  分数={avg_str}")
        
    elif isinstance(data, dict):
        # 对象格式 (后期模型)
        has_groups = "groups" in data
        if has_groups:
            group_keys = list(data["groups"].keys())
            # 检查子格式
            first_group = data["groups"].get(group_keys[0], {}) if group_keys else {}
            if "scores" in first_group:
                sub_format = "scores_array"
                avg_str = ", ".join(f"{g}={data['groups'][g].get('average', '?')}" for g in sorted(group_keys))
                formats[model] = {
                    "type": "object/scores_array",
                    "groups": sorted(group_keys),
                    "averages": {g: data["groups"][g].get("average", 0) for g in sorted(group_keys)}
                }
            elif "components" in first_group:
                sub_format = "components_detail"
                avg_str = ", ".join(f"{g}={data['groups'][g].get('group_average', '?')}" for g in sorted(group_keys))
                formats[model] = {
                    "type": "object/components_detail",
                    "groups": sorted(group_keys),
                    "averages": {g: data["groups"][g].get("group_average", 0) for g in sorted(group_keys)}
                }
            else:
                sub_format = "unknown"
                avg_str = "N/A"
                formats[model] = {"type": f"object/{sub_format}", "groups": sorted(group_keys)}
            
            print(f"{model:<30} 格式=对象/{sub_format}  组={sorted(group_keys)}  分数={avg_str}")
        else:
            print(f"{model:<30} 格式=对象(无groups字段)  顶级键={list(data.keys())[:5]}")
            formats[model] = {"type": "object/no_groups"}

# 评估维度一致性
print("\n## 3. 评估维度一致性审计\n")
print("早期模型(数组格式)的评估维度:")
array_dims = None
for model, info in sorted(formats.items()):
    if info["type"] == "array":
        with open(json_files[model]["path"]) as fp:
            data = json.load(fp)
        dims = [k for k in data[0].keys() if k not in ("model", "task_id", "group", "group_name", "file", "total")]
        dims_core = [k.replace("_detail", "") for k in dims if not k.endswith("_detail")]
        if array_dims is None:
            array_dims = dims_core
        match = "✅" if dims_core == array_dims else "❌"
        print(f"  {model:<28} 维度={dims_core}  {match}")

print("\n后期模型(对象格式)的评估维度:")
for model, info in sorted(formats.items()):
    if info["type"].startswith("object/"):
        with open(json_files[model]["path"]) as fp:
            data = json.load(fp)
        if "groups" in data:
            first_group_key = list(data["groups"].keys())[0]
            fg = data["groups"][first_group_key]
            if "scores" in fg:
                dims = [k for k in fg.keys() if k not in ("name", "scores", "average")]
                print(f"  {model:<28} 维度={dims}")
            elif "components" in fg:
                first_comp = list(fg["components"].values())[0]
                dims = [k for k in first_comp.keys() if k != "average_score"]
                print(f"  {model:<28} 维度={dims}")

# 评分标准一致性
print("\n## 4. 评分标准一致性审计\n")
print(f"{'模型':<30} {'评分制':<12} {'A组均分':<10} {'D组均分':<10} {'F组均分':<10}")
print("-" * 72)
for model, info in sorted(formats.items()):
    if model.startswith("_"):
        continue
    avgs = info.get("averages", {})
    a_avg = avgs.get("A", "N/A")
    d_avg = avgs.get("D", "N/A")
    f_avg = avgs.get("F", "N/A")
    
    # 判断评分制
    if info["type"] == "array":
        score_system = "0-1×5=5分制"
    else:
        score_system = "连续1-5分制"
    
    print(f"{model:<30} {score_system:<12} {str(a_avg):<10} {str(d_avg):<10} {str(f_avg):<10}")

# 任务集一致性
print("\n## 5. 任务集一致性审计\n")
expected_tasks = ["T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08", "T09", "T10"]
expected_groups = ["A", "D", "F"]
for model, info in sorted(formats.items()):
    if model.startswith("_"):
        continue
    issues = []
    if info.get("groups") != expected_groups:
        issues.append(f"组不一致: 期望{expected_groups}, 实际{info.get('groups')}")
    if info["type"] == "array":
        if info.get("tasks") != expected_tasks:
            issues.append(f"任务不一致: 期望{expected_tasks}, 实际{info.get('tasks')}")
        if info.get("n_records") != 30:
            issues.append(f"记录数不一致: 期望30, 实际{info.get('n_records')}")
    
    status = "✅ 通过" if not issues else "❌ " + "; ".join(issues)
    print(f"  {model:<28} {status}")

# 汇总
print("\n" + "=" * 70)
print("## 6. 问题汇总")
print("=" * 70)

issues_found = []

# 检查文件位置不一致
locs = set(info["location"] for info in json_files.values())
if len(locs) > 1:
    issues_found.append("🔴 P0: JSON文件存放位置不一致 - 部分在experiment_data/，部分在experiment_data/generations/")

# 检查格式不一致
format_types = set(info["type"] for m, info in formats.items() if not m.startswith("_"))
if len(format_types) > 1:
    issues_found.append(f"🔴 P0: JSON格式不一致 - 存在{len(format_types)}种不同格式: {format_types}")

# 检查评分制不一致
score_systems = set()
for m, info in formats.items():
    if m.startswith("_"):
        continue
    if info["type"] == "array":
        score_systems.add("binary_sum")
    else:
        score_systems.add("continuous")
if len(score_systems) > 1:
    issues_found.append("🔴 P0: 评分标准不一致 - 早期模型使用0/1二元评分(总分5)，后期模型使用连续1-5分评分")

# 检查项目说明中的分数与实际数据是否匹配
print("\n### 项目说明文档记录 vs 实际JSON数据对比")
doc_scores = {
    "deepseek-v3.2": {"note": "4.2 (优化后)", "doc_values": {"A": 4.2}},
    "gemini-3.0-flash": {"note": "4.3", "doc_values": {"A": 4.3}},
    "gemini-3.0-pro": {"note": "3.9", "doc_values": {"A": 3.9}},
    "gemini-3.1-flash-lite": {"note": "4.1", "doc_values": {"A": 4.1}},
    "glm-5.0-turbo": {"note": "4.0", "doc_values": {"A": 4.0}},
    "gpt-5.4": {"note": "4.4", "doc_values": {"A": 4.4}},
    "kimi-k2.5": {"note": "3.8", "doc_values": {"A": 3.8}},
    "minimax-m2.7": {"note": "3.9", "doc_values": {"A": 3.9}},
    "hunyuan-2.0-thinking": {"note": "A=4.11, D=4.11, F=3.91", "doc_values": {"A": 4.11, "D": 4.11, "F": 3.91}},
    "claude-haiku-4.5": {"note": "A=4.15, D=3.95, F=3.75", "doc_values": {"A": 4.15, "D": 3.95, "F": 3.75}},
    "hunyuan-2.0-instruct": {"note": "A=4.29, D=4.08, F=3.88", "doc_values": {"A": 4.29, "D": 4.08, "F": 3.88}},
}

for model, doc in sorted(doc_scores.items()):
    if model in formats:
        actual = formats[model].get("averages", {})
        mismatches = []
        for g, doc_val in doc["doc_values"].items():
            act_val = actual.get(g)
            if act_val is not None and abs(act_val - doc_val) > 0.05:
                mismatches.append(f"{g}: 文档={doc_val}, 实际={act_val}")
        if mismatches:
            issues_found.append(f"🟡 P1: {model} 分数不匹配 - {'; '.join(mismatches)}")
            print(f"  {model:<28} ❌ {'; '.join(mismatches)}")
        else:
            print(f"  {model:<28} ✅ 分数一致")
    else:
        print(f"  {model:<28} ⚠️ 无JSON数据文件")

print()
for issue in issues_found:
    print(f"  {issue}")

if not issues_found:
    print("  ✅ 未发现问题")
else:
    print(f"\n  共发现 {len(issues_found)} 个问题")
