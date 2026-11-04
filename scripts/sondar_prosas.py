#!/usr/bin/env python3
"""SONDA do Prosas — só diagnóstico, não grava nada.

O Prosas (prosas.com.br, maior agregador de editais para OSC) é um site em
AngularJS: o HTML de /editais/ só tem o molde ({{ 'editais' | translate }}), e
os editais chegam depois, por JavaScript, de alguma API. Esta sonda procura um
caminho legível por robô:
  1. robots.txt e sitemap(s): a lista de páginas que o site dá ao Google;
  2. se as páginas de edital do sitemap vêm com título/texto no HTML;
  3. endereços de API citados no HTML e nos arquivos .js do app;
  4. alguns endereços de API prováveis.
"""
from __future__ import annotations

import re
import sys
from urllib.parse import urljoin

import requests

sys.path.insert(0, ".")
from radar.fontes_genericas import HEADERS  # noqa: E402

BASE = "https://prosas.com.br"


def get(url, **kw):
    try:
        return requests.get(url, headers={**HEADERS, **kw.pop("headers", {})}, timeout=25, **kw)
    except Exception as e:
        print(f"  ERRO {url}: {type(e).__name__}: {str(e)[:100]}")
        return None


def mostra(rotulo, r, n=300):
    if r is None:
        return
    ct = r.headers.get("content-type", "")
    print(f"  {rotulo}: {r.status_code} {ct[:40]} bytes={len(r.content)} final={r.url[:90]}")
    print("    " + r.text[:n].replace("\n", " ") + ("…" if len(r.text) > n else ""))


print("== 1. robots.txt")
r = get(BASE + "/robots.txt")
mostra("robots", r, 800)
sitemaps = re.findall(r"(?im)^sitemap:\s*(\S+)", r.text) if r is not None and r.ok else []
sitemaps = sitemaps or [BASE + "/sitemap.xml", BASE + "/sitemap_index.xml"]

print("== 2. sitemaps")
urls_edital = []
for sm in sitemaps[:6]:
    r = get(sm)
    mostra(sm, r, 400)
    if r is not None and r.ok:
        locs = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", r.text)
        print(f"    {len(locs)} <loc>; com 'edital': {sum('edital' in l for l in locs)}")
        for l in locs[:5]:
            print("     ", l)
        urls_edital += [l for l in locs if "edital" in l.lower()]
        for sub in [l for l in locs if l.endswith(".xml")][:4]:
            r2 = get(sub)
            if r2 is not None and r2.ok:
                l2 = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", r2.text)
                ed = [l for l in l2 if "edital" in l.lower()]
                print(f"    sub {sub}: {len(l2)} locs, {len(ed)} com edital; ex: {ed[:3]}")
                urls_edital += ed

print(f"== 3. páginas de edital ({len(urls_edital)} achadas); lendo 3")
for u in urls_edital[:3]:
    r = get(u)
    if r is None:
        continue
    t = re.search(r"<title>(.*?)</title>", r.text, re.S)
    og = re.findall(r'<meta[^>]+property="og:(title|description)"[^>]+content="([^"]*)"', r.text)
    print(f"  {r.status_code} {u[:90]} title={t.group(1).strip()[:90] if t else None} og={og[:2]}")
    print("    tem {{ }} (molde):", "{{" in r.text, "| ld+json:", "ld+json" in r.text)

print("== 4. APIs citadas no HTML e nos .js")
r = get(BASE + "/editais/")
apis = set()
if r is not None and r.ok:
    scripts = re.findall(r'<script[^>]+src="([^"]+)"', r.text)
    print("  scripts:", scripts[:12])
    apis |= set(re.findall(r'["\'](/?(?:api|v\d)/[^"\'\s]{2,80})["\']', r.text))
    apis |= set(re.findall(r'https?://[a-z0-9.-]*prosas[a-z0-9.-]*/[^"\'\s<>]{0,80}', r.text))
    for s in scripts[:8]:
        js = get(urljoin(BASE, s))
        if js is not None and js.ok and len(js.text) < 8_000_000:
            achados = set(re.findall(r'["\'](/?(?:api|v\d)/[^"\'\s]{2,80})["\']', js.text))
            achados |= set(re.findall(r'["\']([^"\']*edita[^"\']{0,60})["\']', js.text))
            achados |= set(re.findall(r'https?://[a-z0-9.-]*prosas[a-z0-9.-]*/[^"\'\s]{0,80}', js.text))
            print(f"  {s[:60]}: {len(js.text)} chars, {len(achados)} candidatos")
            apis |= achados
for a in sorted(apis)[:80]:
    print("   ", a)

print("== 5. endereços de API prováveis")
for caminho in ["/api/editais", "/api/v1/editais", "/api/v2/editais", "/editais.json",
                "/api/public/editais", "/api/editais?status=aberto", "/editais?format=json"]:
    mostra(caminho, get(BASE + caminho, headers={"Accept": "application/json"}), 200)
