"""Teste puro do conteúdo da Metodologia de Emendas.

Trava os pesos REAIS do Estadual (config/pfc_municipios.toml), os três escopos,
a régua curada do Federal/Senador e a regra de ouro. Sem Streamlit/Sheets.
    python tests/test_metodologia_emendas.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.formato import (  # noqa: E402
    _modo_emenda,
    explorador_parlamentar_comps,
    metodologia_emendas_conteudo,
)


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


def test_explorador_comps_reais_estadual_e_federal():
    # federal e estadual usam as MESMAS colunas no CRM → mesma estrutura, valores reais
    fed = explorador_parlamentar_comps(
        {"nome": "Vitor Lippi", "escopo_nome": "Federal", "score": 97, "ader": 90, "chance": 70})
    assert fed["total"] == 97 and fed["nome"] == "Vitor Lippi" and fed["escopo_nome"] == "Federal"
    assert fed["comps"] == [{"n": "Aderência", "v": 90, "c": "#8B7BF0"},
                            {"n": "Chance", "v": 70, "c": "#5B9BD5"}]
    est = explorador_parlamentar_comps(
        {"nome": "Ana Lima", "escopo_nome": "Estadual", "score": 61, "ader": 55, "chance": 40})
    assert [c["v"] for c in est["comps"]] == [55, 40]   # componentes reais, não estimados


def test_explorador_campo_faltante_vira_zero_sem_crashar():
    d = explorador_parlamentar_comps({"nome": "X"})
    assert d["total"] == 0 and [c["v"] for c in d["comps"]] == [0, 0]
    assert explorador_parlamentar_comps({})["nome"] == "(sem nome)"


if __name__ == "__main__":
    test_tres_escopos_e_golden_rule()
    test_pesos_estaduais_sao_os_reais_do_toml()
    test_federal_curado_criterios_e_faixa()
    test_modo_emenda_roteia_metodologia()
    test_explorador_comps_reais_estadual_e_federal()
    test_explorador_campo_faltante_vira_zero_sem_crashar()
    print("OK — testes da Metodologia de Emendas passaram.")
