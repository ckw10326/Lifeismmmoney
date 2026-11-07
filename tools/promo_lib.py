"""旅遊重大優惠的資料規則。

網站（js/app.js）與每日快照共用這裡的分類結果；下架、版本與通知候選只在這一支決定。
此模組不發送訊息、不連網、不讀取憑證。
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

SCHEMA_VERSION = 1
TITLE = "Life is money 旅遊重大優惠"
TAIPEI = ZoneInfo("Asia/Taipei")

CRITERIA = [
    "航空公司全航線大促",
    "旅展或旅遊網站年度檔期",
    "比平常便宜30%以上",
    "廉航單程未稅NT$1000以下",
]

# 八欄。內容版本只看這些，加上來源與呼叫端明確給出的購買時間。
CONTENT_TEXT_KEYS = (
    "vendor",
    "name",
    "buy",
    "travel",
    "route",
    "cond",
    "url",
    "src",
)

FIELD_LABELS = {
    "vendor": "業者",
    "name": "活動名稱",
    "crit": "符合標準",
    "buy": "促銷購買期間",
    "travel": "適用出發期間",
    "route": "代表航線與最低價",
    "cond": "重點條件",
    "url": "官方連結",
}

QUALIFIED_KEYS = (
    "vendor",
    "name",
    "crit",
    "buy",
    "travel",
    "route",
    "cond",
    "url",
)

# 查詢時間、倒數、一次性旗標。出現在增量裡會被丟掉，不進內容版本。
NOISE_KEYS = {
    "new",
    "alerted_update",
    "days_left",
    "query_time",
    "query_time_taipei",
    "last_checked",
    "last_checked_taipei",
    "countdown",
    "remaining",
    "remaining_days",
}

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WEEKDAY = "一二三四五六日"
WEEKDAY_RE = re.compile(
    r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})（([一二三四五六日])）"
)
DATETIME_RE = re.compile(
    r"(?P<y>\d{4})[/.](?P<m>\d{1,2})[/.](?P<d>\d{1,2})"
    r"(?:（[一二三四五六日]）|\([一二三四五六日]\))?"
    r"\s*(?P<h>\d{1,2}):(?P<mi>\d{2})(?::(?P<s>\d{2}))?"
)
ZONE_RES = (
    (re.compile(r"台北時間|台灣時間|Asia/Taipei"), "+08:00"),
    (re.compile(r"UTC\s*\+\s*0?8|GMT\s*\+\s*0?8|(?<!\d)\+08:00"), "+08:00"),
    (re.compile(r"UTC\s*\+\s*0?7|GMT\s*\+\s*0?7|(?<!\d)\+07:00"), "+07:00"),
)

RULES = {
    "expiry": "只有 window.purchase_end 是帶時區的完整時間時，as_of >= purchase_end 才離開現行清單。只有日期、只有鐘點但沒寫時區、或多個時區並存，都不自動下架。",
    "upcoming": "purchase_start 尚未到的優惠仍留在現行清單，並標成尚未開賣。",
    "identity": "id 穩定。content_version 不含查詢時間、倒數與 new/alerted_update。",
    "notify": "工具只寫出通知候選，不發送訊息。notified_version 只在 ack 後才推進。",
    "history": "優惠、排除項、觀察句與檢查紀錄都不刪除。",
}

DATA_NOTE = (
    "現行優惠原文來自附件 latest.json（檔內查詢時間 2026-11-07 12:25）"
    "以及初始腳本裡、後來未再出現在 latest.json 的越捷 10 條航線。"
    "每一筆的最後查證時間是該筆內容在附件中最後一次被寫下的時間，"
    "不是網頁開啟日，也不代表 2026-11-07 有把所有舊優惠重查一遍。"
    "10/27 沒有檢查紀錄，未補。11/01 與 11/05 的紀錄寫明未產生 HTML，未補造快照。"
    "購買期間裡的星期若與日曆不符，只產生警告，不改原文。"
)


class PromoError(ValueError):
    """呼叫端可以修正的資料錯誤。不寫檔。"""


def empty_catalog() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "title": TITLE,
        "criteria": list(CRITERIA),
        "rules": dict(RULES),
        "data_note": DATA_NOTE,
        "deals": [],
        "excluded": [],
        "pending_watch": [],
        "checks": [],
        "last_successful_check": None,
    }


def _strip(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_aware(value: str, *, field: str = "時間") -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise PromoError(f"{field} 必須是帶時區的字串")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise PromoError(f"{field} 無法解析：{value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PromoError(f"{field} 沒有時區，拒絕猜測：{value}")
    if parsed.microsecond:
        raise PromoError(f"{field} 請精確到秒，不要帶小數：{value}")
    return parsed


def canonical_dt(value: str | None, *, field: str = "時間") -> str | None:
    if value is None or value == "":
        return None
    return parse_aware(value, field=field).isoformat(timespec="seconds")


def instant(value: str) -> datetime:
    return parse_aware(value).astimezone(timezone.utc)


def content_payload(raw: dict) -> dict:
    crit_raw = raw.get("crit") or []
    if isinstance(crit_raw, str):
        crit_raw = [crit_raw]
    if not isinstance(crit_raw, list):
        raise PromoError("crit 必須是字串陣列")
    crit = [_strip(item) for item in crit_raw if _strip(item)]
    end = _strip(raw.get("end")) or None
    if end is not None and not DATE_RE.fullmatch(end):
        raise PromoError(f"end 只能是 YYYY-MM-DD 或空值，收到：{end}")
    return {
        "vendor": _strip(raw.get("vendor")),
        "name": _strip(raw.get("name")),
        "crit": crit,
        "buy": _strip(raw.get("buy")),
        "end": end,
        "travel": _strip(raw.get("travel")),
        "route": _strip(raw.get("route")),
        "cond": _strip(raw.get("cond")),
        "url": _strip(raw.get("url")),
        "src": _strip(raw.get("src")),
        "purchase_start": canonical_dt(raw.get("purchase_start"), field="purchase_start"),
        "purchase_end": canonical_dt(raw.get("purchase_end"), field="purchase_end"),
    }


def content_version(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "cv_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def check_id(value: str) -> str:
    if not isinstance(value, str):
        raise PromoError("id 必須是小寫英數與連字號")
    if not ID_RE.fullmatch(value):
        raise PromoError(f"id 格式不符（小寫英數與連字號，最長 64）：{value}")
    return value


def is_qualified(deal: dict) -> bool:
    if deal.get("observe"):
        return False
    for key in QUALIFIED_KEYS:
        value = deal.get(key)
        if key == "crit":
            if not value:
                return False
        elif not _strip(value):
            return False
    return True


def weekday_warnings(text: str) -> list[str]:
    found = []
    for match in WEEKDAY_RE.finditer(text or ""):
        year, month, day, label = (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            match.group(4),
        )
        try:
            actual = date(year, month, day).weekday()
        except ValueError:
            found.append(f"日期無法解析：{match.group(0)}。保留原文。")
            continue
        actual_label = WEEKDAY[actual]
        if actual_label != label:
            found.append(
                f"星期不一致：原文「{match.group(0)}」標（{label}），"
                f"該日實際為星期{actual_label}。保留原文，未改寫。"
            )
    return found


def zones_in(text: str) -> list[str]:
    found: list[str] = []
    for pattern, offset in ZONE_RES:
        if pattern.search(text or "") and offset not in found:
            found.append(offset)
    return found


def datetimes_in(text: str) -> list[tuple[int, int, int, int, int, int]]:
    found = []
    for match in DATETIME_RE.finditer(text or ""):
        second = int(match.group("s") or 0)
        found.append(
            (
                int(match.group("y")),
                int(match.group("m")),
                int(match.group("d")),
                int(match.group("h")),
                int(match.group("mi")),
                second,
            )
        )
    return found


def parse_buy_window(buy: str) -> tuple[str | None, str | None, list[str]]:
    """從購買期間原文推結束時間。

    只有「恰好一個時區」且「至少兩個帶鐘點的完整日期」才填 window。
    推導結果不改原文，也不進入 content_version。
    """
    warnings: list[str] = []
    text = buy or ""
    zones = zones_in(text)
    clocks = datetimes_in(text)
    if len(zones) > 1:
        warnings.append("購買期間同時出現多個時區，不自動解析開始或結束時間，因此不自動下架。")
        return None, None, warnings
    if clocks and not zones:
        warnings.append("購買期間有鐘點，但沒有寫時區，不自動下架。")
        return None, None, warnings
    if not clocks:
        return None, None, warnings
    if len(clocks) == 1:
        warnings.append("購買期間只找到一個含鐘點的時間，無法分辨是開始還是結束，不自動下架。")
        return None, None, warnings
    offset = zones[0]
    start = _clock_to_iso(clocks[0], offset)
    end = _clock_to_iso(clocks[-1], offset)
    if start is None or end is None:
        warnings.append("購買期間的鐘點無法組成有效時間，不自動下架。")
        return None, None, warnings
    return start, end, warnings


def _clock_to_iso(parts: tuple[int, int, int, int, int, int], offset: str) -> str | None:
    year, month, day, hour, minute, second = parts
    try:
        parsed = datetime.fromisoformat(
            f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}{offset}"
        )
    except ValueError:
        return None
    return parsed.isoformat(timespec="seconds")


def missing_field_warnings(deal: dict) -> list[str]:
    missing = []
    for key in QUALIFIED_KEYS:
        value = deal.get(key)
        empty = not value if key == "crit" else not _strip(value)
        if empty:
            missing.append(FIELD_LABELS[key])
    if not missing:
        return []
    return ["缺少欄位：" + "、".join(missing) + "。列入觀察，不當作可通知的合格優惠。"]


def deal_warnings(deal: dict) -> list[str]:
    warnings: list[str] = []
    warnings.extend(missing_field_warnings(deal))
    blob = "\n".join(_strip(deal.get(key)) for key in ("buy", "travel", "route", "cond", "name"))
    warnings.extend(weekday_warnings(blob))
    if "待確認" in blob:
        warnings.append("原文含「待確認」，維持原文，未補齊。")
    end = deal.get("end")
    buy = _strip(deal.get("buy"))
    if end and DATE_RE.fullmatch(end):
        year, month, day = end.split("-")
        forms = {end, f"{year}/{int(month)}/{int(day)}", f"{year}/{month}/{day}"}
        if not any(form in buy for form in forms):
            warnings.append(
                f"end 欄為 {end}，購買期間原文沒有同一個完整日期。兩邊都保留，未改寫。"
            )
    explicit_start = deal.get("purchase_start")
    explicit_end = deal.get("purchase_end")
    parsed_start, parsed_end, parsed_warnings = parse_buy_window(buy)
    if explicit_start or explicit_end:
        if parsed_end and explicit_end and parsed_end != explicit_end:
            warnings.append(
                "明確記入的 purchase_end 與購買期間原文解析結果不同。下架只採用明確記入的時間，原文不改。"
            )
        if parsed_start and explicit_start and parsed_start != explicit_start:
            warnings.append(
                "明確記入的 purchase_start 與購買期間原文解析結果不同。顯示與下架只採用明確記入的時間，原文不改。"
            )
    else:
        warnings.extend(parsed_warnings)
    url = _strip(deal.get("url"))
    if url and not (url.startswith("https://") or url.startswith("http://")):
        warnings.append("官方連結不是 http 或 https，頁面只以文字顯示，不會做成連結。")
    return warnings


def effective_window(deal: dict) -> dict:
    explicit_start = deal.get("purchase_start")
    explicit_end = deal.get("purchase_end")
    if explicit_start or explicit_end:
        return {
            "purchase_start": explicit_start,
            "purchase_end": explicit_end,
            "basis": "explicit",
        }
    start, end, _warnings = parse_buy_window(_strip(deal.get("buy")))
    if start or end:
        return {"purchase_start": start, "purchase_end": end, "basis": "parsed_buy"}
    return {"purchase_start": None, "purchase_end": None, "basis": "unresolved"}


def refresh_annotations(deal: dict) -> dict:
    deal["warnings"] = deal_warnings(deal)
    deal["window"] = effective_window(deal)
    return deal


def sale_flags(deal: dict, as_of: datetime) -> dict:
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise PromoError("as_of 必須帶時區")
    window = deal.get("window") or {}
    end_iso = window.get("purchase_end")
    start_iso = window.get("purchase_start")
    ended = bool(end_iso) and as_of >= parse_aware(end_iso, field="purchase_end")
    upcoming = bool(start_iso) and as_of < parse_aware(start_iso, field="purchase_start")
    date_only_past = False
    end = deal.get("end")
    if not end_iso and end and DATE_RE.fullmatch(end):
        taipei_day = as_of.astimezone(TAIPEI).date().isoformat()
        date_only_past = taipei_day > end
    return {
        "ended": ended,
        "upcoming": upcoming,
        "date_only_past": date_only_past,
    }


def classify(deal: dict, as_of: datetime) -> str:
    flags = sale_flags(deal, as_of)
    if flags["ended"]:
        return "ended"
    if not is_qualified(deal):
        return "watch"
    if deal.get("notified_version") != deal.get("content_version"):
        return "new"
    return "current"


def view_model(catalog: dict, as_of: datetime) -> dict:
    sections = {"new": [], "current": [], "watch": [], "ended": []}
    flags = {}
    for deal in catalog.get("deals") or []:
        section = classify(deal, as_of)
        sections[section].append(deal["id"])
        flags[deal["id"]] = sale_flags(deal, as_of)
    for key in sections:
        sections[key] = sorted(sections[key])
    open_watch = sorted(
        item["id"] for item in catalog.get("pending_watch") or [] if item.get("status") == "open"
    )
    closed_watch = sorted(
        item["id"] for item in catalog.get("pending_watch") or [] if item.get("status") != "open"
    )
    return {
        "sections": sections,
        "flags": flags,
        "open_watch": open_watch,
        "closed_watch": closed_watch,
    }


def _ordered_deal(deal: dict) -> dict:
    payload = content_payload(deal)
    revisions = []
    for revision in deal.get("revisions") or []:
        revisions.append(
            {
                "content_version": revision["content_version"],
                "recorded_at": revision.get("recorded_at"),
                "content": content_payload(revision.get("content") or {}),
            }
        )
    ordered = {
        "id": deal["id"],
        **payload,
        "observe": bool(deal.get("observe")),
        "content_version": deal["content_version"],
        "notified_version": deal.get("notified_version"),
        "first_seen_at": deal.get("first_seen_at"),
        "last_verified_at": deal.get("last_verified_at"),
        "window": {
            "purchase_start": (deal.get("window") or {}).get("purchase_start"),
            "purchase_end": (deal.get("window") or {}).get("purchase_end"),
            "basis": (deal.get("window") or {}).get("basis") or "unresolved",
        },
        "warnings": list(deal.get("warnings") or []),
        "review_notes": list(deal.get("review_notes") or []),
        "revisions": revisions,
    }
    return ordered


def _ordered_check(check: dict) -> dict:
    return {
        "id": check["id"],
        "checked_at": check["checked_at"],
        "summary": check.get("summary") or "",
        "result": check.get("result") or "no_change",
        "sent": bool(check.get("sent")),
        "snapshot_html": check.get("snapshot_html"),
        "snapshot_note": check.get("snapshot_note"),
        "timezone_explicit": bool(check.get("timezone_explicit", True)),
        "candidates": [
            {
                "id": item["id"],
                "content_version": item["content_version"],
                "change": item["change"],
            }
            for item in (check.get("candidates") or [])
        ],
        "ignored_fields": list(check.get("ignored_fields") or []),
    }


def normalize_catalog(catalog: dict) -> dict:
    deals = [_ordered_deal(refresh_annotations(copy.deepcopy(deal))) for deal in catalog.get("deals") or []]
    deals.sort(key=lambda item: item["id"])
    excluded = []
    for item in catalog.get("excluded") or []:
        excluded.append(
            {
                "id": item["id"],
                "item": item.get("item") or "",
                "reason": item.get("reason") or "",
                "recorded_at": item.get("recorded_at"),
                "source_note": item.get("source_note") or "",
            }
        )
    excluded.sort(key=lambda item: item["id"])
    watches = []
    for item in catalog.get("pending_watch") or []:
        watches.append(
            {
                "id": item["id"],
                "text": item.get("text") or "",
                "status": item.get("status") or "open",
                "recorded_at": item.get("recorded_at"),
                "closed_at": item.get("closed_at"),
                "note": item.get("note") or "",
            }
        )
    watches.sort(key=lambda item: item["id"])
    checks = [_ordered_check(item) for item in catalog.get("checks") or []]
    checks.sort(key=lambda item: item["checked_at"])
    last = None
    if checks:
        latest = max(checks, key=lambda item: instant(item["checked_at"]))
        last = {
            "id": latest["id"],
            "checked_at": latest["checked_at"],
            "summary": latest["summary"],
            "result": latest["result"],
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "title": catalog.get("title") or TITLE,
        "criteria": list(catalog.get("criteria") or CRITERIA),
        "rules": dict(RULES),
        "data_note": catalog.get("data_note") or DATA_NOTE,
        "deals": deals,
        "excluded": excluded,
        "pending_watch": watches,
        "checks": checks,
        "last_successful_check": last,
    }


def dump_catalog(catalog: dict) -> str:
    return json.dumps(normalize_catalog(catalog), ensure_ascii=False, indent=2) + "\n"


def load_catalog(text: str) -> dict:
    data = json.loads(text)
    if data.get("schema_version") != SCHEMA_VERSION:
        raise PromoError("不支援的 schema_version")
    return data


def validate_catalog(catalog: dict) -> list[str]:
    errors = []
    if catalog.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version 不是 1")
    seen = set()
    versions_by_id = {}
    for deal in catalog.get("deals") or []:
        ident = deal.get("id")
        if ident in seen:
            errors.append(f"重複 id：{ident}")
        seen.add(ident)
        try:
            payload = content_payload(deal)
        except PromoError as exc:
            errors.append(f"{ident}：{exc}")
            continue
        expected = content_version(payload)
        if deal.get("content_version") != expected:
            errors.append(f"{ident} 的 content_version 與內容不一致")
        known = {expected}
        for revision in deal.get("revisions") or []:
            known.add(revision.get("content_version"))
        notified = deal.get("notified_version")
        if notified is not None and notified not in known:
            errors.append(f"{ident} 的 notified_version 對不到任何內容版本")
        versions_by_id[ident] = known | {notified}
        basis = (deal.get("window") or {}).get("basis")
        if basis not in {"explicit", "parsed_buy", "unresolved"}:
            errors.append(f"{ident} 的 window.basis 不正確")
    check_instants = []
    for check in catalog.get("checks") or []:
        try:
            parsed = parse_aware(check.get("checked_at") or "", field="checked_at")
        except PromoError as exc:
            errors.append(str(exc))
            continue
        check_instants.append(parsed.astimezone(timezone.utc))
        if parsed.astimezone(TAIPEI).date().isoformat() == "2026-10-27":
            errors.append("不應存在 2026-10-27 的檢查紀錄")
    if len(check_instants) != len(set(check_instants)):
        errors.append("檢查紀錄有重複的同一瞬間")
    return errors


def snapshot_relpath(checked_at: str) -> str:
    local = parse_aware(checked_at, field="checked_at").astimezone(TAIPEI)
    return f"snapshots/promos-{local.strftime('%Y%m%d-%H%M')}.html"


def outbox_relpath(checked_at: str) -> str:
    local = parse_aware(checked_at, field="checked_at").astimezone(TAIPEI)
    return f"data/outbox/{local.strftime('%Y%m%d-%H%M')}.json"


def _find_deal(catalog: dict, ident: str) -> dict | None:
    for deal in catalog["deals"]:
        if deal["id"] == ident:
            return deal
    return None


def make_record(
    raw: dict,
    *,
    first_seen_at: str | None,
    last_verified_at: str | None,
    notified: bool,
    revisions: list | None = None,
) -> dict:
    ident = check_id(raw["id"])
    payload = content_payload(raw)
    version = content_version(payload)
    record = {
        "id": ident,
        **payload,
        "observe": bool(raw.get("observe")),
        "content_version": version,
        "notified_version": version if notified else None,
        "first_seen_at": first_seen_at,
        "last_verified_at": last_verified_at,
        "revisions": revisions or [],
        "review_notes": list(raw.get("review_notes") or []),
    }
    return refresh_annotations(record)


def apply_delta(catalog: dict, delta: dict) -> tuple[dict, dict]:
    if not isinstance(delta, dict):
        raise PromoError("增量檔必須是 JSON 物件")
    allowed = {
        "checked_at",
        "summary",
        "upserts",
        "verify_ids",
        "excluded_add",
        "pending_watch",
        "ack_notified",
    }
    extra = sorted(set(delta) - allowed)
    if extra:
        raise PromoError("增量檔有未支援的欄位（每日不要重寫整份清單）：" + "、".join(extra))
    for banned in ("delete", "remove", "deleted", "removed_ids"):
        if banned in delta:
            raise PromoError("歷史不刪，增量檔不能帶刪除欄位")
    checked_at = canonical_dt(delta.get("checked_at"), field="checked_at")
    if not checked_at:
        raise PromoError("checked_at 必填，而且要帶時區")
    next_catalog = copy.deepcopy(catalog)
    next_catalog.setdefault("deals", [])
    next_catalog.setdefault("excluded", [])
    next_catalog.setdefault("pending_watch", [])
    next_catalog.setdefault("checks", [])
    for existing in next_catalog["checks"]:
        if instant(existing["checked_at"]) == instant(checked_at):
            return catalog, {
                "status": "duplicate",
                "check_id": existing["id"],
                "checked_at": existing["checked_at"],
                "notify": False,
                "candidates": [],
                "snapshot_html": None,
                "snapshot_relpath": None,
                "outbox_relpath": None,
                "warnings": ["這個查證時間已經寫入過，沒有再次變更資料。"],
                "ignored_fields": [],
            }

    report_warnings: list[str] = []
    ignored: list[str] = []
    upserts = delta.get("upserts") or []
    if not isinstance(upserts, list):
        raise PromoError("upserts 必須是陣列")
    seen_ids = set()
    for raw in upserts:
        if not isinstance(raw, dict):
            raise PromoError("upserts 裡的每一筆都必須是物件")
        ident = check_id(raw.get("id") or "")
        if ident in seen_ids:
            raise PromoError(f"同一份增量裡 id 重複：{ident}")
        seen_ids.add(ident)
        noise = sorted(set(raw) & NOISE_KEYS)
        if noise:
            ignored.extend(f"{ident}:{key}" for key in noise)
            report_warnings.append(f"{ident} 忽略不進入內容版本的欄位：" + "、".join(noise))
        current = _find_deal(next_catalog, ident)
        merged = {} if current is None else content_payload(current)
        merged["id"] = ident
        merged["observe"] = bool(current.get("observe")) if current else False
        for key in list(CONTENT_TEXT_KEYS) + ["crit", "end", "purchase_start", "purchase_end", "observe"]:
            if key in raw and key not in NOISE_KEYS:
                merged[key] = raw[key]
        revisions = list(current.get("revisions") or []) if current else []
        payload = content_payload(merged)
        version = content_version(payload)
        if current and current["content_version"] != version:
            revisions.append(
                {
                    "content_version": current["content_version"],
                    "recorded_at": checked_at,
                    "content": content_payload(current),
                }
            )
            notified_version = current.get("notified_version")
            first_seen = current.get("first_seen_at")
        elif current:
            notified_version = current.get("notified_version")
            first_seen = current.get("first_seen_at")
        else:
            notified_version = None
            first_seen = checked_at
        record = {
            "id": ident,
            **payload,
            "observe": bool(merged.get("observe")),
            "content_version": version,
            "notified_version": notified_version,
            "first_seen_at": first_seen,
            "last_verified_at": checked_at,
            "revisions": revisions,
            "review_notes": list(current.get("review_notes") or []) if current else [],
        }
        refresh_annotations(record)
        if current is None:
            next_catalog["deals"].append(record)
        else:
            current.clear()
            current.update(record)

    mentioned = set(seen_ids)
    for ident in delta.get("verify_ids") or []:
        ident = check_id(ident)
        if ident in mentioned:
            continue
        current = _find_deal(next_catalog, ident)
        if current is None:
            report_warnings.append(f"verify_ids 找不到 {ident}，沒有新建空白優惠。")
            continue
        current["last_verified_at"] = checked_at

    for extra in delta.get("excluded_add") or []:
        if not isinstance(extra, dict):
            raise PromoError("excluded_add 的每一筆都必須是物件")
        item = _strip(extra.get("item"))
        reason = _strip(extra.get("reason"))
        if not item or not reason:
            raise PromoError("排除項要有 item 與 reason")
        if any(old["item"] == item and old["reason"] == reason for old in next_catalog["excluded"]):
            report_warnings.append(f"排除項已存在，未重複新增：{item}")
            continue
        number = len(next_catalog["excluded"]) + 1
        next_catalog["excluded"].append(
            {
                "id": f"exc-{number:03d}",
                "item": item,
                "reason": reason,
                "recorded_at": checked_at,
                "source_note": "由增量檔新增",
            }
        )

    for watch in delta.get("pending_watch") or []:
        if isinstance(watch, str):
            watch = {"text": watch, "status": "open"}
        if not isinstance(watch, dict):
            raise PromoError("pending_watch 的每一筆都必須是物件或字串")
        status = watch.get("status") or "open"
        if status not in {"open", "closed"}:
            raise PromoError("觀察項 status 只能是 open 或 closed")
        text = _strip(watch.get("text"))
        ident = watch.get("id")
        existing = None
        if ident:
            ident = check_id(ident) if ident.startswith("watch-") or ID_RE.fullmatch(ident) else None
        for current in next_catalog["pending_watch"]:
            if ident and current["id"] == ident:
                existing = current
                break
            if text and current["text"] == text:
                existing = current
                break
        if existing is None:
            if not text:
                raise PromoError("新的觀察項要有 text")
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
            next_catalog["pending_watch"].append(
                {
                    "id": f"watch-{digest}",
                    "text": text,
                    "status": status,
                    "recorded_at": checked_at,
                    "closed_at": checked_at if status == "closed" else None,
                    "note": _strip(watch.get("note")),
                }
            )
        else:
            if text and text != existing["text"]:
                report_warnings.append(
                    f"{existing['id']} 的原文已保留，這次沒有覆蓋成新句子。請用新 text 另建一筆。"
                )
            if status == "closed" and existing.get("status") != "closed":
                existing["status"] = "closed"
                existing["closed_at"] = checked_at
            elif status == "open" and existing.get("status") != "open":
                existing["status"] = "open"
                existing["closed_at"] = None
            if _strip(watch.get("note")):
                existing["note"] = _strip(watch.get("note"))

    acks = delta.get("ack_notified") or []
    _apply_acks(next_catalog, acks)

    candidates = _candidates(next_catalog, as_of=parse_aware(checked_at, field="checked_at"))
    result = "candidate" if candidates else "no_change"
    summary = _strip(delta.get("summary")) or (
        "有新的合格優惠或重大更新，已產生通知候選，尚未發送。"
        if candidates
        else "無新的合格優惠或重大更新，只留下檢查紀錄，不通知。"
    )
    check = {
        "id": checked_at,
        "checked_at": checked_at,
        "summary": summary,
        "result": result,
        "sent": False,
        "snapshot_html": snapshot_relpath(checked_at) if candidates else None,
        "snapshot_note": None
        if candidates
        else "無新合格或重大更新，不產生 HTML。",
        "timezone_explicit": True,
        "candidates": candidates,
        "ignored_fields": ignored,
    }
    next_catalog["checks"].append(check)
    for deal in next_catalog["deals"]:
        refresh_annotations(deal)
    normalized = normalize_catalog(next_catalog)
    report = {
        "status": "applied",
        "check_id": checked_at,
        "checked_at": checked_at,
        "notify": bool(candidates),
        "candidates": candidates,
        "snapshot_html": None,
        "snapshot_relpath": check["snapshot_html"],
        "outbox_relpath": outbox_relpath(checked_at) if candidates else None,
        "warnings": report_warnings,
        "ignored_fields": ignored,
    }
    return normalized, report


def _candidates(catalog: dict, as_of: datetime) -> list[dict]:
    found = []
    for deal in catalog["deals"]:
        if classify(deal, as_of) != "new":
            continue
        previous = deal.get("revisions") or []
        found.append(
            {
                "id": deal["id"],
                "content_version": deal["content_version"],
                "change": "major_update" if previous else "new",
            }
        )
    found.sort(key=lambda item: item["id"])
    return found


def _apply_acks(catalog: dict, acks: list) -> None:
    if not acks:
        return
    if not isinstance(acks, list):
        raise PromoError("ack_notified 必須是陣列")
    for ack in acks:
        if not isinstance(ack, dict):
            raise PromoError("ack 的每一筆都必須是物件")
        ident = check_id(ack.get("id") or "")
        version = ack.get("content_version")
        deal = _find_deal(catalog, ident)
        if deal is None:
            raise PromoError(f"ack 找不到優惠：{ident}")
        if version != deal.get("content_version"):
            raise PromoError(
                f"{ident} 的 ack 版本不是目前內容版本，拒絕把舊通知記成已涵蓋新內容"
            )
        deal["notified_version"] = version
    for check in catalog.get("checks") or []:
        pending = check.get("candidates") or []
        if not pending:
            continue
        if all(_ack_covers(catalog, item) for item in pending):
            check["sent"] = True


def _ack_covers(catalog: dict, candidate: dict) -> bool:
    deal = _find_deal(catalog, candidate["id"])
    return bool(
        deal
        and deal.get("notified_version") == candidate["content_version"]
        and deal.get("content_version") == candidate["content_version"]
    )


def ack_versions(catalog: dict, acks: list) -> tuple[dict, dict]:
    if not acks:
        raise PromoError("ack 檔是空的")
    next_catalog = copy.deepcopy(catalog)
    before = dump_catalog(next_catalog)
    _apply_acks(next_catalog, acks)
    normalized = normalize_catalog(next_catalog)
    changed = dump_catalog(normalized) != before
    return normalized, {
        "status": "acked" if changed else "already_acked",
        "notify": False,
        "sent_message": False,
    }
