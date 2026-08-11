"""AppTest headless: fim da aba 'Descobrir' + fusão na Visão geral (Frente 1).

Confirma que (a) a aba 'Descobrir' sumiu da navegação da sidebar; (b) a Visão geral
com escopo Estadual renderiza sem exceção e mostra a lista unificada ('quem abordar').
Semeia o session_state pra passar do login e cair na página.
    python tests/test_descobrir_unificado.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest  # noqa: E402

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


def _run_visao(escopo="Estadual"):
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["user"] = {"nome": "Teste QA", "email": "qa@pfc", "inicial": "Q"}
    at.session_state["radar_escolhido"] = "emendas"
    at.session_state["emenda_page"] = "Visão geral"
    at.session_state["emenda_escopo_filtro"] = escopo
    at.run()
    return at


def test_aba_descobrir_sumiu_e_visao_mostra_lista():
    at = _run_visao("Estadual")
    assert not at.exception, f"exceção no render: {at.exception}"
    # (a) 'Descobrir' não é mais um botão de navegação
    labels = [str(getattr(b, "label", "")) for b in at.button]
    assert not any("Descobrir" in x for x in labels), f"'Descobrir' ainda na nav: {labels}"
    # (b) a lista unificada aparece abaixo da capa
    blob = " ".join(str(getattr(m, "value", "")) for m in at.markdown)
    assert "quem abordar" in blob


def test_legado_descobrir_cai_na_visao_sem_quebrar():
    # sessão antiga apontando pra 'Descobrir' (aposentada) não pode quebrar
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["user"] = {"nome": "Q", "email": "q@q", "inicial": "Q"}
    at.session_state["radar_escolhido"] = "emendas"
    at.session_state["emenda_page"] = "Descobrir"   # legado
    at.run()
    assert not at.exception


if __name__ == "__main__":
    test_aba_descobrir_sumiu_e_visao_mostra_lista()
    test_legado_descobrir_cai_na_visao_sem_quebrar()
    print("OK — fim da aba Descobrir + fusão na Visão geral (Frente 1) passou.")
