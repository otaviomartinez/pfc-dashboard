"""Contato institucional da prefeitura (cadastro de CNPJ da Receita Federal).

Gerado por scripts/importar_contatos_prefeitura.py ->
data/prefeituras/contatos_prefeitura.csv.

É contato INSTITUCIONAL (regra 2 do CLAUDE.md): e-mail e telefone que a própria
prefeitura mantém no cadastro nacional, nunca contato pessoal de ninguém. O
código não sobrescreve o que o Fábio anotar à mão.
"""
from __future__ import annotations

import csv
import os
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_CONTATOS = os.path.join(BASE, "data", "prefeituras", "contatos_prefeitura.csv")


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.split()).lower()


def carregar(caminho: str | None = None) -> dict[str, dict]:
    """{cod_ibge: {municipio, email, telefone, endereco, cep, razao_social}}.

    Loader GRACIOSO: arquivo ausente -> {} (o painel cai para os links de busca).
    Linha sem e-mail E sem telefone é descartada: não serve para contato.
    """
    caminho = caminho or CSV_CONTATOS
    if not os.path.isfile(caminho):
        return {}
    try:
        with open(caminho, encoding="utf-8-sig", newline="") as f:
            linhas = list(csv.DictReader(f))
    except OSError:
        return {}
    saida = {}
    for linha in linhas:
        b = {str(k).strip().lower(): (v or "").strip() for k, v in linha.items()}
        cod = b.get("cod_ibge", "")
        if not cod or not (b.get("email") or b.get("telefone")):
            continue
        saida[cod] = {
            "municipio": b.get("municipio", ""),
            "razao_social": b.get("razao_social", ""),
            "email": b.get("email", ""),
            "telefone": b.get("telefone", ""),
            "endereco": b.get("endereco", ""),
            "cep": b.get("cep", ""),
            "cnpj": b.get("cnpj", ""),
        }
    return saida


def por_codigo(cod_ibge, caminho: str | None = None) -> dict | None:
    """Contato pelo código IBGE — casamento exato, sem depender de grafia."""
    return carregar(caminho).get(str(cod_ibge or "").strip())


def por_municipio(municipio: str, caminho: str | None = None) -> dict | None:
    """Contato pelo NOME do município (o painel nem sempre tem o cod_ibge à mão)."""
    alvo = _norm(municipio)
    for reg in carregar(caminho).values():
        if _norm(reg.get("municipio")) == alvo:
            return reg
    return None
