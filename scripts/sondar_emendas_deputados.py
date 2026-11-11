"""Sonda (só diagnóstico, NÃO grava nada): emendas linha a linha de alguns
deputados estaduais + ficha oficial da ALESP (sala, andar, base eleitoral) e
servidores lotados no gabinete (dados abertos da ALESP).

Roda pela "Sonda Fiscal" com alvo=emendas_deputados. Os nomes vêm da variável
ALVOS (separados por ';'); sem ela, usa a lista padrão abaixo.
"""
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import emendas  # noqa: E402

PADRAO = "Valdomiro Lopes;Monica Seixas;Danilo Balas;Rodrigo Moraes;Rogério Nogueira;Capitão Telhada"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/126 Safari/537.36"}


def n(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).lower().split())


alvos = [a.strip() for a in os.environ.get("ALVOS", PADRAO).split(";") if a.strip()]
chaves = {a: n(a) for a in alvos}


def e_alvo(nome):
    x = n(nome)
    for a, k in chaves.items():
        if k in x:
            return a
    return None


# ------------------------------------------------------------------ emendas
print("=" * 70, "\nEMENDAS (Transparência SP, painéis 2023-2025)\n" + "=" * 70)
por = {a: [] for a in alvos}
for ano in (2023, 2024, 2025):
    try:
        linhas = emendas.linhas_da_api(ano)
    except Exception as e:  # noqa: BLE001
        print(f"[{ano}] FALHOU: {type(e).__name__}: {str(e)[:200]}")
        continue
    print(f"[{ano}] {len(linhas)} linhas")
    for l in linhas:
        a = e_alvo(l["parlamentar"])
        if a:
            por[a].append(l)

for a, ls in por.items():
    print(f"\n##### {a}: {len(ls)} emendas no total")
    nomes = sorted({l["parlamentar"] for l in ls})
    print("nomes no painel:", nomes)
    for l in ls:
        te = emendas._e_transferencia_especial(l["objeto"])
        l["area"] = emendas.classificar_area(l["orgao"], te)
    for area in ("educação", "assistência social", "saúde", "outra", "transferência especial"):
        sub = [l for l in ls if l["area"] == area]
        pago = sum(l["valor"] for l in sub if n(l["estagio"]) == "pagas")
        print(f"  {area:22} n={len(sub):3}  autorizado={sum(l['valor'] for l in sub):>13,.2f}  pago={pago:>13,.2f}")
    print("  -- 8 MAIORES (qualquer área):")
    for l in sorted(ls, key=lambda x: -x["valor"])[:8]:
        print(f"     {l['valor']:>12,.2f} | {l['ano']} | {l['area'][:12]:12} | {l['municipio'][:22]:22} | "
              f"{l['estagio'][:12]:12} | {l['orgao'][:18]:18} | {l['objeto'][:110]}")
    print("  -- TODAS de EDUCAÇÃO e ASSISTÊNCIA SOCIAL:")
    for l in sorted((x for x in ls if x["area"] in emendas.AREAS_PFC), key=lambda x: -x["valor"]):
        print(f"     {l['valor']:>12,.2f} | {l['ano']} | {l['area'][:9]:9} | {l['municipio'][:22]:22} | "
              f"{l['estagio'][:12]:12} | {l['objeto'][:140]}")

# ------------------------------------------------------------------ ALESP
print("\n" + "=" * 70, "\nALESP — ficha oficial (dados abertos)\n" + "=" * 70)


def baixar(url):
    try:
        r = requests.get(url, headers=UA, timeout=90)
        print(f"   {r.status_code} {len(r.content):>9} bytes  {url}")
        return r.content if r.status_code == 200 else None
    except Exception as e:  # noqa: BLE001
        print(f"   ERRO {type(e).__name__}: {str(e)[:120]}  {url}")
        return None


def folhas(el):
    return {c.tag: (c.text or "").strip() for c in el if len(c) == 0 and (c.text or "").strip()}


base = "https://www.al.sp.gov.br/repositorioDados/"
xml = baixar(base + "deputados/deputados.xml")
matriculas = {}
if xml:
    raiz = ET.fromstring(xml)
    for dep in raiz.iter("Deputado"):
        f = folhas(dep)
        a = e_alvo(f.get("NomeParlamentar", ""))
        if not a:
            continue
        matriculas[a] = f.get("Matricula", "")
        print(f"\n##### {a}")
        for k, v in f.items():
            if k != "Biografia":
                print(f"   {k}: {v[:300]}")
        for sub in dep:
            if len(sub):
                itens = [" / ".join(folhas(x).values()) or (x.text or "").strip() for x in sub]
                print(f"   {sub.tag}: {'; '.join(i for i in itens if i)[:600]}")
        bio = re.sub(r"<[^>]+>", " ", f.get("Biografia", ""))
        print(f"   Biografia: {' '.join(bio.split())[:1500]}")

for nome_arq in ("deputados/deputado_area_atuacao.xml", "deputados/deputado_base_eleitoral.xml",
                 "deputados/areas_atuacao.xml", "deputados/bases_eleitorais.xml"):
    x = baixar(base + nome_arq)
    if x:
        print("   amostra:", re.sub(r"\s+", " ", x[:600].decode("utf-8", "replace")))

print("\n-- Servidores lotados nos gabinetes (dados abertos da administração)")
for nome_arq in ("administracao/funcionarios_lotacoes.xml", "administracao/lotacoes.xml",
                 "administracao/funcionarios_cargos.xml", "administracao/funcionarios.xml"):
    x = baixar(base + nome_arq)
    if not x:
        continue
    try:
        raiz = ET.fromstring(x)
    except ET.ParseError as e:
        print("   XML inválido:", e)
        continue
    filhos = list(raiz)
    print(f"   {len(filhos)} registros; campos: {[c.tag for c in filhos[0]] if filhos else []}")
    achados = {a: [] for a in alvos}
    for reg in filhos:
        f = folhas(reg)
        texto = n(" ".join(f.values()))
        if "gab" not in texto and "dep" not in texto:
            continue
        for a, k in chaves.items():
            # o gabinete vem como "GABINETE DEP. FULANO": casa pelo último sobrenome também
            if k in texto or (len(k.split()) > 1 and "gab" in texto and k.split()[-1] in texto.split()):
                achados[a].append(f)
    for a, regs in achados.items():
        print(f"\n   ##### {a}: {len(regs)} registros")
        for f in regs[:60]:
            print("      ", " | ".join(f"{k}={v}" for k, v in f.items())[:260])

print("\n-- Página pública de cada deputado")
for a, mat in matriculas.items():
    h = baixar(f"https://www.al.sp.gov.br/deputado/?matricula={mat}")
    if h:
        t = re.sub(r"(?is)<(script|style).*?</\1>", " ", h.decode("utf-8", "replace"))
        t = " ".join(re.sub(r"<[^>]+>", " ", t).split())
        i = t.find("Sala")
        print(f"   [{a}] {t[max(0, i - 300): i + 900]}")
