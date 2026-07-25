# PFC — Dashboard de Inteligência de Captação

Sistema de captação de recursos do **Programa Futuro Cientista** (UFSCar Sorocaba).
Streamlit + Google Sheets + GitHub Actions. Coordenador do projeto: Prof. Fábio Leite.

Duas frentes, escolhidas num **hub** de entrada:
- **Captação Privada** — radar automático que varre 38 fontes/dia atrás de editais e prêmios (identidade âmbar)
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
- **Expandida (250px)** mostra os nomes. Alterna pelo botão `.tn-sb`, na barra fixa superior — que fica **fora** da sidebar de propósito, para continuar clicável em qualquer modo.
- **Não existe modo "escondida".** Existiu por um commit e foi aposentado: menos estados, e nenhum caminho em que o usuário fique sem navegação. Se pedirem "recolher a sidebar de vez", lembre que isso reabre o risco de ficar preso.
- Quem manda é o Python: `st.session_state["sidebar_expandida"]`, alternado em `render_topnav`. Ausente = modo ícone.
- O rótulo de `st.button` é texto puro e **não aceita HTML** — por isso ícone e tooltip entram por CSS, via a classe `st-key-<chave>` que o Streamlit põe no container. Ver `css_icones_botoes`. Por isso também as chaves dos botões são slugs ASCII: chave com espaço ou acento não vira seletor válido.

## Emendas — como o painel está montado

Duas coisas convivem no painel de Emendas e **não se misturam**:

**1. CRM dos deputados do Fábio** — aba `Deputados` no Google Sheets (mesma
planilha das empresas). Relacionamento manual: diálogo, temperatura, status,
contatos pessoais/de assessor. Sensível (regra 2). Porta única: leitura
`dados.carregar_deputados`; escrita `dados.adicionar_deputado_crm` (puxar) e
`dados.atualizar_status_deputado` (arrastar no funil). Detalhes de gravação nas
Armadilhas.

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
z-index acima do overlay). O dossiê traz score, autorizado vs pago (rotulados,
nunca somados), municípios diretos/vizinhos e o contato OFICIAL. **"Puxar para
o CRM"** grava o deputado como nova linha na aba `Deputados`.

**Contatos: dois tipos que não se misturam.** Os 3 campos OFICIAIS (`Email
Oficial`, `Telefone Gabinete`, `Página ALESP`) são públicos, da ALESP,
preenchidos por código (marca "não encontrado" quem não é titular). Os campos
`Email`, `Telefones`, `WhatsApp`, `Instagram` são do Fábio (pessoal/assessor,
sensível) — o código **nunca** escreve por cima deles.

## Armadilhas conhecidas deste projeto

- **Custom Components v2 travam certas animações CSS.** `transition:visibility`, `transition:width` e `animation` com `scaleX` já congelaram elementos (largura ficou em zero, dropdown abrindo e fechando sozinho) — e `!important` inline foi ignorado. O padrão não está totalmente mapeado. **Solução:** use valores diretos no HTML, `display` em vez de `visibility`, ou anime via `setInterval`/`setTimeout` no JS (funciona). Se um elemento parecer "morto", suspeite disso primeiro.
- `requestAnimationFrame` **não roda** no runtime dos componentes v2. Use timers.
- **A sidebar some intermitentemente** (o Streamlit não monta o elemento na transição hub → painel). Mitigado pela barra de navegação superior fixa, que é independente da sidebar — é a rede de segurança para o usuário nunca ficar preso. A recuperação automática (`_preparar_sidebar` → `_SIDEBAR_FIX_JS`, que clica no botão nativo de expandir até a barra aparecer) roda **em todo render, sem exceção**. Já houve uma versão em que ela era desligada quando o usuário recolhia de propósito; se voltar a existir um caso desses, esse desvio volta junto — evite. O bug em si ainda não foi eliminado.
- **Dois pontos de CSS da sidebar quebram em silêncio** — nenhum dos dois gera erro, a interface só para de funcionar direito:
  - **Ordem de injeção e especificidade** (bloco `SIDEBAR` do CSS global — procure por "ATENÇÃO"): o CSS global é o modo ícone (60px `!important`); o `_SIDEBAR_EXPANDIDA_CSS` só vence porque é injetado **depois**, em `_preparar_sidebar()`, e porque repete os seletores para empatar com a variante `[aria-expanded="false"]`. Mover a injeção para antes, ou baixar a especificidade, e o botão de expandir deixa de funcionar — parecendo bug no botão.
  - **`overflow:visible` na cadeia da sidebar**: o tooltip do modo ícone é um `::after` que precisa vazar para fora dos 60px. Ele depende de `overflow:visible` declarado em **todos** os ancestrais (sidebar → container → `stVerticalBlock` → `stElementContainer` → `stButton`). Um `overflow:hidden` em qualquer um deles corta o balão. Se um dia a sidebar precisar de scroll próprio, esse tooltip precisa de outra solução (por exemplo `position:fixed` posicionado por JS).
- **Três paletas paralelas de cor de etapa** (`CORES_ETAPA`, `CORES_STATUS`, `ACENTOS_HEX`) precisam ser mantidas em sincronia manualmente. Frágil — deveriam virar uma só.
- `app.py` passou de 3.600 linhas (componentes v2 com CSS/JS como strings Python). Quebrar em módulos é desejável, mas **não durante uma fase de entrega**.
- **CRM de deputados no Google Sheets — a escrita tem invariantes que quebram em silêncio se ignoradas.** Aba `Deputados`, mesma planilha das empresas; leitura/escrita só pela porta única (`dados.carregar_deputados` / `adicionar_deputado_crm` / `atualizar_status_deputado`). O CSV `data/deputados_estaduais.csv` segue fora do git como **rede de segurança de leitura** (fallback se o Sheets cair); nesse modo a escrita fica **bloqueada**, para as duas fontes não divergirem.
  - **Puxar** (`adicionar_deputado_crm`): **append-only + RAW** — nunca regrava linha existente; guarda tudo como texto (um Diálogo com `=` não vira fórmula). Recusa duplicata por nome normalizado/contido ("Danilo Balas" ↔ "Agente Federal Danilo Balas").
  - **Arrastar no funil** (`atualizar_status_deputado`): escreve **só a célula de Status** — diálogo, temperatura e contatos ficam intactos. Não cria linha.
  - Leitura/escrita **por nome de coluna**, então coluna nova na aba flui sozinha. Isso destravou o deploy: o painel de Emendas não fica mais vazio fora da máquina local.

## Fila de trabalho

**Já feito (fase Emendas, esta leva):** CRM migrado para o Sheets; levantamento
completo dos 94 (extrator Power BI 2023-25, rankings território/expansão, config
editável, vizinhança IBGE); tela **Descobrir** com card clicável; ponte **puxar
para o CRM**; **contatos oficiais** da ALESP; **drag-and-drop** no funil de
Emendas. **Fase visual: encerrada** — mudança visual nova é escopo novo, não fila.

**Próximo trabalho — nesta ordem:**
1. **Editar informações do deputado pela tela.** Hoje dá para puxar e arrastar a
   etapa; falta editar diálogo, temperatura e contatos pelo app, gravando no
   Sheets pela porta única (`dados`), respeitando o campo sensível (regra 2).
2. **Relatório de Prioridades** — botão que gera página/PDF do que está vencendo
   (instituição, data final, valor).
3. **Acurácia das datas dos editais** (frente Captação; regra 3 — uma data
   errada é pior que nenhuma). Ainda pendente.
4. Notificação por **e-mail** quando faltarem 15 dias para um prazo.
5. **Deputado federal e senador** (aguardando as tabelas do Fábio).

**Futuro (conversar antes):**
- Aba "Prefeituras": escolas (estaduais e municipais) e unidades do CRAS por cidade de SP, para plano de expansão.
- Estatísticas por parlamentar: que emendas cada um liberou (edu/social) e em que região.
- Reatualizar o levantamento a cada novo ciclo de emendas (rerodar o extrator; os deputados são lista quase fixa, o que muda são as emendas).

**Faxina (só depois da entrega):** unificar as paletas de etapa, quebrar `app.py` em módulos.
