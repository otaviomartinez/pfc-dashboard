# Dashboard de Inteligência de Captação (PFC)

App **Streamlit** para priorizar e acompanhar a captação de recursos do
**Programa Futuro Cientista**. O **Google Sheets é o banco de dados ao vivo**:
o app lê e escreve direto na planilha. Sem credenciais, ele cai automaticamente
para o arquivo local `data/empresas.csv` (somente leitura) — e funciona normalmente.

Um selo no topo mostra o modo atual: **🟢 Conectado ao Google Sheets** ou
**🟠 Modo local (CSV)**.

## O que tem
- **Visão geral** — KPIs (organizações, em prospecção, valor-alvo total, oportunidades hoje), funil por status e cobertura regional.
- **Ranking** — tabela por Score PFC com busca e filtro; cada organização abre um **dossiê** completo, onde você **salva observações** e **muda o status** (grava na planilha).
- **Radar** — fila de oportunidades; **Aprovar** grava na aba `Novidades_pendentes` (criada automaticamente).
- **Funil** — kanban de 5 colunas (Mapear, Prospectar, Monitorar, Edital, Ativo) com **arrastar-e-soltar**: mover um card entre colunas chama `atualizar_status()` e grava na planilha.
- **Metodologia** — explica o Score PFC (Aderência 35% · Valor 25% · Região 20% · Acionabilidade 20%).

---

## 1. Como rodar

Pré-requisito: **Python 3.10+** instalado.

```bash
# 1. (opcional, recomendado) crie um ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 2. instale as dependências
pip install -r requirements.txt

# 3. rode o app
streamlit run app.py
```

O app abre em `http://localhost:8501`. **Sem nenhuma configuração extra ele já
funciona em modo CSV**, usando `data/empresas.csv` (123 organizações).

---

## 2. Conectar ao Google Sheets (passo a passo)

Conectar habilita a **escrita ao vivo** (observações, status e leads do radar
voltam para a planilha).

### a) Crie a conta de serviço
1. Acesse <https://console.cloud.google.com/> e crie (ou escolha) um projeto.
2. Em **APIs e Serviços → Biblioteca**, ative **Google Sheets API** e **Google Drive API**.
3. Em **APIs e Serviços → Credenciais → Criar credenciais → Conta de serviço**, crie a conta.
4. Abra a conta criada → aba **Chaves → Adicionar chave → Criar nova chave → JSON**.
   Um arquivo `.json` será baixado.

### b) Prepare a planilha
1. Crie uma planilha no Google Sheets com uma aba chamada **`empresas`**
   (ou deixe o app usar a 1ª aba). Use os mesmos cabeçalhos do `data/empresas.csv`
   — dica: importe o CSV direto para a planilha.
2. Copie o **e-mail da conta de serviço** (campo `client_email` do JSON) e
   **compartilhe a planilha** com esse e-mail como **Editor**.

### c) Preencha os secrets
1. Copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml`.
2. Cole o conteúdo do JSON dentro do bloco `[gcp_service_account]` (todos os campos)
   e informe a planilha em **uma** das opções:

```toml
spreadsheet_url = "https://docs.google.com/spreadsheets/d/SEU_ID/edit"
# ou: spreadsheet_key = "SEU_ID"
# ou: spreadsheet_name = "PFC Captação"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "...@....iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
universe_domain = "googleapis.com"
```

> A `private_key` deve ficar **em uma linha só**, com os `\n` literais
> exatamente como vêm no JSON.

3. Rode `streamlit run app.py`. O selo deve mudar para **Conectado ao Google Sheets**.

---

## Estrutura do projeto
```
PROJETO_PFC/
├── app.py                     # interface (login, 6 páginas, modais, gráficos)
├── src/
│   └── dados.py               # leitura/escrita: Google Sheets ↔ CSV
├── kanban_component/
│   └── index.html             # componente de drag-and-drop (HTML5 nativo, sem libs)
├── radar/                     # Radar de Descoberta (scraper diário, 3 camadas)
│   ├── fontes_ancora.py       # Camada 1: 18 fontes com extração dedicada
│   ├── fontes_genericas.py    # Camada 2: extrator genérico + utilitários
│   ├── config_fontes.json     # Camada 2: URLs (edite sem tocar em código)
│   ├── descoberta.py          # Camada 3: sugestão de novas fontes
│   ├── scorer.py              # pontuação (35/25/20/20)
│   ├── dedup.py               # deduplicação (URL + similaridade de título)
│   ├── main.py                # orquestração (python -m radar.main)
│   └── requirements.txt       # deps mínimas do radar (CI)
├── data/
│   └── empresas.csv           # base de fallback (123 organizações)
├── .streamlit/
│   ├── config.toml            # tema escuro
│   └── secrets.toml.example   # modelo de credenciais (copie p/ secrets.toml)
├── .github/workflows/radar.yml # agendamento diário do radar
├── requirements.txt
├── .gitignore
└── README.md
```

## Notas
- As leituras usam `st.cache_data(ttl=60)` — edições feitas direto na planilha
  aparecem no app em até ~60s (ou clique em **🔄 Atualizar** no Ranking).
- O `Score PFC` no MVP é a coluna já existente na planilha; a aba **Metodologia**
  documenta e visualiza a fórmula de ponderação.
- Segredos ficam só em `.streamlit/secrets.toml`, que **não** vai para o Git.

---

## Radar automático (Radar de Descoberta)

Um scraper diário (`requests` + `BeautifulSoup`, **sem API de IA paga**) varre
editais e oportunidades, pontua pela mesma fórmula do Score PFC (35/25/20/20),
deduplica e grava as aprovadas na aba **`Novidades_pendentes`** — as mesmas que
aparecem na aba **Radar** do app. Arquitetura em 3 camadas para crescer sem
reescrever código:

- **Camada 1** (`radar/fontes_ancora.py`) — 18 fontes verificadas com extração dedicada.
- **Camada 2** (`radar/fontes_genericas.py` + `radar/config_fontes.json`) — extrator genérico para URLs que você adiciona no JSON.
- **Camada 3** (`radar/descoberta.py`) — sugere novas fontes em `radar/fontes_candidatas.csv` (para revisão humana; nunca entra sozinho no radar).

### Rodar manualmente
```bash
pip install -r radar/requirements.txt
python -m radar.main          # sem credenciais → grava em radar/preview_local.csv
```
Saídas: fila em `Novidades_pendentes` (ou `preview_local.csv`), descartes em
`radar/log_filtrados.csv`, candidatas em `radar/fontes_candidatas.csv`.

### Agendamento (GitHub Actions)
O workflow `.github/workflows/radar.yml` roda **todo dia às 09:00 UTC (06:00 Brasília)**
e também sob demanda (aba **Actions → Radar de Descoberta → Run workflow**).

**Configurar os GitHub Secrets** (repositório → *Settings → Secrets and variables → Actions → New repository secret*):
- `GCP_SERVICE_ACCOUNT_JSON` — cole o **conteúdo inteiro** do JSON da conta de serviço.
- `SPREADSHEET_KEY` — o ID da planilha (o trecho entre `/d/` e `/edit` na URL do Google Sheets).

Sem esses secrets, o radar roda mesmo assim e salva em `preview_local.csv` (não falha).

### Adicionar uma fonte nova (Camada 2, sem programar)
Edite **`radar/config_fontes.json`** e acrescente um bloco:
```json
{ "nome": "Fundação Exemplo (editais)", "url": "https://exemplo.org.br/editais", "categoria": "generico", "ativo": true }
```
Salve e faça commit — na próxima execução o radar já varre essa URL pelo extrator
genérico. Para desligar temporariamente uma fonte, troque `"ativo": true` por `false`.
Fontes com `exemplo.org` ou `ativo:false` são ignoradas.
