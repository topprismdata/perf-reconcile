# -*- coding: utf-8 -*-
"""对照算法：三方记录 → 偏差四分类（确定性全序，逐字节稳定报告）。

匹配为每店内贪心三遍（精确→人店不符→日期漂移），消费式：一条打卡至多
认领一个计划拜访。全部键/序显式，无隐式 dict 序依赖。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date

# 打卡契约版本（自定，待 App 对齐；语义变更升 major）
CHECKIN_SCHEMA_VERSION = "1.0"

_OK = "OK"
_MISS = "MISS"
_OFF_PLAN = "OFF_PLAN"
_DRIFT = "DATE_DRIFT"
_REP = "REP_MISMATCH"


@dataclass(frozen=True)
class PlanVisit:
    store_code: str
    date: str  # ISO 日期（字典序=时间序）
    rep: str
    plan_version_ref: str


@dataclass(frozen=True)
class ActualCheckin:
    store_code: str
    date: str
    rep: str
    status: str = "完成"  # 完成 | 取消（取消不认领计划）


@dataclass(frozen=True)
class Deviation:
    kind: str
    store_code: str
    planned_date: str
    actual_date: str
    planned_rep: str
    actual_rep: str
    reason: str

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "store": self.store_code,
            "planned_date": self.planned_date,
            "actual_date": self.actual_date,
            "planned_rep": self.planned_rep,
            "actual_rep": self.actual_rep,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ReconcileReport:
    schema_version: str
    plan_version_refs: tuple[str, ...]
    deviations: tuple[Deviation, ...]
    counts: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "plan_version_refs": list(self.plan_version_refs),
            "counts": dict(self.counts),
            "deviations": [d.as_dict() for d in self.deviations],
        }


def _days(a: str, b: str) -> int:
    return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)


def reconcile(plan: list[PlanVisit], actuals: list[ActualCheckin]) -> ReconcileReport:
    """计划×打卡 → 偏差报告（MISS/OFF_PLAN/DATE_DRIFT/REP_MISMATCH；OK 计数）。"""
    by_store_p: dict[str, list[PlanVisit]] = {}
    for p in plan:
        by_store_p.setdefault(p.store_code, []).append(p)
    by_store_a: dict[str, list[ActualCheckin]] = {}
    for a in actuals:
        by_store_a.setdefault(a.store_code, []).append(a)

    deviations: list[Deviation] = []
    ok_count = 0
    for store in sorted(set(by_store_p) | set(by_store_a)):
        pending_p = sorted(by_store_p.get(store, []), key=lambda p: (p.date, p.rep))
        pending_a = sorted(by_store_a.get(store, []), key=lambda a: (a.date, a.rep))
        used_a: set[int] = set()

        # 遍 1：同日同人 → OK
        for p in list(pending_p):
            for i, a in enumerate(pending_a):
                if i not in used_a and a.status != "取消" and a.date == p.date and a.rep == p.rep:
                    used_a.add(i)
                    pending_p.remove(p)
                    ok_count += 1
                    break
        # 遍 2：同日不同人 → REP_MISMATCH
        for p in list(pending_p):
            for i, a in enumerate(pending_a):
                if i not in used_a and a.status != "取消" and a.date == p.date and a.rep != p.rep:
                    used_a.add(i)
                    pending_p.remove(p)
                    deviations.append(Deviation(_REP, store, p.date, a.date, p.rep, a.rep,
                                                "同日打卡但人店不符"))
                    break
        # 遍 3：同人异日最近邻 → DATE_DRIFT
        for p in list(pending_p):
            cand = [(i, a) for i, a in enumerate(pending_a)
                    if i not in used_a and a.status != "取消" and a.rep == p.rep]
            if cand:
                i, a = min(cand, key=lambda ia: (_days(ia[1].date, p.date), ia[1].date))
                used_a.add(i)
                pending_p.remove(p)
                deviations.append(Deviation(_DRIFT, store, p.date, a.date, p.rep, a.rep,
                                            f"漂移 {_days(a.date, p.date)} 天"))
        # 剩余计划 → MISS（当日有取消打卡则注明）
        for p in pending_p:
            cancelled = any(a.date == p.date and a.status == "取消" for a in pending_a)
            deviations.append(Deviation(_MISS, store, p.date, "", p.rep, "",
                                        "取消" if cancelled else "无打卡"))
        # 剩余打卡 → OFF_PLAN
        for i, a in enumerate(pending_a):
            if i not in used_a and a.status != "取消":
                deviations.append(Deviation(_OFF_PLAN, store, "", a.date, "", a.rep,
                                            "计划外拜访"))

    deviations.sort(key=lambda d: (d.kind, d.store_code, d.planned_date, d.actual_date))
    counts = {_OK: ok_count}
    for d in deviations:
        counts[d.kind] = counts.get(d.kind, 0) + 1
    refs = tuple(sorted({p.plan_version_ref for p in plan}))
    return ReconcileReport(CHECKIN_SCHEMA_VERSION, refs, tuple(deviations), counts)


def render_report(report: ReconcileReport) -> str:
    """逐字节稳定序列化（回归锁定用）。"""
    return json.dumps(report.as_dict(), ensure_ascii=False, sort_keys=True)
