# EXP-C Prompt 模板目录

## 结构

每个任务一个子目录，每个子目录包含 9 个 prompt 文件：

```
{task_id}/
├── S1_header.md              ← S1 Architect, Header 编码
├── S1_nl_compact.md          ← S1 Architect, NL-compact 编码
├── S1_nl_full.md             ← S1 Architect, NL-full 编码
├── S2_header_template.md     ← S2 Implementer, Header（含 {S1_OUTPUT} 占位符）
├── S2_nl_compact_template.md ← S2 Implementer, NL-compact
├── S2_nl_full_template.md    ← S2 Implementer, NL-full
├── S3_header_template.md     ← S3 Auditor, Header（含 {S2_OUTPUT} 占位符）
├── S3_nl_compact_template.md ← S3 Auditor, NL-compact
└── S3_nl_full_template.md    ← S3 Auditor, NL-full
```

## S1 prompt 直接使用

S1 的 3 个 prompt 可直接粘贴给模型。

## S2/S3 prompt 需要填充

S2 的 `{S1_OUTPUT}` 占位符需替换为对应管线 S1 的实际输出。
S3 的 `{S2_OUTPUT}` 占位符需替换为对应管线 S2 的实际输出。

**填充由砚在 Phase 间隔自动完成。**

## Prompt 对齐原则

三种编码条件的 prompt 严格对齐：
- 相同的 Role instruction
- 相同的 User Requirement
- 相同的 Include 列表 / Output format
- **唯一不同：约束表达段落**

详见 `EXP_C_DESIGN.md` §7.1 的 Prompt 对齐防污染声明。

## 生成

- `MC-FE-01/` 为手工编写的范例
- 其余 11 个任务由 `generate_exp_c_prompts.py` 脚本生成

*最后更新：2026-04-01*
