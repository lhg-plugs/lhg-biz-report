<!-- About 简介（推送后填写到仓库 About 栏）：
商业分析报告专家：原始数据到图文报告一条龙 ｜ 一键安装：/plugin marketplace add lhg-plugs/lhg-biz-report
-->
<!-- topics（推送后打）：claude-code, claude-plugin, agent-skills, business-analysis, reporting -->

# lhg-biz-report：商业分析报告专家

> **一句话介绍**：原始数据到图文报告一条龙——数据接入清洗→指标口径统一→洞察提炼→图文报告/PPT 生成，复用 lhg-excel 与 lhg-ppt 的方法论，31 条确定性规则把关，口径不统一不许写报告。
>
> **一键安装**：在 Claude Code 里运行
> ```
> /plugin marketplace add lhg-plugs/lhg-biz-report
> /plugin install lhg-biz-report@lhg-plugs
> ```

## 它是什么

`lhg-biz-report` 是一个 Claude Code 插件（plugin 为主、skill 为辅），专为"有数据、缺报告"的小白设计。它是一个**组合工作流**插件：

- **复用** `lhg-plugs/lhg-excel` 的方法论：数据清洗走 `lhg-ex-clean` 五步法、复算走 `lhg-ex-recalc` 思路（本插件的 `lhg-br-intake` 只定输入输出契约，细节以 lhg-excel 为准）
- **复用** `lhg-plugs/lhg-ppt` 的方法论：报告大纲走 `lhg-ppt-outline` 金字塔结构、PPT 生成走 `lhg-ppt-build`（本插件的 `lhg-br-deliver` 只定商业报告的内容标准）
- **本插件原创**：指标口径统一（`lhg-br-metric` + `metrics.json` 字典规范）与洞察提炼（`lhg-br-insight` 四个对比框架 + SO WHAT 三问），以及 31 条报告审计规则

包含：

- **3 个命令**（小白入口）：`biz-report` 原始数据一条龙，`metric-define` 指标口径统一，`report-audit` 报告发布前体检
- **4 个平台中立 skill**（方法论，可移植到豆包/Workbuddy 等 agent 平台）：数据接入、口径统一、洞察提炼、报告交付
- **2 个专家 agent**：数据分析师、独立报告质检员
- **1 个硬门 hook**：对外发送前自动校验报告包完整性（可一键豁免，不骚扰）
- **31 条确定性自查规则**：指标口径 8、计算正确性 7、数据-图表对应 6、报告结构 10，纯 Python、零第三方依赖，5 秒出结果

工作流：`biz-report`（一条龙）→ `report-audit`（查一遍），也可以只用 `metric-define` 先统一口径。

## 3 个命令用法

| 命令 | 作用 | 示例 |
|---|---|---|
| `/lhg-biz-report:biz-report` | 原始数据一条龙：清洗→口径→洞察→报告/PPT | `/lhg-biz-report:biz-report ./sales.xlsx "Q3 经营分析"` |
| `/lhg-biz-report:metric-define` | 指标口径统一：输出 metrics.json | `/lhg-biz-report:metric-define ./sales.xlsx` |
| `/lhg-biz-report:report-audit` | 报告发布前体检（脚本 + 人工评审清单） | `/lhg-biz-report:report-audit ./report` |

## 自查说明

自查 = 确定性脚本（机器）+ 人工评审清单（人）：

1. 先跑 `scripts/audit/report_audit.py`（31 条规则：指标口径 8、计算 7、图表对应 6、报告结构 10），零 LLM 成本；
2. 发现分三级：**blocker**（必须修，对外发送前 hook 会拦截）、**warning**（修或写豁免理由）、**nit**（顺手修）；
3. 再按 `lhg-br-deliver` skill 第 6 节评审清单过一遍脚本抓不到的（30 秒结论测试、数字抽查、图表诚实）。

blocker 清零才算做完；为清零改规则算作弊，不许。

## 目录结构

```
lhg-biz-report/
├── .claude-plugin/          # plugin.json（插件清单）+ marketplace.json（本仓即市场）
├── commands/                # 3 个命令：biz-report / metric-define / report-audit
├── skills/                  # 4 个平台中立 skill（接入/口径/洞察/交付）
├── agents/                  # 2 个专家 agent（data-analyst / report-reviewer）
├── hooks/                   # 1 个硬门（发送前报告包校验）+ 豁免说明
├── scripts/audit/           # 31 条确定性自查规则（零第三方依赖）
├── fixtures/                # 冒烟测试用例（坏/好对照）
├── smoke_test.py            # 一键冒烟测试
├── ATTRIBUTION.md           # 灵感来源与许可声明（含复用关系）
└── LICENSE                  # MIT
```

## 什么时候用 / 什么时候不用（FAQ）

**什么时候用：**

- 你有一堆表格，但老板要的是一份"能看的报告"时 → 用 `/lhg-biz-report:biz-report`，一条龙走完
- 你们部门对"营收"有三种算法，报告里数字老打架时 → 先用 `/lhg-biz-report:metric-define` 统一口径
- 报告发出前怕翻车（同比算错、图和表对不上、结论没数据支撑）时 → 跑 `/lhg-biz-report:report-audit`
- 你想给团队立一套"口径不统一不许写报告"的纪律时 → 它的 hook 硬门与审计脚本开箱即用

**什么时候不用：**

- 你要的是实时 BI 看板/数据大屏 → 本插件做的是"一次性分析报告"，看板请找 BI 工具
- 你的数据在数据库里且需要写 SQL 取数 → 先取数成表格再进本插件（本插件不管取数）
- 你只是想把表格做漂亮（调格式、做透视表）→ 直接用 `lhg-plugs/lhg-excel`，不用绕到本插件

**风险点诚实说明：**

- **审计规则是启发式**：31 条规则覆盖的是"常见翻车点"，同比/环比重算依赖 period 列的顺序，数据缺失时间段时结论可能失真；"30 秒结论测试"这类主观项必须人眼过
- **口径拍板需要真人**：冲突对齐会必须用户拍板，AI 不能替你决定"营收含不含税"
- **组合工作流的前置要求**：数据清洗细节与 PPT 页面构建分别复用 lhg-excel / lhg-ppt 的方法论，两者是独立插件，需单独安装（见复用声明）
- **因果推断的边界**：本插件只做描述性分析（发生了什么），不做因果归因（为什么发生）——"因为做了活动所以涨了"这类结论需要专门的归因分析，不在本插件范围内

## lhg-plugs 插件矩阵

| 插件 | 一句话 | 安装 |
|---|---|---|
| [lhg-video-edit](https://github.com/lhg-plugs/lhg-video-edit) | 一句话把口播素材剪成爆款短视频（+口播脚本子命令） | `/plugin install lhg-video-edit@lhg-plugs` |
| [lhg-fullstack](https://github.com/lhg-plugs/lhg-fullstack) | 小白一句话 → 高质量全栈应用 | `/plugin install lhg-fullstack@lhg-plugs` |
| [lhg-shopify](https://github.com/lhg-plugs/lhg-shopify) | 独立站建站专家：从选品页到结账的开店流水线 | `/plugin install lhg-shopify@lhg-plugs` |
| [lhg-biz-report](https://github.com/lhg-plugs/lhg-biz-report) | 商业分析报告专家：原始数据到图文报告一条龙 | `/plugin install lhg-biz-report@lhg-plugs` |

## 自检与反馈

本插件自带质检：每次使用后可跑 `python3 smoke_test.py` 一键验证（JSON 合法、skill/command/agent 完整性、31 条规则、fixtures 命中、hooks 行为）。

发现 bug 或有改进建议，以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-biz-report/issues，正文写清"复现步骤 → 实际表现 → 期望表现"。

## 出品：刘洪光

本插件由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 视频号：搜「刘洪光实名上网」
- 微信：lhgsmsw
