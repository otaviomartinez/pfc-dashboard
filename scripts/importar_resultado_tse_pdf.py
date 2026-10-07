#!/usr/bin/env python3
"""Resultado oficial da eleição de 2026 em SP, a partir dos PDFs do TRE-SP.

    python scripts/importar_resultado_tse_pdf.py <pasta-com-os-pdfs>

Por que PDF e não o zip de dados abertos: os relatórios do SISTOT (sistema de
totalização) chegaram primeiro e são OFICIAIS. São cinco:
  - "deputadas-e-deputados-estaduais-eleitos"  -> nome de URNA, votos, % e situação
  - "deputadas-e-deputados-federais-eleitos"   -> idem
  - "senadores-eleitos"                        -> idem
  - "resultado-da-votacao-...-estaduais-por-partido..." -> TODOS os candidatos,
  - "resultado-da-votacao-...-federais-por-partido..."     com nome CIVIL e o
                                                           partido/federação
A chave que une os dois tipos é o NÚMERO do candidato (por cargo).

TRÊS ARMADILHAS DO DOCUMENTO, tratadas aqui:
  1. nome longo quebra em duas linhas ("…ADORNO BECKER" / "GRANDINI");
  2. no relatório por partido, a coluna "% Votos" é a fatia do PARTIDO, igual
     para todos do bloco — não é o percentual do candidato (esse vem só do
     relatório de eleitos);
  3. dentro de uma FEDERAÇÃO o relatório não diz o partido de cada um. O campo
     `partido` guarda exatamente o que o documento diz (o nome da federação), e
     nunca é deduzido do número do candidato — legendas mudaram com fusões.
Resultado "sujeito a modificações" até a diplomação: o carimbo do relatório vai
para a coluna `resultado_em`, e a tela é obrigada a mostrá-lo.

Requer `pdftotext` (poppler). Nada roda no Streamlit: é construção offline.
"""
from __future__ import annotations

import csv
import glob
import os
import re
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(BASE, "data", "eleicoes", "resultado_sp_2026.csv")
COLUNAS = ["cargo", "numero", "nome_urna", "nome", "partido", "sigla", "votos",
           "pct_votos", "destinacao", "situacao", "resultado_em"]

# Linha de candidato: "*13133 - EDUARDO MATARAZZO SUPLICY   654.627   15.68   Válido   Eleito por QP"
_RE_CAND = re.compile(
    r"^\s*\*?(?P<num>\d{2,5}) - (?P<nome>.+?)\s{2,}(?P<votos>[\d\.]+)\s+"
    r"(?P<pct>[\d\.,]+%?)\s+(?P<dest>Válido|Anulado sub judice|Anulado|Nulo)\s+"
    r"\*?(?P<sit>.+?)\s*$")
_RE_CABECALHO = re.compile(r"^(\S.*?)\s{3,}Votos\s")
_RE_CARGO = re.compile(r"^Cargo:\s*(.+?)\s*$")
_RE_RESULTADO = re.compile(r"Resultado em (\d{2}/\d{2}/\d{4} - \d{2}:\d{2}:\d{2})")
_RUIDO = ("Justiça Eleitoral", "SISTOT", "Eleições Gerais", "OFICIAL", "Resultado de votação",
          "UF:", "Cargo:", "Candidato:", "computados", "Resultado em", "*Candidato",
          "**Percentual", "PROPORCIONAL")

# Sigla só para partido ISOLADO e só quando é inequívoca. Federação e partido
# desconhecido ficam com o nome oficial, sem sigla — nunca adivinhar.
SIGLAS = {
    "PARTIDO LIBERAL": "PL", "PARTIDO SOCIAL DEMOCRÁTICO": "PSD",
    "PARTIDO SOCIALISTA BRASILEIRO": "PSB", "PARTIDO DEMOCRÁTICO TRABALHISTA": "PDT",
    "PARTIDO NOVO": "NOVO", "REPUBLICANOS": "REPUBLICANOS", "PODEMOS": "PODEMOS",
    "AVANTE": "AVANTE", "AGIR": "AGIR", "MOVIMENTO DEMOCRÁTICO BRASILEIRO": "MDB",
    "DEMOCRACIA CRISTÃ": "DC", "PARTIDO MISSÃO": "MISSÃO", "UNIDADE POPULAR": "UP",
    "PARTIDO SOCIALISTA DOS TRABALHADORES": "PSTU", "PARTIDO DA CAUSA OPERÁRIA": "PCO",
    "MOBILIZAÇÃO NACIONAL": "MOBILIZA",
}

CARGO_NORMAL = {"DEPUTADO ESTADUAL": "DEPUTADO ESTADUAL", "DEPUTADO FEDERAL": "DEPUTADO FEDERAL",
                "SENADOR": "SENADOR"}


def _texto(pdf: str) -> str:
    """Texto do PDF com o layout preservado (as colunas dependem dele)."""
    return subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True,
                          text=True, check=True).stdout


def _int(v: str) -> int:
    return int(str(v).replace(".", "").replace(",", "") or 0)


def ler_relatorio(texto: str, por_partido: bool) -> tuple[list[dict], str]:
    """PURA: linhas de candidato de um relatório do SISTOT.

    Devolve (candidatos, resultado_em). Em relatório por partido, cada candidato
    herda o cabeçalho de bloco (partido/federação) acima dele.
    """
    cargo, bloco, saida, resultado_em = "", "", [], ""
    for linha in texto.splitlines():
        m = _RE_RESULTADO.search(linha)
        if m:
            resultado_em = m.group(1)
        m = _RE_CARGO.match(linha.strip())
        if m:
            cargo = CARGO_NORMAL.get(m.group(1).upper(), m.group(1).upper())
            continue
        if por_partido:
            m = _RE_CABECALHO.match(linha)
            if m and not linha.lstrip().startswith(("Candidato", "*")) \
                    and not re.match(r"^\s*\*?\d", linha):
                bloco = m.group(1).strip()
                continue
        m = _RE_CAND.match(linha)
        if m:
            saida.append({
                "cargo": cargo, "numero": m.group("num"),
                "nome": " ".join(m.group("nome").split()),
                "votos": _int(m.group("votos")),
                "pct": m.group("pct"), "destinacao": m.group("dest"),
                "situacao": " ".join(m.group("sit").split()),
                "bloco": bloco,
            })
            continue
        # continuação de nome quebrado: uma linha só de letras, logo após um candidato
        so = linha.strip()
        if (saida and so and not any(r in linha for r in _RUIDO)
                and re.fullmatch(r"[A-ZÁÉÍÓÚÂÊÔÃÕÇÜ' \-\.]+", so)
                and so != bloco):
            saida[-1]["nome"] = f'{saida[-1]["nome"]} {so}'
    return saida, resultado_em


def juntar(eleitos: list[dict], por_partido: list[dict], resultado_em: str) -> list[dict]:
    """PURA: um registro por candidato, unindo pelos (cargo, número).

    Do relatório por partido vêm TODOS (nome civil, partido, situação final); do de
    eleitos vêm o nome de URNA e o % individual. Senador não tem relatório por
    partido aqui: entra só com o que o de eleitos traz.
    """
    urna = {(e["cargo"], e["numero"]): e for e in eleitos}
    saida, vistos = [], set()
    for c in por_partido:
        chave = (c["cargo"], c["numero"])
        vistos.add(chave)
        e = urna.get(chave, {})
        saida.append({
            "cargo": c["cargo"], "numero": c["numero"],
            "nome_urna": e.get("nome", ""), "nome": c["nome"],
            "partido": c["bloco"], "sigla": SIGLAS.get(c["bloco"].upper(), ""),
            "votos": c["votos"],
            "pct_votos": e.get("pct", "").replace("%", ""),   # % do PARTIDO não entra
            "destinacao": c["destinacao"], "situacao": c["situacao"],
            "resultado_em": resultado_em,
        })
    for chave, e in urna.items():                   # senadores (e qualquer órfão)
        if chave in vistos:
            continue
        saida.append({
            "cargo": e["cargo"], "numero": e["numero"], "nome_urna": e["nome"],
            "nome": "", "partido": "", "sigla": "", "votos": e["votos"],
            "pct_votos": e["pct"].replace("%", ""), "destinacao": e["destinacao"],
            "situacao": e["situacao"], "resultado_em": resultado_em,
        })
    return saida


def main() -> int:
    if len(sys.argv) < 2 or not os.path.isdir(sys.argv[1]):
        print("Uso: python scripts/importar_resultado_tse_pdf.py <pasta-com-os-5-pdfs>")
        return 1
    pdfs = glob.glob(os.path.join(sys.argv[1], "*.pdf"))
    eleitos, por_partido, carimbos = [], [], []
    for pdf in pdfs:
        nome = os.path.basename(pdf).lower()
        partido = "por-partido" in nome
        linhas, quando = ler_relatorio(_texto(pdf), por_partido=partido)
        carimbos.append(quando)
        (por_partido if partido else eleitos).extend(linhas)
        print(f"  {len(linhas):5d} candidatos · {os.path.basename(pdf)[:70]}")
    if not eleitos or not por_partido:
        print("! Faltam relatórios (preciso dos de ELEITOS e dos POR PARTIDO). Nada gravado.")
        return 1
    resultado_em = max((c for c in carimbos if c), default="")
    registros = juntar(eleitos, por_partido, resultado_em)

    # conferência contra o que o próprio documento diz
    sit_eleito = ("ELEITO", "ELEITO POR QP", "ELEITO POR MÉDIA")
    n = {c: sum(1 for r in registros if r["cargo"] == c and r["situacao"].upper() in sit_eleito)
         for c in ("DEPUTADO ESTADUAL", "DEPUTADO FEDERAL", "SENADOR")}
    print(f"  eleitos: {n}  (esperado: 94 estaduais · 70 federais · 2 senadores)")
    sem_urna = [r for r in registros if r["situacao"].upper() in sit_eleito and not r["nome_urna"]]
    if sem_urna:
        print(f"! {len(sem_urna)} eleitos sem nome de urna — o número não casou. Nada gravado.")
        return 1

    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(sorted(registros, key=lambda r: (r["cargo"], -int(r["votos"]))))
    print(f"{len(registros)} candidatos -> {SAIDA} (resultado de {resultado_em})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
