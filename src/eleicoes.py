"""Eleição geral de 2026 — o que muda para o painel de Emendas.

Lê data/eleicoes/resultado_sp_2026.csv (relatórios OFICIAIS do TRE-SP, via
scripts/importar_resultado_tse_pdf.py) — ou, na falta dele, o candidatos_sp_2026.csv
do zip do TSE — e cruza com quem está HOJE no mandato.

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
Balas" quem a urna chama de "DANILO BALAS"). Regra conservadora, em níveis
(ver `_nivel`): só afirma quando há UM candidato no nível mais forte; dois ou
mais viram "a conferir"; nenhum vira
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
# Fonte preferida: os relatórios OFICIAIS do TRE-SP (SISTOT), lidos por
# scripts/importar_resultado_tse_pdf.py. O CSV do zip de dados abertos fica de
# reserva — mesmas colunas essenciais (cargo, nome_urna, nome, situação).
CSV_RESULTADO = os.path.join(BASE, "data", "eleicoes", "resultado_sp_2026.csv")

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
    """Candidatos de SP aos 3 cargos. Sem arquivo -> [] (a tela segue como hoje).
    Sem caminho: o resultado oficial (PDF do TRE-SP) e, na falta dele, o zip."""
    if caminho is None:
        caminho = CSV_RESULTADO if os.path.isfile(CSV_RESULTADO) else CSV_CANDIDATOS
    try:
        with open(caminho, encoding="utf-8-sig", newline="") as f:
            return [dict(r) for r in csv.DictReader(f)]
    except (FileNotFoundError, OSError):
        return []


# Títulos que o nome PARLAMENTAR carrega e o nome CIVIL não ("Agente Federal
# Danilo Balas" é "DANILO MASCARENHAS DE BALAS" no TSE).
_TITULOS = {"dr", "dra", "doutor", "doutora", "major", "delegado", "delegada",
            "professor", "professora", "prof", "pastor", "pastora", "sargento",
            "coronel", "capitao", "tenente", "cabo", "agente", "federal", "irmao",
            "irma", "bispo", "missionario", "missionaria"}
# Apelido -> formas do nome civil. Lista curta e EXPLÍCITA, só com casos vistos
# nos 94 da ALESP — apelido genérico ("Zé") geraria casamento errado.
_APELIDOS = {"beth": ("elisabeth", "elizabeth", "isabeth"), "rafa": ("rafael",),
             "carlao": ("carlos",)}


# Casos CONFERIDOS À MÃO contra o relatório do TRE-SP: o nome parlamentar não
# tem palavra em comum suficiente com o de urna/civil para a regra automática,
# mas o documento não deixa dúvida (cargo + número). Só entra aqui quem foi
# conferido — na dúvida, fica "não encontrado", que é o rótulo honesto.
CONFERIDOS = {
    "monica seixas do movimento pretas": ("DEPUTADO ESTADUAL", "50900"),  # MONICA DAS PRETAS · MONICA CRISTINA SEIXAS BONFIM
    "teonilio barba": ("DEPUTADO ESTADUAL", "13110"),  # BARBA · TEONILIO MONTEIRO DA COSTA
    "maurici": ("DEPUTADO ESTADUAL", "13011"),         # MARIO MAURICI DE LIMA MORAIS
}


def _tokens(nome: str) -> list[str]:
    return [("junior" if t == "jr" else t) for t in _norm(nome).split() if t not in _TITULOS]


def _formas(nome_cand) -> list[str]:
    """Nome de urna com duas formas ("TELHADINHA - CAPITÃO TELHADA") vale pelas duas."""
    txt = str(nome_cand or "")
    partes = [p for p in txt.split(" - ") if p.strip()] if " - " in txt else []
    return [txt] + partes


def _contido_em_ordem(curto: list[str], longo: list[str]) -> bool:
    """Todas as palavras do nome curto aparecem, NA ORDEM, no longo — palavras a
    mais no meio são permitidas ("edson giriboni" em "edson de oliveira
    giriboni"). Apelido conhecido vale pela forma civil."""
    i = 0
    for t in longo:
        if i < len(curto) and (t == curto[i] or t in _APELIDOS.get(curto[i], ())):
            i += 1
    return i == len(curto)


def _nivel(nome_atual: str, cand: dict) -> int:
    """Força da evidência de que `cand` é a pessoa `nome_atual`. 0 = nenhuma.

      3  IGUAL, nome INTEIRO com título — ao de urna (vale mesmo com uma palavra
         só: "Donato" = "DONATO", "Professora Bebel" = "PROFESSORA BEBEL") ou
         ao civil. NUNCA igual "depois de tirar os títulos": "Capitão Telhada"
         virava "telhada" = "telhada" de "CORONEL TELHADA" — pai e filho,
         pessoas diferentes, e o painel diria que o deputado foi para a Câmara;
      2  CONTIDO, palavras seguidas, ≥2 palavras ("Agente Federal Danilo Balas"
         x "DANILO BALAS");
      1  CONTIDO EM ORDEM, com palavras a mais no meio, ≥2 palavras ("Edson
         Giriboni" x "EDSON DE OLIVEIRA GIRIBONI"; "Beth" vale "Elisabeth").
    Títulos (Dr., Major, Agente Federal…) não contam como palavra.
    """
    a_txt, a = _norm(nome_atual), _tokens(nome_atual)
    conferido = CONFERIDOS.get(a_txt)
    if conferido:                              # conferido à mão: só aquele candidato
        return 3 if (_norm(cand.get("cargo")), str(cand.get("numero"))) == \
            (_norm(conferido[0]), conferido[1]) else 0
    nomes = _formas(cand.get("nome_urna")) + [cand.get("nome")]
    if a_txt and a_txt in {_norm(n) for n in nomes}:
        return 3
    if len(a) < 2:
        return 0                               # uma palavra só: só vale se IGUAL
    melhor = 0
    for nome_cand in nomes:
        b = _tokens(nome_cand)
        if len(b) < 2:
            continue
        curto, longo = (a, b) if len(a) <= len(b) else (b, a)
        if f" {' '.join(curto)} " in f" {' '.join(longo)} ":
            melhor = max(melhor, 2)
        elif _contido_em_ordem(curto, longo):
            melhor = max(melhor, 1)
    return melhor


def _compativel(nome_atual: str, cand: dict) -> bool:
    return _nivel(nome_atual, cand) > 0


def _melhores(nome_atual: str, candidatos: list[dict]) -> list[dict]:
    """Os candidatos do nível MAIS FORTE encontrado. Um IGUAL vence qualquer
    número de parecidos — antes, "Rafael Silva" (urna idêntica) virava "a
    conferir" porque outros nomes civis também continham rafael…silva."""
    por_nivel: dict[int, dict] = {}
    for c in candidatos:
        n = _nivel(nome_atual, c)
        if n:
            chave = c.get("sq_candidato") or (c.get("cargo"), c.get("numero") or c.get("nome"))
            por_nivel.setdefault(n, {})[chave] = c
    return list(por_nivel[max(por_nivel)].values()) if por_nivel else []


def situacao_2026(nome_atual: str, cargo_atual: str, candidatos: list[dict]) -> dict:
    """O que a eleição de 2026 decidiu sobre quem está HOJE no cargo.

    Devolve {status, rotulo, cargo_2027, cargo_disputado, partido, votos, numero}.
    `votos` só existe com o resultado oficial (PDF do TRE-SP); no zip vem vazio. `cargo_atual` é
    'DEPUTADO ESTADUAL', 'DEPUTADO FEDERAL' ou 'SENADOR'.
    """
    achados = _melhores(nome_atual, candidatos)
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
            "cargo_disputado": c.get("cargo", ""),
            "partido": c.get("sigla") or c.get("partido", ""),
            "votos": c.get("votos", ""), "numero": c.get("numero", "")}


def eleitos(candidatos: list[dict], cargo: str) -> list[dict]:
    return [c for c in candidatos if _norm(c.get("cargo")) == _norm(cargo) and eleito(c)]


def novos_eleitos(candidatos: list[dict], cargo: str, nomes_atuais: list[str]) -> list[dict]:
    """Eleitos em 2026 para `cargo` que NÃO estão hoje na lista de `cargo`:
    a bancada nova, com quem começar relacionamento antes da posse."""
    return [c for c in eleitos(candidatos, cargo)
            if not any(_compativel(n, c) for n in nomes_atuais)]
