"""Tela e dossiê do painel Prefeituras — harness AppTest (Passos 6, 7 e 8).

Confirma que a tela renderiza SEM exceção mesmo com zero dado baixado (que é o
estado real hoje: Tesouro/TSE bloqueados por política) e que o aviso da REGRA DE
OURO aparece — ele não é decoração, é contrato: ninguém pode ler um percentual
achando que é dinheiro disponível.

Lembrete do CLAUDE.md: o AppTest não substitui conferir na tela. A verificação
visual é do usuário, na URL publicada, depois do push.

    python tests/test_prefeituras_tela.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit.testing.v1 import AppTest  # noqa: E402

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
USER = {"nome": "Teste QA", "email": "qa@pfc", "inicial": "Q"}


def _render(page="Prefeituras"):
    at = AppTest.from_file(APP, default_timeout=200)
    at.session_state["user"] = dict(USER)
    at.session_state["radar_escolhido"] = "emendas"
    at.session_state["emenda_page"] = page
    at.run()
    assert not at.exception, f"render de '{page}' quebrou: {at.exception}"
    return at


def test_tela_renderiza_sem_dado_nenhum():
    at = _render()
    md = " ".join(m.value for m in at.markdown)
    assert 'class="pf-cell"' in md, "nenhum card de município"
    assert md.count('class="pf-cell"') == 11, "esperados os 11 municípios"


def test_aviso_da_regra_de_ouro_e_obrigatorio():
    md = " ".join(m.value for m in _render().markdown)
    assert "não verba disponível" in md
    assert "saúde fiscal" in md


def test_municipio_sem_dado_nao_some_nem_vira_zero():
    """Sem CSV baixado, tudo é 'sem dado' — e NENHUM vira 0%."""
    md = " ".join(m.value for m in _render().markdown)
    assert "sem dado" in md.lower()
    assert "0,0%" not in md, "município sem dado virou 0% (deveria ser 'sem dado')"


def test_pagina_esta_na_sidebar_de_emendas():
    # NÃO importar app.py aqui: ele tem trava de login no topo do módulo e
    # estoura KeyError('user') fora do AppTest. Lê-se o fonte, como texto.
    from ui.formato import _modo_emenda
    assert _modo_emenda("Prefeituras") == "prefeituras"
    fonte = open(APP, encoding="utf-8").read()
    assert '"Prefeituras",' in fonte, "página não entrou em EMENDA_PAGES"
    assert '"emnav_prefeituras": "prefeitura"' in fonte, "sem ícone na sidebar"
    assert '"emnav_prefeituras": "#4FA8A0"' in fonte, "sem cor de pastilha"


def test_outras_paginas_de_emendas_seguem_de_pe():
    """Não regredir o que já existia ao acrescentar a página."""
    for page in ("Visão geral", "Territórios em Aberto", "Metodologia"):
        _render(page)


def test_pdf_do_municipio_com_campos_ausentes():
    """Omissão graciosa: dossiê quase vazio não pode quebrar o PDF."""
    import datetime

    from src.relatorios import pdf_resumo_prefeitura
    pdf = pdf_resumo_prefeitura({"municipio": "Guareí"},
                                datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
    assert pdf[:4] == b"%PDF" and len(pdf) > 800


def test_ponte_para_prospeccao_usa_tipo_e_etapa_que_existem():
    """O tipo 'Prefeitura' e a etapa inicial precisam ser os canônicos."""
    from ui.formato import PROSPECCAO_TIPOS
    assert "Prefeitura" in PROSPECCAO_TIPOS
    fonte = open(APP, encoding="utf-8").read()
    assert '"Tipo": "Prefeitura"' in fonte
    assert '"Status": PROSPECCAO_ETAPAS[0]' in fonte, \
        "a etapa inicial não pode ser um texto inventado"


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
    print("OK — tela e dossiê de Prefeituras (11 cards, regra de ouro, PDF) passaram.")
