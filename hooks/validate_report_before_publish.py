#!/usr/bin/env python3
"""lhg-biz-report 硬门：对外发送报告前校验报告包完整性。

触发：PreToolUse / Bash。脚本先判断本次 Bash 命令是否为"对外发送"
（send / publish / mail 发送意图，或 release 打包意图），不是则 0 开销
直接放行；是则查找并校验交付目录下的报告包
（report.md + metrics.json）。

校验项：metrics.json 合法、每个指标有定义、report.md 前 15 行见结论、
正文引用的图表在 charts.csv 中存在。

逃生方式（按推荐度排序）：
  1. 修好报告后重新发送（推荐）。
  2. 紧急情况：LHG_BR_HOOKS_OFF=1 <发送命令>（单次豁免本次 hook）。
  3. /plugin disable lhg-biz-report（整个插件停用，hooks 不再触发）。

设计原则：脚本内部出错时 fail-open 直接放行，不因插件自身故障骚扰用户；
找不到报告包时只做提醒式放行（additionalContext），不拦截——因为用户
可能在发送与本插件无关的文件。零第三方依赖。
"""

import csv
import json
import os
import re
import sys

SEND_RE = re.compile(
    r"(?<![\w-])(send|publish|release)\b.*\.(md|pdf|pptx?)\b|"
    r"\bmail\b.*\.(md|pdf|pptx?)\b|"
    r"(?<![\w-])(send|publish)\b",
    re.I,
)


def find_report_files(project_dir):
    found = {}
    for name, key in (("report.md", "report"), ("metrics.json", "metrics"),
                      ("charts.csv", "charts")):
        p = os.path.join(project_dir, name)
        if os.path.isfile(p):
            found[key] = p
    return found


def validate(files):
    """返回 (ok, [问题列表])。"""
    problems = []
    metrics_p = files.get("metrics")
    if metrics_p:
        try:
            with open(metrics_p, encoding="utf-8") as fh:
                mj = json.load(fh)
            for m in mj.get("metrics", []):
                if isinstance(m, dict) and not (m.get("definition") or "").strip():
                    problems.append("指标「%s」缺少定义，口径未统一不许外发。"
                                    % m.get("name", "?"))
        except Exception as e:
            problems.append("metrics.json 解析失败：%s" % e)
    else:
        problems.append("缺少 metrics.json：口径未统一不许外发。")

    report_p = files.get("report")
    if report_p:
        try:
            with open(report_p, encoding="utf-8") as fh:
                text = fh.read()
        except Exception as e:
            return False, problems + ["report.md 读取失败：%s" % e]
        head = "\n".join(text.split("\n")[:15])
        if "结论" not in head and "核心发现" not in head:
            problems.append("报告前 15 行没有结论：结论先行再外发。")
        charts_p = files.get("charts")
        if charts_p:
            try:
                with open(charts_p, encoding="utf-8-sig", newline="") as fh:
                    ids = {(r.get("chart_id") or "").strip()
                           for r in csv.DictReader(fh)}
            except Exception:
                ids = set()
            for cid in sorted(set(re.findall(r"\b(c\d+)\b", text))):
                if cid not in ids:
                    problems.append("正文引用了图表 %s，但 charts.csv 中没有。" % cid)
    else:
        problems.append("缺少 report.md。")
    return (not problems), problems


def main() -> int:
    if os.environ.get("LHG_BR_HOOKS_OFF") == "1":
        return 0

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        return 0  # 输入解析失败：fail-open

    tool_input = payload.get("tool_input", {}) or {}
    command = tool_input.get("command", "") or ""

    if not SEND_RE.search(command):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    files = find_report_files(project_dir)

    if not files:
        out = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "additionalContext": (
                    "提醒：本次发送未在当前目录找到报告包"
                    "（report.md/metrics.json）。"
                    "如果是用 lhg-biz-report 做的报告，请先跑 "
                    "/lhg-biz-report:report-audit，否则跳过此提醒。"
                ),
            }
        }
        sys.stdout.write(json.dumps(out, ensure_ascii=False))
        return 0

    try:
        ok, problems = validate(files)
    except Exception:
        return 0  # 校验自身出错：fail-open

    if ok:
        return 0

    lines = [
        "发送被 lhg-biz-report 硬门拦截：报告包校验发现 %d 个问题，修好再发送。"
        % len(problems),
        "",
    ]
    for p in problems[:10]:
        lines.append("- " + p)
    if len(problems) > 10:
        lines.append("…另有 %d 个" % (len(problems) - 10))
    lines += [
        "",
        "修复方式：跑 /lhg-biz-report:report-audit 按 blocker 清单修复后重新发送；",
        "紧急豁免（单次）：LHG_BR_HOOKS_OFF=1 <发送命令>",
    ]
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "\n".join(lines),
        }
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
