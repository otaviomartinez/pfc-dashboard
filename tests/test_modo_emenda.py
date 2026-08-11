"""Teste puro de _modo_emenda (Passo 8 · Commit 1 — unificação de estado).

Blinda a migração: cada página da sidebar de Emendas mapeia pro modo certo, e valor
LEGADO ('Lista', das antigas FEDERAL_PAGES aposentadas) ou desconhecido cai em
'visao' — assim uma sessão antiga com emenda_page fora das EMENDA_PAGES não quebra.
Rodar da raiz do projeto:

    python tests/test_modo_emenda.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.formato import _modo_emenda  # noqa: E402

# As 5 páginas atuais da sidebar (espelham EMENDA_PAGES em app.py).
ESPERADO = {
    "Visão geral": "visao",
    "Territórios em Aberto": "orfaos",
    "Funil de negociação": "funil",
    "Relatório": "relatorio",
    "Metodologia": "metodologia",
}


def test_paginas_validas_mapeiam_certo():
    for page, modo in ESPERADO.items():
        assert _modo_emenda(page) == modo, f"{page} deveria virar {modo}"


def test_legado_e_desconhecido_caem_em_visao():
    # 'Lista' (painel Federal antigo), 'Deputados' e 'Descobrir' foram aposentadas —
    # não podem quebrar a migração de estado legado
    assert _modo_emenda("Lista") == "visao"
    assert _modo_emenda("Deputados") == "visao"
    assert _modo_emenda("Descobrir") == "visao"
    # valores estranhos / vazio / None
    assert _modo_emenda("Qualquer coisa") == "visao"
    assert _modo_emenda("") == "visao"
    assert _modo_emenda(None) == "visao"


if __name__ == "__main__":
    test_paginas_validas_mapeiam_certo()
    test_legado_e_desconhecido_caem_em_visao()
    print("OK — testes de _modo_emenda (Passo 8) passaram.")
