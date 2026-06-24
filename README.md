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
├── app.py                     # interface (login, 5 páginas, modais, gráficos)
├── src/
│   └── dados.py               # leitura/escrita: Google Sheets ↔ CSV
├── kanban_component/
│   └── index.html             # componente de drag-and-drop (HTML5 nativo, sem libs)
├── data/
│   └── empresas.csv           # base de fallback (123 organizações)
├── .streamlit/
│   ├── config.toml            # tema escuro
│   └── secrets.toml.example   # modelo de credenciais (copie p/ secrets.toml)
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
