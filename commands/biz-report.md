---
description: 原始数据一条龙：表格/CSV 接入清洗→指标口径统一→洞察提炼→图文报告/PPT，交付前必须跑报告审计。
argument-hint: [数据文件路径] [报告主题]
---

# /lhg-biz-report:biz-report —— 原始数据到图文报告一条龙

用户输入在 `$ARGUMENTS` 中：`[数据文件路径] [报告主题]`。数据文件缺省时先问用户要。

本插件是**组合工作流**：数据处理复用 `lhg-excel` 组织插件的方法论（`lhg-ex-clean` 清洗五步法、`lhg-ex-recalc` 复算），报告生成复用 `lhg-ppt` 组织插件的方法论（`lhg-ppt-outline` 金字塔大纲、`lhg-ppt-build` 页面构建）。本插件的 4 个 skill 只解决"分析"本身，不管"洗表"和"画页面"的细节——细节去那两个插件里找。

全程加载本插件 skills：`lhg-br-intake`（数据接入）、`lhg-br-metric`（口径统一）、`lhg-br-insight`（洞察提炼）、`lhg-br-deliver`（报告交付）。分析工作可分派给 `data-analyst` agent，完成后必须跑 `report-audit`。

## 流程

### 1. 数据接入（加载 lhg-br-intake，复用 lhg-ex-clean）
- 拿到原始表格/CSV，先诊断后清洗（表头、空值、重复、类型混杂、junk 行），输出干净数据 + 数据字典。
- **硬规则**：清洗前备份原文件，口径问题先记下来，不许悄悄改数。

### 2. 指标口径统一（加载 lhg-br-metric）
- 输出 `metrics.json`（指标字典）：每个指标一名一定义一单位一周期一来源。
- 同名指标定义冲突 → 开"口径对齐会"（问用户），不许各说各话。
- **硬规则**：metrics.json 没定，洞察不许开工。

### 3. 洞察提炼（加载 lhg-br-insight）
- 四个对比框架跑一遍：同比、环比、占比、结构拆解；每个数字过"SO WHAT"三问。
- 输出洞察清单（观点 + 数据支撑 + 口径标注），用户确认后再写报告。

### 4. 报告交付（加载 lhg-br-deliver，复用 lhg-ppt-outline）
- 结论先行的大纲 → 用户确认 → 生成图文报告（Markdown）或 PPT（走 lhg-ppt 方法论）。
- 图表数据必须与源数据对得上（audit 的 CHART-* 会查）。

### 5. 报告审计
- 跑 `/lhg-biz-report:report-audit`，blocker 清零才交付。
- 对外发送（邮件/发布）前 hook 会自动校验报告包完整性，被拦截就修报告，不要关 hook。
- 交付物：干净数据 + `metrics.json` + 报告/PPT + 审计报告（四件套，缺一不可）。

## 硬规则
- 口径没统一就写报告 → 不许（这是本插件与"数字打架"的分界线）。
- 报告里的同比/环比数字与源数据对不上 → 不许交付。
- 为通过审计改审计脚本规则 → 作弊，不许。
