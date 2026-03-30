#!/usr/bin/env python3
"""
评估Claude-Haiku-4.5生成的代码
根据METHODOLOGY.md中的评估规则进行0/1二元评分
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

BASE_DIR = Path("/Users/erichztang/Downloads/古文运动/experiment_data")
MODEL_DIR = BASE_DIR / "generations" / "claude-haiku-4.5"

# 评估规则
EVALUATION_RULES = {
    'techScore': {
        'name': '技术栈正确',
        'check': lambda code: 'import React' in code and ': React.FC' in code
    },
    'formatScore': {
        'name': '输出形式正确',
        'check': lambda code: 'export default' in code and ('const ' in code or 'function ' in code)
    },
    'styleScore': {
        'name': '样式方案正确',
        'check': lambda code: 'className' in code  # Tailwind使用className
    },
    'depsScore': {
        'name': '依赖约束遵守',
        'check': lambda code: not any(lib in code for lib in [
            'axios', 'lodash', 'moment', 'dayjs', 'date-fns', 'react-router', 'redux', 
            'zustand', 'jotai', 'recoil', 'react-query', 'swr', 'framer-motion', 
            'react-spring', 'material-ui', '@mui', 'antd', 'chakra-ui', 'react-icons', 
            'heroicons', 'lucide-react', 'marked', 'react-markdown', 'remark', 
            'react-table', 'tanstack', 'formik', 'react-hook-form', 'yup', 'zod'
        ])
    },
}

# 功能关键词
KEYWORDS = {
    'T01': ['add', 'delete', 'filter', 'complete', 'done'],
    'T02': ['email', 'password', 'valid', 'error', 'pwd'],
    'T03': ['avatar', 'name', 'bio', 'follow'],
    'T04': ['item', 'quantity', 'price', 'checkout', 'qty'],
    'T05': ['temp', 'humid', 'wind', 'forecast'],
    'T06': ['split', 'editor', 'preview', 'markdown'],
    'T07': ['grid', 'lightbox', 'lazy'],
    'T08': ['message', 'input', 'send', 'scroll'],
    'T09': ['sort', 'paginat', 'search'],
    'T10': ['toggle', 'select', 'save'],
}

def evaluate_code(code: str, task_id: str) -> Dict[str, int]:
    """评估单个代码文件"""
    scores = {}
    
    # 基础技术评分
    scores['techScore'] = 1 if EVALUATION_RULES['techScore']['check'](code) else 0
    scores['formatScore'] = 1 if EVALUATION_RULES['formatScore']['check'](code) else 0
    scores['styleScore'] = 1 if EVALUATION_RULES['styleScore']['check'](code) else 0
    scores['depsScore'] = 1 if EVALUATION_RULES['depsScore']['check'](code) else 0
    
    # 功能完整性评分 (0/1)
    keywords = KEYWORDS.get(task_id, [])
    code_lower = code.lower()
    matched = sum(1 for kw in keywords if kw.lower() in code_lower)
    keyword_ratio = matched / len(keywords) if keywords else 1.0
    scores['funcScore'] = 1 if keyword_ratio >= 0.75 else 0
    
    scores['total'] = sum(scores.values())
    
    return scores

def main():
    print("=" * 70)
    print("Claude-Haiku-4.5 代码评估报告")
    print("=" * 70)
    
    results = []
    
    # 遍历所有任务和组
    for task_id in sorted([f'T{i:02d}' for i in range(1, 11)]):
        for group in ['A', 'D', 'F']:
            # 查找对应的tsx文件
            pattern = f"{MODEL_DIR}/{group}/{task_id}_*.tsx"
            import glob
            files = glob.glob(str(pattern))
            
            if not files:
                print(f"❌ 文件未找到: {pattern}")
                continue
            
            filepath = files[0]
            code = Path(filepath).read_text()
            
            # 评估
            scores = evaluate_code(code, task_id)
            
            # 获取任务名
            component_name = os.path.basename(filepath).replace('.tsx', '')
            
            # 记录结果
            result = {
                'component': component_name,
                'group': group,
                'techScore': scores['techScore'],
                'formatScore': scores['formatScore'],
                'funcScore': scores['funcScore'],
                'styleScore': scores['styleScore'],
                'depsScore': scores['depsScore'],
                'total': scores['total']
            }
            results.append(result)
            
            print(f"{component_name:<25} {group}  →  {scores['total']}/5  "
                  f"(Tech:{scores['techScore']} Format:{scores['formatScore']} "
                  f"Func:{scores['funcScore']} Style:{scores['styleScore']} Deps:{scores['depsScore']})")
    
    # 计算统计数据
    print("\n" + "=" * 70)
    print("统计汇总")
    print("=" * 70)
    
    for group in ['A', 'D', 'F']:
        group_results = [r for r in results if r['group'] == group]
        group_totals = [r['total'] for r in group_results]
        avg = sum(group_totals) / len(group_totals) if group_totals else 0
        full_score_count = sum(1 for t in group_totals if t == 5)
        
        print(f"组{group}: 平均分={avg:.2f}, 满分数={full_score_count}/10")
    
    # 保存结果
    output_file = BASE_DIR / "accuracy_results_claude-haiku-4.5.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ 评估结果已保存到: {output_file}")
    print(f"总计: {len(results)} 个文件评估完成")

if __name__ == '__main__':
    main()
