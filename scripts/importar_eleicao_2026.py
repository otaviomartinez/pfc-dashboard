#!/usr/bin/env python3
"""Importa o resultado da eleição de 2026 (TSE) para SP -> CSV versionado.

    python scripts/importar_eleicao_2026.py ~/Downloads/consulta_cand_2026.zip

ONDE BAIXAR (no navegador — o CDN do TSE recusa o robô do GitHub, já testado):
  dadosabertos.tse.jus.br -> "Candidatos - 2026" -> consulta_cand_2026.zip
  (serve o nacional ou o só-SP: o script filtra SP sozinho).

Gera data/eleicoes/candidatos_sp_2026.csv com os candidatos de SP a deputado
estadual, deputado federal e senador, e a SITUAÇÃO de cada um (eleito, eleito
por QP/média, suplente, não eleito). Guarda só o mínimo público: cargo, nomes,
número, partido, situação e o id do TSE. Nada de CPF ou e-mail.

DUAS RECUSAS, as duas de propósito:
  - não grava CSV vazio (apagaria o que já funciona);
  - não grava se o arquivo ainda NÃO traz o resultado (situação em branco ou
    "#NULO#"): o TSE atualiza esse arquivo em lotes depois da eleição. Nesse
    caso diz para baixar de novo em alguns dias — em vez de gravar uma lista
    em que ninguém foi eleito.
CSV do TSE: latin-1, separado por ';' (mesmo formato do de 2024).
"""
import csv
import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.eleicoes import CARGOS, SITUACOES_ELEITO  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(BASE, "data", "eleicoes", "candidatos_sp_2026.csv")
COLUNAS = ["sq_candidato", "cargo", "nome_urna", "nome", "numero", "partido", "situacao"]
SEM_RESULTADO = {"", "#NULO#", "#NULO", "NÃO DIVULGÁVEL", "NAO DIVULGAVEL", "#NE#"}


def _linhas_do_zip(caminho: str):
    """Itera as linhas de todos os CSVs de candidatos dentro do zip."""
    with zipfile.ZipFile(caminho) as z:
        nomes = [n for n in z.namelist()
                 if n.lower().endswith(".csv") and "consulta_cand" in n.lower()]
        # prefere o recorte de SP; senão, o nacional (filtrado por SG_UF)
        sp = [n for n in nomes if n.upper().endswith("_SP.CSV")]
        for nome in (sp or nomes):
            with z.open(nome) as fh:
                texto = io.TextIOWrapper(fh, encoding="latin-1", newline="")
                yield from csv.DictReader(texto, delimiter=";")


def extrair(linhas) -> list[dict]:
    """PURA: das linhas do TSE, só SP x 3 cargos, só os campos mínimos."""
    saida, vistos = [], set()
    for r in linhas:
        if str(r.get("SG_UF", "")).strip().upper() != "SP":
            continue
        cargo = str(r.get("DS_CARGO", "")).strip().upper()
        if cargo not in CARGOS:
            continue
        sq = str(r.get("SQ_CANDIDATO", "")).strip()
        if sq and sq in vistos:
            continue
        vistos.add(sq)
        saida.append({
            "sq_candidato": sq, "cargo": cargo,
            "nome_urna": str(r.get("NM_URNA_CANDIDATO", "")).strip(),
            "nome": str(r.get("NM_CANDIDATO", "")).strip(),
            "numero": str(r.get("NR_CANDIDATO", "")).strip(),
            "partido": str(r.get("SG_PARTIDO", "")).strip().upper(),
            "situacao": str(r.get("DS_SIT_TOT_TURNO", "")).strip().upper(),
        })
    return saida


def tem_resultado(candidatos: list[dict]) -> bool:
    """O arquivo já foi atualizado com a totalização? Basta haver eleitos."""
    eleitos = {s.upper() for s in SITUACOES_ELEITO}
    return any(c["situacao"] in eleitos for c in candidatos)


def main() -> int:
    if len(sys.argv) < 2 or not os.path.isfile(sys.argv[1]):
        print("Uso: python scripts/importar_eleicao_2026.py <consulta_cand_2026.zip>")
        print("Baixe no navegador: dadosabertos.tse.jus.br -> Candidatos - 2026.")
        return 1
    candidatos = extrair(_linhas_do_zip(sys.argv[1]))
    if not candidatos:
        print("! Nenhum candidato de SP aos 3 cargos no arquivo. É o zip certo "
              "(consulta_cand_2026)? Nada gravado.")
        return 1
    if not tem_resultado(candidatos):
        sem = sum(1 for c in candidatos if c["situacao"] in SEM_RESULTADO)
        print(f"! O arquivo ainda NÃO traz o resultado: {sem} de {len(candidatos)} "
              "candidatos sem situação de totalização. O TSE atualiza em lotes — "
              "baixe de novo em alguns dias. Nada gravado.")
        return 1

    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(sorted(candidatos, key=lambda c: (c["cargo"], c["nome_urna"])))
    eleitos = {s.upper() for s in SITUACOES_ELEITO}
    print(f"{len(candidatos)} candidatos de SP gravados -> {SAIDA}")
    for cargo in CARGOS:
        n = sum(1 for c in candidatos if c["cargo"] == cargo and c["situacao"] in eleitos)
        print(f"  {cargo:18} {n:3d} eleitos")
    print("  esperado: 94 estaduais · 70 federais · 2 senadores (SP)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
