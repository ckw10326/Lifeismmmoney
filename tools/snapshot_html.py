"""自包含的每日 HTML 快照。只在有通知候選時由 daily.py 呼叫。"""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

from promo_lib import TITLE, classify, parse_aware, sale_flags

ROOT_CSS = Path(__file__).resolve().parents[1] / "css" / "site.css"


def render(catalog: dict, checked_at: str, css_text: str | None = None) -> str:
    as_of = parse_aware(checked_at, field="checked_at")
    css = css_text if css_text is not None else ROOT_CSS.read_text(encoding="utf-8")
    if "980px" in css:
        raise RuntimeError("快照 CSS 不應強制 980px 寬表")
    check = next(item for item in catalog["checks"] if item["checked_at"] == checked_at)
    candidate_ids = {item["id"] for item in check.get("candidates") or []}
    deals = {deal["id"]: deal for deal in catalog["deals"]}
    sections = {"new": [], "current": [], "watch": [], "ended": []}
    for deal in catalog["deals"]:
        sections[classify(deal, as_of)].append(deal)
    for group in sections.values():
        group.sort(key=lambda item: item["id"])
    open_watch = [item for item in catalog["pending_watch"] if item.get("status") == "open"]
    closed_watch = [item for item in catalog["pending_watch"] if item.get("status") != "open"]
    parts = [
        "<!DOCTYPE html>",
        '<html lang="zh-Hant">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(TITLE)} {esc(checked_at)}</title>",
        "<style>",
        css,
        "</style>",
        "</head>",
        "<body>",
        '<header class="top">',
        f"<h1>{esc(TITLE)}</h1>",
        f"<p>這份快照的查證時間：{esc(checked_at)}。它不是檔案存檔當下的時鐘，也不能把舊優惠改標成今天查過。</p>",
        f"<p>{esc(check.get('summary') or '')}</p>",
        "</header>",
        '<main id="app">',
        _candidate_block(check, deals),
        _section("新優惠／重大更新", sections["new"], as_of, candidate_ids),
        _section("目前仍有效", sections["current"], as_of, candidate_ids),
        _watch_section(sections["watch"], open_watch, closed_watch, as_of),
        _section("購買期已結束（仍保留）", sections["ended"], as_of, candidate_ids),
        _excluded(catalog),
        "</main>",
        "<footer><p>價格是業者公告的起價。此工具只產生快照與通知候選，沒有發送訊息。</p></footer>",
        "</body></html>",
    ]
    return "\n".join(parts) + "\n"


def _candidate_block(check: dict, deals: dict) -> str:
    rows = ['<section id="candidates"><h2>通知候選（尚未發送）</h2>']
    candidates = check.get("candidates") or []
    if not candidates:
        rows.append("<p>這次沒有通知候選。</p></section>")
        return "\n".join(rows)
    rows.append("<ul>")
    for item in candidates:
        deal = deals[item["id"]]
        rows.append(
            "<li>"
            f"{esc(deal['vendor'])}：{esc(deal['name'])}"
            f"（{esc(item['change'])}，{esc(item['content_version'])}）"
            "</li>"
        )
    rows.append("</ul></section>")
    return "\n".join(rows)


def _section(title: str, deals: list, as_of: datetime, highlight: set[str]) -> str:
    rows = [f"<section><h2>{esc(title)}</h2>"]
    if not deals:
        rows.append("<p>沒有項目。</p></section>")
        return "\n".join(rows)
    rows.append('<div class="cards">')
    for deal in deals:
        rows.append(_card(deal, as_of, deal["id"] in highlight))
    rows.append("</div></section>")
    return "\n".join(rows)


def _watch_section(deals: list, open_watch: list, closed_watch: list, as_of: datetime) -> str:
    rows = ['<section id="watch"><h2>觀察中</h2>']
    if not deals and not open_watch:
        rows.append("<p>沒有觀察中的項目。</p>")
    if deals:
        rows.append('<div class="cards">')
        for deal in deals:
            rows.append(_card(deal, as_of, False))
        rows.append("</div>")
    if open_watch:
        rows.append("<ul>")
        for item in open_watch:
            rows.append(f"<li>{esc(item['text'])}</li>")
        rows.append("</ul>")
    if closed_watch:
        rows.append("<h3>先前觀察，原文保留</h3><ul>")
        for item in closed_watch:
            note = f"（{item['note']}）" if item.get("note") else ""
            rows.append(f"<li>{esc(item['text'])}{esc(note)}</li>")
        rows.append("</ul>")
    rows.append("</section>")
    return "\n".join(rows)


def _excluded(catalog: dict) -> str:
    rows = ["<section><h2>有看到但未列入</h2><ul>"]
    for item in catalog.get("excluded") or []:
        rows.append(f"<li>{esc(item['item'])}：{esc(item['reason'])}</li>")
    rows.append("</ul></section>")
    return "\n".join(rows)


def _card(deal: dict, as_of: datetime, highlight: bool) -> str:
    flags = sale_flags(deal, as_of)
    classes = "card hl" if highlight else "card"
    bits = [f'<article class="{classes}">']
    bits.append(f"<h3>{esc(deal.get('vendor'))}</h3>")
    bits.append(f"<p>{esc(deal.get('name'))}</p>")
    if flags["upcoming"]:
        bits.append('<p class="badge">尚未開賣</p>')
    if flags["date_only_past"]:
        bits.append(
            f"<p class=\"badge\">end 只有日期（{esc(deal.get('end'))}），沒有時分與時區，因此仍留在清單。</p>"
        )
    rows = [
        ("業者", deal.get("vendor")),
        ("活動名稱", deal.get("name")),
        ("符合標準", "、".join(deal.get("crit") or [])),
        ("促銷購買期間", deal.get("buy")),
        ("適用出發期間", deal.get("travel")),
        ("代表航線與最低價", deal.get("route")),
        ("重點條件", deal.get("cond")),
        ("官方連結", deal.get("url")),
        ("資料來源", deal.get("src")),
        ("此筆最後查證", deal.get("last_verified_at") or "沒有單獨的查證時間"),
        ("下架判斷", _window_text(deal)),
    ]
    bits.append('<dl class="fields">')
    for label, value in rows:
        bits.append(f"<dt>{esc(label)}</dt><dd>{esc(value)}</dd>")
    bits.append("</dl>")
    for warning in deal.get("warnings") or []:
        bits.append(f'<p class="warn">{esc(warning)}</p>')
    for note in deal.get("review_notes") or []:
        bits.append(f'<p class="warn">{esc(note)}</p>')
    bits.append("</article>")
    return "\n".join(bits)


def _window_text(deal: dict) -> str:
    window = deal.get("window") or {}
    if window.get("basis") == "unresolved" or not window.get("purchase_end"):
        return "沒有單一、完整、含時區的購買結束時間，不自動下架。"
    basis = "明確記入" if window.get("basis") == "explicit" else "由購買期間原文解析，原文仍以上方為準"
    start = window.get("purchase_start") or "未填"
    return f"開始 {start}；結束 {window.get('purchase_end')}（{basis}）"


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)
