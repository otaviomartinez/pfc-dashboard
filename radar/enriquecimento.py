"""
Enriquecimento — visita a página do PRÓPRIO edital para melhorar a ficha.

A listagem costuma trazer título curto e descrição truncada; a página do
edital tem o parágrafo de abertura, o valor (R$ …) e a data-limite. Este
módulo busca esses três campos e só sobrescreve quando encontra algo MELHOR
(nunca apaga o que veio da listagem). Falha de rede nunca derruba o radar.

Custo controlado: enriquecer só quem vai para a fila (chamado pelo main.py
depois do filtro/dedup), no máximo MAX_ENRIQUECIMENTOS por rodada, maiores
scores primeiro, com pausa entre requests.
"""
from __future__ import annotations

import re
import time

import requests
from bs4 import BeautifulSoup

from radar import prazos
from radar.fontes_genericas import HEADERS, TIMEOUT, limpar_texto

MAX_ENRIQUECIMENTOS = 40
PAUSA_S = 0.4  # respiro entre requests para não parecer abuso

_RE_VALOR = re.compile(
    r"r\$\s?\d[\d\.\,]*(?:\s?(?:mil|milh(?:ao|ão|oes|ões)|mi\b))?", re.IGNORECASE)

# Tags que só carregam navegação/rodapé — fora do texto útil da página.
_TAGS_RUIDO = ["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]


def _primeiro_paragrafo(soup) -> str:
    """Primeiro <p> substancial (>120 chars) do conteúdo da página."""
    for p in soup.find_all("p"):
        txt = limpar_texto(p.get_text(" "))
        if len(txt) > 120:
            return txt
    return ""


def enriquecer(op: dict) -> dict:
    """Melhora descricao/valor_estimado/prazo a partir da página do edital.

    Devolve {"desc": bool, "valor": bool, "prazo": bool} indicando o que
    melhorou. Qualquer falha devolve tudo False, sem exceção propagada.
    """
    ganho = {"desc": False, "valor": False, "prazo": False}
    url = str(op.get("url", "")).strip()
    if not url.startswith("http"):
        return ganho
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200 or not r.text:
            return ganho
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(_TAGS_RUIDO):
            tag.decompose()

        # descrição: primeiro parágrafo substancial, se for mais rico
        par = _primeiro_paragrafo(soup)
        if par and len(par) > len(op.get("descricao", "")):
            op["descricao"] = par[:600]
            ganho["desc"] = True

        texto_pagina = limpar_texto(soup.get_text(" "))[:30000]

        # valor: só preenche se a listagem não trouxe nada
        if not str(op.get("valor_estimado", "")).strip():
            m = _RE_VALOR.search(texto_pagina)
            if m:
                op["valor_estimado"] = limpar_texto(m.group(0))
                ganho["valor"] = True

        # prazo: a página do edital costuma ter a data que a listagem omite
        if not isinstance(op.get("dias_restantes"), int):
            iso = prazos.extrair_prazo(texto_pagina, url)
            if iso:
                op["prazo"] = iso
                op["dias_restantes"] = prazos.dias_restantes(iso)
                ganho["prazo"] = True
    except Exception:
        pass
    return ganho


def enriquecer_lote(fila: list[dict], maximo: int = MAX_ENRIQUECIMENTOS,
                    pausa: float = PAUSA_S) -> dict:
    """Enriquece as `maximo` oportunidades de maior score da fila (já ordenada).

    Devolve contadores: {"tentadas", "enriquecidas", "com_prazo", "com_valor"}.
    """
    stats = {"tentadas": 0, "enriquecidas": 0, "com_prazo": 0, "com_valor": 0}
    for op in fila[:maximo]:
        stats["tentadas"] += 1
        g = enriquecer(op)
        if any(g.values()):
            stats["enriquecidas"] += 1
        if g["prazo"]:
            stats["com_prazo"] += 1
        if g["valor"]:
            stats["com_valor"] += 1
        time.sleep(pausa)
    return stats
