"""Testes puros da pastilha POR SEÇÃO na sidebar de Captação — ui/formato.py.

Prova que:
  - Operação (5 chaves nav_*) vira pastilha ÂMBAR #E8873A; Dados (2 chaves) AZUL-AÇO
    #5B9BD5; footer (trocar_radar/logout) fica NEUTRO (sem pastilha);
  - SEM cores, a saída da Captação é byte-idêntica à de antes;
  - TODO seletor começa em .st-key- e NÃO há 'emnav_' (não vaza pra Emendas);
  - NÃO-REGRESSÃO do Commit 1: o MESMO helper ainda colore Emendas (emnav_*)
    idêntico (pastilha #8B7BF026 na Visão Geral).

    python tests/test_css_sidebar_captacao.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.formato import css_icones_botoes  # noqa: E402

ALVO = "[data-testid='stMarkdownContainer']"
OPERACAO = ["nav_visao-geral", "nav_radar", "nav_ranking", "nav_funil", "nav_relatorio"]
DADOS = ["nav_metodologia", "nav_verificacao"]
NAV_ICONES = {"nav_visao-geral": "visao-geral", "nav_radar": "radar", "nav_ranking": "ranking",
              "nav_funil": "funil", "nav_relatorio": "relatorio",
              "nav_metodologia": "metodologia", "nav_verificacao": "verificacao",
              "trocar_radar": "trocar-radar", "logout": "sair"}
NAV_ROTULOS = {**{k: k for k in NAV_ICONES}}
NAV_CORES = {**{k: "#E8873A" for k in OPERACAO}, **{k: "#5B9BD5" for k in DADOS}}
COR = {"#E8873A": "âmbar", "#5B9BD5": "azul-aço"}


def _pastilha_bloco(css, chave):
    pre = (f".st-key-{chave} .stButton>button {ALVO}::before"
           f"{{width:26px;height:26px;border-radius:8px;flex:none;background-color:")
    assert pre in css, f"pastilha ausente para {chave}"
    i = css.index(pre)
    return css[i:css.index("}", i) + 1]


def test_operacao_ambar():
    css = css_icones_botoes(NAV_ICONES, NAV_ROTULOS, NAV_CORES)
    for k in OPERACAO:
        bloco = _pastilha_bloco(css, k)
        assert "background-color:#E8873A26" in bloco, f"{k} não está âmbar"
        assert "%23E8873A" in bloco and "mask:none" in bloco  # ícone âmbar no SVG + mask off


def test_dados_azul_aco():
    css = css_icones_botoes(NAV_ICONES, NAV_ROTULOS, NAV_CORES)
    for k in DADOS:
        bloco = _pastilha_bloco(css, k)
        assert "background-color:#5B9BD526" in bloco, f"{k} não está azul-aço"
        assert "%235B9BD5" in bloco and "mask:none" in bloco


def test_footer_neutro():
    css = css_icones_botoes(NAV_ICONES, NAV_ROTULOS, NAV_CORES)
    for k in ("trocar_radar", "logout"):
        assert ".st-key-" + k in css  # ainda tem o ícone padrão (mask)
        assert f".st-key-{k} .stButton>button {ALVO}::before{{width:26px" not in css


def test_sem_cores_byte_identico():
    a = css_icones_botoes(NAV_ICONES, NAV_ROTULOS)
    b = css_icones_botoes(NAV_ICONES, NAV_ROTULOS, None)
    assert a == b
    for marca in ("background-color:#", "width:26px"):
        assert marca not in a


def test_escopo_nav_sem_vazar_emendas():
    css = css_icones_botoes(NAV_ICONES, NAV_ROTULOS, NAV_CORES)
    for linha in css.splitlines():
        assert linha.startswith(".st-key-"), f"seletor não escopado: {linha[:70]}"
    assert "emnav_" not in css, "vazou seletor de Emendas na CSS da Captação"


def test_nao_regressao_emendas_no_mesmo_helper():
    # O helper compartilhado continua colorindo Emendas idêntico (pastilha violeta).
    em_icones = {"emnav_visao-geral": "visao-geral", "emnav_relatorio": "relatorio"}
    em_cores = {"emnav_visao-geral": "#8B7BF0", "emnav_relatorio": "#EC6A8C"}
    css = css_icones_botoes(em_icones, em_icones, em_cores)
    bloco = _pastilha_bloco(css, "emnav_visao-geral")
    assert "background-color:#8B7BF026" in bloco and "%238B7BF0" in bloco
    assert "nav_" not in css.replace("emnav_", "")  # nenhuma chave nav_ da Captação vazou


if __name__ == "__main__":
    test_operacao_ambar()
    test_dados_azul_aco()
    test_footer_neutro()
    test_sem_cores_byte_identico()
    test_escopo_nav_sem_vazar_emendas()
    test_nao_regressao_emendas_no_mesmo_helper()
    print("OK — testes da pastilha por seção (Captação) + não-regressão de Emendas passaram.")
