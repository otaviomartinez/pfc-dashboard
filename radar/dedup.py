"""
Deduplicação — evita reenviar oportunidades já presentes na fila.

Compara por URL normalizada e por similaridade de título (difflib). Também
remove duplicatas dentro do próprio lote novo.
"""
from __future__ import annotations

import difflib
from urllib.parse import urlparse


def _norm_url(url: str) -> str:
    """URL sem esquema, sem www, sem barra final e sem query — para comparar."""
    try:
        p = urlparse((url or "").strip().lower())
        net = p.netloc[4:] if p.netloc.startswith("www.") else p.netloc
        return (net + p.path).rstrip("/")
    except Exception:
        return (url or "").strip().lower()


def _parecido(titulo: str, titulos_existentes, limiar: float) -> bool:
    t = (titulo or "").lower()
    for outro in titulos_existentes:
        if difflib.SequenceMatcher(None, t, (outro or "").lower()).ratio() >= limiar:
            return True
    return False


def deduplicar(novas: list[dict], existentes: list[dict], limiar: float = 0.86):
    """Devolve (unicas, n_duplicatas). `existentes` = [{'titulo','url'}, ...]."""
    urls = {_norm_url(e.get("url", "")) for e in existentes if e.get("url")}
    titulos = [e.get("titulo", "") for e in existentes if e.get("titulo")]

    unicas, duplicatas = [], 0
    for op in novas:
        u = _norm_url(op.get("url", ""))
        if u and u in urls:
            duplicatas += 1
            continue
        if _parecido(op.get("titulo", ""), titulos, limiar):
            duplicatas += 1
            continue
        unicas.append(op)
        if u:
            urls.add(u)
        titulos.append(op.get("titulo", ""))
    return unicas, duplicatas
