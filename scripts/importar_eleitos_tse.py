#!/usr/bin/env python3
"""Importa prefeitos/vices/vereadores eleitos em 2024 (TSE) -> CSV versionado.

RODE NA SUA MÁQUINA, UMA VEZ (aqui no dev o domínio do TSE está bloqueado por
política da organização — gateway 403). Não roda em runtime do Streamlit.

    # 1) baixe o zip (uma vez):
    #    https://dadosabertos.tse.jus.br/dataset/candidatos-2024
    #    arquivo: consulta_cand_2024_SP.zip
    # 2) rode apontando para ele:
    python scripts/importar_eleitos_tse.py ~/Downloads/consulta_cand_2024_SP.zip

Gera data/prefeituras/eleitos_2024.csv só com os municípios do painel.
CSV do TSE: latin-1, separado por ';'.
"""
import csv
import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prefeituras.config import carregar_municipios, normalizar_nome  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(BASE, "data", "prefeituras", "eleitos_2024.csv")

CARGOS = {"PREFEITO", "VICE-PREFEITO", "VEREADOR"}
ELEITOS = {"ELEITO", "ELEITO POR MÉDIA", "ELEITO POR QP"}


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    caminho = sys.argv[1]
    if not os.path.isfile(caminho):
        print(f"arquivo não encontrado: {caminho}")
        return 2

    alvos = {normalizar_nome(m["nome"]): m["nome"] for m in carregar_municipios()}
    linhas = []
    with zipfile.ZipFile(caminho) as z:
        nome_csv = next((n for n in z.namelist()
                         if n.lower().endswith(".csv") and "_SP" in n), None)
        if not nome_csv:
            print("CSV de SP não encontrado dentro do zip")
            return 1
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
