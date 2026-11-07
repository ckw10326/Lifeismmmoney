import json, html, datetime
now = datetime.datetime.now()
fname = now.strftime("promos-%Y%m%d-%H%M.html")
qtime = now.strftime("%Y-%m-%d %H:%M")
today = now.date()
data = json.load(open("latest.json"))
deals = [d for d in data["deals"] if not d.get("end") or d["end"] >= today.isoformat()]
for d in deals: d.pop("new", None)
new = [
 dict(id="nx-itf-2026", vendor="澳門航空", name="ITF 台灣國際旅展 台灣出發澳門航線促銷", crit=["② 旅展年度檔期"],
  buy="2026/10/20 – 2026/11/30（開票日）", end="2026-11-30", travel="2026/11/01 – 2027/06/30",
  route="台北／台中／高雄⇄澳門 經濟艙來回未稅 NT$2,500 起（部落客實查台北來回含稅約 6,652、高雄約 6,648）；商務艙來回未稅 13,500 起",
  cond="經濟艙含 1 件 32 公斤託運行李（飛悅經濟艙 2 件共 50 公斤）；含稅價以官網查詢為準；台北出發另收每航段 USD10 訂位服務費（旅行社通路）",
  url="https://www.travel4u.com.tw/flight/airline/campaign/NX/49/", src="山富旅遊澳門航空專案頁（已開啟）、可樂旅遊專區、吃貨瑪莉整理", new=True),
 dict(id="tr-itf-2026", vendor="酷航 Scoot", name="ITF 線上旅展", crit=["② 旅展年度檔期"],
  buy="2026/10/22 – 2026/11/12", end="2026-11-12", travel="待確認（以官網為準）",
  route="台北⇄東京、北海道（札幌）、首爾、新加坡；最低價未公布（近期參考：台北–東京單程含稅 3,799、札幌單程含稅 5,099）",
  cond="手提行李 10kg（廉航中最多）；不含託運；官方活動頁未開啟、細節待確認",
  url="https://www.flyscoot.com/zh-tw", src="吃貨瑪莉整理、搜尋摘要（官方頁未開啟）", new=True),
]
ids={d["id"] for d in deals}
deals = new + [d for d in deals if d["id"] not in {n["id"] for n in new}]
data["deals"]=deals
data["query_time_taipei"]=qtime
data["last_checked_taipei"]=qtime
data["excluded"] += [
 {"item":"ANA 全日空 ITF 線上旅展（10/21–11/11，松山–羽田，2027/2/1–6/25 出發）","reason":"來回含稅約 15,132，與平常價差不大；亮點只有日本國內線延伸免費"},
 {"item":"汶萊皇家航空 ITF 85 折起（至 11/20）","reason":"僅部落客資料、需汶萊轉機，力度一般"},
 {"item":"飛遊網列的「虎航全航線 88 折」","reason":"是 2026/8/20–8/21 APP 慶祝活動，早已結束"},
 {"item":"樂桃雙11快閃（搜尋結果）","reason":"查到的是 2025 年活動；2026 年尚未公布，列入觀察"},
]
data["pending_watch"]=["台灣虎航 ITF／雙11 促銷（截至 11/02 仍未公布；去年 11/05 尊榮虎、11/06–10 全員，單程未稅 799 起）",
 "Trip.com 雙11 旅展（2026 年尚未公布；去年 11/10–11/14，有單程 11 元、999 元機票）",
 "樂桃 雙11 快閃（2026 年尚未公布；去年 11/06 12:00–11/11，台灣出發單程未稅 1,511 起）"]
json.dump(data, open("latest.json","w"), ensure_ascii=False, indent=2)
e=html.escape
def dl(d): return None if not d.get("end") else (datetime.date.fromisoformat(d["end"])-today).days
def row(d):
    n=dl(d); tags=""
    if d.get("new"): tags+='<span class="tag new">新</span>'
    if n is not None and n<=3: tags+=f'<span class="tag urgent">剩 {n} 天</span>' if n>0 else '<span class="tag urgent">今天截止</span>'
    if d["id"]=="ez-itf-2026": tags+='<span class="tag urgent">11/04 11:00 搶 100 元機票</span>'
    cls=' class="hl"' if d.get("new") else (' class="ur"' if (n is not None and n<=3) or d["id"]=="ez-itf-2026" else "")
    return f"""<tr{cls}><td><b>{e(d['vendor'])}</b>{tags}</td><td>{e(d['name'])}</td><td>{'<br>'.join(e(c) for c in d['crit'])}</td><td>{e(d['buy'])}</td><td>{e(d['travel'])}</td><td>{e(d['route'])}</td><td>{e(d['cond'])}<div class="src">來源：{e(d['src'])}</div></td><td><a href="{e(d['url'])}" target="_blank">活動頁</a></td></tr>"""
head="<tr><th>業者</th><th>活動名稱</th><th>符合標準</th><th>促銷購買期間</th><th>適用出發期間</th><th>代表航線與最低價</th><th>重點條件</th><th>官方連結</th></tr>"
newd=[d for d in deals if d.get("new")]
old=sorted([d for d in deals if not d.get("new")], key=lambda x:x["end"] or "9999")
pend="".join(f"<li>{e(p)}</li>" for p in data["pending_watch"])
out=f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>機票重大促銷 {qtime}</title><style>
body{{font-family:-apple-system,"PingFang TC","Noto Sans TC",sans-serif;margin:0;padding:14px;background:#f5f6f8;color:#222;line-height:1.5}}
h1{{font-size:1.25em;margin:.2em 0}}h2{{font-size:1.05em;margin:1.2em 0 .4em}}
.sum{{background:#fff;border-left:5px solid #e8590c;padding:10px 12px;border-radius:6px}}
.wrap{{overflow-x:auto;background:#fff;border-radius:8px}}table{{border-collapse:collapse;min-width:980px;font-size:.88em}}
th,td{{border-bottom:1px solid #e3e3e3;padding:8px;vertical-align:top;text-align:left}}th{{background:#2b3a55;color:#fff;position:sticky;top:0}}
tr.hl td{{background:#fff4e6}}tr.ur td{{background:#ffecec}}.tag{{display:inline-block;font-size:.75em;padding:1px 6px;border-radius:10px;margin:3px 3px 0 0;color:#fff}}
.new{{background:#e8590c}}.urgent{{background:#c92a2a}}.src{{color:#888;font-size:.85em;margin-top:4px}}a{{color:#1c7ed6}}.note{{color:#666;font-size:.85em}}
</style></head><body>
<h1>✈️ 機票重大促銷提醒</h1>
<div class="sum">新發現兩個旅展檔期：<b>澳門航空</b>台灣出發澳門來回未稅 NT$2,500 起（含稅約 6,650，含 32 公斤託運，買到 11/30），以及<b>酷航線上旅展</b>（至 11/12，最低價未公布）。提醒：<b>易遊網 100 元沖繩、曼谷機票是後天 11/04（三）11:00 開搶</b>。<br><span class="note">查詢時間：{qtime}（台北時間）</span></div>
<h2>🆕 新優惠</h2><div class="wrap"><table>{head}{''.join(row(d) for d in newd)}</table></div>
<h2>📌 目前仍在進行、之前已提醒過</h2><div class="wrap"><table>{head}{''.join(row(d) for d in old)}</table></div>
<h2>👀 持續觀察中（尚未公布）</h2><ul>{pend}</ul>
<p class="note">價格多為「起」價，未稅／含稅依各家標示；限量秒殺商品不保證買得到，下單前請以官方頁面為準。標「官方頁未開啟」者資料來自新聞或部落客整理。</p>
</body></html>"""
open(fname,"w").write(out)
print(fname)
