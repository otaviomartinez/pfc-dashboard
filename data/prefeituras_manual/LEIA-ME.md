# Preenchimento manual do MDE (plano B)

O índice de MDE (os 25% do art. 212 da CF) **não está exposto** na API do
SICONFI para os nossos 11 municípios: o RREO-Anexo 08, que é o demonstrativo
desse índice, volta vazio em 2024 e 2025 (os outros anexos respondem normal).

Este é o caminho que **não depende de API nenhuma**.

## Como preencher

1. Abra `2025.csv` (já vem com os 11 municípios e o código IBGE certo).
2. Para cada um, preencha a coluna **`percentual`** com o índice de aplicação
   no ensino. Use vírgula ou ponto, tanto faz (`27,4` ou `27.4`).
3. `valor_aplicado` e `receita_base` são **opcionais** — preencha se tiver.
4. Salve e rode o workflow (GitHub → Actions → "Dados do Painel Prefeituras" →
   Run workflow). O coletor tenta a API primeiro e, não achando, usa este
   arquivo.

## Onde achar o número (fonte oficial)

- **SIOPE / FNDE** — <https://www.fnde.gov.br/siope/> — é o sistema oficial do
  indicador dos 25%.
- **TCE-SP** — <https://transparencia.tce.sp.gov.br/> — traz o índice
  **apurado e julgado** pelo Tribunal, que é mais forte que o declarado.

## Regra de honestidade (CLAUDE.md, regra 5)

- Município que você **não** preencher fica **"sem dado"** — e isso está certo.
  Não chute, não repita o ano anterior, não arredonde "de cabeça".
- Anote de onde tirou. Dado **declarado pelo município** (SIOPE) e dado
  **julgado pelo TCE** não são a mesma coisa; na dúvida, o do TCE vale mais.
- Um percentual errado é pior que nenhum: ele faz o painel **acusar uma
  prefeitura** de descumprir a Constituição. Já aconteceu uma vez, por um bug
  meu, com 9 dos 11.
