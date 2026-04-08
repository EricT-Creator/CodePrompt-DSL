#!/usr/bin/env python3
"""EXP-D Scoring Script — scores 36 S2 files, outputs exp_d_scores.csv"""
import csv, os, re, sys
from pathlib import Path

BASE = Path(__file__).parent / "generations"
TASKS = ["MC-BE-05", "MC-BE-06", "MC-PY-05", "MC-PY-06"]
ENCS = ["H", "NLc", "NLf"]
RUNS = [1, 2, 3]
CI = {"MC-BE-05": {2,3}, "MC-BE-06": {2,3}, "MC-PY-05": {2,3}, "MC-PY-06": {2,3}}

ALLOWED_BE = {"os","sys","time","datetime","typing","json","re","collections","math","io","uuid","hashlib","dataclasses","enum","functools","itertools","contextlib","copy","string","textwrap","abc","pathlib","urllib"}
ALLOWED_PY = set(list(ALLOWED_BE) + ["socket","ssl","struct","select","errno","signal","urllib"])

def _imports(code):
    mods = set()
    for m in re.finditer(r"^\s*(?:from|import)\s+([\w.]+)", code, re.M):
        mods.add(m.group(1).split(".")[0])
    return mods

def check_be_deps(code):
    mods = _imports(code)
    allowed = ALLOWED_BE | {"fastapi","uvicorn","pydantic","starlette"}
    return "PASS" if mods.issubset(allowed) else "FAIL"

def check_py_stdlib(code):
    mods = _imports(code)
    return "PASS" if mods.issubset(ALLOWED_PY) else "FAIL"

def has_type_hints(code):
    # Match public methods (not starting with _) across possibly multi-line signatures
    all_pub = re.findall(r"def (?!_)\w+\(", code)
    # Check for -> in the region after def until the colon
    pub_with_hints = len(re.findall(r"def (?!_)\w+\([^)]*\)\s*->\s*\w", code, re.DOTALL))
    if not all_pub: return "PASS"
    return "PASS" if pub_with_hints / len(all_pub) >= 0.5 else "FAIL"

# --- per-task scoring ---
def score_be05(code):
    c1 = "PASS" if re.search(r"from fastapi|import fastapi", code) else "FAIL"
    c2 = "FAIL" if re.search(r"import logging|from logging", code) else ("PASS" if "print(" in code else "FAIL")
    c3 = "FAIL" if re.search(r"BaseModel", code) else "PASS"
    c4 = check_be_deps(code)
    c5 = "PASS"
    c6 = "PASS" if not code.strip().startswith("```") else "FAIL"
    return [c1,c2,c3,c4,c5,c6]

def score_be06(code):
    c1 = "PASS" if re.search(r"from fastapi|import fastapi", code) else "FAIL"
    handlers = re.findall(r"@app\.\w+.*\n\s*(async\s+)?def\s+", code)
    c2 = "FAIL" if any("async" in (h or "") for h in handlers) else "PASS"
    c3 = "FAIL" if re.search(r"from pathlib|import pathlib|Path\(", code) else "PASS"
    c4 = check_be_deps(code)
    c5 = "PASS"
    c6 = "PASS" if not code.strip().startswith("```") else "FAIL"
    return [c1,c2,c3,c4,c5,c6]

def score_py05(code):
    c1 = check_py_stdlib(code)
    c2 = "FAIL" if re.search(r"import configparser|import json|import yaml|from configparser|from json|from yaml", code) else "PASS"
    c3 = "PASS" if re.search(r"__slots__", code) or re.search(r"NamedTuple", code) else "FAIL"
    c4 = has_type_hints(code)
    c5 = "PASS" if re.search(r"class\s+ConfigError", code) and re.search(r"raise\s+ConfigError", code) else "FAIL"
    c6 = "PASS" if re.search(r"class\s+\w+", code) else "FAIL"
    return [c1,c2,c3,c4,c5,c6]

def score_py06(code):
    c1 = check_py_stdlib(code)
    c2_fail = bool(re.search(r"import urllib|from urllib|import http\.client|from http", code))
    c2_socket = bool(re.search(r"import socket", code))
    c2 = "FAIL" if c2_fail else ("PASS" if c2_socket else "FAIL")
    c3 = "FAIL" if re.search(r'''f["']|f"""''', code) else "PASS"
    c4 = has_type_hints(code)
    c5 = "PASS" if re.search(r"@dataclass", code) and re.search(r"class\s+Response", code) else "FAIL"
    c6 = "PASS" if re.search(r"class\s+\w+", code) else "FAIL"
    return [c1,c2,c3,c4,c5,c6]

SCORERS = {"MC-BE-05": score_be05, "MC-BE-06": score_be06, "MC-PY-05": score_py05, "MC-PY-06": score_py06}

def main():
    rows = []
    for task in TASKS:
        scorer = SCORERS[task]
        ci_set = CI[task]
        for enc in ENCS:
            for run in RUNS:
                fpath = BASE / task / ("%s_run%d" % (enc, run)) / "S2_implementer.py"
                if not fpath.exists():
                    rows.append([task, enc, run] + ["SKIP"]*6 + ["","","","MISSING","file not found"])
                    continue
                code = fpath.read_text(encoding="utf-8")
                scores = scorer(code)
                total = len(scores)
                passed = scores.count("PASS")
                csr = round(passed / total, 3) if total else 0
                normal_idx = [i for i in range(6) if (i+1) not in ci_set]
                counter_idx = [i for i in range(6) if (i+1) in ci_set]
                n_pass = sum(1 for i in normal_idx if scores[i] == "PASS")
                c_pass = sum(1 for i in counter_idx if scores[i] == "PASS")
                csr_n = round(n_pass / len(normal_idx), 3) if normal_idx else 0
                csr_c = round(c_pass / len(counter_idx), 3) if counter_idx else 0
                fails = [("C%d" % (i+1)) for i in range(6) if scores[i] == "FAIL"]
                notes = "; ".join(fails) if fails else ""
                status = "PASS" if all(s == "PASS" for s in scores) else "PARTIAL"
                rows.append([task, enc, run] + scores + [csr, csr_n, csr_c, status, notes])
    out = Path(__file__).parent / "exp_d_scores.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["task","encoding","run","C1","C2","C3","C4","C5","C6","CSR_obj","CSR_normal","CSR_counter","status","notes"])
        w.writerows(rows)
    print("Wrote %d rows to %s" % (len(rows), out))
    # summary
    total_checks = len(rows) * 6
    total_fail = sum(r[3:9].count("FAIL") for r in rows)
    print("Total constraint checks: %d, Failures: %d (%.1f%%)" % (total_checks, total_fail, 100*total_fail/total_checks))
    for task in TASKS:
        task_rows = [r for r in rows if r[0] == task]
        for ci in sorted(CI[task]):
            fails = sum(1 for r in task_rows if r[2+ci] == "FAIL")
            print("  %s C%d: %d/%d FAIL" % (task, ci, fails, len(task_rows)))

if __name__ == "__main__":
    main()
