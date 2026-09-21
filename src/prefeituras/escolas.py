"""Cadastro de escolas do INEP (Catálogo de Escolas) — contato por município.

Fonte: INEP, "Catálogo de Escolas" exportado para SP
(data/inep/escolas_sp.csv, UTF-8 com BOM, separador vírgula). 33.357 escolas de
SP; 3.113 nos 88 municípios do painel (os 11 + os 77 vizinhos da expansão).

POR QUE ESTA FONTE: o TSE mascara e-mail de candidato ("NÃO DIVULGÁVEL" em
8.329 de 8.329 eleitos de SP), e o Censo Escolar só traz contagem de matrícula.
Este é um CADASTRO: traz endereço e telefone REAIS, por escola.

E é o contato mais acionável para o PFC: o programa acontece DENTRO da escola.
Falar com a diretora de uma escola municipal costuma abrir mais porta que o
gabinete do prefeito.

CONTATO INSTITUCIONAL, sempre (regra 2 do CLAUDE.md): é telefone de escola
pública, não telefone pessoal de ninguém. O código nunca sobrescreve o contato
que o Fábio anotar à mão.
"""
from __future__ import annotations

import csv
import os
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_ESCOLAS = os.path.join(BASE, "data", "inep", "escolas_sp.csv")


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.split()).lower()


def _carregar_tudo(caminho: str | None = None) -> list[dict]:
    caminho = caminho or CSV_ESCOLAS
    if not os.path.isfile(caminho):
        return []
    try:
        with open(caminho, encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []


def por_municipio(municipio: str, caminho: str | None = None,
                  so_publicas: bool = True) -> list[dict]:
    """Escolas de um município: [{nome, inep, dependencia, endereco, telefone,
    etapas, porte}]. Loader GRACIOSO: [] se o arquivo faltar.

    `so_publicas=True` por padrão: o PFC atua na rede pública, e listar escola
    privada só polui. Ordena municipais primeiro (é com a prefeitura que o
    convênio é assinado), depois por nome.
    """
    alvo = _norm(municipio)
    saida = []
    for linha in _carregar_tudo(caminho):
        if _norm(linha.get("Município")) != alvo:
            continue
        categoria = str(linha.get("Categoria Administrativa") or "")
        if so_publicas and "Pública" not in categoria:
            continue
        saida.append({
            "nome": str(linha.get("Escola") or "").strip(),
            "inep": str(linha.get("Código INEP") or "").strip(),
            "dependencia": str(linha.get("Dependência Administrativa") or "").strip(),
            "endereco": " ".join(str(linha.get("Endereço") or "").split()),
            "telefone": str(linha.get("Telefone") or "").strip(),
            "localizacao": str(linha.get("Localização") or "").strip(),
            "etapas": str(linha.get("Etapas e Modalidade de Ensino Oferecidas") or "").strip(),
            "porte": str(linha.get("Porte da Escola") or "").strip(),
        })
    ordem = {"Municipal": 0, "Estadual": 1, "Federal": 2}
    saida.sort(key=lambda e: (ordem.get(e["dependencia"], 9), e["nome"]))
    return saida


def resumo_municipio(municipio: str, caminho: str | None = None) -> dict:
    """{total, municipais, estaduais, com_telefone} — para o card e o placar."""
    escolas = por_municipio(municipio, caminho)
    return {
        "total": len(escolas),
        "municipais": sum(1 for e in escolas if e["dependencia"] == "Municipal"),
        "estaduais": sum(1 for e in escolas if e["dependencia"] == "Estadual"),
        "com_telefone": sum(1 for e in escolas if e["telefone"]),
    }
