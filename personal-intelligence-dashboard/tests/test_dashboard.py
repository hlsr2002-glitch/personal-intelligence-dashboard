import json
import sys
import unittest
from pathlib import Path
from datetime import date
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

    def test_opportunity_score_explains_unknowns_and_is_not_a_success_probability(self):
        arrisca = next(item for item in dashboard.current_opportunities(date(2026, 11, 7)) if item["id"] == "arrisca-c-2026")
        self.assertEqual(arrisca["score_label"], "Prioridade de investigação")
        self.assertEqual(arrisca["score"], 33)
        self.assertEqual(arrisca["score_confidence"], 35)
        criteria = {item["id"]: item for item in arrisca["score_criteria"]}
        self.assertIsNone(criteria["demand"]["points"])
        self.assertIsNone(criteria["competition"]["points"])
        self.assertIn("Não foi encontrada", criteria["demand"]["basis"])

    def test_expired_public_calls_drop_out_of_the_current_radar(self):
        current = dashboard.current_opportunities(date(2026, 12, 1))
        self.assertNotIn("alt2030-2026-24-economia-circular", [item["id"] for item in current])
        self.assertIn("arrisca-c-2026", [item["id"] for item in current])
        after_deadlines = dashboard.current_opportunities(date(2027, 1, 1))
        self.assertEqual(after_deadlines, [])

    def test_recommendation_history_deduplicates_and_keeps_the_source_snapshot(self):
        recommendations = dashboard.build_recommendations(dashboard.current_opportunities(date(2026, 11, 7)))
        first = dashboard.update_recommendation_history([], recommendations, date(2026, 11, 7))
        again = dashboard.update_recommendation_history(first, recommendations, date(2026, 11, 8))
        self.assertEqual(len(again), len(first))
        self.assertEqual(again[0]["first_seen"], "2026-11-07")
        self.assertEqual(again[0]["last_seen"], "2026-11-08")
        self.assertTrue(again[0]["source_url"].startswith("https://"))

    def test_daily_briefing_does_not_reannounce_the_same_opportunity(self):
        first = dashboard.build_payload([], [], [], [], today=date(2026, 11, 7))
        self.assertTrue(first["new_recommendation_ids"])
        self.assertIn("Novos sinais", first["briefing"]["title"])
        second = dashboard.build_payload(
            [], [], [], [],
            previous_history=first["recommendation_history"],
            today=date(2026, 11, 8),
        )
        self.assertEqual(second["new_recommendation_ids"], [])
        self.assertIn("Sem sinal novo", second["briefing"]["title"])

    def test_alert_history_records_only_observed_financial_thresholds_once(self):
        observed = dashboard.make_alerts(
            [{"symbol": "QQQ", "name": "Nasdaq 100", "change_pct": -5.2, "date": "2026-11-06"}],
            [],
        )
        first = dashboard.update_alert_history([], observed, date(2026, 11, 7))
        again = dashboard.update_alert_history(first, observed, date(2026, 11, 8))
        self.assertEqual(len(first), 1)
        self.assertEqual(len(again), 1)
        self.assertEqual(first[0]["event_id"], "queda:QQQ:2026-11-06")
        self.assertEqual(dashboard.update_alert_history([], [], date(2026, 11, 7)), [])

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
