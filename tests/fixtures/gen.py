import json, html, datetime
now = datetime.datetime.now()
stamp = now.strftime("%H%M")
qtime = now.strftime("%Y-%m-%d %H:%M")
today = datetime.date(2026,10,29)
deals = [
 dict(id="vietjet-10routes-202610", vendor="越捷航空 VietJet", name="慶10條新航線開通 票價 NT$0 起", crit=["④ 廉航單程未稅 ≤ NT$1,000"],
      buy="2026/10/26 01:00 – 2026/11/01 23:59（台北時間）", end="2026-11-01", travel="2026/11/01 – 2027/10/31（夏季、節假日、春節等旺季除外）",
      route="台南→河內 單程未稅 TWD 110 起（官網頁面「已看到」價）；台北/台中/高雄⇄胡志明市、河內，台北⇄富國島 NT$0 起（未稅）",
      cond="未含稅費與附加費；促銷票售罄可能提前結束；改票需付費", url="https://www.vietjetair.com/zh-tw/flight-tickets/celebrate-10-new-routes-lets-vietjet-tickets-price-from-just-1-october-26th-november-1st-2026", src="越捷官網活動頁（WebSearch 摘錄，WebFetch 逾時）"),
 dict(id="itf-2026", vendor="ITF 台灣國際旅展", name="2026 ITF 實體旅展（南港展覽館1館）", crit=["② 旅展年度檔期"],
      buy="2026/11/06（五）12:00–18:00；11/07–11/09 10:00–18:00", end="2026-11-09", travel="依各參展業者",
      route="12 家航空參展：華航、長榮、星宇、虎航、國泰、日航、樂桃、星悅、天馬、阿提哈德、太陽富國、ANA",
      cond="門票 NT$200（預售 NT$180 至 11/05）；虎航旅展票價尚未公布，可能在展期公布", url="https://www.taiwanitf.org.tw/Information3", src="ITF 官網、中央社 10/21"),
 dict(id="nz-itf-2026", vendor="紐西蘭航空", name="年度線上旅展", crit=["② 旅展年度檔期"],
      buy="至 2026/11/09", end="2026-11-09", travel="待確認（以官網為準）",
      route="台北直飛奧克蘭 經濟艙來回未稅 NT$29,500 起", cond="指定票價可免費延伸至基督城或威靈頓", url="https://supertaste.tvbs.com.tw/pack/362119", src="食尚玩家整理（官方頁未開啟，待確認）"),
 dict(id="lion-itf-2026", vendor="雄獅旅遊", name="ITF 線上旅展", crit=["② 旅遊網站年度檔期"],
      buy="2026/10/12 – 2026/11/09（每天 11:00 開搶）", end="2026-11-09", travel="2026/10/12 – 2027/12/31（依商品）",
      route="機票：週三、週六國外機票滿 5,000 折 400；週日滿 10,000 折 400；中信卡國際機票滿額折 1,000",
      cond="主力是團體／機加酒（滿 3 萬折 3,000、滿 5 萬折 5,000 限量）；純機票折扣力度小", url="https://lifegoods.cc/liontravel-itf/", src="部落客整理、CTWANT（官方頁未開啟）"),
 dict(id="sq-itf-2026", vendor="新加坡航空（含酷航航點）", name="ITF 線上旅展 最高 8 折", crit=["② 旅展年度檔期"],
      buy="至 2026/11/12（開始日待確認）", end="2026-11-12", travel="依航點不同（待確認）",
      route="台北–新加坡 來回含稅 11,088 起；峇里島 10,628 起；雪梨 25,158 起", cond="需新加坡轉機；會員萬事達卡付款可抽周杰倫演唱會票", url="https://www.businesstoday.com.tw/article/category/183031/post/202610190027/", src="今周刊、食尚玩家（官方頁未開啟）"),
 dict(id="cx-itf-2026", vendor="國泰航空", name="線上旅展 70+ 航點 8 折起", crit=["② 旅展年度檔期"],
      buy="2026/10/16 – 2026/11/13", end="2026-11-13", travel="至 2027/09/30（2027/02/03–02/07 不適用）",
      route="台北–香港 經濟艙 TWD 7,674 起；高雄–香港 來回含稅 7,450 起；台北–東京 來回含稅 13,433 起",
      cond="限台北、高雄出發；會員碼 CXITF500（亞洲每張折 500，限 2,400 張）／CXITF1000（長程滿 2 萬折 1,000，限 900 筆）", url="https://yenlabaero.com/cathay-pacific-online-travel-fair-2026", src="顏究所、今周刊（國泰官網未開啟）"),
 dict(id="jl-itf-2026", vendor="日本航空", name="東京、名古屋、沖繩 8 折起", crit=["② 旅展年度檔期"],
      buy="至 2026/11/13", end="2026-11-13", travel="至 2027/03/23",
      route="台北–沖繩 來回含稅 7,639 起；名古屋 13,144 起；東京 13,859 起", cond="經濟艙含 2 件託運行李", url="https://www.businesstoday.com.tw/article/category/183031/post/202610190027/", src="今周刊（官方頁未開啟）"),
 dict(id="cola-tk-2026", vendor="可樂旅遊 × 土耳其航空", name="土航全航線 88 折起（獨家）", crit=["② 旅遊網站年度檔期"],
      buy="2026/10/13 – 2026/11/13", end="2026-11-13", travel="至 2027/12/31",
      route="經伊斯坦堡轉機往歐洲、中東、非洲（未公布最低價）", cond="購票可抽台北–伊斯坦堡來回機票；10/17 一日加碼已結束", url="https://www.ctwant.com/article/501796/", src="CTWANT、食尚玩家"),
 dict(id="settour-itf-2026", vendor="東南旅遊", name="2026 ITF 線上旅展（每週主題）", crit=["② 旅遊網站年度檔期"],
      buy="2026/10/08 – 2026/11/13（待確認）", end="2026-11-13", travel="待確認",
      route="港澳、日韓機票現折 399（待確認）；機加酒滿 3 萬折 1,500", cond="官方頁擋爬（403），內容來自搜尋摘要，待確認", url="https://www.settour.com.tw/act/mkt/itf_online/fit.html", src="搜尋摘要（官網 403）"),
 dict(id="br-itf-2026", vendor="長榮航空", name="ITF 線上旅展 精選航線 82 折起", crit=["② 旅展年度檔期"],
      buy="2026/10/21 – 2026/11/15 23:59", end="2026-11-15", travel="2026/10/21 – 2027/06/30（依航線）",
      route="桃園–香港 單程未稅 3,280 起；桃園–沖繩 單程未稅 6,640 起；松山–羽田 11,305 起",
      cond="限官網／App、台灣出發；不可與聯名卡官網優惠併用；購票抽商務艙機票", url="https://promotion.evaair.com/tw/online-travel-fair/index.html", src="中央社、自由時報（長榮官網擋爬）"),
 dict(id="ci-itf-2026", vendor="中華航空", name="ITF 線上旅展 精選航線 76 折起", crit=["② 旅展年度檔期"],
      buy="2026/10/16 – 2026/11/21 23:59", end="2026-11-21", travel="依航線，多為 2026/10/16 – 2027/06 下旬（春節前後排除）",
      route="香港 未稅 3,240 起；宿霧 未稅 3,354 起；釜山／沖繩 未稅 5,994 起；雪梨 單程未稅 16,188 起",
      cond="未稅價；華夏會員購票登錄抽獎（最高 6 張區域線商務艙）", url="https://2026itf.china-airlines.com/", src="華航 ITF 官網、優惠說明 PDF、中央社"),
 dict(id="jx-itf-2026", vendor="星宇航空", name="ITF 線上旅展 精選航線 85 折起", crit=["② 旅展年度檔期", "① 航空公司大促（官方稱全航線）"],
      buy="2026/10/15 – 2026/11/23", end="2026-11-23", travel="2026/10/22 起，依航線（最長至 2027/06/30，春節不適用）",
      route="台北–宿霧 來回含稅 8,105 起；熊本 10,679 起；富國島 11,107 起；神戶 12,334 起",
      cond="台北、台中、高雄出發；玉山聯名卡碼已於 10/19 結束；受油價影響甜價不多", url="https://latestnews.starlux-airlines.com/zh-TW/about-us/travel-advisories/advisories/latest-news/2026_ITF_promotion", src="星宇官網公告（已開啟）"),
 dict(id="ez-itf-2026", vendor="易遊網 ezTravel", name="ITF 線上旅展「全民普發 折扣放大節」", crit=["② 旅遊網站年度檔期"],
      buy="進行中（截止日待確認）", end=None, travel="待確認",
      route="宣稱狂撒 300 萬折扣碼、5 折券；機票碼如 flight300（週三 App 滿 6,000 折 300）、26hsbcitf（滙豐卡 App 滿 6,000 折 800，10/28–11/11，廉航不適用）",
      cond="官方活動頁未列日期與機票細節，待確認", url="https://promo.eztravel.com.tw/uglyrabbit-37368", src="易遊網活動頁（已開啟）、滙豐活動頁摘要"),
]
def days_left(d):
    if not d: return None
    return (datetime.date.fromisoformat(d)-today).days
deals.sort(key=lambda x: x["end"] or "9999")
excluded = [
 ("亞洲航空 全航線 7–8 折起","已於 10/25 截止（清邁單程含稅 3,939 起，曾符合標準②①）"),
 ("亞洲航空 DRAGONSWIN 折 NT$500（10/27–11/1）","單筆滿 6,000 才折 500，約 8%，力度不足"),
 ("樂桃 國際線優惠（10/14–10/17）","已結束；最低沖繩單程未稅 1,280，也未達 ≤1,000"),
 ("台灣虎航 樂虎卡 999 起快閃（10/14–10/15）","已結束，且限樂虎卡持卡人；ITF 促銷尚未公布"),
 ("台灣虎航 × AFTEE 85 折（至 10/31）","支付工具優惠，舊用戶上限只折 NT$100"),
 ("LINE 旅遊年度旅展（虎航 3%、華航 1% 點數回饋）","只有點數回饋，非票價折扣"),
 ("華航「雙十一」84 折","僅限中國大陸出發飛台灣，不適用台灣出發"),
 ("燦星旅遊 線上旅展（10/16–11/9）","機票只有 1% 星旅券，主力是團體行程"),
 ("Trip.com 11 月機票優惠頁、LINE Bank 85 折碼","常態比價頁／小額優惠碼，無明確大型檔期"),
 ("捷星、酷航","官網未見台灣出發促銷；捷星桃園–大阪來回約 7,584 屬一般價"),
]
blocked = [("長榮航空 flights.evaair.com","Access Denied（擋爬），改用中央社／自由時報"),
 ("東南旅遊 settour.com.tw","403 Forbidden"),
 ("越捷官網活動頁","WebFetch 逾時，改用搜尋摘錄"),
 ("國泰、日航、新航、紐航、雄獅、可樂官網","未直接開啟，資訊來自新聞與部落客整理（已標註來源）"),
 ("標準③（比平常便宜 30%）","本次找不到可靠的歷史均價依據，沒有項目以此標準列入")]
E=html.escape
rows=""
for d in deals:
    dl=days_left(d["end"]); urgent = dl is not None and dl<=3
    badge = f'<span class="badge red">剩 {dl} 天截止</span>' if urgent else (f'<span class="badge">剩 {dl} 天</span>' if dl is not None else '<span class="badge gray">截止日待確認</span>')
    crit="".join(f'<span class="tag">{E(c)}</span>' for c in d["crit"])
    rows+=f'''<tr class="{'urgent' if urgent else ''}">
<td data-l="業者"><b>{E(d["vendor"])}</b></td>
<td data-l="活動名稱">{E(d["name"])}<br>{badge}</td>
<td data-l="符合標準">{crit}</td>
<td data-l="購買期間">{E(d["buy"])}</td>
<td data-l="出發期間">{E(d["travel"])}</td>
<td data-l="代表航線／最低價">{E(d["route"])}</td>
<td data-l="重點條件">{E(d["cond"])}<div class="src">來源：{E(d["src"])}</div></td>
<td data-l="官方連結"><a href="{E(d["url"])}" target="_blank" rel="noopener">開啟</a></td></tr>'''
exc="".join(f"<li><b>{E(a)}</b>：{E(b)}</li>" for a,b in excluded)
blk="".join(f"<li><b>{E(a)}</b>：{E(b)}</li>" for a,b in blocked)
n=len(deals); nurg=sum(1 for d in deals if (days_left(d["end"]) or 99)<=3)
page=f'''<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>機票重大促銷比對 {qtime}</title><style>
body{{font-family:-apple-system,"PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif;margin:0;background:#f4f6fa;color:#1f2937;line-height:1.55}}
.wrap{{max-width:1200px;margin:auto;padding:16px}}
header{{background:linear-gradient(135deg,#1e3a8a,#2563eb);color:#fff;border-radius:14px;padding:18px 20px}}
header h1{{margin:0 0 6px;font-size:1.4rem}} header p{{margin:4px 0;opacity:.95}}
.cards{{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}}
.card{{flex:1;min-width:150px;background:#fff;border-radius:12px;padding:12px 14px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
.card .n{{font-size:1.6rem;font-weight:700;color:#1d4ed8}} .card.red .n{{color:#dc2626}}
.alert{{background:#fef2f2;border-left:5px solid #dc2626;padding:10px 14px;border-radius:8px;margin:10px 0}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08);font-size:.92rem}}
th{{background:#1e3a8a;color:#fff;text-align:left;padding:10px;white-space:nowrap}}
td{{padding:10px;border-bottom:1px solid #e5e7eb;vertical-align:top}}
tr.urgent td{{background:#fff1f2}}
.badge{{display:inline-block;margin-top:4px;padding:2px 8px;border-radius:999px;background:#dbeafe;color:#1e40af;font-size:.78rem}}
.badge.red{{background:#dc2626;color:#fff;font-weight:700}} .badge.gray{{background:#e5e7eb;color:#374151}}
.tag{{display:inline-block;margin:2px 2px 2px 0;padding:2px 8px;border-radius:6px;background:#ecfdf5;color:#065f46;font-size:.8rem}}
.src{{color:#6b7280;font-size:.78rem;margin-top:4px}} a{{color:#2563eb;font-weight:600}}
section{{background:#fff;border-radius:12px;padding:14px 18px;margin-top:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
section h2{{font-size:1.05rem;margin:0 0 8px}} section li{{margin:4px 0;font-size:.9rem}}
footer{{color:#6b7280;font-size:.8rem;margin:16px 4px}}
@media(max-width:760px){{table,thead,tbody,tr,td{{display:block}} thead{{display:none}}
tr{{margin-bottom:12px;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.1);background:#fff;overflow:hidden}}
td{{border:none;border-bottom:1px solid #f1f5f9}} td::before{{content:attr(data-l);display:block;font-size:.75rem;color:#6b7280;font-weight:600}}}}
</style></head><body><div class="wrap">
<header><h1>✈️ 機票重大促銷比對</h1><p>查詢時間：{qtime}（台北時間）</p>
<p>本次共 <b>{n}</b> 筆符合標準；目前正值 ITF 台灣國際旅展（11/6–11/9）檔期，大多數航空與旅行社的線上旅展都在 11/9–11/23 之間截止。</p></header>
<div class="cards"><div class="card"><div class="n">{n}</div>符合標準的優惠</div>
<div class="card red"><div class="n">{nurg}</div>3 天內截止</div>
<div class="card"><div class="n">{len(excluded)}</div>看到但排除</div></div>
<div class="alert">⏰ <b>最急：</b>越捷航空 NT$0 起（未稅）促銷 <b>11/1（日）23:59</b> 截止，台北／台中／高雄／台南往越南。<br>👀 <b>待觀察：</b>台灣虎航 ITF 促銷尚未公布，可能在旅展期間（11/6–11/9）推出。</div>
<table><thead><tr><th>業者</th><th>活動名稱</th><th>符合標準</th><th>促銷購買期間</th><th>適用出發期間</th><th>代表航線與最低價</th><th>重點條件</th><th>官方連結</th></tr></thead><tbody>{rows}</tbody></table>
<section><h2>🚫 有看到但不符合標準而排除</h2><ul>{exc}</ul>
<p style="font-size:.85rem;color:#6b7280">如果覺得太嚴或太鬆，可以告訴我調整標準，例如把「已結束」的也列出來當參考，或把旅行社的小額折扣碼排除掉。</p></section>
<section><h2>⚠️ 查不到或擋爬的網站</h2><ul>{blk}</ul></section>
<footer>價格皆為業者公告的「起」價，實際以訂票頁為準；「未稅」價需另加稅金與燃油附加費。標示「待確認」者未能在官方頁面核實。</footer>
</div></body></html>'''
path=f"/workspace/flight-promos/promos-20261029-{stamp}.html"
open(path,"w",encoding="utf-8").write(page)
json.dump({"query_time_taipei":qtime,"criteria":["航空公司全航線大促","旅展或旅遊網站年度檔期","比平常便宜30%以上","廉航單程未稅NT$1000以下"],
 "deals":[{k:d[k] for k in ("id","vendor","name","crit","buy","end","travel","route","cond","url","src")} for d in deals],
 "excluded":[{"item":a,"reason":b} for a,b in excluded],"pending_watch":["台灣虎航 ITF 促銷（尚未公布）"]},
 open("/workspace/flight-promos/latest.json","w",encoding="utf-8"),ensure_ascii=False,indent=2)
print(path,n,nurg)
