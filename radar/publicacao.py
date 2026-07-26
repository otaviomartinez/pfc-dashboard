"""
Data de PUBLICAÇÃO da página — mas só quando vem de METADADO estruturado.

Serve de âncora para inferir o ANO de um prazo escrito sem ano ("inscrições
até 3 de agosto"). A sondagem mostrou por que a trava de metadado é essencial:
a htmldate acha uma data em quase toda página, mas em sites sem metadado (o
captadores.org.br, fonte ABCR) ela chuta do texto/URL e devolve ano velho
(2021-2025). Usar esse palpite reintroduziria o bug do ano errado.

Regra: só devolve data quando a página tem JSON-LD `datePublished`,
`og:article:published_time` ou `<time datetime>`. Sem esse metadado -> None,
e o prazo fica "a confirmar" (nunca deduzir ano de palpite).
"""
from __future__ import annotations

import datetime

from bs4 import BeautifulSoup

try:  # htmldate é dependência do radar (radar/requirements.txt)
    from htmldate import find_date
    _HTMLDATE_OK = True
except Exception:  # pragma: no cover - ambiente sem a lib degrada para "sem data"
    _HTMLDATE_OK = False


def _tem_metadado_data(soup: BeautifulSoup) -> bool:
    """True se a página traz data de publicação ESTRUTURADA (não do corpo)."""
    # JSON-LD com datePublished
    for s in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if s.string and "datepublished" in s.string.lower():
            return True
    # OpenGraph / meta
    if soup.find("meta", attrs={"property": "article:published_time"}):
        return True
    if soup.find("meta", attrs={"name": "article:published_time"}):
        return True
    # <time datetime="...">
    if soup.find("time", attrs={"datetime": True}):
        return True
    return False


def data_publicacao(html: str) -> datetime.date | None:
    """Data de publicação (date) SÓ de metadado estruturado, ou None.

    Gate primeiro (metadado existe?); só então usa a htmldate como parser
    robusto. Sem metadado ou sem htmldate -> None (prazo fica "a confirmar").
    """
    if not html or not _HTMLDATE_OK:
        return None
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return None
    if not _tem_metadado_data(soup):
        return None  # captadores.org.br etc.: sem metadado -> não infere ano
    try:
        # extensive_search=False mantém a htmldate nas fontes confiáveis
        # (cabeçalho/metadado), sem vasculhar o texto do corpo.
        iso = find_date(html, original_date=True, extensive_search=False)
        return datetime.date.fromisoformat(iso) if iso else None
    except Exception:
        return None
