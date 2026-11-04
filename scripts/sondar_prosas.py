#!/usr/bin/env python3
"""SONDA do Prosas (5ª) — só diagnóstico, não grava nada.

4ª sonda: a listagem (Next.js) carrega o componente <prosas-listagem-editais>
do front-sdk (cdn.prosas.com.br), que busca os editais sozinho. Falta o ENDEREÇO
dessa busca. Esta sonda mostra o código em volta de fetch/axios/baseURL no
script da página /editais e no front-sdk, e lê /api/public/env.json (onde o app
antigo guardava configuração). Pausa de 30 s entre pedidos (Crawl-Delay 30).
"""
from __future__ import annotations

import re
import sys
import time

import requests

sys.path.insert(0, ".")
from radar.fontes_genericas import HEADERS  # noqa: E402

PAUSA = 30
PISTAS = ["fetch(", "axios", "baseURL", "apiUrl", "api_url", "API_URL", "/editais", "editais?",
          "listagem", "graphql", "/v1/", "/v2/", "endpoint"]


def pega(url, **kw):
    r = requests.get(url, headers={**HEADERS, **kw}, timeout=40)
    print(f"-- {url} -> {r.status_code} bytes={len(r.content)} ct={r.headers.get('content-type', '')[:40]}")
    return r


def contextos(texto, rotulo, por_pista=3):
    for p in PISTAS:
        for m in list(re.finditer(re.escape(p), texto))[:por_pista]:
            trecho = re.sub(r"\s+", " ", texto[max(0, m.start() - 250): m.end() + 350])
            print(f"   [{rotulo} | {p}] {trecho}")


r = pega("https://prosas.com.br/editais?format=json")
chunk = re.search(r'src="(/_next/static/chunks/pages/editais-[^"]+\.js)"', r.text)
if chunk:
    time.sleep(PAUSA)
    contextos(pega("https://prosas.com.br" + chunk.group(1)).text, "pages/editais")
time.sleep(PAUSA)
contextos(pega("https://cdn.prosas.com.br/front-sdk/prod/latest/webcomponents.bundle.js").text,
          "front-sdk", por_pista=4)
time.sleep(PAUSA)
env = pega("https://prosas.com.br/api/public/env.json", Accept="application/json")
print("   env.json:", env.text[:1500])
