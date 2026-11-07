(function () {
  "use strict";

  var TITLES = {
    home: "Início",
    opportunities: "Oportunidades",
    advisor: "Conselheiro",
    trends: "Tendências",
    knowledge: "Conhecimento",
    economy: "Economia",
    projects: "Projetos",
    alerts: "Alertas"
  };
  var PATHS = {
    home: "index.html",
    opportunities: "opportunities.html",
    advisor: "advisor.html",
    trends: "trends.html",
    knowledge: "knowledge.html",
    economy: "economy.html",
    projects: "projects.html",
    alerts: "alerts.html"
  };
  var state = {
    page: document.body.getAttribute("data-page") || "home",
    data: null,
    projects: [],
    watchlist: [],
    filters: {},
    chartRange: {},
    message: ""
  };
  var main = document.getElementById("main");
  var lastModalTrigger = null;

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (char) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char];
    });
  }
  function safeUrl(value) {
    try {
      var url = new URL(value);
      return url.protocol === "https:" ? url.href : "";
    } catch (error) {
      return "";
    }
  }
  function records(value) { return Array.isArray(value) ? value : []; }
  function fmt(value, digits) {
    var n = Number(value);
    if (!Number.isFinite(n)) return "—";
    return new Intl.NumberFormat("pt-PT", {
      minimumFractionDigits: digits == null ? 1 : digits,
      maximumFractionDigits: digits == null ? 1 : digits
    }).format(n);
  }
  function dateLabel(value) {
    if (!value) return "data não indicada";
    var q = String(value).match(/^(\d{4})-Q([1-4])$/);
    if (q) return "T" + q[2] + " " + q[1];
    var raw = String(value);
    var dt = new Date(raw.length === 7 ? raw + "-01T00:00:00Z" : raw);
    if (Number.isNaN(dt.valueOf())) return raw;
    return new Intl.DateTimeFormat("pt-PT", {
      year: "numeric", month: "short",
      day: raw.length > 7 ? "2-digit" : undefined,
      timeZone: "UTC"
    }).format(dt);
  }
  function dateValue(value) {
    var q = String(value || "").match(/^(\d{4})-Q([1-4])$/);
    if (q) return Date.UTC(Number(q[1]), (Number(q[2]) - 1) * 3, 1);
    return Date.parse(String(value || "").length === 7 ? value + "-01T00:00:00Z" : value);
  }
  function updatedLabel(value) {
    if (!value) return "Atualização indisponível";
    var dt = new Date(value);
    if (Number.isNaN(dt.valueOf())) return "Atualização indisponível";
    return "Atualizado " + new Intl.DateTimeFormat("pt-PT", {
      dateStyle: "medium", timeStyle: "short"
    }).format(dt);
  }
  function sourceLink(name, url, label) {
    var href = safeUrl(url);
    if (!href) return '<span class="article-meta">' + esc(name || "Fonte não indicada") + "</span>";
    return '<a class="source-link" href="' + esc(href) + '" target="_blank" rel="noopener noreferrer">' +
      esc(label || ("Fonte: " + (name || "original"))) + ' ↗</a>';
  }
  function pageHead(eyebrow, title, lede, extra) {
    return '<div class="page-head"><div><div class="eyebrow">' + esc(eyebrow) + "</div><h1>" +
      esc(title) + '</h1><p class="page-lede">' + esc(lede) + "</p></div>" +
      (extra || "") + "</div>";
  }
  function sectionHead(index, title, description, right) {
    return '<div class="section-heading"><div class="section-title-wrap"><span class="section-index">' +
      esc(index) + '</span><h2>' + esc(title) + "</h2></div><p>" + esc(description) +
      (right || "") + "</p></div>";
  }
  function empty(title, detail) {
    return '<div class="empty-state"><div><strong>' + esc(title) + "</strong><p>" +
      esc(detail) + "</p></div></div>";
  }
  function tag(text, color) {
    return '<span class="tag' + (color ? " tag-" + color : "") + '">' + esc(text) + "</span>";
  }
  function notice(title, body, warning) {
    return '<div class="' + (warning ? "warning-banner" : "quiet-banner") +
      '" role="note"><span class="banner-icon" aria-hidden="true">' +
      (warning ? "!" : "✳") + "</span><span><strong>" + esc(title) + "</strong> " +
      esc(body) + "</span></div>";
  }
  function sourceList(items) {
    return '<div class="grid grid-3">' + items.map(function (item) {
      return '<article class="card source-card"><div class="opportunity-badges">' +
        tag(item.category, "blue") + tag(item.status, item.status.indexOf("terceiros") >= 0 ? "amber" : "") +
        '</div><h3>' + esc(item.name) + '</h3><p>' + esc(item.description) + "</p>" +
        sourceLink(item.name, item.url, "Abrir fonte") + "</article>";
    }).join("") + "</div>";
  }
  function metricCard(name, value, detail, date, color, description) {
    return '<article class="card"><div class="card-kicker">' + esc(name) + '</div><div class="metric-value">' +
      esc(value) + '</div><div class="metric-foot"><span class="' + (color || "") + '">' +
      esc(detail) + "</span><span>" + esc(dateLabel(date)) + "</span></div>" +
      (description ? '<p class="metric-note">' + esc(description) + "</p>" : "") + "</article>";
  }
  function historyRows(items, filterCategory, filterSince) {
    var list = records(items).filter(function (item) {
      return (!filterCategory || item.category === filterCategory) &&
        (!filterSince || String(item.first_seen || item.date || "") >= filterSince);
    });
    if (!list.length) return empty("Ainda sem histórico guardado", "As recomendações públicas ficam registadas quando o fluxo diário as encontra. Não há notas pessoais nesta área.");
    return '<div class="timeline">' + list.map(function (item) {
      return '<article class="timeline-item"><div class="timeline-date">' +
        esc(dateLabel(item.first_seen || item.date)) + '</div><span class="timeline-dot" aria-hidden="true"></span>' +
        '<div class="timeline-body"><h3>' + esc(item.title) + "</h3><p>" +
        esc(item.why || item.event || item.description || "") + "</p><div class=\"tag-row\">" +
        tag(item.category || "Sinal público") + sourceLink(item.source, item.source_url, "Fonte original") +
        "</div></div></article>";
    }).join("") + "</div>";
  }

  function renderHome() {
    var data = state.data;
    var recs = records(data.recommendations);
    var opportunities = records(data.opportunities);
    var portugal = records(data.portugal);
    var alerts = records(data.alerts);
    var research = records(data.research);
    var title = data.briefing && data.briefing.title || "Sem novidade fundamentada nesta atualização";
    var detail = data.briefing && data.briefing.detail || "Não há recomendações qualificadas nos dados disponíveis.";
    var recMarkup = recs.length ? '<div class="grid">' + recs.slice(0, 2).map(recommendationCard).join("") + "</div>" :
      empty("Sem recomendação de decisão hoje", "Não há um sinal público qualificado nos dados atuais. Usa as fontes originais abaixo para procurar oportunidades abertas.");
    var keyData = [
      metricCard("Oportunidades com prazo ativo", opportunities.length, "amostra pública", data.opportunity_source_mode && data.opportunity_source_mode.checked_at, "positive", "Amostra manual de avisos oficiais; confirma sempre o estado na fonte."),
      metricCard("Indicadores de Portugal", portugal.length, "séries Eurostat", data.updated_at, "", "As frequências de publicação variam entre indicadores."),
      metricCard("Artigos com resumo", research.length, "registos OpenAlex", data.updated_at, "", "Resumo automático do abstract; não substitui a leitura do estudo."),
      metricCard("Alertas ativos", alerts.length, "limiares seletivos", data.updated_at, alerts.length ? "negative" : "", "Sem alertas não significa ausência de risco.")
    ].join("");
    var marketItems = records(data.quotes);
    var marketPreview = marketItems.length ? '<div class="grid grid-3">' + marketItems.slice(0, 3).map(function (item) {
      var change = Number(item.change_pct);
      var direction = change > 0 ? "positive" : change < 0 ? "negative" : "";
      return metricCard(item.name || item.symbol, fmt(item.price, 2) + " " + (item.currency || "USD"),
        (change > 0 ? "+" : "") + fmt(change, 2) + "% no último fecho", item.date, direction,
        "Preço indicativo em USD; ETF usado como referência, não ativo recomendado.");
    }).join("") + "</div>" : empty("Dados de mercado sem atualização", "Verifica na área Economia quando o último fluxo tiver executado. As chaves e a fonte original controlam a disponibilidade.");
    var checked = data.opportunity_source_mode && data.opportunity_source_mode.checked_at;
    return '<section class="hero"><div class="hero-content"><div class="eyebrow">Briefing · Portugal e mundo</div>' +
      '<h1>Menos ruído.<br>Mais contexto.</h1><p>Oportunidades, dados e investigação organizados para ajudar a decidir o que merece atenção — com a fonte e a incerteza à vista.</p>' +
      '<a class="hero-link" href="opportunities.html" data-route="opportunities">Explorar o radar <span aria-hidden="true">→</span></a></div>' +
      '<aside class="hero-aside"><div class="label">ESTADO DO BRIEFING</div><div class="hero-stat"><strong>' +
      esc(recs.length) + '</strong><span>recomendações em vigor</span></div><p>' + esc(detail) + '</p><div class="tag-row" style="margin-top:12px">' +
      tag("Regras transparentes", "green") + tag("Sem modelo de IA", "blue") + "</div></aside></section>" +
      '<section class="section"><div class="card briefing-card"><div class="briefing-icon" aria-hidden="true">✳</div><div><div class="card-kicker">LEITURA DE HOJE</div><h3>' +
      esc(title) + '</h3><p>' + esc(detail) + "</p></div><span class=\"briefing-arrow\" aria-hidden=\"true\">↗</span></div></section>" +
      '<section class="section">' + sectionHead("01", "Sinais que merecem atenção", "Cada recomendação aponta o acontecimento, a fonte, a ação e as limitações.") + recMarkup + "</section>" +
      '<section class="section">' + sectionHead("02", "Estado do painel", "Um resumo das fontes já processadas nesta atualização.") +
      '<div class="grid grid-4">' + keyData + "</div></section>" +
      '<section class="section">' + sectionHead("03", "Mercados em contexto", "Preços recentes de ETFs de referência. Oscilações normais não geram notificações.") + marketPreview + "</section>" +
      '<section class="section">' + sectionHead("04", "O que está operacional", "A base pública funciona; alguns serviços pessoais aguardam armazenamento privado.") +
      '<div class="grid grid-3">' +
      '<article class="card"><div class="card-kicker">RADAR</div><h3>Fontes oficiais e avisos</h3><p class="metric-note">Oportunidades atuais com fonte IAPMEI, data de verificação e prazo. A sincronização automática dos portais está pendente.</p><a class="hero-link" href="opportunities.html" data-route="opportunities">Abrir oportunidades →</a></article>' +
      '<article class="card"><div class="card-kicker">PRIVACIDADE</div><h3>Projetos só durante esta sessão</h3><p class="metric-note">A página estática é pública; notas e itens de acompanhamento não são enviados nem guardados.</p><a class="hero-link" href="projects.html" data-route="projects">Abrir espaço temporário →</a></article>' +
      '<article class="card"><div class="card-kicker">SAÚDE</div><h3>Integração reservada</h3><p class="metric-note">Não recolhe nem publica informação de saúde. Uma fase posterior precisará de autenticação e armazenamento privado.</p></article>' +
      "</div><p class=\"chart-note\">Fontes do radar verificadas manualmente em " + esc(dateLabel(checked)) + ". Atualização automática de avisos, autenticação privada e API de IA não estão configuradas.</p></section>";
  }

  function recommendationCard(item) {
    var isNew = records(state.data.new_recommendation_ids).indexOf(item.id) >= 0;
    return '<article class="card signal-card"><div class="signal-top"><div><div class="opportunity-badges">' +
      tag(item.category || "Oportunidade", "blue") + tag(isNew ? "Novo nesta execução" : "Em acompanhamento", isNew ? "green" : "") +
      tag("Prazo " + dateLabel(item.deadline), "amber") +
      '</div><h3>' + esc(item.title) + "</h3></div>" +
      '<div class="score-wrap"><div class="score-ring" style="--score:' + esc(item.score || 0) +
      '"><strong>' + esc(item.score || 0) + "</strong></div></div></div><p><strong>O que foi identificado:</strong> " +
      esc(item.event) + "</p><p><strong>Relevância:</strong> " + esc(item.why) +
      "</p><p><strong>Limitação:</strong> " + esc(item.risk) + '</p><div class="signal-meta"><span>Ação: ' +
      esc(item.action) + "</span>" + sourceLink(item.source, item.source_url, "Fonte original") + "</div></article>";
  }

  function opportunityCard(item) {
    var capital = item.capital_note || "Não indicado na fonte consultada.";
    var steps = records(item.next_steps).map(function (step) { return "<li>" + esc(step) + "</li>"; }).join("");
    var known = (Number(item.score_confidence) || 0) + "% dos pesos cobertos por informação disponível";
    return '<article class="card opportunity-card" data-opportunity="' + esc(item.id) + '" data-category="' +
      esc(item.category) + '" data-sector="' + esc(item.sector) + '" data-location="' + esc(item.location) +
      '" data-capital="' + (item.capital_required == null ? "unknown" : Number(item.capital_required) >= 200000 ? "high" : "known") + '">' +
      '<div class="opportunity-badges">' + tag(item.category, "blue") + tag(item.status, item.status === "Aberto" ? "green" : "amber") +
      tag(item.sector, "violet") + "</div><h3>" + esc(item.title) + '</h3><div class="signal-meta"><span>' +
      esc(item.location) + "</span><span>Publicado " + esc(dateLabel(item.published_at)) + "</span>" +
      "<span>Prazo " + esc(dateLabel(item.deadline)) + "</span></div><p>" + esc(item.description) + "</p>" +
      '<div class="opportunity-detail"><strong>A quem se destina</strong><p>' + esc(item.eligibility) + "</p></div>" +
      '<div class="opportunity-detail"><strong>Porque pode interessar</strong><p>' + esc(item.why_it_matters) + "</p></div>" +
      '<div class="opportunity-detail"><strong>Capital / despesa</strong><p>' + esc(capital) + "</p></div>" +
      '<div class="opportunity-detail"><strong>Potencial de mercado</strong><p>' + esc(item.market_potential) + "</p></div>" +
      '<div class="opportunity-detail"><strong>Riscos e limitações</strong><p>' + esc(item.risks) + "</p></div>" +
      '<div class="opportunity-detail"><strong>Próximos passos</strong><ul class="detail-list">' + steps + "</ul></div>" +
      '<div class="opportunity-actions"><div class="score-wrap"><div class="score-ring" style="--score:' +
      esc(item.score) + '"><strong>' + esc(item.score) + "</strong></div><div class=\"score-copy\"><strong>" +
      esc(item.score_label) + '</strong><span>' + esc(known) +
      '</span></div><button class="text-button" data-action="score" data-id="' + esc(item.id) +
      '" aria-label="Ver critérios da pontuação">Ver critérios</button></div><button class="button-secondary" data-action="watch" data-id="' +
      esc(item.id) + '">＋ Acompanhar nesta sessão</button></div><div class="article-links">' +
      tag("Revisto " + dateLabel(item.source_checked_at), "amber") + sourceLink(item.source, item.source_url, "Abrir fonte original") +
      "</div></article>";
  }

  function getFilteredOpportunities() {
    var all = records(state.data.opportunities);
    var f = state.filters.opportunities || {};
    return all.filter(function (item) {
      var search = String(f.search || "").toLowerCase().trim();
      var searchable = [item.title, item.description, item.category, item.sector, item.location, item.source].join(" ").toLowerCase();
      var capital = item.capital_required == null ? "unknown" : Number(item.capital_required) >= 200000 ? "high" : "known";
      return (!search || searchable.indexOf(search) >= 0) &&
        (!f.category || item.category === f.category) &&
        (!f.location || item.location.toLowerCase().indexOf(f.location.toLowerCase()) >= 0) &&
        (!f.sector || item.sector === f.sector) &&
        (!f.capital || f.capital === capital) &&
        (!f.relevance || Number(item.score || 0) >= Number(f.relevance));
    }).sort(function (a, b) {
      return f.sort === "deadline" ?
        String(a.deadline).localeCompare(String(b.deadline)) :
        (b.score || 0) - (a.score || 0);
    });
  }

  function renderOpportunities() {
    var data = state.data;
    var items = getFilteredOpportunities();
    var all = records(data.opportunities);
    var sourceMode = data.opportunity_source_mode || {};
    var categories = Array.from(new Set(all.map(function (item) { return item.category; })));
    var sectors = Array.from(new Set(all.map(function (item) { return item.sector; })));
    var locations = Array.from(new Set(all.map(function (item) { return item.location; })));
    var f = state.filters.opportunities || {};
    var select = function (id, label, values, selected) {
      return '<div class="filter-control"><label for="' + id + '">' + label + '</label><select id="' + id + '">' +
        '<option value="">Todas</option>' + values.map(function (v) {
          return '<option value="' + esc(v) + '"' + (selected === v ? " selected" : "") + ">" + esc(v) + "</option>";
        }).join("") + "</select></div>";
    };
    var filterMarkup = '<form class="filters" id="opportunity-filters"><div class="filter-control"><label for="opp-search">Pesquisa</label><input id="opp-search" name="search" value="' +
      esc(f.search || "") + '" placeholder="Título, setor ou fonte"></div>' +
      select("opp-category", "Categoria", categories, f.category) +
      select("opp-sector", "Setor", sectors, f.sector) +
      select("opp-location", "Localização", locations, f.location) +
      '<div class="filter-control"><label for="opp-capital">Capital publicado</label><select id="opp-capital"><option value="">Qualquer</option><option value="unknown"' +
      (f.capital === "unknown" ? " selected" : "") + '>Não indicado</option><option value="high"' +
      (f.capital === "high" ? " selected" : "") + '>Despesa ≥ 200 mil €</option><option value="known"' +
      (f.capital === "known" ? " selected" : "") + '>Outro valor publicado</option></select></div>' +
      '<div class="filter-control"><label for="opp-relevance">Relevância mínima</label><select id="opp-relevance"><option value="">Qualquer</option>' +
      [10, 20, 30, 40].map(function (score) {
        return '<option value="' + score + '"' + (String(f.relevance || "") === String(score) ? " selected" : "") + ">" + score + "+ pontos</option>";
      }).join("") + '</select></div><div class="filter-control"><label for="opp-sort">Ordenar</label><select id="opp-sort"><option value="score"' +
      (f.sort !== "deadline" ? " selected" : "") + '>Prioridade</option><option value="deadline"' +
      (f.sort === "deadline" ? " selected" : "") + '>Prazo mais próximo</option></select></div>' +
      '<button class="button" type="submit">Aplicar filtros</button><span class="filter-spacer"></span>' +
      '<span class="filter-count">' + items.length + " de " + all.length + " oportunidades ativas</span></form>";
    var cards = items.length ? '<div class="grid">' + items.map(opportunityCard).join("") + "</div>" :
      empty(all.length ? "Nenhuma oportunidade corresponde aos filtros" : "Não há avisos selecionados ativos nesta amostra",
        "A lista é curta e foi verificada manualmente. Consulta as páginas originais abaixo para novas publicações e confirma o estado antes de agir.");
    return pageHead("Descoberta · Portugal", "Oportunidades", "Avisos oficiais e concursos com prazos publicados. As hipóteses de negócio não são apresentadas como procura comprovada.") +
      notice("Estado da integração", sourceMode.notice || "A lista não está sincronizada automaticamente.", true) +
      '<section class="section"><div class="filters-intro">' + sectionHead("01", "Radar verificado", "Dados da fonte, data, prazo, elegibilidade, riscos e próximos passos estão visíveis em cada cartão.") +
      filterMarkup + '<div class="grid" style="margin-top:14px">' + cards + "</div></section>" +
      hypothesisCard(all) +
      '<section class="section">' + sectionHead("03", "Fontes para explorar", "Ligações diretas para portais oficiais e uma fonte de terceiros identificada como não verificada.") +
      sourceList(records(data.opportunity_sources)) + "</section>" +
      '<section class="section"><div class="card"><div class="card-kicker">COMO LER A PONTUAÇÃO</div><h3>Prioridade para investigar, não probabilidade de sucesso</h3><p class="metric-note">A pontuação soma apenas critérios suportados por evidência disponível. O que falta — procura, concorrência, escalabilidade, capital total e complexidade do teu caso — aparece como desconhecido e reduz a cobertura. Não é uma recomendação de investimento.</p></div></section>';
  }

  function hypothesisCard(opportunities) {
    var signal = opportunities.find(function (item) {
      return item.id === "alt2030-2026-24-economia-circular";
    });
    if (!signal) return "";
    return '<section class="section">' + sectionHead("02", "Hipótese para validar", "Uma ideia de serviço pode nascer de uma prioridade pública; isto não prova procura nem avalia concorrência.") +
      '<article class="card opportunity-card"><div class="opportunity-badges">' + tag("Hipótese de negócio", "violet") +
      tag("Alentejo", "blue") + tag("Não validada", "amber") + '</div><h3>Serviço digital de diagnóstico de água e circularidade para PME</h3>' +
      '<p><strong>Ideia:</strong> testar um serviço simples para ajudar pequenas empresas a identificar consumos de água e possibilidades de aproveitamento de subprodutos.</p>' +
      '<p><strong>Sinal observado:</strong> o aviso ALT2030-2026-24 inclui a circularidade e a otimização de água entre as áreas elegíveis. Isto revela uma prioridade de política pública, não procura comprovada de clientes.</p>' +
      '<div class="opportunity-detail"><strong>Capital e mercado</strong><p>Não estimados. O mínimo de 200.000 € do aviso refere-se à despesa elegível de um projeto candidato, não ao custo de lançar esta hipótese de serviço.</p></div>' +
      '<div class="opportunity-detail"><strong>Riscos</strong><p>Disposição de pagamento, concorrência, capacidade técnica e dimensão real do segmento não foram investigadas.</p></div>' +
      '<div class="opportunity-detail"><strong>Próximo teste de baixo custo</strong><ul class="detail-list"><li>Entrevistar cinco PME da região sobre controlo de água e desperdício.</li><li>Mapear soluções e consultores já disponíveis antes de construir software.</li><li>Testar um diagnóstico manual e verificar se alguém pagaria por ele.</li></ul></div>' +
      '<div class="article-links">' + sourceLink(signal.source, signal.source_url, "Sinal de origem") +
      '<button class="button-secondary" data-action="watch" data-id="' + esc(signal.id) + '">Acompanhar o aviso nesta sessão</button></div></article></section>';
  }

  function renderAdvisor() {
    var data = state.data;
    var recs = records(data.recommendations);
    var history = records(data.recommendation_history);
    var cats = Array.from(new Set(history.map(function (item) { return item.category || "Sinal público"; })));
    var categoryFilter = '<div class="filter-control"><label for="history-category">Categoria</label><select id="history-category"><option value="">Todas</option>' +
      cats.map(function (cat) { return '<option value="' + esc(cat) + '">' + esc(cat) + "</option>"; }).join("") + "</select></div>";
    return pageHead("Análise · Regras explícitas", "Conselheiro", "Recomendações ligadas a fontes públicas, com contexto, risco e uma ação concreta. Não há um modelo de IA ligado.") +
      notice("Versão baseada em regras", "O sistema não afirma ter analisado dados com IA. A ligação a um modelo só será feita quando existir uma API configurada e autorizada.", false) +
      '<section class="section">' + sectionHead("01", "Recomendações em vigor", "As recomendações atuais são derivadas de avisos oficiais e das suas condições publicadas.") +
      (recs.length ? '<div class="grid">' + recs.map(recommendationCard).join("") + "</div>" :
        empty("Sem recomendação fundamentada hoje", "Não foi identificado um sinal que justifique uma ação. Continua a consultar as fontes originais.")) +
      "</section><section class=\"section\">" + sectionHead("02", "Histórico público", "Mantém a fonte e o contexto disponíveis à data da recomendação; guarda apenas informação pública.") +
      '<form class="filters" id="history-filters">' + categoryFilter +
      '<div class="filter-control"><label for="history-since">Desde</label><input id="history-since" type="date"></div><button class="button" type="submit">Filtrar histórico</button></form>' +
      '<div class="card" style="margin-top:13px" id="history-list">' + historyRows(history) + "</div></section>" +
      '<section class="section"><div class="card"><div class="card-kicker">ÂMBITO EDITORIAL</div><h3>Oportunidades em Portugal, tecnologia e serviços digitais</h3><p class="metric-note">O radar dá prioridade a projetos de menor investimento quando a fonte permite confirmá-lo. Não guarda um perfil pessoal nem usa histórico privado. A pontuação deve ser revista quando houver dados de procura, custos e concorrência.</p></div></section>';
  }

  function renderTrends() {
    var data = state.data;
    var recs = records(data.research);
    var trends = recs.filter(function (item) {
      var text = (item.title || "").toLowerCase();
      return /artificial intelligence|machine learning|digital|energy|robot|technology|innovation|inteligência artificial|tecnolog|energia|inovação/.test(text);
    });
    var insights = records(data.insights && data.insights.opportunities).filter(function (item) {
      return !/^Sem sinal/.test(item.title || "");
    });
    var trendMarkup = trends.length ? '<div class="grid grid-2">' + trends.slice(0, 6).map(articleCard).join("") + "</div>" :
      empty("Sem tendência tecnológica destacada", "A pesquisa atual não encontrou artigos com abstract e dados suficientes para destacar uma tendência.");
    return pageHead("Mudança · Evidência recente", "Tendências", "Sinais de investigação e indicadores que ajudam a acompanhar mudanças. Um artigo isolado não prova que um setor esteja a crescer.") +
      '<section class="section">' + sectionHead("01", "Tecnologia e investigação", "Artigos recentes indexados no OpenAlex; a página original inclui método e limitações.") +
      trendMarkup + "</section>" +
      '<section class="section">' + sectionHead("02", "Sinais económicos relacionados", "Interpretações descritivas ligadas a séries observadas, sem previsões de mercado.") +
      (insights.length ? '<div class="grid grid-2">' + insights.map(function (item) {
        return '<article class="card"><div class="card-kicker">DADO OBSERVADO</div><h3>' + esc(item.title) +
          '</h3><p class="metric-note">' + esc(item.detail) + '</p><div class="article-links">' +
          sourceLink(item.source, item.source_url, "Fonte original") + "</div></article>";
      }).join("") + "</div>" : empty("Sem sinal destacado pelas regras atuais", "Os indicadores disponíveis não ativaram uma regra descritiva nesta atualização.")) +
      "</section><section class=\"section\">" + sectionHead("03", "Como validar uma tendência", "Antes de investir, compare séries independentes, observe vários períodos e confirme com potenciais clientes.") +
      '<div class="grid grid-3"><article class="card"><div class="callout-number">01</div><h3>Procura</h3><p class="metric-note">Procura entrevistas, encomendas, despesa ou outros sinais observáveis, não apenas interesse em redes sociais.</p></article><article class="card"><div class="callout-number">02</div><h3>Concorrência</h3><p class="metric-note">Conta alternativas existentes e o custo de mudar para a solução.</p></article><article class="card"><div class="callout-number">03</div><h3>Economia do modelo</h3><p class="metric-note">Estima custos de aquisição, preço, margem, capital de trabalho e tempo até à primeira receita.</p></article></div></section>';
  }

  function articleCard(item) {
    var text = '<article class="card article-card"><div class="article-meta">' + esc(item.source || "OpenAlex") +
      " · " + esc(dateLabel(item.date)) + (item.citations ? " · " + esc(item.citations) + " citações indexadas" : "") +
      '</div><h3>' + esc(item.title || "Artigo sem título") + '</h3><p><strong>Resumo:</strong> ' +
      esc(item.summary || "Resumo indisponível.") + '</p><p><strong>Conclusão destacada:</strong> ' +
      esc(item.conclusion || "Consulta o artigo original para as conclusões.") + '</p><p><strong>Porque ler:</strong> ' +
      esc(item.why_read || "Ajuda a aprofundar este tema.") + '</p><div class="article-links">' +
      sourceLink("OpenAlex", item.url, "Registo original") +
      (item.doi ? sourceLink("DOI", item.doi, "DOI") : "") +
      tag(item.open_access ? "Acesso aberto indicado" : "Acesso aberto não confirmado") + "</div></article>";
    return text;
  }

  function renderKnowledge() {
    var items = records(state.data.research).slice();
    var f = state.filters.knowledge || {};
    items = items.filter(function (item) {
      var s = String(f.search || "").toLowerCase().trim();
      return !s || (item.title + " " + item.summary + " " + item.conclusion).toLowerCase().indexOf(s) >= 0;
    });
    items.sort(function (a, b) { return String(b.date || "").localeCompare(String(a.date || "")); });
    var content = items.length ? '<div class="grid grid-2">' + items.map(articleCard).join("") + "</div>" :
      empty("Sem artigos com resumo nesta atualização", "O sistema mostra apenas registos OpenAlex com abstract disponível. Se não encontrar artigos, não fabrica resumos.");
    return pageHead("Estudos · Leitura crítica", "Conhecimento", "Resumos curtos a partir dos abstracts indexados, com conclusão destacada, motivo para ler e ligação ao registo original.") +
      '<form class="filters" id="knowledge-filters"><div class="filter-control" style="flex:1 1 260px"><label for="knowledge-search">Pesquisar artigos</label><input id="knowledge-search" value="' +
      esc(f.search || "") + '" placeholder="Tema, título ou conclusão"></div><button class="button" type="submit">Pesquisar</button><span class="filter-count">' + items.length + " artigos</span></form>" +
      '<section class="section">' + sectionHead("01", "Artigos recentes", "A síntese pode omitir pormenores. A fonte original continua a ser a referência.") +
      content + "</section>";
  }

  function renderEconomy() {
    var data = state.data;
    var quotes = records(data.quotes);
    var portugal = records(data.portugal);
    var macro = records(data.macro);
    var quoteCards = quotes.length ? '<div class="grid grid-3">' + quotes.map(function (item) {
      var change = Number(item.change_pct);
      return metricCard(item.name || item.symbol, fmt(item.price, 2) + " " + (item.currency || "USD"),
        (change > 0 ? "+" : "") + fmt(change, 2) + "% último fecho", item.date,
        change > 0 ? "positive" : change < 0 ? "negative" : "",
        "ETF de referência; preços em USD e potencialmente atrasados.");
    }).join("") + "</div>" : empty("Sem preços de mercado", "Verifica a próxima execução do fluxo e a chave Alpha Vantage. Esta secção não estima retornos futuros.");
    var ptCards = portugal.length ? '<div class="grid grid-3">' + portugal.map(function (item) {
      return metricCard(item.name || item.id, fmt(item.value, 1) + (item.unit ? " " + item.unit : ""),
        item.frequency || "Eurostat", item.date, "", item.description);
    }).join("") + "</div>" : empty("Indicadores de Portugal indisponíveis", "Os indicadores Eurostat são recolhidos pelo fluxo diário. A sua frequência é mensal ou trimestral.");
    var macroCards = macro.length ? '<div class="grid grid-3">' + macro.map(function (item) {
      return metricCard(item.name || item.id, fmt(item.value, 1) + (item.unit ? " " + item.unit : ""),
        item.frequency || "FRED", item.date, "", item.description);
    }).join("") + "</div>" : empty("Contexto macroeconómico indisponível", "A série FRED não descreve diretamente Portugal. Confirma a chave FRED e o último fluxo.");
    return pageHead("Dados · Contexto e interpretação", "Economia", "Portugal, indicadores internacionais e ativos de referência. O valor, a data, a unidade e uma explicação simples acompanham cada série.") +
      '<section class="section">' + sectionHead("01", "Portugal", "Eurostat · os dados podem ser revistos e chegam com diferentes atrasos de publicação.") + ptCards +
      chartWidget("portugal", portugal, "Evolução dos indicadores portugueses") + "</section>" +
      '<section class="section">' + sectionHead("02", "Mercados globais", "Alpha Vantage · ETFs de referência cotados em USD, não recomendações de compra ou venda.") + quoteCards +
      chartWidget("quotes", quotes, "Séries de mercado") + "</section>" +
      '<section class="section">' + sectionHead("03", "Indicadores dos Estados Unidos", "FRED · contexto global, sem equivalência direta com a economia portuguesa.") + macroCards +
      chartWidget("macro", macro, "Indicadores macroeconómicos") + "</section>" +
      '<section class="section"><div class="grid grid-2"><article class="card"><div class="card-kicker">INFLAÇÃO</div><h3>Taxa menor não significa preços a descer</h3><p class="metric-note">Uma descida da taxa indica que os preços estão a subir mais devagar. Para falar de queda de preços, seria preciso observar inflação negativa.</p></article><article class="card"><div class="card-kicker">MERCADOS</div><h3>Oscilações não são por si só um sinal de decisão</h3><p class="metric-note">O painel usa limiares raros para alertas. Variações normais e desempenho passado não permitem prever retornos futuros.</p></article></div></section>';
  }

  function chartWidget(source, items, title) {
    var available = items.filter(function (item) { return records(item.history).length > 1; });
    if (!available.length) return '<div class="section">' + empty("Histórico ainda indisponível", "O gráfico aparecerá quando existir uma série com pelo menos duas observações.") + "</div>";
    var id = "chart-" + source;
    var select = '<label for="' + id + '-select">Série<select id="' + id + '-select" data-chart-select="' + source + '">' +
      available.map(function (item, index) {
        return '<option value="' + index + '">' + esc(item.name || item.id || item.symbol) + "</option>";
      }).join("") + "</select></label>";
    return '<div class="section"><article class="card chart-card"><div class="chart-head"><div><div class="card-kicker">EVOLUÇÃO HISTÓRICA</div><h3>' +
      esc(title) + '</h3><p>Seleciona uma série e um período. Toca no gráfico para consultar um ponto.</p></div>' +
      '<div class="chart-periods" data-chart-ranges="' + source + '" role="group" aria-label="Período do gráfico">' +
      '<button type="button" data-days="90" aria-pressed="true">90d</button><button type="button" data-days="365" aria-pressed="false">1a</button>' +
      '<button type="button" data-days="1095" aria-pressed="false">3a</button><button type="button" data-days="all" aria-pressed="false">Máx.</button></div></div>' +
      '<div class="chart-filters">' + select + '</div><div class="chart-wrap"><canvas class="chart-canvas" id="' + id +
      '" data-chart="' + source + '" role="img" aria-label="' + esc(title) + '"></canvas><div class="chart-tooltip" aria-hidden="true"></div></div>' +
      '<div class="chart-legend"><span><i class="legend-dot"></i>Observações da fonte</span><span>Filtra um período para explorar tendências; não é uma previsão.</span></div>' +
      '<div class="chart-accessible" data-chart-table="' + source + '"></div></article></div>';
  }

  function renderProjects() {
    var projects = state.projects;
    var watch = state.watchlist;
    var projectList = projects.length ? '<div class="project-list">' + projects.map(function (item) {
      return '<article class="project-item"><div class="project-item-head"><strong>' + esc(item.title) +
        '</strong><select aria-label="Estado de ' + esc(item.title) + '" data-project-status="' + esc(item.id) + '">' +
        ["Por explorar", "Em investigação", "Em validação", "Em desenvolvimento", "Arquivado"].map(function (status) {
          return '<option' + (status === item.status ? " selected" : "") + ">" + esc(status) + "</option>";
        }).join("") + '</select></div><p>' + esc(item.next || "") + (item.notes ? "\\n" + esc(item.notes) : "") +
        '</p><button class="text-button" data-action="remove-project" data-id="' + esc(item.id) + '">Remover da sessão</button></article>';
    }).join("") + "</div>" : empty("Ainda sem projetos nesta sessão", "Adiciona uma ideia ou iniciativa. O conteúdo fica apenas na memória desta página e desaparece ao atualizar ou fechar.");
    var watchList = watch.length ? '<div class="project-list">' + watch.map(function (item) {
      return '<article class="project-item"><div class="project-item-head"><strong>' + esc(item.title) +
        '</strong><select aria-label="Estado de ' + esc(item.title) + '" data-watch-status="' + esc(item.id) + '">' +
        ["Por explorar", "Em investigação", "Em validação", "Em desenvolvimento", "Arquivado"].map(function (status) {
          return '<option' + (status === item.status ? " selected" : "") + ">" + esc(status) + "</option>";
        }).join("") + '</select></div><p>' + esc(item.notes || "Sem nota ainda.") +
        '</p><div class="article-links">' + sourceLink(item.source, item.source_url, "Fonte original") +
        '<button class="text-button" data-action="remove-watch" data-id="' + esc(item.id) + '">Retirar</button></div></article>';
    }).join("") + "</div>" : empty("A lista desta sessão está vazia", "Usa «Acompanhar nesta sessão» no radar para guardar temporariamente uma oportunidade.");
    return pageHead("Organização · Local e temporário", "Projetos", "Um espaço de trabalho temporário para testar a interface de projetos e acompanhamento, sem enviar notas para um servidor.") +
      notice("Persistência privada ainda pendente", "Esta página GitHub Pages é pública. Itens, notas e estados ficam apenas na memória desta sessão do separador; não persistem depois de atualizar ou navegar para fora do Hub.", true) +
      '<section class="section"><div class="grid grid-2"><div><div class="section-heading"><div class="section-title-wrap"><span class="section-index">01</span><h2>Ideias e projetos</h2></div></div>' +
      '<article class="card"><form id="project-form" class="form-grid"><div class="form-field full"><label for="project-title">Nome da ideia ou projeto</label><input id="project-title" name="title" required maxlength="90" placeholder="Ex.: testar um serviço digital"></div>' +
      '<div class="form-field"><label for="project-status">Estado</label><select id="project-status" name="status"><option>Por explorar</option><option>Em investigação</option><option>Em validação</option><option>Em desenvolvimento</option></select></div>' +
      '<div class="form-field"><label for="project-next">Próximo passo</label><input id="project-next" name="next" maxlength="140" placeholder="Ação a verificar"></div>' +
      '<div class="form-field full"><label for="project-notes">Notas temporárias</label><textarea id="project-notes" name="notes" maxlength="500" placeholder="Não incluir dados pessoais ou confidenciais."></textarea></div>' +
      '<div class="form-field full form-actions"><button class="button" type="submit">Adicionar só a esta sessão</button></div></form></article><div style="margin-top:12px" id="project-list">' + projectList + "</div></div>" +
      '<div><div class="section-heading"><div class="section-title-wrap"><span class="section-index">02</span><h2>Acompanhamento</h2></div></div><div id="watch-list">' +
      watchList + "</div><p class=\"chart-note\">Este protótipo não grava nada em localStorage, no GitHub ou num servidor.</p></div></div></section>";
  }

  function renderAlerts() {
    var data = state.data;
    var active = records(data.alerts);
    var history = records(data.alert_history);
    var activeMarkup = active.length ? '<div class="grid">' + active.map(function (item) {
      return '<article class="alert-card"><span class="alert-mark" aria-hidden="true">!</span><div><div class="opportunity-badges">' +
        tag(item.level || "Relevante", "amber") + tag(dateLabel(item.date)) + '</div><h3>' + esc(item.title) +
        '</h3><p>' + esc(item.detail) + "</p></div></article>";
    }).join("") + "</div>" : empty("Sem alertas críticos ativos", "Os limiares seletivos não foram atingidos nesta atualização. Isto não significa ausência de risco; só significa que as regras não dispararam.");
    var historyMarkup = history.length ? '<div class="card">' + history.slice(0, 60).map(function (item) {
      return '<div class="history-row"><span class="history-date">' + esc(dateLabel(item.date)) +
        '</span><div><h3>' + esc(item.title) + "</h3><p>" + esc(item.detail) +
        '</p><div class="article-meta">' + esc(item.level || "Alerta") + " · Fonte de dados: " +
        esc(item.source || "série monitorizada") + "</div></div>" + tag("Evento observado", "amber") + "</div>";
    }).join("") + "</div>" : empty("Sem eventos guardados", "O histórico de alertas só inclui limiares efetivamente acionados; o teste neutro ntfy não aparece como alerta financeiro.");
    return pageHead("Notificações · Sensibilidade equilibrada", "Alertas", "Avisa apenas para movimentos ou limiares relevantes. O teste ntfy é separado e não cria um alerta financeiro.") +
      '<section class="section">' + sectionHead("01", "Estado atual", "A execução diária publica os valores e mantém a deteção de duplicados.") + activeMarkup + "</section>" +
      '<section class="section">' + sectionHead("02", "Regras de disparo", "Os limiares continuam seletivos para evitar falsos alarmes de mercado.") +
      '<div class="grid grid-3"><article class="card rule-card"><div class="card-kicker">MERCADO</div><strong>Queda diária de 5% ou mais</strong><p>Usa a última sessão diária de negociação de cada ativo.</p></article>' +
      '<article class="card rule-card"><div class="card-kicker">VOLATILIDADE</div><strong>VIX acima de 35</strong><p>Sinal de volatilidade implícita elevada; não prevê a direção do mercado.</p></article>' +
      '<article class="card rule-card"><div class="card-kicker">DUPLICADOS</div><strong>Apenas novos IDs de alerta</strong><p>O estado do fluxo compara com a execução anterior antes de notificar.</p></article></div></section>' +
      '<section class="section">' + sectionHead("03", "Histórico de alertas", "Guarda apenas acontecimentos que ultrapassaram os limiares; mensagens de teste são excluídas.") + historyMarkup + "</section>" +
      '<section class="section"><div class="card"><div class="card-kicker">TESTE NEUTRO PARA O IPHONE</div><h3>Confirma a receção sem criar um alerta de mercado</h3><p class="metric-note">Na página Actions, executa o workflow «Atualizar dashboard» e ativa apenas a opção de teste ntfy. A mensagem tem prioridade normal, identifica-se como teste e só é enviada depois da publicação. Não insere um evento no histórico financeiro.</p><a class="button" style="margin-top:12px" href="https://github.com/hlsr2002-glitch/personal-intelligence-dashboard/actions/workflows/update-dashboard.yml" target="_blank" rel="noopener noreferrer">Abrir teste seguro no GitHub Actions ↗</a></div></section>';
  }

  function renderPage() {
    if (!state.data) {
      main.innerHTML = '<div class="loading-state" role="status"><span class="spinner" aria-hidden="true"></span>A preparar o painel…</div>';
      return;
    }
    var renderers = {
      home: renderHome,
      opportunities: renderOpportunities,
      advisor: renderAdvisor,
      trends: renderTrends,
      knowledge: renderKnowledge,
      economy: renderEconomy,
      projects: renderProjects,
      alerts: renderAlerts
    };
    var renderer = renderers[state.page] || renderHome;
    main.innerHTML = renderer() + '<span class="sr-only" id="live-message" aria-live="polite">' + esc(state.message) + "</span>";
    updatePageMetadata();
    if (state.page === "economy") hydrateCharts();
    bindPageInteractions();
  }

  function updatePageMetadata() {
    var title = TITLES[state.page] || "Início";
    var crumb = document.getElementById("crumb-title");
    var updated = document.getElementById("updated-label");
    if (crumb) crumb.textContent = title;
    document.title = title + " · Personal Intelligence Hub";
    if (updated) updated.textContent = updatedLabel(state.data.updated_at);
    document.querySelectorAll("[data-route]").forEach(function (link) {
      var selected = link.getAttribute("data-route") === state.page;
      if (selected) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
  }

  function setRoute(page, push) {
    if (!PATHS[page]) return;
    state.page = page;
    if (push) history.pushState({ page: page }, "", PATHS[page]);
    renderPage();
    if (main) main.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }

  function bindPageInteractions() {
    var oppForm = document.getElementById("opportunity-filters");
    if (oppForm) oppForm.addEventListener("submit", function (event) {
      event.preventDefault();
      state.filters.opportunities = {
        search: document.getElementById("opp-search").value,
        category: document.getElementById("opp-category").value,
        sector: document.getElementById("opp-sector").value,
        location: document.getElementById("opp-location").value,
        capital: document.getElementById("opp-capital").value,
        relevance: document.getElementById("opp-relevance").value,
        sort: document.getElementById("opp-sort").value
      };
      renderPage();
    });
    var knowledgeForm = document.getElementById("knowledge-filters");
    if (knowledgeForm) knowledgeForm.addEventListener("submit", function (event) {
      event.preventDefault();
      state.filters.knowledge = { search: document.getElementById("knowledge-search").value };
      renderPage();
    });
    var historyForm = document.getElementById("history-filters");
    if (historyForm) historyForm.addEventListener("submit", function (event) {
      event.preventDefault();
      var cat = document.getElementById("history-category").value;
      var since = document.getElementById("history-since").value;
      var node = document.getElementById("history-list");
      node.innerHTML = historyRows(state.data.recommendation_history, cat, since);
    });
    var projectForm = document.getElementById("project-form");
    if (projectForm) projectForm.addEventListener("submit", function (event) {
      event.preventDefault();
      var form = new FormData(projectForm);
      state.projects.unshift({
        id: String(Date.now()),
        title: String(form.get("title") || "").trim(),
        status: String(form.get("status") || "Por explorar"),
        next: String(form.get("next") || "").trim(),
        notes: String(form.get("notes") || "").trim()
      });
      state.message = "Projeto adicionado apenas nesta sessão.";
      renderPage();
    });
    document.querySelectorAll("[data-project-status]").forEach(function (select) {
      select.addEventListener("change", function () {
        var item = state.projects.find(function (entry) { return entry.id === select.getAttribute("data-project-status"); });
        if (item) item.status = select.value;
      });
    });
    document.querySelectorAll("[data-watch-status]").forEach(function (select) {
      select.addEventListener("change", function () {
        var item = state.watchlist.find(function (entry) { return entry.id === select.getAttribute("data-watch-status"); });
        if (item) item.status = select.value;
      });
    });
    main.querySelectorAll("[data-action]").forEach(function (button) {
      button.addEventListener("click", function () {
        var action = button.getAttribute("data-action");
        var id = button.getAttribute("data-id");
        if (action === "score") showScore(id);
        if (action === "watch") addWatch(id);
        if (action === "remove-watch") {
          state.watchlist = state.watchlist.filter(function (item) { return item.id !== id; });
          renderPage();
        }
        if (action === "remove-project") {
          state.projects = state.projects.filter(function (item) { return item.id !== id; });
          renderPage();
        }
      });
    });
    var close = document.querySelector("[data-action='close-modal']");
    if (close) close.addEventListener("click", closeModal);
  }

  function addWatch(id) {
    var item = records(state.data.opportunities).find(function (entry) { return entry.id === id; });
    if (!item) return;
    if (!state.watchlist.some(function (entry) { return entry.id === id; })) {
      state.watchlist.unshift({
        id: item.id,
        title: item.title,
        source: item.source,
        source_url: item.source_url,
        notes: item.next_steps && item.next_steps[0] || "",
        status: "Por explorar"
      });
      state.message = "Oportunidade guardada apenas nesta sessão.";
    } else {
      state.message = "Esta oportunidade já está acompanhada nesta sessão.";
    }
    renderPage();
    var announcement = document.getElementById("live-message");
    if (announcement) announcement.textContent = state.message;
  }

  function showScore(id) {
    var item = records(state.data.opportunities).find(function (entry) { return entry.id === id; });
    if (!item) return;
    var rows = records(item.score_criteria).map(function (criterion) {
      var known = criterion.points != null;
      var points = known ? Number(criterion.points) : 0;
      var pct = criterion.weight ? points / Number(criterion.weight) * 100 : 0;
      return '<div class="rubric-row"><span>' + esc(criterion.label) + '</span><div class="rubric-bar"><i style="width:' +
        Math.max(0, Math.min(100, pct)) + '%"></i></div><em class="' + (known ? "" : "unknown") + '">' +
        (known ? esc(points) + "/" + esc(criterion.weight) : "N/D") + "</em></div>" +
        '<div class="article-meta" style="margin:-4px 0 5px">' + esc(criterion.basis) + "</div>";
    }).join("");
    var modal = document.createElement("div");
    lastModalTrigger = document.activeElement;
    modal.className = "score-modal";
    modal.setAttribute("role", "presentation");
    modal.innerHTML = '<section class="modal-panel" role="dialog" aria-modal="true" aria-labelledby="score-title"><div class="modal-head"><div><div class="eyebrow">TRANSPARÊNCIA</div><h2 id="score-title">' +
      esc(item.score_label) + " · " + esc(item.score) + "/100</h2><p class=\"page-lede\">" +
      esc(item.title) + '</p></div><button class="modal-close" type="button" data-action="close-modal" aria-label="Fechar">×</button></div>' +
      '<p class="notice-inline">Pontuação heurística de triagem, não probabilidade de sucesso. Critérios sem dados ficam como N/D e não recebem pontos. Cobertura observada: ' +
      esc(item.score_confidence) + "%.</p><div class=\"rubric\" style=\"margin-top:15px\">" + rows +
      '</div><p class="chart-note">Compatibilidade é uma regra editorial baseada nos interesses indicados. Procura, concorrência, escala, complexidade e capital total precisam de validação independente.</p></section>';
    modal.addEventListener("click", function (event) { if (event.target === modal) closeModal(); });
    document.body.appendChild(modal);
    var close = modal.querySelector("[data-action='close-modal']");
    if (close) close.addEventListener("click", closeModal);
    modal.addEventListener("keydown", function (event) { if (event.key === "Escape") closeModal(); });
    if (close) close.focus();
  }
  function closeModal() {
    var modal = document.querySelector(".score-modal");
    if (modal) modal.remove();
    if (lastModalTrigger && typeof lastModalTrigger.focus === "function") lastModalTrigger.focus();
    lastModalTrigger = null;
  }

  function hydrateCharts() {
    var sources = {
      quotes: records(state.data.quotes),
      portugal: records(state.data.portugal),
      macro: records(state.data.macro)
    };
    document.querySelectorAll("[data-chart]").forEach(function (canvas) {
      var source = canvas.getAttribute("data-chart");
      var select = document.querySelector("[data-chart-select='" + source + "']");
      var items = sources[source] || [];
      var available = items.filter(function (item) { return records(item.history).length > 1; });
      if (!select || !available.length) return;
      var range = state.chartRange[source] || 90;
      var render = function () { drawChart(canvas, select, available, range, source); };
      select.addEventListener("change", render);
      var rangeGroup = document.querySelector("[data-chart-ranges='" + source + "']");
      if (rangeGroup) rangeGroup.querySelectorAll("button").forEach(function (button) {
        var selected = String(button.getAttribute("data-days")) === String(range);
        button.setAttribute("aria-pressed", String(selected));
        button.addEventListener("click", function () {
          var raw = button.getAttribute("data-days");
          range = raw === "all" ? "all" : Number(raw);
          state.chartRange[source] = range;
          rangeGroup.querySelectorAll("button").forEach(function (other) {
            other.setAttribute("aria-pressed", String(other === button));
          });
          render();
        });
      });
      if (window.ResizeObserver) new ResizeObserver(render).observe(canvas.parentElement);
      else window.addEventListener("resize", render);
      render();
    });
  }

  function drawChart(canvas, select, available, range, source) {
    var item = available[Number(select.value) || 0];
    var all = records(item.history).filter(function (point) {
      return point.date && Number.isFinite(Number(point.value));
    });
    if (range !== "all" && all.length) {
      var cutoff = dateValue(all[all.length - 1].date) - Number(range) * 86400000;
      all = all.filter(function (point) { return dateValue(point.date) >= cutoff; });
    }
    var box = canvas.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.round(box.width * dpr));
    canvas.height = Math.max(1, Math.round(box.height * dpr));
    var ctx = canvas.getContext("2d");
    if (!ctx || !all.length) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    var width = box.width, height = box.height, left = 48, right = 10, top = 12, bottom = 26;
    var plotW = Math.max(1, width - left - right), plotH = Math.max(1, height - top - bottom);
    var values = all.map(function (point) { return Number(point.value); });
    var min = Math.min.apply(null, values), max = Math.max.apply(null, values);
    if (min === max) { min -= 1; max += 1; }
    var pad = (max - min) * .09; min -= pad; max += pad;
    ctx.clearRect(0, 0, width, height);
    ctx.font = "10px system-ui";
    ctx.strokeStyle = "#26364b"; ctx.fillStyle = "#8494ab"; ctx.lineWidth = 1;
    ctx.textAlign = "right"; ctx.textBaseline = "middle";
    for (var i = 0; i < 4; i++) {
      var gy = top + plotH * i / 3;
      ctx.beginPath(); ctx.moveTo(left, gy); ctx.lineTo(width - right, gy); ctx.stroke();
      ctx.fillText(fmt(max - (max - min) * i / 3, Math.abs(max) > 100 ? 0 : 2), left - 7, gy);
    }
    function x(index) { return left + (all.length < 2 ? plotW / 2 : index / (all.length - 1) * plotW); }
    function y(value) { return top + (max - value) / (max - min) * plotH; }
    ctx.beginPath();
    all.forEach(function (point, index) {
      if (index === 0) ctx.moveTo(x(index), y(Number(point.value)));
      else ctx.lineTo(x(index), y(Number(point.value)));
    });
    ctx.lineWidth = 2.3; ctx.strokeStyle = source === "quotes" ? "#88a9ff" : "#5bd9cc";
    ctx.lineJoin = "round"; ctx.lineCap = "round"; ctx.stroke();
    var gradient = ctx.createLinearGradient(0, top, 0, top + plotH);
    gradient.addColorStop(0, source === "quotes" ? "rgba(136,169,255,.22)" : "rgba(91,217,204,.2)");
    gradient.addColorStop(1, "rgba(91,217,204,0)");
    ctx.lineTo(x(all.length - 1), top + plotH); ctx.lineTo(x(0), top + plotH); ctx.closePath();
    ctx.fillStyle = gradient; ctx.fill();
    ctx.fillStyle = "#8494ab"; ctx.textBaseline = "top"; ctx.textAlign = "left";
    ctx.fillText(dateLabel(all[0].date), left, top + plotH + 8);
    ctx.textAlign = "right"; ctx.fillText(dateLabel(all[all.length - 1].date), width - right, top + plotH + 8);
    var tooltip = canvas.parentElement.querySelector(".chart-tooltip");
    function show(event) {
      var bounds = canvas.getBoundingClientRect();
      var localX = event.clientX - bounds.left;
      var fraction = Math.max(0, Math.min(1, (localX - left) / plotW));
      var index = Math.round(fraction * (all.length - 1));
      var point = all[index];
      if (!point || !tooltip) return;
      var pointX = x(index);
      tooltip.innerHTML = "<strong>" + esc(dateLabel(point.date)) + "</strong><br>" +
        esc(fmt(point.value, 2)) + (item.unit ? " " + esc(item.unit) : "");
      tooltip.style.display = "block";
      tooltip.style.left = Math.min(Math.max(5, pointX + 8), Math.max(5, width - 145)) + "px";
      tooltip.style.top = "8px";
    }
    canvas.onpointermove = show;
    canvas.onpointerdown = show;
    canvas.onpointerleave = function () { if (tooltip) tooltip.style.display = "none"; };
    var table = document.querySelector("[data-chart-table='" + source + "']");
    if (table) {
      table.innerHTML = '<details><summary class="text-button">Últimas observações para leitores de ecrã</summary><table class="chart-table"><thead><tr><th>Data</th><th>Valor</th></tr></thead><tbody>' +
        all.slice(-5).reverse().map(function (point) {
          return "<tr><td>" + esc(dateLabel(point.date)) + "</td><td>" + esc(fmt(point.value, 2)) +
            (item.unit ? " " + esc(item.unit) : "") + "</td></tr>";
        }).join("") + "</tbody></table></details>";
    }
  }

  function loadData() {
    fetch("data.json?v=" + Date.now(), { cache: "no-store" }).then(function (response) {
      if (!response.ok) throw new Error("Dados indisponíveis");
      return response.json();
    }).then(function (payload) {
      state.data = payload;
      var status = document.getElementById("source-status");
      if (status) status.textContent = "Dados públicos atualizados";
      renderPage();
    }).catch(function () {
      if (main) main.innerHTML = empty("Não foi possível carregar os dados", "Tenta novamente mais tarde. O dashboard depende da última execução do GitHub Actions.");
      var status = document.getElementById("source-status");
      if (status) status.textContent = "Fontes temporariamente indisponíveis";
    });
  }

  document.addEventListener("click", function (event) {
    var link = event.target.closest && event.target.closest("[data-route]");
    if (!link) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    setRoute(link.getAttribute("data-route"), true);
  });
  window.addEventListener("popstate", function (event) {
    var page = event.state && event.state.page;
    if (!page) {
      var filename = location.pathname.split("/").pop() || "index.html";
      page = Object.keys(PATHS).find(function (key) { return PATHS[key] === filename; }) || "home";
    }
    state.page = page;
    renderPage();
  });
  loadData();
})();
