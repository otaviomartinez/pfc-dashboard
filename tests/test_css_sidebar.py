"""Testes puros do CSS da sidebar (pastilha colorida por página) — ui/formato.py.

Prova que:
  - SEM `cores`, css_icones_botoes é byte-idêntico à saída de antes (não-regressão
    da sidebar de Captação, que chama sem cores);
  - COM `cores`, cada chave vira uma PASTILHA (fundo tênue da cor + ícone na cor,
    mask cancelado), escopada a .st-key-<chave>;
  - só as chaves em `cores` ganham pastilha;
  - TODO seletor emitido começa em .st-key-<chave> (não vaza pra nav_* nem conteúdo).

    python tests/test_css_sidebar.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.formato import css_icones_botoes  # noqa: E402

MAPA = {"emnav_visao-geral": "visao-geral", "emnav_descobrir": "descobrir",
        "emnav_relatorio": "relatorio", "emenda_logout": "sair"}
ROTULOS = {"emnav_visao-geral": "Visão geral", "emnav_descobrir": "Descobrir"}
CORES = {"emnav_visao-geral": "#8B7BF0", "emnav_descobrir": "#5B9BD5",
         "emnav_relatorio": "#EC6A8C"}
ALVO = "[data-testid='stMarkdownContainer']"


def test_sem_cores_byte_identico():
    # cores=None (default) e cores omitido dão exatamente o mesmo texto — e nenhuma
    # marca de pastilha aparece (prova de não-regressão da Captação).
    a = css_icones_botoes(MAPA, ROTULOS)
    b = css_icones_botoes(MAPA, ROTULOS, None)
    assert a == b
    for marca in ("background-color:#", 'background-image:url("data:image/svg', "mask:none",
                  "width:26px"):
        assert marca not in a, f"marca de pastilha vazou sem cores: {marca}"


def test_com_cores_emite_pastilha_por_chave():
    css = css_icones_botoes(MAPA, ROTULOS, CORES)
    for chave, cor in CORES.items():
        prefixo = (f".st-key-{chave} .stButton>button {ALVO}::before"
                   f"{{width:26px;height:26px;border-radius:8px;flex:none;"
                   f"background-color:{cor}26;")
        assert prefixo in css, f"pastilha ausente/errada para {chave}"
        bloco = css[css.index(prefixo):css.index("}", css.index(prefixo)) + 1]
        assert 'background-image:url("data:image/svg' in bloco   # ícone colorido
        assert "mask:none" in bloco                              # mask base cancelado
        assert cor.replace("#", "%23") in bloco                  # a cor entra no SVG (stroke)


def test_so_chaves_em_cores_ganham_pastilha():
    css = css_icones_botoes(MAPA, ROTULOS, CORES)
    # emenda_logout NÃO está em CORES -> segue com o ícone padrão (mask), sem pastilha
    assert ".st-key-emenda_logout" in css
    assert f".st-key-emenda_logout .stButton>button {ALVO}::before{{width:26px" not in css


def test_todo_seletor_escopado_por_chave():
    # não-vazamento: TODA regra começa em .st-key-<algo>. Como as chaves são emnav_*/
    # emenda_*, nenhum seletor casa nav_* (Captação) nem o conteúdo.
    css = css_icones_botoes(MAPA, ROTULOS, CORES)
    for linha in css.splitlines():
        assert linha.startswith(".st-key-"), f"seletor não escopado: {linha[:70]}"


if __name__ == "__main__":
    test_sem_cores_byte_identico()
    test_com_cores_emite_pastilha_por_chave()
    test_so_chaves_em_cores_ganham_pastilha()
    test_todo_seletor_escopado_por_chave()
    print("OK — testes do CSS da sidebar (pastilha por página) passaram.")
