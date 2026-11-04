#!/usr/bin/env python3
"""SONDA do Prosas (4ª) — só diagnóstico, não grava nada.

3ª sonda: https://prosas.com.br/editais redireciona para o site de marketing
(produtos.prosas.com.br), mas /editais?format=json devolveu a LISTAGEM em Next.js
(120 KB, "Prosas | Listagem de editais"). Esta sonda abre a listagem por esse
caminho, procura os dados embutidos e as APIs nos scripts dela e no pacote de
componentes do front novo (cdn.prosas.com.br/front-sdk). Pausa de 30 s entre
pedidos (robots.txt: Crawl-Delay 30).
"""
from __future__ import annotations

import json
import re
import sys
import time

import requests

sys.path.insert(0, ".")
from radar.fontes_genericas import HEADERS  # noqa: E402

PAUSA = 30
ACHADOS = set()


def pega(url):
    r = requests.get(url, headers=HEADERS, timeout=40, allow_redirects=True)
    print(f"-- {url} -> {r.status_code} final={r.url} bytes={len(r.content)}")
    return r


def caca_apis(texto, rotulo):
    novos = set(re.findall(r'["`\'](https?://[a-z0-9.-]*prosas[a-z0-9.-]*/[^"`\'\s]{0,90})["`\']', texto))
    novos |= set(re.findall(r'["`\'](/api/[^"`\'\s]{1,90})["`\']', texto))
    novos |= set(re.findall(r'["`\']([^"`\'\s]{0,50}edita[^"`\'\s]{0,60})["`\']', texto))
    print(f"   {rotulo}: {len(novos)} endereços")
    ACHADOS.update(novos)


r = pega("https://prosas.com.br/editais?format=json")
t = re.search(r"<title>(.*?)</title>", r.text, re.S)
print("   título:", t.group(1).strip() if t else None)
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
if m:
    d = json.loads(m.group(1))
    print("   __NEXT_DATA__ chaves:", list(d), "| page:", d.get("page"), "| buildId:", d.get("buildId"))
    print("   props:", json.dumps(d.get("props", {}), ensure_ascii=False)[:2500])
else:
    print("   sem __NEXT_DATA__; trecho:", re.sub(r"\s+", " ", r.text[:1500]))
caca_apis(r.text, "HTML da listagem")
scripts = re.findall(r'<script[^>]+src="([^"]+)"', r.text)
print("   scripts:", scripts[:20])
for s in [s for s in scripts if "/_next/static/" in s][:6]:
    time.sleep(PAUSA)
    u = s if s.startswith("http") else "https://prosas.com.br" + s
    caca_apis(pega(u).text, s[-60:])

time.sleep(PAUSA)
caca_apis(pega("https://cdn.prosas.com.br/front-sdk/prod/latest/webcomponents.bundle.js").text,
          "front-sdk webcomponents")

print("== endereços achados")
for a in sorted(ACHADOS)[:120]:
    print("   ", a)
