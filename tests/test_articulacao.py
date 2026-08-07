"""Teste puro do predicado 'em articulação' (fix status federal).

Garante que a CONTAGEM (KPI) e a LISTA de 'em articulação' concordam — ambas pelo
mesmo predicado de ETAPA (status), nunca pelo Diálogo — e que status vazio conta
como 'não iniciado'. Roda sem Streamlit/Sheets (funções puras de ui/formato.py):

    python tests/test_articulacao.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.formato import _e_nao_iniciado, capa_payload_parlamentares  # noqa: E402


def _reg(status, dialogo="", **over):
    """Registro federal falso no formato de carregar_parlamentares (campos que a
    capa lê). `dialogo` existe só para provar que NÃO entra no predicado."""
    base = dict(escopo="federal", escopo_nome="Federal", nome="Vitor Lippi",
                partido="PSDB", score=97, ader=90, chance=70,
                status=status, dialogo=dialogo, temp="Morno", temp_cor="#E8B54A")
    base.update(over)
    return base


def _articulacao(ctx):
    return ctx["payload"]["hero"]["articulacao"]


def test_contato_iniciado_kpi_e_lista_concordam():
    # Status CRM = etapa "Contato iniciado"; Diálogo diz "não iniciado" (ruído).
    ctx = capa_payload_parlamentares([_reg("Contato iniciado", dialogo="não iniciado")])
    assert _articulacao(ctx) == 1                      # KPI conta
    assert len(ctx["em_articulacao"]) == 1             # lista mostra
    assert ctx["em_articulacao"][0]["nome"] == "Vitor Lippi"


def test_nao_iniciado_nao_conta_e_dialogo_nao_vaza():
    # Etapa "Não iniciado"; Diálogo diz "Contato iniciado" (ruído que NÃO pode vazar).
    ctx = capa_payload_parlamentares([_reg("Não iniciado", dialogo="Contato iniciado")])
    assert _articulacao(ctx) == 0
    assert ctx["em_articulacao"] == []


def test_status_vazio_e_nao_iniciado():
    ctx = capa_payload_parlamentares([_reg("")])
    assert _articulacao(ctx) == 0
    assert ctx["em_articulacao"] == []


def test_helper_unitario():
    assert _e_nao_iniciado("Contato iniciado") is False
    assert _e_nao_iniciado("Reunião") is False
    assert _e_nao_iniciado("Não iniciado") is True
    assert _e_nao_iniciado("nao iniciado") is True
    assert _e_nao_iniciado("") is True
    assert _e_nao_iniciado("   ") is True
    assert _e_nao_iniciado(None) is True


if __name__ == "__main__":
    test_contato_iniciado_kpi_e_lista_concordam()
    test_nao_iniciado_nao_conta_e_dialogo_nao_vaza()
    test_status_vazio_e_nao_iniciado()
    test_helper_unitario()
    print("OK — testes de 'em articulação' (fix status federal) passaram.")
