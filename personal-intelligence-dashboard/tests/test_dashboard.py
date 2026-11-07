import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

import build_dashboard as dashboard
import ntfy_utils


class DashboardTests(unittest.TestCase):
    def test_parse_sparse_eurostat_json_stat_time_series(self):
        payload = {
            "id": ["geo", "time"],
            "size": [1, 3],
            "dimension": {"time": {"category": {"index": {"2023-01": 0, "2023-02": 1, "2023-03": 2}}}},
            "value": {"0": 1.2, "2": 1.4},
        }
        self.assertEqual(
            dashboard.parse_json_stat_series(payload),
            [{"date": "2023-01", "value": 1.2}, {"date": "2023-03", "value": 1.4}],
        )

    def test_reconstruct_openalex_abstract_and_make_reading_notes(self):
        abstract = dashboard.reconstruct_abstract({"Employment": [0], "increased": [1], "in": [2], "Portugal.": [3]})
        self.assertEqual(abstract, "Employment increased in Portugal.")
        self.assertEqual(dashboard._why_read("Employment in Portugal", abstract), "Traz evidência diretamente ligada a Portugal.")

    def test_alert_thresholds_remain_selective(self):
        quotes = [
            {"symbol": "SPY", "name": "S&P 500", "change_pct": -4.99},
            {"symbol": "QQQ", "name": "Nasdaq 100", "change_pct": -5.0},
        ]
        self.assertEqual([a["id"] for a in dashboard.make_alerts(quotes, [])], ["queda:QQQ"])
        self.assertEqual(dashboard.make_alerts([], [{"id": "VIXCLS", "value": 35}]), [])
        self.assertEqual(dashboard.make_alerts([], [{"id": "VIXCLS", "value": 35.1, "date": "2026-11-06"}])[0]["id"], "vix:acima-35")

    def test_ntfy_topic_accepts_slug_and_topic_url_without_exposing_url(self):
        self.assertEqual(ntfy_utils.normalize_topic("dashboard_topic_31"), "dashboard_topic_31")
        self.assertEqual(ntfy_utils.normalize_topic("ntfy.sh/dashboard_topic_31"), "dashboard_topic_31")
        self.assertEqual(ntfy_utils.normalize_topic("https://ntfy.sh/dashboard_topic_31"), "dashboard_topic_31")
        self.assertIsNone(ntfy_utils.normalize_topic("https://evil.example/dashboard_topic_31"))
        self.assertIsNone(ntfy_utils.normalize_topic("ntfy.sh/topic/extra"))

    def test_neutral_ntfy_test_has_no_financial_alert_side_effect(self):
        captured = {}

        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["title"] = request.get_header("Title")
            captured["priority"] = request.get_header("Priority")
            captured["body"] = request.data.decode()
            return Response()

        with patch.object(ntfy_utils.urllib.request, "urlopen", fake_urlopen):
            self.assertTrue(ntfy_utils.send_test_notification("ntfy.sh/dashboard_topic_31"))

        self.assertEqual(captured["title"], "Teste de notificações")
        self.assertEqual(captured["priority"], "default")
        self.assertIn("não representa um alerta financeiro", captured["body"])
        self.assertNotIn("active_alerts", json.dumps(captured))


if __name__ == "__main__":
    unittest.main()
