"""Teste puro do modelo de linhas do placar de Prospecção (Frente 3).

`linhas_placar_prospeccao` monta o modelo (nome/sub/valor) das verbas conquistadas.
Sem Streamlit/HTML. Rodar da raiz:

    python tests/test_placar_prospeccao.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.formato import linhas_placar_prospeccao  # noqa: E402


def test_ganhos_viram_linhas():
    ganhos = [
        {"Nome": "Emenda Vitor Lippi", "Tipo": "Emenda", "Financiador": "Vitor Lippi",
         "Previsão": "set", "Valor": "R$ 200 mil"},
        {"Nome": "Prêmio X", "Tipo": "Prêmio", "Valor": "R$ 50 mil"},
    ]
    linhas = linhas_placar_prospeccao(ganhos)
    assert len(linhas) == 2
    assert linhas[0] == {"nome": "Emenda Vitor Lippi",
                         "sub": "Emenda · Vitor Lippi · set", "valor": "R$ 200 mil"}
    assert linhas[1]["nome"] == "Prêmio X"
    assert linhas[1]["sub"] == "Prêmio"        # só o Tipo (sem financiador/previsão)
    assert linhas[1]["valor"] == "R$ 50 mil"


def test_lista_vazia():
    assert linhas_placar_prospeccao([]) == []
    assert linhas_placar_prospeccao(None) == []


def test_robustez_campo_faltante():
    # tudo faltando → fallbacks, sem crash
    assert linhas_placar_prospeccao([{}]) == [{"nome": "(sem nome)", "sub": "", "valor": "—"}]
    # só o nome
    assert linhas_placar_prospeccao([{"Nome": "Só nome"}]) == \
        [{"nome": "Só nome", "sub": "", "valor": "—"}]


if __name__ == "__main__":
    test_ganhos_viram_linhas()
    test_lista_vazia()
    test_robustez_campo_faltante()
    print("OK — testes do placar de Prospecção (Frente 3) passaram.")
