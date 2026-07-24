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
SAIDA_BASE = RAIZ / "data" / "emendas_parlamentares.csv"
SAIDA_REVISAO = RAIZ / "data" / "emendas_revisao_nomes.csv"

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
    SAIDA_BASE.parent.mkdir(parents=True, exist_ok=True)
    resultado["base"].to_csv(SAIDA_BASE, index=False, encoding="utf-8-sig")
    resultado["revisao"].to_csv(SAIDA_REVISAO, index=False, encoding="utf-8-sig")
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
