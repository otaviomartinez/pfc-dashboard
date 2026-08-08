"""Teste puro do roteador de destino do hub (Prospecção Frente 1 · navegação).

`_destino_radar` decide qual painel a raiz renderiza a partir de
session_state['radar_escolhido']. Sem Streamlit/Sheets. Rodar da raiz:

    python tests/test_destino_radar.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.formato import _destino_radar  # noqa: E402


def test_tres_destinos_mapeiam_para_si():
    assert _destino_radar("captacao") == "captacao"
    assert _destino_radar("emendas") == "emendas"
    assert _destino_radar("prospeccao") == "prospeccao"


def test_none_vai_para_hub():
    assert _destino_radar(None) == "hub"


def test_legado_ou_desconhecido_cai_no_hub():
    # valor corrompido/legado → Central (fallback são), nunca uma tela errada
    assert _destino_radar("lixo") == "hub"
    assert _destino_radar("") == "hub"
    assert _destino_radar("captação") == "hub"   # com acento não é a chave canônica


if __name__ == "__main__":
    test_tres_destinos_mapeiam_para_si()
    test_none_vai_para_hub()
    test_legado_ou_desconhecido_cai_no_hub()
    print("OK — testes do roteador de destino (Prospecção nav) passaram.")
