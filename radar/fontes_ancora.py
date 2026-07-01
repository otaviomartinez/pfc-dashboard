"""
Camada 1 — extração DEDICADA das 18 fontes verificadas.

Uma função por fonte, cada uma devolvendo uma lista de dicts padronizados
(titulo, descricao, url, fonte, data_encontrada, prazo, valor_estimado).
Extração conservadora: nunca inventa prazo/valor ausentes. O isolamento
(try/except por fonte) fica no orquestrador (main.py).
"""
from __future__ import annotations

from radar.fontes_genericas import extrair_de_soup, pegar_soup


def _coletar(url: str, fonte: str, seletores, limite: int = 25) -> list[dict]:
    """Baixa a página e extrai itens usando os seletores dedicados da fonte.

    Sem fallback para 'todos os links': se os seletores não casarem, devolve []
    (extração conservadora — melhor 0 que ruído de navegação).
    """
    soup = pegar_soup(url)
    return extrair_de_soup(soup, url, fonte, seletores=seletores, limite=limite,
                           permitir_fallback=False)


# --- Agregadores -------------------------------------------------------------
def fonte_prosas():
    return _coletar("https://prosas.com.br/editais/", "Prosas",
                    ["div[class*=card]", "div[class*=edital]", "article", "li.item"])


def fonte_observatorio3setor():
    return _coletar("https://observatorio3setor.org.br/", "Observatório 3º Setor",
                    ["article", "div[class*=post]", "div[class*=card]", ".elementor-post"])


def fonte_abcr():
    return _coletar("https://captadores.org.br/editais/", "ABCR",
                    ["article", "div[class*=edital]", "div[class*=card]", ".elementor-post"])


def fonte_mapaosc():
    return _coletar("https://mapaosc.ipea.gov.br/editais", "Mapa das OSC (IPEA)",
                    ["div[class*=card]", "article", "li", "tr"])


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
    return _coletar("https://www.itausocial.org.br/editais/", "Itaú Social",
                    ["article", "div[class*=card]", "div[class*=edital]", ".elementor-post"])


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
    return _coletar("https://fundacaolemann.org.br/", "Fundação Lemann",
                    ["article", "div[class*=card]", "div[class*=post]", ".elementor-post"])


def fonte_ayrton_senna():
    return _coletar("https://institutoayrtonsenna.org.br/", "Instituto Ayrton Senna",
                    ["article", "div[class*=card]", "div[class*=noticia]", ".elementor-post"])


def fonte_instituto_cpfl():
    return _coletar("https://institutocpfl.org.br/", "Instituto CPFL",
                    ["article", "div[class*=card]", "div[class*=post]", ".elementor-post"])


def fonte_gife():
    return _coletar("https://gife.org.br/", "GIFE",
                    ["article", "div[class*=card]", "div[class*=post]", ".elementor-post"])


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


# Registro nome -> função (usado com isolamento em main.py).
FONTES = {
    "Prosas": fonte_prosas,
    "Observatório 3º Setor": fonte_observatorio3setor,
    "ABCR": fonte_abcr,
    "Mapa das OSC (IPEA)": fonte_mapaosc,
    "CNPq": fonte_cnpq,
    "FAPESP": fonte_fapesp,
    "Finep": fonte_finep,
    "Fundação Banco do Brasil": fonte_fbb,
    "Itaú Social": fonte_itau_social,
    "Instituto Unibanco": fonte_instituto_unibanco,
    "Fundação Telefônica Vivo": fonte_fund_telefonica,
    "Fundação Lemann": fonte_fund_lemann,
    "Instituto Ayrton Senna": fonte_ayrton_senna,
    "Instituto CPFL": fonte_instituto_cpfl,
    "GIFE": fonte_gife,
    "Fundação Bradesco": fonte_fund_bradesco,
    "Fundação Roberto Marinho": fonte_frm,
    "Parque Tecnológico de Sorocaba": fonte_parque_sorocaba,
}

# URLs das fontes-âncora (para a Camada 3 varrer links externos).
ANCORA_URLS = [
    "https://prosas.com.br/editais/",
    "https://observatorio3setor.org.br/",
    "https://captadores.org.br/editais/",
    "https://mapaosc.ipea.gov.br/editais",
    "https://www.gov.br/cnpq/pt-br/chamadas/abertas-para-submissao",
    "https://fapesp.br/chamadas/",
    "http://www.finep.gov.br/chamadas-publicas/chamadaspublicas?situacao=aberta",
    "https://fbb.org.br/editais-de-projetos/editais-publicos/",
    "https://www.itausocial.org.br/editais/",
    "https://www.institutounibanco.org.br/iniciativas/editais/",
    "https://www.fundacaotelefonicavivo.org.br/noticias/",
    "https://fundacaolemann.org.br/",
    "https://institutoayrtonsenna.org.br/",
    "https://institutocpfl.org.br/",
    "https://gife.org.br/",
    "https://fundacao.bradesco/instituicoes",
    "https://www.frm.org.br/",
    "https://www.parquetecsorocaba.com.br/",
]
