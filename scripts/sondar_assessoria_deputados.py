"""Sonda (só diagnóstico, NÃO grava nada): contatos de ASSESSORIA publicados
pelos próprios mandatos e pela ALESP. Extrai dos HTMLs os links mailto:, tel:,
wa.me e os e-mails (inclusive os ofuscados pelo Cloudflare).
Roda pela "Sonda Fiscal" com alvo=assessoria_deputados.
"""
import html as _html
import re

import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
PAGINAS = [
    "https://danilobalas.com.br/", "https://danilobalas.com.br/contato/",
    "https://rogerionogueira.com.br/", "https://rogerionogueira.com.br/contato/",
    "https://capitaotelhada.com.br/",
    "https://pretas.org/", "https://pretas.org/emendas-ambiental-2026/",
    "https://monicaseixas.com.br/", "https://www.monicaseixas.com.br/contato/",
    "https://valdomirolopes.com.br/", "https://www.valdomirolopes.com.br/contato/",
    "https://rodrigomoraes.com.br/", "https://deputadorodrigomoraes.com.br/",
    "https://www.al.sp.gov.br/deputado/contato/",
] + [f"https://www.al.sp.gov.br/servidor/lista/?idUA={u}" for u in (20374, 20451, 20455, 20452, 20427, 20434)]
ALVOS = re.compile(r"(?i)valdomiro|seixas|pretas|balas|rodrigo moraes|rio nogueira|telhada")


def cf(hexa):
    try:
        b = bytes.fromhex(hexa)
        return "".join(chr(x ^ b[0]) for x in b[1:])
    except ValueError:
        return ""


def texto(h):
    t = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", h)
    return " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", t)).split())


for url in PAGINAS:
    print("\n" + "=" * 70 + f"\n{url}")
    try:
        r = requests.get(url, headers=UA, timeout=40)
    except Exception as e:  # noqa: BLE001
        print(f"   ERRO {type(e).__name__}: {str(e)[:120]}")
        continue
    r.encoding = r.apparent_encoding or r.encoding
    h = r.text
    t = texto(h)
    print(f"   HTTP {r.status_code} · {len(t)} caracteres · final: {r.url}")
    if r.status_code != 200:
        continue
    achados = set()
    for m in re.findall(r'(?i)href="(mailto:[^"]+|tel:[^"]+|https?://(?:wa\.me|api\.whatsapp\.com|web\.whatsapp\.com)[^"]+)"', h):
        achados.add(_html.unescape(m)[:160])
    for m in re.findall(r'data-cfemail="([0-9a-f]+)"', h):
        achados.add("cloudflare-email: " + cf(m))
    for m in re.findall(r"/cdn-cgi/l/email-protection#([0-9a-f]+)", h):
        achados.add("cloudflare-email: " + cf(m))
    if "al.sp.gov.br/deputado/contato" in url:
        # lista geral: mostra só o trecho de cada um dos seis
        for m in ALVOS.finditer(t):
            print("   ·", t[max(0, m.start() - 10): m.end() + 190])
        continue
    for m in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}", t):
        achados.add("e-mail no texto: " + m)
    for a in sorted(achados):
        print("   ·", a)
    for m in re.finditer(r"(?i)assessor|imprensa|agenda|emenda", t):
        print("   ~", t[max(0, m.start() - 90): m.end() + 160])
        break
    if "servidor/lista" in url:
        i = t.find("Lotação")
        print("   amostra:", t[max(0, i): i + 700])
