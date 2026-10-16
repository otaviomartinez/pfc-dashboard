#!/usr/bin/env python3
"""Votação para SENADOR por município (SP, 2026) -> CSV versionado.

    python scripts/importar_votacao_municipio_2026.py ~/Downloads/votacao_candidato_munzona_2026.zip

ONDE BAIXAR (no navegador — o CDN do TSE recusa o robô do GitHub, já testado):
  dadosabertos.tse.jus.br -> "Resultados - 2026" -> "Votação nominal por
  município e zona" (votacao_candidato_munzona_2026.zip). Serve o nacional ou
  o só-SP: o script filtra SP e o cargo SENADOR sozinho.

Gera data/eleicoes/votacao_senador_municipio_2026.csv: uma linha por
(município, candidato), somando as zonas. É a parte TERRITORIAL do score de
senador (src/score_senador.py): quanto da votação de cada um veio das cidades
do PFC e vizinhas.

Recusas, de propósito: não grava arquivo vazio, e não grava se não houver
nenhum voto de senador (arquivo errado ou ainda sem totalização).
CSV do TSE: latin-1, separado por ';'. Só 1º turno (senador não tem 2º).
"""
import csv
import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.score_senador import CSV_VOTACAO, norm_municipio, pesos_territorio_padrao  # noqa: E402

COLUNAS = ["municipio", "cod_tse", "numero", "nome_urna", "votos"]


def _linhas_do_zip(caminho: str):
    """Itera as linhas dos CSVs de votação por município/zona dentro do zip."""
    with zipfile.ZipFile(caminho) as z:
        nomes = [n for n in z.namelist()
                 if n.lower().endswith(".csv") and "munzona" in n.lower()]
        sp = [n for n in nomes if n.upper().endswith("_SP.CSV")]
        for nome in (sp or nomes):
            with z.open(nome) as fh:
                texto = io.TextIOWrapper(fh, encoding="latin-1", newline="")
                yield from csv.DictReader(texto, delimiter=";")


def _int(v) -> int:
    try:
        return int(str(v).strip() or 0)
    except ValueError:
        return 0


def extrair(linhas) -> list[dict]:
    """PURA: SP x SENADOR x 1º turno, somando as zonas de cada município.
    Usa votos nominais VÁLIDOS quando a coluna existe (exclui anulado sub judice)."""
    soma, info = {}, {}
    for r in linhas:
        if str(r.get("SG_UF", "")).strip().upper() != "SP":
            continue
        if str(r.get("DS_CARGO", "")).strip().upper() != "SENADOR":
            continue
        if str(r.get("NR_TURNO", "1")).strip() not in ("1", ""):
            continue
        votos = r.get("QT_VOTOS_NOMINAIS_VALIDOS")
        votos = _int(votos if votos not in (None, "") else r.get("QT_VOTOS_NOMINAIS"))
        mun = str(r.get("NM_MUNICIPIO", "")).strip()
        num = str(r.get("NR_CANDIDATO", "")).strip()
        if not mun or not num:
            continue
        chave = (mun, num)
        soma[chave] = soma.get(chave, 0) + votos
        info[chave] = (str(r.get("CD_MUNICIPIO", "")).strip(),
                       str(r.get("NM_URNA_CANDIDATO", "")).strip())
    return [{"municipio": m, "cod_tse": info[(m, n)][0], "numero": n,
             "nome_urna": info[(m, n)][1], "votos": v}
            for (m, n), v in soma.items()]


def main() -> int:
    if len(sys.argv) < 2 or not os.path.isfile(sys.argv[1]):
        print("Uso: python scripts/importar_votacao_municipio_2026.py <votacao_candidato_munzona_2026.zip>")
        print("Baixe no navegador: dadosabertos.tse.jus.br -> Resultados - 2026.")
        return 1
    linhas = extrair(_linhas_do_zip(sys.argv[1]))
    if not linhas or not sum(r["votos"] for r in linhas):
        print("! Nenhum voto para SENADOR em SP no arquivo. É o zip certo "
              "(votacao_candidato_munzona_2026)? Nada gravado.")
        return 1

    # conferência: as cidades do território precisam ser achadas pelo nome
    muns = {norm_municipio(r["municipio"]) for r in linhas}
    faltam = sorted(m for m in pesos_territorio_padrao() if m not in muns)
    os.makedirs(os.path.dirname(CSV_VOTACAO), exist_ok=True)
    with open(CSV_VOTACAO, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(sorted(linhas, key=lambda r: (r["municipio"], -r["votos"])))
    print(f"{len(linhas)} linhas ({len(muns)} municípios) -> {CSV_VOTACAO}")
    if faltam:
        print(f"! {len(faltam)} cidade(s) do território sem casamento de nome: {', '.join(faltam)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
