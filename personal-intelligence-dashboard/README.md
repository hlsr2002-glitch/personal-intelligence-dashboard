# Aplicação do dashboard

O site público está em [hlsr2002-glitch.github.io/personal-intelligence-dashboard](https://hlsr2002-glitch.github.io/personal-intelligence-dashboard/). A página lê `docs/data.json`, criado em cada execução do workflow da raiz do repositório.

## Ficheiros

- `build_dashboard.py`: recolhe séries públicas, interpreta os indicadores e gera os dados do site.
- `config.example.json`: símbolos, séries económicas e temas de investigação.
- `ntfy_utils.py`: envia alertas financeiros novos e uma mensagem neutra de teste.
- `send_ntfy_test.py`: teste manual, sem executar regras financeiras ou editar estado de alertas.
- `data/active_alerts.json`: estado inicial; o workflow preserva o estado entre execuções usando a cache do GitHub Actions.
- `docs/index.html`: interface responsiva, gráficos e filtros temporais.
- `docs/data.json`: exemplo vazio do formato consumido pelo site; o workflow gera os dados publicados.
- `tests/`: testes para fontes, limiares e separação do teste ntfy.

As fontes são Alpha Vantage, FRED, Eurostat e OpenAlex. Os dados publicados são indicadores públicos. Nenhum segredo, dado pessoal ou dado de saúde deve ser incluído nos ficheiros.
