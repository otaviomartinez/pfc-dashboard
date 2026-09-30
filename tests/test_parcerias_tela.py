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


def test_hub_tem_botoes_ladeando_os_radares():
    """Os mini-cards de Prospecção/Parcerias eram position:absolute nos cantos e
    se SOBREPUNHAM aos cards-herói (o print do usuário mostrou a pilha). Viraram
    botões no fluxo normal, um de cada LADO dos radares:
    atalho · radar · radar · atalho."""
    from ui import estilos
    assert "hub-minibtn" in estilos._HUB_CSS
    assert ".hub-card.c3{position:absolute" not in estilos._HUB_CSS
    assert ".hub-card.c4{position:absolute" not in estilos._HUB_CSS
    js = estilos._HUB_JS
    assert "card('c3'" not in js and "card('c4'" not in js
    ordem = [js.index("mini('m3'"), js.index("card('c1'"),
             js.index("card('c2'"), js.index("mini('m4'")]
    assert ordem == sorted(ordem), "ordem esperada: atalho · radar · radar · atalho"


def test_clique_cobre_o_card_inteiro():
    """BUG REAL: eu posicionava o `.stButton` com inset:0, mas o pai dele
    (stElementContainer, que o Streamlit posiciona) virava a referência — então
    o clique só pegava a faixa do botão, embaixo do card. O certo é posicionar o
    CONTAINER do botão (st-key-<chave>), como faz o .dd-cell do Descobrir.
    Verificado em Chromium: nos 5 pontos do card, elementFromPoint devolve o
    botão."""
    import ast as _ast
    fonte = open(APP, encoding="utf-8").read()
    css = next(n.value.value for n in _ast.parse(fonte).body
               if isinstance(n, _ast.Assign)
               and getattr(n.targets[0], "id", "") == "_PARCERIAS_CSS")
    assert '[class*="st-key-pc_"] [class*="st-key-parc_ver_"]{position:absolute' in css
    assert '[class*="st-key-pc_"] .stButton{position:absolute' not in css, \
        "posicionar o .stButton é o bug — o pai dele vira a referência"
    assert 'pointer-events:none' in css, "o card não pode comer o clique"


def test_modulos_saem_da_tela():
    """O Fábio não precisa distinguir M1/M2/M3/M4 para decidir quem abordar."""
    fonte = open(APP, encoding="utf-8").read()
    assert "_mods_txt" not in fonte
    assert "MODULOS_PFC" not in fonte, "nem no filtro, nem no dossiê"


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
    test_hub_tem_botoes_ladeando_os_radares()
    test_clique_cobre_o_card_inteiro()
    test_modulos_saem_da_tela()
    test_selo_de_canal_reflete_a_direcao()
    test_tela_parcerias_renderiza()
    print("OK — Radar de Parcerias: roteamento + tela renderizam.")
