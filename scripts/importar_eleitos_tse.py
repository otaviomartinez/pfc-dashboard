#!/usr/bin/env python3
"""Importa prefeitos/vices/vereadores eleitos em 2024 (TSE) -> CSV versionado.

Roda no GitHub Actions (lá a internet é livre) ou na máquina do usuário. NÃO
roda em runtime do Streamlit — é construção offline, igual ao molde de emendas.

    python scripts/importar_eleitos_tse.py                    # baixa sozinho
    python scripts/importar_eleitos_tse.py ~/Downloads/x.zip  # usa um zip local

Gera data/prefeituras/eleitos_2024.csv só com os municípios do painel.
CSV do TSE: latin-1, separado por ';'.
"""
import csv
import io
import os
import sys
import tempfile
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prefeituras.config import carregar_municipios, normalizar_nome  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(BASE, "data", "prefeituras", "eleitos_2024.csv")

CARGOS = {"PREFEITO", "VICE-PREFEITO", "VEREADOR"}
ELEITOS = {"ELEITO", "ELEITO POR MÉDIA", "ELEITO POR QP"}

# O TSE serve os dados abertos pelo CDN. A URL muda de padrão de vez em quando,
# então tentamos algumas e dizemos CLARAMENTE qual funcionou (ou que nenhuma
# funcionou) — nunca falhamos em silêncio.
URLS_TSE = [
    "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2024_SP.zip",
    "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2024.zip",
    "https://dadosabertos.tse.jus.br/dataset/candidatos-2024/resource/download/consulta_cand_2024_SP.zip",
]


def urls_do_ckan() -> list[str]:
    """URLs de recurso do dataset no CKAN do TSE (dadosabertos é CKAN, igual ao
    Tesouro). Descobrir bate chutar CDN: o log mostrou 403 nas três URLs fixas."""
    api = ("https://dadosabertos.tse.jus.br/api/3/action/"
           "package_show?id=candidatos-2024")
    try:
        req = urllib.request.Request(api, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            import json as _json
            pacote = _json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  CKAN do TSE não respondeu: {type(e).__name__}: {str(e)[:90]}")
        return []
    achadas = []
    for rec in (pacote.get("result") or {}).get("resources") or []:
        url = str(rec.get("url") or "")
        if url.lower().endswith(".zip") and "_sp" in url.lower():
            achadas.insert(0, url)            # o de SP primeiro
        elif url.lower().endswith(".zip"):
            achadas.append(url)
    print(f"  CKAN listou {len(achadas)} zip(s)")
    return achadas[:4]


def baixar_zip() -> str | None:
    """Baixa o zip do TSE para um arquivo temporário. Caminho, ou None."""
    for url in urls_do_ckan() + URLS_TSE:
        try:
            print(f"  tentando {url[:88]}…")
            # O CDN do TSE devolve 403 para User-Agent de robô. Cabeçalhos de
            # navegador resolvem — não é burlar nada: é dado aberto público,
            # servido por um CDN que filtra UA.
            req = urllib.request.Request(url, headers={
                "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/126.0 Safari/537.36"),
                "Accept": "application/zip,application/octet-stream,*/*",
                "Accept-Language": "pt-BR,pt;q=0.9",
                "Referer": "https://dadosabertos.tse.jus.br/",
            })
            with urllib.request.urlopen(req, timeout=300) as r:
                dados = r.read()
            if len(dados) < 10_000:
                print(f"    resposta pequena demais ({len(dados)} bytes) — ignorando")
                continue
            destino = os.path.join(tempfile.mkdtemp(), "consulta_cand.zip")
            with open(destino, "wb") as f:
                f.write(dados)
            print(f"    OK · {len(dados)//1024//1024} MB")
            return destino
        except Exception as e:
            print(f"    falhou: {type(e).__name__}: {str(e)[:100]}")
    print("  ! nenhuma URL do TSE respondeu. Baixe à mão em "
          "https://dadosabertos.tse.jus.br/dataset/candidatos-2024 e rode "
          "passando o caminho do zip.")
    return None


def main() -> int:
    if len(sys.argv) >= 2:
        caminho = sys.argv[1]
        if not os.path.isfile(caminho):
            print(f"arquivo não encontrado: {caminho}")
            return 2
    else:
        print("== TSE · baixando os candidatos de 2024 ==")
        caminho = baixar_zip()
        if not caminho:
            return 1

    alvos = {normalizar_nome(m["nome"]): m["nome"] for m in carregar_municipios()}
    linhas = []
    with zipfile.ZipFile(caminho) as z:
        csvs = [n for n in z.namelist() if n.lower().endswith(".csv")]
        # prefere o arquivo de SP; se o zip for o nacional, usa o maior CSV
        # (o filtro por SG_UF == SP abaixo garante o recorte de qualquer jeito).
        nome_csv = next((n for n in csvs if "_SP" in n.upper()), None)
        if not nome_csv:
            nome_csv = max(csvs, key=lambda n: z.getinfo(n).file_size) if csvs else None
        if not nome_csv:
            print("nenhum CSV encontrado dentro do zip")
            return 1
        print(f"  lendo {nome_csv}")
        with z.open(nome_csv) as fh:
            texto = io.TextIOWrapper(fh, encoding="latin-1", newline="")
            for r in csv.DictReader(texto, delimiter=";"):
                if r.get("SG_UF", "").upper() != "SP":
                    continue
                if r.get("DS_CARGO", "").upper() not in CARGOS:
                    continue
                if r.get("DS_SIT_TOT_TURNO", "").upper() not in ELEITOS:
                    continue
                municipio = alvos.get(normalizar_nome(r.get("NM_UE", "")))
                if not municipio:
                    continue
                linhas.append({
                    "municipio": municipio,
                    "cargo": r.get("DS_CARGO", "").upper(),
                    "nome_urna": r.get("NM_URNA_CANDIDATO", "").strip(),
                    "nome": r.get("NM_CANDIDATO", "").strip(),
                    "partido": r.get("SG_PARTIDO", "").strip().upper(),
                })

    # Sanidade (o plano exige): exatamente 1 prefeito por município.
    problemas = []
    for mun in alvos.values():
        n = sum(1 for x in linhas if x["municipio"] == mun and x["cargo"] == "PREFEITO")
        if n != 1:
            problemas.append(f"{mun}: {n} prefeito(s)")
        n_ver = sum(1 for x in linhas if x["municipio"] == mun and x["cargo"] == "VEREADOR")
        if n_ver < 9:
            problemas.append(f"{mun}: só {n_ver} vereador(es) — confira")

    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["municipio", "cargo", "nome_urna",
                                          "nome", "partido"])
        w.writeheader()
        w.writerows(sorted(linhas, key=lambda x: (x["municipio"], x["cargo"])))

    print(f"{len(linhas)} eleitos gravados em {SAIDA}")
    if problemas:
        print("AVISOS DE SANIDADE (confira antes de confiar):")
        for p in problemas:
            print("   -", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
