"""
Camada 1 — extração DEDICADA das fontes-âncora verificadas.

Uma função por fonte, cada uma devolvendo uma lista de dicts padronizados
(titulo, descricao, url, fonte, data_encontrada, prazo, valor_estimado).
Extração conservadora: nunca inventa prazo/valor ausentes. O isolamento
(try/except por fonte) fica no orquestrador (main.py).
"""
from __future__ import annotations

import datetime
import re
import time
import unicodedata
from urllib.parse import urljoin

import requests

from radar.fontes_genericas import (
    HEADERS, extrair_de_soup, extrair_feed, extrair_wp_api, limpar_texto, montar_item, pegar_soup,
)


def _coletar(url: str, fonte: str, seletores, limite: int = 25) -> list[dict]:
    """Baixa a página e extrai itens usando os seletores dedicados da fonte.

    Sem fallback para 'todos os links': se os seletores não casarem, devolve []
    (extração conservadora — melhor 0 que ruído de navegação).
    """
    soup = pegar_soup(url)
    return extrair_de_soup(soup, url, fonte, seletores=seletores, limite=limite,
                           permitir_fallback=False)


# --- Agregadores -------------------------------------------------------------
# Home traz mais notícia que prêmio; as seções /tag/premio/ e a de editais
# carregam os prêmios institucionais (BRB Impacto Social, LED, FEAC, BNDES,
# prêmio internacional) que a home não destaca. Raspa as três e dedup por URL.
_OBS3_URLS = [
    "https://observatorio3setor.org.br/",
    "https://observatorio3setor.org.br/tag/premio/",
    "https://observatorio3setor.org.br/secoes_tematicas/editais/",
]
_OBS3_SELETORES = ["article", "div[class*=post]", "div[class*=card]",
                   ".elementor-post", "h2 a[href]", "h3 a[href]"]


def fonte_observatorio3setor():
    itens, vistos = [], set()
    for url in _OBS3_URLS:
        for it in _coletar(url, "Observatório 3º Setor", _OBS3_SELETORES):
            u = it.get("url", "")
            if u and u not in vistos:
                vistos.add(u)
                itens.append(it)
    return itens


def fonte_abcr():
    return _coletar("https://captadores.org.br/editais/", "ABCR",
                    ["article", "div[class*=edital]", "div[class*=card]", ".elementor-post"])


def fonte_mapaosc():
    return _coletar("https://mapaosc.ipea.gov.br/editais", "Mapa das OSC (IPEA)",
                    ["div[class*=card]", "article", "li", "tr"])


def fonte_capta():
    # Apex capta.org.br falha DNS às vezes; o www é estável. Editais ficam em
    # blocos div.post (título em h3). Muita coisa é ambiente/cultura/social —
    # o filtro de relevância derruba o que não é captação de educação/ciência.
    return _coletar("https://www.capta.org.br/fontes-de-financiamento/oportunidades/",
                    "Capta",
                    ["div.post", "h3.arquivos a", "h3 a[href]", "div[class*=post]"])


def fonte_rede_filantropia():
    """Rede Filantropia: os editais são matérias em /informacao/<slug> espalhadas
    numa grade Bootstrap (sem bloco limpo), então extraímos por LINK, não por
    seletor de bloco. Corta o ruído de curso pago (links p/ dialogosocial.com.br)
    e navegação curta. O filtro de relevância decide o que é captação de fato."""
    base = "https://filantropia.ong/"
    soup = pegar_soup(base)
    if soup is None:
        return []
    itens, vistos = [], set()
    for a in soup.find_all("a", href=True):
        href = urljoin(base, (a.get("href") or "").strip())
        # só matérias do próprio site; nunca o curso pago (dialogosocial)
        if "/informacao/" not in href or "dialogosocial" in href.lower():
            continue
        titulo = limpar_texto(a.get_text())
        if len(titulo) < 20 or href in vistos:
            continue
        vistos.add(href)
        itens.append(montar_item(titulo, "", href, "Rede Filantropia"))
        if len(itens) >= 40:
            break
    return itens


# --- Órgãos públicos ---------------------------------------------------------
def fonte_cnpq():
    return _coletar("https://www.gov.br/cnpq/pt-br/chamadas/abertas-para-submissao", "CNPq",
                    ["article", "li[class*=item]", "div[class*=chamada]", ".tileItem", "tr"])


def fonte_fapesp():
    return _coletar("https://fapesp.br/chamadas/", "FAPESP",
                    ["div[class*=chamada]", "article", "li", "tr", "div[class*=card]"])


def fonte_finep():
    return _coletar(
        "http://www.finep.gov.br/chamadas-publicas/chamadaspublicas?situacao=aberta", "Finep",
        ["div[class*=chamada]", "article", "li[class*=item]", "tr", "div[class*=card]"])


# --- Fundações com editais próprios ------------------------------------------
def fonte_fbb():
    return _coletar("https://fbb.org.br/editais-de-projetos/editais-publicos/",
                    "Fundação Banco do Brasil",
                    ["article", "div[class*=edital]", "div[class*=card]", ".elementor-post"])


def fonte_itau_social():
    # Sonda de nov/2026: o HTML de /editais/ virou só um link para a plataforma
    # (editais.itausocial.org.br); o FEED da própria seção é o que traz os posts.
    return (extrair_feed("https://www.itausocial.org.br/editais/feed/", "Itaú Social")
            or extrair_feed("https://www.itausocial.org.br/feed/", "Itaú Social"))


def fonte_instituto_unibanco():
    return _coletar("https://www.institutounibanco.org.br/iniciativas/editais/",
                    "Instituto Unibanco",
                    ["article", "div[class*=card]", "div[class*=edital]", ".elementor-post"])


# --- Institutos de relacionamento (notícias/novidades) -----------------------
def fonte_fund_telefonica():
    return _coletar("https://www.fundacaotelefonicavivo.org.br/noticias/",
                    "Fundação Telefônica Vivo",
                    ["article", "div[class*=card]", "div[class*=noticia]", ".elementor-post"])


def fonte_fund_lemann():
    # Sonda nov/2026: HTML não casa mais; o feed do WordPress funciona.
    return extrair_feed("https://fundacaolemann.org.br/feed/", "Fundação Lemann")


def fonte_ayrton_senna():
    # Sonda nov/2026: sem feed, mas a API do WordPress responde.
    return extrair_wp_api("https://institutoayrtonsenna.org.br/", "Instituto Ayrton Senna")


def fonte_instituto_cpfl():
    return _coletar("https://institutocpfl.org.br/", "Instituto CPFL",
                    ["article", "div[class*=card]", "div[class*=post]", ".elementor-post"])


def fonte_gife():
    # Sonda nov/2026: feed do WordPress funciona (notícias do investimento
    # social; o crivo do scorer separa o que é edital).
    return extrair_feed("https://gife.org.br/feed/", "GIFE")


def fonte_fund_bradesco():
    return _coletar("https://fundacao.bradesco/instituicoes", "Fundação Bradesco",
                    ["article", "div[class*=card]", "li", "div[class*=item]"])


def fonte_frm():
    return _coletar("https://www.frm.org.br/", "Fundação Roberto Marinho",
                    ["article", "div[class*=card]", "div[class*=post]", ".elementor-post"])


# --- Regional ----------------------------------------------------------------
def fonte_parque_sorocaba():
    return _coletar("https://www.parquetecsorocaba.com.br/", "Parque Tecnológico de Sorocaba",
                    ["article", "div[class*=card]", "div[class*=noticia]", ".elementor-post"])


# --- Ciência jovem / prêmios / educação --------------------------------------
def fonte_mcti():
    return _coletar("https://www.gov.br/mcti/pt-br/acompanhe-o-mcti/noticias", "MCTI",
                    ["article", ".tileItem", "li[class*=item]", "div[class*=noticia]", "div[class*=card]"])


def fonte_premio_itau_unicef():
    return _coletar("https://premioitauunicef.org.br/", "Prêmio Itaú-Unicef",
                    ["article", "div[class*=card]", "div[class*=post]", ".elementor-post", "div[class*=noticia]"])


def fonte_porvir():
    return _coletar("https://porvir.org/", "PORVIR",
                    ["article", "div[class*=card]", "div[class*=post]", ".elementor-post", "li.item"])


def fonte_instituto_votorantim():
    return _coletar("https://www.institutovotorantim.org.br/", "Instituto Votorantim",
                    ["article", "div[class*=card]", "div[class*=noticia]", "div[class*=post]", ".elementor-post"])


# NOTA: as fontes de OLIMPÍADA (OBMEP, OBA, OBBiotec, Comunidade Científica Jr)
# e as FEIRAS de ciências (FEBRACE, MOSTRATEC) foram REMOVIDAS deste radar. Elas
# servem à MISSÃO do PFC (alunos fazendo ciência), não à CAPTAÇÃO (dinheiro que a
# organização levanta): no diagnóstico traziam 43 itens e ZERO captação. Se um
# dia o PFC quiser um radar de "oportunidades para alunos", ele é OUTRO produto,
# com outra régua.


# --- Pesquisa / institutos de educação ---------------------------------------
def fonte_impa():
    return _coletar("https://impa.br/noticias/", "IMPA",
                    ["article", "div[class*=card]", "div[class*=noticia]",
                     "div[class*=post]", "li[class*=item]"])


def fonte_instituto_peninsula():
    return _coletar("https://www.institutopeninsula.org.br/", "Instituto Península",
                    ["article", "div[class*=card]", "div[class*=post]",
                     ".elementor-post", "div[class*=noticia]"])


def fonte_educar_dpaschoal():
    return _coletar("https://educar.org.br/", "Fundação Educar DPaschoal",
                    ["article", "div[class*=card]", "div[class*=post]",
                     ".elementor-post", "div[class*=noticia]", "li[class*=item]"])


# --- NOVAS (nov/2026): financiadores de OSC de educação/infância/juventude,
# todas conferidas pela sonda (scripts/sondar_fontes_radar.py) no GitHub ---------
def fonte_alana():
    return extrair_feed("https://alana.org.br/feed/", "Instituto Alana")


def fonte_instituto_claro():
    return extrair_feed("https://www.institutoclaro.org.br/feed/", "Instituto Claro")


def fonte_feac():
    """FEAC: página "Editais e Chamadas" (links de edital) + feed das notícias."""
    itens, vistos = [], set()
    soup = pegar_soup("https://feac.org.br/editais/")
    if soup is not None:
        for a in soup.find_all("a", href=True):
            href = urljoin("https://feac.org.br/editais/", a["href"].strip())
            titulo = limpar_texto(a.get_text())
            if ("edital" in href.lower() or "chamada" in href.lower()) and len(titulo) >= 15 \
                    and href not in vistos and href.rstrip("/") != "https://feac.org.br/editais":
                vistos.add(href)
                itens.append(montar_item(titulo, "", href, "Fundação FEAC"))
    return itens + [i for i in extrair_feed("https://feac.org.br/feed/", "Fundação FEAC")
                    if i["url"] not in vistos]


def fonte_instituto_mrv():
    return extrair_feed("https://institutomrv.com.br/feed/", "Instituto MRV")


def fonte_fmcsv():
    return extrair_feed("https://fundacaomariacecilia.org.br/feed/",
                        "Fundação Maria Cecilia Souto Vidigal")


def fonte_fundo_brasil():
    """Fundo Brasil de Direitos Humanos: a página de editais lista links /edital/."""
    base = "https://www.fundobrasil.org.br/nosso-trabalho/apoio-a-sociedade-civil/editais-gerais-e-especificos/"
    soup = pegar_soup(base)
    if soup is None:
        return []
    itens, vistos = [], set()
    for a in soup.find_all("a", href=True):
        href = urljoin(base, a["href"].strip())
        titulo = limpar_texto(a.get_text())
        if "/edital/" in href and len(titulo) >= 15 and href not in vistos:
            vistos.add(href)
            itens.append(montar_item(titulo, "", href, "Fundo Brasil de Direitos Humanos"))
    return itens


# --- PROSAS (nov/2026): o maior agregador de editais para OSC ----------------
# O site é JavaScript; 6 sondas acharam a API pública que a própria página usa:
#   /selecao/api/v2/publics/oportunidades  (JSON:API, 20 por página por padrão)
# Traz nome, financiador, áreas e o PRAZO ESTRUTURADO das inscrições (data e hora
# do sistema do Prosas — prazo confiável, regra 3). O robots.txt do Prosas pede
# 30 s entre pedidos (Crawl-Delay): respeitamos, com poucas páginas grandes.
# Decisão do coordenador (nov/2026): ler mesmo com o robots.txt fechando o site
# para robôs que não são buscadores; leitura 1x/dia, só a lista pública, sem
# login. Se o Prosas bloquear, a fonte volta vazia e o resumo da rodada mostra.
PROSAS_API = "https://prosas.com.br/selecao/api/v2/publics/oportunidades"
PROSAS_PAUSA = 30
PROSAS_POR_PAGINA = 50
PROSAS_MAX_PAGINAS = 4

# Edital de ÓRGÃO PÚBLICO local (secretaria municipal, fundação de cultura de um
# estado…) só aceita entidade daquele lugar. Vale para o PFC se o órgão for do
# estado de SP ou de uma cidade do PFC; senão, fora.
_ORGAO_LOCAL = re.compile(
    r"\b(secretaria (municipal|estadual|de estado)|prefeitura|municipio de|governo do estado|"
    r"fundacao (de )?cultura|fundacao cultural|fundacao catarinense|conselho municipal|"
    r"camara municipal|secult|secretaria de cultura)\b")
# PALAVRA INTEIRA: "itu" solto casava "instITUto" e salvava órgão de outro estado.
_LOCAL_PFC = re.compile(
    r"\b(sao paulo|paulista|sorocaba|ipero|tatui|salto|sao roque|rio claro|mirassol|"
    r"corumbatai|capela do alto|cesario lange|guarei|juquia|votorantim|itu)\b")


def _n(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def prosas_orgao_de_fora(nome: str, financiador: str) -> bool:
    """PURA: edital de órgão público de outro lugar (não SP, não cidade do PFC)."""
    texto = _n(f"{financiador} {nome}")
    return bool(_ORGAO_LOCAL.search(texto)) and not _LOCAL_PFC.search(texto)


def itens_prosas(payload: dict, hoje=None) -> list[dict]:
    """PURA: itens do radar a partir de uma página da API do Prosas (JSON:API).
    Fica de fora: inscrição já encerrada e edital de órgão público de outro lugar."""
    hoje = hoje or datetime.date.today()
    incluidos = {(i.get("type"), str(i.get("id"))): i.get("attributes") or {}
                 for i in (payload or {}).get("included") or []}
    saida = []
    for d in (payload or {}).get("data") or []:
        a = d.get("attributes") or {}
        nome = limpar_texto(a.get("nome"))
        if not nome:
            continue
        rel = d.get("relationships") or {}
        inc = (rel.get("incentivador") or {}).get("data") or {}
        fin = incluidos.get((inc.get("type"), str(inc.get("id"))), {})
        financiador = limpar_texto(fin.get("nome") or fin.get("nome_fantasia") or fin.get("razao_social")
                                   or a.get("nome_empresa") or "")
        areas = [limpar_texto((incluidos.get((x.get("type"), str(x.get("id"))), {}) or {}).get("nome", ""))
                 for x in ((rel.get("area_interesses") or {}).get("data") or [])]
        areas = [x for x in areas if x]
        fim = str(a.get("encerramento_das_inscricoes") or a.get("data_final_inscricoes") or "")[:10]
        try:
            prazo = datetime.date.fromisoformat(fim) if fim else None
        except ValueError:
            prazo = None
        if prazo and prazo < hoje:
            continue
        if prosas_orgao_de_fora(nome, financiador):
            continue
        partes = [financiador, "áreas: " + ", ".join(areas) if areas else "",
                  f"inscrições até {prazo.strftime('%d/%m/%Y')}" if prazo else ""]
        item = montar_item(nome, " · ".join(x for x in partes if x),
                           f"https://prosas.com.br/editais/{a.get('id') or d.get('id')}", "Prosas")
        if prazo:
            # prazo ESTRUTURADO do sistema do Prosas — não é texto adivinhado
            item["prazo"] = prazo.isoformat()
            item["dias_restantes"] = (prazo - hoje).days
        saida.append(item)
    return saida


def fonte_prosas():
    itens = []
    for pagina in range(1, PROSAS_MAX_PAGINAS + 1):
        if pagina > 1:
            time.sleep(PROSAS_PAUSA)
        try:
            r = requests.get(PROSAS_API, params={
                "page[page]": pagina, "page[size]": PROSAS_POR_PAGINA,
                "include": "area_interesses,incentivador"},
                headers={**HEADERS, "Accept": "application/vnd.api+json, application/json"},
                timeout=40)
            if r.status_code != 200:
                break
            payload = r.json()
        except Exception:
            break
        itens += itens_prosas(payload)
        if len(payload.get("data") or []) < PROSAS_POR_PAGINA:
            break
    return itens


# DESATIVADAS na sonda de nov/2026 (o motivo fica registrado para ninguém
# reativar no escuro; a sonda pode ser rodada de novo a qualquer momento):
FONTES_DESATIVADAS = {
    "Finep": "redireciona para /oportunidades (crédito a empresas), sem lista de chamadas",
    "Instituto Unibanco": "página em JavaScript: 0 links no HTML",
    "Fundação Telefônica Vivo": "bloqueia robô (HTTP 403)",
    "Fundação Roberto Marinho": "página em JavaScript e sem feed",
    "Parque Tecnológico de Sorocaba": "página em JavaScript; só tem licitações",
    "Prêmio Itaú-Unicef": "domínio fora do ar (não conecta)",
    "Instituto Península": "certificado de segurança inválido",
    "Fundação Educar DPaschoal": "certificado de segurança inválido",
}


# Registro nome -> função (usado com isolamento em main.py).
FONTES = {
    "Observatório 3º Setor": fonte_observatorio3setor,
    "ABCR": fonte_abcr,
    "Mapa das OSC (IPEA)": fonte_mapaosc,
    "Capta": fonte_capta,
    "Rede Filantropia": fonte_rede_filantropia,
    "CNPq": fonte_cnpq,
    "FAPESP": fonte_fapesp,
    "Fundação Banco do Brasil": fonte_fbb,
    "Itaú Social": fonte_itau_social,
    "Fundação Lemann": fonte_fund_lemann,
    "Instituto Ayrton Senna": fonte_ayrton_senna,
    "Instituto CPFL": fonte_instituto_cpfl,
    "GIFE": fonte_gife,
    "Fundação Bradesco": fonte_fund_bradesco,
    "MCTI": fonte_mcti,
    "PORVIR": fonte_porvir,
    "Instituto Votorantim": fonte_instituto_votorantim,
    "IMPA": fonte_impa,
    "Instituto Alana": fonte_alana,
    "Instituto Claro": fonte_instituto_claro,
    "Fundação FEAC": fonte_feac,
    "Instituto MRV": fonte_instituto_mrv,
    "Fundação Maria Cecilia Souto Vidigal": fonte_fmcsv,
    "Fundo Brasil de Direitos Humanos": fonte_fundo_brasil,
    "Prosas": fonte_prosas,
}

# URLs das fontes-âncora (para a Camada 3 varrer links externos).
ANCORA_URLS = [
    "https://observatorio3setor.org.br/",
    "https://captadores.org.br/editais/",
    "https://mapaosc.ipea.gov.br/editais",
    "https://www.capta.org.br/fontes-de-financiamento/oportunidades/",
    "https://filantropia.ong/",
    "https://www.gov.br/cnpq/pt-br/chamadas/abertas-para-submissao",
    "https://fapesp.br/chamadas/",
    "https://fbb.org.br/editais-de-projetos/editais-publicos/",
    "https://www.itausocial.org.br/editais/",
    "https://fundacaolemann.org.br/",
    "https://institutoayrtonsenna.org.br/",
    "https://institutocpfl.org.br/",
    "https://gife.org.br/",
    "https://fundacao.bradesco/instituicoes",
    "https://www.gov.br/mcti/pt-br/acompanhe-o-mcti/noticias",
    "https://porvir.org/",
    "https://www.institutovotorantim.org.br/",
    "https://impa.br/noticias/",
    "https://alana.org.br/",
    "https://www.institutoclaro.org.br/",
    "https://feac.org.br/editais/",
    "https://institutomrv.com.br/",
    "https://fundacaomariacecilia.org.br/",
    "https://www.fundobrasil.org.br/nosso-trabalho/apoio-a-sociedade-civil/editais-gerais-e-especificos/",
    "https://prosas.com.br/editais",
]


# Nome -> URL da fonte, para a RESERVA por feed/API quando o HTML vem vazio
# (radar/main.py). FONTES e ANCORA_URLS estão na mesma ordem; o assert pega o
# dia em que alguém acrescentar numa lista e esquecer da outra.
assert len(FONTES) == len(ANCORA_URLS), "FONTES e ANCORA_URLS fora de sincronia"
URL_DA_FONTE = dict(zip(FONTES, ANCORA_URLS))
