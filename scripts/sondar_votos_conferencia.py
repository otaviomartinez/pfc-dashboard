"""Sonda (só diagnóstico, NÃO grava nada): CONFERE a leitura de votos por
município. (1) total estadual de cada candidato no arquivo do estado; (2) em
cada cidade do PFC, o bloco de totais do próprio TSE (votos nominais) contra a
soma dos candidatos; (3) os votos dos seis, lidos de novo.
Roda pela "Sonda Fiscal" com alvo=votos_conferencia.
"""
import json

import requests

BASE = "https://resultados.tse.jus.br/oficial/ele2026/6259/dados/sp"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/126 Safari/537.36",
      "Referer": "https://resultados.tse.jus.br/"}
CIDADES = {"Capela do Alto": "63070", "Cesário Lange": "63339", "Corumbataí": "63550", "Guareí": "64718",
           "Iperó": "65218", "Juquiá": "66230", "Mirassol": "67075", "Rio Claro": "69795", "Salto": "70050",
           "São Roque": "71137", "Tatuí": "71811"}
SEIS = ["40211", "50900", "22007", "22411", "55555", "11190"]


def cands(no, out):
    """Só candidato de verdade: objeto com 'n' de 5 dígitos, nome e 'vap'."""
    if isinstance(no, dict):
        if "vap" in no and len(str(no.get("n", ""))) == 5 and ("nm" in no or "nmu" in no):
            out[str(no["n"])] = (no.get("nmu") or no.get("nm"), int(no["vap"]), no.get("st") or no.get("dvt") or "")
        for v in no.values():
            cands(v, out)
    elif isinstance(no, list):
        for v in no:
            cands(v, out)


def pega(url):
    r = requests.get(url, headers=UA, timeout=90)
    print(f"   {r.status_code} {len(r.content):>9} bytes {url}")
    return r.json() if r.status_code == 200 else None


print("== 1. Arquivo do ESTADO")
j = pega(f"{BASE}/sp-c0007-e006259-u.json")
if j:
    a = {}
    cands(j, a)
    print("   carimbo:", j.get("dt"), j.get("ht"), "· totais:", json.dumps(j.get("v"), ensure_ascii=False)[:500],
          json.dumps(j.get("s"), ensure_ascii=False)[:300])
    for n in SEIS:
        print(f"UF|{n}|{a.get(n)}")

print("\n== 2. Cada cidade")
for cid, cod in CIDADES.items():
    j = pega(f"{BASE}/sp{cod}-c0007-e006259-u.json")
    if not j:
        print(f"FALHOU|{cid}")
        continue
    a = {}
    cands(j, a)
    print(f"TOT|{cid}|soma dos candidatos={sum(v for _, v, _ in a.values())}|candidatos={len(a)}|"
          f"carimbo={j.get('dt')} {j.get('ht')}|v={json.dumps(j.get('v'), ensure_ascii=False)[:420]}")
    print(f"SEIS|{cid}|" + "|".join(f"{n}={a.get(n, ('', 0, ''))[1]}" for n in SEIS))
    top = sorted(a.items(), key=lambda x: -x[1][1])[:4]
    print(f"TOP|{cid}|" + "|".join(f"{nm} {v}" for _, (nm, v, _) in top))
