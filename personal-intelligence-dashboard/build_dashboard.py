#!/usr/bin/env python3
"""Recolhe fontes públicas e gera os dados consumidos pelo dashboard estático."""

from __future__ import annotations

import json
import copy
import hashlib
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
HISTORY_PATH = DATA_DIR / "recommendation_history.json"
OUTPUT_PATH = DOCS_DIR / "data.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


# Short, manually checked public-source snapshot. Each entry is removed from
# the live radar after its published deadline. The source directory remains
# live as outbound links; no undocumented API or private portal is scraped.
OPPORTUNITY_CHECKED_AT = "2026-11-07"
CURATED_OPPORTUNITIES: list[dict[str, Any]] = [
    {
        "id": "arrisca-c-2026",
        "title": "ARRISCA C — concurso nacional de ideias de base científico-tecnológica",
        "category": "Concurso / criação de empresa",
        "sector": "Tecnologia e inovação",
        "location": "Portugal",
        "source": "IAPMEI",
        "source_url": "https://www.iapmei.pt/pt/comunicacao/noticias/arrisca-c-candidaturas-ate-18-de-dezembro/",
        "published_at": "2026-11-02",
        "deadline": "2026-12-18",
        "description": "Concurso para valorizar ideias de negócio e promover spin-offs académicas e startups. A 15.ª edição inclui cinco categorias e prémios monetários até 2.500 €, além de prémios em serviços.",
        "eligibility": "Docentes, investigadores, pessoal técnico, bolseiros e estudantes atuais ou antigos do ensino superior; a categoria Júnior destina-se a estudantes do secundário e técnico-profissional.",
        "why_it_matters": "É uma via concreta para testar uma ideia científico-tecnológica através de avaliação, mentoria, incubação e outros serviços.",
        "capital_required": None,
        "capital_note": "O anúncio não indica o capital necessário para criar a empresa. Os prémios até 2.500 € são prémios do concurso, não um orçamento garantido para lançar o negócio.",
        "market_potential": "O concurso não demonstra procura comercial nem valida clientes. A procura teria de ser testada com utilizadores e compradores reais.",
        "risks": "Elegibilidade restrita a determinados vínculos académicos; prémios e serviços dependem do resultado do concurso; não há garantia de financiamento ou sucesso comercial.",
        "next_steps": [
            "Confirmar a elegibilidade e as regras da categoria no regulamento oficial.",
            "Verificar o prazo e os documentos diretamente no site do concurso.",
            "Falar com potenciais utilizadores antes de investir em desenvolvimento."
        ],
        "fit_points": 20,
        "source_checked_at": "2026-11-07",
        "kind": "call"
    },
    {
        "id": "mpr-2026-07-demonstradores",
        "title": "I&D Empresarial — projetos demonstradores individuais e em copromoção",
        "category": "Apoio / I&D empresarial",
        "sector": "Tecnologia e inovação",
        "location": "Portugal continental e Regiões Autónomas (ver aviso)",
        "source": "IAPMEI · Aviso MPr-2026-07",
        "source_url": "https://www.iapmei.pt/pt/comunicacao/noticias/concurso-aberto-aviso-mpr-2026-07/",
        "published_at": "2026-07-22",
        "deadline": "2026-12-29",
        "description": "Apoio a projetos demonstradores de tecnologias avançadas e linhas-piloto, partindo de I&D concluída e demonstrando vantagens técnicas e económicas em contexto real.",
        "eligibility": "Micro, pequenas e médias empresas e empresas de pequena-média capitalização com contabilidade organizada; copromoção com entidades do sistema de investigação e inovação também prevista.",
        "why_it_matters": "Pode interessar a empresas com tecnologia já desenvolvida que precisem de demonstrar funcionamento e valor em condições reais.",
        "capital_required": None,
        "capital_note": "A página consultada não indica um montante de investimento por projeto. Confirmar dotação, despesas elegíveis e condições no aviso oficial.",
        "market_potential": "O aviso pede demonstração de vantagens técnicas e económicas; não prova por si só procura suficiente nem viabilidade comercial.",
        "risks": "Destina-se a empresas com contabilidade organizada e I&D concluída; exige preparação técnica e documental. A elegibilidade exata depende do aviso e da região.",
        "next_steps": [
            "Ler o aviso completo e confirmar se o projeto e a região são elegíveis.",
            "Validar o prazo de candidatura no Balcão dos Fundos.",
            "Estimar custos elegíveis, contrapartida própria e evidência de procura antes de avançar."
        ],
        "fit_points": 14,
        "source_checked_at": "2026-11-07",
        "kind": "call"
    },
    {
        "id": "alt2030-2026-24-economia-circular",
        "title": "Economia Circular — ITI Água e Ecossistemas da Paisagem",
        "category": "Incentivo / sustentabilidade",
        "sector": "Economia circular e água",
        "location": "Alentejo",
        "source": "IAPMEI · Aviso ALT2030-2026-24",
        "source_url": "https://www.iapmei.pt/pt/comunicacao/noticias/transicao-esg-novos-incentivos-a-economia-circular-no-alentejo/",
        "published_at": "2026-06-15",
        "deadline": "2026-11-30",
        "description": "Apoio para PME sediadas no Alentejo com investimentos em economia circular, eficiência de processos, novos produtos a partir de subprodutos e otimização do uso de água.",
        "eligibility": "Pequenas e médias empresas sediadas no Alentejo; consultar o aviso para condições completas.",
        "why_it_matters": "É um aviso específico para modelos e processos de economia circular, com prazo próximo e localização definida.",
        "capital_required": 200000,
        "capital_note": "O aviso indica despesa elegível mínima de 200.000 € e cofinanciamento máximo de 60%. A despesa mínima não é o custo total do projeto nem garante aprovação.",
        "market_potential": "O aviso identifica áreas elegíveis, mas não mede a procura final por produtos ou serviços; essa validação cabe ao promotor.",
        "risks": "Exige PME sediada no Alentejo, investimento elevado e confirmação das regras de elegibilidade. Prazo publicado: 30 de novembro de 2026.",
        "next_steps": [
            "Confirmar que a sede e a atividade cumprem os critérios territoriais.",
            "Ler o aviso ALT2030-2026-24 e validar custos elegíveis.",
            "Calcular a necessidade de tesouraria e a contrapartida antes de considerar candidatura."
        ],
        "fit_points": 8,
        "source_checked_at": "2026-11-07",
        "kind": "call"
    },
    {
        "id": "pme-lider-2026",
        "title": "Estatuto PME Líder 2026",
        "category": "Estatuto empresarial",
        "sector": "PME e financiamento",
        "location": "Portugal",
        "source": "IAPMEI",
        "source_url": "https://www.iapmei.pt/pt/comunicacao/noticias/pme-lider-2026-candidaturas-abertas/",
        "published_at": "2026-10-29",
        "deadline": "2026-11-30",
        "description": "Candidatura ao estatuto PME Líder 2026. O processo começa através de um banco parceiro, que analisa o perfil de risco e formaliza a proposta ao IAPMEI.",
        "eligibility": "PME que cumpram o regulamento dos Estatutos PME Líder e PME Excelência 2026.",
        "why_it_matters": "Pode facilitar o acesso a condições especiais junto da banca e a serviços associados para uma PME já em atividade.",
        "capital_required": None,
        "capital_note": "Não é um subsídio nem uma estimativa de capital de arranque.",
        "market_potential": "O estatuto não é evidência de procura de mercado.",
        "risks": "Adequado a PME já constituídas que cumpram os critérios; a decisão depende de análise do banco parceiro e do IAPMEI.",
        "next_steps": [
            "Consultar o regulamento de 2026.",
            "Confirmar os critérios com um banco parceiro antes de preparar candidatura."
        ],
        "fit_points": 4,
        "source_checked_at": "2026-11-07",
        "kind": "support"
    }
]


OPPORTUNITY_SOURCES: list[dict[str, str]] = [
    {
        "id": "iapmei-een",
        "name": "IAPMEI · Enterprise Europe Network",
        "category": "Parcerias e procura comercial",
        "url": "https://www.iapmei.pt/pt/saber-mais/apoio-empresarial-e-formacao/enterprise-europe-network/oportunidades-de-negocio/",
        "description": "Ofertas e pedidos de cooperação de empresas europeias, com publicações datadas. As oportunidades mudam e devem ser confirmadas na página original.",
        "status": "Consulta direta ao portal"
    },
    {
        "id": "portugal2030-open",
        "name": "Portugal 2030 · Avisos",
        "category": "Apoios e concursos abertos",
        "url": "https://portugal2030.pt/avisos/",
        "description": "Pesquisa oficial de avisos e prazos de candidatura. O estado e as regras completas devem ser confirmados na ficha e no aviso PDF.",
        "status": "Consulta direta ao portal"
    },
    {
        "id": "portugal2030-plan",
        "name": "Portugal 2030 · Plano Anual de Avisos",
        "category": "Avisos previstos",
        "url": "https://portugal2030.pt/plano-anual-de-avisos/",
        "description": "Calendário previsional de avisos; um aviso planeado não significa que as candidaturas estejam abertas.",
        "status": "Previsão, não candidatura aberta"
    },
    {
        "id": "iapmei-news",
        "name": "IAPMEI · Concursos e notícias",
        "category": "Empreendedorismo e PME",
        "url": "https://www.iapmei.pt/pt/comunicacao/noticias",
        "description": "Atualizações oficiais sobre concursos, iniciativas, incentivos e oportunidades empresariais.",
        "status": "Consulta direta ao portal"
    },
    {
        "id": "base",
        "name": "Portal BASE · Contratação pública",
        "category": "Concursos e necessidades públicas",
        "url": "https://www.base.gov.pt/Base4/pt/",
        "description": "Pesquisar procedimentos e contratos públicos. A API oficial exige credenciais e autorização; este painel não a consulta.",
        "status": "Ligação de pesquisa; API pendente"
    },
    {
        "id": "trespasse",
        "name": "Portal do Trespasse",
        "category": "Negócios à venda · fonte de terceiros",
        "url": "https://portaldotrespasse.pt/",
        "description": "Anúncios de terceiros sem validação independente pelo dashboard. Confirmar identidade, contas, dívidas, licenças e condições antes de negociar.",
        "status": "Fonte de terceiros; não verificada"
    }
]


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
                    "date": quote.get("date", ""),
                    "source": quote.get("source", "Alpha Vantage"),
                    "source_url": quote.get("source_url", ""),
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
                    "date": vix.get("date", ""),
                    "source": vix.get("source", "FRED"),
                    "source_url": vix.get("source_url", ""),
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


def update_alert_history(
    previous: list[dict[str, Any]] | None,
    alerts: list[dict[str, Any]],
    today: date | None = None,
) -> list[dict[str, Any]]:
    today = today or date.today()
    snapshots: dict[str, dict[str, Any]] = {}
    for item in previous or []:
        if isinstance(item, dict) and item.get("event_id"):
            snapshots[str(item["event_id"])] = item
    for alert in alerts:
        event_date = str(alert.get("date") or today.isoformat())[:10]
        event_id = f"{alert['id']}:{event_date}"
        snapshots.setdefault(
            event_id,
            {
                **alert,
                "event_id": event_id,
                "date": event_date,
                "first_seen": today.isoformat(),
            },
        )
    cutoff = today - timedelta(days=180)
    history = [
        item for item in snapshots.values()
        if _safe_date(item.get("date")) >= cutoff
    ]
    history.sort(key=lambda item: item.get("date", ""), reverse=True)
    return history[:300]


def _load_alert_history() -> list[dict[str, Any]]:
    try:
        loaded = json.loads((DATA_DIR / "alert_history.json").read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, list) else []
    except (OSError, json.JSONDecodeError, TypeError):
        return []


def score_opportunity(
    opportunity: dict[str, Any], today: date | None = None
) -> dict[str, Any]:
    """Score investigation priority from known evidence, never success odds."""
    today = today or date.today()
    deadline = date.fromisoformat(opportunity["deadline"])
    days_left = (deadline - today).days
    timing_points = 5 if days_left <= 7 else 4 if days_left <= 30 else 3 if days_left <= 90 else 2
    criteria = [
        {
            "id": "compatibility",
            "label": "Compatibilidade com os interesses indicados",
            "weight": 20,
            "points": opportunity.get("fit_points"),
            "basis": "Regra editorial: tecnologia, empreendedorismo em Portugal e baixo investimento inicial."
        },
        {
            "id": "demand",
            "label": "Evidência de procura de mercado",
            "weight": 20,
            "points": None,
            "basis": "Não foi encontrada evidência de procura de clientes no aviso."
        },
        {
            "id": "capital",
            "label": "Capital inicial e investimento",
            "weight": 15,
            "points": None,
            "basis": "O aviso não permite estimar capital total de arranque."
        },
        {
            "id": "complexity",
            "label": "Complexidade de execução",
            "weight": 10,
            "points": None,
            "basis": "A complexidade do projeto depende do caso concreto."
        },
        {
            "id": "competition",
            "label": "Concorrência",
            "weight": 10,
            "points": None,
            "basis": "Não foi feita análise de concorrentes."
        },
        {
            "id": "scalability",
            "label": "Escalabilidade",
            "weight": 10,
            "points": None,
            "basis": "O potencial de escala não é descrito pelo aviso."
        },
        {
            "id": "source",
            "label": "Qualidade e verificabilidade da fonte",
            "weight": 10,
            "points": 10,
            "basis": "Fonte primária oficial com título, data e prazo publicados."
        },
        {
            "id": "timing",
            "label": "Prazo e oportunidade temporal",
            "weight": 5,
            "points": timing_points,
            "basis": f"{days_left} dias até ao prazo indicado; confirmar no anúncio original."
        }
    ]
    known_weight = sum(row["weight"] for row in criteria if row["points"] is not None)
    score = sum(
        row["points"] if row["points"] is not None else 0
        for row in criteria
    )
    return {
        **opportunity,
        "score": score,
        "score_label": "Prioridade de investigação",
        "score_confidence": round(known_weight),
        "score_criteria": criteria,
        "days_until_deadline": days_left,
        "status": "Aberto" if days_left >= 0 else "Encerrado"
    }


def current_opportunities(today: date | None = None) -> list[dict[str, Any]]:
    today = today or date.today()
    opportunities = []
    for source in CURATED_OPPORTUNITIES:
        if date.fromisoformat(source["deadline"]) < today:
            continue
        opportunities.append(score_opportunity(copy.deepcopy(source), today))
    return sorted(
        opportunities,
        key=lambda item: (item["score"], -item["days_until_deadline"]),
        reverse=True,
    )


def build_recommendations(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recommendations = []
    for opportunity in opportunities[:3]:
        recommendations.append(
            {
                "id": f"{opportunity['id']}:{opportunity['source_checked_at']}",
                "category": opportunity["category"],
                "title": f"Confirmar elegibilidade: {opportunity['title']}",
                "event": opportunity["description"],
                "why": opportunity["why_it_matters"],
                "risk": opportunity["risks"],
                "action": opportunity["next_steps"][0],
                "source": opportunity["source"],
                "source_url": opportunity["source_url"],
                "date": opportunity["published_at"],
                "deadline": opportunity["deadline"],
                "score": opportunity["score"],
                "score_confidence": opportunity["score_confidence"],
                "opportunity_id": opportunity["id"],
                "basis": "Regra transparente sobre uma oportunidade pública, revista manualmente; sem modelo de IA."
            }
        )
    return recommendations


def update_recommendation_history(
    previous: list[dict[str, Any]] | None,
    recommendations: list[dict[str, Any]],
    today: date | None = None,
) -> list[dict[str, Any]]:
    today = today or date.today()
    snapshots: dict[str, dict[str, Any]] = {}
    for item in previous or []:
        if isinstance(item, dict) and item.get("id"):
            snapshots[str(item["id"])] = item
    for recommendation in recommendations:
        identifier = recommendation["id"]
        if identifier not in snapshots:
            snapshots[identifier] = {
                **recommendation,
                "first_seen": today.isoformat(),
                "last_seen": today.isoformat()
            }
        else:
            snapshots[identifier]["last_seen"] = today.isoformat()
    cutoff = today - timedelta(days=180)
    retained = [
        item for item in snapshots.values()
        if _safe_date(item.get("last_seen") or item.get("date")) >= cutoff
    ]
    retained.sort(key=lambda item: item.get("first_seen", ""), reverse=True)
    return retained[:300]


def _safe_date(value: Any) -> date:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return date.min


def _load_recommendation_history() -> list[dict[str, Any]]:
    try:
        loaded = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        return loaded if isinstance(loaded, list) else []
    except (OSError, json.JSONDecodeError, TypeError):
        return []


def build_payload(
    quotes: list[dict[str, Any]],
    macro: list[dict[str, Any]],
    portugal: list[dict[str, Any]],
    research: list[dict[str, Any]],
    previous_alert_ids: set[str] | None = None,
    ntfy_topic: str | None = None,
    previous_history: list[dict[str, Any]] | None = None,
    today: date | None = None,
    previous_alert_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    today = today or date.today()
    alerts = make_alerts(quotes, macro)
    previous = previous_alert_ids or set()
    new_alerts = [alert for alert in alerts if alert["id"] not in previous]
    if ntfy_topic and new_alerts:
        send_alert_notifications(ntfy_topic, new_alerts)
    opportunities = current_opportunities(today)
    recommendations = build_recommendations(opportunities)
    old_history = previous_history or []
    known_ids = {item.get("id") for item in old_history if isinstance(item, dict)}
    recommendation_history = update_recommendation_history(
        old_history, recommendations, today
    )
    alert_history = update_alert_history(previous_alert_history, alerts, today)
    new_recommendation_ids = [
        item["id"] for item in recommendations if item["id"] not in known_ids
    ]
    if new_recommendation_ids:
        briefing_title = "Novos sinais concretos para investigar"
        briefing_detail = (
            f"{len(new_recommendation_ids)} recomendação(ões) nova(s); "
            f"{len(recommendations) - len(new_recommendation_ids)} continuam em acompanhamento. "
            "Cada sinal inclui fonte, prazo e limitações."
        )
    elif recommendations:
        briefing_title = "Sem sinal novo; oportunidades em acompanhamento"
        briefing_detail = (
            f"As {len(recommendations)} recomendações atuais já foram vistas. "
            "Os prazos e as fontes continuam disponíveis para validação."
        )
    else:
        briefing_title = "Sem novidade fundamentada nesta atualização"
        briefing_detail = (
            "Não há recomendações qualificadas nos dados disponíveis. "
            "Consulta as fontes originais antes de concluir que não existem oportunidades."
        )
    return {
        "schema_version": 3,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "quotes": quotes,
        "macro": macro,
        "portugal": portugal,
        "research": research,
        "alerts": alerts,
        "insights": generate_insights(quotes, portugal),
        "opportunities": opportunities,
        "opportunity_sources": OPPORTUNITY_SOURCES,
        "opportunity_source_mode": {
            "type": "curated_snapshot",
            "checked_at": OPPORTUNITY_CHECKED_AT,
            "notice": "Oportunidades consultadas manualmente em fonte oficial; expiram pelo prazo publicado. A sincronização automática dos avisos está pendente."
        },
        "recommendations": recommendations,
        "new_recommendation_ids": new_recommendation_ids,
        "recommendation_history": recommendation_history,
        "alert_history": alert_history,
        "briefing": {
            "title": briefing_title,
            "detail": briefing_detail
        },
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
    previous_history = _load_recommendation_history()
    previous_alert_history = _load_alert_history()
    payload = build_payload(
        quotes, macro, portugal, research, previous, ntfy_topic,
        previous_history=previous_history,
        previous_alert_history=previous_alert_history,
    )

    STATE_PATH.write_text(
        json.dumps([alert["id"] for alert in payload["alerts"]], indent=2) + "\n",
        encoding="utf-8",
    )
    HISTORY_PATH.write_text(
        json.dumps(payload["recommendation_history"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (DATA_DIR / "alert_history.json").write_text(
        json.dumps(payload["alert_history"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "Dashboard gerado: "
        f"{len(quotes)} séries de mercado, {len(macro)} séries FRED, "
        f"{len(portugal)} indicadores de Portugal, {len(research)} artigos, "
        f"{len(payload['alerts'])} alertas ativos, "
        f"{len(payload['opportunities'])} oportunidades públicas em prazo."
    )


if __name__ == "__main__":
    main()
