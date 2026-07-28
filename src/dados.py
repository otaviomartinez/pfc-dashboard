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
    atualizar_deputado(nome, campos)-> {"sucesso": bool, "mensagem": str}  (edita o CRM, só campos que mudaram)
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
# Base de deputados do radar de Emendas (dados sensíveis, fora do git).
DEPUTADOS_CSV = Path(__file__).resolve().parent.parent / "data" / "deputados_estaduais.csv"

# Aba (worksheet) com a base de organizações dentro da planilha Google.
ABA_DADOS = "empresas"
ABA_BASE = "Base_Empresas"  # nome alternativo da base (usado ao aprovar do Radar)
# Aba onde o Radar grava as oportunidades aprovadas.
ABA_PENDENTES = "Novidades_pendentes"
# Aba opcional de editais privados (prazos).
ABA_EDITAIS = "Editais_Privados"
# Aba do CRM de deputados (radar de Emendas). Contém o Diálogo sensível — a
# planilha inteira deve permanecer restrita; no app o Diálogo só renderiza logado.
ABA_DEPUTADOS = "Deputados"
# Aba de inscritos no alerta de editais por e-mail (cadastro pelo próprio app).
# Só e-mail + data + flag Ativo — nada sensível. O radar lê daqui para enviar.
ABA_INSCRITOS = "Inscritos Alerta"
HEADERS_INSCRITOS = ["Email", "Data inscrição", "Ativo"]
# Cabeçalho EXATO da aba de novidades.
HEADERS_NOVIDADES = [
    "Data", "Fonte", "Título", "Descrição", "Score Aderência",
    "Prazo", "Valor estimado", "Link da fonte", "Status aprovação",
]
# Cabeçalho EXATO do CRM de deputados (mesmas 22 colunas do CSV original).
# A leitura/escrita é POR NOME de coluna, então adicionar uma nova (ex.: "Site")
# na aba do Sheets não quebra o código — o campo novo flui sozinho.
HEADERS_DEPUTADOS = [
    "Ordem de Abordagem", "Deputado", "Partido", "Chance Emenda (0-100)",
    "Aderência PFC (0-100)", "Score Integrado", "Prioridade",
    "Proximidade Territorial", "Diálogo", "Status", "Temperatura",
    "Base Regional", "Endereço/Escritório", "Gabinete ALESP", "Telefones",
    "WhatsApp", "Email", "Instagram", "Emenda/Ação", "Valor",
    "Estratégia PFC", "Observações",
]
# Colunas OFICIAIS da ALESP (públicas, vindas da fonte oficial): a edição pela
# tela NUNCA escreve nelas — o Fábio não edita contato oficial. Guarda de defesa
# em atualizar_deputado(), mesmo que o app já não as ofereça para edição.
COLS_OFICIAIS_ALESP = {
    "Email Oficial", "Telefone Gabinete", "Página ALESP", "Pagina ALESP",
}

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
    """Worksheet da base: tenta 'empresas', depois 'Base_Empresas', senão 1ª aba."""
    for nome in (ABA_DADOS, ABA_BASE):
        try:
            return sh.worksheet(nome)
        except Exception:
            continue
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
        carregar_novidades_pendentes.clear()
    except Exception:
        pass
    try:
        carregar_deputados.clear()
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


def criar_aba_deputados() -> bool:
    """Garante a aba 'Deputados' com o cabeçalho padrão. True se criada agora."""
    sh = _conectar()
    if sh is None:
        return False
    try:
        if ABA_DEPUTADOS in [w.title for w in sh.worksheets()]:
            return False
        ws = sh.add_worksheet(title=ABA_DEPUTADOS, rows=200, cols=len(HEADERS_DEPUTADOS))
        ws.append_row(HEADERS_DEPUTADOS)
        return True
    except Exception:
        return False


@st.cache_data(ttl=60, show_spinner=False)
def carregar_deputados() -> pd.DataFrame:
    """Base de deputados estaduais (CRM do radar de Emendas).

    Fonte da verdade = aba 'Deputados' no Google Sheets (leitura E escrita). Se
    o Sheets estiver indisponível, cai para o CSV local como REDE DE SEGURANÇA
    de leitura (pode estar defasado; nesse modo a escrita fica bloqueada, para
    os dois nunca divergirem). Sem nenhum dos dois, devolve vazio.

    Contém informação sensível (diálogos, contatos): a planilha é restrita e o
    Diálogo só renderiza para usuário logado. A leitura é POR NOME de coluna,
    então colunas novas na aba fluem sem mexer no código.
    """
    sh = _conectar()
    if sh is not None:
        try:
            registros = sh.worksheet(ABA_DEPUTADOS).get_all_records()
            if registros:
                df = pd.DataFrame(registros).astype(str)
                # get_all_records devolve "" para vazio e tipa números; normaliza
                return df.replace({"None": "", "nan": ""}).fillna("")
        except Exception:
            pass  # aba ausente/erro -> fallback CSV
    try:
        df = pd.read_csv(DEPUTADOS_CSV, dtype=str).fillna("")
        return df.dropna(how="all")
    except Exception:
        return pd.DataFrame()


def deputados_conectado() -> bool:
    """True se a leitura dos deputados veio do Sheets (não do fallback CSV)."""
    sh = _conectar()
    if sh is None:
        return False
    try:
        return bool(sh.worksheet(ABA_DEPUTADOS).get_all_records())
    except Exception:
        return False


# Levantamento de emendas (tela "Descobrir"): rankings gerados por src/emendas.py.
# São dados PÚBLICOS (transparência), versionados — não confundir com o CSV
# sensível dos 16 deputados acima. Sem o arquivo, degrada para vazio.
RANKING_TERRITORIO_CSV = Path(__file__).resolve().parent.parent / "data" / "emendas_ranking_pfc_territorio.csv"
RANKING_EXPANSAO_CSV = Path(__file__).resolve().parent.parent / "data" / "emendas_ranking_pfc_expansao.csv"
# Contatos OFICIAIS (públicos) dos titulares da ALESP — email de gabinete,
# telefone e página oficial. Enriquecido a partir do XML da ALESP. NÃO confundir
# com os contatos pessoais/de assessor do Fábio (esses ficam no CRM sensível).
TITULARES_CSV = Path(__file__).resolve().parent.parent / "data" / "deputados_alesp_titulares.csv"


@st.cache_data(ttl=60, show_spinner=False)
def carregar_ranking_territorio() -> pd.DataFrame:
    """Seção 'Abordar já': deputados que já financiam edu/social nos municípios do PFC."""
    try:
        return pd.read_csv(RANKING_TERRITORIO_CSV).fillna("")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60, show_spinner=False)
def carregar_ranking_expansao() -> pd.DataFrame:
    """Seção 'Cortejar': alinhados de fora, em camadas (prioritários / demais)."""
    try:
        return pd.read_csv(RANKING_EXPANSAO_CSV).fillna("")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def carregar_contatos_oficiais() -> pd.DataFrame:
    """Tabela pública de contatos oficiais dos titulares (ALESP)."""
    try:
        return pd.read_csv(TITULARES_CSV, dtype=str).fillna("")
    except Exception:
        return pd.DataFrame()


# Dados públicos (versionados) para a tela de MUNICÍPIOS ÓRFÃOS: municípios do
# PFC sem emenda edu/social, a base de execução por deputado×município e o mapa
# de Regiões Imediatas do IBGE. Todos gerados/mantidos por src/emendas.py.
ORFAOS_CSV = Path(__file__).resolve().parent.parent / "data" / "municipios_pfc_sem_emenda.csv"
EMENDAS_BASE_CSV = Path(__file__).resolve().parent.parent / "data" / "emendas_parlamentares.csv"
REGIOES_IBGE_CSV = Path(__file__).resolve().parent.parent / "data" / "ibge_regioes_imediatas_sp.csv"


# encoding utf-8-sig: estes CSVs têm BOM; sem isso a 1ª coluna vira
# "﻿municipio" em ambientes cujo pandas não descarta o BOM sozinho — uma
# diferença local↔produção. Falha de leitura sempre degrada para DataFrame vazio.
@st.cache_data(ttl=300, show_spinner=False)
def carregar_municipios_orfaos() -> pd.DataFrame:
    """Municípios do PFC que NÃO recebem emenda de educação/social."""
    try:
        return pd.read_csv(ORFAOS_CSV, dtype=str, encoding="utf-8-sig").fillna("")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def carregar_emendas_base() -> pd.DataFrame:
    """Base de execução de emendas (deputado × município × área × valores)."""
    try:
        return pd.read_csv(EMENDAS_BASE_CSV, dtype=str, encoding="utf-8-sig").fillna("")
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def carregar_regioes_ibge() -> pd.DataFrame:
    """Mapa município → Região Imediata (IBGE 2017), para a vizinhança."""
    try:
        return pd.read_csv(REGIOES_IBGE_CSV, dtype=str, encoding="utf-8-sig").fillna("")
    except Exception:
        return pd.DataFrame()


def contato_oficial(nome: str) -> dict:
    """Email/telefone/página oficiais do deputado, casando por nome (contenção).

    Devolve {"email","telefone","pagina"} — vazio se não houver tabela; com
    "não encontrado" nos campos se o deputado não estiver entre os titulares.
    Contatos PÚBLICOS: podem aparecer no levantamento e no dossiê.
    """
    df = carregar_contatos_oficiais()
    if df.empty or "nome_parlamentar" not in df:
        return {}
    for _, r in df.iterrows():
        if _mesmo_deputado(nome, r["nome_parlamentar"]):
            return {"email": r.get("email_oficial", "").strip(),
                    "telefone": r.get("telefone_gabinete", "").strip(),
                    "pagina": r.get("pagina_alesp", "").strip()}
    return {"email": "não encontrado", "telefone": "não encontrado", "pagina": ""}


# --------------------------------------------------------------------------- #
# ESCRITA no CRM sensível: puxar um deputado da tela "Descobrir"
# ---------------------------------------------------------------------------
# O CRM vive na aba 'Deputados' do Google Sheets (dado sensível do Fábio).
# Esta é a ÚNICA função que ESCREVE nele, e é APPEND-ONLY de propósito:
#   * nunca modifica uma linha existente -> diálogo, temperatura e status que o
#     Fábio já escreveu ficam intactos (salvaguarda: não sobrescrever);
#   * recusa duplicata por nome normalizado/contido (salvaguarda: não duplicar).
# Só grava quando conectado ao Sheets; no fallback CSV a escrita é bloqueada
# (para as duas fontes nunca divergirem).
# --------------------------------------------------------------------------- #
def _tokens_nome(nome: str) -> set:
    """Nome -> conjunto de tokens sem acento/minúsculo, para comparar."""
    import unicodedata
    s = unicodedata.normalize("NFKD", str(nome or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return set(s.lower().split())


def _mesmo_deputado(a: str, b: str) -> bool:
    """True se a e b são o mesmo deputado (igual, ou um contém todos os tokens
    do outro — ex.: 'Danilo Balas' ⊆ 'Agente Federal Danilo Balas'). Exige 2+
    tokens em comum via contenção total, então 'Altair Moraes' != 'Rodrigo Moraes'."""
    ta, tb = _tokens_nome(a), _tokens_nome(b)
    if not ta or not tb:
        return False
    return ta == tb or ta <= tb or tb <= ta


def deputado_no_crm(nome: str, df: pd.DataFrame | None = None) -> bool:
    """O deputado (por nome, com normalização) já está no CRM?"""
    df = carregar_deputados() if df is None else df
    if df.empty or "Deputado" not in df:
        return False
    return any(_mesmo_deputado(nome, x) for x in df["Deputado"])


def adicionar_deputado_crm(novo: dict) -> dict:
    """Acrescenta UM deputado à aba 'Deputados' do Sheets. {'sucesso', 'motivo'}.

    novo: {coluna_do_CRM: valor}. Escreve POR NOME de coluna (usa o cabeçalho
    real da aba), então respeita colunas novas. Colunas ausentes ficam vazias
    para o Fábio preencher. Append-only: nunca toca nas linhas existentes.
    """
    sh = _conectar()
    if sh is None:
        return {"sucesso": False, "motivo": "sheets_indisponivel",
                "mensagem": "Sem conexão com o Google Sheets — a gravação fica "
                            "bloqueada no modo local para não divergir dos dados."}
    nome = str(novo.get("Deputado", "")).strip()
    if not nome:
        return {"sucesso": False, "motivo": "sem_nome"}
    try:
        criar_aba_deputados()  # idempotente: cria a aba se ainda não existir
        ws = sh.worksheet(ABA_DEPUTADOS)
        cabecalho = ws.row_values(1) or HEADERS_DEPUTADOS
        if not ws.row_values(1):
            ws.append_row(HEADERS_DEPUTADOS)
            cabecalho = HEADERS_DEPUTADOS
        existentes = [str(r.get("Deputado", "")) for r in ws.get_all_records()]
        if any(_mesmo_deputado(nome, x) for x in existentes):
            return {"sucesso": False, "motivo": "duplicado"}
        # linha na ordem EXATA do cabeçalho da aba; só preenche o que veio.
        # RAW (não USER_ENTERED): guarda tudo como TEXTO literal — um Diálogo que
        # comece com "=" nunca vira fórmula (proteção contra injeção de fórmula).
        linha = [str(novo.get(col, "")) for col in cabecalho]
        ws.append_row(linha, value_input_option="RAW")
    except Exception as e:  # noqa: BLE001
        return {"sucesso": False, "motivo": "escrita", "mensagem": str(e)}

    carregar_deputados.clear()  # invalida o cache p/ o próximo read enxergar a linha
    return {"sucesso": True, "motivo": "ok"}


def atualizar_status_deputado(nome: str, novo_status: str) -> dict:
    """Grava SÓ a coluna Status do deputado (por nome) na aba Deputados.

    Usado pelo drag-and-drop do funil de Emendas. Escreve UMA célula — diálogo,
    temperatura, contatos e os demais campos ficam intactos (mesmo espírito do
    _atualizar_celula das empresas). Não cria linha: se o deputado não existir,
    devolve erro. Retorna {sucesso, mensagem}.
    """
    nome = str(nome or "").strip()
    novo_status = str(novo_status or "").strip()
    if not nome or not novo_status:
        return {"sucesso": False, "mensagem": "Deputado ou etapa em branco."}
    sh = _conectar()
    if sh is None:
        return {"sucesso": False, "mensagem": "Sem conexão com o Google Sheets — a etapa "
                "não foi gravada (modo local)."}
    try:
        ws = sh.worksheet(ABA_DEPUTADOS)
        cab = [str(c).strip() for c in ws.row_values(1)]
        if "Deputado" not in cab or "Status" not in cab:
            return {"sucesso": False, "mensagem": "Aba Deputados sem coluna Deputado/Status."}
        col_dep = cab.index("Deputado") + 1
        col_status = cab.index("Status") + 1
        nomes = ws.col_values(col_dep)  # nomes[0] é o cabeçalho
        linha = next((i for i, v in enumerate(nomes[1:], start=2)
                      if str(v).strip() == nome), None)
        if linha is None:
            return {"sucesso": False, "mensagem": f"Deputado '{nome}' não encontrado na aba."}
        ws.update_cell(linha, col_status, novo_status)  # só a célula de Status
        carregar_deputados.clear()
        return {"sucesso": True, "mensagem": f"{nome}: etapa → {novo_status}."}
    except Exception as e:  # noqa: BLE001
        return {"sucesso": False, "mensagem": f"Erro ao gravar no Google Sheets: {e}"}


def atualizar_deputado(nome: str, campos: dict) -> dict:
    """Grava SÓ as células dos campos informados do deputado (por nome) na aba
    Deputados. Preserva TODO o resto: escreve apenas as colunas presentes em
    `campos`, célula a célula, sem tocar nas demais (mesmo espírito de
    atualizar_status_deputado, mas para vários campos de uma vez). Usado pela
    edição do dossiê (diálogo, status, temperatura, próximos passos).

    Invariantes (as mesmas que valem para o resto do CRM):
      * Só grava conectado ao Sheets; no fallback CSV a escrita fica bloqueada
        (para as duas fontes nunca divergirem).
      * RAW (não USER_ENTERED): guarda tudo como TEXTO literal — um Diálogo que
        comece com "=" nunca vira fórmula (proteção contra injeção de fórmula).
      * Recusa as colunas OFICIAIS da ALESP — contato oficial não se edita aqui.
      * Escreve POR NOME de coluna; uma coluna que ainda não exista na aba é
        criada no fim do cabeçalho antes de gravar ("coluna nova flui sozinha").
      * NÃO cria linha: se o deputado não existir na aba, devolve erro.

    Retorna {sucesso, mensagem}.
    """
    nome = str(nome or "").strip()
    if not nome:
        return {"sucesso": False, "mensagem": "Deputado em branco."}
    # Descarta colunas oficiais e chaves vazias; None vira "". String vazia é
    # permitida de propósito (deixa o Fábio LIMPAR um campo).
    campos = {str(k).strip(): ("" if v is None else str(v))
              for k, v in (campos or {}).items()
              if str(k).strip() and str(k).strip() not in COLS_OFICIAIS_ALESP}
    if not campos:
        return {"sucesso": False, "mensagem": "Nada para gravar."}

    sh = _conectar()
    if sh is None:
        return {"sucesso": False, "mensagem": "Sem conexão com o Google Sheets — as "
                "alterações não foram gravadas (modo local, escrita bloqueada)."}
    try:
        import gspread
        ws = sh.worksheet(ABA_DEPUTADOS)
        cab = [str(c).strip() for c in ws.row_values(1)]
        if "Deputado" not in cab:
            return {"sucesso": False, "mensagem": "Aba Deputados sem coluna Deputado."}
        col_dep = cab.index("Deputado") + 1
        nomes = ws.col_values(col_dep)  # nomes[0] é o cabeçalho
        linha = next((i for i, v in enumerate(nomes[1:], start=2)
                      if str(v).strip() == nome), None)
        if linha is None:
            return {"sucesso": False, "mensagem": f"Deputado '{nome}' não encontrado na aba."}

        # Cria no cabeçalho qualquer coluna nova ANTES de montar as células.
        for col in campos:
            if col not in cab:
                cab.append(col)
                ws.update_cell(1, len(cab), col)

        # Uma única chamada de escrita para todas as células (RAW).
        celulas = [gspread.Cell(linha, cab.index(col) + 1, val)
                   for col, val in campos.items()]
        ws.update_cells(celulas, value_input_option="RAW")
        carregar_deputados.clear()  # invalida o cache p/ o próximo read enxergar
        return {"sucesso": True,
                "mensagem": f"{nome}: {len(celulas)} campo(s) atualizado(s) na aba Deputados."}
    except Exception as e:  # noqa: BLE001
        return {"sucesso": False, "mensagem": f"Erro ao gravar no Google Sheets: {e}"}


def anexar_dialogo_deputado(nome: str, texto: str) -> dict:
    """Acrescenta uma observação DATADA ao campo Diálogo do deputado (por nome).

    É a "observação rápida" do card do funil. Escreve no MESMO campo que o
    dossiê edita (Diálogo, sensível), então o que se anota aqui aparece lá e
    vice-versa — não há campo paralelo. Append: preserva o diálogo já existente
    (mesmo espírito de salvar_observacao das empresas) e, por passar por
    atualizar_deputado, grava só aquela célula (RAW), sem tocar em status,
    temperatura, contatos ou os demais campos. Retorna {sucesso, mensagem}.
    """
    texto = (texto or "").strip()
    nome = str(nome or "").strip()
    if not texto:
        return {"sucesso": False, "mensagem": "Escreva uma observação antes de salvar."}
    if not nome:
        return {"sucesso": False, "mensagem": "Deputado em branco."}

    # Lê o Diálogo atual (fonte da verdade: aba Deputados) para anexar sem perder.
    atual = ""
    df = carregar_deputados()
    if not df.empty and "Deputado" in df and "Diálogo" in df:
        match = df[df["Deputado"].astype(str).str.strip() == nome]
        if not match.empty:
            atual = str(match.iloc[0]["Diálogo"]).strip()

    carimbo = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")
    nova = f"[{carimbo}] {texto}"
    combinado = f"{atual}\n{nova}".strip() if atual else nova
    return atualizar_deputado(nome, {"Diálogo": combinado})


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


@st.cache_data(ttl=60, show_spinner=False)
def carregar_novidades_pendentes() -> list[dict]:
    """Lê a aba 'Novidades_pendentes' e devolve as linhas 'Pendente de revisão'.

    Cada item é um dict com as colunas: Data, Fonte, Título, Descrição,
    Score Aderência, Prazo, Valor estimado, Link da fonte, Status aprovação.
    """
    sh = _conectar()
    if sh is None:
        return []
    try:
        registros = sh.worksheet(ABA_PENDENTES).get_all_records()
    except Exception:
        return []
    return [r for r in registros
            if str(r.get("Status aprovação", "")).strip().lower() == "pendente de revisão"]


# --------------------------------------------------------------------------- #
# Inscritos no alerta de editais por e-mail (cadastro pelo app)
# --------------------------------------------------------------------------- #
import re as _re

_RE_EMAIL = _re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _email_valido(email: str) -> bool:
    return bool(_RE_EMAIL.match(str(email or "").strip()))


def _inscrito_ativo(valor: str) -> bool:
    """Trata Ativo vazio/'Sim'/'True'/'1' como ativo; só 'Não'/'False'/'0' saem."""
    return str(valor or "").strip().lower() not in ("não", "nao", "false", "0", "inativo")


def criar_aba_inscritos() -> bool:
    """Garante a aba 'Inscritos Alerta' com o cabeçalho padrão. True se criada agora."""
    sh = _conectar()
    if sh is None:
        return False
    try:
        if ABA_INSCRITOS in [w.title for w in sh.worksheets()]:
            return False
        ws = sh.add_worksheet(title=ABA_INSCRITOS, rows=500, cols=len(HEADERS_INSCRITOS))
        ws.append_row(HEADERS_INSCRITOS)
        return True
    except Exception:
        return False


@st.cache_data(ttl=60, show_spinner=False)
def carregar_inscritos() -> pd.DataFrame:
    """Lê a aba 'Inscritos Alerta' (Email, Data inscrição, Ativo). Vazio se não existir/CSV."""
    sh = _conectar()
    if sh is None:
        return pd.DataFrame()
    try:
        if ABA_INSCRITOS not in [w.title for w in sh.worksheets()]:
            return pd.DataFrame()
        return pd.DataFrame(sh.worksheet(ABA_INSCRITOS).get_all_records())
    except Exception:
        return pd.DataFrame()


def adicionar_inscrito(email: str) -> dict:
    """Inscreve um e-mail no alerta de editais. Retorna {sucesso, mensagem}.

    Valida o formato, evita duplicar (reativa se estava inativo) e grava
    append-only RAW na aba 'Inscritos Alerta' — mesmo padrão da porta única.
    Só grava conectado ao Sheets; no modo CSV a escrita fica bloqueada.
    """
    email = str(email or "").strip().lower()
    if not _email_valido(email):
        return {"sucesso": False, "mensagem": "E-mail inválido. Confira e tente de novo."}
    sh = _conectar()
    if sh is None:
        return {"sucesso": False, "mensagem": "Sem conexão com o Google Sheets — a "
                "inscrição não foi gravada (modo local)."}
    try:
        criar_aba_inscritos()  # idempotente
        ws = sh.worksheet(ABA_INSCRITOS)
        cabecalho = ws.row_values(1) or HEADERS_INSCRITOS
        if not ws.row_values(1):
            ws.append_row(HEADERS_INSCRITOS)
            cabecalho = HEADERS_INSCRITOS
        registros = ws.get_all_records()
        for i, r in enumerate(registros, start=2):
            if str(r.get("Email", "")).strip().lower() == email:
                if _inscrito_ativo(r.get("Ativo", "")):
                    return {"sucesso": True, "mensagem": "Esse e-mail já está inscrito."}
                if "Ativo" in cabecalho:
                    ws.update_cell(i, cabecalho.index("Ativo") + 1, "Sim")  # reativa
                carregar_inscritos.clear()
                return {"sucesso": True, "mensagem": "Pronto, sua inscrição foi reativada."}
        linha_map = {"Email": email,
                     "Data inscrição": pd.Timestamp.now().strftime("%d/%m/%Y %H:%M"),
                     "Ativo": "Sim"}
        ws.append_row([str(linha_map.get(c, "")) for c in cabecalho], value_input_option="RAW")
        carregar_inscritos.clear()
        return {"sucesso": True,
                "mensagem": "Pronto, você receberá os alertas de editais por e-mail."}
    except Exception as e:  # noqa: BLE001
        return {"sucesso": False, "mensagem": f"Erro ao gravar inscrição: {e}"}


def desinscrever(email: str) -> dict:
    """Sai da lista: marca Ativo='Não' na linha do e-mail (não apaga). {sucesso, mensagem}."""
    email = str(email or "").strip().lower()
    if not _email_valido(email):
        return {"sucesso": False, "mensagem": "E-mail inválido."}
    sh = _conectar()
    if sh is None:
        return {"sucesso": False, "mensagem": "Sem conexão com o Google Sheets — não "
                "foi possível sair da lista agora (modo local)."}
    try:
        if ABA_INSCRITOS not in [w.title for w in sh.worksheets()]:
            return {"sucesso": False, "mensagem": "Ninguém inscrito ainda."}
        ws = sh.worksheet(ABA_INSCRITOS)
        cab = [str(c).strip() for c in ws.row_values(1)]
        if "Email" not in cab or "Ativo" not in cab:
            return {"sucesso": False, "mensagem": "Aba de inscritos incompleta."}
        emails = ws.col_values(cab.index("Email") + 1)
        linha = next((i for i, v in enumerate(emails[1:], start=2)
                      if str(v).strip().lower() == email), None)
        if linha is None:
            return {"sucesso": False, "mensagem": "Esse e-mail não está na lista."}
        ws.update_cell(linha, cab.index("Ativo") + 1, "Não")
        carregar_inscritos.clear()
        return {"sucesso": True, "mensagem": "Pronto, você saiu da lista de alertas."}
    except Exception as e:  # noqa: BLE001
        return {"sucesso": False, "mensagem": f"Erro ao sair da lista: {e}"}


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


# --------------------------------------------------------------------------- #
# Fila do Radar (aba Novidades_pendentes) -> aprovar/descartar
# --------------------------------------------------------------------------- #
def _semaforo_por_score(score) -> str:
    try:
        s = float(str(score).replace(",", "."))
    except (TypeError, ValueError):
        return "🟡"
    return "🟢" if s >= 70 else ("🟡" if s >= 45 else "🔴")


def _valor_para_reais(texto) -> int:
    """Extrai o MAIOR valor em reais de um texto ('R$ 80 mil – R$ 200 mil' -> 200000)."""
    import re
    maior = 0
    for m in re.finditer(r"([\d\.]+(?:,\d+)?)\s*(mil|milh|mi|k)?", str(texto or "").lower()):
        try:
            base = float(m.group(1).replace(".", "").replace(",", "."))
        except ValueError:
            continue
        unid = m.group(2) or ""
        if unid in ("mil", "k"):
            base *= 1_000
        elif unid.startswith("milh") or unid == "mi":
            base *= 1_000_000
        if base >= 1_000:
            maior = max(maior, int(base))
    return maior


def _atualizar_status_novidade(novidade: dict, novo_status: str) -> dict:
    """Muda 'Status aprovação' da linha da novidade (casa por Link ou Título)."""
    sh = _conectar()
    if sh is None:
        return {"sucesso": False, "mensagem": _MSG_CSV}
    try:
        ws = sh.worksheet(ABA_PENDENTES)
        cab = [str(c).strip() for c in ws.row_values(1)]
        c_status = cab.index("Status aprovação") + 1
        alvo_link = str(novidade.get("Link da fonte", "")).strip()
        alvo_tit = str(novidade.get("Título", "")).strip()
        col_link = ws.col_values(cab.index("Link da fonte") + 1) if "Link da fonte" in cab else []
        col_tit = ws.col_values(cab.index("Título") + 1) if "Título" in cab else []

        linha = None
        for i in range(2, max(len(col_link), len(col_tit)) + 1):
            link_i = col_link[i - 1].strip() if i - 1 < len(col_link) else ""
            tit_i = col_tit[i - 1].strip() if i - 1 < len(col_tit) else ""
            if (alvo_link and link_i == alvo_link) or (alvo_tit and tit_i == alvo_tit):
                linha = i
                break
        if linha is None:
            return {"sucesso": False, "mensagem": "Novidade não encontrada na aba (talvez já resolvida)."}
        ws.update_cell(linha, c_status, novo_status)
        carregar_novidades_pendentes.clear()
        return {"sucesso": True, "mensagem": f"Status atualizado para '{novo_status}'."}
    except Exception as e:
        return {"sucesso": False, "mensagem": f"Erro ao atualizar a novidade: {e}"}


def descartar_novidade(novidade: dict) -> dict:
    """Marca a novidade como 'Descartada'. Retorna {sucesso, mensagem}."""
    return _atualizar_status_novidade(novidade, "Descartada")


def aprovar_novidade(novidade: dict) -> dict:
    """Aprova a novidade: status -> 'Aprovada' E cria uma linha na base (Status 'Edital')."""
    sh = _conectar()
    if sh is None:
        return {"sucesso": False, "mensagem": _MSG_CSV}
    try:
        base_ws = _aba_dados(sh)
        cab = [str(c).strip() for c in base_ws.row_values(1)]
        # próximo ID numérico
        if COL_ID in cab:
            ids = [int(x) for x in base_ws.col_values(cab.index(COL_ID) + 1)[1:]
                   if str(x).strip().isdigit()]
            novo_id = (max(ids) + 1) if ids else 1
        else:
            novo_id = ""

        score = novidade.get("Score Aderência", "")
        titulo = str(novidade.get("Título", "")).strip()
        valores = {
            COL_ID: novo_id,
            COL_EMPRESA: str(novidade.get("Fonte", "")).strip() or titulo or "Oportunidade",
            COL_INSTITUTO: titulo,
            COL_SCORE: score,
            COL_SEMAFORO: _semaforo_por_score(score),
            COL_STATUS: "Edital",
            COL_EDITAL: titulo,
            COL_JANELA: str(novidade.get("Prazo", "")).strip(),
            COL_VALVO: _valor_para_reais(novidade.get("Valor estimado", "")) or "",
            COL_URL: str(novidade.get("Link da fonte", "")).strip(),
            COL_OBS: f"[Radar] {str(novidade.get('Descrição', '')).strip()}".strip(),
            COL_PROX_ACAO: "Analisar edital e avaliar aderência",
            COL_RESP: "Radar",
            COL_VERIF: "Não verificada",
        }
        linha = [str(valores.get(h, "")) for h in cab] if cab else list(valores.values())
        base_ws.append_row(linha, value_input_option="USER_ENTERED")

        # marca a novidade como Aprovada
        res = _atualizar_status_novidade(novidade, "Aprovada")
        carregar_empresas.clear()
        if not res["sucesso"]:
            return {"sucesso": True,
                    "mensagem": "Adicionada à base (Edital), mas o status da fila não pôde ser atualizado."}
        return {"sucesso": True, "mensagem": "Aprovada e adicionada à base como Edital."}
    except Exception as e:
        return {"sucesso": False, "mensagem": f"Erro ao aprovar: {e}"}
