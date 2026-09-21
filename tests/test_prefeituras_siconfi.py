"""Parsers do SICONFI — src/prefeituras/siconfi.py (PUROS, sem rede).

ATENÇÃO, DÍVIDA CONHECIDA: o plano pede fixture REAL salva de uma resposta de
verdade. O domínio do Tesouro está bloqueado por política da organização no
ambiente de dev (gateway 403), então os casos abaixo usam estruturas SINTÉTICAS,
rotuladas como tal — nunca apresentadas como resposta real. Para fechar a dívida,
rode na sua máquina:  python scripts/capturar_fixture_siconfi.py
Havendo tests/fixtures/siconfi_rreo_anexo08.json, o teste do fim valida o parser
contra ela automaticamente.

    python tests/test_prefeituras_siconfi.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prefeituras import siconfi  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "fixtures", "siconfi_rreo_anexo08.json")


def _linha(conta, valor, exercicio=2025, periodo=6):
    """Linha SINTÉTICA no formato do RREO (não é resposta real da API)."""
    return {"conta": conta, "valor": valor,
            "exercicio": exercicio, "periodo": periodo}


def test_numero_tolera_formato_brasileiro():
    assert siconfi._num("1.234,56") == 1234.56
    assert siconfi._num(1234.56) == 1234.56
    assert siconfi._num("R$ 2.000,00") == 2000.0
    assert siconfi._num("") is None and siconfi._num(None) is None
    assert siconfi._num("abc") is None


def test_percentual_pronto_na_linha():
    itens = [_linha("APLICAÇÃO EM MDE (%) - MÍNIMO 25%", 27.4)]
    mde = siconfi.extrair_mde(itens)
    assert mde["percentual"] == 27.4
    assert mde["exercicio"] == 2025 and mde["periodo"] == 6


def test_percentual_calculado_quando_nao_vem_pronto():
    itens = [_linha("TOTAL DAS DESPESAS PARA FINS DE LIMITE", 2_500_000.0),
             _linha("RECEITA RESULTANTE DE IMPOSTOS", 10_000_000.0)]
    mde = siconfi.extrair_mde(itens)
    assert mde["percentual"] == 25.0
    assert mde["valor_aplicado"] == 2_500_000.0
    assert mde["receita_base"] == 10_000_000.0


def test_sem_exercicio_o_dado_nao_existe():
    """Regra de honestidade: percentual sem exercício amarrado -> None."""
    itens = [{"conta": "APLICAÇÃO EM MDE (%)", "valor": 26.0}]   # sem exercício
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


if __name__ == "__main__":
    test_numero_tolera_formato_brasileiro()
    test_percentual_pronto_na_linha()
    test_percentual_calculado_quando_nao_vem_pronto()
    test_sem_exercicio_o_dado_nao_existe()
    test_vazio_devolve_none_nao_zero()
    test_extrai_caixa()
    test_fallback_manual_ausente_nao_quebra()
    test_fixture_real_se_existir()
    print("OK — parsers do SICONFI (MDE, caixa, fallback manual) passaram.")
