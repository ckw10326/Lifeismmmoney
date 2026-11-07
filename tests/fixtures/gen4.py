import json, html, datetime
now = datetime.datetime.now()
fname = now.strftime("promos-%Y%m%d-%H%M.html")
qtime = now.strftime("%Y-%m-%d %H:%M")
today = now.date()
data = json.load(open("latest.json"))
deals = [d for d in data["deals"] if not d.get("end") or d["end"] >= today.isoformat()]
for d in deals: d.pop("new", None)
new = [
 dict(id="it-itf-2026", vendor="台灣虎航", name="2026 ITF 線上旅展 全航線單程未稅 999 元起", crit=["① 航空公司全航線大促","② 旅展年度檔期","④ 廉航單程未稅 ≤ NT$1,000"],
  buy="2026/11/06（五）10:00 – 2026/11/09（一）23:59", end="2026-11-09", travel="2026/11/06 – 2027/10/30（部分航班至 2027/03/27）",
  route="台北／台中–沖繩、台北–石垣島 單程未稅 999 起；仁川、濟州 1,199 起；釜山 1,399 起；大阪、福岡 1,799 起；東京成田／羽田、名古屋 1,899 起；札幌 2,299 起；峴港 1,799 起",
  cond="單程未稅、不含託運行李；優惠碼 IT700CJU（濟州再折 700）、IT500PUS（釜山再折 500），限來回、旅遊期至 2027/06/30；旅展攤位 J709 出示行程單送桌曆",
  url="https://static.tigerairtw.com/www/events/2611ITF/", src="虎航官網新聞稿 11/02、NOWnews、聯合新聞網", new=True),
 dict(id="ak-itf-2026", vendor="亞洲航空 AirAsia", name="ITF 線上旅展冬季促銷", crit=["② 旅展年度檔期"],
  buy="即日起 – 2026/11/08", end="2026-11-08", travel="2026/11/09 – 2027/02/06",
  route="高雄–馬尼拉 單程含稅 2,290 起；台北–馬尼拉 2,410；高雄–曼谷 2,473；台北–亞庇 2,806、曼谷 2,900；台北–福岡 4,715、大阪 4,821",
  cond="單程含稅價；限量；MOVE App 訂指定航班可免一次改期手續費（需補差價）；日本線價格偏一般",
  url="https://www.airasia.com/zh/tw", src="AirAsia 新聞稿（Public 平台）、PChome、理財周刊；官方活動頁未開啟", new=True),
]
ids={d["id"] for d in deals}
deals = new + [d for d in deals if d["id"] not in {n["id"] for n in new}]
data["deals"]=deals
data["query_time_taipei"]=qtime
data["last_checked_taipei"]=qtime
data["excluded"] += [
 {"item":"台灣虎航 2027 夏季航班第二波（11/03 10:00–11/04 23:59，1,599 起）","reason":"精選航線、最低 1,599 未達 ≤1,000，非全航線"},
 {"item":"Trip.com 雙11 代碼 1111FLIGHT／1111ASIA（滿額折 500／滿萬折 1,111）","reason":"僅部落客列出、官方頁未見正式檔期，折扣幅度小"},
 {"item":"Trinity Airways 直播特價（11/02–11/06）","reason":"韓國出發、韓國信用卡加碼，非台灣出發"},
 {"item":"香港航空 周二激賞飛（11/03）","reason":"香港出發，不適用台灣出發"},
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
    if d["id"]=="ez-itf-2026": tags+='<span class="tag urgent">明天 11/04 11:00 搶 100 元機票</span>'
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
<div class="sum"><b>台灣虎航 ITF 線上旅展</b>確定 11/06（五）10:00 開賣到 11/09，全航線單程未稅 999 元起（沖繩、石垣島 999；首爾、濟州 1,199），符合破盤價標準；另有 <b>AirAsia 旅展冬季促銷</b>買到 11/08，馬尼拉單程含稅 2,290 起。提醒：<b>易遊網 100 元沖繩、曼谷機票是明天 11/04（三）11:00 開搶</b>。<br><span class="note">查詢時間：{qtime}（台北時間）</span></div>
<h2>🆕 新優惠</h2><div class="wrap"><table>{head}{''.join(row(d) for d in newd)}</table></div>
<h2>📌 目前仍在進行、之前已提醒過</h2><div class="wrap"><table>{head}{''.join(row(d) for d in old)}</table></div>
<h2>👀 持續觀察中（尚未公布）</h2><ul>{pend}</ul>
<p class="note">價格多為「起」價，未稅／含稅依各家標示；限量秒殺商品不保證買得到，下單前請以官方頁面為準。標「官方頁未開啟」者資料來自新聞或部落客整理。</p>
</body></html>"""
open(fname,"w").write(out)
print(fname)
