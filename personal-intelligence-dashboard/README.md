# Personal Intelligence Hub

O site público está em [hlsr2002-glitch.github.io/personal-intelligence-dashboard](https://hlsr2002-glitch.github.io/personal-intelligence-dashboard/). O GitHub Actions executa o fluxo diário, recolhe os dados públicos e publica a pasta docs.

## Páginas

Início, Oportunidades, Conselheiro, Tendências, Conhecimento, Economia, Projetos e Alertas. build_site.py gera as páginas HTML; docs/assets/hub.css e docs/assets/hub.js mantêm o design e as interações comuns.

## Fontes e limites

- Mercados: Alpha Vantage.
- Indicadores macroeconómicos: FRED.
- Indicadores de Portugal: Eurostat.
- Resumos de investigação: abstracts indexados no OpenAlex.
- Oportunidades: amostra curta consultada manualmente em fontes oficiais IAPMEI/Portugal 2030. As fichas mostram a fonte, a data de verificação, o prazo e os dados em falta; oportunidades expiram automaticamente pelo prazo publicado.
- O radar também liga a portais oficiais de avisos, IAPMEI/EEN e contratação pública. A importação automática de avisos e a API autenticada do Portal BASE não estão configuradas. A previsão do Plano Anual não é apresentada como candidatura aberta.
- O Conselheiro usa regras documentadas. Não há uma API de IA configurada.
- Os scores são prioridades de investigação; pontos desconhecidos reduzem a cobertura e não são probabilidades de sucesso.

## Privacidade e armazenamento

O repositório e o GitHub Pages são públicos. A lista de acompanhamento e os projetos funcionam apenas na memória desta sessão do navegador e desaparecem quando a página é atualizada ou fechada. Não escrevas dados pessoais ou confidenciais. A persistência privada requer autenticação e um serviço de armazenamento privado; ainda não está implementada. A área de saúde não recolhe nem publica dados.

O histórico publicado contém recomendações e alertas derivados de fontes públicas. O workflow preserva esse histórico usando a cache do GitHub Actions. Nunca incluir notas pessoais nesse histórico.

## Automatizações

O workflow .github/workflows/update-dashboard.yml mantém a recolha diária, o deploy do Pages, os segredos Alpha Vantage/FRED/ntfy, os limiares seletivos e a prevenção de alertas duplicados. workflow_dispatch inclui um teste ntfy neutro separado das regras financeiras.

## Desenvolvimento local

    python3 -m unittest discover -s personal-intelligence-dashboard/tests -v
    python3 personal-intelligence-dashboard/build_site.py

Para abrir localmente, inicia um servidor HTTP na pasta personal-intelligence-dashboard/docs. A página precisa de data.json; a recolha completa usa os segredos configurados em GitHub Actions.
