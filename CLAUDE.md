# PFC — Dashboard de Inteligência de Captação

Sistema de captação de recursos do **Programa Futuro Cientista** (UFSCar Sorocaba).
Streamlit + Google Sheets + GitHub Actions. Coordenador do projeto: Prof. Fábio Leite.

Duas frentes, escolhidas num **hub** de entrada:
- **Captação Privada** — radar automático que varre 38 fontes/dia atrás de editais e prêmios (identidade âmbar)
- **Emendas Parlamentares** — CRM de relacionamento com deputados; dado manual, não descoberta automática (identidade violeta)

## Como trabalhar comigo

- **Responda sempre em português do Brasil.** Sou estudante de 1º ano, iniciante em código — explique o "porquê" em linguagem simples antes de aplicar mudanças grandes.
- **Uma tela / um assunto por vez.** Teste antes de commitar, commite antes de seguir.
- Mensagens de commit no formato `fix:`, `feat:`, `visual:` + descrição curta em português.
- Antes de mudanças grandes, crie uma tag git de segurança e me diga como reverter.
- Se algo que eu pedi conflitar com uma funcionalidade que já existe, **me avise antes de mudar** — funcionalidade tem prioridade sobre visual.

## Regras que não podem ser quebradas

1. **O drag-and-drop do funil grava status no Google Sheets.** Nunca quebre esse caminho. Mexeu no kanban? Teste a gravação.
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

## Armadilhas conhecidas deste projeto

- **Custom Components v2 travam certas animações CSS.** `transition:visibility`, `transition:width` e `animation` com `scaleX` já congelaram elementos (largura ficou em zero, dropdown abrindo e fechando sozinho) — e `!important` inline foi ignorado. O padrão não está totalmente mapeado. **Solução:** use valores diretos no HTML, `display` em vez de `visibility`, ou anime via `setInterval`/`setTimeout` no JS (funciona). Se um elemento parecer "morto", suspeite disso primeiro.
- `requestAnimationFrame` **não roda** no runtime dos componentes v2. Use timers.
- **A sidebar some intermitentemente** (o Streamlit não monta o elemento na transição hub → painel). Mitigado pela barra de navegação superior fixa, que é independente da sidebar — é a rede de segurança para o usuário nunca ficar preso. O bug em si ainda não foi eliminado.
- **Três paletas paralelas de cor de etapa** (`CORES_ETAPA`, `CORES_STATUS`, `ACENTOS_HEX`) precisam ser mantidas em sincronia manualmente. Frágil — deveriam virar uma só.
- `app.py` passou de 3.600 linhas (componentes v2 com CSS/JS como strings Python). Quebrar em módulos é desejável, mas **não durante uma fase de entrega**.
- O CSV dos deputados está fora do git: **em deploy, o painel de Emendas aparece vazio.** Resolver migrando os deputados para uma aba do Google Sheets.

## Fila de trabalho

**Visual (pendente):**
- Sidebar de Emendas: espaçamento entre itens e trocar emojis por ícones SVG
- Esconder a toolbar nativa do Streamlit (botão "Deploy" sobrepõe a barra superior)
- Botão visível de recolher/reexibir a sidebar nos dois painéis
- Hub ainda mostra "4 diálogos" fixo no card de Emendas (deve ler o dado real)

**Features, nesta ordem:**
1. Acurácia das datas dos editais (protege a credibilidade do sistema)
2. Migrar deputados do CSV para o Google Sheets (destrava o deploy)
3. Deputado federal e senador (aguardando as tabelas do Fábio)
4. Relatório de Prioridades (botão que gera página/PDF do que está vencendo: instituição, data final, valor)
5. Notificação por **e-mail** quando faltarem 15 dias para um prazo
6. Buscar e-mails e contatos oficiais dos deputados

**Futuro (agosto+, conversar antes):**
- Levantamento atualizável dos 94 deputados estaduais de SP, com ranking de alinhamento ao PFC (educação/social), região que mais financia e contatos. Não é radar diário — deputados são lista quase fixa; o que muda são as emendas por ciclo.
- Aba "Prefeituras": escolas (estaduais e municipais) e unidades do CRAS por cidade de SP, para plano de expansão
- Estatísticas por parlamentar: que emendas cada um liberou (filtrando educação/social) e em que região

**Faxina (só depois da entrega):** unificar as paletas, quebrar `app.py` em módulos.
