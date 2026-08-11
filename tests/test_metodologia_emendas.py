"""Teste puro do conteúdo da Metodologia de Emendas.

Trava os pesos REAIS do Estadual (config/pfc_municipios.toml), os três escopos,
a régua curada do Federal/Senador e a regra de ouro. Sem Streamlit/Sheets.
    python tests/test_metodologia_emendas.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.formato import _modo_emenda, metodologia_emendas_conteudo  # noqa: E402


def test_tres_escopos_e_golden_rule():
    c = metodologia_emendas_conteudo()
    assert "estadual" in c and "federal_senador" in c
    gr = c["golden_rule"].lower()
    assert "somada" in gr and "separad" in gr        # aut/pago separados, faixa não somada
    tit = c["federal_senador"]["titulo"]
    assert "Federal" in tit and "Senador" in tit     # os três escopos nomeados


def test_pesos_estaduais_sao_os_reais_do_toml():
    est = metodologia_emendas_conteudo()["estadual"]
    assert est["fator_vizinho"] == 0.45              # DIRETO cheio / VIZINHO 0,45× / LONGE 0
    terr = {p["n"]: p["w"] for p in est["secoes"][0]["pesos"]}
    assert terr == {"Volume": 45, "Alinhamento": 30, "Presença": 25}
    exp = {p["n"]: p["w"] for p in est["secoes"][1]["pesos"]}
    assert exp == {"Volume geral": 45, "Alinhamento": 40, "Proximidade": 15}
    # cada seção soma 100 (o toml exige pesos somando 1.0)
    assert sum(terr.values()) == 100 and sum(exp.values()) == 100


def test_federal_curado_criterios_e_faixa():
    fs = metodologia_emendas_conteudo()["federal_senador"]
    nomes = [cr["n"] for cr in fs["criterios"]]
    assert "Aderência" in nomes and "Chance" in nomes
    assert "curado" in fs["resumo"].lower()          # honesto: não recalculado pelo app
    assert "sugerida" in fs["valor"].lower()         # faixa sugerida (golden rule)


def test_modo_emenda_roteia_metodologia():
    assert _modo_emenda("Metodologia") == "metodologia"


if __name__ == "__main__":
    test_tres_escopos_e_golden_rule()
    test_pesos_estaduais_sao_os_reais_do_toml()
    test_federal_curado_criterios_e_faixa()
    test_modo_emenda_roteia_metodologia()
    print("OK — testes da Metodologia de Emendas passaram.")
