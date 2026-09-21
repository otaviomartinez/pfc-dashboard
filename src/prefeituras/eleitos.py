"""Prefeitos, vices e vereadores eleitos em 2024 (mandato 2025-2028).

Fonte: dados abertos do TSE (consulta_cand_2024_SP.zip). Baixado e filtrado UMA
VEZ por scripts/importar_eleitos_tse.py -> data/prefeituras/eleitos_2024.csv.
Nada de rede em runtime (a API DivulgaCandContas não tem doc oficial nem CORS).

REGRA: partido é campo FACTUAL do TSE. Zero editorial político — sem adjetivo,
sem juízo, sem ranking por partido.
"""
from __future__ import annotations

import csv
import os

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_ELEITOS = os.path.join(BASE, "data", "prefeituras", "eleitos_2024.csv")

CARGOS = ("PREFEITO", "VICE-PREFEITO", "VEREADOR")


def carregar(caminho: str | None = None) -> list[dict]:
    """[{municipio, cargo, nome_urna, nome, partido}]. Loader GRACIOSO: [] se faltar."""
    caminho = caminho or CSV_ELEITOS
    if not os.path.isfile(caminho):
        return []
    try:
        with open(caminho, encoding="utf-8-sig") as f:
            linhas = list(csv.DictReader(f))
    except OSError:
        return []
    saida = []
    for linha in linhas:
        b = {str(k).strip().lower(): (v or "").strip() for k, v in linha.items()}
        if not b.get("municipio"):
            continue
        saida.append({"municipio": b.get("municipio", ""),
                      "cargo": b.get("cargo", "").upper(),
                      "nome_urna": b.get("nome_urna", ""),
                      "nome": b.get("nome", ""),
                      "partido": b.get("partido", "").upper()})
    return saida


def por_municipio(municipio: str, eleitos: list[dict] | None = None) -> list[dict]:
    """Eleitos de um município, prefeito primeiro, depois vice, depois vereadores."""
    from src.prefeituras.config import normalizar_nome
    alvo = normalizar_nome(municipio)
    ordem = {"PREFEITO": 0, "VICE-PREFEITO": 1, "VEREADOR": 2}
    achados = [e for e in (eleitos if eleitos is not None else carregar())
               if normalizar_nome(e["municipio"]) == alvo]
    return sorted(achados, key=lambda e: (ordem.get(e["cargo"], 9), e["nome_urna"]))


def prefeito_de(municipio: str, eleitos: list[dict] | None = None) -> dict | None:
    """O prefeito do município, ou None se o CSV não estiver disponível."""
    for e in por_municipio(municipio, eleitos):
        if e["cargo"] == "PREFEITO":
            return e
    return None


def partidos_do_municipio(municipio: str, eleitos: list[dict] | None = None) -> set[str]:
    """Conjunto de siglas presentes no município (base da ponte partidária)."""
    return {e["partido"] for e in por_municipio(municipio, eleitos) if e["partido"]}
