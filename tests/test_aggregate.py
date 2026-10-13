# -*- coding: utf-8 -*-
"""WP30 聚合层：四联确定性、缺数据 None 不猜测。"""

import json

from perf_reconcile import (
    ActualCheckin,
    PlanVisit,
    coverage,
    dashboard,
    deviance,
    grade_distribution,
    load,
    reconcile,
    render_dashboard,
)


def _report():
    plan = [PlanVisit("S1", "2026-11-03", "张三", "B#1"),
            PlanVisit("S2", "2026-11-04", "李四", "B#1")]
    act = [ActualCheckin("S2", "2026-11-04", "王五"),
           ActualCheckin("S9", "2026-11-05", "赵六")]
    return reconcile(plan, act)


def test_coverage_zero_total_is_none_not_zero():
    assert coverage(0, 0)["rate"] is None
    assert coverage(30, 100)["rate"] == 0.3


def test_load_dedup_and_sort():
    d = load(["张三", "张三", "李四"], 5, {"张三": 20, "李四": 10})
    assert d["reps"] == ["张三", "李四"]  # 去重排序
    assert d["visits_per_rep_day"] == {"张三": 4.0, "李四": 2.0}
    assert load(["张三"], 0, {})["visits_per_rep_day"] is None  # 无工作日不猜


def test_grade_distribution_sorted():
    g = grade_distribution({"S1": "A", "S2": "B", "S3": "A"})
    assert g["counts"] == {"A": 2, "B": 1}
    assert list(g["counts"]) == sorted(g["counts"])


def test_deviance_rate():
    d = deviance(_report())
    # 计划 2（S1 MISS + S2 REP_MISMATCH 各认领一次）；OFF_PLAN(S9) 不属计划
    assert d["planned_visits"] == 2
    assert d["deviations"] == 3  # MISS + REP_MISMATCH + OFF_PLAN
    assert d["rate"] == 1.5  # 偏差含计划外，可 >1（如实暴露，不截断粉饰）
    assert d["by_kind"] == {"MISS": 1, "OFF_PLAN": 1, "REP_MISMATCH": 1}


def test_dashboard_byte_stable():
    doc = dashboard({"served_outlets": 30, "total_outlets": 100},
                    {"reps": ["张三"], "workdays": 5,
                     "visits_by_rep": {"张三": 20}},
                    {"S1": "A"}, _report())
    a = render_dashboard(doc)
    b = render_dashboard(dashboard(
        {"total_outlets": 100, "served_outlets": 30},  # kwargs 序不同
        {"workdays": 5, "reps": ["张三"], "visits_by_rep": {"张三": 20}},
        {"S1": "A"}, _report()))
    assert a == b
    assert json.loads(a)["schema"] == "perf-dashboard@1.0"
