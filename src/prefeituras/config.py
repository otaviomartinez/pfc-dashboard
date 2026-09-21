"""Config dos municípios do painel Prefeituras (config/pfc_prefeituras.toml).

Lê o TOML no formato `[[municipios]]` (nome, cod_ibge, regiao_imediata_*) e
RECONFERE cada código contra a tabela oficial do IBGE, reusando o índice de
`resolver_ibge` — não duplica a leitura do CSV.

Por que reconferir a cada carregamento: o plano proíbe chutar código IBGE, e um
código errado não dá erro — faz o SICONFI responder VAZIO em silêncio, que é o
pior tipo de bug deste projeto. Então falha aqui, barulhento, nomeando o
município.
"""
from __future__ import annotations

import os
import tomllib

from src.prefeituras.resolver_ibge import _norm, indexar_por_municipio

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG = os.path.join(BASE, "config", "pfc_prefeituras.toml")
IBGE_CSV = os.path.join(BASE, "data", "ibge_regioes_imediatas_sp.csv")


def normalizar_nome(s) -> str:
    """Nome comparável: sem acento, sem caixa, sem espaço duplo."""
    return _norm(s)


def carregar_ibge_sp(caminho: str | None = None) -> dict[str, dict]:
    """{nome normalizado: registro} da tabela do IBGE. {} se o CSV faltar."""
    import csv
    try:
        with open(caminho or IBGE_CSV, encoding="utf-8-sig") as f:
            return indexar_por_municipio(list(csv.DictReader(f)))
    except (OSError, ValueError):
        return {}


def carregar_municipios(caminho: str | None = None, validar: bool = True) -> list[dict]:
    """Os municípios do painel: [{nome, cod_ibge, regiao_imediata, grupo}].

    `grupo` é opcional no TOML (o painel só usa para rotular); ausente vira "".
    `validar=True` confere cada cod_ibge contra o IBGE e levanta ValueError
    nomeando o município quando não bate.
    """
    with open(caminho or CONFIG, "rb") as f:
        cfg = tomllib.load(f)

    # aceita o formato plano [[municipios]] e também [[grupos]] com aninhados,
    # para não quebrar se alguém voltar a agrupar por peso mais tarde.
    brutos = list(cfg.get("municipios") or [])
    for grupo in cfg.get("grupos", []) or []:
        for m in grupo.get("municipios", []) or []:
            brutos.append({**m, "grupo": grupo.get("nome", "")})

    muns, vistos = [], set()
    for m in brutos:
        nome = str(m.get("nome", "")).strip()
        cod = str(m.get("cod_ibge", "")).strip()
        if not nome or not cod:
            raise ValueError(f"município sem nome ou cod_ibge no TOML: {m!r}")
        if cod in vistos:
            raise ValueError(f"cod_ibge duplicado no TOML: {cod} ({nome})")
        vistos.add(cod)
        muns.append({
            "nome": nome, "cod_ibge": cod, "grupo": str(m.get("grupo", "") or ""),
            "regiao_imediata": str(m.get("regiao_imediata_nome")
                                   or m.get("regiao_imediata") or "").strip(),
        })

    if validar:
        ibge = carregar_ibge_sp()
        if ibge:   # sem o CSV não dá para validar; não inventa validação
            for m in muns:
                linha = ibge.get(normalizar_nome(m["nome"]))
                if linha is None:
                    raise ValueError(
                        f"'{m['nome']}' não existe na base do IBGE de SP — "
                        "corrija o nome em config/pfc_prefeituras.toml")
                if str(linha["cod_ibge"]).strip() != m["cod_ibge"]:
                    raise ValueError(
                        f"cod_ibge errado para '{m['nome']}': TOML diz "
                        f"{m['cod_ibge']}, IBGE diz {linha['cod_ibge']}")
    return muns


def municipios_da_regiao(regiao: str) -> list[dict]:
    """Vizinhos: municípios de SP na mesma região imediata (Passo 9/expansão)."""
    alvo = normalizar_nome(regiao)
    return [{"nome": r["municipio"], "cod_ibge": r["cod_ibge"],
             "regiao_imediata": r["regiao_imediata_nome"]}
            for r in carregar_ibge_sp().values()
            if normalizar_nome(r["regiao_imediata_nome"]) == alvo]
