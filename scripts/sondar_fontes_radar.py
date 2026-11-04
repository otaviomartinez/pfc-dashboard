#!/usr/bin/env python3
"""SONDA das fontes do radar — só diagnóstico, não grava nada.

    python scripts/sondar_fontes_radar.py

Por que existe: 17 de 42 fontes vinham VAZIAS e os sites são bloqueados no
ambiente do assistente. Antes de reescrever extrator, a gente pergunta ao site
e LÊ a resposta (mesma lição da sonda fiscal). Para cada fonte, imprime uma
linha JSON com:
  - a página: status, endereço final (mudou?), tamanho, título, nº de links,
    sinais de página montada por JavaScript (o radar não enxerga essas);
  - links que parecem oportunidade (edital, chamada, inscrição, prêmio…);
  - FEED RSS (/feed/) e API do WordPress (/wp-json/wp/v2/posts): quando existem,
    são o jeito mais estável de ler — não quebram quando o site muda o visual.
"""
from __future__ import annotations

import json
import re
import sys
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, ".")
from radar.fontes_genericas import HEADERS  # noqa: E402

ALVOS = {
    # --- as 17 que vieram VAZIAS na rodada de 03/11/2026
    "Prosas": ["https://prosas.com.br/editais/", "https://prosas.com.br/"],
    "Finep": ["http://www.finep.gov.br/chamadas-publicas/chamadaspublicas?situacao=aberta",
              "https://www.finep.gov.br/chamadas-publicas"],
    "Itaú Social": ["https://www.itausocial.org.br/editais/", "https://www.itausocial.org.br/"],
    "Instituto Unibanco": ["https://www.institutounibanco.org.br/iniciativas/editais/",
                           "https://www.institutounibanco.org.br/"],
    "Fundação Telefônica Vivo": ["https://www.fundacaotelefonicavivo.org.br/noticias/",
                                 "https://www.fundacaotelefonicavivo.org.br/"],
    "Fundação Lemann": ["https://fundacaolemann.org.br/"],
    "Instituto Ayrton Senna": ["https://institutoayrtonsenna.org.br/"],
    "GIFE": ["https://gife.org.br/"],
    "Fundação Roberto Marinho": ["https://www.frm.org.br/"],
    "Parque Tecnológico de Sorocaba": ["https://www.parquetecsorocaba.com.br/"],
    "Prêmio Itaú-Unicef": ["https://premioitauunicef.org.br/"],
    "Instituto Votorantim": ["https://www.institutovotorantim.org.br/"],
    "Instituto Península": ["https://www.institutopeninsula.org.br/"],
    "Fundação Educar DPaschoal": ["https://educar.org.br/"],
    "Cenpec": ["https://www.cenpec.org.br/"],
    "Conviva Educação": ["https://convivaeducacao.org.br/"],
    "Instituto Natura": ["https://www.institutonatura.org/"],
    # --- candidatas NOVAS: financiadores de OSC de educação/infância/juventude
    "Fundação Abrinq": ["https://www.fadc.org.br/"],
    "Instituto Alana": ["https://alana.org.br/"],
    "Instituto Claro": ["https://www.institutoclaro.org.br/"],
    "Fundação Itaú": ["https://www.fundacaoitau.org.br/"],
    "B3 Social": ["https://www.b3social.com.br/"],
    "Fundação FEAC": ["https://feac.org.br/"],
    "Instituto MRV": ["https://institutomrv.com.br/"],
    "Fundo Brasil de Direitos Humanos": ["https://www.fundobrasil.org.br/"],
    "Fundação Maria Cecilia Souto Vidigal": ["https://www.fmcsv.org.br/"],
    "Fundação Volkswagen": ["https://www.fundacaovw.org.br/"],
    "Instituto Sicredi": ["https://www.institutosicredi.org/"],
}
_OPORT = re.compile(r"edital|editais|chamada|inscri|pr[eê]mio|sele[cç][aã]o|oportunidade|"
                    r"fomento|apoio a projetos|financiamento", re.I)


def _get(url, timeout=20):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return r
    except Exception as e:
        return e


def _pagina(url):
    r = _get(url)
    if isinstance(r, Exception):
        return {"url": url, "erro": f"{type(r).__name__}: {str(r)[:120]}"}
    info = {"url": url, "status": r.status_code, "final": r.url, "bytes": len(r.content)}
    if r.status_code != 200:
        return info
    soup = BeautifulSoup(r.text, "html.parser")
    links = soup.find_all("a", href=True)
    texto = soup.get_text(" ", strip=True)
    info.update({
        "titulo": (soup.title.get_text(strip=True) if soup.title else "")[:90],
        "links": len(links), "texto_chars": len(texto),
        "js": any(k in r.text for k in ("__NEXT_DATA__", 'id="root"', 'id="app"', "ng-version",
                                         "window.__NUXT__")) and len(texto) < 3000,
        "cloudflare": "cf-chl" in r.text or "Just a moment" in r.text,
        "wordpress": "wp-content" in r.text,
        "rss": [urljoin(url, l.get("href")) for l in soup.find_all("link", type="application/rss+xml")][:2],
        "oportunidades": [],
    })
    vistos = set()
    for a in links:
        t = " ".join(a.get_text(" ").split())
        h = urljoin(url, a["href"])
        if len(t) >= 12 and _OPORT.search(t + " " + h) and h not in vistos:
            vistos.add(h)
            info["oportunidades"].append(f"{t[:80]} | {h[:110]}")
        if len(info["oportunidades"]) >= 8:
            break
    return info


def _feed(base):
    raiz = f"{urlparse(base).scheme}://{urlparse(base).netloc}"
    out = {}
    r = _get(raiz + "/feed/")
    if not isinstance(r, Exception) and r.status_code == 200 and "<rss" in r.text[:500]:
        itens = re.findall(r"<item>.*?<title>(.*?)</title>", r.text, re.S)[:4]
        out["feed"] = {"n": r.text.count("<item>"), "titulos": [re.sub(r"<!\[CDATA\[|\]\]>", "", t)[:80] for t in itens]}
    r = _get(raiz + "/wp-json/wp/v2/posts?per_page=5&_fields=title,link,date")
    if not isinstance(r, Exception) and r.status_code == 200 and r.text.lstrip().startswith("["):
        try:
            posts = r.json()
            out["wp_api"] = [f'{p.get("date", "")[:10]} {p.get("title", {}).get("rendered", "")[:70]}' for p in posts][:4]
        except ValueError:
            pass
    return out


def main():
    for nome, urls in ALVOS.items():
        res = {"fonte": nome, "paginas": [_pagina(u) for u in urls]}
        res.update(_feed(urls[0]))
        print("SONDA " + json.dumps(res, ensure_ascii=False))
        sys.stdout.flush()
        time.sleep(0.5)


if __name__ == "__main__":
    main()
