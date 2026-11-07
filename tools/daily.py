#!/usr/bin/env python3
"""合併每日增量、驗證，並在有通知候選時寫出快照。

不發送訊息，不部署，不修改 HTML/CSS/JS 模板。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from promo_lib import (
    PromoError,
    ack_versions,
    apply_delta,
    dump_catalog,
    load_catalog,
    validate_catalog,
)
from snapshot_html import render

ACK_HINT = (
    "實際送出通知之後，執行 python3 tools/daily.py ack <ack.json>，"
    "帶上 id 與 content_version。這個檔案只是候選，不是已發送證明。"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="旅遊重大優惠資料合併（不發送、不部署）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    apply_parser = sub.add_parser("apply", help="套用一份增量 JSON")
    apply_parser.add_argument("delta")
    apply_parser.add_argument("--catalog", default="data/catalog.json")
    apply_parser.add_argument("--root", default=".")
    apply_parser.add_argument("--dry-run", action="store_true")

    ack_parser = sub.add_parser("ack", help="把已實際送出的內容版本記成已通知")
    ack_parser.add_argument("ackfile")
    ack_parser.add_argument("--catalog", default="data/catalog.json")
    ack_parser.add_argument("--root", default=".")

    validate_parser = sub.add_parser("validate", help="檢查資料檔是否符合規則")
    validate_parser.add_argument("--catalog", default="data/catalog.json")
    validate_parser.add_argument("--root", default=".")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "apply":
            report = command_apply(args)
        elif args.cmd == "ack":
            report = command_ack(args)
        else:
            report = command_validate(args)
    except PromoError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stdout)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report.get("status") == "invalid":
        return 2
    return 0


def command_apply(args) -> dict:
    root = Path(args.root)
    catalog_path = _resolve(root, args.catalog)
    delta_path = Path(args.delta)
    catalog = load_catalog(catalog_path.read_text(encoding="utf-8"))
    delta = json.loads(delta_path.read_text(encoding="utf-8"))
    updated, report = apply_delta(catalog, delta)
    if report["status"] == "duplicate" or args.dry_run:
        if args.dry_run and report["status"] == "applied":
            report["status"] = "dry_run"
        report["snapshot_html"] = None
        return report
    snapshot_body = None
    if report["notify"]:
        snapshot_body = render(updated, report["checked_at"])
        _write_new(root / report["snapshot_relpath"], snapshot_body)
        _write_new(root / report["outbox_relpath"], _outbox(updated, report))
    catalog_path.write_text(dump_catalog(updated), encoding="utf-8")
    report["snapshot_html"] = None
    return report


def command_ack(args) -> dict:
    root = Path(args.root)
    catalog_path = _resolve(root, args.catalog)
    payload = json.loads(Path(args.ackfile).read_text(encoding="utf-8"))
    acks = payload.get("ack_notified") if isinstance(payload, dict) else None
    if acks is None:
        raise PromoError("ack 檔要有 ack_notified 陣列")
    catalog = load_catalog(catalog_path.read_text(encoding="utf-8"))
    updated, report = ack_versions(catalog, acks)
    if report["status"] == "acked":
        catalog_path.write_text(dump_catalog(updated), encoding="utf-8")
    return report


def command_validate(args) -> dict:
    root = Path(args.root)
    catalog_path = _resolve(root, args.catalog)
    catalog = load_catalog(catalog_path.read_text(encoding="utf-8"))
    errors = validate_catalog(catalog)
    return {
        "status": "ok" if not errors else "invalid",
        "errors": errors,
        "deals": len(catalog.get("deals") or []),
        "checks": len(catalog.get("checks") or []),
    }


def _outbox(catalog: dict, report: dict) -> str:
    deals = {deal["id"]: deal for deal in catalog["deals"]}
    candidates = []
    for item in report["candidates"]:
        deal = deals[item["id"]]
        candidates.append(
            {
                "id": item["id"],
                "content_version": item["content_version"],
                "change": item["change"],
                "vendor": deal["vendor"],
                "name": deal["name"],
                "url": deal["url"],
            }
        )
    body = {
        "check_id": report["check_id"],
        "checked_at": report["checked_at"],
        "notify": True,
        "message_status": "candidate_only_not_sent",
        "candidates": candidates,
        "ack_hint": ACK_HINT,
    }
    return json.dumps(body, ensure_ascii=False, indent=2) + "\n"


def _write_new(path: Path, text: str) -> None:
    if path.exists():
        raise PromoError(f"檔案已存在，拒絕覆蓋：{path.as_posix()}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    return path


if __name__ == "__main__":
    sys.exit(main())
