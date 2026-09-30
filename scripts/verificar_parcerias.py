#!/usr/bin/env python3
"""Procura, no site de cada parceiro da base curada, o CANAL de doação/patrocínio.

POR QUE EXISTE: os 16 da base-semente vieram com `fonte = "curadoria inicial (a
confirmar)"` e obs "verificar canal de doação". São HIPÓTESES, não levantamento.
Este script transforma o que der em evidência rastreável — e deixa dito, com
todas as letras, o que não der.

O QUE ELE PODE E O QUE NÃO PODE AFIRMAR
  PODE: "existe no site uma página institucional de doação/patrocínio/edital,
        e aqui está a URL e o trecho que a identifica".
  NÃO PODE: "a empresa tem programa aberto agora", "aceita este tipo de
        projeto", "este é o canal certo para o PFC". Página institucional é
        indício de canal, nunca prova de programa vigente — é o mesmo cuidado
        da regra 3 (data de edital): indício não vira afirmação.

Nada é inventado: site fora do ar, ou sem nada encontrável, vira
status "não encontrado" — que é resposta legítima (regra 5c).

Roda no GitHub Actions (rede livre):
    python scripts/verificar_parcerias.py
"""
import csv
import datetime
import os
import re
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from radar.fontes_genericas import pegar_soup, limpar_texto  # noqa: E402
from src import parcerias  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(BASE, "data", "parcerias_verificacao.csv")
COLUNAS = ["nome", "site", "status", "tipo_canal", "canal_url", "canal_titulo",
           "evidencia", "verificado_em"]

# Termos que identificam um canal, em ordem de FORÇA: um "edital aberto" vale
# mais que uma página genérica de sustentabilidade.
CANAIS = [
    ("edital", ("edital", "editais", "chamada publica", "chamada de projetos",
                "inscricoes abertas", "submissao de projetos")),
    ("doação", ("doacao", "doacoes", "doe ", "como doar", "quero doar",
                "faca uma doacao")),
    ("patrocínio", ("patrocinio", "patrocinios", "seja um patrocinador",
                    "apoio a projetos", "apoie um projeto", "parceria",
                    "seja um parceiro", "proponha seu projeto")),
    ("institucional", ("responsabilidade social", "sustentabilidade",
                       "investimento social", "impacto social", "instituto",
                       "fundacao", "esg")),
]
# Nunca confundir com canal: são páginas de venda/atendimento.
RUIDO = ("carrinho", "produto", "loja", "comprar", "trabalhe conosco", "vagas",
         "politica de privacidade", "fale conosco", "sac")


def _norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()


def _classificar(texto: str) -> tuple[str, str] | None:
    """(tipo_canal, termo) do termo mais FORTE presente. None se nenhum."""
    t = _norm(texto)
    if any(r in t for r in RUIDO):
        return None
    for tipo, termos in CANAIS:
        for termo in termos:
            if termo in t:
                return tipo, termo.strip()
    return None


def candidatos(soup, site: str) -> list[dict]:
    """Links da home que parecem canal, do mais forte para o mais fraco."""
    forca = {tipo: i for i, (tipo, _) in enumerate(CANAIS)}
    achados = {}
    for a in soup.find_all("a", href=True):
        rotulo = limpar_texto(a.get_text())
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        clas = _classificar(f"{rotulo} {href}")
        if not clas:
            continue
        url = urllib.parse.urljoin(site, href)
        if url not in achados:
            achados[url] = {"tipo": clas[0], "termo": clas[1],
                            "titulo": rotulo[:90] or clas[1], "url": url}
    return sorted(achados.values(), key=lambda x: forca.get(x["tipo"], 9))


def evidencia_da_pagina(url: str) -> str:
    """Trecho curto da página do canal, para o Fábio julgar sem abrir o link."""
    soup = pegar_soup(url)
    if soup is None:
        return ""
    for tag in soup.find_all(["h1", "h2", "p"]):
        txt = limpar_texto(tag.get_text())
        if len(txt) > 50 and _classificar(txt):
            return txt[:220]
    titulo = soup.find("title")
    return limpar_texto(titulo.get_text())[:220] if titulo else ""


def verificar(p: dict) -> dict:
    nome, site = p.get("nome", ""), str(p.get("site", "")).strip()
    hoje = datetime.date.today().isoformat()
    linha = {"nome": nome, "site": site, "status": "não encontrado",
             "tipo_canal": "", "canal_url": "", "canal_titulo": "",
             "evidencia": "", "verificado_em": hoje}
    if not site:
        linha["status"] = "sem site na base"
        return linha
    soup = pegar_soup(site)
    if soup is None:
        linha["status"] = "site não respondeu"
        return linha
    achados = candidatos(soup, site)
    if not achados:
        return linha                      # respondeu, mas nada encontrável
    melhor = achados[0]
    linha.update({"status": "canal encontrado", "tipo_canal": melhor["tipo"],
                  "canal_url": melhor["url"], "canal_titulo": melhor["titulo"],
                  "evidencia": evidencia_da_pagina(melhor["url"])})
    return linha


def main() -> int:
    base = parcerias.carregar_parcerias()
    if not base:
        print("! base-semente vazia — nada a verificar.")
        return 1
    print(f"== Verificando canal de doação/patrocínio · {len(base)} parceiros ==")

    linhas = []
    for i, p in enumerate(base, 1):
        linha = verificar(p)
        linhas.append(linha)
        marca = {"canal encontrado": "ok ", "não encontrado": "-- ",
                 "site não respondeu": "!! ", "sem site na base": "?? "}
        print(f"  {marca.get(linha['status'], '   ')}{linha['nome'][:26]:26} "
              f"{linha['status']:20} {linha['tipo_canal'][:12]:12} "
              f"{linha['canal_url'][:58]}")
        time.sleep(1.0)                   # educado com os sites
        if i % 8 == 0:
            print(f"    {i}/{len(base)}…")

    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(linhas)

    achou = sum(1 for l in linhas if l["status"] == "canal encontrado")
    print(f"\n{len(linhas)} verificados -> {SAIDA}")
    print(f"  canal encontrado: {achou} · sem canal encontrável: {len(linhas)-achou}")
    por_tipo = {}
    for l in linhas:
        if l["tipo_canal"]:
            por_tipo[l["tipo_canal"]] = por_tipo.get(l["tipo_canal"], 0) + 1
    if por_tipo:
        print(f"  por tipo: {por_tipo}")
    print("  LEMBRETE: canal encontrado = existe página institucional. NÃO "
          "significa programa aberto agora.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
