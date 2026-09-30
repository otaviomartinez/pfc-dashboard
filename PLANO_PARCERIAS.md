# Radar de Parcerias — o quarto radar

> **Nota de origem.** O código (`src/parcerias.py`, `app.py`) cita este arquivo,
> mas ele não tinha sido commitado — o plano ficou só na conversa que construiu a
> tela. Este documento foi **reconstruído a partir do código que está no ar**, e
> não é a transcrição do plano original: descreve o que existe hoje e o que
> ficou em aberto. Onde o código não decide uma coisa, está escrito "em aberto",
> não inventado.

## O que é

Os três primeiros radares perguntam "de onde vem dinheiro?" (Captação),
"quem indica a emenda?" (Emendas) e "quem assina o convênio?" (Prefeituras).
O quarto pergunta **"quem doa material e serviço?"** — empresas e fundações que
sustentam o PFC em espécie, não em edital.

**Regra de ouro, igual à do levantamento de deputados: nada aqui é parceria
confirmada.** Todo item nasce com status `a abordar`; a curadoria é manual; o
código **nunca** inventa contato, valor ou vínculo. Um "candidato a abordar"
escrito como se fosse parceiro fechado quebraria a confiança do Fábio na tela
inteira — é o análogo do "prazo a confirmar" do radar de editais.

## Os quatro módulos do PFC

O parceiro é ligado a um ou mais módulos (campo `modulos`, `"2;3;4"`):

| Módulo | Frente |
|---|---|
| 1 | escolas |
| 2 | desenvolvimento social |
| 3 | Fundação Casa |
| 4 | situação de rua |

## Como o dado circula

1. **Base-semente** `data/parcerias_seed.csv` — 16 candidatos curados à mão
   (fabricantes de material escolar para o módulo 1; fundações do direito da
   criança para os módulos 2/3/4). Coluna `fonte` diz `curadoria inicial (a
   confirmar)` — é rótulo de procedência, não enfeite.
2. **Aba `Parcerias` do Sheets** — `dados.criar_aba_parcerias()` cria a aba e,
   **só na criação**, semeia com o CSV dando um ID sequencial. É **idempotente**:
   se a aba já existe, não re-semeia (senão o trabalho do Fábio seria
   sobrescrito a cada deploy).
3. **A tela** lê a aba quando conectado e **cai no CSV** quando não há Sheets —
   mesma rede de segurança do CRM de deputados.

### Portas de escrita (as únicas)

- `dados.atualizar_status_parceria(id, status)` — grava **só a célula de status**,
  casando por **ID**, e valida contra `PARCERIA_STATUS`
  (`a abordar` · `em contato` · `ativa` · `recusou`). Não toca em nenhum outro campo.
- A ponte para a Prospecção **não cria porta nova**: reusa
  `dados.adicionar_prospeccao` com `Tipo = "Patrocínio"`, com **dedup por nome**
  para não duplicar, e desabilitada offline.

## Camada pura (`src/parcerias.py`)

Sem rede, sem Streamlit, testável: `carregar_parcerias`, `preparar`,
`parse_modulos` (`"2;3;4"` → `[2,3,4]`, tolerante a vírgula e lixo),
`filtrar_parcerias` (módulo/tipo/status/busca, todos opcionais),
`parceiros_por_modulo`, `tipos_disponiveis`, `status_disponiveis` e
`gancho_parceria` — que prioriza o `como_abordar` curado e, quando vazio, compõe
do foco/tipo **sem inventar canal**.

Testes: `tests/test_parcerias.py` e `tests/test_parcerias_tela.py`.

## Verificação dos canais — o que a checagem real mostrou

`scripts/verificar_parcerias.py` (workflow mensal "Verificar canais de
parceria") abre o site de cada parceiro e procura a página de
edital/apoio a projetos/doação, guardando URL, trecho e a **data** em que viu.
Resultado da 1ª checagem (set/2026), nos 16:

| Situação | Nº |
|---|---|
| **Canal que RECEBE PROJETO** (serve ao PFC) | **2** |
| Página institucional, sem canal de submissão | 5 |
| Doação ao próprio parceiro (direção inversa) | 2 |
| Site não respondeu ao robô | 5 |
| Nada encontrável / sem site na base | 2 |

Os dois que servem: **Fundação Roberto Marinho** (edital) e **Instituto Ayrton
Senna** (apoio a projetos).

**Três lições que viraram código:**
1. **Direção importa mais que existência.** A 1ª versão contou "Como doar" como
   achado bom — mas é o público doando PARA o parceiro, o contrário do que o
   PFC precisa. Cada canal carrega agora uma `direcao`.
2. **O nome do parceiro não é indício.** "instituto"/"fundação" estão no nome de
   metade deles; isso fez o Instituto Alana apontar para uma página do Facebook.
   Esses termos saíram, e rede social entrou no ruído.
3. **Site grande bloqueia robô.** BIC, Nestlé, Instituto Coca-Cola, Instituto
   Carrefour e Fundação Telefônica não responderam nem pela variante `www`.
   Para eles, o caminho é manual — e o painel diz isso, em vez de fingir.

**O que "canal encontrado" significa:** existe a página. **Não** significa
programa aberto agora, nem que aceita o tipo de projeto do PFC.

## Em aberto

- **Nunca foi visto rodando.** Dois commits dizem literalmente "[verificar layout
  no ar]" e "[verificar no app publicado]": o card no hub (aqua, canto inferior
  esquerdo) e a entrada no menu precisam de conferência visual no Streamlit.
- **A aba `Parcerias` do Sheets só nasce na primeira execução conectada** — até
  lá a tela roda do CSV e o status não persiste.
- **Migrar a curadoria para o Sheets** (o Fábio editando ao vivo) é escrita de
  produção e depende de OK explícito dele.
- **Contatos dos parceiros**: a base tem `site`, não tem e-mail nem telefone.
  Preencher isso é curadoria manual — não há cadastro público de "canal de
  doação" (mesmo beco dos contatos de prefeitura).
