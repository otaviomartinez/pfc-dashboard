"""CAPAG (Capacidade de Pagamento, Tesouro Nacional) — leitura do CSV cacheado.

Fonte: dataset CKAN `capag-municipios` do Tesouro Transparente (XLSX anual).
Baixado UMA VEZ, recortado para os municípios que interessam e versionado como
data/prefeituras/capag_<ano>.csv. Nada de rede em runtime.

REGRA QUE NÃO PODE SER QUEBRADA: **ausência de nota não é nota ruim.** Município
que não homologou a DCA fica SEM nota no CAPAG. Isso vira o rótulo próprio
"não avaliado" — nunca é tratado como C/D nem como risco.

Notas: A (boa), B (razoável), C (fraca), D (crítica), a partir de três
indicadores — endividamento, poupança corrente e liquidez.
"""
from __future__ import annotations

import csv
import os

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR_DADOS = os.path.join(BASE, "data", "prefeituras")

NOTAS_VALIDAS = ("A", "B", "C", "D")
ROTULO_SEM_NOTA = "não avaliado"


def caminho_csv(exercicio: int) -> str:
    return os.path.join(DIR_DADOS, f"capag_{exercicio}.csv")


def carregar(exercicio: int) -> dict[str, dict]:
    """{cod_ibge: {nota, endividamento, poupanca, liquidez, exercicio}}.

    Loader GRACIOSO: arquivo ausente/ilegível -> {} (o painel mostra "não
    avaliado"), nunca exceção. O app precisa abrir mesmo sem esse dado.
    """
    caminho = caminho_csv(exercicio)
    if not os.path.isfile(caminho):
        return {}
    try:
        with open(caminho, encoding="utf-8-sig") as f:
            linhas = list(csv.DictReader(f))
    except OSError:
        return {}

    saida: dict[str, dict] = {}
    for linha in linhas:
        baixo = {str(k).strip().lower(): (v or "").strip() for k, v in linha.items()}
        cod = baixo.get("cod_ibge", "")
        if not cod:
            continue
        nota = baixo.get("nota", "").upper()
        saida[cod] = {
            "nota": nota if nota in NOTAS_VALIDAS else "",   # fora da escala = sem nota
            "endividamento": baixo.get("endividamento", ""),
            "poupanca": baixo.get("poupanca", ""),
            "liquidez": baixo.get("liquidez", ""),
            "exercicio": exercicio,
        }
    return saida


def rotulo_nota(nota) -> str:
    """Rótulo de exibição. Sem nota -> 'não avaliado' (nunca 'ruim')."""
    n = str(nota or "").strip().upper()
    return n if n in NOTAS_VALIDAS else ROTULO_SEM_NOTA


def nota_saudavel(nota) -> bool | None:
    """True para A/B, False para C/D, None quando NÃO HÁ nota.

    O None é o ponto todo desta função: quem chama é obrigado a tratar
    "não avaliado" como terceiro estado, não como False.
    """
    n = str(nota or "").strip().upper()
    if n in ("A", "B"):
        return True
    if n in ("C", "D"):
        return False
    return None


def exercicio_disponivel(preferido: int | None = None) -> int | None:
    """Exercício mais recente com capag_<ano>.csv no disco, ou None.

    Existe porque o CAPAG NÃO pode depender do MDE: os dois vêm de fontes
    diferentes e um pode chegar sem o outro (foi o que aconteceu — CAPAG
    baixado, MDE indisponível, e o painel ignorava o CAPAG).
    """
    if not os.path.isdir(DIR_DADOS):
        return None
    anos = []
    for nome in os.listdir(DIR_DADOS):
        if nome.startswith("capag_") and nome.endswith(".csv"):
            try:
                anos.append(int(nome[6:-4]))
            except ValueError:
                continue
    if preferido and preferido in anos:
        return preferido
    return max(anos) if anos else None
