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
  var HEADERS = ["業者", "活動名稱", "符合標準", "促銷購買期間", "適用出發期間", "代表航線與最低價", "重點條件", "官方連結"];

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

  function shortTaipei(iso) {
    if (!iso) return "";
    var parsed = new Date(iso);
    if (Number.isNaN(parsed.getTime())) return String(iso);
    var parts = new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Taipei",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    }).formatToParts(parsed);
    function get(type) {
      for (var i = 0; i < parts.length; i += 1) {
        if (parts[i].type === type) return parts[i].value;
      }
      return "";
    }
    return get("year") + "-" + get("month") + "-" + get("day") + " " + get("hour") + ":" + get("minute");
  }

  function daysLeft(deal, asOfIso) {
    if (!deal.end || !/^\d{4}-\d{2}-\d{2}$/.test(deal.end)) return null;
    var today = taipeiDate(Date.parse(asOfIso));
    var start = Date.parse(today + "T00:00:00Z");
    var end = Date.parse(deal.end + "T00:00:00Z");
    if (!Number.isFinite(start) || !Number.isFinite(end)) return null;
    return Math.round((end - start) / 86400000);
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

  function tdText(value) {
    return el("td", null, value || "");
  }

  function appendRow(tbody, deal, asOfIso, isNew) {
    var n = daysLeft(deal, asOfIso);
    var tr = document.createElement("tr");
    if (isNew) tr.className = "hl";
    else if (n !== null && n >= 0 && n <= 3) tr.className = "ur";

    var vendor = document.createElement("td");
    var name = document.createElement("b");
    name.textContent = deal.vendor || "";
    vendor.appendChild(name);
    if (isNew) vendor.appendChild(el("span", "tag new", "新"));
    if (n === 0) vendor.appendChild(el("span", "tag urgent", "今天截止"));
    else if (n !== null && n > 0 && n <= 3) vendor.appendChild(el("span", "tag urgent", "剩 " + n + " 天"));
    tr.appendChild(vendor);
    tr.appendChild(tdText(deal.name));

    var crit = document.createElement("td");
    (deal.crit || []).forEach(function (item, index) {
      if (index) crit.appendChild(document.createElement("br"));
      crit.appendChild(document.createTextNode(item));
    });
    tr.appendChild(crit);
    tr.appendChild(tdText(deal.buy));
    tr.appendChild(tdText(deal.travel));
    tr.appendChild(tdText(deal.route));

    var cond = document.createElement("td");
    cond.appendChild(document.createTextNode(deal.cond || ""));
    if (deal.src) cond.appendChild(el("div", "src", "來源：" + deal.src));
    tr.appendChild(cond);

    var linkCell = document.createElement("td");
    var href = safeHref(deal.url);
    if (href) {
      var link = el("a", null, "活動頁");
      link.href = href;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      linkCell.appendChild(link);
    } else if (deal.url) {
      linkCell.textContent = String(deal.url);
    }
    tr.appendChild(linkCell);
    tbody.appendChild(tr);
  }

  function tableFor(deals, asOfIso, isNew) {
    var wrap = el("div", "wrap");
    var table = document.createElement("table");
    var head = document.createElement("tr");
    HEADERS.forEach(function (label) {
      head.appendChild(el("th", null, label));
    });
    var thead = document.createElement("thead");
    thead.appendChild(head);
    var tbody = document.createElement("tbody");
    deals.forEach(function (deal) {
      appendRow(tbody, deal, asOfIso, isNew);
    });
    table.appendChild(thead);
    table.appendChild(tbody);
    wrap.appendChild(table);
    return wrap;
  }

  function section(title, id, deals, emptyText, asOfIso, isNew) {
    var node = el("section");
    node.id = id;
    node.appendChild(el("h2", null, title));
    if (!deals.length) node.appendChild(el("p", null, emptyText));
    else node.appendChild(tableFor(deals, asOfIso, isNew));
    return node;
  }

  function fillSummary(summary, catalog, newDeals) {
    while (summary.firstChild) summary.removeChild(summary.firstChild);
    var last = catalog.last_successful_check;
    if (newDeals.length) {
      summary.appendChild(document.createTextNode("新優惠：" + newDeals.map(function (deal) {
        return (deal.vendor || "") + " " + (deal.name || "");
      }).join("；") + "。"));
    } else {
      summary.appendChild(document.createTextNode("目前沒有尚未通知的新優惠。"));
    }
    summary.appendChild(document.createElement("br"));
    var when = last ? shortTaipei(last.checked_at) + "（台北時間）" : "尚無檢查紀錄";
    summary.appendChild(el("span", "note", "查詢時間：" + when));
  }

  function render(catalog, asOfIso, documentRef) {
    var app = documentRef.getElementById("app");
    var summary = documentRef.getElementById("summary");
    var note = documentRef.getElementById("data-note");
    while (app.firstChild) app.removeChild(app.firstChild);
    if (note) note.textContent = catalog.data_note || "";
    var byId = {};
    (catalog.deals || []).forEach(function (deal) {
      byId[deal.id] = deal;
    });
    var model = viewModel(catalog, asOfIso);
    function take(ids) {
      return ids.map(function (id) { return byId[id]; });
    }
    var fresh = take(model.sections.new);
    if (summary) fillSummary(summary, catalog, fresh);
    app.appendChild(section("🆕 新優惠", "new", fresh, "這次沒有新優惠。", asOfIso, true));
    app.appendChild(section(
      "📌 目前仍在進行、之前已提醒過",
      "current",
      take(model.sections.current),
      "目前沒有仍在清單上的舊優惠。",
      asOfIso,
      false
    ));
    var watch = el("section");
    watch.id = "watch";
    watch.appendChild(el("h2", null, "👀 持續觀察中"));
    var watchDeals = take(model.sections.watch);
    if (watchDeals.length) watch.appendChild(tableFor(watchDeals, asOfIso, false));
    var openItems = (catalog.pending_watch || []).filter(function (item) { return item.status === "open"; });
    var closedItems = (catalog.pending_watch || []).filter(function (item) { return item.status !== "open"; });
    if (!watchDeals.length && !openItems.length) watch.appendChild(el("p", null, "目前沒有觀察項目。"));
    if (openItems.length || closedItems.length) {
      var list = document.createElement("ul");
      openItems.forEach(function (item) { list.appendChild(el("li", null, item.text)); });
      closedItems.forEach(function (item) {
        list.appendChild(el("li", null, item.note ? item.text + "（" + item.note + "）" : item.text));
      });
      watch.appendChild(list);
    }
    app.appendChild(watch);
    app.appendChild(section(
      "購買期已結束（資料仍保留）",
      "ended",
      take(model.sections.ended),
      "沒有已用完整時區時間判定結束的優惠。",
      asOfIso,
      false
    ));
    var excluded = el("section");
    excluded.id = "excluded";
    excluded.appendChild(el("h2", null, "有看到但未列入"));
    var excludedList = document.createElement("ul");
    (catalog.excluded || []).forEach(function (item) {
      excludedList.appendChild(el("li", null, item.item + "：" + item.reason));
    });
    excluded.appendChild(excludedList);
    app.appendChild(excluded);
  }

  function mount(documentRef) {
    var app = documentRef.getElementById("app");
    var summary = documentRef.getElementById("summary");
    var dataUrl = catalogUrl(globalThis.location.href);
    if (summary) summary.textContent = "正在讀取資料…";
    fetch(dataUrl)
      .then(function (response) {
        if (!response.ok) throw new Error(String(response.status));
        return response.json();
      })
      .then(function (catalog) {
        render(catalog, new Date().toISOString(), documentRef);
      })
      .catch(function () {
        if (app) app.textContent = "";
        if (summary) summary.textContent = "讀不到 " + dataUrl + "。請用網站伺服器開啟這個目錄。";
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
