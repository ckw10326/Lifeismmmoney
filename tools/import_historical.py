#!/usr/bin/env python3
"""把離線附件整理進 catalog。不重查外部網站，不補造缺漏的日期或 HTML。"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import sys
from pathlib import Path

from promo_lib import (
    DATA_NOTE,
    PromoError,
    content_payload,
    content_version,
    dump_catalog,
    empty_catalog,
    make_record,
    validate_catalog,
)

INITIAL_AT = "2026-10-29T12:30:00+08:00"
EZ_UPDATE_AT = "2026-10-31T12:23:00+08:00"
INTRODUCED = {
    "nx-itf-2026": "2026-11-02T12:18:00+08:00",
    "tr-itf-2026": "2026-11-02T12:18:00+08:00",
    "ak-itf-2026": "2026-11-03T12:20:00+08:00",
    "it-itf-2026": "2026-11-03T12:20:00+08:00",
    "ze-itf-2026": "2026-11-04T12:18:00+08:00",
    "trip-1111-2026": "2026-11-07T12:25:00+08:00",
    "vj-doubleday-20261110": "2026-11-07T12:25:00+08:00",
}
HISTORICAL_CANDIDATES = {
    "2026-10-31T12:23:00+08:00": ["ez-itf-2026"],
    "2026-11-02T12:18:00+08:00": ["nx-itf-2026", "tr-itf-2026"],
    "2026-11-03T12:20:00+08:00": ["ak-itf-2026", "it-itf-2026"],
    "2026-11-04T12:18:00+08:00": ["ze-itf-2026"],
    "2026-11-07T12:25:00+08:00": ["trip-1111-2026", "vj-doubleday-20261110"],
}
SNAPSHOT_FILES = {
    "2026-11-04T12:18:00+08:00": "promos-20261104-1218.html",
    "2026-11-07T12:25:00+08:00": "promos-20261107-1225.html",
}
SCRIPT_ORDER = ("gen.py", "gen2.py", "gen3.py", "gen4.py", "gen5.py")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="由離線附件產生 catalog 與歷史快照複本")
    parser.add_argument("--fixtures", default="tests/fixtures")
    parser.add_argument("--out", default="data/catalog.json")
    parser.add_argument("--snapshots", default="snapshots")
    args = parser.parse_args(argv)
    fixtures = Path(args.fixtures)
    catalog = build_catalog(fixtures)
    errors = validate_catalog(catalog)
    if errors:
        raise SystemExit("；".join(errors))
    copy_original_snapshots(fixtures, Path(args.snapshots))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(dump_catalog(catalog), encoding="utf-8")
    print(args.out)
    return 0


def build_catalog(fixtures: Path) -> dict:
    latest = json.loads((fixtures / "latest.json").read_text(encoding="utf-8"))
    initial = extract_deals(fixtures / "gen.py")
    initial_map = {deal["id"]: deal for deal in initial}
    latest_map = {deal["id"]: deal for deal in latest["deals"]}
    order = list(dict.fromkeys([deal["id"] for deal in initial] + [deal["id"] for deal in latest["deals"]]))
    catalog = empty_catalog()
    catalog["data_note"] = DATA_NOTE
    records = []
    for ident in order:
        records.append(_record_for(ident, initial_map.get(ident), latest_map.get(ident)))
    catalog["deals"] = records
    catalog["excluded"] = _excluded(latest.get("excluded") or [])
    catalog["pending_watch"] = _watches(fixtures, latest.get("pending_watch") or [])
    catalog["checks"] = _checks(fixtures, {deal["id"]: deal for deal in records})
    return catalog


def _record_for(ident: str, initial: dict | None, latest: dict | None) -> dict:
    if initial and latest:
        old_payload = content_payload(initial)
        new_payload = content_payload(latest)
        if old_payload == new_payload:
            return make_record(latest, first_seen_at=INITIAL_AT, last_verified_at=INITIAL_AT, notified=True)
        revision = {
            "content_version": content_version(old_payload),
            "recorded_at": EZ_UPDATE_AT if ident == "ez-itf-2026" else None,
            "content": old_payload,
        }
        record = make_record(
            latest,
            first_seen_at=INITIAL_AT,
            last_verified_at=EZ_UPDATE_AT if ident == "ez-itf-2026" else None,
            notified=True,
            revisions=[revision],
        )
        if ident != "ez-itf-2026":
            record["review_notes"] = [
                "內容與初始腳本不同，但檢查紀錄沒有單獨寫出變更日。最後查證時間留空，未臆造中間日期。"
            ]
        return record
    if latest:
        when = INTRODUCED.get(ident)
        if not when:
            raise PromoError(f"最新清單出現附件腳本沒有對應引入日的 id，拒絕猜測：{ident}")
        return make_record(latest, first_seen_at=when, last_verified_at=when, notified=True)
    return make_record(initial, first_seen_at=INITIAL_AT, last_verified_at=INITIAL_AT, notified=True)


def _excluded(items: list) -> list:
    rows = []
    for index, item in enumerate(items, start=1):
        rows.append(
            {
                "id": f"exc-{index:03d}",
                "item": item.get("item") or "",
                "reason": item.get("reason") or "",
                "recorded_at": None,
                "source_note": "見附件 latest.json 的排除清單。各則寫入日沒有逐筆還原，不把整份清單標成 2026-11-07 的新查證。",
            }
        )
    return rows


def _watches(fixtures: Path, latest_open: list) -> list:
    seen: list[str] = []
    for name in SCRIPT_ORDER:
        for group in extract_string_lists(fixtures / name, "pending_watch"):
            for text in group:
                if text not in seen:
                    seen.append(text)
    for text in latest_open:
        if text not in seen:
            seen.append(text)
    open_set = set(latest_open)
    rows = []
    for text in seen:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
        is_open = text in open_set
        rows.append(
            {
                "id": f"watch-{digest}",
                "text": text,
                "status": "open" if is_open else "closed",
                "recorded_at": None,
                "closed_at": None,
                "note": ""
                if is_open
                else "2026-11-07 的 latest.json 已不再把這句放在現行觀察清單。原文保留，沒有刪除。",
            }
        )
    return rows


def _checks(fixtures: Path, deals: dict) -> list:
    rows = []
    for checked_at, summary, explicit in parse_check_log(fixtures / "check-log.txt"):
        sent = _sent(summary)
        if sent and checked_at not in HISTORICAL_CANDIDATES:
            raise PromoError(f"紀錄寫已通知，但沒有對應的優惠名單，拒絕補造：{checked_at}")
        candidates = []
        for ident in HISTORICAL_CANDIDATES.get(checked_at, []):
            deal = deals[ident]
            candidates.append(
                {
                    "id": ident,
                    "content_version": deal["content_version"],
                    "change": "major_update" if deal.get("revisions") else "new",
                }
            )
        snapshot_name = SNAPSHOT_FILES.get(checked_at)
        if snapshot_name:
            snapshot_html = f"snapshots/{snapshot_name}"
            note = "附件原件，不是用現在的模板重產。"
        elif "未產生 HTML" in summary:
            snapshot_html = None
            note = "當日紀錄寫明未產生 HTML，未補造。"
        elif "已產生 HTML" in summary:
            snapshot_html = None
            note = "紀錄寫已產生 HTML，但附件沒有該檔，不補造。"
        else:
            snapshot_html = None
            note = "未通知，沒有對應的 HTML。"
        if not explicit:
            note += "此行沒有寫「台北時間」，時刻仍依同一份每日中午紀錄記為 +08:00，原文未改。"
        rows.append(
            {
                "id": checked_at,
                "checked_at": checked_at,
                "summary": summary,
                "result": "notified_historically" if sent else "no_change",
                "sent": sent,
                "snapshot_html": snapshot_html,
                "snapshot_note": note,
                "timezone_explicit": explicit,
                "candidates": candidates,
                "ignored_fields": [],
            }
        )
    return rows


def parse_check_log(path: Path) -> list[tuple[str, str, bool]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        day, clock, rest = line.split(" ", 2)
        explicit = "台北時間" in line
        checked_at = f"{day}T{clock}:00+08:00"
        rows.append((checked_at, line, explicit))
    return rows


def _sent(summary: str) -> bool:
    if "未通知" in summary:
        return False
    return "已通知" in summary or "並通知" in summary


def copy_original_snapshots(fixtures: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in SNAPSHOT_FILES.values():
        source = fixtures / name
        target = destination / name
        data = source.read_bytes()
        if target.exists() and target.read_bytes() != data:
            raise PromoError(f"歷史快照與附件不一致，拒絕覆蓋：{name}")
        if not target.exists():
            shutil.copyfile(source, target)


def extract_deals(path: Path) -> list:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "deals" for target in node.targets
        ):
            expr = ast.Expression(node.value)
            return eval(compile(expr, str(path), "eval"), {"__builtins__": {"dict": dict}}, {})
    raise PromoError(f"{path} 找不到 deals")


def extract_string_lists(path: Path, key: str) -> list[list]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return [json.loads(text).get(key) or []]
    tree = ast.parse(text)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if _target_key(target) == key:
                    found.append(ast.literal_eval(node.value))
        elif isinstance(node, ast.Dict):
            for dict_key, value in zip(node.keys, node.values):
                if isinstance(dict_key, ast.Constant) and dict_key.value == key:
                    found.append(ast.literal_eval(value))
    return found


def _target_key(target):
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant):
        return target.slice.value
    return None


if __name__ == "__main__":
    sys.exit(main())
