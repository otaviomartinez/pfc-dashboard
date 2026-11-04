"""
Deduplicação — evita reenviar oportunidades já presentes na fila.

Compara por URL normalizada e por similaridade de título (difflib). Também
remove duplicatas dentro do próprio lote novo.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from urllib.parse import urlparse

# Palavras que não distinguem um edital de outro (e datas: "29 Set 2026").
_VAZIAS = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "para", "com",
    "por", "no", "na", "nos", "nas", "um", "uma", "via", "ao", "aos", "que", "sua",
    "seu", "abre", "lanca", "lancam", "recebe", "inscricoes", "edital", "jan", "fev",
    "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez",
}


def _norm_url(url: str) -> str:
    """URL sem esquema, sem www, sem barra final e sem query — para comparar."""
    try:
        p = urlparse((url or "").strip().lower())
        net = p.netloc[4:] if p.netloc.startswith("www.") else p.netloc
        return (net + p.path).rstrip("/")
    except Exception:
        return (url or "").strip().lower()


def _palavras(titulo: str) -> set:
    s = unicodedata.normalize("NFKD", str(titulo or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return {p for p in re.findall(r"[a-z0-9]+", s)
            if p not in _VAZIAS and not p.isdigit() and len(p) > 1}


def mesmo_edital(a: str, b: str, limiar_palavras: float = 0.6) -> bool:
    """O mesmo edital noticiado por duas fontes com títulos diferentes:
      "Zurich Seguros abre edital nacional para apoiar projetos sociais via leis
       de incentivo fiscal"  (ABCR)
      "Zurich Seguros abre edital para projetos sociais com incentivo fiscal
       29 Set 2026"           (Rede Filantropia)
    A comparação letra a letra (difflib) não pega; a de PALAVRAS em comum pega.
    Exige 4+ palavras em comum, para dois títulos curtos e genéricos não colarem."""
    pa, pb = _palavras(a), _palavras(b)
    if not pa or not pb:
        return False
    comum = pa & pb
    return len(comum) >= 4 and len(comum) / len(pa | pb) >= limiar_palavras


def _parecido(titulo: str, titulos_existentes, limiar: float) -> bool:
    t = (titulo or "").lower()
    for outro in titulos_existentes:
        if difflib.SequenceMatcher(None, t, (outro or "").lower()).ratio() >= limiar:
            return True
        if mesmo_edital(titulo, outro):
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
