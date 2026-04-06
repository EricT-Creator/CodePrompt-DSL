#!/usr/bin/env python3
"""EXP-C2b: Score DeepSeek S2 weak-model probe."""
import csv, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "EXP_C"))
from score_s2_binary import (
    fe01_c1, fe01_c2, fe01_c3, fe01_c4, fe01_c5, fe01_c6,
    be03_c1, be03_c2, be03_c3, be03_c4, be03_c5, be03_c6,
    py03_c1, py03_c2, py03_c3, py03_c4, py03_c5, py03_c6,
)

GENS = Path(__file__).parent / "generations"
OUT = Path(__file__).parent / "analysis" / "exp_c2b_results.csv"

TASKS = ["MC-FE-01", "MC-BE-03", "MC-PY-03"]
MODES = ["R", "H", "S"]
RUNS = [1, 2]
EXT = {"MC-FE-01": "tsx", "MC-BE-03": "py", "MC-PY-03": "py"}

SCORERS = {
    "MC-FE-01": [fe01_c1, fe01_c2, fe01_c3, fe01_c4, fe01_c5, fe01_c6],
    "MC-BE-03": [be03_c1, be03_c2, be03_c3, be03_c4, be03_c5, be03_c6],
    "MC-PY-03": [py03_c1, py03_c2, py03_c3, py03_c4, py03_c5, py03_c6],
}

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["task","mode","run","model","C1","C2","C3","C4","C5","C6",
              "CSR_obj","CSR_normal","CSR_counter","notes","status"]
    rows = []

    for task in TASKS:
        for mode in MODES:
            for run in RUNS:
                dir_name = f"H_{mode}_ds_run{run}"
                ext = EXT[task]
                fpath = GENS / task / dir_name / f"S2_implementer.{ext}"
                
                row = {"task":task,"mode":mode,"run":run,"model":"deepseek"}
                
                if not fpath.exists():
                    row["status"] = "MISSING"
                    for i in range(1,7): row[f"C{i}"] = "N/A"
                    row.update({"CSR_obj":"N/A","CSR_normal":"N/A","CSR_counter":"N/A","notes":"missing"})
                    rows.append(row)
                    continue
                
                code = fpath.read_text(encoding="utf-8", errors="replace")
                if code.strip().startswith("```"):
                    lines = code.strip().split("\n")
                    if lines[0].startswith("```"): lines = lines[1:]
                    if lines and lines[-1].strip() == "```": lines = lines[:-1]
                    code = "\n".join(lines)
                
                scorers = SCORERS[task]
                results = []; notes_parts = []
                for i, scorer in enumerate(scorers):
                    val, note = scorer(code)
                    row[f"C{i+1}"] = val; results.append(val)
                    if note: notes_parts.append(f"C{i+1}:{note}")
                
                row["CSR_obj"] = f"{sum(results)/6:.3f}"
                row["CSR_normal"] = f"{sum(results[i] for i in [0,3,4,5])/4:.3f}"
                row["CSR_counter"] = f"{sum(results[i] for i in [1,2])/2:.3f}"
                row["notes"] = "; ".join(notes_parts)
                row["status"] = "SCORED"
                rows.append(row)

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

    scored = [r for r in rows if r["status"]=="SCORED"]
    print(f"Total: {len(rows)} | Scored: {len(scored)}\n")

    # By mode
    print("━━━ DeepSeek CSR by Mode ━━━")
    for mode in MODES:
        mr = [r for r in scored if r["mode"]==mode]
        csr = sum(float(r["CSR_obj"]) for r in mr)/len(mr)
        counter = sum(float(r["CSR_counter"]) for r in mr)/len(mr)
        print(f"  {mode:3s}: CSR={csr:.3f} Counter={counter:.3f} (n={len(mr)})")

    # By mode × task
    print("\n━━━ DeepSeek CSR by Mode × Task ━━━")
    print(f"  {'Mode':4s} {'FE-01':>8s} {'BE-03':>8s} {'PY-03':>8s}")
    for mode in MODES:
        vals = []
        for task in TASKS:
            mr = [r for r in scored if r["mode"]==mode and r["task"]==task]
            csr = sum(float(r["CSR_obj"]) for r in mr)/len(mr) if mr else 0
            vals.append(f"{csr:.3f}")
        print(f"  {mode:4s} {vals[0]:>8s} {vals[1]:>8s} {vals[2]:>8s}")

    # Per-constraint
    print("\n━━━ Per-constraint pass rate by Mode ━━━")
    for mode in MODES:
        mr = [r for r in scored if r["mode"]==mode]
        cs = []
        for i in range(1,7):
            passed = sum(1 for r in mr if r[f"C{i}"]==1)
            cs.append(f"C{i}={passed}/{len(mr)}")
        print(f"  {mode}: {' '.join(cs)}")

    # KEY comparison with Opus
    print("\n━━━ KEY: DeepSeek vs Opus (same conditions) ━━━")
    # Load Opus C2 results for H encoding
    c2_path = Path(__file__).parent / "analysis" / "exp_c2_results.csv"
    if c2_path.exists():
        with open(c2_path) as f:
            opus_rows = [r for r in csv.DictReader(f) if r["encoding"]=="H" and r["status"]=="SCORED"]
        for mode in MODES:
            opus_mr = [r for r in opus_rows if r["mode"]==mode]
            ds_mr = [r for r in scored if r["mode"]==mode]
            if opus_mr and ds_mr:
                o_csr = sum(float(r["CSR_obj"]) for r in opus_mr)/len(opus_mr)
                d_csr = sum(float(r["CSR_obj"]) for r in ds_mr)/len(ds_mr)
                print(f"  {mode}: Opus={o_csr:.3f} DeepSeek={d_csr:.3f} Δ={d_csr-o_csr:+.3f}")

    # KEY: R vs H for DeepSeek
    print("\n━━━ KEY: R vs H (handoff decay in weak model?) ━━━")
    r_rows = [r for r in scored if r["mode"]=="R"]
    h_rows = [r for r in scored if r["mode"]=="H"]
    r_csr = sum(float(r["CSR_obj"]) for r in r_rows)/len(r_rows)
    h_csr = sum(float(r["CSR_obj"]) for r in h_rows)/len(h_rows)
    delta = h_csr - r_csr
    print(f"  R: {r_csr:.3f} | H: {h_csr:.3f} | Δ={delta:+.3f}")
    if abs(delta) < 0.01:
        print("  → NO DECAY (even with weak model)")
    elif delta < -0.05:
        print("  → ⚠️ DECAY DETECTED in weak model!")
    else:
        print(f"  → Small difference, direction: {'decay' if delta<0 else 'improvement'}")

    # S recovery
    s_rows = [r for r in scored if r["mode"]=="S"]
    s_csr = sum(float(r["CSR_obj"]) for r in s_rows)/len(s_rows)
    print(f"  S: {s_csr:.3f} | Δ(S-H)={s_csr-h_csr:+.3f}")

    print(f"\nCSV: {OUT}")

if __name__ == "__main__":
    main()
