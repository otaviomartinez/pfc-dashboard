"""
Camada de dados do Dashboard de Inteligência de Captação (PFC).

O Google Sheets é o banco de dados AO VIVO. Quando há credenciais de conta de
serviço em st.secrets["gcp_service_account"], o app LÊ e ESCREVE direto na
planilha (sincronização real). Sem credenciais — ou se a conexão falhar — ele
cai automaticamente para o arquivo local `data/empresas.csv` em modo somente
leitura.

Funções públicas:
    carregar_empresas()            -> (DataFrame, modo_conectado: bool)   [cacheada, ttl=60s]
    criar_aba_novidades()          -> bool   (True = criada agora · False = já existia/indisponível)
    adicionar_lead_radar(lead)     -> {"sucesso": bool, "mensagem": str}
    salvar_observacao(id, texto)   -> {"sucesso": bool, "mensagem": str}
    atualizar_status(id, status)   -> {"sucesso": bool, "mensagem": str}
    limpar_caches()                -> None   (força nova leitura/reconexão)
    modo_conexao()                 -> "sheets" | "csv"

Regras:
    * Leituras usam st.cache_data(ttl=60); ESCRITAS nunca são cacheadas.
    * TODAS as funções de escrita são protegidas por try/except e degradam com
      elegância, devolvendo a mensagem de erro para o app exibir (st.warning).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

# --------------------------------------------------------------------------- #
# Configuração de colunas e caminhos
# --------------------------------------------------------------------------- #
CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "empresas.csv"

# Aba (worksheet) com a base de organizações dentro da planilha Google.
ABA_DADOS = "empresas"
# Aba onde o Radar grava as oportunidades aprovadas.
ABA_PENDENTES = "Novidades_pendentes"
# Aba opcional de editais privados (prazos).
ABA_EDITAIS = "Editais_Privados"
# Cabeçalho EXATO da aba de novidades.
HEADERS_NOVIDADES = [
    "Data", "Fonte", "Título", "Descrição", "Score Aderência",
    "Prazo", "Valor estimado", "Link da fonte", "Status aprovação",
]

# Nomes EXATOS das colunas, conforme a planilha / o CSV.
COL_ID = "ID"
COL_PRIORIDADE = "Prioridade"
COL_SCORE = "Score PFC"
COL_SEMAFORO = "Semáforo"
COL_EMPRESA = "Empresa/Grupo"
COL_INSTITUTO = "Instituto/Fundação/Programa"
COL_SETOR = "Setor"
COL_SUBSETOR = "Subsetor"
COL_TIPO = "Tipo de oportunidade"
COL_MODALIDADE = "Modalidade de apoio"
COL_VMIN = "Valor mín. estimado"
COL_VMAX = "Valor máx. estimado"
COL_VALVO = "Valor alvo PFC"
COL_STATUS = "Status"
COL_CHANCE = "Chance (%)"
COL_PRESENCA = "Presença em municípios PFC"
COL_REGIAO = "Municípios/Região estratégica"
COL_SEDE = "Cidade-sede/Unidade estratégica"
COL_UF = "UF"
COL_PUBLICO = "Público-alvo"
COL_ENCAIXE = "Encaixe com PFC"
COL_PROPOSTA = "Proposta PFC recomendada"
COL_PROX_ACAO = "Próxima ação"
COL_RESP = "Responsável"
COL_EDITAL = "Edital/Programa"
COL_JANELA = "Janela provável"
COL_URL = "Fonte/URL"
COL_CONTATO = "Contato sugerido"
COL_CANAL = "E-mail/Canal"
COL_SOCIAL = "LinkedIn/Instagram"
COL_OBS = "Observações"
COL_VERIF = "Fonte verificada"

# Colunas tratadas como numéricas.
COLS_NUMERICAS = [COL_SCORE, COL_CHANCE, COL_VMIN, COL_VMAX, COL_VALVO]

# Os 5 status válidos do funil (ordem do kanban).
STATUS_FUNIL = ["Mapear", "Prospectar", "Monitorar", "Edital", "Ativo"]

# Garante que estas colunas sempre existam no DataFrame, mesmo se faltarem.
COLUNAS_ESPERADAS = [
    COL_ID, COL_PRIORIDADE, COL_SCORE, COL_SEMAFORO, COL_EMPRESA, COL_INSTITUTO,
    COL_SETOR, COL_SUBSETOR, COL_TIPO, COL_MODALIDADE, COL_VMIN, COL_VMAX,
    COL_VALVO, COL_STATUS, COL_CHANCE, COL_PRESENCA, COL_REGIAO, COL_SEDE,
    COL_UF, COL_PUBLICO, COL_ENCAIXE, COL_PROPOSTA, COL_PROX_ACAO, COL_RESP,
    COL_EDITAL, COL_JANELA, COL_URL, COL_CONTATO, COL_CANAL, COL_SOCIAL,
    COL_OBS, COL_VERIF,
]

_MSG_CSV = ("Modo local (CSV): a alteração não foi gravada. "
            "Conecte ao Google Sheets (veja o README) para habilitar a escrita.")


# --------------------------------------------------------------------------- #
# Conexão com o Google Sheets (silenciosa: qualquer falha vira modo CSV)
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner=False)
def _conectar():
    """Devolve o objeto Spreadsheet do gspread ou None (sem credenciais/erro)."""
    try:
        # Acessar st.secrets sem arquivo configurado pode lançar exceção.
        try:
            tem_credenciais = "gcp_service_account" in st.secrets
        except Exception:
            return None
        if not tem_credenciais:
            return None

        import gspread
        from google.oauth2.service_account import Credentials

        escopos = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        info = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(info, scopes=escopos)
        cliente = gspread.authorize(creds)

        # Localiza a planilha por URL, por chave ou por nome (nessa ordem).
        if "spreadsheet_url" in st.secrets:
            return cliente.open_by_url(st.secrets["spreadsheet_url"])
        if "spreadsheet_key" in st.secrets:
            return cliente.open_by_key(st.secrets["spreadsheet_key"])
        nome = st.secrets.get("spreadsheet_name", "PFC Captação")
        return cliente.open(nome)
    except Exception:
        # Falha de credencial/rede/planilha -> opera em modo CSV.
        return None


def _aba_dados(sh):
    """Worksheet principal: tenta o nome configurado e cai para a 1ª aba."""
    try:
        return sh.worksheet(ABA_DADOS)
    except Exception:
        return sh.sheet1


def modo_conexao() -> str:
    """'sheets' se a leitura veio do Google Sheets; senão 'csv'."""
    return "sheets" if carregar_empresas()[1] else "csv"


def limpar_caches() -> None:
    """Limpa cache de leitura e de conexão (para reconectar/refrescar)."""
    try:
        carregar_empresas.clear()
    except Exception:
        pass
    try:
        carregar_editais_privados.clear()
    except Exception:
        pass
    try:
        _conectar.clear()
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Leitura
# --------------------------------------------------------------------------- #
def _normalizar(df: pd.DataFrame) -> pd.DataFrame:
    """Garante colunas esperadas, tipa numéricos e remove linhas vazias."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Remove linhas completamente vazias (robustez contra planilha "suja").
    df = df.dropna(how="all")

    for col in COLUNAS_ESPERADAS:
        if col not in df.columns:
            df[col] = ""

    # Texto: ausentes viram string vazia (a UI nunca quebra).
    texto_cols = [c for c in df.columns if c not in COLS_NUMERICAS]
    if texto_cols:
        df[texto_cols] = df[texto_cols].fillna("").astype(str)
        df[texto_cols] = df[texto_cols].apply(lambda s: s.str.strip())

    # Numérico: coage com segurança (valores inválidos viram 0).
    for col in COLS_NUMERICAS:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Descarta linhas sem nome de organização.
    df = df[df[COL_EMPRESA].astype(str).str.strip() != ""]
    return df.reset_index(drop=True)


@st.cache_data(ttl=60, show_spinner=False)
def carregar_empresas() -> tuple[pd.DataFrame, bool]:
    """Carrega as organizações. Retorna (DataFrame, modo_conectado).

    modo_conectado=True somente quando os dados vieram do Google Sheets.
    """
    sh = _conectar()
    if sh is not None:
        try:
            registros = _aba_dados(sh).get_all_records()
            if registros:
                return _normalizar(pd.DataFrame(registros)), True
        except Exception:
            pass  # cai para o CSV abaixo

    try:
        df = pd.read_csv(CSV_PATH, dtype=str)
    except Exception:
        # Última linha de defesa: DataFrame vazio com as colunas esperadas.
        df = pd.DataFrame(columns=COLUNAS_ESPERADAS)
    return _normalizar(df), False


def _ler_base() -> pd.DataFrame:
    """Atalho interno para obter apenas o DataFrame."""
    return carregar_empresas()[0]


@st.cache_data(ttl=60, show_spinner=False)
def carregar_editais_privados() -> pd.DataFrame:
    """Lê a aba opcional 'Editais_Privados' (prazos). Vazio se não existir/CSV."""
    sh = _conectar()
    if sh is None:
        return pd.DataFrame()
    try:
        titulos = [w.title for w in sh.worksheets()]
        if ABA_EDITAIS not in titulos:
            return pd.DataFrame()
        registros = sh.worksheet(ABA_EDITAIS).get_all_records()
        return pd.DataFrame(registros)
    except Exception:
        return pd.DataFrame()


# --------------------------------------------------------------------------- #
# Escrita (somente quando conectado ao Google Sheets)
# --------------------------------------------------------------------------- #
def _atualizar_celula(id_org, coluna: str, valor) -> dict:
    """Atualiza uma célula da linha cujo ID == id_org. Retorna {sucesso, mensagem}."""
    sh = _conectar()
    if sh is None:
        return {"sucesso": False, "mensagem": _MSG_CSV}
    try:
        ws = _aba_dados(sh)
        cabecalho = [str(c).strip() for c in ws.row_values(1)]
        if coluna not in cabecalho:
            return {"sucesso": False, "mensagem": f"Coluna '{coluna}' não existe na planilha."}
        if COL_ID not in cabecalho:
            return {"sucesso": False, "mensagem": f"Coluna '{COL_ID}' não existe na planilha."}

        col_idx = cabecalho.index(coluna) + 1
        id_idx = cabecalho.index(COL_ID) + 1
        ids = ws.col_values(id_idx)  # ids[0] é o cabeçalho

        linha = None
        alvo = str(id_org).strip()
        for i, v in enumerate(ids[1:], start=2):
            if str(v).strip() == alvo:
                linha = i
                break
        if linha is None:
            return {"sucesso": False,
                    "mensagem": f"Organização ID {id_org} não encontrada na planilha."}

        ws.update_cell(linha, col_idx, valor)
        carregar_empresas.clear()  # invalida o cache para refletir a mudança
        return {"sucesso": True, "mensagem": "Gravado no Google Sheets."}
    except Exception as e:
        return {"sucesso": False, "mensagem": f"Erro ao gravar no Google Sheets: {e}"}


def criar_aba_novidades() -> bool:
    """Garante a aba 'Novidades_pendentes' com o cabeçalho padrão.

    Retorna True se foi CRIADA agora; False se já existia (ou indisponível/CSV).
    """
    sh = _conectar()
    if sh is None:
        return False
    try:
        titulos = [w.title for w in sh.worksheets()]
        if ABA_PENDENTES in titulos:
            return False  # já existia
        ws = sh.add_worksheet(title=ABA_PENDENTES, rows=500, cols=len(HEADERS_NOVIDADES))
        ws.append_row(HEADERS_NOVIDADES)
        return True  # criada agora
    except Exception:
        return False


def adicionar_lead_radar(lead_dict: dict) -> dict:
    """Grava um lead aprovado na aba 'Novidades_pendentes'. Retorna {sucesso, mensagem}."""
    sh = _conectar()
    if sh is None:
        return {"sucesso": False, "mensagem": "Lead salvo em memória (modo CSV) — "
                "conecte ao Google Sheets para gravar de verdade."}
    try:
        # (a) garante a aba (cria se não existir)
        criar_aba_novidades()
        ws = sh.worksheet(ABA_PENDENTES)
        if not ws.row_values(1):  # aba existente porém vazia
            ws.append_row(HEADERS_NOVIDADES)

        ld = lead_dict or {}

        def pega(*chaves, padrao=""):
            for c in chaves:
                if c in ld and str(ld[c]).strip() != "":
                    return ld[c]
            return padrao

        # (b) monta a linha na ORDEM exata do cabeçalho
        linha = [
            pega("data", "Data", padrao=pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")),
            pega("fonte", "Fonte"),
            pega("titulo", "título", "Título"),
            pega("descricao", "descrição", "Descrição"),
            pega("score_aderencia", "score_aderência", "Score Aderência"),
            pega("prazo", "Prazo"),
            pega("valor_estimado", "Valor estimado"),
            pega("link", "Link da fonte", "url"),
            pega("status", "Status aprovação", padrao="Pendente de revisão"),
        ]
        # (c) grava de verdade no Sheets
        ws.append_row([str(x) for x in linha], value_input_option="USER_ENTERED")
        return {"sucesso": True, "mensagem": "Lead enviado para a aba 'Novidades_pendentes'."}
    except Exception as e:
        return {"sucesso": False, "mensagem": f"Erro ao gravar o lead no Google Sheets: {e}"}


def salvar_observacao(id_org, texto: str) -> dict:
    """Acrescenta uma observação datada à coluna Observações. Retorna {sucesso, mensagem}."""
    texto = (texto or "").strip()
    if not texto:
        return {"sucesso": False, "mensagem": "Escreva uma observação antes de salvar."}

    sh = _conectar()
    if sh is None:
        return {"sucesso": False, "mensagem": _MSG_CSV}

    try:
        # (a) encontra a organização e lê a observação atual
        df = _ler_base()
        atual = ""
        match = df[df[COL_ID].astype(str).str.strip() == str(id_org).strip()]
        if not match.empty:
            atual = str(match.iloc[0][COL_OBS]).strip()
            if atual == "—":
                atual = ""

        carimbo = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")
        nova = f"[{carimbo}] {texto}"
        combinado = f"{atual}\n{nova}".strip() if atual else nova

        # (b)(c) atualiza a coluna Observações (grava no Sheets)
        return _atualizar_celula(id_org, COL_OBS, combinado)
    except Exception as e:
        return {"sucesso": False, "mensagem": f"Erro ao gravar observação: {e}"}


def atualizar_status(id_org, novo_status: str) -> dict:
    """Valida e grava o novo Status da organização. Retorna {sucesso, mensagem}."""
    novo_status = (novo_status or "").strip()
    # (a) valida contra os 5 status oficiais
    if novo_status not in STATUS_FUNIL:
        return {"sucesso": False,
                "mensagem": f"Status inválido. Use um de: {', '.join(STATUS_FUNIL)}."}
    # (b)(c) grava na coluna Status
    return _atualizar_celula(id_org, COL_STATUS, novo_status)


def marcar_fonte(id_org, status: str, url: str | None = None) -> dict:
    """Saneamento da base: grava o URL oficial (se informado) na coluna Fonte/URL
    e atualiza a coluna 'Fonte verificada' (ex.: 'Verificada' / 'Verificação
    pendente'). Mesmo padrão de escrita de salvar_observacao. Retorna {sucesso, mensagem}.
    """
    status = (status or "").strip()
    if not status:
        return {"sucesso": False, "mensagem": "Status de verificação inválido."}
    if url is not None and str(url).strip():
        res_url = _atualizar_celula(id_org, COL_URL, str(url).strip())
        if not res_url["sucesso"]:
            return res_url
    return _atualizar_celula(id_org, COL_VERIF, status)
