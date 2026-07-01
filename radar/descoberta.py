"""
Camada 3 — descoberta de novas fontes (para revisão humana).

Durante a varredura, coleta os links EXTERNOS citados nas páginas-âncora que
NÃO estão na lista de fontes conhecidas, agrega por domínio com contagem de
menções e grava em radar/fontes_candidatas.csv. NÃO adiciona nada ao radar
automaticamente — é só um insumo para você expandir o config_fontes.json.
"""
from __future__ import annotations

import csv
import datetime
import os
from urllib.parse import urljoin

from radar.fontes_genericas import dominio_de, pegar_soup

# Domínios de ruído que não interessam como fonte de fomento.
_IGNORAR = {
    "facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com",
    "linkedin.com", "whatsapp.com", "wa.me", "t.me", "telegram.org",
    "google.com", "goo.gl", "maps.google.com", "flickr.com", "spotify.com",
    "apple.com", "play.google.com", "gov.br", "jusbrasil.com.br",
}


def _relevante(dom: str, conhecidos: set) -> bool:
    if not dom or "." not in dom:
        return False
    # ignora o próprio domínio e subdomínios de fontes já conhecidas
    if any(dom == c or dom.endswith("." + c) for c in conhecidos):
        return False
    return not any(dom == ig or dom.endswith("." + ig) for ig in _IGNORAR)


def descobrir_candidatas(urls_ancora, dominios_conhecidos, caminho_csv) -> int:
    """Varre as páginas-âncora, agrega domínios externos e persiste no CSV.

    Devolve o número de domínios candidatos DISTINTOS vistos nesta execução.
    """
    conhecidos = {d.lower() for d in dominios_conhecidos}
    contagem = {}
    for url in urls_ancora:
        try:
            soup = pegar_soup(url)
            if soup is None:
                continue
            for a in soup.find_all("a", href=True):
                dom = dominio_de(urljoin(url, a["href"]))
                if _relevante(dom, conhecidos):
                    contagem[dom] = contagem.get(dom, 0) + 1
        except Exception:
            continue
    _persistir(caminho_csv, contagem)
    return len(contagem)


def _persistir(caminho_csv, contagem) -> None:
    """Acumula as contagens no CSV (soma com execuções anteriores)."""
    hoje = datetime.date.today().isoformat()
    linhas = {}
    if os.path.exists(caminho_csv):
        try:
            with open(caminho_csv, encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    linhas[row.get("dominio", "")] = {
                        "dominio": row.get("dominio", ""),
                        "nome_inferido": row.get("nome_inferido", ""),
                        "mencoes": int(row.get("mencoes", "0") or 0),
                        "ultima_data": row.get("ultima_data", ""),
                    }
        except Exception:
            linhas = {}

    for dom, n in contagem.items():
        atual = linhas.get(dom, {"dominio": dom, "nome_inferido": _nome_inferido(dom),
                                 "mencoes": 0, "ultima_data": ""})
        atual["mencoes"] += n
        atual["ultima_data"] = hoje
        linhas[dom] = atual

    ordenado = sorted(linhas.values(), key=lambda x: x["mencoes"], reverse=True)
    try:
        with open(caminho_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["dominio", "nome_inferido", "mencoes", "ultima_data"])
            w.writeheader()
            w.writerows(ordenado)
    except Exception:
        pass


def _nome_inferido(dom: str) -> str:
    """Nome legível aproximado a partir do domínio (ex.: institutox.org.br)."""
    base = dom.split(".")[0].replace("-", " ")
    return base.title()
