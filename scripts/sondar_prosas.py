#!/usr/bin/env python3
"""SONDA do Prosas (6ª) — navegador de verdade (Playwright), só diagnóstico.

5 sondas por HTML/JS não acharam o endereço da lista: a página Next.js monta a
busca em módulos espalhados. Aqui um Chromium sem tela abre a listagem como uma
pessoa abriria, e ANOTA cada resposta JSON que a página recebe — o endereço da
lista aparece de um jeito ou de outro. Imprime também o texto dos cards que a
página exibiu. Uma visita só (o robots.txt pede Crawl-Delay de 30 s).
"""
from __future__ import annotations

import json

from playwright.sync_api import sync_playwright

URL = "https://prosas.com.br/editais?format=json"

with sync_playwright() as p:
    nav = p.chromium.launch()
    pg = nav.new_page(locale="pt-BR", user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"))
    respostas = []

    def anota(resp):
        ct = resp.headers.get("content-type", "")
        if "json" in ct and resp.request.resource_type in ("xhr", "fetch"):
            try:
                corpo = resp.text()
            except Exception:
                corpo = ""
            respostas.append((resp.request.method, resp.url, resp.status, len(corpo), corpo[:1500]))

    pg.on("response", anota)
    pg.goto(URL, wait_until="networkidle", timeout=90_000)
    pg.wait_for_timeout(8000)
    print("== título:", pg.title(), "| url:", pg.url)
    print(f"== {len(respostas)} respostas JSON (xhr/fetch)")
    for metodo, url, st, n, corpo in respostas:
        print(f"-- {metodo} {st} {n}B {url}")
        print("   ", corpo.replace("\n", " ")[:1500])
    texto = pg.inner_text("body")
    print("== texto da página (3000 chars)")
    print(texto[:3000])
    links = pg.eval_on_selector_all("a[href]", "els => els.map(e => [e.innerText.trim().slice(0,80), e.href])")
    print("== links com 'edita'")
    for t, h in [x for x in links if "edita" in x[1].lower()][:25]:
        print("   ", json.dumps([t, h], ensure_ascii=False))
    nav.close()
