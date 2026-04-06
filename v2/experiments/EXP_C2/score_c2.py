#!/usr/bin/env python3
"""EXP-C2: Score S2 code against constraints. Reuses EXP-C scoring logic."""
import csv, re, sys
from pathlib import Path

# Import scoring functions from EXP-C
sys.path.insert(0, str(Path(__file__).parent.parent / "EXP_C"))
from score_s2_binary import (
    fe01_c1, fe01_c2, fe01_c3, fe01_c4, fe01_c5, fe01_c6,
    be03_c1, be03_c2, be03_c3, be03_c4, be03_c5, be03_c6,
    py03_c1, py03_c2, py03_c3, py03_c4, py03_c5, py03_c6,
)

GENS = Path(__file__).parent / "generations"
OUT = Path(__file__).parent / "analysis" / "exp_c2_results.csv"

TASKS = ["MC-FE-01", "MC-BE-03", "MC-PY-03"]
ENCS = ["H", "NLf"]
MODES = ["R", "H", "S", "SN"]
RUNS = [1, 2]

SCORERS = {
    "MC-FE-01": [fe01_c1, fe01_c2, fe01_c3, fe01_c4, fe01_c5, fe01_c6],
    "MC-BE-03": [be03_c1, be03_c2, be03_c3, be03_c4, be03_c5, be03_c6],
    "MC-PY-03": [py03_c1, py03_c2, py03_c3, py03_c4, py03_c5, py03_c6],
}

EXT = {"MC-FE-01": "tsx", "MC-BE-03": "py", "MC-PY-03": "py"}

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["task","encoding","mode","run","C1","C2","C3","C4","C5","C6",
              "CSR_obj","CSR_normal","CSR_counter","notes","status"]
    rows = []

    for task in TASKS:
        for enc in ENCS:
            for mode in MODES:
                for run in RUNS:
                    dir_name = f"{enc}_{mode}_run{run}"
                    ext = EXT[task]
                    fpath = GENS / task / dir_name / f"S2_implementer.{ext}"
                    
                    row = {"task":task,"encoding":enc,"mode":mode,"run":run}
                    
                    if not fpath.exists():
                        row["status"] = "MISSING"
                        for i in range(1,7): row[f"C{i}"] = "N/A"
                        row.update({"CSR_obj":"N/A","CSR_normal":"N/A","CSR_counter":"N/A","notes":"file missing"})
                        rows.append(row)
                        continue
                    
                    code = fpath.read_text(encoding="utf-8", errors="replace")
                    
                    # Strip markdown wrapping if present
                    if code.strip().startswith("```"):
                        lines = code.strip().split("\n")
                        # Remove first and last ``` lines
                        if lines[0].startswith("```"):
                            lines = lines[1:]
                        if lines and lines[-1].strip() == "```":
                            lines = lines[:-1]
                        code = "\n".join(lines)
                    
                    scorers = SCORERS[task]
                    results = []
                    notes_parts = []
                    for i, scorer in enumerate(scorers):
                        val, note = scorer(code)
                        row[f"C{i+1}"] = val
                        results.append(val)
                        if note: notes_parts.append(f"C{i+1}:{note}")
                    
                    csr = sum(results) / 6
                    normal = sum(results[i] for i in [0,3,4,5]) / 4  # C1,C4,C5,C6
                    counter = sum(results[i] for i in [1,2]) / 2      # C2,C3
                    
                    row["CSR_obj"] = f"{csr:.3f}"
                    row["CSR_normal"] = f"{normal:.3f}"
                    row["CSR_counter"] = f"{counter:.3f}"
                    row["notes"] = "; ".join(notes_parts)
                    row["status"] = "SCORED"
                    rows.append(row)

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # ═══ Analysis ═══
    scored = [r for r in rows if r["status"]=="SCORED"]
    print(f"Total: {len(rows)} | Scored: {len(scored)} | Missing: {len(rows)-len(scored)}")
    
    # By mode
    print("\n━━━ CSR by Propagation Mode ━━━")
    for mode in MODES:
        mr = [r for r in scored if r["mode"]==mode]
        if mr:
            csr = sum(float(r["CSR_obj"]) for r in mr)/len(mr)
            counter = sum(float(r["CSR_counter"]) for r in mr)/len(mr)
            print(f"  {mode:3s}: CSR={csr:.3f} Counter={counter:.3f} (n={len(mr)})")
    
    # By mode × encoding
    print("\n━━━ CSR by Mode × Encoding ━━━")
    print(f"  {'Mode':4s} {'H':>10s} {'NLf':>10s}")
    for mode in MODES:
        vals = []
        for enc in ENCS:
            mr = [r for r in scored if r["mode"]==mode and r["encoding"]==enc]
            if mr:
                csr = sum(float(r["CSR_obj"]) for r in mr)/len(mr)
                vals.append(f"{csr:.3f}({len(mr)})")
            else:
                vals.append("---")
        print(f"  {mode:4s} {vals[0]:>10s} {vals[1]:>10s}")
    
    # By mode × task
    print("\n━━━ CSR by Mode × Task ━━━")
    print(f"  {'Mode':4s} {'FE-01':>10s} {'BE-03':>10s} {'PY-03':>10s}")
    for mode in MODES:
        vals = []
        for task in TASKS:
            mr = [r for r in scored if r["mode"]==mode and r["task"]==task]
            if mr:
                csr = sum(float(r["CSR_obj"]) for r in mr)/len(mr)
                vals.append(f"{csr:.3f}")
            else:
                vals.append("---")
        print(f"  {mode:4s} {vals[0]:>10s} {vals[1]:>10s} {vals[2]:>10s}")
    
    # Per-constraint by mode
    print("\n━━━ Per-constraint pass rate by Mode ━━━")
    for mode in MODES:
        mr = [r for r in scored if r["mode"]==mode]
        cs = []
        for i in range(1,7):
            passed = sum(1 for r in mr if r[f"C{i}"]== 1)
            cs.append(f"C{i}={passed}/{len(mr)}")
        print(f"  {mode}: {' '.join(cs)}")

    # Key comparison: R vs H
    print("\n━━━ KEY: R vs H (does handoff decay exist?) ━━━")
    r_rows = [r for r in scored if r["mode"]=="R"]
    h_rows = [r for r in scored if r["mode"]=="H"]
    r_csr = sum(float(r["CSR_obj"]) for r in r_rows)/len(r_rows)
    h_csr = sum(float(r["CSR_obj"]) for r in h_rows)/len(h_rows)
    print(f"  R (Reinjection): CSR={r_csr:.3f} (n={len(r_rows)})")
    print(f"  H (Handoff):     CSR={h_csr:.3f} (n={len(h_rows)})")
    print(f"  Δ(H-R):          {h_csr-r_csr:+.3f}")
    print(f"  {'⚠️ DECAY DETECTED' if h_csr < r_csr - 0.05 else '≈ NO SIGNIFICANT DECAY' if abs(h_csr-r_csr)<0.05 else '↑ HANDOFF BETTER?!'}")

    # S vs SN
    print("\n━━━ KEY: S vs SN (structured vs NL checklist) ━━━")
    s_rows = [r for r in scored if r["mode"]=="S"]
    sn_rows = [r for r in scored if r["mode"]=="SN"]
    s_csr = sum(float(r["CSR_obj"]) for r in s_rows)/len(s_rows)
    sn_csr = sum(float(r["CSR_obj"]) for r in sn_rows)/len(sn_rows)
    print(f"  S (Structured):  CSR={s_csr:.3f}")
    print(f"  SN (NL checklist): CSR={sn_csr:.3f}")
    print(f"  Δ(S-SN):         {s_csr-sn_csr:+.3f}")

    print(f"\nCSV: {OUT}")

if __name__ == "__main__":
    main()
