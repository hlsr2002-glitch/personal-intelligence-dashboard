#!/usr/bin/env python3
"""Gera as páginas HTML independentes do Personal Intelligence Hub."""

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
ASSETS = DOCS / "assets"

PAGES = [
    ("index.html", "home", "Início", "Briefing diário com oportunidades e sinais verificados."),
    ("opportunities.html", "opportunities", "Oportunidades", "Avisos, concursos e ideias para investigar em Portugal."),
    ("advisor.html", "advisor", "Conselheiro", "Recomendações fundamentadas, limitações e histórico."),
    ("trends.html", "trends", "Tendências", "Mudanças tecnológicas e sinais para acompanhar."),
    ("knowledge.html", "knowledge", "Conhecimento", "Artigos de investigação com resumo e fonte original."),
    ("economy.html", "economy", "Economia", "Indicadores de Portugal, mercados e contexto global."),
    ("projects.html", "projects", "Projetos", "Espaço de trabalho temporário, sem guardar dados pessoais."),
    ("alerts.html", "alerts", "Alertas", "Estado, regras e histórico das notificações."),
]

ICON = """<svg class="brand-mark" viewBox="0 0 40 40" aria-hidden="true">
<circle cx="20" cy="20" r="15.5" fill="none" stroke="#88aaff" stroke-width="1.6"/>
<circle cx="20" cy="20" r="6" fill="#58dbc4"/><path d="M20 3v7M37 20h-7M20 37v-7M3 20h7" stroke="#7888a5" stroke-width="1.2"/>
</svg>"""


def render_page(current_id: str, title: str, description: str) -> str:
    asset_version = hashlib.sha256((ASSETS / "hub.js").read_bytes()).hexdigest()[:12]
    links = []
    for filename, page_id, label, _ in PAGES:
        current = ' aria-current="page"' if page_id == current_id else ""
        links.append(
            f'<a class="nav-link" href="{filename}" data-route="{page_id}"{current}>'
            f'<span class="nav-icon" aria-hidden="true">{nav_icon(page_id)}</span>'
            f'<span>{label}</span></a>'
        )
    navigation = "\n".join(links)
    return f"""<!doctype html>
<html lang="pt-PT">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#0c1018">
  <meta name="description" content="{description}">
  <title>{title} · Personal Intelligence Hub</title>
  <link rel="stylesheet" href="assets/hub.css">
  <script defer src="assets/hub.js?v={asset_version}"></script>
</head>
<body data-page="{current_id}">
  <a class="skip-link" href="#main">Saltar para o conteúdo principal</a>
  <div class="app-shell">
    <aside class="sidebar">
      <a class="brand" href="index.html" data-route="home">
        {ICON}
        <span class="brand-text"><strong>PERSONAL</strong><span>INTELLIGENCE HUB</span></span>
      </a>
      <div class="workspace-label">ESPAÇO PESSOAL <span aria-hidden="true">·</span> PÚBLICO</div>
      <nav class="side-nav" aria-label="Navegação principal">
        {navigation}
      </nav>
      <div class="sidebar-bottom">
        <div class="source-status"><span class="pulse" aria-hidden="true"></span><span id="source-status">A carregar fontes públicas</span></div>
        <div class="sidebar-note">Sinais fundamentados.<br>Decisões continuam a ser tuas.</div>
        <a class="sidebar-help" href="https://github.com/hlsr2002-glitch/personal-intelligence-dashboard/blob/main/personal-intelligence-dashboard/README.md" target="_blank" rel="noopener noreferrer">Como funciona <span aria-hidden="true">↗</span></a>
      </div>
    </aside>
    <div class="main-column">
      <header class="topbar">
        <div class="mobile-brand">{ICON}<span>INTELLIGENCE HUB</span></div>
        <div class="breadcrumbs"><span>PAINEL</span><b aria-hidden="true">/</b><strong id="crumb-title">{title}</strong></div>
        <div class="topbar-meta"><span class="topbar-date" id="updated-label">A sincronizar…</span><span class="avatar" aria-label="Perfil privado não configurado">H</span></div>
      </header>
      <nav class="mobile-nav" aria-label="Navegação principal">
        {navigation}
      </nav>
      <main id="main" class="page-main" tabindex="-1">
        <div class="loading-state" role="status"><span class="spinner" aria-hidden="true"></span>A preparar o painel…</div>
      </main>
      <footer class="page-footer">
        <span>PERSONAL INTELLIGENCE HUB <b>·</b> PROTÓTIPO PÚBLICO</span>
        <span>Fontes originais e limitações junto a cada sinal.</span>
      </footer>
    </div>
  </div>
</body>
</html>
"""


def nav_icon(page_id: str) -> str:
    icons = {
        "home": "◈",
        "opportunities": "✳",
        "advisor": "⌁",
        "trends": "↗",
        "knowledge": "⌘",
        "economy": "◷",
        "projects": "◇",
        "alerts": "◎",
    }
    return icons[page_id]


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    for filename, page_id, title, description in PAGES:
        (DOCS / filename).write_text(
            render_page(page_id, title, description), encoding="utf-8"
        )
    print(f"Geradas {len(PAGES)} páginas independentes.")


if __name__ == "__main__":
    main()
