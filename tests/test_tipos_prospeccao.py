"""Teste puro dos tipos de verba da Prospecção (Frente 2: tipos fixos + tolerância).

Cobre a lista canônica (4, sem 'Outro', com 'Prefeitura') e a exibição tolerante a
tipo legado (o card 'OUTRO' já gravado NÃO pode sumir). Sem Streamlit/Sheets.
    python tests/test_tipos_prospeccao.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.formato import PROSPECCAO_TIPOS, rotulo_tipo_prospeccao  # noqa: E402


def test_lista_fixa_de_4_sem_outro_com_prefeitura():
    assert PROSPECCAO_TIPOS == ["Emenda", "Patrocínio", "Prefeitura", "Prêmio"]
    assert len(PROSPECCAO_TIPOS) == 4
    assert "Outro" not in PROSPECCAO_TIPOS      # removido do formulário de entrada
    assert "Prefeitura" in PROSPECCAO_TIPOS     # adicionado


def test_rotulo_tolera_tipo_legado_nao_esconde():
    # o registro real "Verba a confirmar" tem Tipo "OUTRO" — deve seguir visível
    assert rotulo_tipo_prospeccao("OUTRO") == "OUTRO"
    assert rotulo_tipo_prospeccao("Emenda") == "Emenda"
    assert rotulo_tipo_prospeccao("  Patrocínio ") == "Patrocínio"


def test_rotulo_vazio_vira_travessao():
    assert rotulo_tipo_prospeccao("") == "—"
    assert rotulo_tipo_prospeccao(None) == "—"
    assert rotulo_tipo_prospeccao("   ") == "—"


if __name__ == "__main__":
    test_lista_fixa_de_4_sem_outro_com_prefeitura()
    test_rotulo_tolera_tipo_legado_nao_esconde()
    test_rotulo_vazio_vira_travessao()
    print("OK — testes dos tipos de Prospecção (Frente 2) passaram.")
