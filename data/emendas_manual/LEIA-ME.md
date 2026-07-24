# Fallback manual do extrator de emendas

O extrator (`src/emendas.py`) tenta primeiro a API do Power BI. Se o
`resourceKey` de um painel rotacionar e a API parar de responder, a extração
**degrada para arquivo manual** em vez de falhar.

## Como gerar o arquivo manual

1. Abra o painel do ano no Portal da Transparência de SP
   (Emendas Parlamentares → painel do ano).
2. No visual de tabela, use o botão **"Baixar os dados"**.
3. Salve o arquivo nesta pasta com o **nome = ano**, ex.: `2024.xlsx` ou `2024.csv`.

O extrator procura `data/emendas_manual/<ano>.*` quando a API falha para aquele
ano. O leitor casa as colunas por nome (tolerante a variação de cabeçalho);
precisa ao menos de: parlamentar, município e valor.

Arquivos aqui dentro **não vão para o git** (podem ser grandes e são
reproduzíveis) — só este LEIA-ME é versionado.
