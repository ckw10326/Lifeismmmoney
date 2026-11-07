import json, html, datetime
now = datetime.datetime.now()
fname = now.strftime("promos-%Y%m%d-%H%M.html")
qtime = now.strftime("%Y-%m-%d %H:%M")
today = now.date()
data = json.load(open("latest.json"))
deals = data["deals"]
# update ezTravel item (major change)
for d in deals:
    if d["id"]=="ez-itf-2026":
        d.update(dict(
          name="ITF 線上旅展「超心動$100貨公司」（與小心臟聯名）",
          crit=["② 旅遊網站年度檔期","④ 破盤價：100 元機票、雙11 單程 1,111 元一口價"],
          buy="2026/10/28 – 2026/11/11；100 元機票平日 11:00 限量搶（10/28 北海道、首爾已搶過；11/04 沖繩、曼谷）；11/11 13:00 雙11 大阪、釜山單程 1,111 元",
          end="2026-11-11",
          travel="依各限量商品頁公告（航空公司、航班、出發日未公布）",
          route="沖繩、曼谷機票 100 元（11/04 11:00）；大阪、釜山單程一口價 1,111 元（11/11 13:00）；另有航空公司旅展票最低 75 折起，如越洋航空台北–沖繩來回含稅 7,066 起、星宇宿霧 8,071 起、長榮胡志明市 9,355 起、華航曼谷 9,688 起",
          cond="全部限量秒殺，指定航班；是否含稅、含行李未公布；10/28、11/04 10:00 另可搶全站最高現折 1,000 元折扣碼；滙豐卡碼 26hsbcitf（App 滿 6,000 折 800，至 11/11，廉航不適用）",
          url="https://www.eztravel.com.tw/activity/ITF/promo/",
          src="TVBS、聯合新聞網、工商時報、三立、窩客島 10/27–10/28 報導（易遊網新聞稿）；官方頁擋爬未能開啟",
          new=True))
deals = [d for d in deals if not d.get("end") or d["end"] >= today.isoformat()]
data["deals"]=deals
data["query_time_taipei"]=qtime
data["pending_watch"]=["台灣虎航 ITF／雙11 促銷（截至 10/31 仍未公布；去年 11/05 尊榮虎、11/06–10 全員，單程未稅 799 起）","Trip.com 雙11 旅展（2026 年尚未公布）"]
data["excluded"].append({"item":"越捷 慶10條新航線 NT$0 起","reason":"11/01 23:59 截止（之前已提醒，明天最後一天）"}) if False else None
json.dump(data, open("latest.json","w"), ensure_ascii=False, indent=2)

e=html.escape
def dl(d):
    return None if not d.get("end") else (datetime.date.fromisoformat(d["end"])-today).days
def row(d):
    n=dl(d); tags=""
    if d.get("new"): tags+='<span class="tag new">新／重大更新</span>'
    if n is not None and n<=3: tags+=f'<span class="tag urgent">剩 {n} 天</span>' if n>0 else '<span class="tag urgent">今天截止</span>'
    cls=' class="hl"' if d.get("new") else (' class="ur"' if (n is not None and n<=3) else "")
    return f"""<tr{cls}><td><b>{e(d['vendor'])}</b>{tags}</td><td>{e(d['name'])}</td><td>{'<br>'.join(e(c) for c in d['crit'])}</td><td>{e(d['buy'])}</td><td>{e(d['travel'])}</td><td>{e(d['route'])}</td><td>{e(d['cond'])}<div class="src">來源：{e(d['src'])}</div></td><td><a href="{e(d['url'])}" target="_blank">活動頁</a></td></tr>"""
head="<tr><th>業者</th><th>活動名稱</th><th>符合標準</th><th>促銷購買期間</th><th>適用出發期間</th><th>代表航線與最低價</th><th>重點條件</th><th>官方連結</th></tr>"
newd=[d for d in deals if d.get("new")]
old=[d for d in deals if not d.get("new")]
old.sort(key=lambda x:x["end"] or "9999")
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
<div class="sum">這次的新消息是<b>易遊網線上旅展</b>：11/04（三）上午 11:00 限量搶<b>沖繩、曼谷 100 元機票</b>，11/11 下午 1:00 再搶<b>大阪、釜山單程 1,111 元</b>一口價（都是秒殺，要先設鬧鐘）。另外越捷 NT$0 起促銷<b>明天 11/01 截止</b>。<br><span class="note">查詢時間：{qtime}（台北時間）</span></div>
<h2>🆕 新優惠／重大更新</h2><div class="wrap"><table>{head}{''.join(row(d) for d in newd)}</table></div>
<h2>📌 目前仍在進行、之前已提醒過</h2><div class="wrap"><table>{head}{''.join(row(d) for d in old)}</table></div>
<h2>👀 持續觀察中（尚未公布）</h2><ul>{pend}</ul>
<p class="note">價格多為「起」價，未稅／含稅依各家標示；限量秒殺商品不保證買得到，下單前請以官方頁面為準。標「官方頁未開啟」者資料來自新聞報導。</p>
</body></html>"""
open(fname,"w").write(out)
print(fname)
