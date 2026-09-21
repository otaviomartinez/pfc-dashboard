"""Config dos municípios do painel Prefeituras (config/pfc_prefeituras.toml).

Por que existe um validador: o plano proíbe chutar código IBGE. O TOML já traz
`cod_ibge` resolvido, mas um código errado digitado à mão passaria despercebido e
contaminaria TODAS as consultas (o SICONFI responderia vazio em silêncio — o pior
tipo de bug deste projeto). Então todo carregamento RECONFERE cada código contra
data/ibge_regioes_imediatas_sp.csv e derruba com erro nomeando o município.
"""
from __future__ import annotations

import csv
import os
import tomllib
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG = os.path.join(BASE, "config", "pfc_prefeituras.toml")
IBGE_CSV = os.path.join(BASE, "data", "ibge_regioes_imediatas_sp.csv")


def normalizar_nome(s) -> str:
    """Nome comparável: sem acento, sem caixa, sem espaço duplo."""
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.split()).lower()


def carregar_ibge_sp(caminho: str | None = None) -> dict[str, dict]:
    """{nome normalizado: linha} dos municípios de SP (IBGE 2017, já no repo)."""
    caminho = caminho or IBGE_CSV
    try:
        with open(caminho, encoding="utf-8-sig") as f:
            return {normalizar_nome(r["municipio"]): r for r in csv.DictReader(f)}
    except (OSError, KeyError):
        return {}


def carregar_municipios(caminho: str | None = None, validar: bool = True) -> list[dict]:
    """Os municípios do painel: [{nome, cod_ibge, regiao_imediata, grupo}].

    `validar=True` (padrão) confere cada cod_ibge contra o CSV do IBGE. Levanta
    ValueError nomeando o município quando o código não bate ou o município não
    existe em SP — falha barulhenta de propósito (ver docstring do módulo).
    """
    caminho = caminho or CONFIG
    with open(caminho, "rb") as f:
        cfg = tomllib.load(f)

    muns, vistos = [], set()
    for grupo in cfg.get("grupos", []):
        for m in grupo.get("municipios", []):
            nome, cod = str(m.get("nome", "")).strip(), str(m.get("cod_ibge", "")).strip()
            if not nome or not cod:
                raise ValueError(f"município sem nome ou cod_ibge no TOML: {m!r}")
            if cod in vistos:
                raise ValueError(f"cod_ibge duplicado no TOML: {cod} ({nome})")
            vistos.add(cod)
            muns.append({"nome": nome, "cod_ibge": cod, "grupo": grupo.get("nome", ""),
                         "regiao_imediata": str(m.get("regiao_imediata", "")).strip()})

    if validar:
        ibge = carregar_ibge_sp()
        if ibge:  # sem o CSV não dá para validar; não inventa validação
            for m in muns:
                linha = ibge.get(normalizar_nome(m["nome"]))
                if linha is None:
                    raise ValueError(
                        f"'{m['nome']}' não existe na base do IBGE de SP — "
                        "corrija o nome em config/pfc_prefeituras.toml")
                if str(linha["id_municipio"]).strip() != m["cod_ibge"]:
                    raise ValueError(
                        f"cod_ibge errado para '{m['nome']}': TOML diz {m['cod_ibge']}, "
                        f"IBGE diz {linha['id_municipio']}")
    return muns


def municipios_da_regiao(regiao: str) -> list[dict]:
    """Vizinhos: municípios de SP na mesma região imediata (para o Passo 9/expansão)."""
    alvo = normalizar_nome(regiao)
    return [{"nome": r["municipio"], "cod_ibge": r["id_municipio"],
             "regiao_imediata": r["regiao_imediata_nome"]}
            for r in carregar_ibge_sp().values()
            if normalizar_nome(r["regiao_imediata_nome"]) == alvo]
