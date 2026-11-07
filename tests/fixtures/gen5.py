import json, html, datetime
now = datetime.datetime.now()
fname = now.strftime("promos-%Y%m%d-%H%M.html")
qtime = now.strftime("%Y-%m-%d %H:%M")
today = now.date()
data = json.load(open("latest.json"))
deals = [d for d in data["deals"] if not d.get("end") or d["end"] >= today.isoformat()]
for d in deals: d.pop("new", None)
new = [
 dict(id="ze-itf-2026", vendor="易斯達航空 Eastar Jet", name="2026 線上旅展限定 韓國航線單程未稅 550 元起", crit=["② 旅展年度檔期","④ 廉航單程未稅 ≤ NT$1,000"],
  buy="2026/11/04（三）09:00 – 2026/11/10（二）23:00", end="2026-11-10", travel="2026/11/05 – 2027/10/31",
  route="桃園–清州 單程未稅 550 起；松山–金浦、桃園–仁川、桃園–釜山 750 起；桃園–濟州 1,050 起",
  cond="單程未稅（另加稅金、燃油費）；須先登入易斯達官網會員才能購票；限量；託運行李規定以官網為準；11/06–11/07 旅展現場攤位有抽獎",
  url="https://main.eastarjet.com/?lang=tw", src="易斯達航空新聞稿（旅奇傳媒、七逗旅遊網、Yahoo 11/04）、NOWnews；官網有防爬驗證未能開啟活動頁", new=True),
]
ids={d["id"] for d in deals}
deals = new + [d for d in deals if d["id"] not in {n["id"] for n in new}]
data["deals"]=deals
data["query_time_taipei"]=qtime
data["last_checked_taipei"]=qtime
data["excluded"] += [
 {"item":"日本航空 ITF 實體旅展限定 台北–沖繩經濟艙 3,200 起（11/06–11/09 現場）","reason":"非廉航，且未說明單程／來回與含稅與否，待旅展公布細節"},
 {"item":"ANA × 樂桃 ITF 實體旅展 台日航線未稅 7,000 起","reason":"屬一般價位"},
 {"item":"太陽富國航空 ITF 每人最高折 600","reason":"折扣幅度小"},
 {"item":"Trip.com 越捷 東南亞度假優惠（台北–胡志明來回 4,623 起）","reason":"常態比價頁，非大型檔期"},
]
data["pending_watch"]=["Trip.com 雙11 旅展（2026 年官方檔期尚未公布；去年 11/10–11/14，有單程 11 元、999 元機票）",
 "樂桃 雙11 快閃（2026 年尚未公布；去年 11/06 12:00–11/11，台灣出發單程未稅 1,511 起）"]
json.dump(data, open("latest.json","w"), ensure_ascii=False, indent=2)
e=html.escape
def dl(d): return None if not d.get("end") else (datetime.date.fromisoformat(d["end"])-today).days
def row(d):
    n=dl(d); tags=""
    if d.get("new"): tags+='<span class="tag new">新</span>'
    if n is not None and n<=3: tags+=f'<span class="tag urgent">剩 {n} 天</span>' if n>0 else '<span class="tag urgent">今天截止</span>'
    cls=' class="hl"' if d.get("new") else (' class="ur"' if (n is not None and n<=3) else "")
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
<div class="sum"><b>易斯達航空（Eastar Jet）線上旅展</b>今天 11/04 09:00 已開賣到 11/10 23:00，韓國線單程未稅 550 元起（桃園–清州 550；金浦、仁川、釜山 750；濟州 1,050），出發可到 2027/10/31，要先登入官網會員才能買。提醒：<b>台灣虎航全航線 999 起是後天 11/06（五）10:00 開賣</b>。<br><span class="note">查詢時間：{qtime}（台北時間）</span></div>
<h2>🆕 新優惠</h2><div class="wrap"><table>{head}{''.join(row(d) for d in newd)}</table></div>
<h2>📌 目前仍在進行、之前已提醒過</h2><div class="wrap"><table>{head}{''.join(row(d) for d in old)}</table></div>
<h2>👀 持續觀察中（尚未公布）</h2><ul>{pend}</ul>
<p class="note">價格多為「起」價，未稅／含稅依各家標示；限量秒殺商品不保證買得到，下單前請以官方頁面為準。標「官方頁未開啟」者資料來自新聞或部落客整理。</p>
</body></html>"""
open(fname,"w").write(out)
print(fname)
