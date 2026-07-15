"""
Avaliação automática das fontes candidatas descobertas (Camada 3 -> humano).

Lê radar/fontes_candidatas.csv (domínios citados nas páginas-âncora), visita
as mais mencionadas e coleta sinais para a decisão humana ficar em 1 clique:
nome do site, se parece listar editais, aderência ao DNA do PFC (palavras-
chave do scorer) e uma URL sugerida de monitoramento. Grava tudo em
radar/candidatas_avaliadas.csv com veredito automático + status "pendente".

NÃO adiciona nada ao radar sozinho: a aprovação é feita no app (aba
Verificação), que move a URL sugerida para config_fontes.json.

Rodar:  python -m radar.avaliar_candidatas
"""
from __future__ import annotations

import csv
import json
import os
import re
import time
from urllib.parse import urljoin, urlparse

from radar.fontes_ancora import ANCORA_URLS
from radar.fontes_genericas import dominio_de, limpar_texto, pegar_soup
from radar.scorer import _score_aderencia

BASE = os.path.dirname(os.path.abspath(__file__))
CANDIDATAS_CSV = os.path.join(BASE, "fontes_candidatas.csv")
AVALIADAS_CSV = os.path.join(BASE, "candidatas_avaliadas.csv")
CONFIG = os.path.join(BASE, "config_fontes.json")

CAMPOS = ["dominio", "nome", "url_sugerida", "aderencia", "tem_editais",
          "mencoes", "veredito", "status"]

MAX_AVALIACOES = 40
PAUSA_S = 0.4
LIMIAR_ADERENCIA = 60

# Sinais de que a página LISTA oportunidades (não só fala do tema).
_PALAVRAS_EDITAIS = ["edital", "editais", "chamada pública", "chamadas",
                     "inscrições", "inscricoes", "seleção de projetos",
                     "selecao de projetos", "oportunidades"]
# Subpáginas óbvias tentadas quando a home não linka uma seção de editais.
_SUBCAMINHOS = ["/editais", "/chamadas", "/oportunidades", "/noticias"]
_RE_LINK_EDITAL = re.compile(r"edita(l|is)|chamada|oportunidad", re.IGNORECASE)

# Infra/encurtadores/mídia que nunca são fonte de fomento (economiza request).
_RUIDO = {
    "bit.ly", "mailchi.mp", "list-manage.com", "soundcloud.com",
    "creativecommons.org", "powerbi.com", "app.powerbi.com", "doubleclick.net",
    "cloudfront.net", "googleapis.com", "gstatic.com", "wp.com", "gravatar.com",
    "addtoany.com", "sharethis.com", "vimeo.com", "issuu.com", "medium.com",
    "wikipedia.org", "wordpress.com", "blogspot.com", "typeform.com",
    "forms.gle", "docs.google.com", "drive.google.com", "sympla.com.br",
    "eventbrite.com", "cutt.ly", "tinyurl.com", "linktr.ee",
}


def _normalizar_dominio(dom: str) -> str:
    """remove porta e www (ex.: 'obmep.org.br:80' -> 'obmep.org.br')."""
    dom = (dom or "").strip().lower().split(":")[0]
    return dom[4:] if dom.startswith("www.") else dom


def _e_ruido(dom: str) -> bool:
    if any(dom == r or dom.endswith("." + r) for r in _RUIDO):
        return True
    return dom.split(".")[0].startswith(("cdn", "static", "assets"))


def _dominios_conhecidos() -> set[str]:
    """Âncoras + fontes já ativas no config (não sugerir o que já monitoramos)."""
    known = {dominio_de(u) for u in ANCORA_URLS}
    try:
        with open(CONFIG, encoding="utf-8") as f:
            cfg = json.load(f)
        for e in cfg if isinstance(cfg, list) else []:
            d = dominio_de(str(e.get("url", "")))
            if d:
                known.add(d)
    except Exception:
        pass
    return {d for d in known if d}


def _titulo_site(soup) -> str:
    og = soup.find("meta", attrs={"property": "og:site_name"})
    if og and og.get("content", "").strip():
        return limpar_texto(og["content"])[:120]
    if soup.title and soup.title.get_text().strip():
        return limpar_texto(soup.title.get_text())[:120]
    return ""


def _tem_sinais_editais(texto: str) -> bool:
    t = (texto or "").lower()
    return any(p in t for p in _PALAVRAS_EDITAIS)


def _link_interno_de_editais(soup, base_url: str) -> str:
    """Primeiro link do MESMO domínio cujo href/texto sugira seção de editais."""
    base_dom = dominio_de(base_url)
    for a in soup.find_all("a", href=True):
        alvo = urljoin(base_url, a["href"].strip())
        if not alvo.startswith("http") or dominio_de(alvo) != base_dom:
            continue
        if _RE_LINK_EDITAL.search(a["href"]) or _RE_LINK_EDITAL.search(a.get_text() or ""):
            return alvo.split("#")[0]
    return ""


def avaliar_candidata(dom: str, mencoes: int) -> dict:
    """Visita o domínio e monta a ficha de decisão (nunca lança exceção)."""
    ficha = {"dominio": dom, "nome": "", "url_sugerida": f"https://{dom}",
             "aderencia": 0, "tem_editais": False, "mencoes": mencoes,
             "veredito": "descartar", "status": "pendente"}
    try:
        home = f"https://{dom}"
        soup = pegar_soup(home) or pegar_soup(f"http://{dom}")
        if soup is None:
            ficha["nome"] = dom
            return ficha  # inacessível -> descartar

        ficha["nome"] = _titulo_site(soup) or dom
        texto_home = limpar_texto(soup.get_text(" "))[:15000]
        ficha["aderencia"] = int(_score_aderencia(texto_home)[0])
        tem_editais = _tem_sinais_editais(texto_home)
        url_sugerida = home

        # subpágina de editais: link interno da home, senão caminhos óbvios
        sub_url = _link_interno_de_editais(soup, home)
        tentativas = ([sub_url] if sub_url else []) + \
                     [home.rstrip("/") + c for c in _SUBCAMINHOS]
        for alvo in tentativas[:2]:  # no máximo 2 requests extras por domínio
            sub_soup = pegar_soup(alvo)
            if sub_soup is None:
                continue
            sub_texto = limpar_texto(sub_soup.get_text(" "))[:15000]
            if _tem_sinais_editais(sub_texto):
                tem_editais = True
                url_sugerida = alvo
                ficha["aderencia"] = max(ficha["aderencia"],
                                         int(_score_aderencia(sub_texto)[0]))
                break

        ficha["tem_editais"] = tem_editais
        ficha["url_sugerida"] = url_sugerida
        aderente = ficha["aderencia"] >= LIMIAR_ADERENCIA
        if aderente and tem_editais:
            ficha["veredito"] = "recomendada"
        elif aderente or tem_editais:
            ficha["veredito"] = "talvez"
    except Exception:
        pass  # ficha parcial já tem defaults seguros
    return ficha


def _ler_candidatas() -> list[dict]:
    try:
        with open(CANDIDATAS_CSV, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def _ler_avaliadas() -> dict[str, dict]:
    try:
        with open(AVALIADAS_CSV, encoding="utf-8", newline="") as f:
            return {r.get("dominio", ""): r for r in csv.DictReader(f)}
    except Exception:
        return {}


def executar() -> dict:
    candidatas = _ler_candidatas()
    avaliadas = _ler_avaliadas()   # preserva aprovada/descartada de rodadas antigas
    conhecidos = _dominios_conhecidos()

    # agrega menções por domínio normalizado e filtra ruído/já conhecidas
    mencoes: dict[str, int] = {}
    for r in candidatas:
        dom = _normalizar_dominio(r.get("dominio", ""))
        if not dom or "." not in dom or _e_ruido(dom):
            continue
        if any(dom == c or dom.endswith("." + c) for c in conhecidos):
            continue
        mencoes[dom] = mencoes.get(dom, 0) + int(r.get("mencoes", "0") or 0)

    fila = sorted(mencoes.items(), key=lambda kv: kv[1], reverse=True)
    n_visitadas = 0
    for dom, n in fila:
        if n_visitadas >= MAX_AVALIACOES:
            break
        ja = avaliadas.get(dom)
        if ja and ja.get("status", "pendente") != "pendente":
            continue  # decisão humana já tomada — não reavalia nem ressuscita
        avaliadas[dom] = avaliar_candidata(dom, n)
        n_visitadas += 1
        time.sleep(PAUSA_S)

    linhas = sorted(avaliadas.values(),
                    key=lambda r: (str(r.get("veredito")) != "recomendada",
                                   str(r.get("veredito")) != "talvez",
                                   -int(r.get("aderencia", 0) or 0)))
    try:
        with open(AVALIADAS_CSV, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore")
            w.writeheader()
            w.writerows(linhas)
    except Exception as e:
        print(f"  ! Não consegui gravar {os.path.basename(AVALIADAS_CSV)}: {e}")

    dist: dict[str, int] = {}
    for r in linhas:
        v = str(r.get("veredito", "?"))
        dist[v] = dist.get(v, 0) + 1
    return {"visitadas": n_visitadas, "total": len(linhas), "distribuicao": dist}


if __name__ == "__main__":
    res = executar()
    print("== Avaliação de fontes candidatas ==")
    print(f"{res['visitadas']} candidatas visitadas nesta rodada · "
          f"{res['total']} no arquivo candidatas_avaliadas.csv")
    print("Vereditos:", ", ".join(f"{k}: {v}" for k, v in
                                  sorted(res["distribuicao"].items())))
