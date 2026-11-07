# Personal Intelligence Dashboard

Protótipo da Fase 1: mercados, indicadores macroeconómicos e investigação recente, com alertas seletivos no modo **Equilibrado**.

> Estado: estrutura preparada; ainda não recebe dados reais até serem configurados os segredos das fontes no GitHub. Não contém aconselhamento financeiro nem dados pessoais.

## O que inclui

- Cotações de ETFs como aproximações de índices e classes de ativos, através da Alpha Vantage.
- Indicadores macroeconómicos da FRED, incluindo a taxa de desemprego, inflação, taxa de fundos federais, rendimento do Treasury a 10 anos e VIX.
- Artigos recentes de economia, tecnologia, energia e inteligência artificial através da OpenAlex.
- Alertas para uma queda diária de 5% ou mais e para VIX acima de 35. Só são enviados quando um alerta começa; o estado ativo fica guardado para evitar repetições.
- Atualização diária por GitHub Actions e envio opcional para um tópico privado ntfy.
- Dashboard estático gerado em `docs/`, sem expor as chaves das APIs no navegador.

As regras são pontos de partida para investigação, não recomendações de compra ou venda. Uma descida de preço, por si só, não constitui uma oportunidade.

## Configuração no GitHub

1. Cria uma chave gratuita da [Alpha Vantage](https://www.alphavantage.co/support/#api-key) e uma chave da [FRED](https://fred.stlouisfed.org/docs/api/api_key.html).
2. No repositório, abre **Settings → Secrets and variables → Actions → New repository secret** e cria:
   - `ALPHA_VANTAGE_API_KEY`
   - `FRED_API_KEY`
3. Para notificações, cria um tópico privado no ntfy e guarda o nome do tópico como o segredo `NTFY_TOPIC`. Não publiques esse nome.
4. Executa manualmente o workflow **Atualizar dashboard** no separador **Actions**, para confirmar a primeira recolha.

O workflow diário corre às 08:17 UTC. Pode haver atraso na execução de tarefas agendadas pelo GitHub. Sem as chaves, o dashboard continua a abrir, mas mostra estados vazios para as fontes não configuradas.

## Pré-visualizar localmente

Com Python 3 instalado, executa `python3 build_dashboard.py` para gerar os ficheiros e `python3 -m http.server 8000 --directory docs` para abrir o dashboard em `http://localhost:8000`.

## Estrutura

```text
build_dashboard.py                 Recolha de dados, regras e geração do dashboard
config.example.json                Lista inicial de símbolos e temas
data/active_alerts.json            Estado usado para não repetir alertas ativos
docs/index.html                    Interface do dashboard
docs/data.json                     Dados mais recentes (gerado automaticamente)
.github/workflows/update.yml       Atualização diária e sob pedido
```

## Fontes e limites

- Alpha Vantage: cotações resumidas; disponibilidade e limites dependem do plano da API.
- FRED: séries económicas oficiais; as datas de divulgação variam por indicador.
- OpenAlex: pesquisa de publicações académicas; relevância e qualidade devem ser avaliadas antes de tirar conclusões.
- ntfy: canal opcional de notificação. Mantém o tópico privado e não coloques segredos no código.

O protótipo não recolhe saúde, agenda, carteira pessoal nem dados bancários. O dashboard não fica publicado na web por predefinição; a ativação de um endereço Pages deverá ser decidida separadamente.
