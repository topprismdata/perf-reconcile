# -*- coding: utf-8 -*-
"""WP29 台账：append-only、链验证、篡改必红、强键必填。"""

import json

import pytest

from perf_reconcile.ledger import ActionLedger, LedgerTamperError


def _e(ref="B#1", **kw):
    return {"plan_version_ref": ref, "action": "补访问", **kw}


def test_append_and_verify(tmp_path):
    led = ActionLedger(tmp_path / "l.jsonl")
    led.append(_e())
    led.append(_e("B#2"))
    assert led.verify() == 2
    assert [e["plan_version_ref"] for e in led.entries()] == ["B#1", "B#2"]


def test_entry_requires_traceability_key(tmp_path):
    led = ActionLedger(tmp_path / "l.jsonl")
    with pytest.raises(ValueError, match="plan_version_ref"):
        led.append({"action": "无锚条目"})


def test_tamper_content_detected(tmp_path):
    led = ActionLedger(tmp_path / "l.jsonl")
    led.append(_e())
    led.append(_e("B#2"))
    rows = [json.loads(x) for x in
            (tmp_path / "l.jsonl").read_text(encoding="utf-8").splitlines()]
    rows[0]["entry"]["action"] = "篡改为为"  # 改写历史条目内容
    (tmp_path / "l.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    with pytest.raises(LedgerTamperError, match="哈希不符"):
        led.verify()


def test_tamper_chain_link_detected(tmp_path):
    """删中间条：后条 prev 指向被删 hash → 链断必红（删尾再追加不属篡改）。"""
    led = ActionLedger(tmp_path / "l.jsonl")
    led.append(_e())
    led.append(_e("B#2"))
    led.append(_e("B#3"))
    lines = (tmp_path / "l.jsonl").read_text(encoding="utf-8").splitlines()
    del lines[1]
    (tmp_path / "l.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(LedgerTamperError, match="prev"):
        led.verify()


def test_no_mutation_api():
    """结构性 append-only：不存在 update/delete/remove 接口。"""
    for forbidden in ("update", "delete", "remove", "truncate"):
        assert not hasattr(ActionLedger, forbidden)
