import json
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from import_historical import build_catalog, parse_check_log  # noqa: E402
from promo_lib import (  # noqa: E402
    CRITERIA,
    PromoError,
    apply_delta,
    content_version,
    content_payload,
    dump_catalog,
    empty_catalog,
    load_catalog,
    make_record,
    parse_aware,
    validate_catalog,
    view_model,
)
from snapshot_html import render  # noqa: E402


def deal(**overrides):
    base = {
        "id": "sample-deal",
        "vendor": "範例航空",
        "name": "範例活動",
        "crit": ["② 旅展年度檔期"],
        "buy": "2026/11/10（一）01:00 – 2026/11/13（三）00:00（台北時間）",
        "end": None,
        "travel": "2026/12/01 – 2027/01/31",
        "route": "台北–東京 未稅 0 元起",
        "cond": "限官網",
        "url": "https://example.com/deal",
        "src": "測試來源",
    }
    base.update(overrides)
    return base


def seed(raw, verified="2026-11-01T12:00:00+08:00", notified=True):
    catalog = empty_catalog()
    catalog["deals"] = [make_record(raw, first_seen_at=verified, last_verified_at=verified, notified=notified)]
    return load_catalog(dump_catalog(catalog))


class HistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog((ROOT / "data/catalog.json").read_text(encoding="utf-8"))
        cls.rebuilt = load_catalog(dump_catalog(build_catalog(ROOT / "tests/fixtures")))

    def test_committed_catalog_matches_offline_fixtures(self):
        self.assertEqual(dump_catalog(self.rebuilt), dump_catalog(self.catalog))
        self.assertEqual(validate_catalog(self.catalog), [])

    def test_criteria_unchanged(self):
        self.assertEqual(self.catalog["criteria"], CRITERIA)

    def test_missing_days_are_not_invented(self):
        stamps = [item["checked_at"] for item in self.catalog["checks"]]
        self.assertFalse(any(item.startswith("2026-10-27") for item in stamps))
        log_lines = [row[1] for row in parse_check_log(ROOT / "tests/fixtures/check-log.txt")]
        self.assertEqual([item["summary"] for item in self.catalog["checks"]], log_lines)
        by_day = {item["checked_at"][:10]: item for item in self.catalog["checks"]}
        for day in ("2026-11-01", "2026-11-05"):
            self.assertIsNone(by_day[day]["snapshot_html"])
            self.assertIn("未補造", by_day[day]["snapshot_note"])
            self.assertFalse(by_day[day]["sent"])
        self.assertIn("台北時間", by_day["2026-11-01"]["snapshot_note"])
        self.assertFalse(by_day["2026-11-01"]["timezone_explicit"])

    def test_original_html_not_regenerated(self):
        for name in ("promos-20261104-1218.html", "promos-20261107-1225.html"):
            fixture = (ROOT / "tests/fixtures" / name).read_bytes()
            saved = (ROOT / "snapshots" / name).read_bytes()
            self.assertEqual(fixture, saved)
            self.assertIn(b"min-width:980px", fixture)
        self.assertNotIn("980px", (ROOT / "css/site.css").read_text(encoding="utf-8"))
        note = next(item for item in self.catalog["checks"] if item["checked_at"].startswith("2026-11-07"))
        self.assertEqual(note["snapshot_html"], "snapshots/promos-20261107-1225.html")
        self.assertIn("不是用現在的模板重產", note["snapshot_note"])

    def test_source_text_and_weekday_warnings_kept(self):
        deals = {item["id"]: item for item in self.catalog["deals"]}
        viet = deals["vj-doubleday-20261110"]
        self.assertIn("2026/11/10（一）", viet["buy"])
        self.assertEqual(viet["end"], "2026-11-12")
        self.assertTrue(any("星期不一致" in item and "星期二" in item for item in viet["warnings"]))
        self.assertEqual(viet["window"]["basis"], "unresolved")
        self.assertIsNone(viet["window"]["purchase_end"])
        trip = deals["trip-1111-2026"]
        self.assertIn("2026/11/11（二）", trip["buy"])
        self.assertIn("2026/11/14（五）", trip["buy"])
        self.assertTrue(any("星期三" in item for item in trip["warnings"]))
        self.assertTrue(any("星期六" in item for item in trip["warnings"]))
        self.assertNotIn("alerted_update", viet)
        self.assertEqual(viet["last_verified_at"], "2026-11-07T12:25:00+08:00")
        self.assertEqual(deals["itf-2026"]["last_verified_at"], "2026-10-29T12:30:00+08:00")
        self.assertNotEqual(deals["itf-2026"]["last_verified_at"][:10], "2026-11-07")

    def test_revision_and_removed_deal_stay(self):
        deals = {item["id"]: item for item in self.catalog["deals"]}
        old = deals["ez-itf-2026"]["revisions"][0]["content"]
        self.assertIn("全民普發", old["name"])
        self.assertIn("超心動", deals["ez-itf-2026"]["name"])
        self.assertEqual(deals["ez-itf-2026"]["last_verified_at"], "2026-10-31T12:23:00+08:00")
        legacy = deals["vietjet-10routes-202610"]
        self.assertEqual(legacy["window"]["purchase_end"], "2026-11-01T23:59:00+08:00")
        as_of = parse_aware("2026-11-07T12:25:00+08:00")
        model = view_model(self.catalog, as_of)
        self.assertIn("vietjet-10routes-202610", model["sections"]["ended"])
        self.assertNotIn("vietjet-10routes-202610", model["sections"]["current"])
        just_before = view_model(self.catalog, parse_aware("2026-11-01T23:58:59+08:00"))
        self.assertIn("vietjet-10routes-202610", just_before["sections"]["current"])

    def test_open_watch_is_latest_sentence_only(self):
        latest = json.loads((ROOT / "tests/fixtures/latest.json").read_text(encoding="utf-8"))
        open_items = [item["text"] for item in self.catalog["pending_watch"] if item["status"] == "open"]
        self.assertEqual(open_items, latest["pending_watch"])
        closed = [item["text"] for item in self.catalog["pending_watch"] if item["status"] == "closed"]
        self.assertTrue(any("台灣虎航 ITF 促銷" in item for item in closed))
        self.assertTrue(all(item["text"] for item in self.catalog["pending_watch"]))


class RuleTests(unittest.TestCase):
    def test_merge_is_idempotent_and_ignores_countdown(self):
        raw = deal(purchase_end="2026-11-13T00:00:00+08:00", purchase_start="2026-11-10T01:00:00+08:00")
        catalog = seed(raw, notified=True)
        before = content_version(content_payload(catalog["deals"][0]))
        delta = {
            "checked_at": "2026-11-08T12:00:00+08:00",
            "summary": "無新的符合標準優惠，未通知。",
            "upserts": [
                {
                    "id": "sample-deal",
                    "new": True,
                    "days_left": 1,
                    "query_time": "2026-11-08 12:00",
                    "alerted_update": "2026-11-08",
                    "route": raw["route"],
                }
            ],
        }
        updated, report = apply_delta(catalog, delta)
        self.assertFalse(report["notify"])
        self.assertIsNone(report["snapshot_relpath"])
        saved = updated["deals"][0]
        self.assertEqual(saved["content_version"], before)
        self.assertEqual(saved["notified_version"], before)
        self.assertNotIn("days_left", saved)
        self.assertEqual(saved["last_verified_at"], "2026-11-08T12:00:00+08:00")
        self.assertEqual(catalog["deals"][0]["last_verified_at"], "2026-11-01T12:00:00+08:00")
        again, second = apply_delta(updated, delta)
        self.assertEqual(second["status"], "duplicate")
        self.assertEqual(dump_catalog(again), dump_catalog(updated))
        same_instant = dict(delta)
        same_instant["checked_at"] = "2026-11-08T04:00:00Z"
        _, third = apply_delta(updated, same_instant)
        self.assertEqual(third["status"], "duplicate")

    def test_timezone_boundary_upcoming_and_date_only(self):
        raw = deal(
            buy="原文維持這樣，不從這裡猜時間",
            purchase_start="2026-11-10T01:00:00+08:00",
            purchase_end="2026-11-13T00:00:00+08:00",
        )
        catalog = seed(raw, notified=False)
        upcoming = view_model(catalog, parse_aware("2026-11-10T00:59:59+08:00"))
        self.assertIn("sample-deal", upcoming["sections"]["new"])
        self.assertTrue(upcoming["flags"]["sample-deal"]["upcoming"])
        self.assertFalse(upcoming["flags"]["sample-deal"]["ended"])
        still = view_model(catalog, parse_aware("2026-11-12T23:59:59+08:00"))
        self.assertIn("sample-deal", still["sections"]["new"])
        ended = view_model(catalog, parse_aware("2026-11-13T00:00:00+08:00"))
        ended_utc = view_model(catalog, parse_aware("2026-11-12T16:00:00Z"))
        self.assertEqual(ended["sections"]["ended"], ["sample-deal"])
        self.assertEqual(ended_utc["sections"]["ended"], ["sample-deal"])

        vague = seed(deal(id="date-only", end="2026-11-08", buy="即日起 – 2026/11/08"))
        same_day = view_model(vague, parse_aware("2026-11-08T23:59:59+08:00"))
        next_day = view_model(vague, parse_aware("2026-11-09T00:00:00+08:00"))
        self.assertIn("date-only", same_day["sections"]["current"])
        self.assertFalse(same_day["flags"]["date-only"]["date_only_past"])
        self.assertIn("date-only", next_day["sections"]["current"])
        self.assertTrue(next_day["flags"]["date-only"]["date_only_past"])
        self.assertIsNone(vague["deals"][0]["window"]["purchase_end"])

        no_zone = seed(deal(id="no-zone", buy="2026/11/01 00:00 – 2026/11/02 23:59", end="2026-11-02"))
        later = view_model(no_zone, parse_aware("2027-01-01T00:00:00+08:00"))
        self.assertIn("no-zone", later["sections"]["current"])
        self.assertTrue(any("沒有寫時區" in item for item in no_zone["deals"][0]["warnings"]))

    def test_major_update_keeps_history_and_missing_fields_stay_in_watch(self):
        catalog = seed(deal(), notified=True)
        delta = {
            "checked_at": "2026-11-08T12:00:00+08:00",
            "summary": "範例活動降價，屬重大更新。",
            "upserts": [{"id": "sample-deal", "route": "台北–東京 未稅 100 元起 <script>alert(1)</script>"}],
        }
        updated, report = apply_delta(catalog, delta)
        self.assertTrue(report["notify"])
        self.assertEqual(report["candidates"][0]["change"], "major_update")
        self.assertEqual(updated["deals"][0]["revisions"][0]["content"]["route"], deal()["route"])
        self.assertIn("<script>", updated["deals"][0]["route"])
        untouched = seed(deal(id="keep-me"))
        untouched["deals"].append(catalog["deals"][0])
        merged, _report = apply_delta(untouched, delta)
        ids = [item["id"] for item in merged["deals"]]
        self.assertIn("keep-me", ids)
        self.assertEqual(next(item for item in merged["deals"] if item["id"] == "keep-me")["route"], deal()["route"])

        incomplete = {
            "checked_at": "2026-11-09T12:00:00+08:00",
            "summary": "缺欄位，先觀察。",
            "upserts": [{"id": "half-deal", "vendor": "只有業者", "name": "缺資料"}],
        }
        watched, watch_report = apply_delta(empty_catalog(), incomplete)
        self.assertFalse(watch_report["notify"])
        model = view_model(watched, parse_aware("2026-11-09T12:00:00+08:00"))
        self.assertEqual(model["sections"]["watch"], ["half-deal"])
        self.assertTrue(any("缺少欄位" in item for item in watched["deals"][0]["warnings"]))

    def test_ack_does_not_send_and_rejects_stale_version(self):
        catalog = seed(deal(), notified=False)
        delta = {"checked_at": "2026-11-08T12:00:00+08:00", "summary": "新優惠。", "upserts": []}
        updated, report = apply_delta(catalog, delta)
        self.assertTrue(report["notify"])
        version = updated["deals"][0]["content_version"]
        with self.assertRaises(PromoError):
            apply_delta(updated, {
                "checked_at": "2026-11-10T12:00:00+08:00",
                "summary": "補記。",
                "ack_notified": [{"id": "sample-deal", "content_version": "cv_not-the-real-one"}],
            })
        acked, ack_report = apply_delta(updated, {
            "checked_at": "2026-11-10T12:00:00+08:00",
            "summary": "已由 bot 送出後回寫。",
            "ack_notified": [{"id": "sample-deal", "content_version": version}],
        })
        self.assertFalse(ack_report["notify"])
        self.assertEqual(acked["deals"][0]["notified_version"], version)
        self.assertTrue(next(item for item in acked["checks"] if item["candidates"])["sent"])
        quiet, quiet_report = apply_delta(acked, {
            "checked_at": "2026-11-11T12:00:00+08:00",
            "summary": "無新的符合標準優惠，未通知。",
        })
        self.assertFalse(quiet_report["notify"])
        self.assertEqual(quiet["deals"][0]["last_verified_at"], "2026-11-01T12:00:00+08:00")

    def test_rejects_delete_and_full_rewrite(self):
        catalog = seed(deal())
        with self.assertRaises(PromoError):
            apply_delta(catalog, {"checked_at": "2026-11-08T12:00:00+08:00", "delete": ["sample-deal"]})
        with self.assertRaises(PromoError):
            apply_delta(catalog, {"checked_at": "2026-11-08T12:00:00+08:00", "deals": []})
        with self.assertRaises(PromoError):
            apply_delta(catalog, {"checked_at": "2026-11-08 12:00"})


class OutputTests(unittest.TestCase):
    def test_snapshot_escapes_html_and_cli_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "data", root / "data")
            (root / "snapshots").mkdir()
            catalog_path = root / "data/catalog.json"
            raw = deal(id="xss-deal", name='A&B <script>alert(1)</script>', vendor='<img src=x onerror="alert(1)">')
            catalog = load_catalog(catalog_path.read_text(encoding="utf-8"))
            catalog["deals"].append(make_record(
                raw, first_seen_at="2026-11-01T12:00:00+08:00", last_verified_at="2026-11-01T12:00:00+08:00", notified=True
            ))
            catalog_path.write_text(dump_catalog(catalog), encoding="utf-8")
            delta = {
                "checked_at": "2026-11-08T12:00:00+08:00",
                "summary": "測試跳脫。",
                "upserts": [{"id": "xss-deal", "route": "<script>alert(1)</script>"}],
            }
            delta_path = root / "delta.json"
            delta_path.write_text(json.dumps(delta), encoding="utf-8")
            first = run_daily(["apply", str(delta_path), "--root", str(root), "--catalog", "data/catalog.json"])
            self.assertEqual(first["status"], "applied")
            self.assertTrue(first["notify"])
            html_path = root / first["snapshot_relpath"]
            body = html_path.read_text(encoding="utf-8")
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", body)
            self.assertNotIn("<script>alert", body)
            self.assertNotIn("<img", body)
            self.assertNotIn(".innerHTML", body)
            self.assertNotIn("980px", body)
            self.assertIn("candidate_only_not_sent", (root / first["outbox_relpath"]).read_text(encoding="utf-8"))
            second = run_daily(["apply", str(delta_path), "--root", str(root), "--catalog", "data/catalog.json"])
            self.assertEqual(second["status"], "duplicate")
            self.assertEqual(list((root / "snapshots").glob("*.html")), [html_path])

    def test_templates_do_not_assign_html(self):
        js = (ROOT / "js/app.js").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn(".innerHTML", js)
        self.assertNotIn("insertAdjacentHTML", js)
        self.assertNotIn("<table", html)
        self.assertNotIn("980px", (ROOT / "css/site.css").read_text(encoding="utf-8"))
        self.assertIn("grid-template-columns: 1fr", (ROOT / "css/site.css").read_text(encoding="utf-8"))

    def test_js_view_matches_python_and_subpath(self):
        catalog = json.loads((ROOT / "data/catalog.json").read_text(encoding="utf-8"))
        as_ofs = [
            "2026-11-01T23:58:59+08:00",
            "2026-11-01T23:59:00+08:00",
            "2026-11-08T12:00:00+08:00",
            "2026-11-09T00:00:00+08:00",
            "2026-11-13T00:00:00+08:00",
        ]
        synthetic = seed(deal(
            id="edge-deal",
            buy="原文",
            purchase_start="2026-11-10T01:00:00+08:00",
            purchase_end="2026-11-13T00:00:00+08:00",
        ), notified=False)
        payload = {
            "catalogs": {"real": catalog, "edge": synthetic},
            "as_ofs": as_ofs + ["2026-11-10T00:59:59+08:00", "2026-11-12T16:00:00Z"],
            "urls": [
                "https://ckw10326.github.io/Lifeismmmoney/",
                "https://ckw10326.github.io/Lifeismmmoney/index.html",
                "https://ckw10326.github.io/Lifeismmmoney",
                "http://127.0.0.1:8765/Lifeismmmoney/",
                "https://ckw10326.github.io/",
            ],
            "hrefs": ["https://example.com/a?b=1&c=2", "javascript:alert(1)", "data:text/html,hi", "http://example.com"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "in.json"
            target = Path(tmp) / "out.json"
            source.write_text(json.dumps(payload), encoding="utf-8")
            script = ROOT / "tests/view_check.js"
            subprocess.run(["node", str(script), str(source), str(target)], check=True)
            got = json.loads(target.read_text(encoding="utf-8"))
        for name, body in payload["catalogs"].items():
            loaded = body if name == "real" else load_catalog(dump_catalog(body))
            for as_of in payload["as_ofs"]:
                expected = view_model(loaded, parse_aware(as_of))
                self.assertEqual(got[name][as_of], {
                    "sections": expected["sections"],
                    "flags": expected["flags"],
                    "open_watch": expected["open_watch"],
                    "closed_watch": expected["closed_watch"],
                })
        base = "https://ckw10326.github.io/Lifeismmmoney/data/catalog.json"
        self.assertEqual(got["urls"][0], base)
        self.assertEqual(got["urls"][1], base)
        self.assertEqual(got["urls"][2], base)
        self.assertEqual(got["urls"][3], "http://127.0.0.1:8765/Lifeismmmoney/data/catalog.json")
        self.assertEqual(got["urls"][4], "https://ckw10326.github.io/data/catalog.json")
        self.assertEqual(got["hrefs"][0], payload["hrefs"][0])
        self.assertEqual(got["hrefs"][1], "")
        self.assertEqual(got["hrefs"][2], "")
        self.assertEqual(got["hrefs"][3], "http://example.com")

    def test_pages_subpath_serves_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "Lifeismmmoney"
            site.mkdir()
            for relative in ("index.html", "css/site.css", "js/app.js", "data/catalog.json"):
                dest = site / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / relative, dest)
            port = free_port()
            server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
            server.directory = tmp
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/Lifeismmmoney/") as response:
                    page = response.read().decode("utf-8")
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/Lifeismmmoney/data/catalog.json") as response:
                    data = response.read()
                self.assertIn('href="css/site.css"', page)
                self.assertIn('src="js/app.js"', page)
                self.assertNotIn('src="/js/app.js"', page)
                self.assertNotIn('href="/data/catalog.json"', page)
                self.assertEqual(json.loads(data)["schema_version"], 1)
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/data/catalog.json")
                    self.fail("子路徑以外不應讀到 catalog")
                except urllib.error.HTTPError as error:
                    error.close()
                    self.assertEqual(error.code, 404)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


class _Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        root = Path(self.server.directory)
        cleaned = path.split("?", 1)[0].split("#", 1)[0]
        relative = cleaned.lstrip("/")
        return str(root / relative)

    def log_message(self, fmt, *args):
        return


def run_daily(args):
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools/daily.py"), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stdout + completed.stderr)
    return json.loads(completed.stdout)


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class RenderHelperTests(unittest.TestCase):
    def test_render_uses_catalog_time_not_a_fresh_stamp(self):
        catalog = seed(deal(name="<b>粗體</b>"), notified=False)
        updated, _report = apply_delta(catalog, {
            "checked_at": "2026-11-08T12:00:00+08:00",
            "summary": "新優惠。",
        })
        body = render(updated, "2026-11-08T12:00:00+08:00", css_text="body{color:#111}")
        self.assertIn("2026-11-08T12:00:00+08:00", body)
        self.assertIn("&lt;b&gt;粗體&lt;/b&gt;", body)
        self.assertNotIn("<b>", body)


if __name__ == "__main__":
    unittest.main()
