# Life is money 旅遊重大優惠

靜態網站。瀏覽器讀取 `data/catalog.json`，沒有資料庫，也沒有另一台伺服器。

固定網址（**尚未啟用**，現在打不開）：<https://ckw10326.github.io/Lifeismmmoney/>

這次只交出模板、合併工具、歷史資料與測試。沒有 merge、沒有改儲存庫可見性、沒有啟用 GitHub Pages、沒有把任何憑證寫進檔案。合併這個 PR 也不等於正式上線。

## 誰做什麼

| 角色 | 做什麼 | 不做什麼 |
| --- | --- | --- |
| 這次的模板 | `index.html`、`css/site.css`、`js/app.js`、`tools/daily.py`、測試、把附件整理進 `data/catalog.json` | 不查今天的票價、不發通知、不排程、不上線 |
| 旅遊活動優惠 bot | 每日中午查詢、寫增量 JSON、執行下面的指令、`git commit` / `git push`、依 outbox 自己發通知；獲准後才啟用 Pages | 不要為了改 JSON 再叫另一個 coding agent；不要改 HTML/CSS/JS；不要執行舊的 `gen.py`～`gen5.py` |

每日查詢仍是台北時間中午。四條標準不要改：

1. 航空公司全航線大促
2. 旅展或旅遊網站年度檔期
3. 比平常便宜30%以上
4. 廉航單程未稅NT$1000以下

## 旅遊活動優惠 bot 的最短日常步驟

在儲存庫根目錄：

```bash
python3 tools/daily.py apply inbox/2026-11-08.json
```

看 stdout 的 `status` 和 `notify`。

- `status` 是 `duplicate`：這次查證時間已經寫過，不要再 commit。
- `notify` 是 `false`：只把 `data/catalog.json` 提交並推上 GitHub。不要產生 HTML，不要發通知。
- `notify` 是 `true`：一併提交 `data/catalog.json`、`data/outbox/` 裡的新檔、`snapshots/` 裡的新檔。由 bot 讀 outbox 發通知。這個工具不會發。

通知真的送出之後：

```bash
python3 tools/daily.py ack inbox/ack.json
git add data/catalog.json
git commit -m "記錄已通知的內容版本"
git push
```

`ack.json` 只放 outbox 裡的 `id` 與 `content_version`。版本不符會整份拒絕，避免把舊通知記成已涵蓋新內容。

驗證資料檔：

```bash
python3 tools/daily.py validate
python3 -m unittest discover -s tests -q
```

## 增量 JSON

每天只放**新增或有變動**的優惠，不要把舊清單整份重貼。欄位說明：

| 欄位 | 必填 | 意思 |
| --- | --- | --- |
| `checked_at` | 是 | 這次成功查完的時間，要帶時區，例如 `2026-11-08T12:00:00+08:00`。這就是頁面上的查證時間。 |
| `summary` | 否 | 寫進檢查紀錄的原文。 |
| `upserts` | 否 | 新優惠，或某一筆有改到的欄位。沒寫到的舊欄位會保留。 |
| `verify_ids` | 否 | 這次有打開看過、但內容沒變的 id。只有這些 id 的「最後查證」會改成今天。 |
| `excluded_add` | 否 | 新的排除項：`item`、`reason`。相同項目與理由不會重複。 |
| `pending_watch` | 否 | 觀察句。`status` 為 `open` 或 `closed`。關閉不會刪掉原文。 |
| `ack_notified` | 否 | 已送出的 `{id, content_version}`。不要在同一份檔案裡 ack 剛剛才發現的新版本。 |

`upserts` 一筆的欄位：

| 欄位 | 說明 |
| --- | --- |
| `id` | 穩定 id，小寫英數與連字號。同一檔期不要改 id。 |
| `vendor` `name` `crit` `buy` `travel` `route` `cond` `url` | 原來的八欄。`crit` 是字串陣列。八欄缺任一欄就進「觀察中」，不進通知候選。 |
| `src` | 資料來源原文。 |
| `end` | 只有 `YYYY-MM-DD` 或 `null`。**不會**用來下架。 |
| `purchase_start` `purchase_end` | 選用。必須是帶時區的完整時間，例如 `2026-11-13T00:00:00+08:00`。缺時區會直接拒絕。 |

內容版本只看八欄、`src`、`end` 和上面兩個明確時間。`new`、`days_left`、`query_time`、`alerted_update`、倒數都不會造成更新。

下架規則：

- 有 `purchase_end`，而且檢視時間 `>=` 該瞬間，才離開「新優惠／目前仍有效」。資料仍留在「購買期已結束」。
- `2026-11-13T00:00:00+08:00` 與 `2026-11-12T16:00:00Z` 是同一瞬間。
- 來源若只寫到分鐘，例如 `23:59`，結束瞬間就是該分鐘的 00 秒，不會自行延伸到 59 秒。
- 只有日期、有鐘點但沒寫時區、或同一段文字出現兩個時區：不自動下架，並留下警告。原文不改。
- `purchase_start` 還沒到：仍顯示，並標「尚未開賣」。

沒有新的合格優惠、也沒有重大內容變更時，只追加一筆檢查紀錄。11/01、11/05 沒有 HTML，10/27 沒有紀錄；這些都沒有補造。

介面範例在 `examples/no-change-delta.json`、`examples/daily-delta.json`、`examples/ack.json`。`examples/daily-delta.json` 是假資料，不要套進正式的 `data/catalog.json`。

## 頁面怎麼讀資料

`index.html`、`css/site.css`、`js/app.js` 是固定檔。`js/app.js` 用目前頁面的網址去找同層的 `data/catalog.json`，所以這三種網址都可以：

- `https://ckw10326.github.io/Lifeismmmoney/`
- `https://ckw10326.github.io/Lifeismmmoney/index.html`
- 本地的 `http://127.0.0.1:埠/Lifeismmmoney/`

頁首的「最後成功查證」來自資料檔，不是打開頁面的時間。每一筆另外顯示自己的來源與最後查證時間。文字用 DOM 的 text 寫入，連結只允許 `http` / `https`。

手機是直向卡片，沒有 980px 寬表。已結束、排除與舊觀察句都留在頁面上。

## 一次設定與還沒做的上線步驟

這份分支現在**沒有部署**。Pages API 回應 404，代表站點還沒建立。

獲准上線時，由旅遊活動優惠 bot 或儲存庫擁有者做，不要由日常查優惠的流程順便做：

1. Merge 本 PR。合併本身仍不會把站公開，除非接著做第 2 步。
2. 打開 GitHub → 這個儲存庫 → Settings → Pages。
3. Build and deployment 選 **Deploy from a branch**。
4. Branch 選 `main`，資料夾選 `/ (root)`，儲存。
5. 等它給出 <https://ckw10326.github.io/Lifeismmmoney/>。根目錄已有 `.nojekyll`，Jekyll 不會吃掉 JSON。
6. 之後每天 `git push` 到 `main` 就會更新網站，不必再改模板。

`examples/pages-workflow.example.yml` 只是備援草稿，而且只寫了手動觸發。不要在獲准之前把它放進 `.github/workflows/`。

不要把 personal access token、deploy key、密碼或 `.env` 放進這個儲存庫。遠端網址裡若出現 token，只留在本機設定，不要寫進檔案。

## 歷史資料怎麼來的

`data/catalog.json` 由 `tools/import_historical.py` 從 `tests/fixtures/` 的離線附件整理而成。附件不是這次重新查證的結果。

- 檢查紀錄是 `check-log.txt` 的原文，共 10 筆，從 2026-10-29 到 2026-11-07。
- `snapshots/promos-20261104-1218.html` 與 `snapshots/promos-20261107-1225.html` 是附件原件。
- 星期與 `end` 欄若和購買期間原文不合，只出現警告。越捷雙日檔的「11/10（一）」等句子沒有改。
- 只有越捷「10 條新航線」同時寫了鐘點和單一的「台北時間」，所以它有下架時間。其餘附件優惠多數沒有單一完整時區，目前仍留在現行清單。

舊的 `gen.py`～`gen5.py` 只放在 `tests/fixtures/` 供離線還原，不是每日入口。
