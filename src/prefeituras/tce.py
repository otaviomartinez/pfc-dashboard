"""Índice de aplicação no ensino apurado pelo TCE-SP (AUDESP).

FONTE MELHOR QUE O SICONFI, por dois motivos:
  1. O SICONFI simplesmente NÃO publica o RREO-Anexo 08 (MDE) para os nossos
     municípios — varremos 2023-2025 x períodos 1-6 e não há nada.
  2. Este índice é APURADO PELO TRIBUNAL, não apenas declarado pela prefeitura.
     Para a regra 5(a) do CLAUDE.md, é a versão forte: "julgado", não
     "declarado (não julgado)".

Arquivo: data/tce_sp/resultado_analises_audesp.csv — baixado do portal de dados
abertos do TCE-SP (Conjunto de Dados -> "Resultado das Análises Audesp (LRF,
Ensino, Saúde)"). Cobre 2016-2025 e os 644 municípios de SP. É latin-1, com ';'
e decimal por vírgula.

ATENÇÃO ao formato: a coluna "Despesa Empenhada Ensino (%)" vem como FRAÇÃO
(0,2736 = 27,36%). Multiplicar por 100 — esquecer disso mostraria "0,27%" e
faria o painel acusar todo mundo de descumprir a Constituição.
"""
from __future__ import annotations

import csv
import os

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_TCE = os.path.join(BASE, "data", "tce_sp", "resultado_analises_audesp.csv")

COL_ANO = "Exercício"
COL_IBGE = "Código IBGE"
COL_PCT = "Despesa Empenhada Ensino (%)"
COL_VALOR = "Despesa Empenhada Ensino"


def _num(v):
    """'0,2736' -> 0.2736. None quando não dá."""
    t = str(v or "").strip().replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def carregar(exercicio: int, caminho: str | None = None) -> dict[str, dict]:
    """{cod_ibge: {percentual, valor_aplicado, exercicio, origem}} de um ano.

    Loader GRACIOSO: arquivo ausente/ilegível -> {}. Linha sem percentual é
    DESCARTADA (não vira 0 — ausência é ausência).
    """
    caminho = caminho or CSV_TCE
    if not os.path.isfile(caminho):
        return {}
    try:
        with open(caminho, encoding="latin-1", newline="") as f:
            linhas = list(csv.DictReader(f, delimiter=";"))
    except OSError:
        return {}

    saida: dict[str, dict] = {}
    for linha in linhas:
        if str(linha.get(COL_ANO, "")).strip() != str(exercicio):
            continue
        cod = str(linha.get(COL_IBGE, "")).strip()
        fracao = _num(linha.get(COL_PCT))
        if not cod or fracao is None:
            continue
        saida[cod] = {
            "percentual": round(fracao * 100, 2),   # FRAÇÃO -> porcentagem
            "valor_aplicado": _num(linha.get(COL_VALOR)),
            "receita_base": None,   # o TCE não publica a base; não derivamos
            "exercicio": int(exercicio),
            "periodo": "",          # é o exercício fechado, não um bimestre
            "origem": "tce-sp",
        }
    return saida


def exercicios_disponiveis(caminho: str | None = None) -> list[int]:
    """Anos presentes no arquivo, do mais recente para o mais antigo."""
    caminho = caminho or CSV_TCE
    if not os.path.isfile(caminho):
        return []
    try:
        with open(caminho, encoding="latin-1", newline="") as f:
            anos = set()
            for linha in csv.DictReader(f, delimiter=";"):
                try:
                    anos.add(int(str(linha.get(COL_ANO, "")).strip()))
                except ValueError:
                    continue
        return sorted(anos, reverse=True)
    except OSError:
        return []
