# Personal Intelligence Dashboard

Protótipo privado da Fase 1 para acompanhar mercados, indicadores macroeconómicos e investigação científica, com alertas seletivos.

O código completo está em [`personal-intelligence-dashboard/`](personal-intelligence-dashboard/). A automação diária está em [`.github/workflows/update-dashboard.yml`](.github/workflows/update-dashboard.yml). Cada execução prepara um artefacto descarregável no separador **Actions**; o dashboard não é publicado na web.

Para obter dados e notificações, configura os segredos `ALPHA_VANTAGE_API_KEY` e `FRED_API_KEY` em **Settings → Secrets and variables → Actions**. `NTFY_TOPIC` é opcional para notificações no iPhone. Consulta o [guia de configuração](personal-intelligence-dashboard/README.md).
