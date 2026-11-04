#!/usr/bin/env python3
"""SONDA do Prosas (3ª) — só diagnóstico, não grava nada.

1ª e 2ª sondas (nov/2026): o /editais.json do app antigo (AngularJS) foi
desligado ("sumiu"), mas https://prosas.com.br/editais (SEM barra) é uma página
NOVA em Next.js ("Prosas | Listagem de editais"). Páginas Next.js costumam trazer
os dados embutidos num <script id="__NEXT_DATA__">. Esta sonda abre a página,
mostra a estrutura desse JSON e as chamadas de API citadas nos scripts dela.
Respeita a pausa de 30 s do robots.txt (Crawl-Delay: 30).
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


def resumo(obj, prof=0, chave="raiz"):
    """Esqueleto do JSON: chaves, tamanhos de lista e um exemplo de folha."""
    pre = "  " * prof
    if prof > 6:
        return
    if isinstance(obj, dict):
        print(f"{pre}{chave}: {{{len(obj)} chaves}}")
        for k, v in list(obj.items())[:25]:
            resumo(v, prof + 1, k)
    elif isinstance(obj, list):
        print(f"{pre}{chave}: [lista de {len(obj)}]")
        if obj:
            resumo(obj[0], prof + 1, "[0]")
    else:
        print(f"{pre}{chave} = {str(obj)[:90]!r}")


r = requests.get(BASE + "/editais", headers=HEADERS, timeout=30)
print("status", r.status_code, "bytes", len(r.content), "final", r.url)
m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text, re.S)
if m:
    dados = json.loads(m.group(1))
    print("== __NEXT_DATA__")
    resumo(dados)
    print("== amostra props (2000 chars)")
    print(json.dumps(dados.get("props", {}), ensure_ascii=False)[:2000])
else:
    print("sem __NEXT_DATA__")
print("== scripts da página")
scripts = re.findall(r'<script[^>]+src="([^"]+)"', r.text)
for s in scripts:
    print("   ", s)
apis = set()
for s in [s for s in scripts if "/_next/static/" in s and ("pages/editais" in s or "_app" in s)][:4]:
    time.sleep(30)
    js = requests.get(s if s.startswith("http") else BASE + s, headers=HEADERS, timeout=30).text
    apis |= set(re.findall(r'["`](https?://[^"`\s]*prosas[^"`\s]{0,80})["`]', js))
    apis |= set(re.findall(r'["`](/api/[^"`\s]{1,80})["`]', js))
    apis |= set(re.findall(r'["`]([^"`\s]{0,40}edita[^"`\s]{0,60})["`]', js))
print("== APIs/endereços nos scripts da página nova")
for a in sorted(apis)[:80]:
    print("   ", a)
