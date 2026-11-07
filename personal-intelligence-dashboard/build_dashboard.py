#!/usr/bin/env python3
"""Recolhe indicadores públicos e gera um dashboard estático em docs/."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.example.json"
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
STATE_PATH = DATA_DIR / "active_alerts.json"
OUTPUT_PATH = DOCS_DIR / "data.json"
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def fetch_json(url: str, *, timeout: int = 20) -> dict[str, Any] | None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PersonalIntelligenceDashboard/1.0 (personal prototype)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload if isinstance(payload, dict) else None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def collect_quotes(api_key: str | None) -> list[dict[str, Any]]:
    if not api_key:
        return []
    results: list[dict[str, Any]] = []
    for index, asset in enumerate(CONFIG["assets"]):
        if index:
            time.sleep(13)  # Respeita o limite típico de pedidos da chave gratuita.
        query = urllib.parse.urlencode(
            {"function": "GLOBAL_QUOTE", "symbol": asset["symbol"], "apikey": api_key}
        )
        payload = fetch_json(f"https://www.alphavantage.co/query?{query}")
        quote = (payload or {}).get("Global Quote", {})
        try:
            price = float(quote["05. price"])
            change_pct = float(quote["10. change percent"].strip(" %"))
            results.append(
                {
                    "symbol": asset["symbol"],
                    "name": asset["name"],
                    "price": price,
                    "change_pct": change_pct,
                    "date": quote.get("07. latest trading day", ""),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return results


def collect_macro(api_key: str | None) -> list[dict[str, Any]]:
    if not api_key:
        return []
    observations: list[dict[str, Any]] = []
    for series in CONFIG["macro_series"]:
        query = urllib.parse.urlencode(
            {
                "series_id": series["id"],
                "api_key": api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": "1",
            }
        )
        payload = fetch_json(f"https://api.stlouisfed.org/fred/series/observations?{query}")
        rows = (payload or {}).get("observations", [])
        if not rows:
            continue
        row = rows[0]
        value = row.get("value")
        if not value or value == ".":
            continue
        try:
            observations.append(
                {
                    "id": series["id"],
                    "name": series["name"],
                    "unit": series["unit"],
                    "value": float(value),
                    "date": row.get("date", ""),
                }
            )
        except (TypeError, ValueError):
            continue
    return observations


def collect_research() -> list[dict[str, Any]]:
    start_date = (date.today() - timedelta(days=30)).isoformat()
    query = urllib.parse.urlencode(
        {
            "search": CONFIG["research_topics"],
            "filter": f"from_publication_date:{start_date}",
            "sort": "publication_date:desc",
            "per-page": "8",
            "select": "id,title,publication_date,doi,primary_location,cited_by_count,open_access",
        }
    )
    payload = fetch_json(f"https://api.openalex.org/works?{query}")
    works = (payload or {}).get("results", [])
    results: list[dict[str, Any]] = []
    for work in works:
        location = work.get("primary_location") or {}
        source = location.get("source") or {}
        results.append(
            {
                "title": work.get("title") or "Título indisponível",
                "date": work.get("publication_date", ""),
                "url": (location.get("landing_page_url") or work.get("doi") or ""),
                "source": source.get("display_name", "OpenAlex"),
                "citations": work.get("cited_by_count", 0),
                "open_access": bool((work.get("open_access") or {}).get("is_oa")),
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


def send_notifications(new_alerts: list[dict[str, str]], topic: str | None) -> None:
    if not topic:
        return
    for alert in new_alerts:
        request = urllib.request.Request(
            f"https://ntfy.sh/{urllib.parse.quote(topic, safe='')}",
            data=f"{alert['title']}\n{alert['detail']}".encode("utf-8"),
            headers={"Title": "Personal Intelligence Dashboard", "Priority": "high"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20):
                pass
        except (urllib.error.URLError, TimeoutError):
            continue


def render_html() -> str:
    return '''<!doctype html>
<html lang="pt-PT"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#101a2a"><title>Personal Intelligence</title>
<style>
:root{color-scheme:dark;--bg:#101a2a;--panel:#19263a;--line:#2c3d55;--muted:#aab8ca;--ink:#f2f6fb;--teal:#75e1c2;--gold:#f1c777;--red:#ff9b91}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top right,#21344b 0,transparent 42%),var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{max-width:1120px;margin:auto;padding:36px 22px 64px}.top{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;margin-bottom:28px}.eyebrow{color:var(--teal);text-transform:uppercase;letter-spacing:.15em;font-size:11px;font-weight:700}h1{font-size:clamp(30px,5vw,48px);line-height:1.08;margin:8px 0}h2{font-size:19px;margin:0}.sub,.muted{color:var(--muted)}.status{border:1px solid var(--line);border-radius:999px;padding:8px 12px;color:var(--teal);white-space:nowrap;font-size:13px}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.panel{background:linear-gradient(150deg,#1c2a3e,#172337);border:1px solid var(--line);border-radius:18px;padding:20px;box-shadow:0 10px 34px #07101c40}.wide{grid-column:span 2}.full{grid-column:1/-1}.panel-head{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:15px}.badge{font-size:11px;color:var(--muted);border:1px solid var(--line);border-radius:999px;padding:4px 8px}.metric{font-size:27px;font-weight:650;margin:8px 0 2px}.small{font-size:12px;color:var(--muted)}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px}.tile{padding:12px;border:1px solid var(--line);border-radius:13px;background:#111c2c80}.positive{color:var(--teal)}.negative{color:var(--red)}.table{width:100%;border-collapse:collapse}.table th,.table td{text-align:left;padding:11px 8px;border-bottom:1px solid var(--line);vertical-align:top}.table th{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}a{color:var(--teal);text-decoration:none}a:hover{text-decoration:underline}.empty{padding:16px;border:1px dashed #42536a;border-radius:12px;color:var(--muted)}.alert{border-left:3px solid var(--red);padding:11px 13px;background:#351f2a;border-radius:0 12px 12px 0;margin:9px 0}.alert strong{display:block}.foot{margin-top:20px;color:var(--muted);font-size:12px}
@media(max-width:760px){main{padding:24px 15px 42px}.top{display:block}.status{display:inline-block;margin-top:8px}.grid{grid-template-columns:1fr}.wide,.full{grid-column:auto}.table th,.table td{padding:8px 5px;font-size:13px}.table th{font-size:10px}}
</style></head><body><main>
<header class="top"><div><div class="eyebrow">Centro de informação e análise</div><h1>Personal Intelligence</h1><div class="sub">Mercados, economia e conhecimento — com alertas equilibrados.</div></div><div class="status" id="updated">A carregar…</div></header>
<section class="grid">
<article class="panel wide"><div class="panel-head"><h2>Mercados</h2><span class="badge">Fontes: Alpha Vantage</span></div><div id="markets" class="cards"></div></article>
<article class="panel"><div class="panel-head"><h2>Macroeconomia</h2><span class="badge">FRED</span></div><div id="macro"></div></article>
<article class="panel"><div class="panel-head"><h2>Alertas</h2><span class="badge">Equilibrado</span></div><div id="alerts"></div></article>
<article class="panel wide"><div class="panel-head"><h2>Investigação recente</h2><span class="badge">OpenAlex · últimos 30 dias</span></div><div id="research"></div></article>
<article class="panel full"><div class="small">Protótipo informativo. Dados sujeitos a atraso, limites e disponibilidade das fontes. Não constitui aconselhamento financeiro.</div></article>
</section><footer class="foot">Atualização automática preparada no GitHub Actions. A publicação web permanece desativada até ser configurada.</footer></main>
<script>
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const safeUrl=u=>/^https:\/\/[^\s]+$/i.test(String(u??""))?String(u):"";
const empty=t=>`<div class="empty">${esc(t)}</div>`;
fetch("data.json",{cache:"no-store"}).then(r=>{if(!r.ok)throw Error();return r.json()}).then(d=>{
 document.querySelector("#updated").textContent=d.updated_at?`Atualizado ${new Date(d.updated_at).toLocaleString("pt-PT")}`:"Sem atualização";
 const markets=document.querySelector("#markets"); markets.innerHTML=d.quotes?.length?d.quotes.map(q=>`<div class="tile"><div class="small">${esc(q.name)}</div><div class="metric">${Number(q.price).toLocaleString("pt-PT",{maximumFractionDigits:2})}</div><div class="${q.change_pct<0?"negative":"positive"}">${q.change_pct>0?"+":""}${Number(q.change_pct).toFixed(2)}% <span class="small">${esc(q.date)}</span></div></div>`).join(""):empty("Configure ALPHA_VANTAGE_API_KEY para carregar cotações.");
 const macro=document.querySelector("#macro"); macro.innerHTML=d.macro?.length?d.macro.map(m=>`<div class="tile" style="margin-bottom:9px"><div class="small">${esc(m.name)}</div><strong>${Number(m.value).toLocaleString("pt-PT",{maximumFractionDigits:2})} ${esc(m.unit)}</strong><div class="small">${esc(m.date)}</div></div>`).join(""):empty("Configure FRED_API_KEY para carregar indicadores.");
 const alerts=document.querySelector("#alerts"); alerts.innerHTML=d.alerts?.length?d.alerts.map(a=>`<div class="alert"><strong>${esc(a.title)}</strong><span class="small">${esc(a.detail)}</span></div>`).join(""):empty("Sem alertas críticos neste momento. Quedas inferiores a 5% e oscilações normais não geram notificação.");
 const research=document.querySelector("#research"); research.innerHTML=d.research?.length?`<table class="table"><thead><tr><th>Publicação</th><th>Data</th><th>Fonte</th><th>Acesso</th></tr></thead><tbody>${d.research.map(p=>{const url=safeUrl(p.url);return `<tr><td>${url?`<a href="${esc(url)}" target="_blank" rel="noopener">${esc(p.title)}</a>`:esc(p.title)}</td><td>${esc(p.date)}</td><td>${esc(p.source)}</td><td>${p.open_access?"Aberto":"Verificar"}</td></tr>`}).join("")}</tbody></table>`:empty("Não foi possível obter publicações recentes nesta execução.");
}).catch(()=>{document.querySelector("#updated").textContent="Dados ainda não gerados";document.querySelector("#markets").innerHTML=empty("Execute build_dashboard.py ou o workflow para iniciar o dashboard.");document.querySelector("#macro").innerHTML=empty("À espera da primeira recolha.");document.querySelector("#alerts").innerHTML=empty("À espera da primeira recolha.");document.querySelector("#research").innerHTML=empty("À espera da primeira recolha.");});
</script></body></html>'''


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    quotes = collect_quotes(os.environ.get("ALPHA_VANTAGE_API_KEY"))
    macro = collect_macro(os.environ.get("FRED_API_KEY"))
    research = collect_research()
    alerts = make_alerts(quotes, macro)
    previous = set()
    try:
        previous = set(json.loads(STATE_PATH.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    new_alerts = [alert for alert in alerts if alert["id"] not in previous]
    send_notifications(new_alerts, os.environ.get("NTFY_TOPIC"))
    STATE_PATH.write_text(json.dumps([alert["id"] for alert in alerts], indent=2) + "\n", encoding="utf-8")
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "quotes": quotes,
        "macro": macro,
        "research": research,
        "alerts": alerts,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (DOCS_DIR / "index.html").write_text(render_html(), encoding="utf-8")
    print(f"Dashboard gerado: {len(quotes)} cotações, {len(macro)} indicadores, {len(research)} publicações, {len(new_alerts)} alertas novos.")


if __name__ == "__main__":
    main()
