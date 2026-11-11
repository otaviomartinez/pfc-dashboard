"""Sonda (só diagnóstico, NÃO grava nada): confere NA FONTE os contatos de
escritório divulgados nos sites dos mandatos e em notícias da ALESP.
Roda pela "Sonda Fiscal" com alvo=contatos_deputados.
"""
import re

import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
PAGINAS = [
    ("Balas site", "https://danilobalas.com.br/"),
    ("Balas contato", "https://danilobalas.com.br/contato/"),
    ("Balas ALESP escritório", "https://www.al.sp.gov.br/noticia/?id=457565"),
    ("Nogueira contato", "https://rogerionogueira.com.br/contato/"),
    ("Nogueira site", "https://rogerionogueira.com.br/"),
    ("Moraes ALESP escritório Itu", "https://www.al.sp.gov.br/noticia/?id=336316"),
    ("Telhada site", "https://capitaotelhada.com.br/"),
    ("Telhada contato", "https://capitaotelhada.com.br/contato/"),
    ("Pretas edital", "https://pretas.org/emendas-ambiental-2026/"),
    ("Pretas site", "https://pretas.org/"),
    ("Pretas contato", "https://pretas.org/contato/"),
    ("ALESP tel Valdomiro", "https://www.al.sp.gov.br/alesp/telefones/?idUA=20374"),
    ("ALESP tel Monica", "https://www.al.sp.gov.br/alesp/telefones/?idUA=20451"),
    ("ALESP tel Balas", "https://www.al.sp.gov.br/alesp/telefones/?idUA=20455"),
    ("ALESP tel Moraes", "https://www.al.sp.gov.br/alesp/telefones/?idUA=20452"),
    ("ALESP tel Nogueira", "https://www.al.sp.gov.br/alesp/telefones/?idUA=20427"),
    ("ALESP tel Telhada", "https://www.al.sp.gov.br/alesp/telefones/?idUA=20434"),
]
CHAVES = re.compile(
    r"(?i)(pra[çc]a|rua |avenida|av\.|cep[: ]|\(\d{2}\)\s?\d{4,5}[- ]?\d{4}|\b3886[- ]?\d{4}|whats|@[a-z0-9.-]+\.[a-z]{2,}|"
    r"inscri[çc][õo]es|edital|escrit[óo]rio|gabinete \d|sala[: ]|hor[áa]rio)")


def texto(html):
    t = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", html)
    return " ".join(re.sub(r"<[^>]+>", " ", t).replace("&nbsp;", " ").split())


for nome, url in PAGINAS:
    print("\n" + "=" * 70 + f"\n{nome}\n{url}")
    try:
        r = requests.get(url, headers=UA, timeout=40)
    except Exception as e:  # noqa: BLE001
        print(f"   ERRO {type(e).__name__}: {str(e)[:150]}")
        continue
    r.encoding = r.apparent_encoding or r.encoding
    t = texto(r.text)
    print(f"   HTTP {r.status_code} · {len(t)} caracteres de texto · final: {r.url}")
    vistos, n = set(), 0
    for m in CHAVES.finditer(t):
        trecho = t[max(0, m.start() - 110): m.end() + 150]
        chave = trecho[90:170]
        if chave in vistos:
            continue
        vistos.add(chave)
        print("   ·", trecho)
        n += 1
        if n >= 14:
            break
