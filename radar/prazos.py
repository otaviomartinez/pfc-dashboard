"""
Extração de data-limite (prazo de inscrição) em textos pt-BR — v2.

extrair_prazo(texto, url="", pub=None) -> "AAAA-MM-DD" ou None.

Três camadas de defesa (a sondagem mostrou por que cada uma importa):
  1. ÂNCORAS EM CAMADAS: só reconhece a data colada a uma âncora FORTE de prazo
     ("prazo de inscrição", "inscrições até", "recebimento de propostas",
     "candidaturas até", "data limite"…). O "até" PURO foi DESCARTADO — era ele
     que pegava a data de execução errada ("recursos até 31 de dezembro") no
     Somando Impactos, em vez do prazo de inscrição real.
  2. ANO com trava de metadado: se a data por extenso não traz o ano, o ano é
     inferido da DATA DE PUBLICAÇÃO (radar/publicacao.py), que só existe quando
     veio de metadado estruturado. Sem ano e sem publicação confiável -> None
     ("a confirmar"). NUNCA se chuta o ano.
  3. Sanidade: prazo que resolve para o passado distante (>120 dias) é descartado
     (pega inferência que caiu num ano velho). Combina com _prazo_confiavel do app.
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

# ÂNCORAS EM CAMADAS (normalizadas, sem acento). Cada uma leva um contexto de
# prazo/inscrição/proposta — o "ate" PURO ficou de fora de propósito.
#   prioridade 0 = prazo de inscrição/candidatura/proposta (o mais confiável)
#   prioridade 1 = genéricas fortes (podem ser um limite secundário, ex.: de
#                  impugnação); só vencem se nenhuma de prioridade 0 aparecer antes.
_ANCORAS = [
    # --- prioridade 0 -------------------------------------------------------
    ("prazo de inscricao", 0), ("prazo de inscricoes", 0), ("prazo das inscricoes", 0),
    ("prazo de submissao", 0),
    ("inscricoes abertas ate o dia", 0), ("inscricoes estao abertas ate o dia", 0),
    ("inscricoes abertas ate", 0), ("inscricoes estao abertas ate", 0),
    ("inscricoes ate o dia", 0), ("inscricoes ate", 0), ("inscricao ate", 0),
    ("inscricoes vao ate", 0), ("inscricoes seguem ate", 0),
    ("inscricoes encerram", 0), ("encerramento das inscricoes", 0),
    ("candidaturas ate", 0), ("candidatura ate", 0),
    ("recebimento de propostas", 0), ("recebimento das propostas", 0),
    ("recebimento de projetos", 0), ("recebimento de inscricoes", 0),
    ("propostas ate", 0), ("submissao ate", 0), ("submissoes ate", 0),
    ("submeter propostas ate", 0), ("prazo termina", 0),
    # --- prioridade 1 -------------------------------------------------------
    ("data limite", 1), ("data-limite", 1), ("prazo final", 1),
]

# data por extenso ("3 de agosto [de 2026]") OU numérica ("03/08[/2026]")
_D_EXT = r"(\d{1,2})\s*(?:o|º)?\s*(?:de\s+)?([a-z]{3,9})\.?(?:\s+de\s+(\d{4}))?"
_D_NUM = r"(\d{1,2})[/\-.](\d{1,2})(?:[/\-.](\d{2,4}))?"
# âncora -> até 40 chars sem dígito -> data
_RE_ANCORAS = [
    (re.compile(re.escape(anc) + r"[^0-9]{0,40}?(?:" + _D_EXT + r"|" + _D_NUM + r")"), pri)
    for anc, pri in _ANCORAS
]


def _norm(s: str) -> str:
    """minúsculas, sem acentos, espaços colapsados — casamento robusto."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower())


def _candidatos(texto_norm: str):
    """Todas as datas ancoradas, como (prioridade, posição, dia, mes, ano|None),
    ordenadas por (prioridade, posição) — a mais confiável e mais ao início primeiro."""
    achados = []
    for rx, pri in _RE_ANCORAS:
        for m in rx.finditer(texto_norm):
            if m.group(1):  # por extenso
                mes = _MESES.get(m.group(2))
                if mes is None:  # "12 meses", "10 cidades"… não é data
                    continue
                dia = int(m.group(1))
                ano = int(m.group(3)) if m.group(3) else None
            else:            # numérica DD/MM[/AAAA]
                dia, mes = int(m.group(4)), int(m.group(5))
                if not (1 <= mes <= 12):
                    continue
                ano = int(m.group(6)) if m.group(6) else None
            if not (1 <= dia <= 31):
                continue
            achados.append((pri, m.start(), dia, mes, ano))
    achados.sort(key=lambda c: (c[0], c[1]))
    return achados


def _resolver_data(dia: int, mes: int, ano: int | None,
                   pub: datetime.date | None) -> datetime.date | None:
    """Ano explícito vence. Sem ano, ancora na PUBLICAÇÃO (só de metadado):
    menor ano em que a data é >= publicação. Sem ano e sem pub -> None."""
    if ano is not None:
        if ano < 100:
            ano += 2000
        try:
            return datetime.date(ano, mes, dia)
        except ValueError:
            return None
    if pub is None:
        return None  # sem ano e sem publicação confiável -> "a confirmar"
    for y in (pub.year, pub.year + 1):
        try:
            d = datetime.date(y, mes, dia)
        except ValueError:
            return None
        if d >= pub:
            return d
    return None


def extrair_prazo(texto: str, url: str = "",
                  pub: datetime.date | None = None) -> str | None:
    """Data-limite em ISO (AAAA-MM-DD) achada no texto, ou None.

    `pub` = data de publicação da página (radar/publicacao.data_publicacao),
    usada só para inferir o ano quando o prazo vem sem ano. Percorre os
    candidatos por confiança e devolve o primeiro que resolve para uma data
    válida e não vencida-há-muito.
    """
    t = _norm(texto)[:30000]
    if not t:
        return None
    hoje = datetime.date.today()
    for _pri, _pos, dia, mes, ano in _candidatos(t):
        data = _resolver_data(dia, mes, ano, pub)
        if data is None:
            continue
        # 3ª linha: prazo vencido há muito (>120 dias) é fantasma/ano velho.
        if (data - hoje).days < -120:
            continue
        return data.isoformat()
    return None


def dias_restantes(prazo_iso: str) -> int | None:
    """(prazo - hoje) em dias; None se o ISO for inválido/vazio."""
    try:
        prazo = datetime.date.fromisoformat(str(prazo_iso or "").strip())
    except ValueError:
        return None
    return (prazo - datetime.date.today()).days
