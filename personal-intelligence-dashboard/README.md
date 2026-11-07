# Personal Intelligence Dashboard

Protótipo privado da Fase 1 para mercados, indicadores macroeconómicos e investigação recente, com alertas seletivos no modo **Equilibrado**.

O código está nesta pasta. A automação fica no repositório, em `.github/workflows/update-dashboard.yml`. Cada execução prepara um artefacto descarregável em **Actions**, válido por 7 dias. O dashboard não está publicado na web.

## O que inclui

- Cotações de ETFs de referência através da Alpha Vantage.
- Indicadores macroeconómicos da FRED, incluindo inflação, taxas de juro, desemprego, PIB, Treasury a 10 anos e VIX.
- Publicações recentes sobre economia, tecnologia, energia e inteligência artificial através da OpenAlex.
- Alertas equilibrados para quedas diárias de 5% ou mais e VIX acima de 35. Uma condição persistente não repete o alerta.

As regras servem para investigação e não são recomendações de compra ou venda. O protótipo não recolhe saúde, agenda, carteira pessoal nem dados bancários.

## Configuração

1. Cria uma chave da [Alpha Vantage](https://www.alphavantage.co/support/#api-key) e uma chave da [FRED](https://fred.stlouisfed.org/docs/api/api_key.html).
2. No repositório, abre **Settings → Secrets and variables → Actions → New repository secret** e cria `ALPHA_VANTAGE_API_KEY` e `FRED_API_KEY`.
3. Para notificações no iPhone, cria um tópico ntfy e guarda o respetivo nome como o segredo opcional `NTFY_TOPIC`.
4. No separador **Actions**, executa manualmente **Atualizar dashboard** para obter o primeiro artefacto. O workflow também corre diariamente às 08:17 UTC.

Sem as chaves, o workflow ainda pode correr, mas não haverá cotações nem indicadores macroeconómicos. As chaves ficam guardadas no GitHub; não as envies nesta conversa.

## Ficheiros

- `build_dashboard.py`: recolha, regras de alerta e geração do dashboard.
- `config.example.json`: símbolos e temas acompanhados.
- `data/active_alerts.json`: estado inicial para deduplicar alertas; execuções guardam estado em cache do Actions.
- `docs/index.html`: interface do dashboard.
- `docs/data.json`: dados gerados e incluídos no artefacto de cada execução.
- `.github/workflows/update-dashboard.yml`: automação diária, na raiz do repositório.

A execução automática não publica o dashboard em Pages. Os resultados são descarregados no artefacto da execução do Actions.
