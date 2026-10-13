# perf-reconcile

模块④ 业绩分析 · 计划-执行对照实体（WP27）。stdlib-only。

```
PlanVisit(plan_version_ref 强键) × ActualCheckin(打卡契约 v1.0)
  → reconcile() → ReconcileReport(偏差四分类, 逐字节稳定)
```

| 分类 | 语义 |
|---|---|
| OK | 同日同人精确匹配 |
| MISS | 计划拜访无打卡（当日有取消打卡则注明 reason=取消） |
| REP_MISMATCH | 同日打卡但人店不符 |
| DATE_DRIFT | 同人异日，最近邻认领（漂移天数入 reason） |
| OFF_PLAN | 未被认领的打卡（含计划外新店） |

匹配为每店内贪心三遍消费式：一条打卡至多认领一个计划拜访。
报告 `render_report` json sort_keys 逐字节稳定；偏差全序
(kind, store, planned_date, actual_date)。

## ⚠️ 契约边界

`CHECKIN_SCHEMA_VERSION = "1.0"` 是**自定版本化契约，待 App 对齐**（计划④
§4 决策点 1）：真实打卡流到位后对齐字段语义=升 major，不悄悄改。

## 运行

```bash
pip install "perf-reconcile @ git+https://github.com/topprismdata/perf-reconcile.git@v0.1.0"
python -m pytest   # 8 passed
```
