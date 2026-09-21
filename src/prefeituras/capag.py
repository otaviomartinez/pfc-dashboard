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

# O Tesouro publica gradações (A+, B+, C-...) além das letras puras. Aceitar só
# "A/B/C/D" jogava fora nota REAL: Cesário Lange ('B+') e Juquiá ('A+') caíam
# como "não avaliado". 'N.D.' (não disponível) continua sendo ausência.
NOTAS_VALIDAS = ("A", "B", "C", "D")


def normalizar_nota(nota) -> str:
    """'a+' -> 'A+'. Devolve "" quando não é nota da escala CAPAG."""
    n = str(nota or "").strip().upper().replace(" ", "")
    if not n or n[0] not in NOTAS_VALIDAS:
        return ""
    if len(n) == 1:
        return n
    return n if (len(n) == 2 and n[1] in "+-") else ""
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
        nota = normalizar_nota(baixo.get("nota", ""))
        saida[cod] = {
            "nota": nota,                     # "" = fora da escala = sem nota
            "endividamento": baixo.get("endividamento", ""),
            "poupanca": baixo.get("poupanca", ""),
            "liquidez": baixo.get("liquidez", ""),
            "exercicio": exercicio,
        }
    return saida


def rotulo_nota(nota) -> str:
    """Rótulo de exibição (mantém a gradação: 'A+'). Sem nota -> 'não avaliado'."""
    return normalizar_nota(nota) or ROTULO_SEM_NOTA


def nota_saudavel(nota) -> bool | None:
    """True para A/B, False para C/D, None quando NÃO HÁ nota.

    O None é o ponto todo desta função: quem chama é obrigado a tratar
    "não avaliado" como terceiro estado, não como False.
    """
    n = normalizar_nota(nota)
    if not n:
        return None
    return n[0] in ("A", "B")      # a LETRA manda; o +/- é só gradação


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
