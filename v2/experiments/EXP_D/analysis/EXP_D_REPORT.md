# EXP-D Analysis Report
## Non-CSS Counter-Intuitive Constraint Extension — Results

**Date**: 2026-04-08  
**Model**: Claude-Opus-4.6  
**Scale**: 4 tasks × 3 encodings × 3 runs = 36 pipelines  

---

## 1. Overall Results

| Metric | Value |
|--------|-------|
| Total constraint checks | 216 (36 pipelines × 6 constraints) |
| Total PASS | 207 (95.8%) |
| Total FAIL | 9 (4.2%) |
| Pipelines with all PASS | 27/36 (75.0%) |
| Pipelines with any FAIL | 9/36 (25.0%) |

## 2. Failure Breakdown by Task

| Task | Counter-Intuitive Constraints | C2 Fail Rate | C3 Fail Rate | Overall CSR |
|------|------------------------------|-------------|-------------|-------------|
| MC-BE-05 | C2: 禁logging, C3: 禁Pydantic | 0/9 (0%) | 0/9 (0%) | 1.000 |
| MC-BE-06 | C2: 禁async def, C3: 禁pathlib | 0/9 (0%) | 0/9 (0%) | 1.000 |
| MC-PY-05 | C2: 禁configparser, C3: 禁dict | 0/9 (0%) | 0/9 (0%) | 1.000 |
| MC-PY-06 | C2: 禁urllib, C3: 禁f-string | **9/9 (100%)** | 0/9 (0%) | 0.833 |

## 3. Encoding Effect on Failures

| Encoding | Total Fails | MC-PY-06 C2 Fails |
|----------|------------|-------------------|
| H (Header) | 3 | 3/3 (100%) |
| NLc (NL-compact) | 3 | 3/3 (100%) |
| NLf (NL-full) | 3 | 3/3 (100%) |

**Encoding has zero effect on failure rate.** All three encodings produce identical failure patterns, consistent with the null result from EXP-C.

## 4. Analysis of the MC-PY-06 C2 Failure

### What happened
All 9 MC-PY-06 files use `from urllib.parse import urlparse, urlencode`. The constraint says "DO NOT use urllib" and the scoring regex matches `from urllib`.

### Failure mechanism: Partial Default Bias
- The model **did** use `import socket` for HTTP communication (constraint intent satisfied)
- But it **also** used `urllib.parse` for URL parsing — a convenience function from the urllib package
- This is a **partial compliance** pattern: the model understands the core prohibition (no HTTP via urllib) but reaches for a related stdlib utility (URL parsing) that shares the banned namespace

### Comparison with EXP-C CSS failures
| Aspect | EXP-C CSS Failures | EXP-D urllib.parse Failures |
|--------|-------------------|---------------------------|
| Domain | Frontend (CSS Modules) | Python stdlib (urllib) |
| Failure rate | 81-90% for CSS constraint | 100% for urllib constraint |
| Mechanism | Model defaults to inline styles/Tailwind | Model defaults to urllib.parse for URL parsing |
| Core intent | Model ignores CSS Modules entirely | Model uses socket but adds urllib.parse |
| Encoding effect | None (H ≈ NLc ≈ NLf) | None (H ≈ NLc ≈ NLf) |

### Key difference
EXP-C failures = model **ignores** the constraint entirely (uses inline styles instead of CSS Modules).  
EXP-D MC-PY-06 = model **partially complies** (uses socket for HTTP) but reaches for a banned helper (urllib.parse for URL parsing).

## 5. Statistical Tests

### 5.1 Counter-intuitive vs Normal constraint failure rate

| Constraint Type | Total Checks | Fails | Failure Rate |
|----------------|-------------|-------|-------------|
| Normal (C1,C4,C5,C6) | 144 | 0 | 0.0% |
| Counter-intuitive (C2,C3) | 72 | 9 | 12.5% |

**Fisher exact test**: p < 0.001 (counter-intuitive constraints fail significantly more often than normal ones)

### 5.2 Encoding effect (Kruskal-Wallis on CSR across H/NLc/NLf)
- H mean CSR: 0.958
- NLc mean CSR: 0.958
- NLf mean CSR: 0.958

All identical → KW test not applicable (zero variance). **No encoding effect.**

### 5.3 Cross-task consistency
- 3/4 tasks: 0% counter-intuitive failure (BE-05, BE-06, PY-05)
- 1/4 tasks: 100% C2 failure (PY-06)

The failure is **task-specific**, not encoding-specific.

## 6. Implications for the Paper

### What EXP-D adds to the argument

1. **Default bias extends beyond CSS** — MC-PY-06 shows urllib.parse is a default tool the model reaches for even when prohibited. This is the same mechanism as CSS Modules failures in EXP-C but in a different domain (Python stdlib).

2. **Zero-result for encoding is robust** — Even with 4 new non-CSS tasks, encoding form (H/NLc/NLf) makes no difference to constraint compliance. All failures are 100% consistent across encodings.

3. **Constraint difficulty is task-specific** — The "禁 urllib" constraint was 100% failed while "禁 logging", "禁 Pydantic", "禁 async def", "禁 pathlib", "禁 configparser", "禁 dict", "禁 f-string" were all 0% failed. Default bias depends on how deeply the banned tool is embedded in the model's default toolkit for the task.

### Nuance: urllib.parse vs urllib.request
The MC-PY-06 failures are arguably "softer" than EXP-C CSS failures:
- Model did use socket for HTTP (core intent met)
- urllib.parse is a URL-parsing utility, not an HTTP client
- Whether this counts as a "real" failure depends on constraint interpretation

This nuance should be discussed in the paper — it illustrates the **boundary between constraint letter and constraint spirit**.

## 7. Combined EXP-C + EXP-D Counter-Intuitive Failure Summary

| Source | Domain | Counter-Intuitive Checks | Fails | Rate |
|--------|--------|-------------------------|-------|------|
| EXP-C | CSS Modules (FE) | 168 | 36 | 21.4% |
| EXP-C | Non-CSS (BE/PY) | 168 | 11 | 6.5% |
| EXP-D | Non-CSS (BE/PY) | 72 | 9 | 12.5% |
| **EXP-C+D Non-CSS** | **Combined** | **240** | **20** | **8.3%** |

**Non-CSS counter-intuitive failure rate ≈ 8.3%**, confirming that default bias is not limited to CSS, though CSS remains the most failure-prone domain.

---

*Generated: 2026-04-08, EXP-D scoring pipeline*
