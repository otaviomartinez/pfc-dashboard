"""Mapa da cota parlamentar: quais deputados federais de SP CIRCULAM no
território do PFC — e quando foi a última vez.

Lê data/cota/presenca_federais_sp.csv, gerado no GitHub Actions por
scripts/importar_cota_parlamentar.py (o site da Câmara é bloqueado no ambiente
do assistente, não no GitHub).

O QUE É E O QUE NÃO É (a tela é obrigada a dizer):
  - É SINAL DE CIRCULAÇÃO: o deputado (ou a equipe dele) abasteceu, comeu ou se
    hospedou numa cidade, com nota paga pela cota. O posto e o restaurante
    ficam onde a nota foi emitida — por isso só essas três categorias.
  - NÃO é agenda: não diz onde ele está hoje. A Câmara publica com atraso (o
    deputado tem até 90 dias para apresentar a nota).
  - NÃO é endereço de escritório: as contas do escritório (luz, telefone) vêm
    de empresas cuja sede pode ser em outra cidade. Ficam num campo à parte,
    rotulado como "fornecedores do escritório".
  - Sem registro ≠ nunca veio: pode ter vindo sem gastar pela cota.

PURO: sem rede, sem Streamlit.
"""
from __future__ import annotations

import csv
import os

from src.score_senador import norm_municipio

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PRESENCA = os.path.join(BASE, "data", "cota", "presenca_federais_sp.csv")
CSV_RESUMO = os.path.join(BASE, "data", "cota", "coleta_resumo.csv")

# Categorias da cota que provam PRESENÇA física na cidade do fornecedor.
PRESENCA = "presenca"
ESCRITORIO = "escritorio"
# Mínimo de notas para dizer "frequenta" (uma nota só pode ser passagem).
MIN_FREQUENTA = 3

CLASSES = {
    "frequenta_pfc": "Frequenta cidades do PFC",
    "passa_regiao": "Passa pela região",
    "sem_registro": "Sem registro na região",
}


def _int(v) -> int:
    try:
        return int(float(str(v).replace(",", ".") or 0))
    except ValueError:
        return 0


def _float(v) -> float:
    try:
        return float(str(v).replace(",", ".") or 0)
    except ValueError:
        return 0.0


def carregar(caminho: str | None = None) -> list[dict]:
    """Linhas agregadas (deputado x município x grupo). Sem arquivo -> []."""
    try:
        with open(caminho or CSV_PRESENCA, encoding="utf-8-sig", newline="") as f:
            return [dict(r) for r in csv.DictReader(f)]
    except (FileNotFoundError, OSError):
        return []


def carregar_resumo(caminho: str | None = None) -> dict:
    """Metadados da coleta: anos, período, cobertura de CNPJ. Sem arquivo -> {}."""
    try:
        with open(caminho or CSV_RESUMO, encoding="utf-8-sig", newline="") as f:
            return {r["chave"]: r["valor"] for r in csv.DictReader(f)}
    except (FileNotFoundError, OSError, KeyError):
        return {}


def territorio_padrao() -> tuple[set, set]:
    """(cidades do PFC, vizinhas) — o MESMO território do ranking de emendas
    (config/pfc_municipios.toml + Regiões Imediatas do IBGE)."""
    try:
        from src import emendas
        cfg = emendas.carregar_config_pfc()
        viz = emendas.mapear_vizinhos(cfg, emendas.carregar_regioes_ibge())
    except Exception:
        return set(), set()
    pfc = {norm_municipio(m) for m in cfg["peso_por_municipio"]}
    return pfc, {norm_municipio(m) for m in viz} - pfc


def montar_mapa(linhas: list[dict], pfc: set, vizinhas: set) -> list[dict]:
    """Um registro por deputado, do que mais circula no território ao que menos.

    Cada um: {deputado_id, deputado, partido, notas_pfc, notas_vizinhas,
    notas_sp, cidades_pfc [(cidade, notas, ultima)], cidades_vizinhas,
    ultima_regiao, escritorio [(cidade, notas)], classe, classe_rotulo}.
    A ordem usa NOTAS (contagem), não valor: um jantar caro não é mais
    presença que três abastecimentos.
    """
    por_dep: dict[str, dict] = {}
    for r in linhas:
        did = str(r.get("deputado_id") or r.get("deputado")).strip()
        if not did:
            continue
        d = por_dep.setdefault(did, {
            "deputado_id": did, "deputado": r.get("deputado", ""), "partido": r.get("partido", ""),
            "notas_pfc": 0, "notas_vizinhas": 0, "notas_sp": 0, "_pfc": {}, "_viz": {},
            "_esc": {}, "ultima_regiao": ""})
        mun, cidade = norm_municipio(r.get("municipio")), r.get("municipio", "")
        n, ultima = _int(r.get("notas")), str(r.get("ultima_data", ""))[:10]
        if r.get("grupo") == ESCRITORIO:
            if str(r.get("uf", "SP")).upper() == "SP":
                d["_esc"][cidade] = d["_esc"].get(cidade, 0) + n
            continue
        if str(r.get("uf", "SP")).upper() != "SP":
            continue
        d["notas_sp"] += n
        alvo = "_pfc" if mun in pfc else "_viz" if mun in vizinhas else None
        if not alvo:
            continue
        d["notas_pfc" if alvo == "_pfc" else "notas_vizinhas"] += n
        n0, u0 = d[alvo].get(cidade, (0, ""))
        d[alvo][cidade] = (n0 + n, max(u0, ultima))
        d["ultima_regiao"] = max(d["ultima_regiao"], ultima)

    saida = []
    for d in por_dep.values():
        d["cidades_pfc"] = sorted(((c, n, u) for c, (n, u) in d.pop("_pfc").items()),
                                  key=lambda x: (-x[1], x[0]))
        d["cidades_vizinhas"] = sorted(((c, n, u) for c, (n, u) in d.pop("_viz").items()),
                                       key=lambda x: (-x[1], x[0]))
        d["escritorio"] = sorted(d.pop("_esc").items(), key=lambda x: (-x[1], x[0]))
        if d["notas_pfc"] >= MIN_FREQUENTA:
            d["classe"] = "frequenta_pfc"
        elif d["notas_pfc"] or d["notas_vizinhas"] >= MIN_FREQUENTA:
            d["classe"] = "passa_regiao"
        else:
            d["classe"] = "sem_registro"
        d["classe_rotulo"] = CLASSES[d["classe"]]
        saida.append(d)
    ordem = list(CLASSES)
    saida.sort(key=lambda d: (ordem.index(d["classe"]), -d["notas_pfc"], -d["notas_vizinhas"],
                              d["deputado"]))
    return saida


def por_cidade(mapa: list[dict], incluir_vizinhas: bool = False) -> list[dict]:
    """Visão inversa: para cada cidade, quem passou por lá (mais notas primeiro).
    [{cidade, total_notas, deputados: [(deputado, notas, ultima, deputado_id)]}]."""
    cidades: dict[str, dict] = {}
    for d in mapa:
        fontes = d["cidades_pfc"] + (d["cidades_vizinhas"] if incluir_vizinhas else [])
        for cidade, n, ultima in fontes:
            c = cidades.setdefault(cidade, {"cidade": cidade, "total_notas": 0, "deputados": []})
            c["total_notas"] += n
            c["deputados"].append((d["deputado"], n, ultima, d["deputado_id"]))
    for c in cidades.values():
        c["deputados"].sort(key=lambda x: (-x[1], x[0]))
    return sorted(cidades.values(), key=lambda c: (-c["total_notas"], c["cidade"]))


def data_br(iso: str) -> str:
    """'2026-08-14' -> '14/08/2026'; vazio continua vazio."""
    s = str(iso or "")[:10]
    return f"{s[8:10]}/{s[5:7]}/{s[:4]}" if len(s) == 10 and s[4] == "-" else s
