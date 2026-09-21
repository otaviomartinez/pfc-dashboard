"""Cliente do SICONFI (Tesouro Nacional) + parsers PUROS do RREO.

API REST pública, sem autenticação:
  https://apidatalake.tesouro.gov.br/ords/siconfi/tt/
Resposta: JSON {"items": [...], "hasMore": bool}.

DUAS REGRAS QUE MANDAM AQUI
1. Nada disto roda no Streamlit. É script offline (python -m src.prefeituras),
   que grava CSV; o app só lê o CSV.
2. Honestidade de período (irmã da regra 3 do CLAUDE.md, a das datas de edital):
   percentual SEM exercício e bimestre amarrados NÃO EXISTE — devolve None e o
   app rotula "sem dado do exercício X". Dado errado é pior que dado ausente.

O anexo do MDE é o RREO-Anexo 08 (Receitas e Despesas com MDE), publicado no 6º
bimestre. A string de `no_anexo` é frágil: se mudar, a API responde 200 com
items=[] — vazio SILENCIOSO. Por isso `buscar_rreo` devolve None (não []) quando
não vem item algum, para o chamador distinguir "não veio" de "veio zero".
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request

BASE_URL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
ANEXO_MDE = "RREO-Anexo 08"        # Receitas e despesas com MDE (art. 212 CF)
ANEXO_FUNDEB = "RREO-Anexo 10"     # FUNDEB (mínimo de 70% p/ magistério)
ANEXO_RGF_CAIXA = "RGF-Anexo 05"   # Disponibilidade de caixa
TIMEOUT = 30


def _get(caminho: str, params: dict, tentativas: int = 3) -> dict | None:
    """GET com retry suave. Devolve o JSON ou None (nunca levanta)."""
    url = f"{BASE_URL}/{caminho}?" + urllib.parse.urlencode(params)
    for n in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if n == tentativas - 1:
                return None
            time.sleep(1.5 * (n + 1))   # backoff suave; a API do Tesouro é lenta
    return None


def buscar_entes(uf: str = "SP") -> list[dict]:
    """Entes do SICONFI (cod_ibge, ente, uf). [] se a API não responder."""
    dados = _get("entes", {})
    itens = (dados or {}).get("items") or []
    return [i for i in itens if str(i.get("uf", "")).upper() == uf.upper()] if uf else itens


def buscar_rreo(cod_ibge: str, exercicio: int, periodo: int = 6,
                anexo: str = ANEXO_MDE, tentativas: int = 3) -> list[dict] | None:
    """Linhas do RREO de um município, ou None quando não veio nada.

    None (e não []) é proposital: `items` vazio costuma significar string de
    anexo errada ou exercício não publicado — quem chama precisa poder rotular
    "sem dado" em vez de assumir zero.
    """
    dados = _get("rreo", {
        "an_exercicio": exercicio, "nr_periodo": periodo,
        "co_tipo_demonstrativo": "RREO", "no_anexo": anexo, "id_ente": cod_ibge,
    }, tentativas=tentativas)
    if not dados:
        return None
    itens = dados.get("items") or []
    return itens or None


def buscar_rgf(cod_ibge: str, exercicio: int, periodo: int = 3,
               anexo: str = ANEXO_RGF_CAIXA) -> list[dict] | None:
    """Linhas do RGF (disponibilidade de caixa). None quando não veio nada."""
    dados = _get("rgf", {
        "an_exercicio": exercicio, "nr_periodo": periodo,
        "co_tipo_demonstrativo": "RGF", "no_anexo": anexo,
        "co_poder": "E", "id_ente": cod_ibge,
    })
    if not dados:
        return None
    itens = dados.get("items") or []
    return itens or None


# --------------------------------------------------------------------------- #
# Parsers PUROS (sem rede) — testáveis com fixture
# --------------------------------------------------------------------------- #
def _num(v):
    """Número tolerante: aceita '1.234,56', 1234.56, None. Devolve float ou None."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    t = str(v).strip().replace("R$", "").replace(" ", "")
    if not t:
        return None
    if "," in t:                      # formato pt-BR: 1.234,56
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def _casa(texto: str, *termos: str) -> bool:
    t = str(texto or "").lower()
    return all(x in t for x in termos)


def _campos(it: dict) -> tuple[str, str, float | None]:
    """(rotulo, coluna, valor) de uma linha do RREO.

    A API responde com `rotulo` (a conta) + `coluna` (qual medida: "% Aplicado",
    "Até o Bimestre"...) + `valor`. Os nomes `conta`/`vl_conta` são aceitos por
    compatibilidade, mas NÃO são o que o SICONFI devolve — descobrimos isso pelo
    log do Actions, depois de o parser antigo ler zero linha de 489.
    """
    rotulo = str(it.get("rotulo") or it.get("conta") or it.get("no_conta") or "")
    coluna = str(it.get("coluna") or "")
    return rotulo, coluna, _num(it.get("valor", it.get("vl_conta")))


def extrair_mde(items, exercicio: int | None = None,
                periodo: int | None = None) -> dict | None:
    """{percentual, valor_aplicado, receita_base, exercicio, periodo} ou None.

    Lê as linhas do RREO-Anexo 08. O percentual pode vir pronto numa linha de
    'APLICAÇÃO EM MDE' / 'MÍNIMO DE 25%'; se não vier, é calculado de
    valor_aplicado / receita_base. SEM exercício e período confirmados, devolve
    None — percentual solto não existe (ver docstring do módulo).
    """
    if not items:
        return None
    pct = valor = receita = None
    exe, per = exercicio, periodo
    for it in items:
        rotulo, coluna, v = _campos(it)
        exe = exe or it.get("exercicio") or it.get("an_exercicio")
        per = per or it.get("periodo") or it.get("nr_periodo")
        if v is None:
            continue
        texto = f"{rotulo} {coluna}"
        # percentual: a medida vem na COLUNA ("% Aplicado ..."), não no rótulo
        e_percentual = "%" in coluna or _casa(coluna, "aplicad")
        if pct is None and e_percentual and 0 < v <= 100 and (
                _casa(texto, "mde") or _casa(texto, "manuten")
                or _casa(texto, "ensino") or _casa(texto, "educac")):
            pct = v
        if valor is None and not e_percentual and _casa(rotulo, "total") \
                and _casa(rotulo, "despesa"):
            valor = v
        if receita is None and not e_percentual and _casa(rotulo, "receita") and \
                (_casa(rotulo, "impostos") or _casa(rotulo, "result")):
            receita = v
    if pct is None and valor and receita:
        pct = round(valor / receita * 100, 2)
    if pct is None:
        return None
    try:
        exe = int(exe) if exe is not None else None
        per = int(per) if per is not None else None
    except (TypeError, ValueError):
        exe, per = None, None
    if exe is None:                    # sem exercício amarrado, o dado não existe
        return None
    return {"percentual": round(float(pct), 2), "valor_aplicado": valor,
            "receita_base": receita, "exercicio": exe, "periodo": per}


def extrair_caixa(items) -> dict | None:
    """{disponibilidade} do RGF-Anexo 05, ou None."""
    if not items:
        return None
    for it in items:
        rotulo, _coluna, v = _campos(it)
        if v is not None and _casa(rotulo, "disponibilidade") and _casa(rotulo, "caixa"):
            return {"disponibilidade": v}
    return None


# --------------------------------------------------------------------------- #
# Fallback manual (igual ao de emendas): arquivo baixado à mão
# --------------------------------------------------------------------------- #
DIR_MANUAL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "prefeituras_manual")


def ler_manual(exercicio: int) -> list[dict]:
    """Linhas de data/prefeituras_manual/<ano>.csv (ou .xlsx). [] se não houver.

    Aceita CSV *e* XLSX de propósito: o XLSX exige openpyxl, que NÃO está no
    requirements.txt — sem ele, o CSV resolve sem tocar no ambiente do deploy.
    Espera as colunas: cod_ibge, percentual, valor_aplicado, receita_base,
    exercicio, periodo (nomes tolerantes a maiúsculas/espaços).
    """
    import csv as _csv
    base = os.path.join(DIR_MANUAL, str(exercicio))
    linhas: list[dict] = []
    if os.path.isfile(base + ".csv"):
        try:
            with open(base + ".csv", encoding="utf-8-sig") as f:
                linhas = list(_csv.DictReader(f))
        except OSError:
            return []
    elif os.path.isfile(base + ".xlsx"):
        try:
            import pandas as pd
            linhas = pd.read_excel(base + ".xlsx").to_dict("records")
        except Exception:
            return []   # sem openpyxl/arquivo corrompido -> degrade, não quebra
    return [{str(k).strip().lower(): v for k, v in linha.items()} for linha in linhas]


def mde_do_manual(cod_ibge: str, exercicio: int) -> dict | None:
    """Registro de MDE do fallback manual para um município, ou None."""
    for linha in ler_manual(exercicio):
        if str(linha.get("cod_ibge", "")).strip() == str(cod_ibge).strip():
            pct = _num(linha.get("percentual"))
            if pct is None:
                return None
            per = _num(linha.get("periodo"))
            return {"percentual": round(pct, 2),
                    "valor_aplicado": _num(linha.get("valor_aplicado")),
                    "receita_base": _num(linha.get("receita_base")),
                    "exercicio": int(exercicio),
                    "periodo": int(per) if per is not None else None}
    return None
