#!/usr/bin/env python3
"""lhg-biz-report 确定性报告审计：31 条规则，零第三方依赖。

扫描报告目录（report.md + metrics.json + data.csv + charts.csv），输出
JSON 与人类可读报告；有 blocker 时以 exit code 2 退出（供 hooks 与 CI 使用）。

报告目录约定：
    report/
    ├── metrics.json   # 指标字典（一名一定义一单位一周期一来源）
    ├── data.csv       # 干净源数据（period 列 + 指标列）
    ├── charts.csv     # 图表数据（chart_id/title/metric/value/period/unit/y_from_zero/note）
    └── report.md      # 报告正文

用法：
    python3 report_audit.py --target <报告目录> [--format json|text]
                            [--fail-on blocker|warning|nit]

规则文案均为本项目原创（商业分析流程思路受 felaris/claude-skills 中
商业分析 skill 的高层思路启发，未复制任何第三方原文与代码；数据处理与
报告生成的方法论复用 lhg-plugs 组织自有插件 lhg-excel / lhg-ppt；
详见仓库 ATTRIBUTION.md）。
"""

import argparse
import csv
import json
import os
import re
import sys

VERSION = "1.0.0"
TOOL = "lhg-biz-report/report-audit"

SKIP_DIRS = {".git", "__pycache__", "node_modules", "dist", "build", ".bak"}


class Finding:
    __slots__ = ("rule_id", "severity", "category", "title", "file", "line",
                 "snippet", "detail")

    def __init__(self, rule_id, severity, category, title, file, line,
                 snippet, detail):
        self.rule_id = rule_id
        self.severity = severity
        self.category = category
        self.title = title
        self.file = file
        self.line = line
        self.snippet = snippet
        self.detail = detail

    def to_dict(self):
        return {
            "rule_id": self.rule_id, "severity": self.severity,
            "category": self.category, "title": self.title,
            "file": self.file, "line": self.line,
            "snippet": self.snippet, "detail": self.detail,
        }


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except UnicodeDecodeError:
        return None
    except OSError:
        return ""


def read_csv_rows(path):
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            return list(csv.DictReader(fh))
    except Exception:
        return None


def collect(target):
    out = {"metrics": None, "data": None, "charts": None, "report": None}
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            p = os.path.join(root, f)
            fl = f.lower()
            if fl == "metrics.json" and out["metrics"] is None:
                out["metrics"] = p
            elif fl == "data.csv" and out["data"] is None:
                out["data"] = p
            elif fl == "charts.csv" and out["charts"] is None:
                out["charts"] = p
            elif fl == "report.md" and out["report"] is None:
                out["report"] = p
    return out


def to_num(s):
    try:
        return float(str(s).strip().replace(",", ""))
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------- 规则注册表
RULES = []
_RULE_BY_ID = {}


def rule(rule_id, severity, category, title, detail):
    def deco(fn):
        r = {"id": rule_id, "severity": severity, "category": category,
             "title": title, "detail": detail}
        _RULE_BY_ID[rule_id] = r
        r["check"] = fn
        RULES.append(r)
        return fn
    return deco


def F(rule_id, path, snippet="", detail="", line=0):
    r = _RULE_BY_ID[rule_id]
    return Finding(rule_id, r["severity"], r["category"], r["title"],
                   path, line, snippet, detail or r["detail"])


# ================================================================ MET（8）
@rule("MET-FILE-001", "blocker", "metric", "metrics.json 存在且为合法 JSON",
      "指标字典缺失或不是合法 JSON：口径无从谈起，报告不许往下走。")
def _met_file(ctx):
    p = ctx["files"]["metrics"]
    if not p:
        yield F("MET-FILE-001", ctx["target"], "",
                "未找到 metrics.json：先跑 /lhg-biz-report:metric-define。")
        return
    try:
        json.loads(read_text(p) or "")
    except Exception as e:
        yield F("MET-FILE-001", p, "", "metrics.json 解析失败：%s" % e)


@rule("MET-DEF-001", "blocker", "metric", "每个指标都有定义",
      "没有定义的指标名就是空话：不同人会按不同意思理解。")
def _met_def(ctx):
    for m, p in ctx["metrics_list"]:
        if not (m.get("definition") or "").strip():
            yield F("MET-DEF-001", p, "",
                    "指标「%s」缺少 definition。" % m.get("name", "?"))


@rule("MET-DUP-001", "blocker", "metric", "同名指标定义唯一",
      "同一个指标名有两个定义，报告里写这个词时没人知道指哪个。")
def _met_dup(ctx):
    seen = {}
    for m, p in ctx["metrics_list"]:
        name = (m.get("name") or "").strip()
        if not name:
            continue
        dfn = (m.get("definition") or "").strip()
        if name in seen and seen[name] != dfn:
            yield F("MET-DUP-001", p, "",
                    "指标「%s」定义冲突：「%s」vs「%s」。" % (name, seen[name], dfn))
        seen.setdefault(name, dfn)


@rule("MET-UNIT-001", "warning", "metric", "每个指标都声明单位",
      "120 万和 120 元差了一万倍：单位不写，数字就是裸奔。")
def _met_unit(ctx):
    for m, p in ctx["metrics_list"]:
        if not (m.get("unit") or "").strip():
            yield F("MET-UNIT-001", p, "",
                    "指标「%s」缺少 unit。" % m.get("name", "?"))


@rule("MET-PERIOD-001", "warning", "metric", "每个指标都声明统计周期",
      "不写周期，‘营收增长 20%’可能是同比、环比或随便一比。")
def _met_period(ctx):
    for m, p in ctx["metrics_list"]:
        if not (m.get("period") or "").strip():
            yield F("MET-PERIOD-001", p, "",
                    "指标「%s」缺少 period（统计周期）。" % m.get("name", "?"))


@rule("MET-FORMULA-001", "warning", "metric", "比率/占比类指标写明公式",
      "毛利率是 毛利/营收 还是 净利润/营收？公式不写，复算无从下手。")
def _met_formula(ctx):
    for m, p in ctx["metrics_list"]:
        name = (m.get("name") or "").strip()
        if any(k in name for k in ("率", "占比", "比值")):
            if not (m.get("formula") or "").strip():
                yield F("MET-FORMULA-001", p, "",
                        "指标「%s」缺少 formula。" % name)


@rule("MET-SOURCE-001", "nit", "metric", "每个指标都声明数据来源",
      "数字从哪来要写清楚，方便追溯与追责。")
def _met_source(ctx):
    for m, p in ctx["metrics_list"]:
        if not (m.get("source") or "").strip():
            yield F("MET-SOURCE-001", p, "",
                    "指标「%s」缺少 source（数据来源）。" % m.get("name", "?"))


@rule("MET-VERSION-001", "nit", "metric", "metrics.json 有版本号",
      "口径会变：版本号让‘上次定的口径’可追溯。")
def _met_version(ctx):
    mj = ctx["metrics_json"]
    if mj is not None and not str(mj.get("version") or "").strip():
        yield F("MET-VERSION-001", ctx["files"]["metrics"])


# ================================================================ CALC（7）
def _pct_change(cur, base):
    if cur is None or base is None or base == 0:
        return None
    return (cur - base) / abs(base) * 100.0


def _claim_near(text, keyword, names):
    """找 keyword（如"同比增长"）附近的指标名与声明百分比。"""
    out = []
    for m in re.finditer(re.escape(keyword) + r"\s*(\d+(?:\.\d+)?)\s*%",
                         text):
        pct = float(m.group(1))
        window = text[max(0, m.start() - 12):m.start()]
        name = next((n for n in names if n in window), None)
        out.append((name, pct, m.start()))
    return out


@rule("CALC-YOY-001", "blocker", "calc", "报告中的同比数字与源数据一致",
      "同比算错是报告第一杀手：读者拿计算器一按，整篇报告信用归零。")
def _calc_yoy(ctx):
    rows, text = ctx["data_rows"], ctx["report_text"]
    names = ctx["col_of"]
    if not rows or text is None:
        return
    first, last = rows[0], rows[-1]
    for name, claimed, pos in _claim_near(text, "同比增长", names):
        if not name or name not in names:
            continue
        col = names[name]
        actual = _pct_change(to_num(last.get(col)), to_num(first.get(col)))
        if actual is not None and abs(actual - claimed) > 0.5:
            yield F("CALC-YOY-001", ctx["files"]["report"],
                    "同比增长 %.1f%%" % claimed, line=ctx["lineno"](pos),
                    detail="「%s」同比自称增长 %.1f%%，按源数据（%s→%s）重算为 %.1f%%。"
                           % (name, claimed, first.get("period"),
                              last.get("period"), actual))


@rule("CALC-QOQ-001", "blocker", "calc", "报告中的环比数字与源数据一致",
      "环比是看 momentum 的，算错会误导业务判断。")
def _calc_qoq(ctx):
    rows, text = ctx["data_rows"], ctx["report_text"]
    names = ctx["col_of"]
    if not rows or len(rows) < 2 or text is None:
        return
    prev, last = rows[-2], rows[-1]
    for name, claimed, pos in _claim_near(text, "环比增长", names):
        if not name or name not in names:
            continue
        col = names[name]
        actual = _pct_change(to_num(last.get(col)), to_num(prev.get(col)))
        if actual is not None and abs(actual - claimed) > 0.5:
            yield F("CALC-QOQ-001", ctx["files"]["report"],
                    "环比增长 %.1f%%" % claimed, line=ctx["lineno"](pos),
                    detail="「%s」环比自称增长 %.1f%%，按源数据（%s→%s）重算为 %.1f%%。"
                           % (name, claimed, prev.get("period"),
                              last.get("period"), actual))


@rule("CALC-SUM-001", "warning", "calc", "合计等于分项之和",
      "总数对不上分项和，读者会怀疑整张表。")
def _calc_sum(ctx):
    rows, sc = ctx["data_rows"], ctx["sum_check"]
    if not rows or not sc:
        return
    total, parts = sc.get("total"), sc.get("parts") or []
    for r in rows:
        t = to_num(r.get(total))
        ps = [to_num(r.get(c)) for c in parts]
        if t is None or any(v is None for v in ps):
            continue
        if abs(t - sum(ps)) > 0.01 * max(1, abs(t)):
            yield F("CALC-SUM-001", ctx["files"]["data"], "",
                    "%s 期：%s=%s，但分项和为 %s。" %
                    (r.get("period"), total, t, sum(ps)))


@rule("CALC-PCT-001", "warning", "calc", "占比类列之和 ≈100%",
      "占比加起来不是 100%，饼图一画就露馅。")
def _calc_pct(ctx):
    rows = ctx["data_rows"]
    if not rows:
        return
    cols = [c for c in (rows[0].keys() if rows else [])
            if "占比" in c or c.endswith("_share")]
    for r in rows:
        vals = [to_num(r.get(c)) for c in cols]
        if not vals or any(v is None for v in vals):
            continue
        if abs(sum(vals) - 100.0) > 1.0:
            yield F("CALC-PCT-001", ctx["files"]["data"], "",
                    "%s 期：占比列之和为 %.1f%%，不是 100%%。" %
                    (r.get("period"), sum(vals)))


@rule("CALC-NEG-001", "nit", "calc", "数值列无异常负值",
      "营收、利润出现负值多半是符号录错，值得看一眼。")
def _calc_neg(ctx):
    rows = ctx["data_rows"]
    if not rows:
        return
    for r in rows:
        for c, v in r.items():
            if c == "period":
                continue
            n = to_num(v)
            if n is not None and n < 0:
                yield F("CALC-NEG-001", ctx["files"]["data"], "",
                        "%s 期 %s=%s 为负值，请确认。" % (r.get("period"), c, v))
                break


@rule("CALC-ROUND-001", "nit", "calc", "小数位数与指标声明一致",
      "口径说保留 1 位，表里出现 3 位小数，读者会困惑哪个是准的。")
def _calc_round(ctx):
    rows = ctx["data_rows"]
    if not rows:
        return
    for m, _ in ctx["metrics_list"]:
        col, dec = m.get("column"), m.get("decimals")
        if not col or dec is None:
            continue
        try:
            dec = int(dec)
        except (ValueError, TypeError):
            continue
        for r in rows:
            v = str(r.get(col) or "")
            if "." in v:
                frac = v.split(".")[1].rstrip("0")
                if len(frac) > dec:
                    yield F("CALC-ROUND-001", ctx["files"]["data"], "",
                            "指标「%s」声明保留 %d 位小数，但源数据出现 %s。"
                            % (m.get("name"), dec, v))
                    break


@rule("CALC-CONSIST-001", "warning", "calc", "同一指标在报告中数值唯一",
      "同一个指标在报告里出现两个不同的数，读者不知道信哪个。")
def _calc_consist(ctx):
    text = ctx["report_text"]
    if text is None:
        return
    for m, _ in ctx["metrics_list"]:
        name = (m.get("name") or "").strip()
        if not name:
            continue
        vals = set()
        for mm in re.finditer(re.escape(name) + r"[^\d\n]{0,6}(\d+(?:\.\d+)?)",
                              text):
            vals.add(mm.group(1))
        if len(vals) > 1:
            yield F("CALC-CONSIST-001", ctx["files"]["report"], "",
                    "指标「%s」在报告中出现多个不同数值：%s。"
                    % (name, "、".join(sorted(vals))))


# ================================================================ CHART（6）
@rule("CHART-FILE-001", "warning", "chart", "charts.csv 存在",
      "没有图表数据文件，报告里的图就无从核对。")
def _chart_file(ctx):
    if not ctx["files"]["charts"]:
        yield F("CHART-FILE-001", ctx["target"], "",
                "未找到 charts.csv：图表数据无法与源数据核对。")


@rule("CHART-MATCH-001", "blocker", "chart", "图表数值与源数据一致",
      "图和表各说各话，是报告里最容易被抓包的翻车。")
def _chart_match(ctx):
    rows, charts = ctx["data_rows"], ctx["chart_rows"]
    names = ctx["col_of"]
    if not rows or not charts:
        return
    by_period = {r.get("period"): r for r in rows}
    for c in charts:
        metric, period = (c.get("metric") or "").strip(), c.get("period")
        if metric not in names or period not in by_period:
            continue
        expect = to_num(by_period[period].get(names[metric]))
        got = to_num(c.get("value"))
        if expect is not None and got is not None and abs(expect - got) > 0.01 * max(1, abs(expect)):
            yield F("CHART-MATCH-001", ctx["files"]["charts"], "",
                    "图表 %s（%s/%s）值为 %s，源数据为 %s，对不上。"
                    % (c.get("chart_id"), metric, period, c.get("value"), expect))


@rule("CHART-LABEL-001", "warning", "chart", "图表标题含指标名",
      "图的标题和指标名对不上，读者找不到图在讲哪个数。")
def _chart_label(ctx):
    for c in ctx["chart_rows"]:
        metric, title = (c.get("metric") or "").strip(), c.get("title") or ""
        if metric and metric not in title:
            yield F("CHART-LABEL-001", ctx["files"]["charts"], "",
                    "图表 %s 标题「%s」未包含指标名「%s」。"
                    % (c.get("chart_id"), title, metric))


@rule("CHART-UNIT-001", "warning", "chart", "图表标注单位",
      "图上没单位，读者不知道纵轴是元还是万元。")
def _chart_unit(ctx):
    for c in ctx["chart_rows"]:
        if not (c.get("unit") or "").strip():
            yield F("CHART-UNIT-001", ctx["files"]["charts"], "",
                    "图表 %s 未标注单位。" % c.get("chart_id"))


@rule("CHART-REF-001", "warning", "chart", "每个图表都在正文中被引用",
      "画了图但正文一次没提，等于白画；也可能是漏写了引用。")
def _chart_ref(ctx):
    text = ctx["report_text"]
    if text is None:
        return
    for c in ctx["chart_rows"]:
        cid = (c.get("chart_id") or "").strip()
        if cid and cid not in text:
            yield F("CHART-REF-001", ctx["files"]["charts"], "",
                    "图表 %s 在 report.md 中未被引用。" % cid)


@rule("CHART-SCALE-001", "nit", "chart", "截断纵轴需标注说明",
      "纵轴不从 0 开始会把小波动画成大涨大跌：要么从 0 画，要么明确标注。")
def _chart_scale(ctx):
    for c in ctx["chart_rows"]:
        y0 = (c.get("y_from_zero") or "").strip().lower()
        if y0 in ("false", "0", "no") and not (c.get("note") or "").strip():
            yield F("CHART-SCALE-001", ctx["files"]["charts"], "",
                    "图表 %s 纵轴不从 0 开始但未在 note 中说明。"
                    % c.get("chart_id"))


# ================================================================ STRUCT（10）
def _report_lines(ctx):
    text = ctx["report_text"]
    return text.split("\n") if text is not None else []


@rule("STRUCT-FILE-001", "blocker", "struct", "report.md 存在",
      "报告正文都没有，审什么。")
def _struct_file(ctx):
    if not ctx["files"]["report"]:
        yield F("STRUCT-FILE-001", ctx["target"], "",
                "未找到 report.md。")


@rule("STRUCT-CONC-001", "blocker", "struct", "结论先行（前 15 行见结论）",
      "读者 30 秒找不到观点就会关掉：结论必须在开头。")
def _struct_conc(ctx):
    lines = _report_lines(ctx)
    if not lines:
        return
    head = "\n".join(lines[:15])
    if "结论" not in head and "核心发现" not in head:
        yield F("STRUCT-CONC-001", ctx["files"]["report"], "",
                "前 15 行未出现结论/核心发现：把观点搬到开头。")


@rule("STRUCT-EXEC-001", "warning", "struct", "有执行摘要",
      "老板只看摘要：没有摘要的报告，阅读完成率打对折。")
def _struct_exec(ctx):
    text = ctx["report_text"]
    if text is None:
        return
    if "摘要" not in text and "概述" not in text:
        yield F("STRUCT-EXEC-001", ctx["files"]["report"])


@rule("STRUCT-DATA-001", "blocker", "struct", "结论段有数据支撑",
      "没有数据支撑的结论是观后感：结论段每段至少带一个数。")
def _struct_data(ctx):
    lines = _report_lines(ctx)
    if not lines:
        return
    in_conc, buf = False, []
    sections = []
    for ln in lines:
        if re.match(r"^#{1,3}\s", ln):
            if in_conc and buf:
                sections.append(buf)
            buf = []
            in_conc = "结论" in ln or "核心发现" in ln
        elif in_conc:
            buf.append(ln)
    if in_conc and buf:
        sections.append(buf)
    for sec in sections:
        paras = [p.strip() for p in "\n".join(sec).replace("\n\n", "\n").split("\n")
                 if p.strip()]
        for p in paras:
            if not re.search(r"\d", p):
                yield F("STRUCT-DATA-001", ctx["files"]["report"],
                        p.strip()[:40],
                        detail="结论段中这段话没有数据支撑：%s" % p.strip()[:60])
                return


@rule("STRUCT-SOURCE-001", "warning", "struct", "数据注明来源与时间",
      "数字没有来源和时间，读者无法判断新不新鲜、真不真。")
def _struct_source(ctx):
    text = ctx["report_text"]
    if text is None:
        return
    if "数据来源" not in text and "数据时间" not in text:
        yield F("STRUCT-SOURCE-001", ctx["files"]["report"])


@rule("STRUCT-RISK-001", "warning", "struct", "有风险提示/局限性说明",
      "只报喜不报忧的报告，第一次翻车就没人信了。")
def _struct_risk(ctx):
    text = ctx["report_text"]
    if text is None:
        return
    if not any(w in text for w in ("风险", "局限", "不足", "不确定性")):
        yield F("STRUCT-RISK-001", ctx["files"]["report"])


@rule("STRUCT-NEXT-001", "warning", "struct", "有下一步建议/行动项",
      "报告的终点是行动：没有‘所以呢’的报告等于白写。")
def _struct_next(ctx):
    text = ctx["report_text"]
    if text is None:
        return
    if not any(w in text for w in ("下一步", "建议", "行动", "计划")):
        yield F("STRUCT-NEXT-001", ctx["files"]["report"])


@rule("STRUCT-TITLE-001", "nit", "struct", "章节标题是完整短语（≥6 字）",
      "‘数据’这种标题信息量为零：标题要让人不看正文也知道讲什么。")
def _struct_title(ctx):
    for ln in _report_lines(ctx):
        m = re.match(r"^#{2,3}\s+(.+?)\s*$", ln)
        if m and len(m.group(1).strip()) < 6:
            yield F("STRUCT-TITLE-001", ctx["files"]["report"], ln.strip(),
                    detail="标题过短（<%d 字），建议写成一句话观点。" % 6)
            return


@rule("STRUCT-DATE-001", "warning", "struct", "注明数据时间范围",
      "不知道数据是哪段时间的，结论无法复用也无法追责。")
def _struct_date(ctx):
    text = ctx["report_text"]
    if text is None:
        return
    if not any(w in text for w in ("数据截至", "时间范围", "统计周期", "数据期间")):
        yield F("STRUCT-DATE-001", ctx["files"]["report"])


@rule("STRUCT-CAVEAT-001", "nit", "struct", "有口径说明",
      "口径写进报告，三个月后回看才知道当初的数是怎么算的。")
def _struct_caveat(ctx):
    text = ctx["report_text"]
    if text is None:
        return
    if "口径说明" not in text and "统计口径" not in text:
        yield F("STRUCT-CAVEAT-001", ctx["files"]["report"])


# ---------------------------------------------------------------- 主流程
def build_ctx(target):
    files = collect(target)
    metrics_json, metrics_list = None, []
    if files["metrics"]:
        try:
            metrics_json = json.loads(read_text(files["metrics"]) or "")
            for m in metrics_json.get("metrics", []):
                if isinstance(m, dict):
                    metrics_list.append((m, files["metrics"]))
        except Exception:
            metrics_json = None
    data_rows = read_csv_rows(files["data"]) if files["data"] else []
    chart_rows = read_csv_rows(files["charts"]) if files["charts"] else []
    report_text = read_text(files["report"]) if files["report"] else None

    col_of = {}
    for m, _ in metrics_list:
        if m.get("name") and m.get("column"):
            col_of[m["name"]] = m["column"]

    def lineno(pos):
        return report_text.count("\n", 0, pos) + 1 if report_text else 0

    return {
        "target": target, "files": files,
        "metrics_json": metrics_json, "metrics_list": metrics_list,
        "data_rows": data_rows or [], "chart_rows": chart_rows or [],
        "report_text": report_text, "col_of": col_of, "lineno": lineno,
        "sum_check": (metrics_json or {}).get("sum_check"),
    }


def run_audit(target):
    ctx = build_ctx(target)
    findings = []
    for r in RULES:
        try:
            for f in r["check"](ctx):
                findings.append(f)
        except Exception as e:  # 单规则出错不炸整轮
            findings.append(Finding(r["id"], "warning", r["category"],
                                    r["title"], target, 0, "",
                                    "规则执行异常（已降级）：%s" % e))
    return findings


def summarize(findings):
    s = {"blocker": 0, "warning": 0, "nit": 0, "rules_run": len(RULES),
         "rules_hit": len({_RULE_BY_ID[f.rule_id]["id"] for f in findings})}
    for f in findings:
        if f.severity in s:
            s[f.severity] += 1
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(description="lhg-biz-report 报告审计（31 条规则）")
    ap.add_argument("--target", required=True)
    ap.add_argument("--format", choices=("json", "text"), default="text")
    ap.add_argument("--fail-on", choices=("blocker", "warning", "nit"),
                    default="blocker")
    args = ap.parse_args(argv)

    findings = run_audit(args.target)
    summary = summarize(findings)

    if args.format == "json":
        print(json.dumps({"tool": TOOL, "version": VERSION, "target": args.target,
                          "summary": summary,
                          "findings": [f.to_dict() for f in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print("lhg-biz-report 报告审计 v%s  target=%s" % (VERSION, args.target))
        print("blocker=%d warning=%d nit=%d  规则 %d/%d 命中"
              % (summary["blocker"], summary["warning"], summary["nit"],
                 summary["rules_hit"], summary["rules_run"]))
        for f in findings:
            print("[%s] %s %s\n      %s" % (f.severity.upper(), f.rule_id,
                                            f.title, f.file))

    order = {"blocker": 0, "warning": 1, "nit": 2}
    worst = min([order[f.severity] for f in findings], default=3)
    if worst <= order[args.fail_on]:
        return 2 if worst == 0 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
