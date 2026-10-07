"""Eleição geral de 2026 — o que muda para o painel de Emendas.

Lê data/eleicoes/candidatos_sp_2026.csv (gerado por
scripts/importar_eleicao_2026.py a partir do consulta_cand_2026 do TSE) e cruza
com quem está HOJE no mandato.

TRÊS FATOS QUE MANDAM AQUI (conferidos em out/2026):
  1. A posse é em 1º de FEVEREIRO de 2027 para os três cargos — inclusive na
     ALESP, que mudou a data (era 15 de março até 2023).
  2. Até lá, quem manda é a bancada ATUAL. E é ela que indica as emendas do
     Orçamento de 2027, que tramita agora. Quem NÃO foi reeleito continua
     indicando emenda até 31/jan — por isso o painel NÃO apaga ninguém hoje.
  3. Resultado só vira definitivo na DIPLOMAÇÃO (dezembro): candidatura sub
     judice e recontagem ainda podem mudar a lista. O painel diz "eleito em
     2026", nunca "empossado".

Casamento de NOMES é o ponto frágil (a ALESP chama de "Agente Federal Danilo
Balas" quem a urna chama de "DANILO BALAS"). Regra conservadora: só afirma
quando há UM candidato compatível; dois ou mais viram "a conferir"; nenhum vira
"não encontrado entre os candidatos" — que NÃO é o mesmo que "não concorreu"
(pode ser só grafia diferente).

PURO: sem rede, sem Streamlit.
"""
from __future__ import annotations

import csv
import os
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_CANDIDATOS = os.path.join(BASE, "data", "eleicoes", "candidatos_sp_2026.csv")

POSSE_2027 = "2027-02-01"
CARGOS = ("DEPUTADO ESTADUAL", "DEPUTADO FEDERAL", "SENADOR")
SITUACOES_ELEITO = ("ELEITO", "ELEITO POR QP", "ELEITO POR MÉDIA", "ELEITO POR MEDIA")

# Rótulos que a tela mostra. Nenhum diz "derrotado" ou adjetiva: é fato do TSE.
ROTULOS = {
    "reeleito": "Reeleito em 2026",
    "eleito_outro_cargo": "Eleito em 2026 para outro cargo",
    "nao_eleito": "Não reeleito — mandato até 31/jan/2027",
    "nao_encontrado": "Não encontrado entre os candidatos de 2026",
    "a_conferir": "Situação a conferir (mais de um nome compatível)",
}


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().replace("-", " ").replace(".", " ").split())


def eleito(c: dict) -> bool:
    return _norm(c.get("situacao")).upper() in {_norm(x).upper() for x in SITUACOES_ELEITO}


def carregar(caminho: str | None = None) -> list[dict]:
    """Candidatos de SP aos 3 cargos. Sem arquivo -> [] (a tela segue como hoje)."""
    caminho = caminho or CSV_CANDIDATOS
    try:
        with open(caminho, encoding="utf-8-sig", newline="") as f:
            return [dict(r) for r in csv.DictReader(f)]
    except (FileNotFoundError, OSError):
        return []


def _compativel(nome_atual: str, cand: dict) -> bool:
    """Igual, ou um nome contido no outro com pelo menos 2 palavras.
    "Agente Federal Danilo Balas" x "DANILO BALAS" -> compatível.
    "Ana" x "Ana Paula Silva" -> NÃO (uma palavra só é ambígua demais)."""
    a = _norm(nome_atual)
    if not a:
        return False
    for b in (_norm(cand.get("nome_urna")), _norm(cand.get("nome"))):
        if not b:
            continue
        if a == b:
            return True
        curto, longo = (a, b) if len(a) <= len(b) else (b, a)
        if len(curto.split()) >= 2 and f" {curto} " in f" {longo} ":
            return True
    return False


def situacao_2026(nome_atual: str, cargo_atual: str, candidatos: list[dict]) -> dict:
    """O que a eleição de 2026 decidiu sobre quem está HOJE no cargo.

    Devolve {status, rotulo, cargo_2027, partido}. `cargo_atual` é
    'DEPUTADO ESTADUAL', 'DEPUTADO FEDERAL' ou 'SENADOR'.
    """
    achados = [c for c in candidatos if _compativel(nome_atual, c)]
    # o mesmo candidato pode aparecer duas vezes (urna e nome civil): dedup por id
    unicos = {c.get("sq_candidato") or (c.get("nome"), c.get("cargo")): c for c in achados}
    achados = list(unicos.values())
    if not achados:
        status, c = "nao_encontrado", {}
    elif len(achados) > 1:
        status, c = "a_conferir", {}
    else:
        c = achados[0]
        if not eleito(c):
            status = "nao_eleito"
        elif _norm(c.get("cargo")) == _norm(cargo_atual):
            status = "reeleito"
        else:
            status = "eleito_outro_cargo"
    return {"status": status, "rotulo": ROTULOS[status],
            "cargo_2027": c.get("cargo", "") if status in ("reeleito", "eleito_outro_cargo") else "",
            "partido": c.get("partido", "")}


def eleitos(candidatos: list[dict], cargo: str) -> list[dict]:
    return [c for c in candidatos if _norm(c.get("cargo")) == _norm(cargo) and eleito(c)]


def novos_eleitos(candidatos: list[dict], cargo: str, nomes_atuais: list[str]) -> list[dict]:
    """Eleitos em 2026 para `cargo` que NÃO estão hoje na lista de `cargo`:
    a bancada nova, com quem começar relacionamento antes da posse."""
    return [c for c in eleitos(candidatos, cargo)
            if not any(_compativel(n, c) for n in nomes_atuais)]
