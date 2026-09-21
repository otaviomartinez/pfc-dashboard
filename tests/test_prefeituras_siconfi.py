"""Parsers do SICONFI — src/prefeituras/siconfi.py (PUROS, sem rede).

O FORMATO aqui não é suposto: veio do log real do GitHub Actions, onde a API
respondeu 489 linhas com as colunas
  ['exercicio','demonstrativo','periodo','periodicidade','instituicao',
   'cod_ibge','uf','populacao','anexo','esfera','rotulo','coluna']
O parser antigo procurava 'conta'/'vl_conta' e por isso lia ZERO de 489 — o bug
que estes testes agora travam. A medida (%) vem na coluna `coluna`, não no
rótulo.

Ainda falta a fixture REAL salva (o dev não alcança o Tesouro: gateway 403).
Rode `python scripts/capturar_fixture_siconfi.py` para fechar essa dívida; o
último teste passa a validar contra ela sozinho.

    python tests/test_prefeituras_siconfi.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prefeituras import siconfi  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "fixtures", "siconfi_rreo_anexo08.json")


def _linha(rotulo, valor, coluna="Até o Bimestre", exercicio=2025, periodo=6):
    """Linha no formato REAL da API (rotulo/coluna/valor), visto no log."""
    return {"rotulo": rotulo, "coluna": coluna, "valor": valor,
            "exercicio": exercicio, "periodo": periodo}


def test_numero_tolera_formato_brasileiro():
    assert siconfi._num("1.234,56") == 1234.56
    assert siconfi._num(1234.56) == 1234.56
    assert siconfi._num("R$ 2.000,00") == 2000.0
    assert siconfi._num("") is None and siconfi._num(None) is None
    assert siconfi._num("abc") is None


def test_percentual_vem_da_coluna_nao_do_rotulo():
    """A medida (%) está em `coluna` — foi o que o parser antigo não viu."""
    itens = [_linha("Aplicação em MDE", 27.4, coluna="% Aplicado Até o Bimestre")]
    mde = siconfi.extrair_mde(itens)
    assert mde["percentual"] == 27.4
    assert mde["exercicio"] == 2025 and mde["periodo"] == 6


def test_aceita_formato_antigo_conta_por_compatibilidade():
    """A chave `conta` continua valendo — mas a conta tem de ser a de MDE.

    (Este teste usava "Aplicação em ensino", que hoje é REJEITADO de propósito:
    era o casamento frouxo que deixou a fatia de educação virar índice de MDE.)
    """
    itens = [{"conta": "Aplicação em MDE", "coluna": "% Aplicado",
              "valor": 26.0, "exercicio": 2025, "periodo": 6}]
    assert siconfi.extrair_mde(itens)["percentual"] == 26.0
    frouxo = [{"conta": "Aplicação em ensino", "coluna": "% Aplicado",
               "valor": 26.0, "exercicio": 2025, "periodo": 6}]
    assert siconfi.extrair_mde(frouxo) is None


def test_percentual_calculado_quando_nao_vem_pronto():
    itens = [_linha("TOTAL DAS DESPESAS PARA FINS DE LIMITE", 2_500_000.0),
             _linha("RECEITA RESULTANTE DE IMPOSTOS", 10_000_000.0)]
    mde = siconfi.extrair_mde(itens)
    assert mde["percentual"] == 25.0
    assert mde["valor_aplicado"] == 2_500_000.0
    assert mde["receita_base"] == 10_000_000.0


def test_sem_exercicio_o_dado_nao_existe():
    """Regra de honestidade: percentual sem exercício amarrado -> None."""
    itens = [{"rotulo": "Aplicação em MDE", "coluna": "% Aplicado",
              "valor": 26.0}]   # sem exercício
    assert siconfi.extrair_mde(itens) is None
    # mas se o chamador souber o exercício, vale:
    assert siconfi.extrair_mde(itens, 2025, 6)["percentual"] == 26.0


def test_vazio_devolve_none_nao_zero():
    """None != 0: 'não veio dado' nunca pode virar 'aplicou 0%'."""
    assert siconfi.extrair_mde([]) is None
    assert siconfi.extrair_mde(None) is None
    assert siconfi.extrair_caixa([]) is None


def test_extrai_caixa():
    itens = [_linha("DISPONIBILIDADE DE CAIXA BRUTA", 5_000_000.0)]
    assert siconfi.extrair_caixa(itens)["disponibilidade"] == 5_000_000.0
    assert siconfi.extrair_caixa([_linha("OUTRA COISA", 10.0)]) is None


def test_fallback_manual_ausente_nao_quebra():
    assert siconfi.ler_manual(1999) == []
    assert siconfi.mde_do_manual("3510302", 1999) is None


def test_fixture_real_se_existir():
    """Fecha a dívida assim que alguém rodar scripts/capturar_fixture_siconfi.py."""
    if not os.path.isfile(FIXTURE):
        print("   (fixture real ainda não capturada — rode "
              "scripts/capturar_fixture_siconfi.py na sua máquina)")
        return
    with open(FIXTURE, encoding="utf-8") as f:
        itens = json.load(f).get("items") or []
    mde = siconfi.extrair_mde(itens)
    assert mde is not None, "o parser não entendeu a resposta REAL do SICONFI"
    assert 0 < mde["percentual"] <= 100
    assert mde["exercicio"]


def test_nao_confunde_fatia_de_educacao_com_indice_de_mde():
    """O bug que inventou 9 municípios "abaixo do mínimo".

    O RREO-Anexo 02 (Despesas por Função) traz a EDUCAÇÃO como fatia da despesa
    total — um número que cai perto de 25% e passava por índice de MDE. Só vale
    a conta que diz MDE ou "manutenção e desenvolvimento do ensino".
    """
    fatia = [_linha("Educação", 25.48, coluna="% (b/total b)")]
    assert siconfi.extrair_mde(fatia) is None, "fatia de educação virou MDE"

    subconta = [_linha("Ensino Fundamental", 18.2, coluna="% (c/a)")]
    assert siconfi.extrair_mde(subconta) is None, "subconta de ensino virou MDE"

    real = [_linha("APLICAÇÃO EM MDE SOBRE A RECEITA LÍQUIDA", 27.9,
                   coluna="% Aplicado Até o Bimestre")]
    assert siconfi.extrair_mde(real)["percentual"] == 27.9


def test_casamento_ignora_acento():
    """Sem strip de acento, "Manutenção..." nunca casava e o MDE passava batido."""
    assert siconfi._casa("Manutenção e Desenvolvimento do Ensino",
                         "manutencao e desenvolvimento")
    por_extenso = [_linha("Manutenção e Desenvolvimento do Ensino", 26.1,
                          coluna="% Mínimo Aplicado")]
    assert siconfi.extrair_mde(por_extenso)["percentual"] == 26.1


if __name__ == "__main__":
    test_numero_tolera_formato_brasileiro()
    test_percentual_vem_da_coluna_nao_do_rotulo()
    test_aceita_formato_antigo_conta_por_compatibilidade()
    test_percentual_calculado_quando_nao_vem_pronto()
    test_sem_exercicio_o_dado_nao_existe()
    test_vazio_devolve_none_nao_zero()
    test_extrai_caixa()
    test_fallback_manual_ausente_nao_quebra()
    test_nao_confunde_fatia_de_educacao_com_indice_de_mde()
    test_casamento_ignora_acento()
    test_fixture_real_se_existir()
    print("OK — parsers do SICONFI (MDE, caixa, fallback manual) passaram.")
