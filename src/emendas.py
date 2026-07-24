"""
Extrator de emendas parlamentares estaduais de São Paulo (radar de Emendas).

Gera uma BASE PRÓPRIA de emendas por parlamentar, separada da planilha curada
do Fábio (os 16 deputados). A base ENRIQUECE o CRM pela chave do deputado — não
o substitui: quem manda sobre relacionamento/diálogo continua sendo a planilha.

Fonte desta etapa: os painéis Power BI do Portal da Transparência de SP, que
cobrem a legislatura atual (2023, 2024, 2025) e trazem execução — não proposta.
Os PDFs 2020-2022 (histórico dos reeleitos) entram numa etapa posterior.

DUAS ENTRADAS por ano (requisito de resiliência):
  1. API `querydata` do Power BI (quando o resourceKey responde).
  2. Arquivo baixado à mão pelo botão "Baixar os dados" do painel (.xlsx/.csv).
Se a API falhar (ex.: resourceKey rotacionado), a extração NÃO morre: ela
degrada para o arquivo manual, se houver um em data/emendas_manual/.

REGRAS que não podem ser quebradas nesta base:
  * PAGO e AUTORIZADO andam SEMPRE em colunas separadas. Nunca somados num só
    número. (`valor_autorizado` = VALOR DECISÃO; `valor_pago` = a parte cujo
    estágio é "Pagas".)
  * TRANSFERÊNCIA ESPECIAL fica FORA do recorte educação/assistência social
    (nessas emendas o município decide o uso, então não têm área). Elas entram
    na base com area_pfc="transferência especial" e são CONTADAS no relatório.
  * Nome que não casa com um dos 16 vai para a FILA DE REVISÃO — nunca é
    descartado nem adivinhado.

Migração futura: a leitura da lista curada é feita SÓ por
`dados.carregar_deputados()`. Quando ela for do CSV para o Google Sheets, essa
é a única função a mudar — este extrator acompanha sem alteração.

Uso:  python -m src.emendas
"""
from __future__ import annotations

import json
import sys
import time
import unicodedata
from pathlib import Path

import pandas as pd

try:
    import requests
except ImportError:  # a extração pela API precisa de requests; o modo arquivo não
    requests = None

from src import dados

# --------------------------------------------------------------------------- #
# Configuração
# --------------------------------------------------------------------------- #
RAIZ = Path(__file__).resolve().parent.parent
DIR_MANUAL = RAIZ / "data" / "emendas_manual"          # arquivos "Baixar os dados"
CONFIG_PFC = RAIZ / "config" / "pfc_municipios.toml"   # grupos, pesos, mínimo — editável
TITULARES_CSV = RAIZ / "data" / "deputados_alesp_titulares.csv"  # ALESP em exercício
REGIOES_IBGE_CSV = RAIZ / "data" / "ibge_regioes_imediatas_sp.csv"  # Regiões Imediatas 2017
SAIDA_BASE = RAIZ / "data" / "emendas_parlamentares.csv"
SAIDA_REVISAO = RAIZ / "data" / "emendas_revisao_nomes.csv"
SAIDA_RANKING = RAIZ / "data" / "emendas_ranking_deputados.csv"
SAIDA_RANKING_TERRITORIO = RAIZ / "data" / "emendas_ranking_pfc_territorio.csv"  # Seção 1
SAIDA_RANKING_EXPANSAO = RAIZ / "data" / "emendas_ranking_pfc_expansao.csv"      # Seção 2
SAIDA_EXCLUIDOS = RAIZ / "data" / "emendas_ranking_excluidos.csv"
SAIDA_MUN_SEM = RAIZ / "data" / "municipios_pfc_sem_emenda.csv"

# Cluster e resourceKeys dos painéis (descobertos na sondagem). O resourceKey
# pode ROTACIONAR se o painel for republicado — por isso a degradação p/ manual.
PBI_CLUSTER = "https://wabi-brazil-south-b-primary-api.analysis.windows.net"
PBI_PANEIS = {
    2023: "f7243798-e16d-47bf-a76d-587c0fc94501",
    2024: "7ae99f38-6898-461b-8d93-aeee788c318a",
    2025: "c53a54e7-9c63-4d84-be1a-5111bf2756d8",
}
_HEADERS = {"Origin": "https://app.powerbi.com", "Referer": "https://app.powerbi.com/",
            "User-Agent": "Mozilla/5.0 Chrome/126", "Content-Type": "application/json;charset=UTF-8"}

# Papel lógico -> palavra-chave no nome da coluna do modelo (case/acento-insensível).
# Mapear por nome (e não por posição) deixa o parser imune a reordenação de colunas.
_PAPEIS = {
    "parlamentar": "PARLAMENTAR",
    "partido": "PARTIDO",
    "municipio": "MUNICIPIO",
    "orgao": "ORGAO PROCESSADOR",
    "objeto": "OBJETO",
    "estagio": "ESTAGIO",
    "valor_decisao": "VALOR DECISAO",
}


# --------------------------------------------------------------------------- #
# Normalização de texto e de nomes
# --------------------------------------------------------------------------- #
def _sem_acento(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c))


def _norm(s: str) -> str:
    """Minúsculo, sem acento, espaços colapsados — para comparar."""
    return " ".join(_sem_acento(s).lower().split())


# --------------------------------------------------------------------------- #
# Lista curada do Fábio — leitura ISOLADA (único ponto de migração p/ Sheets)
# --------------------------------------------------------------------------- #
def carregar_lista_curada() -> pd.DataFrame:
    """Os 16 deputados do Fábio, com nome e partido.

    Delega para `dados.carregar_deputados()` de propósito: essa é a ÚNICA porta
    de leitura da lista. Migrou o CSV para o Sheets? Mexe lá, não aqui.
    """
    dfd = dados.carregar_deputados()
    if dfd is None or dfd.empty:
        return pd.DataFrame(columns=["nome", "partido"])
    out = pd.DataFrame({
        "nome": dfd["Deputado"].astype(str).str.strip(),
        "partido": dfd.get("Partido", pd.Series([""] * len(dfd))).astype(str).str.strip(),
    })
    return out[out["nome"] != ""].reset_index(drop=True)


def construir_indice_nomes(curados: pd.DataFrame) -> dict:
    """Índice para casar nomes: cada nome curado -> conjunto de tokens normalizados."""
    return {row["nome"]: set(_norm(row["nome"]).split()) for _, row in curados.iterrows()}


def casar_parlamentar(nome_pbi: str, indice: dict) -> tuple[str | None, str]:
    """Casa um nome do PBI com um dos 16. Devolve (nome_curado|None, situacao).

    situacao ∈ {"exato", "normalizado", "ambiguo", "sem_match"}.
      * exato       — igual após normalizar (acento/caixa).
      * normalizado — todos os tokens do nome curado estão contidos no nome do
                      PBI (ex.: "Danilo Balas" ⊆ "AGENTE FEDERAL DANILO BALAS").
                      É o que o requisito chama de "normalizar para casar".
      * ambiguo     — dois ou mais curados batem no mesmo nome do PBI -> revisão.
      * sem_match   — nenhum token significativo em comum -> é outro deputado.
    Um overlap de UM só token (Altair Moraes ~ Rodrigo Moraes) NÃO casa: exige
    conter TODOS os tokens do nome curado, que sempre tem 2+.
    """
    alvo = set(_norm(nome_pbi).split())
    exatos = [c for c, toks in indice.items() if toks == alvo]
    if len(exatos) == 1:
        return exatos[0], "exato"
    contidos = [c for c, toks in indice.items() if toks <= alvo]
    if len(contidos) == 1:
        return contidos[0], "normalizado"
    if len(contidos) >= 2:
        return None, "ambiguo"
    return None, "sem_match"


# --------------------------------------------------------------------------- #
# Classificação de área e de transferência especial
# --------------------------------------------------------------------------- #
def _e_transferencia_especial(objeto: str) -> bool:
    return "transferencia especial" in _norm(objeto)


def classificar_area(orgao: str, transferencia_especial: bool) -> str:
    """area_pfc: recorte grosso para o PFC. TE nunca vira educação/social."""
    if transferencia_especial:
        return "transferência especial"
    o = _norm(orgao)
    if "educacao" in o:
        return "educação"
    if "desenv. social" in o or "desenvolvimento social" in o or "assistencia" in o:
        return "assistência social"
    if "saude" in o:
        return "saúde"
    return "outra"


AREAS_PFC = ("educação", "assistência social")


# --------------------------------------------------------------------------- #
# Decodificação do DSR do Power BI
# --------------------------------------------------------------------------- #
def _mapear_colunas(resposta: dict) -> dict:
    """Papel lógico -> nome da coluna no schema do DSR (G0.., M0..).

    Usa o `descriptor.Select` da resposta: as colunas de agrupamento (kind 1)
    viram G0,G1,... na ordem; as de medida (kind 2) viram M0,M1,... na ordem.
    Casar por palavra-chave no nome torna o parser resiliente entre os anos.
    """
    desc = resposta["results"][0]["result"]["data"]["descriptor"]["Select"]
    grupos = [s["Name"] for s in desc if s.get("Kind", s.get("kind")) == 1]
    medidas = [s["Name"] for s in desc if s.get("Kind", s.get("kind")) == 2]
    nome_para_col = {}
    for i, nome in enumerate(grupos):
        nome_para_col[nome] = f"G{i}"
    for j, nome in enumerate(medidas):
        nome_para_col[nome] = f"M{j}"

    papel_para_col = {}
    for papel, chave in _PAPEIS.items():
        achou = [c for nome, c in nome_para_col.items() if chave in _sem_acento(nome).upper()]
        if not achou:
            raise ValueError(f"coluna do papel {papel!r} (chave {chave!r}) não encontrada "
                             f"no descriptor; layout do painel mudou")
        papel_para_col[papel] = achou[0]
    return papel_para_col


def decodificar_dsr(resposta: dict) -> list[dict]:
    """Linhas cruas do DSR, já com os índices de dicionário resolvidos.

    O DSR comprime: cada linha traz só as colunas que MUDARAM (bitmask R =
    repete a anterior; bitmask Ø = nula); textos são índices em ValueDicts.
    """
    ds = resposta["results"][0]["result"]["data"]["dsr"]["DS"][0]
    vd = ds.get("ValueDicts", {})
    # segmento de dados = o de mais linhas (DM1); o outro (DM0) é só o resumo
    seg = max(ds["PH"], key=lambda s: len(next(iter(s.values()))))
    linhas_raw = next(iter(seg.values()))
    esquema = linhas_raw[0]["S"]
    nomes = [c["N"] for c in esquema]
    dicts = [c.get("DN") for c in esquema]

    saida, anterior = [], [None] * len(esquema)
    for row in linhas_raw:
        c = row.get("C", [])
        rep, nul, ci, valores = row.get("R", 0), row.get("Ø", 0), 0, []
        for i in range(len(esquema)):
            if nul & (1 << i):
                v = None
            elif rep & (1 << i):
                v = anterior[i]
            else:
                v = c[ci] if ci < len(c) else None
                ci += 1
            valores.append(v)
        anterior = valores
        linha = {}
        for i, nome in enumerate(nomes):
            v, dn = valores[i], dicts[i]
            if dn and isinstance(v, int) and dn in vd and 0 <= v < len(vd[dn]):
                v = vd[dn][v]
            linha[nome] = v
        saida.append(linha)
    return saida


def resumo_dsr(resposta: dict) -> dict:
    """Totais do segmento-resumo (DM0): {'autorizado': x, 'pago_ou_remanejado': y}.

    Serve para reconciliar contra o que foi extraído linha a linha — se não
    bater, alguma linha caiu na decodificação e a extração deve ser rejeitada.
    """
    ds = resposta["results"][0]["result"]["data"]["dsr"]["DS"][0]
    resumo = min(ds["PH"], key=lambda s: len(next(iter(s.values()))))
    linha = next(iter(resumo.values()))[0]
    nums = [v for v in linha.get("C", []) if isinstance(v, (int, float))]
    return {"medidas": nums}


# --------------------------------------------------------------------------- #
# Front-ends de entrada: API e arquivo manual
# --------------------------------------------------------------------------- #
def _com_retry(fn, tentativas=4, espera=2):
    ultimo = None
    for i in range(tentativas):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 — rede é instável de propósito aqui
            ultimo = e
            if i < tentativas - 1:
                time.sleep(espera)
    raise ultimo


def baixar_querydata(resource_key: str) -> dict:
    """Puxa a resposta bruta da API querydata para um painel (janela ampla)."""
    if requests is None:
        raise RuntimeError("requests não instalado — use o modo arquivo manual")
    h = dict(_HEADERS, **{"X-PowerBI-ResourceKey": resource_key})
    meta = _com_retry(lambda: requests.get(
        f"{PBI_CLUSTER}/public/reports/{resource_key}/modelsAndExploration"
        "?preferReadOnlySession=true", headers=h, timeout=90))
    meta.raise_for_status()
    import gzip
    bruto = gzip.decompress(meta.content) if meta.content[:2] == b"\x1f\x8b" else meta.content
    mj = json.loads(bruto)
    sec = mj["exploration"]["sections"][0]
    melhor, n = None, 0
    for vc in sec["visualContainers"]:
        q = vc.get("query")
        if not q:
            continue
        try:
            sel = json.loads(q)["Commands"][0]["SemanticQueryDataShapeCommand"]["Query"]["Select"]
        except Exception:  # noqa: BLE001
            continue
        if len(sel) > n:
            melhor, n = vc, len(sel)
    if melhor is None:
        raise ValueError("painel sem visual de tabela reconhecível")
    cmd = json.loads(melhor["query"])["Commands"][0]["SemanticQueryDataShapeCommand"]
    cmd["Binding"]["DataReduction"]["Primary"]["Window"]["Count"] = 30000  # tudo numa página
    corpo = {"version": "1.0.0", "queries": [{
        "Query": {"Commands": [{"SemanticQueryDataShapeCommand": cmd}]}, "QueryId": "",
        "ApplicationContext": {"DatasetId": mj["models"][0]["dbName"],
                               "Sources": [{"ReportId": str(mj["exploration"]["reportId"])}]}}],
        "cancelQueries": [], "modelId": mj["models"][0]["id"]}
    r = _com_retry(lambda: requests.post(
        f"{PBI_CLUSTER}/public/reports/querydata?synchronous=true",
        json=corpo, headers=h, timeout=120))
    r.raise_for_status()
    return r.json()


def linhas_da_api(ano: int, resposta: dict | None = None) -> list[dict]:
    """Linhas cruas (papéis lógicos) a partir da resposta querydata de um ano."""
    if resposta is None:
        resposta = baixar_querydata(PBI_PANEIS[ano])
    papel = _mapear_colunas(resposta)
    brutas = decodificar_dsr(resposta)
    # reconciliação: soma do valor extraído vs resumo do painel
    col_val = papel["valor_decisao"]
    soma = sum((l.get(col_val) or 0) for l in brutas)
    resumo = resumo_dsr(resposta)["medidas"]
    if resumo and not any(abs(soma - m) < 1.0 for m in resumo):
        raise ValueError(f"{ano}: soma extraída R$ {soma:,.2f} não bate com o resumo "
                         f"{resumo} — possível perda de linhas na decodificação")
    saida = []
    for l in brutas:
        saida.append({
            "ano": ano,
            "parlamentar": l.get(papel["parlamentar"]) or "",
            "partido": l.get(papel["partido"]) or "",
            "municipio": l.get(papel["municipio"]) or "",
            "orgao": l.get(papel["orgao"]) or "",
            "objeto": l.get(papel["objeto"]) or "",
            "estagio": l.get(papel["estagio"]) or "",
            "valor": float(l.get(col_val) or 0),
            "fonte": "powerbi-api",
        })
    return saida


# Sinônimos de cabeçalho para o arquivo "Baixar os dados" (nomes podem variar).
_COLS_MANUAL = {
    "parlamentar": ("parlamentar", "deputado", "autor"),
    "partido": ("partido",),
    "municipio": ("municipio", "município", "cidade"),
    "orgao": ("orgao processador", "órgão processador", "orgao", "órgão", "secretaria"),
    "objeto": ("objeto", "descricao", "descrição"),
    "estagio": ("estagio", "estágio", "situacao", "situação", "status"),
    "valor": ("valor decisao", "valor decisão", "valor", "valor autorizado", "valor da emenda"),
}


def linhas_de_arquivo(caminho: Path, ano: int) -> list[dict]:
    """Lê um arquivo baixado à mão (.xlsx/.csv) do painel e devolve linhas cruas.

    Casa as colunas por nome (tolerante a variação de cabeçalho), para o botão
    "Baixar os dados" servir de rede de segurança quando a API não responde.
    """
    if caminho.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(caminho, dtype=str)
    else:
        df = pd.read_csv(caminho, dtype=str, sep=None, engine="python")
    df = df.fillna("")
    norm_cols = {_norm(c): c for c in df.columns}

    def achar(papel):
        for alvo in _COLS_MANUAL[papel]:
            if _norm(alvo) in norm_cols:
                return norm_cols[_norm(alvo)]
        return None

    mapa = {p: achar(p) for p in _COLS_MANUAL}
    faltando = [p for p in ("parlamentar", "municipio", "valor") if not mapa[p]]
    if faltando:
        raise ValueError(f"{caminho.name}: colunas essenciais ausentes: {faltando}. "
                         f"Cabeçalhos vistos: {list(df.columns)}")

    def val(x):
        t = "".join(ch for ch in str(x) if ch.isdigit() or ch in ",.-")
        t = t.replace(".", "").replace(",", ".")
        try:
            return float(t)
        except ValueError:
            return 0.0

    saida = []
    for _, r in df.iterrows():
        if not str(r[mapa["parlamentar"]]).strip():
            continue
        saida.append({
            "ano": ano,
            "parlamentar": str(r[mapa["parlamentar"]]).strip(),
            "partido": str(r[mapa["partido"]]).strip() if mapa["partido"] else "",
            "municipio": str(r[mapa["municipio"]]).strip(),
            "orgao": str(r[mapa["orgao"]]).strip() if mapa["orgao"] else "",
            "objeto": str(r[mapa["objeto"]]).strip() if mapa["objeto"] else "",
            "estagio": str(r[mapa["estagio"]]).strip() if mapa["estagio"] else "",
            "valor": val(r[mapa["valor"]]),
            "fonte": "arquivo-manual",
        })
    return saida


def obter_linhas_do_ano(ano: int) -> tuple[list[dict], str]:
    """Uma entrada por ano: tenta a API; se falhar, cai para o arquivo manual.

    Devolve (linhas, origem). origem ∈ {"powerbi-api", "arquivo-manual",
    "indisponível"}. Nunca levanta: a feature degrada, não morre.
    """
    try:
        return linhas_da_api(ano), "powerbi-api"
    except Exception as e:  # noqa: BLE001
        print(f"  [aviso] API falhou para {ano}: {e}")
    # degradação: procura um arquivo manual data/emendas_manual/<ano>.*
    if DIR_MANUAL.is_dir():
        for cand in sorted(DIR_MANUAL.glob(f"{ano}.*")):
            try:
                return linhas_de_arquivo(cand, ano), "arquivo-manual"
            except Exception as e:  # noqa: BLE001
                print(f"  [aviso] arquivo {cand.name} ilegível: {e}")
    print(f"  [aviso] {ano} sem API e sem arquivo manual — ano ignorado")
    return [], "indisponível"


# --------------------------------------------------------------------------- #
# Pipeline: casar nomes, classificar, agregar
# --------------------------------------------------------------------------- #
def construir_base(linhas: list[dict], curados: pd.DataFrame) -> dict:
    """Transforma linhas cruas na base agregada + fila de revisão + relatório.

    Retorna {"base": DataFrame, "revisao": DataFrame, "relatorio": dict}.
    """
    indice = construir_indice_nomes(curados)
    partido_curado = {r["nome"]: r["partido"] for _, r in curados.iterrows()}

    agreg: dict[tuple, dict] = {}
    revisao: dict[str, dict] = {}
    te_excluidas = 0
    te_valor = 0.0
    vistos_por_ano: dict[int, set] = {}

    for l in linhas:
        canon, situacao = casar_parlamentar(l["parlamentar"], indice)
        if canon is None:
            # só vira revisão se houver alguma pista (ambíguo). "sem_match" é
            # outro deputado dos 94 — nem entra (não é um dos 16).
            if situacao == "ambiguo":
                r = revisao.setdefault(l["parlamentar"], {
                    "nome_pbi": l["parlamentar"], "situacao": situacao,
                    "anos": set(), "n_linhas": 0, "valor_total": 0.0})
                r["anos"].add(l["ano"])
                r["n_linhas"] += 1
                r["valor_total"] += l["valor"]
            continue

        vistos_por_ano.setdefault(l["ano"], set()).add(canon)
        te = _e_transferencia_especial(l["objeto"])
        area = classificar_area(l["orgao"], te)
        if te and area == "transferência especial":
            te_excluidas += 1
            te_valor += l["valor"]

        chave = (canon, partido_curado.get(canon, l["partido"]),
                 l["municipio"], l["orgao"], area, l["ano"])
        a = agreg.setdefault(chave, {"n_emendas": 0, "valor_autorizado": 0.0,
                                     "valor_pago": 0.0, "transferencia_especial": te})
        a["n_emendas"] += 1
        a["valor_autorizado"] += l["valor"]
        if _norm(l["estagio"]) == "pagas":       # PAGO só quando estágio = Pagas
            a["valor_pago"] += l["valor"]

    base = pd.DataFrame([
        {"deputado": k[0], "partido": k[1], "municipio": k[2], "orgao_processador": k[3],
         "area": k[4], "ano": k[5], "n_emendas": v["n_emendas"],
         "valor_autorizado": round(v["valor_autorizado"], 2),
         "valor_pago": round(v["valor_pago"], 2),
         "transferencia_especial": v["transferencia_especial"]}
        for k, v in agreg.items()
    ])
    if not base.empty:
        base = base.sort_values(
            ["deputado", "ano", "valor_autorizado"], ascending=[True, True, False]
        ).reset_index(drop=True)

    # curados que não apareceram em NENHUM ano viram item de revisão (ex.: grafia
    # diferente, suplente recente, ou simplesmente sem emendas) — não somem calados
    presentes = set().union(*vistos_por_ano.values()) if vistos_por_ano else set()
    for _, r in curados.iterrows():
        if r["nome"] not in presentes:
            revisao.setdefault(r["nome"], {
                "nome_pbi": "", "situacao": "curado_sem_emenda",
                "anos": set(), "n_linhas": 0, "valor_total": 0.0,
                "deputado_curado": r["nome"]})

    rev = pd.DataFrame([
        {"nome_pbi": v.get("nome_pbi", ""),
         "deputado_curado_suspeito": v.get("deputado_curado", ""),
         "situacao": v["situacao"], "anos": ",".join(map(str, sorted(v["anos"]))),
         "n_linhas": v["n_linhas"], "valor_total": round(v["valor_total"], 2)}
        for v in revisao.values()
    ])

    relatorio = {
        "linhas_cruas": len(linhas),
        "deputados_casados": len(presentes),
        "deputados_curados": len(curados),
        "te_excluidas_do_recorte": te_excluidas,
        "te_valor": round(te_valor, 2),
        "itens_revisao": len(rev),
    }
    return {"base": base, "revisao": rev, "relatorio": relatorio}


# --------------------------------------------------------------------------- #
# Ranking dos 94 por alinhamento ao PFC
# --------------------------------------------------------------------------- #
_PARTICULAS = {"de", "da", "do", "das", "dos", "e"}


def _titulo(nome: str) -> str:
    """'AGENTE FEDERAL DANILO BALAS' -> 'Agente Federal Danilo Balas'."""
    palavras = str(nome).strip().split()
    return " ".join(p.capitalize() if _norm(p) not in _PARTICULAS else p.lower()
                    for p in palavras)


def gerar_ranking(linhas: list[dict], curados: pd.DataFrame) -> pd.DataFrame:
    """Ranking de TODOS os parlamentares (não só os 16) por alinhamento ao PFC.

    Alinhamento = quanto o deputado destinou a EDUCAÇÃO + ASSISTÊNCIA SOCIAL
    (TRANSFERÊNCIA ESPECIAL fica de fora — não tem área). Autorizado e pago
    andam separados. Ordena pelo autorizado no recorte (o "quanto destinou"),
    e traz também a fatia % do total do deputado, para reordenar por proporção
    se quiser. Marca quem já está na planilha do Fábio — os de fora que pontuam
    alto são a descoberta.
    """
    indice = construir_indice_nomes(curados)
    dep: dict[str, dict] = {}
    for l in linhas:
        nome = str(l["parlamentar"]).strip()
        if not nome:
            continue
        te = _e_transferencia_especial(l["objeto"])
        area = classificar_area(l["orgao"], te)
        d = dep.setdefault(nome, {
            "partidos": {}, "auto_geral": 0.0, "auto_te": 0.0,
            "auto_pfc": 0.0, "pago_pfc": 0.0, "n_pfc": 0,
            "mun_auto": {}})  # município -> autorizado no recorte PFC
        if l["partido"]:
            d["partidos"][l["partido"]] = d["partidos"].get(l["partido"], 0) + 1
        pago = l["valor"] if _norm(l["estagio"]) == "pagas" else 0.0
        if te:
            d["auto_te"] += l["valor"]
        else:
            d["auto_geral"] += l["valor"]        # geral = fora de TE
        if area in AREAS_PFC:
            d["auto_pfc"] += l["valor"]
            d["pago_pfc"] += pago
            d["n_pfc"] += 1
            if l["municipio"]:
                d["mun_auto"][l["municipio"]] = d["mun_auto"].get(l["municipio"], 0) + l["valor"]

    linhas_rk = []
    for nome, d in dep.items():
        canon, situacao = casar_parlamentar(nome, indice)
        na_planilha = situacao in ("exato", "normalizado")
        partido = max(d["partidos"], key=d["partidos"].get) if d["partidos"] else ""
        muns = sorted(d["mun_auto"], key=d["mun_auto"].get, reverse=True)
        top_mun = muns[0] if muns else ""
        share = (d["auto_pfc"] / d["auto_geral"] * 100) if d["auto_geral"] else 0.0
        linhas_rk.append({
            "deputado": _titulo(nome),
            "partido": partido,
            "na_planilha_fabio": na_planilha,
            "deputado_fabio": canon or "",
            "autorizado_pfc": round(d["auto_pfc"], 2),
            "pago_pfc": round(d["pago_pfc"], 2),
            "fatia_pfc_pct": round(share, 1),
            "n_emendas_pfc": d["n_pfc"],
            "n_municipios_pfc": len(d["mun_auto"]),
            "municipio_top": top_mun,
            "autorizado_municipio_top": round(d["mun_auto"].get(top_mun, 0), 2),
            "municipios_pfc": "; ".join(muns),
            "autorizado_geral_sem_te": round(d["auto_geral"], 2),
        })

    rk = pd.DataFrame(linhas_rk)
    if rk.empty:
        return rk
    rk = rk.sort_values("autorizado_pfc", ascending=False).reset_index(drop=True)
    rk.insert(0, "posicao", rk.index + 1)
    return rk


# --------------------------------------------------------------------------- #
# Ranking focado nos municípios do PFC (score composto + titulares)
# --------------------------------------------------------------------------- #
def carregar_config_pfc(caminho: Path = CONFIG_PFC) -> dict:
    """Lê config/pfc_municipios.toml: municípios por peso, pesos do score, mínimo.

    Devolve {"peso_por_municipio": {mun_norm: peso}, "grupo_por_municipio":
    {mun_norm: nome_grupo}, "score": {...}, "grupos": [...]}.
    """
    import tomllib
    with open(caminho, "rb") as f:
        cfg = tomllib.load(f)
    peso_por_mun, grupo_por_mun = {}, {}
    for g in cfg.get("grupos", []):
        for m in g.get("municipios", []):
            peso_por_mun[_norm(m)] = float(g["peso"])
            grupo_por_mun[_norm(m)] = g["nome"]

    terr = cfg.get("score_territorio", {})
    exp = cfg.get("score_expansao", {})
    for nome, sec, chaves in (("score_territorio", terr,
                               ("peso_alinhamento", "peso_volume", "peso_presenca")),
                              ("score_expansao", exp,
                               ("peso_alinhamento", "peso_volume_geral", "peso_proximidade"))):
        soma = sum(sec.get(k, 0) for k in chaves)
        if abs(soma - 1.0) > 1e-6:
            raise ValueError(f"pesos de [{nome}] somam {soma}, deveriam somar 1.0 — "
                             f"ajuste {caminho.name}")
    fator = exp.get("fator_vizinho", 0.45)
    if not 0 < fator < 1:
        raise ValueError(f"fator_vizinho={fator} inválido: precisa de 0 < fator < 1 "
                         f"(o vizinho é sempre uma fração do direto). Ajuste {caminho.name}")
    return {"peso_por_municipio": peso_por_mun, "grupo_por_municipio": grupo_por_mun,
            "score_territorio": terr, "score_expansao": exp, "grupos": cfg.get("grupos", [])}


def carregar_titulares(caminho: Path = TITULARES_CSV) -> dict:
    """Titulares em exercício da ALESP: {nome_norm: {"nome": ..., "partido": ...}}."""
    if not caminho.exists():
        return {}
    df = pd.read_csv(caminho, dtype=str).fillna("")
    return {_norm(r["nome_parlamentar"]): {"nome": r["nome_parlamentar"].strip(),
                                           "partido": r.get("partido", "").strip()}
            for _, r in df.iterrows()}


def gerar_ranking_pfc(linhas: list[dict], titulares: dict, config: dict,
                      curados: pd.DataFrame | None = None) -> dict:
    """Ranking dos deputados por alinhamento ao PFC, restrito aos municípios do PFC.

    Score composto (0-100), pesos vindos da config e normalizados pelo maior
    valor entre os que qualificam:
      alinhamento — fatia % das emendas do deputado em educação/social (geral);
      volume      — R$ autorizado a edu/social nos municípios do PFC, ponderado
                    pelo peso do grupo do município;
      presença    — soma dos pesos dos municípios-PFC distintos onde atua.
    Entra no ranking quem é TITULAR em exercício e tem pelo menos `min_emendas`
    emendas de edu/social nos municípios do PFC (trava anti "42% em uma só").

    Retorna {"ranking", "excluidos", "municipios_sem_emenda", "relatorio"}.
    """
    peso_mun = config["peso_por_municipio"]
    grupo_mun = config["grupo_por_municipio"]
    sc = config["score_territorio"]
    min_emendas = int(sc.get("min_emendas", 2))
    idx_curados = construir_indice_nomes(curados) if curados is not None else {}

    def na_planilha(nome):
        return casar_parlamentar(nome, idx_curados)[1] in ("exato", "normalizado")

    # agrega por deputado; separa geral (p/ alinhamento) de território-PFC
    dep: dict[str, dict] = {}
    # cobertura por município do PFC (qualquer deputado) p/ o relatório de lacunas
    mun_cobertura = {m: {"n": 0, "autorizado": 0.0, "deputados": set()} for m in peso_mun}

    for l in linhas:
        nome = str(l["parlamentar"]).strip()
        if not nome:
            continue
        te = _e_transferencia_especial(l["objeto"])
        area = classificar_area(l["orgao"], te)
        pago = l["valor"] if _norm(l["estagio"]) == "pagas" else 0.0
        d = dep.setdefault(nome, {"partidos": {}, "auto_geral": 0.0, "auto_pfc_edusoc": 0.0,
                                  "pago_pfc": 0.0, "n_territorio": 0, "vol_ponderado": 0.0,
                                  "mun_pesos": {}, "mun_auto": {}})
        if l["partido"]:
            d["partidos"][l["partido"]] = d["partidos"].get(l["partido"], 0) + 1
        if not te:
            d["auto_geral"] += l["valor"]
        mnorm = _norm(l["municipio"])
        no_pfc = mnorm in peso_mun
        edusoc = area in AREAS_PFC
        if no_pfc and edusoc and not te:
            peso = peso_mun[mnorm]
            d["auto_pfc_edusoc"] += l["valor"]
            d["pago_pfc"] += pago
            d["n_territorio"] += 1
            d["vol_ponderado"] += l["valor"] * peso
            d["mun_pesos"][l["municipio"]] = peso
            d["mun_auto"][l["municipio"]] = d["mun_auto"].get(l["municipio"], 0) + l["valor"]
            mc = mun_cobertura[mnorm]
            mc["n"] += 1
            mc["autorizado"] += l["valor"]
            mc["deputados"].add(nome)

    # candidatos = quem tem ao menos 1 emenda edu/social no território do PFC
    candidatos = [(nome, d, titulares.get(_norm(nome)))
                  for nome, d in dep.items() if d["n_territorio"] > 0]

    # alinhamento = fatia edu/social GERAL do deputado (qualquer município), então
    # somamos o edu/social geral numa passada dedicada.
    geral_edusoc = {}
    for l in linhas:
        nome = str(l["parlamentar"]).strip()
        if not nome:
            continue
        te = _e_transferencia_especial(l["objeto"])
        if te:
            continue
        if classificar_area(l["orgao"], te) in AREAS_PFC:
            geral_edusoc[nome] = geral_edusoc.get(nome, 0.0) + l["valor"]

    qualificados = [(n, d, t) for (n, d, t) in candidatos
                    if t is not None and d["n_territorio"] >= min_emendas]
    # normalizadores (máximos entre os qualificados)
    max_vol = max((d["vol_ponderado"] for _, d, _ in qualificados), default=0.0) or 1.0
    max_pres = max((sum(d["mun_pesos"].values()) for _, d, _ in qualificados), default=0.0) or 1.0

    def alinhamento_pct(nome, d):
        base = d["auto_geral"]
        return (geral_edusoc.get(nome, 0.0) / base * 100) if base else 0.0

    max_alin = max((alinhamento_pct(n, d) for n, d, _ in qualificados), default=0.0) or 1.0

    linhas_rk = []
    for nome, d, tit in qualificados:
        alin = alinhamento_pct(nome, d)
        presenca = sum(d["mun_pesos"].values())
        c_alin = alin / max_alin
        c_vol = d["vol_ponderado"] / max_vol
        c_pres = presenca / max_pres
        score = 100 * (sc["peso_alinhamento"] * c_alin + sc["peso_volume"] * c_vol
                       + sc["peso_presenca"] * c_pres)
        muns = sorted(d["mun_auto"], key=d["mun_auto"].get, reverse=True)
        grupos_atua = sorted({grupo_mun[_norm(m)] for m in d["mun_auto"]})
        linhas_rk.append({
            "deputado": tit["nome"], "partido": tit["partido"] or (
                max(d["partidos"], key=d["partidos"].get) if d["partidos"] else ""),
            "na_planilha_fabio": na_planilha(nome),
            "score_pfc": round(score, 1),
            "alinhamento_pct": round(alin, 1),
            "autorizado_pfc": round(d["auto_pfc_edusoc"], 2),
            "pago_pfc": round(d["pago_pfc"], 2),
            "volume_ponderado": round(d["vol_ponderado"], 2),
            "presenca_ponderada": round(presenca, 2),
            "n_emendas_territorio": d["n_territorio"],
            "n_municipios_pfc": len(d["mun_auto"]),
            "municipios_pfc": "; ".join(muns),
            "grupos": "; ".join(grupos_atua),
        })
    ranking = pd.DataFrame(linhas_rk)
    if not ranking.empty:
        ranking = ranking.sort_values("score_pfc", ascending=False).reset_index(drop=True)
        ranking.insert(0, "posicao", ranking.index + 1)

    # excluídos: quem tem atividade no território mas NÃO é titular em exercício
    excl = []
    for nome, d, tit in candidatos:
        if tit is not None:
            continue
        muns = sorted(d["mun_auto"], key=d["mun_auto"].get, reverse=True)
        excl.append({"nome_pbi": _titulo(nome),
                     "motivo": "não é titular em exercício (ALESP)",
                     "autorizado_pfc": round(d["auto_pfc_edusoc"], 2),
                     "n_emendas_territorio": d["n_territorio"],
                     "municipios_pfc": "; ".join(muns)})
    excluidos = pd.DataFrame(excl).sort_values(
        "autorizado_pfc", ascending=False).reset_index(drop=True) if excl else pd.DataFrame(
        columns=["nome_pbi", "motivo", "autorizado_pfc", "n_emendas_territorio", "municipios_pfc"])

    # relatório de lacuna: municípios do PFC sem NENHUMA emenda edu/social
    nome_orig = {}
    for g in config["grupos"]:
        for m in g["municipios"]:
            nome_orig[_norm(m)] = (m, g["nome"], g["peso"])
    linhas_sem = []
    for mnorm, mc in mun_cobertura.items():
        m, grupo, peso = nome_orig.get(mnorm, (mnorm, "", 0))
        linhas_sem.append({"municipio": m, "grupo": grupo, "peso": peso,
                           "n_emendas_edu_social": mc["n"],
                           "autorizado_total": round(mc["autorizado"], 2),
                           "n_deputados": len(mc["deputados"])})
    cobertura = pd.DataFrame(linhas_sem).sort_values(
        ["n_emendas_edu_social", "municipio"]).reset_index(drop=True)
    sem_emenda = cobertura[cobertura["n_emendas_edu_social"] == 0].reset_index(drop=True)

    # titulares que qualificariam por atividade mas ficaram abaixo do mínimo,
    # e titulares sem nenhuma atividade no território — para o relatório
    titulares_sem_territorio = sorted(
        t["nome"] for k, t in titulares.items()
        if k not in {_norm(n) for n, d, _ in candidatos})
    abaixo_min = sorted(
        tit["nome"] for n, d, tit in candidatos
        if tit is not None and d["n_territorio"] < min_emendas)

    relatorio = {
        "titulares_total": len(titulares),
        "no_ranking": len(ranking),
        "excluidos_nao_titulares": len(excluidos),
        "titulares_abaixo_do_minimo": abaixo_min,
        "titulares_sem_atividade_territorio": len(titulares_sem_territorio),
        "municipios_pfc_total": len(peso_mun),
        "municipios_pfc_sem_emenda": list(sem_emenda["municipio"]),
        "min_emendas": min_emendas,
    }
    return {"ranking": ranking, "excluidos": excluidos, "cobertura": cobertura,
            "municipios_sem_emenda": sem_emenda, "relatorio": relatorio}


def carregar_regioes_ibge(caminho: Path = REGIOES_IBGE_CSV) -> dict:
    """Regiões Geográficas Imediatas 2017 (IBGE): {municipio_norm: (ri_id, ri_nome)}
    e {ri_id: set(municipio_norm)}."""
    if not caminho.exists():
        return {"por_municipio": {}, "por_regiao": {}}
    df = pd.read_csv(caminho, dtype=str).fillna("")
    por_mun, por_regiao = {}, {}
    for _, r in df.iterrows():
        mn = _norm(r["municipio"])
        ri = (r["regiao_imediata_id"], r["regiao_imediata_nome"])
        por_mun[mn] = ri
        por_regiao.setdefault(r["regiao_imediata_id"], set()).add(mn)
    return {"por_municipio": por_mun, "por_regiao": por_regiao}


def mapear_vizinhos(config: dict, regioes: dict) -> dict:
    """Municípios VIZINHOS dos do PFC (mesma Região Imediata), com peso-base.

    base = maior peso de grupo entre os municípios do PFC que estão na mesma
    Região Imediata do vizinho. Vizinho que também é do PFC não entra (é direto).
    Devolve {municipio_norm_vizinho: base}.
    """
    peso_mun = config["peso_por_municipio"]
    por_mun = regioes["por_municipio"]
    por_regiao = regioes["por_regiao"]
    # peso-base por Região Imediata = maior peso de grupo entre os PFC dela
    base_por_ri: dict[str, float] = {}
    for mn, peso in peso_mun.items():
        ri = por_mun.get(mn)
        if ri:
            base_por_ri[ri[0]] = max(base_por_ri.get(ri[0], 0.0), peso)
    vizinhos = {}
    for ri_id, base in base_por_ri.items():
        for mn in por_regiao.get(ri_id, set()):
            if mn not in peso_mun:            # exclui os próprios municípios do PFC
                vizinhos[mn] = max(vizinhos.get(mn, 0.0), base)
    return vizinhos


def _perfil_deputados(linhas: list[dict], peso_mun: dict, vizinhos: dict | None = None,
                      fator_vizinho: float = 0.0) -> dict:
    """Perfil por deputado usado nas duas seções: volume/alinhamento GERAL de
    edu/social (estado todo), o pé DIRETO no território do PFC e o pé VIZINHO
    (mesma Região Imediata). Proximidade em 3 níveis:
        direto  = valor * peso_grupo               (peso cheio)
        vizinho = valor * base_ri * fator_vizinho   (fração do direto da região)
        longe   = 0
    """
    vizinhos = vizinhos or {}
    perfil: dict[str, dict] = {}
    for l in linhas:
        nome = str(l["parlamentar"]).strip()
        if not nome:
            continue
        te = _e_transferencia_especial(l["objeto"])
        area = classificar_area(l["orgao"], te)
        pago = l["valor"] if _norm(l["estagio"]) == "pagas" else 0.0
        p = perfil.setdefault(nome, {
            "partidos": {}, "auto_geral": 0.0,          # total non-TE (denominador da fatia)
            "edusoc_auto": 0.0, "edusoc_pago": 0.0,     # edu/social no estado todo
            "mun_edusoc": set(),                          # municípios (estado) c/ edu/social
            "terr_auto": 0.0, "terr_pond": 0.0,          # DIRETO: R$ e peso no território
            "terr_emendas": 0, "terr_mun": {},
            "viz_auto": 0.0, "viz_pond": 0.0, "viz_mun": {}})  # VIZINHO
        if l["partido"]:
            p["partidos"][l["partido"]] = p["partidos"].get(l["partido"], 0) + 1
        if te:
            continue
        p["auto_geral"] += l["valor"]
        if area in AREAS_PFC:
            p["edusoc_auto"] += l["valor"]
            p["edusoc_pago"] += pago
            mnorm = _norm(l["municipio"])
            if l["municipio"]:
                p["mun_edusoc"].add(mnorm)
            if mnorm in peso_mun:                        # DIRETO
                peso = peso_mun[mnorm]
                p["terr_auto"] += l["valor"]
                p["terr_pond"] += l["valor"] * peso
                p["terr_emendas"] += 1
                p["terr_mun"][l["municipio"]] = peso
            elif mnorm in vizinhos:                      # VIZINHO
                base = vizinhos[mnorm]
                p["viz_auto"] += l["valor"]
                p["viz_pond"] += l["valor"] * base * fator_vizinho
                p["viz_mun"][l["municipio"]] = round(base * fator_vizinho, 3)
    return perfil


def gerar_ranking_expansao(linhas: list[dict], titulares: dict, config: dict,
                           curados: pd.DataFrame | None = None,
                           regioes: dict | None = None) -> dict:
    """Seção 2 — "Expansão" (cortejar).

    Alvos de MÉDIO prazo: titulares com alto alinhamento e alto volume GERAL de
    educação/social no estado, que ainda NÃO destinam (ou destinam pouco) para
    os municípios do PFC. O contrário de caso perdido — emenda se redireciona a
    cada ciclo, e quem já financia educação pesado é o mais fácil de trazer.

    Score composto (0-100), pesos de [score_expansao] normalizados pelo maior
    valor entre os elegíveis:
      alinhamento  — fatia % edu/social do deputado (orientação);
      volume_geral — R$ autorizado a edu/social em TODO o estado (potência);
      proximidade  — FACILITADOR em 3 níveis: DIRETO (município do PFC, peso do
                     grupo) + VIZINHO (mesma Região Imediata, fração do direto)
                     + LONGE (zero). Quem já atua aqui ou ao lado é mais fácil.

    Elegível = TITULAR em exercício + volume geral edu/social >= min_volume_geral
    + NÃO ser da Seção 1 (menos que `min_emendas` do território). As duas seções
    particionam pelos mesmos deputados: quem já está no território sai daqui.
    """
    sc = config["score_expansao"]
    peso_mun = config["peso_por_municipio"]
    min_vol = float(sc.get("min_volume_geral", 0))
    fator_viz = float(sc.get("fator_vizinho", 0.45))
    camada_min = float(sc.get("camada_prioritaria_min", 5_000_000))
    min_emendas_terr = int(config["score_territorio"].get("min_emendas", 2))
    vizinhos = mapear_vizinhos(config, regioes) if regioes else {}
    perfil = _perfil_deputados(linhas, peso_mun, vizinhos, fator_viz)
    idx_curados = construir_indice_nomes(curados) if curados is not None else {}

    elegiveis = []
    for nome, p in perfil.items():
        tit = titulares.get(_norm(nome))
        if tit is None:
            continue                                   # só titulares em exercício
        if p["edusoc_auto"] < min_vol:
            continue                                   # volume geral irrelevante
        if p["terr_emendas"] >= min_emendas_terr:
            continue                                   # já é da Seção 1 (no território)
        elegiveis.append((nome, p, tit))

    def alin_de(p):
        return (p["edusoc_auto"] / p["auto_geral"] * 100) if p["auto_geral"] else 0.0

    max_alin = max((alin_de(p) for _, p, _ in elegiveis), default=0.0) or 1.0
    max_vol = max((p["edusoc_auto"] for _, p, _ in elegiveis), default=0.0) or 1.0
    # proximidade = direto + vizinho. O MESMO normalizador vale para o score com
    # e sem vizinhança, para os dois serem comparáveis (sem viz <= com viz sempre).
    max_prox = max((p["terr_pond"] + p["viz_pond"] for _, p, _ in elegiveis), default=0.0) or 1.0

    def score(p, prox_pond):
        return 100 * (sc["peso_alinhamento"] * (alin_de(p) / max_alin)
                      + sc["peso_volume_geral"] * (p["edusoc_auto"] / max_vol)
                      + sc["peso_proximidade"] * (prox_pond / max_prox))

    linhas_rk = []
    for nome, p, tit in elegiveis:
        prox_total = p["terr_pond"] + p["viz_pond"]
        s_novo = score(p, prox_total)
        s_antigo = score(p, p["terr_pond"])   # contrafactual: se vizinho não contasse
        muns_terr = sorted(p["terr_mun"], key=lambda m: p["terr_mun"][m], reverse=True)
        muns_viz = sorted(p["viz_mun"], key=lambda m: p["viz_mun"][m], reverse=True)
        vol = p["edusoc_auto"]
        linhas_rk.append({
            "deputado": tit["nome"],
            "partido": tit["partido"] or (max(p["partidos"], key=p["partidos"].get)
                                          if p["partidos"] else ""),
            "na_planilha_fabio": casar_parlamentar(nome, idx_curados)[1] in ("exato", "normalizado"),
            "camada": "alvo prioritário" if vol >= camada_min else "demais candidatos",
            "score_expansao": round(s_novo, 1),
            "score_sem_vizinhanca": round(s_antigo, 1),
            "alinhamento_pct": round(alin_de(p), 1),
            "autorizado_geral_edusoc": round(vol, 2),
            "pago_geral_edusoc": round(p["edusoc_pago"], 2),
            "n_municipios_edusoc": len(p["mun_edusoc"]),
            "proximidade_ponderada": round(prox_total, 2),
            "prox_direto": round(p["terr_pond"], 2),
            "prox_vizinho": round(p["viz_pond"], 2),
            "autorizado_direto": round(p["terr_auto"], 2),
            "autorizado_vizinho": round(p["viz_auto"], 2),
            "municipios_pfc_diretos": "; ".join(muns_terr),
            "municipios_vizinhos": "; ".join(muns_viz),
        })
    rk = pd.DataFrame(linhas_rk)
    if not rk.empty:
        # ranks globais por score (para medir o efeito da vizinhança): antigo x novo
        rk["posicao_sem_vizinhanca"] = rk["score_sem_vizinhanca"].rank(
            ascending=False, method="first").astype(int)
        rk["posicao_global"] = rk["score_expansao"].rank(
            ascending=False, method="first").astype(int)
        rk["subiu_por_vizinhanca"] = rk["posicao_sem_vizinhanca"] - rk["posicao_global"]
        # ordenação final em CAMADAS (prioritários antes; score dentro de cada)
        ordem_camada = {"alvo prioritário": 0, "demais candidatos": 1}
        rk["_c"] = rk["camada"].map(ordem_camada)
        rk = rk.sort_values(["_c", "score_expansao"], ascending=[True, False]).drop(
            columns="_c").reset_index(drop=True)
        rk.insert(0, "posicao", rk.index + 1)

    relatorio = {
        "elegiveis": len(rk),
        "min_volume_geral": min_vol,
        "fator_vizinho": fator_viz,
        "prioritarios": int((rk["camada"] == "alvo prioritário").sum()) if not rk.empty else 0,
        "com_pe_direto": int((rk["prox_direto"] > 0).sum()) if not rk.empty else 0,
        "com_vizinhanca": int((rk["prox_vizinho"] > 0).sum()) if not rk.empty else 0,
    }
    return {"ranking": rk, "relatorio": relatorio}


# --------------------------------------------------------------------------- #
# Orquestração
# --------------------------------------------------------------------------- #
def gerar(anos=(2023, 2024, 2025), respostas: dict | None = None) -> dict:
    """Extrai os anos, monta a base e grava os CSVs. `respostas` permite injetar
    JSONs já baixados (usado nos testes/verificação, sem tocar a rede)."""
    curados = carregar_lista_curada()
    if curados.empty:
        raise RuntimeError("lista curada vazia — sem os 16 deputados não há chave de casamento")

    todas, origens = [], {}
    for ano in anos:
        if respostas and ano in respostas:
            linhas, origem = linhas_da_api(ano, respostas[ano]), "powerbi-api(injetado)"
        else:
            linhas, origem = obter_linhas_do_ano(ano)
        origens[ano] = (origem, len(linhas))
        todas.extend(linhas)

    resultado = construir_base(todas, curados)
    resultado["ranking"] = gerar_ranking(todas, curados)  # todos os 94, não só os 16
    SAIDA_BASE.parent.mkdir(parents=True, exist_ok=True)
    resultado["base"].to_csv(SAIDA_BASE, index=False, encoding="utf-8-sig")
    resultado["revisao"].to_csv(SAIDA_REVISAO, index=False, encoding="utf-8-sig")
    resultado["ranking"].to_csv(SAIDA_RANKING, index=False, encoding="utf-8-sig")

    # Ranking do PFC em duas seções (território e expansão), se houver config
    if CONFIG_PFC.exists():
        titulares, cfg = carregar_titulares(), carregar_config_pfc()
        regioes = carregar_regioes_ibge()
        pfc = gerar_ranking_pfc(todas, titulares, cfg, curados)                    # Seção 1
        exp = gerar_ranking_expansao(todas, titulares, cfg, curados, regioes)      # Seção 2
        pfc["ranking"].to_csv(SAIDA_RANKING_TERRITORIO, index=False, encoding="utf-8-sig")
        exp["ranking"].to_csv(SAIDA_RANKING_EXPANSAO, index=False, encoding="utf-8-sig")
        pfc["excluidos"].to_csv(SAIDA_EXCLUIDOS, index=False, encoding="utf-8-sig")
        pfc["municipios_sem_emenda"].to_csv(SAIDA_MUN_SEM, index=False, encoding="utf-8-sig")
        resultado["pfc"] = pfc
        resultado["expansao"] = exp

    resultado["origens"] = origens
    return resultado


def main():
    print("Extraindo emendas parlamentares (Power BI 2023-2025)...")
    res = gerar()
    r = res["relatorio"]
    print("\nOrigem por ano:")
    for ano, (origem, n) in res["origens"].items():
        print(f"  {ano}: {origem}  ({n} linhas)")
    print("\nRelatório:")
    for k, v in r.items():
        print(f"  {k}: {v}")
    print(f"\nBase   -> {SAIDA_BASE}  ({len(res['base'])} linhas)")
    print(f"Revisão-> {SAIDA_REVISAO}  ({len(res['revisao'])} itens)")
    if not res["revisao"].empty:
        print("\nFila de revisão de nomes:")
        for _, x in res["revisao"].iterrows():
            print(f"  [{x['situacao']}] {x['nome_pbi'] or x['deputado_curado_suspeito']}")


if __name__ == "__main__":
    sys.exit(main())
