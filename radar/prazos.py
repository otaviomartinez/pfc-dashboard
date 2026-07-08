"""
Extração conservadora de data-limite (prazo de inscrição) em textos pt-BR.

extrair_prazo(texto, url="") -> "AAAA-MM-DD" ou None.
Só reconhece datas ancoradas em um gatilho de prazo ("inscrições até",
"prazo:", "encerra em", "submissão até"…) — uma data solta pode ser data de
publicação, então é ignorada. Nunca inventa: ambíguo/invalido devolve None.
"""
from __future__ import annotations

import datetime
import re
import unicodedata

_MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11,
    "dezembro": 12,
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}

# Palavras que ancoram uma data como PRAZO (não data de publicação).
_GATILHOS = (
    "inscricao", "inscricoes", "submissao", "submissoes", "candidatura",
    "candidaturas", "prazo", "encerra", "encerram", "encerramento",
    "deadline", "data limite", "data-limite", "termina", "terminam", "ate",
)

# gatilho -> até 30 chars sem dígito -> data por extenso OU numérica
_RE_PRAZO = re.compile(
    r"\b(?:" + "|".join(_GATILHOS) + r")\b"
    r"[^0-9]{0,30}?"
    r"(?:"
    r"(\d{1,2})\s*(?:o|º)?\s*(?:de\s+)?([a-z]{3,9})\.?(?:\s+de\s+(\d{4}))?"  # 16 de março [de 2026]
    r"|(\d{1,2})[/\-.](\d{1,2})(?:[/\-.](\d{2,4}))?"                          # 16/03[/2026]
    r")"
)


def _norm(s: str) -> str:
    """minúsculas, sem acentos, espaços colapsados — casamento robusto."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower())


def _montar_data(dia: int, mes: int, ano: int | None, hoje: datetime.date):
    """Valida a data; sem ano, assume o próximo ano em que ela ainda é futura."""
    if ano is not None and ano < 100:
        ano += 2000
    if ano is not None:
        try:
            return datetime.date(ano, mes, dia)
        except ValueError:
            return None
    try:
        d = datetime.date(hoje.year, mes, dia)
    except ValueError:
        return None
    return d if d >= hoje else datetime.date(hoje.year + 1, mes, dia)


def extrair_prazo(texto: str, url: str = "") -> str | None:
    """Data-limite em ISO (AAAA-MM-DD) achada no texto, ou None."""
    t = _norm(texto)[:30000]
    if not t:
        return None
    hoje = datetime.date.today()
    for m in _RE_PRAZO.finditer(t):
        if m.group(1):                       # data por extenso
            mes = _MESES.get(m.group(2))
            if mes is None:                  # "12 meses", "10 cidades"… não é data
                continue
            data = _montar_data(int(m.group(1)), mes,
                                int(m.group(3)) if m.group(3) else None, hoje)
        else:                                # data numérica DD/MM[/AAAA]
            dia, mes = int(m.group(4)), int(m.group(5))
            if not (1 <= mes <= 12):
                continue
            data = _montar_data(dia, mes,
                                int(m.group(6)) if m.group(6) else None, hoje)
        if data is not None:
            return data.isoformat()
    return None


def dias_restantes(prazo_iso: str) -> int | None:
    """(prazo - hoje) em dias; None se o ISO for inválido/vazio."""
    try:
        prazo = datetime.date.fromisoformat(str(prazo_iso or "").strip())
    except ValueError:
        return None
    return (prazo - datetime.date.today()).days
