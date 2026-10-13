# -*- coding: utf-8 -*-
"""生成单文件业绩看板 HTML（④WP30；零外部依赖，数据快照内嵌）。

用法：python scripts/build_dashboard.py <out.html>
数据=合成快照（真实打卡流待 App，④L12）；四联渲染：覆盖率/负载/等级/偏差率。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from perf_reconcile import (  # noqa: E402
    ActualCheckin,
    PlanVisit,
    dashboard,
    reconcile,
    render_dashboard,
)

# 合成快照（与 test_aggregate 同数据，售前演示口径）
PLAN = [PlanVisit("S1", "2026-11-03", "张三", "B#1"),
        PlanVisit("S2", "2026-11-04", "李四", "B#1"),
        PlanVisit("S3", "2026-11-05", "张三", "B#1")]
ACT = [ActualCheckin("S2", "2026-11-04", "王五"),
       ActualCheckin("S3", "2026-11-05", "张三"),
       ActualCheckin("S9", "2026-11-06", "赵六")]
GRADES = {"S1": "A", "S2": "B", "S3": "A", "S4": "C", "S5": "B"}

DOC = dashboard(
    {"served_outlets": 30, "total_outlets": 100},
    {"reps": ["张三", "李四", "王五"], "workdays": 5,
     "visits_by_rep": {"张三": 20, "李四": 10, "王五": 15}},
    GRADES,
    reconcile(PLAN, ACT),
)

HTML = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>业绩分析看板 · 合成快照</title>
<style>
:root{--ink:#1a1a2e;--muted:#6b7280;--line:#e5e7eb;--accent:#2563eb;--warn:#d97706;--bad:#dc2626}
*{box-sizing:border-box;margin:0;padding:0}
body{font:15px/1.6 -apple-system,"PingFang SC",sans-serif;color:var(--ink);background:#f8fafc;padding:32px}
.wrap{max-width:960px;margin:0 auto}
h1{font-size:22px;margin-bottom:4px}
.sub{color:var(--muted);font-size:13px;margin-bottom:24px}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
@media(max-width:640px){.grid{grid-template-columns:1fr}}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:20px}
.card h2{font-size:13px;color:var(--muted);font-weight:600;letter-spacing:.04em;text-transform:uppercase;margin-bottom:12px}
.big{font-size:32px;font-weight:700}
.big small{font-size:14px;color:var(--muted);font-weight:400}
.bar{height:8px;background:var(--line);border-radius:4px;margin:12px 0;overflow:hidden}
.bar i{display:block;height:100%;background:var(--accent)}
.rows{font-size:13px;color:var(--muted);margin-top:8px}
.rows div{display:flex;justify-content:space-between;padding:3px 0;border-top:1px dashed var(--line)}
.rows div:first-child{border-top:0}
.chip{display:inline-block;padding:2px 8px;border-radius:10px;font-size:12px;margin:2px}
.chip.a{background:#dbeafe;color:#1e40af}.chip.b{background:#fef3c7;color:#92400e}.chip.c{background:#fee2e2;color:#991b1b}
.warn{color:var(--warn)}.bad{color:var(--bad)}
.foot{margin-top:24px;font-size:12px;color:var(--muted);text-align:center}
</style></head><body><div class="wrap">
<h1>业绩分析看板</h1>
<div class="sub">合成快照 · 真实打卡数据流待 App 对齐（契约 v1.0）· 生成自 perf-reconcile 聚合层</div>
<div class="grid" id="g"></div>
<div class="foot">四联指标确定性 JSON · 缺数据记 None 不猜测 · 偏差率含计划外可 &gt;1（如实暴露）</div>
</div>
<script>
const D = __DATA__;
const pct = x => x==null ? "—" : (x*100).toFixed(1)+"%";
const g = document.getElementById("g");
function card(t,inner){const d=document.createElement("div");d.className="card";d.innerHTML="<h2>"+t+"</h2>"+inner;g.appendChild(d);}

const c=D.coverage;
card("覆盖率", '<div class="big">'+pct(c.rate)+' <small>已服务/全量</small></div><div class="bar"><i style="width:'+((c.rate||0)*100)+'%"></i></div><div class="rows"><div><span>已服务</span><b>'+c.served+'</b></div><div><span>全量售点</span><b>'+c.total+'</b></div></div>');

const l=D.load;
let lrows="";for(const r in l.visits_per_rep_day){lrows+="<div><span>"+r+"</span><b>"+l.visits_per_rep_day[r]+"</b></div>";}
card("日均负载", '<div class="big">'+(l.visits_per_rep_day?Object.values(l.visits_per_rep_day).reduce((a,b)=>a+b,0)/Object.keys(l.visits_per_rep_day).length:"—").toFixed(1)+' <small>拜访/人日</small></div><div class="rows">'+lrows+'</div>');

const gr=D.grade;let gchips="";for(const k in gr.counts){gchips+='<span class="chip '+k.toLowerCase()+'">'+k+' ×'+gr.counts[k]+'</span>';}
card("市场区隔等级分布", '<div style="margin:8px 0">'+gchips+'</div><div class="rows"><div><span>门店总数</span><b>'+Object.values(gr.counts).reduce((a,b)=>a+b,0)+'</b></div></div>');

const dv=D.deviance;
let drows="";for(const k in dv.by_kind){drows+="<div><span>"+k+"</span><b>"+dv.by_kind[k]+"</b></div>";}
const dcls = dv.rate==null?"":dv.rate>1?"bad":dv.rate>0.3?"warn":"";
card("计划-执行偏差率", '<div class="big '+dcls+'">'+pct(dv.rate)+' <small>偏差/计划</small></div><div class="rows">'+drows+'<div><span>计划拜访</span><b>'+(dv.planned_visits??"—")+'</b></div></div>');
</script></body></html>
"""


def main(out: str) -> int:
    html = HTML.replace("__DATA__", render_dashboard(DOC))
    Path(out).write_text(html, encoding="utf-8")
    print(f"看板已生成: {out} ({len(html)} 字节, 数据快照内嵌零外部依赖)")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(args[0]))
