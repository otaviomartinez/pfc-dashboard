"""Resolve o código IBGE dos municípios do PFC — OFFLINE, sem chutar.

O plano previa consultar a API `/entes` do SICONFI. Mas a tabela oficial do IBGE
(código de 7 dígitos + região imediata) já está versionada no repo em
`data/ibge_regioes_imediatas_sp.csv`. Então resolvemos a partir dela: é a MESMA
fonte oficial, funciona offline e não depende de rede. A regra de ouro do
projeto continua valendo — "NÃO CHUTE CÓDIGO IBGE": o casamento é por NOME
EXATO (ignorando acento e maiúsculas) na coluna `municipio`; nome que não casa
vira ERRO explícito, nunca aproximação.

Uso:
    python -m src.prefeituras.resolver_ibge            # valida o pfc_prefeituras.toml
    python -m src.prefeituras.resolver_ibge --listar   # só imprime a resolução dos 11
"""
from __future__ import annotations

import csv
import os
import sys
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_IBGE = os.path.join(BASE, "data", "ibge_regioes_imediatas_sp.csv")
CONFIG_TOML = os.path.join(BASE, "config", "pfc_prefeituras.toml")

# Os 11 municípios do PFC (mesma lista do plano e do pfc_municipios.toml).
MUNICIPIOS_PFC = [
    "Capela do Alto", "Cesário Lange", "Corumbataí", "Guareí", "Iperó",
    "Juquiá", "Mirassol", "Rio Claro", "Salto", "São Roque", "Tatuí",
]


def _norm(s: str) -> str:
    """minúsculas, sem acento, espaços colapsados — casamento robusto de nome."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


# --------------------------------------------------------------------------- #
# Funções PURAS (sem I/O) — o coração testável
# --------------------------------------------------------------------------- #
def indexar_por_municipio(linhas: list[dict]) -> dict:
    """Índice nome-normalizado -> registro, casando SÓ pela coluna `municipio`
    (nunca pela região). Nomes de município em SP são únicos; se aparecer o
    mesmo nome normalizado duas vezes, é erro de fonte -> levanta."""
    indice = {}
    for r in linhas:
        chave = _norm(r.get("municipio", ""))
        if not chave:
            continue
        if chave in indice:
            raise ValueError(f"nome de município repetido na tabela IBGE: {r.get('municipio')!r}")
        indice[chave] = {
            "municipio": str(r.get("municipio", "")).strip(),
            "cod_ibge": str(r.get("id_municipio", "")).strip(),
            "regiao_imediata_id": str(r.get("regiao_imediata_id", "")).strip(),
            "regiao_imediata_nome": str(r.get("regiao_imediata_nome", "")).strip(),
        }
    return indice


def resolver(municipios: list[str], indice: dict) -> tuple[list[dict], list[str]]:
    """(resolvidos, faltando). Casa por NOME EXATO normalizado. Preserva o nome
    como escrito na config em `nome`, e traz o oficial do IBGE em `municipio`.
    Não aproxima: nome ausente do índice entra em `faltando`."""
    resolvidos, faltando = [], []
    for nome in municipios:
        reg = indice.get(_norm(nome))
        if reg is None:
            faltando.append(nome)
            continue
        resolvidos.append({"nome": nome, **reg})
    return resolvidos, faltando


def validar_resolucao(resolvidos: list[dict], faltando: list[str],
                      esperado: int) -> list[str]:
    """Lista de problemas (vazia = tudo certo): faltando, contagem, código com
    formato inválido (não são 7 dígitos) ou código duplicado."""
    problemas = []
    if faltando:
        problemas.append(f"não resolvidos (nome não casou na tabela IBGE): {faltando}")
    if len(resolvidos) != esperado:
        problemas.append(f"esperava {esperado} municípios, resolvi {len(resolvidos)}")
    for r in resolvidos:
        cod = r.get("cod_ibge", "")
        if not (cod.isdigit() and len(cod) == 7):
            problemas.append(f"código IBGE inválido para {r.get('nome')!r}: {cod!r}")
    codigos = [r.get("cod_ibge") for r in resolvidos]
    if len(set(codigos)) != len(codigos):
        problemas.append(f"códigos IBGE duplicados: {codigos}")
    return problemas


# --------------------------------------------------------------------------- #
# I/O (finas, à volta do núcleo puro)
# --------------------------------------------------------------------------- #
def carregar_tabela_ibge(caminho: str = CSV_IBGE) -> list[dict]:
    """Lê o CSV oficial de municípios × região imediata (utf-8, com BOM)."""
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def resolver_municipios_pfc(municipios: list[str] | None = None,
                            caminho_csv: str = CSV_IBGE) -> tuple[list[dict], list[str]]:
    """Atalho: lê a tabela, indexa e resolve os municípios do PFC."""
    municipios = municipios if municipios is not None else MUNICIPIOS_PFC
    indice = indexar_por_municipio(carregar_tabela_ibge(caminho_csv))
    return resolver(municipios, indice)


def _formatar_toml(resolvidos: list[dict]) -> str:
    """Gera o texto do pfc_prefeituras.toml (fonte editável do painel)."""
    cab = (
        "# =============================================================================\n"
        "# Municípios do PFC — painel de Prefeituras\n"
        "# =============================================================================\n"
        "# Fonte editável do painel. Para ADICIONAR um município: acrescente um bloco\n"
        "# [[municipios]] com o `nome`; depois rode para preencher/validar os códigos:\n"
        "#     python -m src.prefeituras.resolver_ibge\n"
        "#\n"
        "# cod_ibge e regiao_imediata_* são RESOLVIDOS da tabela oficial do IBGE já\n"
        "# versionada no repo (data/ibge_regioes_imediatas_sp.csv) — NUNCA chute.\n"
        "# =============================================================================\n\n"
    )
    blocos = []
    for r in resolvidos:
        blocos.append(
            "[[municipios]]\n"
            f'nome = "{r["nome"]}"\n'
            f'cod_ibge = "{r["cod_ibge"]}"\n'
            f'regiao_imediata_id = "{r["regiao_imediata_id"]}"\n'
            f'regiao_imediata_nome = "{r["regiao_imediata_nome"]}"\n'
        )
    return cab + "\n".join(blocos)


def escrever_toml(caminho: str = CONFIG_TOML) -> list[dict]:
    """(re)gera o pfc_prefeituras.toml a partir da resolução. Levanta se algo
    não bater — nunca grava config com código chutado ou faltando."""
    resolvidos, faltando = resolver_municipios_pfc()
    problemas = validar_resolucao(resolvidos, faltando, len(MUNICIPIOS_PFC))
    if problemas:
        raise ValueError("não vou gravar a config com problemas:\n  - " + "\n  - ".join(problemas))
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write(_formatar_toml(resolvidos))
    return resolvidos


def main(argv: list[str]) -> int:
    resolvidos, faltando = resolver_municipios_pfc()
    problemas = validar_resolucao(resolvidos, faltando, len(MUNICIPIOS_PFC))
    for r in resolvidos:
        print(f"  {r['cod_ibge']}  {r['nome']:<16} · {r['regiao_imediata_nome']}")
    if problemas:
        print("\nPROBLEMAS:")
        for p in problemas:
            print(f"  - {p}")
        return 1
    if "--listar" in argv:
        print(f"\nOK — {len(resolvidos)} municípios resolvidos (só listagem, nada gravado).")
        return 0
    # padrão: valida que o toml em disco bate com a resolução (drift/chute)
    print(f"\nOK — {len(resolvidos)} municípios resolvidos, todos com código IBGE de 7 dígitos.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
