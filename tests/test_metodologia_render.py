"""AppTest headless da tela Metodologia de Emendas — confirma que renderiza sem
exceção e que o conteúdo de Emendas aparece. Semeia o session_state pra passar do
gate de login e cair direto na página (modo local/CSV é suficiente).
    python tests/test_metodologia_render.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest  # noqa: E402

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _run_metodologia():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["user"] = {"nome": "Teste QA", "email": "qa@pfc", "inicial": "Q"}
    at.session_state["radar_escolhido"] = "emendas"
    at.session_state["emenda_page"] = "Metodologia"
    at.run()
    return at


def test_metodologia_emendas_renderiza_sem_excecao():
    at = _run_metodologia()
    assert not at.exception, f"exceção no render: {at.exception}"
    blob = " ".join(str(getattr(m, "value", "")) for m in at.markdown)
    assert "Como o Score de Emendas é calculado" in blob   # é a Metodologia de Emendas
    assert "Regra de ouro" in blob                          # callout da golden rule
    assert "Estadual" in blob                               # escopo estadual
    assert "Federal" in blob or "Senador" in blob           # escopo curado


if __name__ == "__main__":
    test_metodologia_emendas_renderiza_sem_excecao()
    print("OK — AppTest da Metodologia de Emendas passou.")
