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
# Obs.: li[class*=item] fica de fora de propósito (casa "menu-item"), e os li
# de card/post levam :not([class*=menu]) porque o WordPress usa classes como
# "menu-item-type-post_type" em navegação.
_SELETORES_GENERICOS = [
    "article", "li[class*=edital]", "div[class*=edital]", "div[class*=chamada]",
    "li[class*=chamada]", "div[class*=card]", "li[class*=card]:not([class*=menu])",
    "div[class*=noticia]", "li[class*=noticia]", "div[class*=post]",
    "li[class*=post]:not([class*=menu])", "div[class*=oportunidade]",
    "li[class*=oportunidade]", ".views-row", ".elementor-post",
    "li.item", "div.item", "h2 a[href]", "h3 a[href]",
]

_MAX_BLOCOS = 120  # teto de blocos agregados por página (evita páginas gigantes)


def coletar_blocos(soup, seletores, agregar: bool = False) -> list:
    """Blocos candidatos a item de listagem.

    agregar=False (Camada 1): devolve o PRIMEIRO conjunto não-vazio entre os
    seletores dedicados — comportamento conservador original.
    agregar=True (Camada 2): UNE os blocos de todos os seletores (sem repetir
    elemento), cobrindo layouts mistos; o ruído extra é barrado adiante pelo
    filtro de sinal do scorer.
    """
    if not agregar:
        for sel in seletores:
            try:
                blocos = soup.select(sel)
            except Exception:
                blocos = []
            if len(blocos) >= 2:
                return blocos
        return []
    achados, vistos = [], set()
    for sel in seletores:
        try:
            blocos = soup.select(sel)
        except Exception:
            blocos = []
        for b in blocos:
            if id(b) not in vistos:
                vistos.add(id(b))
                achados.append(b)
        if len(achados) >= _MAX_BLOCOS:
            break
    return achados if len(achados) >= 2 else []


def extrair_de_soup(soup, base_url, fonte, seletores=None, limite=30,
                    permitir_fallback=True) -> list[dict]:
    """Núcleo de extração reaproveitado pela Camada 1 e pela Camada 2.

    permitir_fallback=False (Camada 1) mantém a extração conservadora: se os
    seletores dedicados não casarem, devolve [] em vez de varrer todos os links.
    """
    if soup is None:
        return []
    seletores = seletores or _SELETORES_GENERICOS
    # Camada 2 (permitir_fallback=True) agrega blocos de TODOS os seletores;
    # Camada 1 mantém o primeiro-que-casar (extração dedicada conservadora).
    blocos = coletar_blocos(soup, seletores, agregar=permitir_fallback)
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


# --- Feed RSS / API do WordPress ---------------------------------------------
# Mais estável que raspar HTML: o feed não muda quando o site troca o visual (foi
# assim que 17 fontes "esvaziaram" — o seletor de HTML parou de casar). Cada item
# traz a DATA DE PUBLICAÇÃO estruturada, o que permite cortar post velho: um post
# de edital publicado há mais de MAX_IDADE_DIAS dias quase sempre já fechou.
MAX_IDADE_DIAS = 120


def _sem_html(s: str) -> str:
    texto = limpar_texto(BeautifulSoup(s or "", "html.parser").get_text(" "))
    return re.sub(r"\s+([.,;:!?])", r"\1", texto)   # "<b>R$ 200 mil</b>." sem espaço solto


def _data_rss(txt: str):
    """'Tue, 03 Nov 2026 10:00:00 +0000' ou ISO -> date; None se não der."""
    from email.utils import parsedate_to_datetime
    txt = (txt or "").strip()
    if not txt:
        return None
    try:
        return parsedate_to_datetime(txt).date()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.date.fromisoformat(txt[:10])
    except ValueError:
        return None


def _local(tag: str) -> str:
    """'{http://www.w3.org/2005/Atom}entry' -> 'entry'; 'content:encoded' -> 'encoded'."""
    return tag.rsplit("}", 1)[-1].rsplit(":", 1)[-1].lower()


def itens_de_feed(xml: str, fonte: str, limite: int = 30, hoje_=None) -> list[dict]:
    """PURA: itens de um feed RSS/Atom (leitor de XML de verdade — trata CDATA e
    os namespaces do Atom). Descarta post mais velho que MAX_IDADE_DIAS (com
    data); sem data, mantém (não dá para julgar). XML quebrado -> []."""
    import xml.etree.ElementTree as ET
    hoje_ = hoje_ or datetime.date.today()
    try:
        raiz = ET.fromstring((xml or "").strip().encode("utf-8"))
    except ET.ParseError:
        return []
    saida = []
    for it in [e for e in raiz.iter() if _local(e.tag) in ("item", "entry")][:limite]:
        campos = {}
        for filho in it:
            nome = _local(filho.tag)
            if nome == "link":
                campos.setdefault("link", (filho.get("href") or filho.text or "").strip())
            elif nome not in campos:
                campos[nome] = filho.text or ""
        titulo = _sem_html(campos.get("title", ""))
        descricao = _sem_html(campos.get("description") or campos.get("summary")
                              or campos.get("encoded") or campos.get("content") or "")
        pub = _data_rss(campos.get("pubdate") or campos.get("published")
                        or campos.get("updated") or campos.get("date") or "")
        if pub and (hoje_ - pub).days > MAX_IDADE_DIAS:
            continue
        if len(titulo) < 12:
            continue
        item = montar_item(titulo, descricao, campos.get("link", ""), fonte)
        if pub:
            item["publicado_em"] = pub.isoformat()
        saida.append(item)
    return saida


def extrair_feed(url_feed: str, fonte: str, limite: int = 30) -> list[dict]:
    """Baixa um feed RSS/Atom e devolve os itens recentes ([] em qualquer falha)."""
    try:
        r = requests.get(url_feed, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200 or "<" not in r.text[:200]:
            return []
        return itens_de_feed(r.text, fonte, limite)
    except Exception:
        return []


def itens_de_wp_api(posts: list, fonte: str, hoje_=None) -> list[dict]:
    """PURA: itens da API REST do WordPress (/wp-json/wp/v2/posts)."""
    hoje_ = hoje_ or datetime.date.today()
    saida = []
    for p in posts or []:
        titulo = _sem_html((p.get("title") or {}).get("rendered", ""))
        descricao = _sem_html((p.get("excerpt") or {}).get("rendered", ""))
        pub = _data_rss(p.get("date", ""))
        if pub and (hoje_ - pub).days > MAX_IDADE_DIAS:
            continue
        if len(titulo) < 12:
            continue
        item = montar_item(titulo, descricao, p.get("link", ""), fonte)
        if pub:
            item["publicado_em"] = pub.isoformat()
        saida.append(item)
    return saida


def extrair_wp_api(base: str, fonte: str, limite: int = 30, busca: str = "") -> list[dict]:
    """Posts recentes pela API do WordPress; `busca` filtra no próprio site
    (ex.: 'edital'). [] em qualquer falha."""
    p = urlparse(base)
    url = (f"{p.scheme}://{p.netloc}/wp-json/wp/v2/posts?per_page={limite}"
           f"&_fields=title,link,date,excerpt" + (f"&search={busca}" if busca else ""))
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200 or not r.text.lstrip().startswith("["):
            return []
        return itens_de_wp_api(r.json(), fonte)
    except Exception:
        return []


def coletar_com_reserva(url_base: str, fonte: str, itens_html: list) -> tuple[list, str]:
    """Se o HTML não rendeu nada, tenta o FEED RSS (/feed/) e depois a API do
    WordPress do mesmo site. Devolve (itens, via): via = "html" | "feed" |
    "wp_api" | "" (nada funcionou). Assim uma fonte que mudou de visual se
    recupera sozinha, sem ninguém reescrever seletor."""
    if itens_html:
        return itens_html, "html"
    if not url_base:
        return [], ""
    p = urlparse(url_base)
    raiz = f"{p.scheme}://{p.netloc}"
    for url_feed in (raiz + "/feed/", url_base.rstrip("/") + "/feed/"):
        itens = extrair_feed(url_feed, fonte)
        if itens:
            return itens, "feed"
    itens = extrair_wp_api(url_base, fonte)
    return (itens, "wp_api") if itens else ([], "")
