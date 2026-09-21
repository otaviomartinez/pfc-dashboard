"""Config do painel Prefeituras — src/prefeituras/config.py.

O plano proíbe chutar código IBGE. O risco real: código errado faz o SICONFI
responder VAZIO em silêncio (o pior bug deste projeto). Por isso o carregamento
reconfere cada código contra data/ibge_regioes_imediatas_sp.csv e falha nomeando
o município. Estes testes travam esse contrato.

    python tests/test_prefeituras_config.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prefeituras.config import (  # noqa: E402
    carregar_municipios, municipios_da_regiao, normalizar_nome,
)

ESPERADOS = {"Capela do Alto", "Cesário Lange", "Corumbataí", "Guareí", "Iperó",
             "Juquiá", "Mirassol", "Rio Claro", "Salto", "São Roque", "Tatuí"}


def test_carrega_os_onze_sem_duplicata():
    muns = carregar_municipios()
    assert len(muns) == 11, f"esperado 11 municípios, veio {len(muns)}"
    assert {m["nome"] for m in muns} == ESPERADOS
    cods = [m["cod_ibge"] for m in muns]
    assert len(cods) == len(set(cods)), "cod_ibge duplicado"


def test_todo_municipio_tem_codigo_de_7_digitos_e_regiao():
    for m in carregar_municipios():
        assert m["cod_ibge"].isdigit() and len(m["cod_ibge"]) == 7, m
        assert m["cod_ibge"].startswith("35"), f"{m['nome']} não é de SP: {m['cod_ibge']}"
        assert m["regiao_imediata"], f"{m['nome']} sem região imediata"
        assert m["grupo"], f"{m['nome']} sem grupo"


def test_codigo_errado_derruba_com_o_nome_do_municipio(tmp=None):
    import tempfile
    toml = ('[[grupos]]\nnome = "T"\n'
            '[[grupos.municipios]]\nnome = "Iperó"\ncod_ibge = "3500000"\n'
            'regiao_imediata = "Sorocaba"\n')
    with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False,
                                     encoding="utf-8") as f:
        f.write(toml)
        caminho = f.name
    try:
        erro = ""
        try:
            carregar_municipios(caminho)
        except ValueError as e:
            erro = str(e)
        assert "Iperó" in erro and "3500000" in erro, f"erro pouco explícito: {erro!r}"
    finally:
        os.unlink(caminho)


def test_nome_inexistente_derruba():
    import tempfile
    toml = ('[[grupos]]\nnome = "T"\n'
            '[[grupos.municipios]]\nnome = "Cidade Que Nao Existe"\n'
            'cod_ibge = "3510302"\nregiao_imediata = "X"\n')
    with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False,
                                     encoding="utf-8") as f:
        f.write(toml)
        caminho = f.name
    try:
        erro = ""
        try:
            carregar_municipios(caminho)
        except ValueError as e:
            erro = str(e)
        assert "Cidade Que Nao Existe" in erro
    finally:
        os.unlink(caminho)


def test_normalizar_nome_ignora_acento_e_caixa():
    assert normalizar_nome("São Roque") == normalizar_nome("sao  roque")
    assert normalizar_nome("Iperó") == "ipero"


def test_vizinhos_da_regiao_imediata():
    viz = municipios_da_regiao("Sorocaba")
    nomes = {v["nome"] for v in viz}
    assert "Sorocaba" in nomes and "Iperó" in nomes
    assert len(viz) > 5


if __name__ == "__main__":
    test_carrega_os_onze_sem_duplicata()
    test_todo_municipio_tem_codigo_de_7_digitos_e_regiao()
    test_codigo_errado_derruba_com_o_nome_do_municipio()
    test_nome_inexistente_derruba()
    test_normalizar_nome_ignora_acento_e_caixa()
    test_vizinhos_da_regiao_imediata()
    print("OK — config de Prefeituras (11 municípios, códigos IBGE conferidos) passou.")
