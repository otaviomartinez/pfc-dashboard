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


def test_card_nao_usa_token_de_cor_inexistente():
    """BUG REAL: o CSS usava var(--card,#fff) e var(--linha,…) — tokens que NÃO
    existem neste design system. O fallback #fff pintava o card de BRANCO e o
    texto usava --ink (quase branco): ilegível no print do usuário. Os tokens
    válidos são --bg/--surface/--surface2/--ink/--muted/--dim."""
    import ast as _ast
    arv = _ast.parse(open(APP, encoding="utf-8").read())
    css = next(n.value.value for n in arv.body
               if isinstance(n, _ast.Assign)
               and getattr(n.targets[0], "id", "") == "_PARCERIAS_CSS")
    import re as _re
    regras = _re.sub(r"/\*.*?\*/", "", css, flags=_re.S)   # fora os comentários
    for token in ("--card", "--linha"):
        assert token not in regras, f"{token} não existe no design system"
    assert "#fff" not in regras.lower(), "fundo branco num painel de base #0E1116"
    assert "--surface" in css and "--ink" in css


def test_hub_tem_botoes_no_lugar_dos_cards_flutuantes():
    """Os mini-cards de Prospecção/Parcerias eram position:absolute nos cantos e
    se SOBREPUNHAM aos cards-herói (o print do usuário mostrou a pilha). Viraram
    botões compactos no fluxo normal."""
    from ui import estilos
    assert "hub-minibtn" in estilos._HUB_CSS and "hub-mini{" in estilos._HUB_CSS
    assert "card('c3'" not in estilos._HUB_JS and "card('c4'" not in estilos._HUB_JS
    assert ".hub-card.c3{position:absolute" not in estilos._HUB_CSS
    assert ".hub-card.c4{position:absolute" not in estilos._HUB_CSS


def test_selo_de_canal_reflete_a_direcao():
    """A cor do selo responde 'dá para submeter projeto?' — não é decoração."""
    import ast as _ast
    fonte = open(APP, encoding="utf-8").read()
    arv = _ast.parse(fonte)
    mapa = next(n.value for n in arv.body
                if isinstance(n, _ast.Assign)
                and getattr(n.targets[0], "id", "") == "_CANAL_SELO")
    chaves = {k.value for k in mapa.keys}
    assert chaves == {"recebe projetos", "indefinido", "direção inversa"}
    assert "parc-legenda" in fonte, "cor semântica exige legenda na tela"


def test_destino_parcerias_valido():
    from ui.formato import _destino_radar
    assert _destino_radar("parcerias") == "parcerias"
    assert _destino_radar("xpto") == "hub"


if __name__ == "__main__":
    test_destino_parcerias_valido()
    test_card_nao_usa_token_de_cor_inexistente()
    test_hub_tem_botoes_no_lugar_dos_cards_flutuantes()
    test_selo_de_canal_reflete_a_direcao()
    test_tela_parcerias_renderiza()
    print("OK — Radar de Parcerias: roteamento + tela renderizam.")
