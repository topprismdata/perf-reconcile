# -*- coding: utf-8 -*-
"""WP27 对照实体：偏差四分类、消费式匹配、逐字节稳定、契约版本可见。"""

import json


from perf_reconcile import (
    CHECKIN_SCHEMA_VERSION,
    ActualCheckin,
    PlanVisit,
    reconcile,
    render_report,
)


def _p(store, d, rep, ref="B#1"):
    return PlanVisit(store, d, rep, ref)


def _a(store, d, rep, status="完成"):
    return ActualCheckin(store, d, rep, status)


def test_ok_exact_match():
    r = reconcile([_p("S1", "2026-11-03", "张三")], [_a("S1", "2026-11-03", "张三")])
    assert r.counts == {"OK": 1} and r.deviations == ()
    assert r.plan_version_refs == ("B#1",)


def test_miss_with_cancel_reason():
    r = reconcile(
        [_p("S1", "2026-11-03", "张三"), _p("S1", "2026-11-05", "张三")],
        [_a("S1", "2026-11-03", "张三", "取消")],
    )
    kinds = {d.kind for d in r.deviations}
    assert kinds == {"MISS"}
    by_date = {d.planned_date: d for d in r.deviations}
    assert by_date["2026-11-03"].reason == "取消"
    assert by_date["2026-11-05"].reason == "无打卡"


def test_rep_mismatch_consumes_checkin():
    r = reconcile([_p("S1", "2026-11-03", "张三")], [_a("S1", "2026-11-03", "李四")])
    assert [(d.kind, d.planned_rep, d.actual_rep) for d in r.deviations] == [
        ("REP_MISMATCH", "张三", "李四")]
    assert r.counts.get("OFF_PLAN") is None  # 已消费，不再计计划外


def test_date_drift_nearest_and_no_double_consume():
    r = reconcile(
        [_p("S1", "2026-11-03", "张三")],
        [_a("S1", "2026-11-05", "张三"), _a("S1", "2026-11-10", "张三")],
    )
    drifts = [d for d in r.deviations if d.kind == "DATE_DRIFT"]
    assert len(drifts) == 1 and drifts[0].actual_date == "2026-11-05"  # 最近邻
    assert drifts[0].reason == "漂移 2 天"
    assert r.counts["OFF_PLAN"] == 1  # 远的那条成计划外


def test_off_plan_new_store():
    r = reconcile([], [_a("S9", "2026-11-03", "张三")])
    assert r.counts == {"OK": 0, "OFF_PLAN": 1}
    assert r.deviations[0].store_code == "S9"


def test_report_byte_stable_and_input_order_free():
    plan = [_p("S1", "2026-11-03", "张三", "B#2"), _p("S2", "2026-11-04", "李四", "B#1")]
    act = [_a("S1", "2026-11-04", "张三"), _a("S3", "2026-11-05", "王五")]
    r1 = render_report(reconcile(plan, act))
    r2 = render_report(reconcile(list(reversed(plan)), list(reversed(act))))
    assert r1 == r2
    doc = json.loads(r1)
    assert doc["schema_version"] == CHECKIN_SCHEMA_VERSION
    assert doc["plan_version_refs"] == ["B#1", "B#2"]  # 排序去重


def test_schema_version_pinned():
    assert CHECKIN_SCHEMA_VERSION == "1.0"  # 变更须显式升 major 并过评审


def test_multi_ref_traceability():
    r = reconcile(
        [_p("S1", "2026-11-03", "张三", "B#7#2"), _p("S2", "2026-11-03", "李四", "B#7#1")],
        [],
    )
    assert r.plan_version_refs == ("B#7#1", "B#7#2")  # 每条偏差可回溯到计划版本
