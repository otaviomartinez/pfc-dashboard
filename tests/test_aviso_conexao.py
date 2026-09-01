"""Aviso visível de Sheets desconectado — app._render_aviso_conexao.

Por que existe: src/dados.py engole exceções e devolve vazio, então falha de
credencial ficava IDÊNTICA a "não há dados" — todas as telas vazias, sem
explicação, parecendo bug do app. O banner precisa aparecer SÓ no modo local:
se aparecesse conectado, viraria poluição permanente.

    python tests/test_aviso_conexao.py
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest  # noqa: E402

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
MARCA = "pfc-aviso-conx"          # classe do banner
USER = {"nome": "Teste QA", "email": "qa@pfc", "inicial": "Q"}


def _render(radar=None):
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["user"] = dict(USER)
    at.session_state["radar_escolhido"] = radar
    at.run()
    assert not at.exception, f"render quebrou ({radar}): {at.exception}"
    return " ".join(m.value for m in at.markdown)


def test_desconectado_mostra_aviso_em_todas_as_telas():
    # hub (sem topnav) e os painéis (via topnav) precisam avisar.
    for radar in (None, "captacao", "emendas"):
        assert MARCA in _render(radar), f"aviso não apareceu em {radar or 'hub'}"


def test_aviso_explica_e_tranquiliza():
    md = _render(None)
    assert "Google Sheets" in md               # diz QUAL é o problema
    assert "Secrets" in md                     # diz ONDE consertar
    assert "nada foi perdido" in md.lower()    # deixa claro que não houve perda


def test_conectado_nao_mostra_aviso():
    from src import dados
    original = dados.carregar_empresas
    dados.carregar_empresas = lambda: (pd.DataFrame(), True)   # simula conectado
    try:
        at = AppTest.from_file(APP, default_timeout=180)
        at.session_state["user"] = dict(USER)
        at.run()
        assert not at.exception, f"render quebrou (conectado): {at.exception}"
        md = " ".join(m.value for m in at.markdown)
        assert MARCA not in md, "aviso apareceu com o Sheets conectado (poluição)"
    finally:
        dados.carregar_empresas = original


if __name__ == "__main__":
    test_desconectado_mostra_aviso_em_todas_as_telas()
    test_aviso_explica_e_tranquiliza()
    test_conectado_nao_mostra_aviso()
    print("OK — aviso de conexão (aparece no modo local, some conectado) passou.")
