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
