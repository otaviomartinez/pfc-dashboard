"""
Camada 2 — extrator genérico + utilitários de rede/texto compartilhados.

extrair_generico(url) tenta descobrir "itens de lista" (editais, notícias) em
qualquer página, por heurística de BeautifulSoup. É best-effort: pode devolver
poucos ou nenhum item em sites fora do padrão — isso é esperado.
"""
from __future__ import annotations

import datetime
import os
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# User-Agent de navegador real (alguns sites bloqueiam clientes sem isso).
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}
TIMEOUT = int(os.environ.get("RADAR_TIMEOUT", "15"))

# Textos de navegação/rodapé que nunca são oportunidades.
_STOP = {"home", "início", "inicio", "menu", "contato", "sobre", "login", "entrar",
         "buscar", "voltar", "leia mais", "saiba mais", "ver mais", "veja mais",
         "todos", "próximo", "anterior", "compartilhar", "newsletter", "cookies"}


def hoje() -> str:
    return datetime.date.today().isoformat()


def pegar_soup(url: str, timeout: int = TIMEOUT):
    """Baixa a URL e devolve um BeautifulSoup, ou None em qualquer falha."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code != 200 or not r.text:
            return None
        return BeautifulSoup(r.text, "html.parser")
    except Exception:
        return None


def limpar_texto(s) -> str:
    """Normaliza espaços em branco de um texto extraído."""
    return re.sub(r"\s+", " ", (s or "")).strip()


def dominio_de(url: str) -> str:
    """Domínio 'registrável' aproximado (sem www)."""
    try:
        net = urlparse(url).netloc.lower()
        return net[4:] if net.startswith("www.") else net
    except Exception:
        return ""


def montar_item(titulo, descricao, url, fonte, prazo="", valor="") -> dict:
    """Item padronizado do radar (nunca inventa prazo/valor)."""
    return {
        "titulo": limpar_texto(titulo)[:300],
        "descricao": limpar_texto(descricao)[:600],
        "url": (url or "").strip(),
        "fonte": fonte,
        "data_encontrada": hoje(),
        "prazo": limpar_texto(prazo),
        "valor_estimado": limpar_texto(valor),
    }


def _link_valido(a) -> bool:
    href = (a.get("href") or "").strip()
    if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
        return False
    return True


def _titulo_do_bloco(bloco, link) -> str:
    """Título: heading dentro do bloco, senão o texto do próprio link."""
    if bloco is not None and getattr(bloco, "name", None) != "a":
        h = bloco.find(["h1", "h2", "h3", "h4"])
        if h and limpar_texto(h.get_text()):
            return limpar_texto(h.get_text())
    return limpar_texto(link.get_text())


def _descricao_do_bloco(bloco, titulo) -> str:
    if bloco is None or getattr(bloco, "name", None) == "a":
        return ""
    texto = limpar_texto(bloco.get_text(" "))
    if texto.startswith(titulo):
        texto = texto[len(titulo):].strip(" -–—·|")
    return texto


# Seletores comuns em sites institucionais (WordPress, Drupal, Elementor…).
_SELETORES_GENERICOS = [
    "article", "li[class*=edital]", "div[class*=edital]", "div[class*=chamada]",
    "div[class*=card]", "div[class*=noticia]", "div[class*=post]",
    ".views-row", ".elementor-post", "li.item", "div.item",
]


def coletar_blocos(soup, seletores) -> list:
    """Primeiro conjunto de blocos não-vazio entre os seletores fornecidos."""
    for sel in seletores:
        try:
            blocos = soup.select(sel)
        except Exception:
            blocos = []
        if len(blocos) >= 2:
            return blocos
    return []


def extrair_de_soup(soup, base_url, fonte, seletores=None, limite=30,
                    permitir_fallback=True) -> list[dict]:
    """Núcleo de extração reaproveitado pela Camada 1 e pela Camada 2.

    permitir_fallback=False (Camada 1) mantém a extração conservadora: se os
    seletores dedicados não casarem, devolve [] em vez de varrer todos os links.
    """
    if soup is None:
        return []
    seletores = seletores or _SELETORES_GENERICOS
    blocos = coletar_blocos(soup, seletores)
    itens, vistos = [], set()

    if not blocos and not permitir_fallback:
        return []
    origem = blocos if blocos else soup.find_all("a", href=True)
    for bloco in origem:
        link = bloco if getattr(bloco, "name", None) == "a" else bloco.find("a", href=True)
        if link is None or not _link_valido(link):
            continue
        titulo = _titulo_do_bloco(bloco, link)
        if not titulo or len(titulo) < 15 or titulo.lower() in _STOP:
            continue
        url = urljoin(base_url, link.get("href").strip())
        if not url.startswith("http") or url in vistos:
            continue
        vistos.add(url)
        desc = _descricao_do_bloco(bloco, titulo)
        itens.append(montar_item(titulo, desc, url, fonte))
        if len(itens) >= limite:
            break
    return itens


def extrair_generico(url: str) -> list[dict]:
    """Camada 2 — extração best-effort de uma URL arbitrária."""
    try:
        soup = pegar_soup(url)
        if soup is None:
            return []
        fonte = f"generico:{dominio_de(url)}"
        return extrair_de_soup(soup, url, fonte)
    except Exception:
        return []
