"""Dependência de FPM por município (gerado por scripts/importar_fpm.py).

Lê data/prefeituras/fpm_<ano>.csv. Sem arquivo -> {} e o painel mostra
"sem dado" — que é resposta legítima, não erro (regra 5c do CLAUDE.md).
"""
from __future__ import annotations

import csv
import glob
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR_DADOS = os.path.join(BASE, "data", "prefeituras")


def exercicios_disponiveis(diretorio: str | None = None) -> list[int]:
    """Anos com arquivo de FPM, do mais recente para o mais antigo."""
    diretorio = diretorio or DIR_DADOS
    anos = []
    for caminho in glob.glob(os.path.join(diretorio, "fpm_*.csv")):
        m = re.search(r"fpm_(\d{4})\.csv$", os.path.basename(caminho))
        if m:
            anos.append(int(m.group(1)))
    return sorted(anos, reverse=True)


def carregar(exercicio: int | None = None, diretorio: str | None = None) -> dict[str, dict]:
    """{cod_ibge: {dependencia_pct, fpm, receitas_correntes, exercicio}}.

    `exercicio=None` pega o ano mais recente disponível. Linha sem percentual é
    descartada (ausência é ausência, nunca 0).
    """
    diretorio = diretorio or DIR_DADOS
    if exercicio is None:
        anos = exercicios_disponiveis(diretorio)
        if not anos:
            return {}
        exercicio = anos[0]
    caminho = os.path.join(diretorio, f"fpm_{exercicio}.csv")
    if not os.path.isfile(caminho):
        return {}
    try:
        with open(caminho, encoding="utf-8-sig", newline="") as f:
            linhas = list(csv.DictReader(f))
    except OSError:
        return {}
    saida = {}
    for linha in linhas:
        cod = str(linha.get("cod_ibge", "")).strip()
        try:
            pct = float(str(linha.get("dependencia_pct", "")).strip())
        except ValueError:
            continue
        if not cod:
            continue
        saida[cod] = {
            "dependencia_pct": pct,
            "fpm": linha.get("fpm", ""),
            "receitas_correntes": linha.get("receitas_correntes", ""),
            "exercicio": int(exercicio),
            "origem": linha.get("origem", "siconfi-dca"),
        }
    return saida
