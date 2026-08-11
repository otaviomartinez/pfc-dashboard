"""AppTest headless: federais aparecem na Visão geral (escopo Federal), em dois
blocos, sem quebrar.

Verifica:
  (a) render do escopo Federal sem exceção;
  (b) os blocos "Curados à mão" e "Importados · score por execução real" aparecem;
  (c) o pool CSV continua íntegro como referência para tag/score;
  (d) as funções puras que alimentam a tela (pool novos, tag de execução) batem.

    python tests/test_federais_execucao.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest  # noqa: E402

from ui.formato import (  # noqa: E402
    _anexar_exec_aos_curados, _federais_pool_novos, _fmt_milhoes,
    _mapa_execucao_federal, _norm_nome_fed,
)

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _run_federal():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["user"] = {"nome": "Teste QA", "email": "qa@pfc", "inicial": "Q"}
    at.session_state["radar_escolhido"] = "emendas"
    at.session_state["emenda_page"] = "Visão geral"
    at.session_state["emenda_escopo_filtro"] = "Federal"
    at.run()
    return at


def test_federal_pool_render_dois_blocos():
    # Novo desenho: os federais vêm TODOS da aba (curados + importados). O render
    # divide em dois blocos por origem; ambos os cabeçalhos aparecem sem exceção,
    # independentemente de haver conexão com o Sheets no ambiente de teste.
    at = _run_federal()
    assert not at.exception, f"exceção no render federal: {at.exception}"
    blob = " ".join(str(getattr(m, "value", "")) for m in at.markdown)
    assert "Curados à mão" in blob, "bloco de curados não apareceu"
    assert "Importados · score por execução real" in blob, "bloco de importados não apareceu"


def test_pool_novos_pura():
    novos = _federais_pool_novos()
    assert len(novos) >= 40, f"esperava ~49 novos, veio {len(novos)}"
    # ordenado por execução desc; todos marcados como execução; nenhum é dos 15
    assert novos == sorted(novos, key=lambda d: d["exec_score"], reverse=True)
    assert all(d.get("_execucao") for d in novos)
    assert novos[0]["nome"] == "Marcio Alvino" and novos[0]["exec_score"] == 100


def test_tag_execucao_nos_curados():
    mapa = _mapa_execucao_federal()
    # o pool casa nome->execução (Vitor Lippi baixo, Sâmia no topo)
    assert mapa.get(_norm_nome_fed("Vitor Lippi")) == 8
    assert mapa.get(_norm_nome_fed("Sâmia Bomfim")) == 100
    # _anexar não apaga o score curado, só acrescenta exec_score
    curado = [{"nome": "Vitor Lippi", "score": 97}]
    _anexar_exec_aos_curados(curado)
    assert curado[0]["score"] == 97 and curado[0]["exec_score"] == 8


def test_fmt_milhoes():
    assert _fmt_milhoes(29620329) == "R$ 29,6 mi"
    assert _fmt_milhoes(0) == "R$ 0"
    assert _fmt_milhoes("") == "—"


if __name__ == "__main__":
    test_federal_pool_render_dois_blocos()
    test_pool_novos_pura()
    test_tag_execucao_nos_curados()
    test_fmt_milhoes()
    print("OK — federais do pool de execução aparecem na Visão geral (Federal).")
