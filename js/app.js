(function (root, factory) {
  var api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.PromoApp = api;
  if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", function () {
      api.mount(document);
    });
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  var QUALIFIED = ["vendor", "name", "buy", "travel", "route", "cond", "url"];

  function isQualified(deal) {
    if (deal.observe) return false;
    for (var i = 0; i < QUALIFIED.length; i += 1) {
      if (!String(deal[QUALIFIED[i]] || "").trim()) return false;
    }
    return Array.isArray(deal.crit) && deal.crit.length > 0;
  }

  function taipeiDate(ms) {
    var parts = new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Taipei",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).formatToParts(new Date(ms));
    function get(type) {
      for (var i = 0; i < parts.length; i += 1) {
        if (parts[i].type === type) return parts[i].value;
      }
      return "";
    }
    return get("year") + "-" + get("month") + "-" + get("day");
  }

  function saleFlags(deal, asOfIso) {
    var asOf = Date.parse(asOfIso);
    var windowInfo = deal.window || {};
    var end = windowInfo.purchase_end ? Date.parse(windowInfo.purchase_end) : NaN;
    var start = windowInfo.purchase_start ? Date.parse(windowInfo.purchase_start) : NaN;
    var ended = Number.isFinite(end) && asOf >= end;
    var upcoming = Number.isFinite(start) && asOf < start;
    var dateOnlyPast = false;
    if (!windowInfo.purchase_end && /^\d{4}-\d{2}-\d{2}$/.test(deal.end || "")) {
      dateOnlyPast = taipeiDate(asOf) > deal.end;
    }
    return { ended: ended, upcoming: upcoming, date_only_past: dateOnlyPast };
  }

  function classify(deal, asOfIso) {
    var flags = saleFlags(deal, asOfIso);
    if (flags.ended) return "ended";
    if (!isQualified(deal)) return "watch";
    if (deal.notified_version !== deal.content_version) return "new";
    return "current";
  }

  function viewModel(catalog, asOfIso) {
    var sections = { new: [], current: [], watch: [], ended: [] };
    var flags = {};
    var deals = catalog.deals || [];
    for (var i = 0; i < deals.length; i += 1) {
      var section = classify(deals[i], asOfIso);
      sections[section].push(deals[i].id);
      flags[deals[i].id] = saleFlags(deals[i], asOfIso);
    }
    Object.keys(sections).forEach(function (key) {
      sections[key].sort();
    });
    var watches = catalog.pending_watch || [];
    return {
      sections: sections,
      flags: flags,
      open_watch: watches.filter(function (item) { return item.status === "open"; }).map(function (item) { return item.id; }).sort(),
      closed_watch: watches.filter(function (item) { return item.status !== "open"; }).map(function (item) { return item.id; }).sort(),
    };
  }

  function catalogUrl(pageHref) {
    var url = new URL(pageHref);
    if (!url.pathname.endsWith("/") && !/\/[^/]+\.[^/]+$/.test(url.pathname)) {
      url.pathname += "/";
    }
    return new URL("data/catalog.json", url).href;
  }

  function safeHref(value) {
    var text = String(value || "").trim();
    if (/^https?:\/\//i.test(text)) return text;
    return "";
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function formatWhen(iso) {
    if (!iso) return "沒有單獨的查證時間";
    var parsed = new Date(iso);
    if (Number.isNaN(parsed.getTime())) return String(iso);
    var shown = new Intl.DateTimeFormat("zh-Hant-TW", {
      timeZone: "Asia/Taipei",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    }).format(parsed);
    return shown + "（台北時間）／原始紀錄 " + iso;
  }

  function windowText(deal) {
    var windowInfo = deal.window || {};
    if (windowInfo.basis === "unresolved" || !windowInfo.purchase_end) {
      return "沒有單一、完整、含時區的購買結束時間，不自動下架。";
    }
    var basis = windowInfo.basis === "explicit"
      ? "明確記入"
      : "由購買期間原文解析，原文仍以上方為準";
    return "開始 " + (windowInfo.purchase_start || "未填") + "；結束 " + windowInfo.purchase_end + "（" + basis + "）";
  }

  function card(deal, flags) {
    var node = el("article", "card");
    node.appendChild(el("h3", null, deal.vendor || "未填業者"));
    node.appendChild(el("p", null, deal.name || ""));
    if (flags.upcoming) node.appendChild(el("p", "badge", "尚未開賣"));
    if (flags.date_only_past) {
      node.appendChild(el("p", "badge", "end 只有日期（" + (deal.end || "") + "），沒有時分與時區，因此仍留在現行清單。"));
    }
    var fields = el("dl", "fields");
    [
      ["業者", deal.vendor],
      ["活動名稱", deal.name],
      ["符合標準", (deal.crit || []).join("、")],
      ["促銷購買期間", deal.buy],
      ["適用出發期間", deal.travel],
      ["代表航線與最低價", deal.route],
      ["重點條件", deal.cond],
      ["官方連結", deal.url],
      ["資料來源", deal.src],
      ["此筆最後查證", formatWhen(deal.last_verified_at)],
      ["下架判斷", windowText(deal)],
    ].forEach(function (pair) {
      fields.appendChild(el("dt", null, pair[0]));
      var value = el("dd");
      value.textContent = pair[1] ? String(pair[1]) : "（空）";
      if (pair[0] === "官方連結" && safeHref(pair[1])) {
        value.appendChild(document.createTextNode(" "));
        var link = el("a", null, "開啟");
        link.href = safeHref(pair[1]);
        link.rel = "noopener noreferrer";
        link.target = "_blank";
        value.appendChild(link);
      }
      fields.appendChild(value);
    });
    node.appendChild(fields);
    (deal.warnings || []).concat(deal.review_notes || []).forEach(function (warning) {
      node.appendChild(el("p", "warn", warning));
    });
    return node;
  }

  function section(title, id, deals, emptyText, asOfIso) {
    var node = el("section");
    node.id = id;
    node.appendChild(el("h2", null, title));
    if (!deals.length) {
      node.appendChild(el("p", null, emptyText));
      return node;
    }
    var cards = el("div", "cards");
    deals.forEach(function (deal) {
      cards.appendChild(card(deal, saleFlags(deal, asOfIso)));
    });
    node.appendChild(cards);
    return node;
  }

  function render(catalog, asOfIso, documentRef) {
    var app = documentRef.getElementById("app");
    var checkLine = documentRef.getElementById("check-line");
    var note = documentRef.getElementById("data-note");
    while (app.firstChild) app.removeChild(app.firstChild);
    var last = catalog.last_successful_check;
    checkLine.textContent = last
      ? "最後成功查證：" + formatWhen(last.checked_at) + "。重新整理這頁不會把查證時間改成現在。"
      : "資料檔裡還沒有成功的檢查紀錄。";
    note.textContent = catalog.data_note || "";
    var byId = {};
    (catalog.deals || []).forEach(function (deal) {
      byId[deal.id] = deal;
    });
    var model = viewModel(catalog, asOfIso);
    function take(ids) {
      return ids.map(function (id) { return byId[id]; });
    }
    var criteria = el("section");
    criteria.appendChild(el("h2", null, "四條判斷標準（維持不變）"));
    var list = el("ol");
    (catalog.criteria || []).forEach(function (item) {
      list.appendChild(el("li", null, item));
    });
    criteria.appendChild(list);
    app.appendChild(criteria);
    app.appendChild(section(
      "新優惠／重大更新",
      "new",
      take(model.sections.new),
      "目前沒有尚未通知的新優惠或重大更新。打開頁面不會把舊優惠變成今天的新發現。",
      asOfIso
    ));
    app.appendChild(section(
      "目前仍有效",
      "current",
      take(model.sections.current),
      "目前沒有仍在購買期內、而且已經通知過的優惠。",
      asOfIso
    ));
    var watch = section(
      "觀察中",
      "watch",
      take(model.sections.watch),
      "沒有缺欄位或標成觀察的優惠。",
      asOfIso
    );
    var openItems = (catalog.pending_watch || []).filter(function (item) {
      return item.status === "open";
    });
    if (openItems.length) {
      var openList = el("ul");
      openItems.forEach(function (item) {
        openList.appendChild(el("li", null, item.text));
      });
      watch.appendChild(openList);
    }
    var closedItems = (catalog.pending_watch || []).filter(function (item) {
      return item.status !== "open";
    });
    if (closedItems.length) {
      watch.appendChild(el("h3", null, "先前觀察，原文保留"));
      var closedList = el("ul");
      closedItems.forEach(function (item) {
        closedList.appendChild(el("li", null, item.note ? item.text + "（" + item.note + "）" : item.text));
      });
      watch.appendChild(closedList);
    }
    app.appendChild(watch);
    app.appendChild(section(
      "購買期已結束（仍保留）",
      "ended",
      take(model.sections.ended),
      "沒有已用完整時區時間判定結束的優惠。只有日期的項目不會出現在這裡。",
      asOfIso
    ));
    var excluded = el("section");
    excluded.id = "excluded";
    excluded.appendChild(el("h2", null, "有看到但未列入"));
    var excludedList = el("ul");
    (catalog.excluded || []).forEach(function (item) {
      excludedList.appendChild(el("li", null, item.item + "：" + item.reason));
    });
    excluded.appendChild(excludedList);
    app.appendChild(excluded);
    var checks = el("section");
    checks.id = "checks";
    checks.appendChild(el("h2", null, "檢查紀錄"));
    var checkList = el("ul");
    (catalog.checks || []).forEach(function (item) {
      var line = el("li");
      line.appendChild(documentRef.createTextNode((item.summary || item.checked_at) + " "));
      if (item.snapshot_note) line.appendChild(el("span", "note", item.snapshot_note));
      if (item.snapshot_html) {
        var link = el("a", null, " 原始快照");
        link.href = item.snapshot_html;
        line.appendChild(link);
      }
      checkList.appendChild(line);
    });
    checks.appendChild(checkList);
    app.appendChild(checks);
  }

  function mount(documentRef) {
    var app = documentRef.getElementById("app");
    var checkLine = documentRef.getElementById("check-line");
    var dataUrl = catalogUrl(globalThis.location.href);
    checkLine.textContent = "正在讀取 " + dataUrl;
    fetch(dataUrl)
      .then(function (response) {
        if (!response.ok) throw new Error(String(response.status));
        return response.json();
      })
      .then(function (catalog) {
        render(catalog, new Date().toISOString(), documentRef);
      })
      .catch(function () {
        app.textContent = "";
        checkLine.textContent = "讀不到 " + dataUrl + "。請用網站伺服器開啟這個目錄（含 GitHub Pages 子路徑）；不要用檔案總管直接點開 HTML。";
      });
  }

  return {
    classify: classify,
    saleFlags: saleFlags,
    viewModel: viewModel,
    catalogUrl: catalogUrl,
    isQualified: isQualified,
    safeHref: safeHref,
    render: render,
    mount: mount,
  };
});
