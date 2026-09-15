"""PASSO 1 — resolução dos códigos IBGE dos municípios do PFC (offline).

Garante que os 11 municípios resolvem para um código IBGE oficial de 7 dígitos,
sem duplicata, casando por NOME EXATO (nunca por substring/aproximação), e que
o config/pfc_prefeituras.toml em disco bate com a tabela oficial (sem chute).

    python tests/test_prefeituras_ibge.py
"""
import os
import sys
import tomllib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prefeituras.resolver_ibge import (  # noqa: E402
    CONFIG_TOML,
    MUNICIPIOS_PFC,
    _norm,
    carregar_tabela_ibge,
    indexar_por_municipio,
    resolver,
    resolver_municipios_pfc,
    validar_resolucao,
)


def _indice():
    return indexar_por_municipio(carregar_tabela_ibge())


def test_onze_resolvidos_sem_problema():
    resolvidos, faltando = resolver_municipios_pfc()
    assert faltando == [], f"nomes que não casaram: {faltando}"
    assert len(resolvidos) == 11
    assert validar_resolucao(resolvidos, faltando, len(MUNICIPIOS_PFC)) == []


def test_codigos_sao_7_digitos_sp_sem_duplicata():
    resolvidos, _ = resolver_municipios_pfc()
    codigos = [r["cod_ibge"] for r in resolvidos]
    assert all(c.isdigit() and len(c) == 7 for c in codigos), codigos
    assert all(c.startswith("35") for c in codigos), f"não-SP no meio: {codigos}"  # 35 = SP
    assert len(set(codigos)) == 11, f"código IBGE duplicado: {codigos}"


def test_casa_por_nome_exato_nao_por_substring():
    indice = _indice()
    # 'Rio Claro' é município E nome de região imediata: tem de pegar o MUNICÍPIO.
    resolvidos, faltando = resolver(["Rio Claro"], indice)
    assert faltando == []
    assert resolvidos[0]["cod_ibge"] == "3543907"
    # um pedaço de nome NÃO pode casar (nada de aproximação):
    _, faltando_parcial = resolver(["Rio"], indice)
    assert faltando_parcial == ["Rio"]


def test_nome_desconhecido_vira_faltando_nunca_aproxima():
    indice = _indice()
    resolvidos, faltando = resolver(["Municipio Inexistente XYZ"], indice)
    assert resolvidos == []
    assert faltando == ["Municipio Inexistente XYZ"]


def test_ignora_acento_e_caixa():
    indice = _indice()
    resolvidos, faltando = resolver(["SAO ROQUE", "cesario lange"], indice)
    assert faltando == []
    assert {r["cod_ibge"] for r in resolvidos} == {"3550605", "3511607"}


def test_toml_em_disco_bate_com_a_tabela_oficial():
    # o config não pode ter código chutado/defasado: cada entrada tem de ser
    # idêntica ao que a tabela oficial do IBGE devolve para aquele nome.
    with open(CONFIG_TOML, "rb") as f:
        cfg = tomllib.load(f)
    entradas = cfg["municipios"]
    assert len(entradas) == 11
    indice = _indice()
    for e in entradas:
        oficial = indice[_norm(e["nome"])]
        assert e["cod_ibge"] == oficial["cod_ibge"], e["nome"]
        assert e["regiao_imediata_id"] == oficial["regiao_imediata_id"], e["nome"]
        assert e["regiao_imediata_nome"] == oficial["regiao_imediata_nome"], e["nome"]


if __name__ == "__main__":
    test_onze_resolvidos_sem_problema()
    test_codigos_sao_7_digitos_sp_sem_duplicata()
    test_casa_por_nome_exato_nao_por_substring()
    test_nome_desconhecido_vira_faltando_nunca_aproxima()
    test_ignora_acento_e_caixa()
    test_toml_em_disco_bate_com_a_tabela_oficial()
    print("OK — PASSO 1: 11 códigos IBGE resolvidos, config bate com a tabela oficial.")
