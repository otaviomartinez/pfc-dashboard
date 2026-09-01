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


def test_aviso_mostra_o_motivo_real():
    md = _render(None)
    assert "Motivo" in md, "o aviso não trouxe o motivo da falha"
    assert "__MOTIVO__" not in md, "placeholder do motivo vazou para a tela"


def test_motivo_nunca_vaza_a_chave_privada():
    """O motivo vai para a TELA — não pode carregar pedaço da chave privada."""
    from src.dados import _sanitizar_erro
    chave = ("-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0B\n"
             "SEGREDO123\n-----END PRIVATE KEY-----\n")
    saida = _sanitizar_erro(ValueError(f"Could not parse: {chave} conta x"))
    assert "BEGIN PRIVATE KEY" not in saida
    assert "SEGREDO123" not in saida
    assert "[chave omitida]" in saida
    # sequência longa tipo base64 (chave colada sem cabeçalho) também sai:
    longo = _sanitizar_erro(ValueError("tok AAAAB3NzaC1yc2EAAAADAQABAAABgQDZ123456789abcdefghij"))
    assert "[omitido]" in longo
    # e a mensagem fica curta o suficiente para caber no banner:
    assert len(_sanitizar_erro(ValueError("x" * 900))) <= 180


if __name__ == "__main__":
    test_desconectado_mostra_aviso_em_todas_as_telas()
    test_aviso_explica_e_tranquiliza()
    test_aviso_mostra_o_motivo_real()
    test_motivo_nunca_vaza_a_chave_privada()
    test_conectado_nao_mostra_aviso()
    print("OK — aviso de conexão (aparece no modo local, some conectado) passou.")
