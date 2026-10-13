# -*- coding: utf-8 -*-
"""行动结果回写台账（④WP29）：append-only + hash 链，结构上无改写路径。

审计链语义延伸：行动结果永不改写历史 episode/计划记录——本模块**不提供**
update/delete API；链验证失败=台账被外部篡改，读侧 fail-closed 报错。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

GENESIS = "0" * 64


class LedgerTamperError(ValueError):
    """链验证失败（外部改写痕迹）。"""


def _entry_hash(prev_hash: str, entry: dict) -> str:
    blob = json.dumps({"prev": prev_hash, "entry": entry},
                      ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class ActionLedger:
    """JSONL 台账：每行 {entry, prev_hash, hash}。"""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _rows(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in
                self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def append(self, entry: dict) -> str:
        """追加一条行动结果（entry 须可 JSON 序列化且含 plan_version_ref）。"""
        if "plan_version_ref" not in entry:
            raise ValueError("台账条目必须携带 plan_version_ref（可追溯强键）")
        rows = self._rows()
        prev = rows[-1]["hash"] if rows else GENESIS
        h = _entry_hash(prev, entry)
        row = {"entry": entry, "prev_hash": prev, "hash": h}
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        return h

    def verify(self) -> int:
        """全链验证，返回条目数；篡改即 LedgerTamperError（fail-closed）。"""
        prev = GENESIS
        n = 0
        for row in self._rows():
            if row.get("prev_hash") != prev:
                raise LedgerTamperError(f"第 {n + 1} 条 prev 链断裂")
            if row.get("hash") != _entry_hash(prev, row["entry"]):
                raise LedgerTamperError(f"第 {n + 1} 条哈希不符（内容被改写）")
            prev = row["hash"]
            n += 1
        return n

    def entries(self) -> list[dict]:
        self.verify()
        return [r["entry"] for r in self._rows()]
