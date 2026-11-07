# Personal Intelligence Dashboard

Dashboard público de indicadores de mercado, economia portuguesa e investigação científica. A interface está em GitHub Pages:

**https://hlsr2002-glitch.github.io/personal-intelligence-dashboard/**

O workflow **Atualizar dashboard** corre diariamente às 08:17 UTC e também pode ser iniciado em **Actions → Atualizar dashboard → Run workflow**. Cada execução recolhe dados, atualiza o dashboard e publica a página. O ficheiro `.github/workflows/update-dashboard.yml` existente foi mantido e inclui um teste ntfy manual opcional.

## O que apresenta

- ETFs de referência e séries diárias da Alpha Vantage, com gráficos e períodos selecionáveis.
- Indicadores dos EUA da FRED, incluindo inflação, taxas, desemprego, PIB, Treasury a 10 anos e VIX.
- Indicadores de Portugal do Eurostat: inflação HICP, desemprego, PIB trimestral real e dívida pública.
- Observações descritivas de oportunidades e riscos, ligadas aos dados e às fontes originais.
- Resumos, conclusão destacada e motivo de leitura de artigos recentes, derivados do abstract indexado pela OpenAlex. Confirma sempre o artigo original.
- Alertas equilibrados: queda diária de 5% ou mais num ativo acompanhado e VIX acima de 35. Uma condição persistente não envia repetidamente o mesmo alerta.
- Uma área de saúde desativada, reservada para uma futura integração privada; não são recolhidos nem publicados dados de saúde.

Os indicadores são dados públicos e podem ser revistos ou ter atraso. Interpretações não são previsões nem aconselhamento financeiro. O dashboard não recolhe carteira pessoal, agenda, dados bancários ou dados de saúde.

## Segredos do GitHub

Em **Settings → Secrets and variables → Actions**, o workflow usa os segredos de repositório `ALPHA_VANTAGE_API_KEY`, `FRED_API_KEY` e `NTFY_TOPIC`. Os valores não devem ser escritos no código ou nos ficheiros publicados. O ntfy aceita o nome do tópico ou o formato `ntfy.sh/nome-do-tópico`; o valor só é utilizado no workflow.

Para verificar a ligação ao iPhone sem criar um falso alerta financeiro, inicia manualmente **Atualizar dashboard** e seleciona a caixa **Enviar uma mensagem neutra de teste ntfy**. O teste envia apenas “Teste de notificações” e não lê nem altera o estado de deduplicação dos alertas. Deixa a caixa desmarcada nas execuções normais.

## Fontes

- [Alpha Vantage](https://www.alphavantage.co/documentation/) para séries diárias de ETFs.
- [FRED](https://fred.stlouisfed.org/docs/api/fred/) para indicadores dos Estados Unidos.
- [Eurostat](https://ec.europa.eu/eurostat/web/main/data/web-services) para indicadores portugueses.
- [OpenAlex](https://docs.openalex.org/) para metadados de investigação e abstracts disponíveis.
- [BCE: objetivo de inflação de 2%](https://www.ecb.europa.eu/press/pr/date/2025/html/ecb.pr250630~aabf988af8.en.html); o objetivo refere-se à área do euro no médio prazo, não é um alvo mensal específico para Portugal.

## Desenvolvimento e verificação

Executa os testes com `python3 -m unittest discover -s personal-intelligence-dashboard/tests -v`. O dashboard é estático e não depende de bibliotecas externas de JavaScript.

Os ficheiros de configuração e aplicação estão em `personal-intelligence-dashboard/`; o workflow de publicação está em `.github/workflows/update-dashboard.yml`.
