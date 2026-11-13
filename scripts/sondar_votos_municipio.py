"""Sonda (só diagnóstico, NÃO grava nada): votação de DEPUTADO ESTADUAL por
município nas cidades do PFC, lida do sistema de divulgação de resultados do
TSE (resultados.tse.jus.br — outro servidor, não o CDN de dados abertos que
recusa o robô). Imprime linhas "CSV|municipio|cod_tse|numero|nome|votos".
Roda pela "Sonda Fiscal" com alvo=votos_municipio.
"""
import json
import os
import sys
import unicodedata

import requests

BASE = "https://resultados.tse.jus.br/oficial"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
      "Accept": "application/json, text/plain, */*", "Referer": "https://resultados.tse.jus.br/"}
PFC = ["Capela do Alto", "Cesário Lange", "Corumbataí", "Guareí", "Iperó", "Juquiá", "Mirassol",
       "Rio Claro", "Salto", "São Roque", "Tatuí",
       # sede do PFC + cidades que podem entrar em 2027 (pedido de nov/2026)
       "Sorocaba", "Mairinque", "Tietê"]
CARGO = os.environ.get("CARGO", "0007")   # 0007 = deputado estadual


def n(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).lower().split())


def pega(url, mostra=True):
    try:
        r = requests.get(url, headers=UA, timeout=60)
    except Exception as e:  # noqa: BLE001
        print(f"   ERRO {type(e).__name__}: {str(e)[:120]} {url}")
        return None
    if mostra:
        print(f"   {r.status_code} {len(r.content):>8} bytes {url}")
    if r.status_code != 200:
        return None
    try:
        return r.json()
    except ValueError:
        try:
            return json.loads(r.content.decode("utf-8-sig"))
        except ValueError:
            print("   (não é JSON):", r.text[:200])
            return None


def candidatos(no, achados):
    """Varre o JSON atrás de qualquer objeto com número de candidato + votos."""
    if isinstance(no, dict):
        if "n" in no and ("vap" in no or "v" in no):
            num = str(no.get("n"))
            votos = no.get("vap", no.get("v"))
            try:
                votos = int(str(votos).replace(".", ""))
            except ValueError:
                votos = None
            if votos is not None:
                achados[num] = (no.get("nmu") or no.get("nm") or "", votos)
        for v in no.values():
            candidatos(v, achados)
    elif isinstance(no, list):
        for v in no:
            candidatos(v, achados)


print("== 1. Eleições publicadas")
cfg = pega(f"{BASE}/comum/config/ele-c.json")
if not cfg:
    sys.exit("sem configuração: o servidor de resultados não respondeu")
print(json.dumps(cfg, ensure_ascii=False)[:2500])

# ciclos/eleições: procura qualquer dict com 'cd' + 'nm' dentro da config
ciclo = str(cfg.get("c") or "")
eleicoes = []


def acha_eleicoes(no):
    if isinstance(no, dict):
        if "cd" in no and "nm" in no and ("tp" in no or "t" in no or "cdt2" in no):
            eleicoes.append(no)
        for v in no.values():
            acha_eleicoes(v)
    elif isinstance(no, list):
        for v in no:
            acha_eleicoes(v)


acha_eleicoes(cfg)
print(f"\nciclo: {ciclo!r} · eleições:", [(e.get("cd"), e.get("nm"), e.get("t") or e.get("tp")) for e in eleicoes])
forcada = os.environ.get("ELEICAO")
codigos = [forcada] if forcada else [str(e["cd"]) for e in eleicoes]
ciclos = [os.environ.get("CICLO")] if os.environ.get("CICLO") else [ciclo, "ele2026"]

ok = None
for cic in dict.fromkeys(c for c in ciclos if c):
    for cd in codigos:
        e6 = f"{int(cd):06d}"
        print(f"\n== 2. Municípios · ciclo {cic} · eleição {cd}")
        mun = pega(f"{BASE}/{cic}/{cd}/config/mun-e{e6}-cm.json")
        if not mun:
            continue
        sp = None
        for uf in mun.get("abr", []):
            if str(uf.get("cd", "")).upper() == "SP":
                sp = uf
        if not sp:
            print("   sem SP nesta eleição; UFs:", [u.get("cd") for u in mun.get("abr", [])][:30])
            continue
        cods = {n(m.get("nm")): str(m.get("cd")) for m in sp.get("mu", [])}
        alvo = {c: cods.get(n(c)) for c in PFC}
        print("   códigos TSE:", alvo)
        primeiro = next((v for v in alvo.values() if v), None)
        if not primeiro:
            continue
        print(f"\n== 3. Formato do arquivo por município (cargo {CARGO})")
        for padrao in ("dados/sp/sp{m}-c{c}-e{e}-u.json", "dados/sp/sp{m}-c{c}-e{e}-v.json",
                       "dados-simplificados/sp/sp{m}-c{c}-e{e}-r.json", "dados/sp/sp{m}-c{c}-e{e}-a.json"):
            url = f"{BASE}/{cic}/{cd}/" + padrao.format(m=primeiro, c=CARGO, e=e6)
            j = pega(url)
            if j:
                a = {}
                candidatos(j, a)
                print(f"   -> {len(a)} candidatos com voto neste arquivo; chaves do topo: {list(j)[:25]}")
                print("   amostra:", json.dumps(j, ensure_ascii=False)[:900])
                if a and not ok:
                    ok = (cic, cd, e6, padrao, alvo)
        if ok:
            break
    if ok:
        break

if not ok:
    sys.exit("\nNENHUM formato devolveu votos por município — ver as respostas acima")

cic, cd, e6, padrao, alvo = ok
print(f"\n== 4. Votos por município · {cic}/{cd} · {padrao}")
for cidade, cod in alvo.items():
    if not cod:
        print(f"SEM_CODIGO|{cidade}")
        continue
    j = pega(f"{BASE}/{cic}/{cd}/" + padrao.format(m=cod, c=CARGO, e=e6), mostra=False)
    if not j:
        print(f"FALHOU|{cidade}|{cod}")
        continue
    a = {}
    candidatos(j, a)
    topo = {k: v for k, v in j.items() if not isinstance(v, (list, dict))}
    print(f"MUN|{cidade}|{cod}|{len(a)} candidatos|{json.dumps(topo, ensure_ascii=False)[:600]}")
    for num, (nome, votos) in sorted(a.items(), key=lambda x: -x[1][1]):
        if votos > 0:
            print(f"CSV|{cidade}|{cod}|{num}|{nome}|{votos}")
print("\nFIM")
