# PFC — Dashboard de Inteligência de Captação

Sistema de captação de recursos do **Programa Futuro Cientista** (UFSCar Sorocaba).
Streamlit + Google Sheets + GitHub Actions. Coordenador do projeto: Prof. Fábio Leite.

Duas frentes, escolhidas num **hub** de entrada:
- **Captação Privada** — radar automático que varre dezenas de fontes/dia atrás de **captação** (editais, chamadas, prêmios institucionais, patrocínio — só dinheiro que o PFC pode captar, com filtro de elegibilidade); identidade âmbar
- **Emendas Parlamentares** — CRM de relacionamento com deputados (manual) **+** levantamento automático de "quem abordar" a partir da execução de emendas e dos contatos oficiais da ALESP (identidade violeta)

## Como trabalhar comigo

- **Responda sempre em português do Brasil.** Sou estudante de 1º ano, iniciante em código — explique o "porquê" em linguagem simples antes de aplicar mudanças grandes.
- **Uma tela / um assunto por vez.** Teste antes de commitar, commite antes de seguir.
- Mensagens de commit no formato `fix:`, `feat:`, `visual:` + descrição curta em português.
- Antes de mudanças grandes, crie uma tag git de segurança e me diga como reverter.
- Se algo que eu pedi conflitar com uma funcionalidade que já existe, **me avise antes de mudar** — funcionalidade tem prioridade sobre visual.

## Regras que não podem ser quebradas

1. **O drag-and-drop dos funis grava status no Google Sheets** — tanto o de Captação (empresas) quanto o de Emendas (deputados). Nunca quebre esse caminho. Mexeu no kanban? Teste a gravação. Os dois reusam o mesmo componente (`kanban_component`, não modifique sem testar os dois); a gravação de deputado é `dados.atualizar_status_deputado` (escreve só a célula Status).
2. **O campo "Diálogo" dos deputados é sensível** (anotações de negociação, nomes de assessores, telefones). Só renderiza para usuário logado. Nunca exponha em versão pública nem commite o CSV.
3. **Acurácia de datas de edital é prioridade.** Só mostre "faltam X dias" quando a data for confiável; se for estimada ou incerta, marque "prazo a confirmar". **Uma data errada é pior que nenhuma** — já tivemos um edital exibido como 2027 por chute de ano.
4. Nunca commite `secrets.toml` nem o CSV dos deputados.

## Design system

- Base cinza-ardósia **#0E1116** (nunca preto puro), elevação em camadas.
- Acento de marca: **#E8873A** (âmbar, Captação) / **#8B7BF0** (violeta, Emendas).
- Fontes: **Inter** (texto) + **JetBrains Mono** (rótulos e números técnicos).
- **Cor é semântica, não decorativa:** verde `#4ADE80` = aderência alta (60+), âmbar `#E8B54A` = média (50–59), cinza `#7C8698` = baixa (<50), `#F0663F` = prazo urgente. Sempre com legenda explicando o significado.
- Cards no estilo "glowcard": borda em gradiente + brilho suave no canto + ícone SVG num quadrado colorido.
- **Hierarquia primeiro:** uma métrica-herói grande responde a pergunta principal em 2 segundos; o resto diminui em tamanho e peso.
- **Quase tudo deve ser clicável e levar a algo real** — KPIs, linhas, etapas do funil. Nada de tela morta nem clique que abre placeholder.
- Ícones: SVG limpos. Não use emoji na interface.

### Sidebar dos painéis — dois modos, nunca escondida

- **Ícones (60px)** é o padrão: só os SVGs das telas, item ativo com fundo no acento do painel + barrinha lateral, e o nome aparecendo como tooltip no hover.
- **Expandida (250px)** mostra os nomes. Alterna por um **botão de recolher no TOPO do rail** (`.pfc-sb-toggle`, dentro da própria sidebar, com respiro e um divisor `.pfc-sb-sep` separando dos itens). Chevron `»` no modo ícone (expandir) / `«` + rótulo no modo expandido (recolher).
- **O toggle é 100% CLIENT-SIDE, sem rerun** (`_SIDEBAR_TOGGLE_JS` + `_SIDEBAR_TOGGLE_CORE`): o estado vive na classe **`pfc-sb-open` no `<html>`** (o React do Streamlit não gerencia o `<html>`, então a classe **sobrevive aos reruns** e não pisca). A largura anima por **timer JS** (`setInterval` + easeOutCubic), NÃO por `transition:width`. O CSS do modo aberto é o `_SIDEBAR_OPEN_CSS`, keyed em `html.pfc-sb-open …` (especificidade maior — vence sem depender da ordem de injeção). **Não há mais estado Python** (`sidebar_expandida` foi aposentado).
- **Não existe modo "escondida".** Existiu por um commit e foi aposentado: menos estados, e nenhum caminho em que o usuário fique sem navegação. Se pedirem "recolher a sidebar de vez", lembre que isso reabre o risco de ficar preso.
- O rótulo de `st.button` é texto puro e **não aceita HTML** — por isso ícone e tooltip dos itens de navegação entram por CSS, via a classe `st-key-<chave>` que o Streamlit põe no container. Ver `css_icones_botoes`. Por isso também as chaves dos botões são slugs ASCII: chave com espaço ou acento não vira seletor válido.

## Emendas — como o painel está montado

Duas coisas convivem no painel de Emendas e **não se misturam**:

**1. CRM dos deputados do Fábio** — aba `Deputados` no Google Sheets (mesma
planilha das empresas). Relacionamento manual: diálogo, temperatura, status,
contatos pessoais/de assessor. Sensível (regra 2). Porta única: leitura
`dados.carregar_deputados`; escrita `dados.adicionar_deputado_crm` (puxar),
`dados.atualizar_status_deputado` (arrastar no funil), `dados.atualizar_deputado`
(editar diálogo/temperatura/status/observações no **dossiê**, só as células que
mudaram) e `dados.anexar_dialogo_deputado` (**observação rápida** clicando num
card do funil — anexa datado ao mesmo campo Diálogo). Edição só para logado
(regra 2); contatos OFICIAIS da ALESP são só-leitura. Detalhes na seção Armadilhas.

**2. Levantamento público "quem abordar"** — descoberta automática, separada do
CRM, a partir de dado oficial:
- **Extrator** `src/emendas.py`: lê a execução de emendas estaduais 2023-2025
  dos painéis Power BI do Transparência SP (endpoint `querydata`; se o
  `resourceKey` rotacionar, cai para arquivo baixado à mão em
  `data/emendas_manual/`). PAGO e AUTORIZADO sempre separados; TRANSFERÊNCIA
  ESPECIAL fica fora do recorte educação/social.
- **Ranking em duas seções** (só titulares em exercício da ALESP):
  `data/emendas_ranking_pfc_territorio.csv` ("Abordar já" — quem já financia
  edu/social nos nossos municípios) e `..._expansao.csv` ("Cortejar" — alto
  volume geral, ainda fora, em camadas prioritário/demais). Score composto com
  vizinhança geográfica (Regiões Imediatas IBGE 2017, `data/ibge_regioes_imediatas_sp.csv`).
- **Config editável** `config/pfc_municipios.toml`: municípios do PFC em grupos
  com pesos, pesos do score, fator de vizinhança, mínimo de emendas. Mudou algo
  aqui? Rode `python -m src.emendas` para regenerar os rankings.
- **Referência pública** `data/deputados_alesp_titulares.csv`: os 94 titulares +
  contatos oficiais (email de gabinete, telefone, página ALESP), do XML oficial.

**Tela "Descobrir"** (aba do painel): as duas seções, cada deputado num
**card clicável por inteiro** (abre o dossiê; o botão "Puxar" é a exceção,
z-index acima do overlay). No topo do dossiê, o **"melhor argumento de abordagem"**
(`_argumento_abordagem`): uma frase-gancho composta só do dado real (município do
PFC, valor edu/social, fatia, vizinhança), escolhendo o argumento mais forte
disponível (território direto > vizinhança > alinhamento proporcional > volume);
sem gancho forte, diz algo honesto — nunca inventa. Abaixo: score, autorizado vs
pago (rotulados, nunca somados), municípios diretos/vizinhos e o contato OFICIAL.
**"Puxar para o CRM"** grava o deputado como nova linha na aba `Deputados`.

**Contatos: dois tipos que não se misturam.** Os 3 campos OFICIAIS (`Email
Oficial`, `Telefone Gabinete`, `Página ALESP`) são públicos, da ALESP,
preenchidos por código (marca "não encontrado" quem não é titular). Os campos
`Email`, `Telefones`, `WhatsApp`, `Instagram` são do Fábio (pessoal/assessor,
sensível) — o código **nunca** escreve por cima deles.

## Radar de Captação — como está

Pipeline em `radar/` (roda no GitHub Actions, `radar.yml`, cron 06:00 Brasília;
`python -m radar.main`). Grava na aba `Novidades_pendentes` do Sheets. **Escrita
é append-only + dedup** — nunca apaga linha; o filtro novo só barra lixo NOVO, o
antigo fica até ser triado no app (rodar o radar não "substitui" a fila).

- **Só captação, por ELEGIBILIDADE (não tema estreito).** Vale qualquer dinheiro
  que o PFC pode captar: educação, ciência, juventude, impacto social,
  comunitário, inovação, formação, prêmio institucional, patrocínio. O filtro
  (`radar/scorer.py`) barra no pré-filtro: oportunidade-para-aluno
  (`NEGATIVAS_ALUNO`: olimpíada, medalha, premiação de estudante, bolsa de
  participante) e o inaplicável (`NAO_ELEGIVEL`: bem-estar animal, saúde
  hospitalar/clínica, recorte étnico/aldeia indígena). A antiga whitelist
  `FONTES_CONTEXTO_EDITAL` foi removida — toda fonte passa pelo mesmo crivo.
- **Fontes** (`radar/fontes_ancora.py`): removidas as de olimpíada (OBMEP, OBA,
  OBBiotec, Comunidade Científica Jr) e as feiras (FEBRACE, MOSTRATEC) — serviam
  à missão, não à captação. Adicionadas **Capta** (via `www.capta.org.br` — o
  apex falha DNS) e **Rede Filantropia** (editais em `/informacao/<slug>`, extraídos
  por link, cortando o curso pago do dialogosocial).
- **Datas v2** (`radar/prazos.py` + `radar/publicacao.py`), regra 3 — nunca chuta
  o ano: **âncoras em camadas** (`prazo de inscrição`, `inscrições até`,
  `recebimento de propostas`, `data limite`; descarta o "até" puro, que pegava a
  data de execução errada). Ano do prazo por extenso vem do texto; se faltar,
  é inferido da **data de publicação SÓ de metadado estruturado**
  (`publicacao.data_publicacao`: JSON-LD `datePublished`/og/`<time>`). Sem ano e
  sem metadado → "a confirmar". `_prazo_confiavel` (−60..180) + corte de vencido
  antigo são a 3ª linha.
- **Relatório de Prioridades** (tela + PDF, `src/relatorios.py` com ReportLab):
  cada painel tem o seu. Captação = editais futuros por urgência (respeita a
  regra 3). Emendas = quem abordar (território + expansão), autorizado/pago
  separados, contato oficial.

## Armadilhas conhecidas deste projeto

- **Custom Components v2 travam certas animações CSS.** `transition:visibility`, `transition:width` e `animation` com `scaleX` já congelaram elementos (largura ficou em zero, dropdown abrindo e fechando sozinho) — e `!important` inline foi ignorado. O padrão não está totalmente mapeado. **Solução:** use valores diretos no HTML, `display` em vez de `visibility`, ou anime via `setInterval`/`setTimeout` no JS (funciona). Se um elemento parecer "morto", suspeite disso primeiro.
- `requestAnimationFrame` **não roda** no runtime dos componentes v2. Use timers.
- **A sidebar some intermitentemente** (o Streamlit não monta o elemento na transição hub → painel). Mitigado pela barra de navegação superior fixa, que é independente da sidebar — é a rede de segurança para o usuário nunca ficar preso. A recuperação automática (`_preparar_sidebar` → `_SIDEBAR_FIX_JS`, que clica no botão nativo de expandir até a barra aparecer) roda **em todo render, sem exceção**. Já houve uma versão em que ela era desligada quando o usuário recolhia de propósito; se voltar a existir um caso desses, esse desvio volta junto — evite. O bug em si ainda não foi eliminado.
- **Listener injetado por `components.html` MORRE ao trocar de painel — instale no realm do PAI.** Um `addEventListener` registrado de DENTRO do iframe do `components.html` (mesmo apontando para `window.parent.document`) é uma closure do realm daquele iframe. Ao trocar de painel, o Streamlit **destrói e recria** esse iframe (`render_sidebar` vs `render_sidebar_emendas` ocupam posições diferentes na árvore) e o listener **para de disparar**; uma trava única no `window`-pai ainda impede re-registrar → o controle quebra num painel e contamina o outro. **Solução (usada no toggle da sidebar):** injetar o núcleo como um `<script>` no `<head>` do PAI (`_SIDEBAR_TOGGLE_JS` faz isso uma vez, guard `__pfcSbInstalled`); aí o listener é dono do `window`-pai e sobrevive a qualquer recriação de iframe / rerun / troca de painel. Vale para QUALQUER listener persistente feito via `components.html`.
- **Um ponto de CSS da sidebar ainda quebra em silêncio** (o outro, de ordem/especificidade, foi resolvido usando `html.pfc-sb-open …`, mais específico, que vence sem depender da ordem de injeção):
  - **`overflow:visible` na cadeia da sidebar**: o tooltip do modo ícone é um `::after` que precisa vazar para fora dos 60px. Ele depende de `overflow:visible` declarado em **todos** os ancestrais (sidebar → container → `stVerticalBlock` → `stElementContainer` → `stButton`). Um `overflow:hidden` em qualquer um deles corta o balão. Se um dia a sidebar precisar de scroll próprio, esse tooltip precisa de outra solução (por exemplo `position:fixed` posicionado por JS).
- **Três paletas paralelas de cor de etapa** (`CORES_ETAPA`, `CORES_STATUS`, `ACENTOS_HEX`) precisam ser mantidas em sincronia manualmente. Frágil — deveriam virar uma só.
- `app.py` chegou a **5.273 linhas** (componentes v2 com CSS/JS como strings Python). A modularização começou, incremental: o **passo 1** extraiu todo o CSS/JS/SVG (33 constantes, ~1.9k linhas) para **`ui/estilos.py`**, que o `app.py` importa de volta — hoje `app.py` tem **~3.366 linhas**. `ui/estilos.py` é só apresentação (sem lógica/runtime), na ordem original para respeitar dependências internas (ex.: `_SIDEBAR_TOGGLE_JS` usa `_SIDEBAR_TOGGLE_CORE`). **Passo 2 pendente** (extrair helpers puros de formatação para `ui/formato.py`). Não modularizar durante fase de entrega.
- **CRM de deputados no Google Sheets — a escrita tem invariantes que quebram em silêncio se ignoradas.** Aba `Deputados`, mesma planilha das empresas; leitura/escrita só pela porta única (`dados.carregar_deputados` / `adicionar_deputado_crm` / `atualizar_status_deputado`). O CSV `data/deputados_estaduais.csv` segue fora do git como **rede de segurança de leitura** (fallback se o Sheets cair); nesse modo a escrita fica **bloqueada**, para as duas fontes não divergirem.
  - **Puxar** (`adicionar_deputado_crm`): **append-only + RAW** — nunca regrava linha existente; guarda tudo como texto (um Diálogo com `=` não vira fórmula). Recusa duplicata por nome normalizado/contido ("Danilo Balas" ↔ "Agente Federal Danilo Balas").
  - **Arrastar no funil** (`atualizar_status_deputado`): escreve **só a célula de Status** — diálogo, temperatura e contatos ficam intactos. Não cria linha.
  - Leitura/escrita **por nome de coluna**, então coluna nova na aba flui sozinha. Isso destravou o deploy: o painel de Emendas não fica mais vazio fora da máquina local.

## Fila de trabalho

**Já feito (última leva):**
- **Emendas — levantamento completo dos 94:** extrator Power BI 2023-25, rankings
  território/expansão, config editável, vizinhança IBGE; tela **Descobrir** com
  card clicável; ponte **puxar para o CRM**; **contatos oficiais** da ALESP;
  **drag-and-drop** no funil; **melhor argumento de abordagem** no dossiê.
- **CRM migrado para o Sheets** (aba `Deputados`) e **edição pela tela**: editar
  diálogo/temperatura/status/observações no dossiê (`atualizar_deputado`) e
  **observação rápida** no card do funil (`anexar_dialogo_deputado`).
- **Relatório de Prioridades** (tela + PDF) nos dois painéis (ReportLab).
- **Radar de Captação:** limpeza (só captação + filtro de elegibilidade, fim das
  fontes de olimpíada/feira), fontes **Capta** e **Rede Filantropia**, e
  **enriquecimento de datas v2** (âncoras em camadas + inferência de ano por
  metadado, nunca chuta). Ver "Radar de Captação — como está".
- **Sidebar:** botão de recolher/expandir **no topo do rail**, 100% client-side
  (sem rerun); pontinho de status = cor de saúde (verde/vermelho).

**Próximo trabalho — EM ANDAMENTO: melhorar a cobertura de datas do radar.**
Diagnóstico feito (fila real: 31 itens, só **7 com data**). **7 NÃO é o teto** —
dos 24 sem data, quase nenhum é impossível: ~16-18 são recuperáveis, e o grosso
com engenharia BARATA. Duas correções pendentes, nesta ordem:
1. **Usar a data "post publicado: 2026" do CORPO dos posts da captadores/ABCR como
   âncora do ano**, em vez do JSON-LD `datePublished` (que fica STALE no ano
   original, 2021/2017, e faz a inferência resolver pro passado e ser descartada).
   A data real de 2026 está visível no corpo — parsear ela recupera ~13 itens
   sem sair da página.
2. **Ampliar as âncoras de prazo, que estão estreitas demais** — perdem frases
   comuns MESMO com o ano escrito (ex.: "inscrições podem ser feitas até 22 de
   julho **de 2026**", "inscrições: em andamento, até 17 de julho **de 2026**").
   Recupera Glocal, Cecierj, tidesetubal etc.
Só isso levaria de **7 para ~20+**. (3ª camada, mais pesada: seguir o link ao
edital original — confirmado que funciona. Caso difícil de verdade: as ~5 notícias
do MCTI que não trazem o prazo na página, só no sistema de chamadas.)

**Depois:**
- Notificação por **e-mail** quando faltarem 15 dias para um prazo.
- **Deputado federal e senador** (aguardando as tabelas do Fábio).

**Futuro (conversar antes):**
- Aba "Prefeituras": escolas (estaduais e municipais) e unidades do CRAS por cidade de SP, para plano de expansão.
- Estatísticas por parlamentar: que emendas cada um liberou (edu/social) e em que região.
- Reatualizar o levantamento a cada novo ciclo de emendas (rerodar o extrator; os deputados são lista quase fixa, o que muda são as emendas).

**Faxina (só depois da entrega):** unificar as paletas de etapa; continuar a modularização do `app.py` (passo 1 — CSS/JS → `ui/estilos.py` — feito; passo 2 — helpers puros → `ui/formato.py` — pendente).
