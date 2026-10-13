# -*- coding: utf-8 -*-
"""看板聚合层（④WP30）：九仓数据面 → 四联指标确定性 JSON。

四联（计划④ §2 WP30 口径）：
- coverage 覆盖率：已服务/全量售点（①动态覆盖率公式同口径）
- load     负载：每代表日均拜访（对照报告 OK+偏差认领数/代表/工作日）
- grade    等级迁移：市场区隔等级分布（②market-partition 维度，入参透传）
- deviance 偏差率：非 OK 偏差 / 计划拜访数（perf-reconcile 报告消费）

纪律：纯函数零 IO、确定性（键排序、浮点 round 到 4 位防平台噪声）、
缺数据记 None 不猜测（与 scenarios.plan_metrics 同口径）。
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from perf_reconcile.reconcile import ReconcileReport


def _r4(x: float) -> float:
    return round(x, 4)


def coverage(served_outlets: int, total_outlets: int) -> dict:
    """①动态覆盖率：total=0 → rate None（不猜测为 0 完美/0 空白）。"""
    rate = _r4(served_outlets / total_outlets) if total_outlets > 0 else None
    return {"metric": "coverage", "served": served_outlets,
            "total": total_outlets, "rate": rate}


def load(reps: Sequence[str], workdays: int,
         visits_by_rep: Mapping[str, int]) -> dict:
    """负载：日均拜访/代表；reps 排序去重防入参序噪声。"""
    rs = sorted(set(reps))
    per_rep = {rep: _r4(visits_by_rep.get(rep, 0) / workdays)
               for rep in rs} if workdays > 0 else {}
    return {"metric": "load", "workdays": workdays, "reps": rs,
            "visits_per_rep_day": per_rep if workdays > 0 else None}


def grade_distribution(grades: Mapping[str, str]) -> dict:
    """等级迁移数据源=②区隔结果；此处分布透传（计数升序键确定性）。"""
    dist: dict[str, int] = {}
    for code in sorted(grades):
        g = grades[code]
        dist[g] = dist.get(g, 0) + 1
    return {"metric": "grade", "counts": {k: dist[k] for k in sorted(dist)}}


def deviance(report: ReconcileReport) -> dict:
    """偏差率：非 OK / 计划拜访数（计划数=0 → None）。"""
    # 计划数 = OK + 全部偏差（MISS/DRIFT/REP 各认领一次计划；OFF_PLAN 不属计划）
    planned = (report.counts.get("OK", 0)
               + sum(c for k, c in report.counts.items()
                     if k in ("MISS", "DATE_DRIFT", "REP_MISMATCH")))
    bad = sum(c for k, c in report.counts.items() if k != "OK")
    rate = _r4(bad / planned) if planned > 0 else None
    return {"metric": "deviance", "planned_visits": planned if planned else None,
            "deviations": bad, "rate": rate,
            "by_kind": {k: v for k, v in sorted(report.counts.items()) if k != "OK"}}


def dashboard(coverage_args: dict, load_args: dict,
              grades: Mapping[str, str], report: ReconcileReport) -> dict:
    """四联聚合文档（看板数据模型；json 序列化前键已定序）。"""
    return {
        "schema": "perf-dashboard@1.0",
        "coverage": coverage(**coverage_args),
        "load": load(**load_args),
        "grade": grade_distribution(grades),
        "deviance": deviance(report),
    }


def render_dashboard(doc: dict[str, Any]) -> str:
    import json
    return json.dumps(doc, ensure_ascii=False, sort_keys=True)
