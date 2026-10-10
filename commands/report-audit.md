---
description: 报告发布前体检：31 条确定性规则扫描（指标口径/计算正确性/数据-图表对应/报告结构），输出 blocker/warning/nit 三级报告。
argument-hint: [报告目录] [--fail-on blocker|warning|nit]
---

# /lhg-biz-report:report-audit —— 报告发布前体检

用户输入在 `$ARGUMENTS` 中：`[报告目录] [--fail-on 级别]`。跑 `scripts/audit/report_audit.py`，再按 `lhg-br-deliver` skill 第 6 节人工评审清单过一遍脚本抓不到的。

## 流程

1. 先跑脚本：`python3 scripts/audit/report_audit.py --target <报告目录> --format text`（31 条规则：指标口径 8、计算 7、图表对应 6、报告结构 10），零 LLM 成本；
2. 发现分三级：**blocker**（必须修，对外发送前 hook 会拦截）、**warning**（修或写豁免理由）、**nit**（顺手修）；
3. 脚本之外，人工过一遍 lhg-br-deliver 第 6 节评审清单（结论先行、数字可溯源、图表诚实）。
4. blocker 清零才算过；改规则来过检算作弊。

## 报告目录约定

```
report/
├── metrics.json   # 指标字典（一名一定义）
├── data.csv       # 干净源数据（period 列 + 指标列）
├── charts.csv     # 图表数据（chart_id/title/metric/value/period/unit）
└── report.md      # 报告正文
```

## 用法

```
python3 scripts/audit/report_audit.py --target ./report --format json
python3 scripts/audit/report_audit.py --target ./report --format text --fail-on warning
```
