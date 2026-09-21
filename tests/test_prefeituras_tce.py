"""Índice de ensino do TCE-SP (AUDESP) — src/prefeituras/tce.py.

Por que esta fonte existe: o SICONFI NÃO publica o RREO-Anexo 08 (MDE) para os
nossos municípios (varrido 2023-2025 x períodos 1-6, nada). O TCE-SP publica os
644 municípios de SP, 2016-2025, e o índice é APURADO pelo Tribunal — a versão
forte da regra 5(a): "julgado", não "declarado".

A armadilha do formato: a coluna vem como FRAÇÃO (0,2736 = 27,36%). Esquecer o
x100 mostraria "0,27%" e faria o painel acusar TODO MUNDO de descumprir a
Constituição — exatamente o tipo de erro que já cometemos uma vez.

    python tests/test_prefeituras_tce.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prefeituras import tce  # noqa: E402
from src.prefeituras.config import carregar_municipios  # noqa: E402

TEM_ARQUIVO = os.path.isfile(tce.CSV_TCE)


def test_arquivo_do_tce_esta_versionado():
    assert TEM_ARQUIVO, f"falta {tce.CSV_TCE}"


def test_fracao_vira_porcentagem():
    """0,2736 -> 27,36. O x100 é o ponto crítico desta fonte."""
    dados = tce.carregar(2025)
    assert dados, "nenhum município lido"
    for cod, reg in list(dados.items())[:50]:
        assert 0 < reg["percentual"] <= 100, (cod, reg["percentual"])
    # um município concreto, conferido contra o arquivo:
    assert dados["3521002"]["percentual"] == 27.36, dados["3521002"]


def test_cobre_os_onze_municipios_do_pfc():
    dados = tce.carregar(2025)
    faltando = [m["nome"] for m in carregar_municipios()
                if m["cod_ibge"] not in dados]
    assert not faltando, f"sem índice do TCE: {faltando}"


def test_marca_a_origem_para_a_ui_rotular_certo():
    """A UI muda o texto de procedência conforme a origem (apurado x declarado)."""
    for reg in list(tce.carregar(2025).values())[:5]:
        assert reg["origem"] == "tce-sp"
        assert reg["exercicio"] == 2025


def test_exercicios_disponiveis():
    anos = tce.exercicios_disponiveis()
    assert 2025 in anos and 2016 in anos
    assert anos == sorted(anos, reverse=True)


def test_loader_gracioso_sem_arquivo():
    assert tce.carregar(2025, "/nao/existe.csv") == {}
    assert tce.exercicios_disponiveis("/nao/existe.csv") == []


def test_ano_inexistente_devolve_vazio_em_vez_de_inventar():
    assert tce.carregar(1999) == {}


if __name__ == "__main__":
    test_arquivo_do_tce_esta_versionado()
    test_fracao_vira_porcentagem()
    test_cobre_os_onze_municipios_do_pfc()
    test_marca_a_origem_para_a_ui_rotular_certo()
    test_exercicios_disponiveis()
    test_loader_gracioso_sem_arquivo()
    test_ano_inexistente_devolve_vazio_em_vez_de_inventar()
    print("OK — índice de ensino do TCE-SP (11/11, fração->%, origem) passou.")
