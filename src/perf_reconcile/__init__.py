"""perf-reconcile：计划-执行对照实体（模块④ WP27）。

三方记录：计划侧（plan_version_ref 强键 + 计划拜访）× 执行侧（实际打卡）。
打卡 schema 为**自定版本化契约（CHECKIN_SCHEMA_VERSION），待 App 对齐**——
对齐时升 major，不悄悄改字段语义（计划④ §4 决策点 1）。

偏差四分类（每店贪心按日期匹配，全序确定性）：
OK / MISS(缺访问) / OFF_PLAN(计划外) / DATE_DRIFT(日期漂移) / REP_MISMATCH(人店不符)
"""
__version__ = "0.3.0"

from perf_reconcile.aggregate import (  # noqa: F401
    coverage,
    dashboard,
    deviance,
    grade_distribution,
    load,
    render_dashboard,
)
from perf_reconcile.ledger import (  # noqa: F401
    GENESIS,
    ActionLedger,
    LedgerTamperError,
)
from perf_reconcile.reconcile import (  # noqa: F401
    CHECKIN_SCHEMA_VERSION,
    ActualCheckin,
    PlanVisit,
    ReconcileReport,
    reconcile,
    render_report,
)

__all__ = [
    "CHECKIN_SCHEMA_VERSION", "ActualCheckin", "PlanVisit",
    "ReconcileReport", "reconcile", "render_report",
    "ActionLedger", "LedgerTamperError", "GENESIS",
    "coverage", "load", "grade_distribution", "deviance", "dashboard",
    "render_dashboard", "__version__",
]
