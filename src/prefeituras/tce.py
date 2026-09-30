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
# Fatores do método fiscal que o MESMO arquivo já traz (não precisa de rede):
COL_PESSOAL_PCT = "Despesa com Pessoal Poder Executivo (%)"
COL_RESULTADO_PCT = "Resultado da Execução Orçamentária (%)"


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


def carregar_fiscal(exercicio: int, caminho: str | None = None) -> dict[str, dict]:
    """{cod_ibge: {pessoal_pct, resultado_pct, exercicio}} — fatores fiscais do
    MESMO arquivo do TCE, apurados pelo Tribunal.

    Por que aqui e não no SICONFI: a sonda varreu o RGF (anexos 01/05/06,
    2023-2025, com e sem co_poder) e **não existe nada** para estes municípios —
    igualzinho ao Anexo 08 do MDE. O que o SP manda é para o AUDESP.

    DUAS ARMADILHAS, as duas conferidas no dado real:
      1. os dois percentuais vêm como FRAÇÃO (0,3888 = 38,88%) — x100, igual ao
         do ensino; sem isso o painel diria que ninguém gasta com pessoal;
      2. o exercício mais recente pode ter o ensino preenchido e o **pessoal
         VAZIO** (ainda não apurado). Campo vazio é `None`, nunca 0 — e o
         chamador é obrigado a mostrar de que exercício o número é (regra 5b/5e).

    `resultado_pct` é o Resultado da Execução Orçamentária (superávit/déficit).
    **Não é disponibilidade de caixa** (essa é o RGF-Anexo 05, que não existe
    para SP) — não rotular como caixa em lugar nenhum.
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
        if not cod:
            continue
        pessoal = _num(linha.get(COL_PESSOAL_PCT))
        resultado = _num(linha.get(COL_RESULTADO_PCT))
        if pessoal is None and resultado is None:
            continue                     # linha sem nenhum fator não serve
        saida[cod] = {
            "pessoal_pct": None if pessoal is None else round(pessoal * 100, 2),
            "resultado_pct": None if resultado is None else round(resultado * 100, 2),
            "exercicio": int(exercicio),
            "origem": "tce-sp",
        }
    return saida


def exercicio_com_pessoal(caminho: str | None = None) -> int | None:
    """Ano mais recente em que o pessoal está REALMENTE apurado.

    O ano corrente costuma ter ensino sem pessoal. Em vez de mostrar "sem dado"
    para todo mundo, procura o ano mais novo que tem o fator — e quem exibe é
    obrigado a dizer o ano (nunca fingir que é o exercício atual, regra 5e).
    """
    for ano in exercicios_disponiveis(caminho):
        reg = carregar_fiscal(ano, caminho)
        if any(r.get("pessoal_pct") is not None for r in reg.values()):
            return ano
    return None


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
