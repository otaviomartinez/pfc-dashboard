#!/usr/bin/env python3
"""SONDA do Prosas (2ª) — só diagnóstico, não grava nada.

1ª sonda (nov/2026): sem sitemap; o app AngularJS busca os editais por $http
num serviço com `find: function(params, meus_editais, cb)` e cita
"/editais/:id.json". Esta sonda mostra o CÓDIGO em volta dessas pistas (para
achar o endereço da LISTA) e testa os candidatos, com a pausa de 30 s que o
robots.txt do Prosas pede (Crawl-Delay: 30).
"""
from __future__ import annotations

import json
import re
import sys
import time

import requests

sys.path.insert(0, ".")
from radar.fontes_genericas import HEADERS  # noqa: E402

BASE = "https://prosas.com.br"
PAUSA = 30


def get(url, **kw):
    try:
        return requests.get(url, headers={**HEADERS, "Accept": "application/json, text/plain, */*"},
                            timeout=30, **kw)
    except Exception as e:
        print(f"  ERRO {url}: {type(e).__name__}: {str(e)[:100]}")
        return None


r = get(BASE + "/editais/")
js_url = re.findall(r'<script[^>]+src="(https://prosas\.com\.br/assets/application-[^"]+\.js)"', r.text)[0]
time.sleep(PAUSA)
js = get(js_url).text
print("== trechos do app em volta das pistas")
for pista in ["meus_editais", "lista_reserva", "/editais/:id.json", "editais.json", "'/editais",
              '"/editais', "editais_abertos", "oportunidades/", "/api/selecao", "privates/", "publics/"]:
    for m in list(re.finditer(re.escape(pista), js))[:3]:
        trecho = js[max(0, m.start() - 500): m.end() + 700].replace("\n", " ")
        print(f"--- [{pista}] @{m.start()}")
        print(re.sub(r"\s+", " ", trecho))
print("== endereços com 'edita' citados no app")
for u in sorted(set(re.findall(r"""["'](/[^"'\s]*edita[^"'\s]*)["']""", js)))[:60]:
    print("   ", u)

print("== testes de candidatos (pausa de 30 s entre pedidos)")
candidatos = ["/editais.json", "/editais/abertos.json", "/api/selecao/v2/publics/editais",
              "/api/selecao/v2/publics/oportunidades", "/oportunidades.json", "/editais?format=json"]
for c in candidatos:
    time.sleep(PAUSA)
    r = get(BASE + c)
    if r is None:
        continue
    corpo = r.text[:400].replace("\n", " ")
    print(f"  {c}: {r.status_code} {r.headers.get('content-type', '')[:40]} bytes={len(r.content)} :: {corpo}")
    if r.ok and r.text.lstrip()[:1] in "[{":
        try:
            d = r.json()
            amostra = d[:2] if isinstance(d, list) else {k: (v if not isinstance(v, list) else v[:2]) for k, v in list(d.items())[:8]}
            print("    JSON:", json.dumps(amostra, ensure_ascii=False)[:1500])
        except ValueError:
            pass
