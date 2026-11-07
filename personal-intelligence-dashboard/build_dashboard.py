#!/usr/bin/env python3
"""Recolhe fontes públicas e gera os dados consumidos pelo dashboard estático."""

from __future__ import annotations

import json
import math
import os
import re
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ntfy_utils import send_alert_notifications


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.example.json"
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
STATE_PATH = DATA_DIR / "active_alerts.json"
OUTPUT_PATH = DOCS_DIR / "data.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def fetch_json(url: str, *, timeout: int = 30) -> dict[str, Any] | None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PersonalIntelligenceDashboard/2.0 (public-data prototype)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload if isinstance(payload, dict) else None
    except (
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ):
        return None


def _numeric(value: Any) -> float | None:
    try:
        if value in (None, "", "."):
            return None
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def _series_metrics(history: list[dict[str, Any]]) -> dict[str, float | None]:
    values = [float(point["value"]) for point in history if _numeric(point.get("value")) is not None]
    if len(values) < 2:
        return {"return_30d": None, "return_90d": None, "volatility_30d": None}

    def pct_return(sessions: int) -> float | None:
        if len(values) < 2:
            return None
        start = values[-min(sessions + 1, len(values))]
        return (values[-1] / start - 1) * 100 if start else None

    daily_returns = [current / prior - 1 for prior, current in zip(values[-31:-1], values[-30:]) if prior]
    volatility = None
    if len(daily_returns) >= 2:
        volatility = statistics.stdev(daily_returns) * math.sqrt(252) * 100
    return {
        "return_30d": pct_return(30),
        "return_90d": pct_return(90),
        "volatility_30d": volatility,
    }


def collect_quotes(api_key: str | None) -> list[dict[str, Any]]:
    if not api_key:
        return []
    results: list[dict[str, Any]] = []
    for index, asset in enumerate(CONFIG["assets"]):
        if index:
            # A free Alpha Vantage key has a low request rate; seven calls stay
            # comfortably below its typical per-minute limit.
            time.sleep(13)
        query = urllib.parse.urlencode(
            {
                "function": "TIME_SERIES_DAILY",
                "symbol": asset["symbol"],
                "outputsize": "compact",
                "apikey": api_key,
            }
        )
        payload = fetch_json(f"https://www.alphavantage.co/query?{query}")
        raw_history = (payload or {}).get("Time Series (Daily)")
        if not isinstance(raw_history, dict):
            continue
        history = []
        for observation_date, row in raw_history.items():
            close = _numeric(row.get("4. close"))
            if close is not None:
                history.append({"date": observation_date, "value": close})
        history.sort(key=lambda point: point["date"])
        if not history:
            continue
        metrics = _series_metrics(history)
        previous_close = history[-2]["value"] if len(history) > 1 else None
        change_pct = (
            (history[-1]["value"] / previous_close - 1) * 100
            if previous_close
            else 0.0
        )
        results.append(
            {
                "symbol": asset["symbol"],
                "name": asset["name"],
                "currency": asset.get("currency", "USD"),
                "price": history[-1]["value"],
                "change_pct": change_pct,
                "date": history[-1]["date"],
                "history": history,
                **metrics,
                "source": "Alpha Vantage",
                "source_url": "https://www.alphavantage.co/documentation/",
            }
        )
    return results


def collect_macro(api_key: str | None) -> list[dict[str, Any]]:
    if not api_key:
        return []
    observations: list[dict[str, Any]] = []
    today = date.today()
    for series in CONFIG["macro_series"]:
        start = today - timedelta(days=365 * int(series.get("history_years", 10)))
        query = urllib.parse.urlencode(
            {
                "series_id": series["id"],
                "api_key": api_key,
                "file_type": "json",
                "sort_order": "asc",
                "observation_start": start.isoformat(),
            }
        )
        payload = fetch_json(f"https://api.stlouisfed.org/fred/series/observations?{query}")
        rows = (payload or {}).get("observations", [])
        history = []
        for row in rows:
            value = _numeric(row.get("value"))
            if value is not None:
                history.append({"date": row.get("date", ""), "value": value})
        if not history:
            continue
        observations.append(
            {
                "id": series["id"],
                "name": series["name"],
                "unit": series["unit"],
                "frequency": series.get("frequency", "Varia"),
                "value": history[-1]["value"],
                "date": history[-1]["date"],
                "history": history,
                "description": series.get("description", ""),
                "source": "FRED",
                "source_url": series.get("source_url", "https://fred.stlouisfed.org/"),
            }
        )
    return observations


def parse_json_stat_series(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Read a Eurostat JSON-stat series, including its sparse value index."""
    dimensions = payload.get("id", [])
    sizes = payload.get("size", [])
    if "time" not in dimensions or len(dimensions) != len(sizes):
        return []
    time_dimension = payload.get("dimension", {}).get("time", {}).get("category", {})
    time_index = time_dimension.get("index", {})
    if isinstance(time_index, list):
        labels_by_position = {position: label for position, label in enumerate(time_index)}
    elif isinstance(time_index, dict):
        labels_by_position = {int(position): label for label, position in time_index.items()}
    else:
        return []
    time_position = dimensions.index("time")
    values = payload.get("value", {})
    entries = enumerate(values) if isinstance(values, list) else values.items()
    output = []
    for flat_index, raw_value in entries:
        value = _numeric(raw_value)
        if value is None:
            continue
        try:
            remainder = int(flat_index)
            coordinates = [0] * len(sizes)
            for position in range(len(sizes) - 1, -1, -1):
                dimension_size = int(sizes[position])
                coordinates[position] = remainder % dimension_size
                remainder //= dimension_size
            observation_date = labels_by_position.get(coordinates[time_position])
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        if observation_date:
            output.append({"date": observation_date, "value": value})
    output.sort(key=lambda point: point["date"])
    return output


def collect_portugal() -> list[dict[str, Any]]:
    series_results = []
    for series in CONFIG["portugal_series"]:
        query = urllib.parse.urlencode({"lang": "en", **series["filters"]})
        payload = fetch_json(
            f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
            f"{series['id']}?{query}"
        )
        history = parse_json_stat_series(payload or {})
        if not history:
            continue
        series_results.append(
            {
                "id": series["id"],
                "name": series["name"],
                "unit": series["unit"],
                "frequency": series["frequency"],
                "value": history[-1]["value"],
                "date": history[-1]["date"],
                "history": history,
                "description": series["description"],
                "source": "Eurostat",
                "source_url": series["source_url"],
            }
        )
    return series_results


def reconstruct_abstract(inverted_index: Any) -> str:
    if not isinstance(inverted_index, dict):
        return ""
    words = []
    for word, positions in inverted_index.items():
        if isinstance(positions, list):
            words.extend((int(position), word) for position in positions)
    words.sort(key=lambda item: item[0])
    text = " ".join(word for _, word in words)
    return re.sub(r"\s+([,.;:!?])", r"\1", text).strip()


def _sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", normalized) if sentence.strip()]


def _truncate(text: str, limit: int = 420) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"


def _why_read(title: str, abstract: str) -> str:
    text = f"{title} {abstract}".lower()
    reasons = [
        (("portugal", "portuguese"), "Traz evidência diretamente ligada a Portugal."),
        (("inflation", "price level", "consumer price"), "Ajuda a compreender a evolução dos preços e os seus fatores."),
        (("unemployment", "employment", "labour market", "labor market", "wage"), "Ajuda a interpretar emprego, salários e condições do mercado de trabalho."),
        (("artificial intelligence", "machine learning", "robot"), "Apresenta evidência sobre aplicações e impactos da inteligência artificial."),
        (("energy", "electricity", "renewable", "climate"), "Relaciona decisões económicas com energia e transição climática."),
    ]
    for terms, reason in reasons:
        if any(term in text for term in terms):
            return reason
    return "Oferece evidência académica recente para conhecer melhor este tema."


def collect_research() -> list[dict[str, Any]]:
    start_date = (date.today() - timedelta(days=90)).isoformat()
    query = urllib.parse.urlencode(
        {
            "search": CONFIG["research_topics"],
            "filter": f"from_publication_date:{start_date},has_abstract:true",
            "sort": "publication_date:desc",
            "per-page": "8",
            "select": "id,title,publication_date,doi,primary_location,cited_by_count,open_access,abstract_inverted_index",
        }
    )
    payload = fetch_json(f"https://api.openalex.org/works?{query}")
    works = (payload or {}).get("results", [])
    results = []
    for work in works:
        abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
        sentences = _sentences(abstract)
        if not abstract or not sentences:
            continue
        location = work.get("primary_location") or {}
        source = location.get("source") or {}
        doi = work.get("doi") or ""
        url = location.get("landing_page_url") or doi or work.get("id") or ""
        conclusion = next(
            (
                sentence
                for sentence in reversed(sentences)
                if re.search(r"\b(conclud|findings?|results?|suggests?|shows?|demonstrat|indicat)\b", sentence, re.I)
            ),
            sentences[-1],
        )
        results.append(
            {
                "title": work.get("title") or "Título indisponível",
                "date": work.get("publication_date", ""),
                "doi": doi,
                "url": url,
                "source": source.get("display_name", "OpenAlex"),
                "citations": work.get("cited_by_count", 0),
                "open_access": bool((work.get("open_access") or {}).get("is_oa")),
                "summary": _truncate(" ".join(sentences[:2])),
                "conclusion": _truncate(conclusion),
                "why_read": _why_read(work.get("title", ""), abstract),
                "summary_basis": "Resumo do registo OpenAlex; confirma no trabalho original.",
            }
        )
    return results


def make_alerts(quotes: list[dict[str, Any]], macro: list[dict[str, Any]]) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    for quote in quotes:
        if quote["change_pct"] <= -5:
            alerts.append(
                {
                    "id": f"queda:{quote['symbol']}",
                    "level": "Crítico",
                    "title": f"Queda diária relevante em {quote['symbol']}",
                    "detail": f"{quote['name']}: {quote['change_pct']:.2f}% no último dia de negociação.",
                }
            )
    vix = next((item for item in macro if item["id"] == "VIXCLS"), None)
    if vix and vix["value"] > 35:
        alerts.append(
            {
                "id": "vix:acima-35",
                "level": "Crítico",
                "title": "Volatilidade de mercado elevada",
                "detail": f"VIX a {vix['value']:.1f} pontos em {vix['date']} (limiar: 35).",
            }
        )
    return alerts


def _last_change(series: dict[str, Any], steps: int = 3) -> float | None:
    history = series.get("history", [])
    if len(history) <= steps:
        return None
    return float(history[-1]["value"]) - float(history[-1 - steps]["value"])


def generate_insights(
    quotes: list[dict[str, Any]], portugal: list[dict[str, Any]]
) -> dict[str, list[dict[str, str]]]:
    constructive: list[dict[str, str]] = []
    risks: list[dict[str, str]] = []
    by_id = {item["id"]: item for item in portugal}

    gdp = by_id.get("namq_10_gdp")
    if gdp:
        if gdp["value"] > 0:
            constructive.append(
                {
                    "title": "Atividade portuguesa cresceu no trimestre",
                    "detail": f"O PIB real avançou {gdp['value']:.1f}% face ao trimestre anterior ({gdp['date']}). É uma leitura de atividade recente, não uma previsão.",
                    "source": "Eurostat · PIB trimestral",
                    "source_url": gdp["source_url"],
                }
            )
        else:
            risks.append(
                {
                    "title": "Atividade portuguesa contraiu no trimestre",
                    "detail": f"O PIB real variou {gdp['value']:.1f}% face ao trimestre anterior ({gdp['date']}). Um trimestre isolado não confirma uma tendência.",
                    "source": "Eurostat · PIB trimestral",
                    "source_url": gdp["source_url"],
                }
            )

    inflation = by_id.get("prc_hicp_minr")
    if inflation:
        delta = _last_change(inflation, 3)
        if inflation["value"] <= 2.5 and delta is not None and delta < 0:
            constructive.append(
                {
                    "title": "Inflação portuguesa moderou nos últimos meses",
                    "detail": f"O HICP anual foi {inflation['value']:.1f}% em {inflation['date']}; caiu {abs(delta):.1f} pontos percentuais em três meses. O objetivo de 2% do BCE refere-se à área do euro e ao médio prazo.",
                    "source": "Eurostat · HICP",
                    "source_url": inflation["source_url"],
                    "context_source": "BCE · objetivo de inflação",
                    "context_source_url": "https://www.ecb.europa.eu/press/pr/date/2025/html/ecb.pr250630~aabf988af8.en.html",
                }
            )
        elif inflation["value"] > 2.5 or (delta is not None and delta > 0.5):
            risks.append(
                {
                    "title": "Pressão dos preços merece acompanhamento",
                    "detail": f"O HICP anual foi {inflation['value']:.1f}% em {inflation['date']}. A inflação mede a variação dos preços; não significa que os preços tenham descido quando a taxa baixa.",
                    "source": "Eurostat · HICP",
                    "source_url": inflation["source_url"],
                }
            )

    unemployment = by_id.get("une_rt_m")
    if unemployment:
        delta = _last_change(unemployment, 3)
        if delta is not None and delta < -0.15:
            constructive.append(
                {
                    "title": "Desemprego recuou face a três meses antes",
                    "detail": f"A taxa ajustada sazonalmente foi {unemployment['value']:.1f}% em {unemployment['date']} ({delta:.1f} pontos percentuais em três meses).",
                    "source": "Eurostat · desemprego mensal",
                    "source_url": unemployment["source_url"],
                }
            )
        elif delta is not None and delta > 0.15:
            risks.append(
                {
                    "title": "Desemprego aumentou face a três meses antes",
                    "detail": f"A taxa ajustada sazonalmente foi {unemployment['value']:.1f}% em {unemployment['date']} (+{delta:.1f} pontos percentuais em três meses).",
                    "source": "Eurostat · desemprego mensal",
                    "source_url": unemployment["source_url"],
                }
            )

    debt = by_id.get("gov_10q_ggdebt")
    if debt:
        delta = _last_change(debt, 4)
        if delta is not None and delta > 2:
            risks.append(
                {
                    "title": "Rácio da dívida pública subiu no último ano",
                    "detail": f"A dívida bruta consolidada foi {debt['value']:.1f}% do PIB em {debt['date']}, uma subida de {delta:.1f} pontos percentuais em quatro trimestres.",
                    "source": "Eurostat · dívida pública trimestral",
                    "source_url": debt["source_url"],
                }
            )

    market_returns = [item for item in quotes if item.get("return_30d") is not None]
    if market_returns:
        best = max(market_returns, key=lambda item: item["return_30d"])
        if best["return_30d"] > 0:
            constructive.append(
                {
                    "title": "Desempenho positivo recente para investigar",
                    "detail": f"{best['name']} valorizou {best['return_30d']:.1f}% em cerca de 30 sessões até {best['date']}. Desempenho passado não indica retorno futuro.",
                    "source": "Alpha Vantage · preços diários",
                    "source_url": best["source_url"],
                }
            )
        most_volatile = max(
            market_returns,
            key=lambda item: item.get("volatility_30d") or 0,
        )
        if (most_volatile.get("volatility_30d") or 0) >= 25:
            risks.append(
                {
                    "title": "Oscilações elevadas num ativo acompanhado",
                    "detail": f"A volatilidade anualizada estimada de {most_volatile['name']} foi {most_volatile['volatility_30d']:.1f}% com base nas últimas 30 sessões. É uma medida de variação, não uma previsão de perda.",
                    "source": "Alpha Vantage · preços diários",
                    "source_url": most_volatile["source_url"],
                }
            )

    if not constructive:
        constructive.append(
            {
                "title": "Sem sinal construtivo destacado nesta atualização",
                "detail": "Os indicadores disponíveis não ativaram as regras descritivas desta secção.",
                "source": "Dados mostrados no dashboard",
                "source_url": "",
            }
        )
    if not risks:
        risks.append(
            {
                "title": "Sem risco destacado pelas regras atuais",
                "detail": "Isto não significa ausência de risco; apenas que os limiares descritivos não foram atingidos.",
                "source": "Dados mostrados no dashboard",
                "source_url": "",
            }
        )
    return {"opportunities": constructive, "risks": risks}


def _load_previous_alert_ids() -> set[str]:
    try:
        return set(json.loads(STATE_PATH.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, TypeError):
        return set()


def build_payload(
    quotes: list[dict[str, Any]],
    macro: list[dict[str, Any]],
    portugal: list[dict[str, Any]],
    research: list[dict[str, Any]],
    previous_alert_ids: set[str] | None = None,
    ntfy_topic: str | None = None,
) -> dict[str, Any]:
    alerts = make_alerts(quotes, macro)
    previous = previous_alert_ids or set()
    new_alerts = [alert for alert in alerts if alert["id"] not in previous]
    if ntfy_topic and new_alerts:
        send_alert_notifications(ntfy_topic, new_alerts)
    return {
        "schema_version": 2,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "quotes": quotes,
        "macro": macro,
        "portugal": portugal,
        "research": research,
        "alerts": alerts,
        "insights": generate_insights(quotes, portugal),
        "health": {
            "enabled": False,
            "message": "Área reservada a uma fase privada futura. Não são recolhidos nem publicados dados de saúde.",
        },
    }


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    alpha_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
    fred_key = os.environ.get("FRED_API_KEY")
    ntfy_topic = os.environ.get("NTFY_TOPIC")

    quotes = collect_quotes(alpha_key)
    macro = collect_macro(fred_key)
    portugal = collect_portugal()
    research = collect_research()
    previous = _load_previous_alert_ids()
    payload = build_payload(quotes, macro, portugal, research, previous, ntfy_topic)

    STATE_PATH.write_text(
        json.dumps([alert["id"] for alert in payload["alerts"]], indent=2) + "\n",
        encoding="utf-8",
    )
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "Dashboard gerado: "
        f"{len(quotes)} séries de mercado, {len(macro)} séries FRED, "
        f"{len(portugal)} indicadores de Portugal, {len(research)} artigos, "
        f"{len(payload['alerts'])} alertas ativos."
    )


if __name__ == "__main__":
    main()
