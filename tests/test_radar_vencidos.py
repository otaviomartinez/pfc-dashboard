"""Teste puro do corte de vencidos da fila do radar — ui/formato._op_vencida.

Regra: item com data de prazo PARSEÁVEL e JÁ PASSADA (relativo a hoje em SP) é
vencido → descartado, inclusive vencido há muito. Data FUTURA nunca é vencida
(o chute de ano distante segue exibido como 'a confirmar'). Sem data parseável
(texto livre) NÃO é vencido — na dúvida, mantém (regra 3).

    python tests/test_radar_vencidos.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.formato import _op_vencida  # noqa: E402

HOJE = datetime.date(2026, 8, 10)


def _op(prazo, dias):
    return {"titulo": "x", "prazo": prazo, "dias": dias}


def test_confiavel_e_passado_e_vencido():
    assert _op_vencida(_op("2026-08-01", -9), HOJE) is True     # 9 dias atrás, confiável
    assert _op_vencida(_op("2026-08-09", -1), HOJE) is True     # ontem


def test_hoje_e_futuro_nao_sao_vencidos():
    assert _op_vencida(_op("2026-08-10", 0), HOJE) is False     # vence hoje: ainda não passou
    assert _op_vencida(_op("2026-08-20", 10), HOJE) is False    # futuro


def test_futuro_e_sem_data_continuam_passando():
    # data FUTURA (mesmo chute de ano distante) nunca é vencida:
    assert _op_vencida(_op("2027-03-01", 203), HOJE) is False   # chute de ano (futuro distante)
    assert _op_vencida(_op("", None), HOJE) is False            # sem prazo
    assert _op_vencida(_op("prazo aberto", "n/d"), HOJE) is False  # texto livre não parseável


def test_vencido_ha_muito_agora_e_cortado():
    # antes a trava de 60 dias deixava passar; agora qualquer data passada corta:
    assert _op_vencida(_op("2020-01-01", -100), HOJE) is True   # vencido há muito
    assert _op_vencida(_op("2026-05-01", -101), HOJE) is True   # vencido há +60 dias


def test_sem_data_parseavel_mantem():
    # dias confiável (fallback da coluna) mas prazo não parseável → não dá pra
    # afirmar vencido → mantém (na dúvida, recall).
    assert _op_vencida(_op("inscrições em andamento", -5), HOJE) is False


def test_usa_sp_por_padrao_sem_quebrar():
    # sem passar `hoje`, usa _hoje_sp() — só garante que roda e devolve bool.
    assert isinstance(_op_vencida(_op("2026-08-01", -9)), bool)


if __name__ == "__main__":
    test_confiavel_e_passado_e_vencido()
    test_hoje_e_futuro_nao_sao_vencidos()
    test_futuro_e_sem_data_continuam_passando()
    test_vencido_ha_muito_agora_e_cortado()
    test_sem_data_parseavel_mantem()
    test_usa_sp_por_padrao_sem_quebrar()
    print("OK — corte de vencidos da fila do radar (SP tz) passou.")
