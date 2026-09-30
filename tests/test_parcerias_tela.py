"""AppTest headless: o Radar de Parcerias roteia e renderiza sem exceção.

Semeia o login e radar_escolhido='parcerias' e confirma que a tela aparece.
    python tests/test_parcerias_tela.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest  # noqa: E402

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _run_parcerias():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["user"] = {"nome": "Teste QA", "email": "qa@pfc", "inicial": "Q"}
    at.session_state["radar_escolhido"] = "parcerias"
    at.run()
    return at


def test_tela_parcerias_renderiza():
    at = _run_parcerias()
    assert not at.exception, f"exceção no render: {at.exception}"
    blob = " ".join(str(getattr(m, "value", "")) for m in at.markdown)
    assert "Radar de Parcerias" in blob
    # algum parceiro curado aparece
    assert "Faber-Castell" in blob or "UNICEF" in blob


def test_destino_parcerias_valido():
    from ui.formato import _destino_radar
    assert _destino_radar("parcerias") == "parcerias"
    assert _destino_radar("xpto") == "hub"


if __name__ == "__main__":
    test_destino_parcerias_valido()
    test_tela_parcerias_renderiza()
    print("OK — Radar de Parcerias: roteamento + tela renderizam.")
