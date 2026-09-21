"""Leitura do CSV de MDE gerado por `python -m src.prefeituras`.

Separado do construtor de propósito: o app importa SÓ isto (leitura pura de
arquivo), nunca o módulo que fala com a API.
"""
from __future__ import annotations

import csv
import os

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR_DADOS = os.path.join(BASE, "data", "prefeituras")


def carregar(exercicio: int) -> dict[str, dict]:
    """{cod_ibge: {percentual, valor_aplicado, receita_base, exercicio, periodo}}.

    Loader GRACIOSO: arquivo ausente -> {} (tudo vira "sem dado" no painel).
    """
    caminho = os.path.join(DIR_DADOS, f"mde_{exercicio}.csv")
    if not os.path.isfile(caminho):
        return {}
    try:
        with open(caminho, encoding="utf-8-sig") as f:
            linhas = list(csv.DictReader(f))
    except OSError:
        return {}

    def num(v):
        try:
            return float(str(v).replace(",", ".")) if str(v).strip() else None
        except ValueError:
            return None

    saida = {}
    for linha in linhas:
        b = {str(k).strip().lower(): (v or "").strip() for k, v in linha.items()}
        cod, pct = b.get("cod_ibge", ""), num(b.get("percentual"))
        if not cod or pct is None:
            continue           # linha sem percentual não vira 0: é ausência
        saida[cod] = {"percentual": pct, "valor_aplicado": num(b.get("valor_aplicado")),
                      "receita_base": num(b.get("receita_base")),
                      "exercicio": int(b.get("exercicio") or exercicio),
                      "periodo": b.get("periodo") or "", "origem": b.get("origem", "")}
    return saida


def exercicio_disponivel(preferido: int | None = None) -> int | None:
    """O exercício mais recente com CSV no disco (ou o preferido, se existir)."""
    if not os.path.isdir(DIR_DADOS):
        return None
    anos = []
    for nome in os.listdir(DIR_DADOS):
        if nome.startswith("mde_") and nome.endswith(".csv"):
            try:
                anos.append(int(nome[4:-4]))
            except ValueError:
                continue
    if preferido and preferido in anos:
        return preferido
    return max(anos) if anos else None
