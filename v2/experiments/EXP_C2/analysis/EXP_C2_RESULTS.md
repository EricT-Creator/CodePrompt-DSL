# EXP-C2 Results

> 日期: 2026-04-04 00:40

## 结果：四种传播模式的 CSR 完全相同

| Mode | CSR-obj | Counter-intuitive CSR | n |
|------|---------|----------------------|---|
| R (Reinjection) | 0.944 | 0.833 | 12 |
| H (Handoff-only) | 0.944 | 0.833 | 12 |
| S (Structured checklist) | 0.944 | 0.833 | 12 |
| SN (NL checklist) | 0.944 | 0.833 | 12 |

**Δ(H-R) = 0.000 — 没有衰减。**
**Δ(S-SN) = 0.000 — 结构化和 NL checklist 没有区别。**

所有差异来自同一个约束：MC-BE-03 的 C2 (asyncio.Queue)，在全部 48 次调用中一致 FAIL (4/12 FAIL per mode)。

## 按编码和任务分

编码间零差异 (H=0.944, NLf=0.944)。
任务间：FE-01=1.000, BE-03=0.833, PY-03=1.000。

## 解读

Opus 在 handoff-only 条件下也能完美遵循约束——它从 S1 方案的自然语言描述中成功提取了所有约束信息。传播模式不是瓶颈，模型能力才是。

这正是评审预警的漏洞 5："Opus 可能太强了，靠 world knowledge 自己补约束。"
