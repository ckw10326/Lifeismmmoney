"""自包含的每日 HTML 快照。版面沿用 11/04、11/07 的八欄表。"""

from __future__ import annotations

import html
import re
from datetime import date, datetime
from pathlib import Path

from promo_lib import TAIPEI, TITLE, classify, parse_aware

ROOT_CSS = Path(__file__).resolve().parents[1] / "css" / "site.css"
HEADERS = ("業者", "活動名稱", "符合標準", "促銷購買期間", "適用出發期間", "代表航線與最低價", "重點條件", "官方連結")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def render(catalog: dict, checked_at: str, css_text: str | None = None) -> str:
    as_of = parse_aware(checked_at, field="checked_at")
    css = css_text if css_text is not None else ROOT_CSS.read_text(encoding="utf-8")
    check = next(item for item in catalog["checks"] if item["checked_at"] == checked_at)
    deals = list(catalog["deals"])
    sections = {"new": [], "current": [], "watch": [], "ended": []}
    for deal in deals:
        sections[classify(deal, as_of)].append(deal)
    for group in sections.values():
        group.sort(key=lambda item: item["id"])
    shown = short_taipei(as_of)
    names = "；".join(f"{deal.get('vendor') or ''} {deal.get('name') or ''}".strip() for deal in sections["new"])
    summary = f"新優惠：{names}。" if names else "目前沒有尚未通知的新優惠。"
    parts = [
        "<!DOCTYPE html>",
        '<html lang="zh-Hant">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(TITLE)} {esc(shown)}</title>",
        "<style>",
        css,
        "</style>",
        "</head>",
        "<body>",
        "<h1>✈️ 機票重大促銷提醒</h1>",
        '<div class="sum">',
        f"{esc(check.get('summary') or summary)}<br>",
        f'<span class="note">查詢時間：{esc(shown)}（台北時間） {esc(checked_at)}</span>',
        "</div>",
        _section("🆕 新優惠", sections["new"], as_of, True),
        _section("📌 目前仍在進行、之前已提醒過", sections["current"], as_of, False),
        _watch(sections["watch"], catalog, as_of),
        _section("購買期已結束（資料仍保留）", sections["ended"], as_of, False),
        "<footer>",
        '<p class="note">價格多為「起」價，未稅／含稅依各家標示；限量秒殺商品不保證買得到，下單前請以官方頁面為準。此快照只在有通知候選時產生，工具沒有發送訊息。</p>',
        f'<p class="note">{esc(catalog.get("data_note") or "")}</p>',
        "</footer>",
        "</body></html>",
    ]
    return "\n".join(parts) + "\n"


def _section(title: str, deals: list, as_of: datetime, is_new: bool) -> str:
    rows = [f"<h2>{esc(title)}</h2>"]
    if not deals:
        rows.append("<p>沒有項目。</p>")
        return "\n".join(rows)
    rows.append('<div class="wrap"><table>')
    rows.append("<tr>" + "".join(f"<th>{esc(label)}</th>" for label in HEADERS) + "</tr>")
    for deal in deals:
        rows.append(_row(deal, as_of, is_new))
    rows.append("</table></div>")
    return "\n".join(rows)


def _watch(deals: list, catalog: dict, as_of: datetime) -> str:
    rows = ["<h2>👀 持續觀察中</h2>"]
    if deals:
        rows.append('<div class="wrap"><table>')
        rows.append("<tr>" + "".join(f"<th>{esc(label)}</th>" for label in HEADERS) + "</tr>")
        for deal in deals:
            rows.append(_row(deal, as_of, False))
        rows.append("</table></div>")
    items = catalog.get("pending_watch") or []
    if items:
        rows.append("<ul>")
        for item in items:
            text = item.get("text") or ""
            if item.get("note"):
                text = f"{text}（{item['note']}）"
            rows.append(f"<li>{esc(text)}</li>")
        rows.append("</ul>")
    elif not deals:
        rows.append("<p>沒有觀察項目。</p>")
    return "\n".join(line for line in rows if line != "")


def _row(deal: dict, as_of: datetime, is_new: bool) -> str:
    left = days_left(deal, as_of)
    if is_new:
        klass = "hl"
    elif left is not None and 0 <= left <= 3:
        klass = "ur"
    else:
        klass = ""
    tags = '<span class="tag new">新</span>' if is_new else ""
    if left == 0:
        tags += '<span class="tag urgent">今天截止</span>'
    elif left is not None and 0 < left <= 3:
        tags += f'<span class="tag urgent">剩 {left} 天</span>'
    crit = "<br>".join(esc(item) for item in (deal.get("crit") or []))
    href = deal.get("url") or ""
    if href.startswith("https://") or href.startswith("http://"):
        link = f'<a href="{esc(href)}" target="_blank" rel="noopener noreferrer">活動頁</a>'
    else:
        link = esc(href)
    src = f'<div class="src">來源：{esc(deal.get("src"))}</div>' if deal.get("src") else ""
    cls = f' class="{klass}"' if klass else ""
    cells = [
        f"<b>{esc(deal.get('vendor'))}</b>{tags}",
        esc(deal.get("name")),
        crit,
        esc(deal.get("buy")),
        esc(deal.get("travel")),
        esc(deal.get("route")),
        esc(deal.get("cond")) + src,
        link,
    ]
    return f"<tr{cls}>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>"


def days_left(deal: dict, as_of: datetime) -> int | None:
    end = deal.get("end") or ""
    if not DATE_RE.fullmatch(end):
        return None
    return (date.fromisoformat(end) - as_of.astimezone(TAIPEI).date()).days


def short_taipei(as_of: datetime) -> str:
    local = as_of.astimezone(TAIPEI)
    return local.strftime("%Y-%m-%d %H:%M")


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)
