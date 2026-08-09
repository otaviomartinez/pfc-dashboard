"""Teste puro da observação rápida do funil (feature: obs também no FEDERAL).

Cobre o roteamento por escopo (plano_obs) e o append+carimbo (compor_dialogo) —
sem Streamlit nem Sheets. Prova: federal grava só 'Diálogo' (NUNCA 'Status CRM'),
estadual usa a porta por nome, escopos não se cruzam e o histórico é preservado.
    python tests/test_obs_federal.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.formato import compor_dialogo, plano_obs  # noqa: E402


def test_plano_federal_grava_so_dialogo_por_id():
    p = plano_obs("federal", "204534", "Falei com a Bea", atual="")
    assert p["porta"] == "federal"
    assert p["id"] == "204534"                         # casa por ID
    assert list(p["campos"].keys()) == ["Diálogo"]     # só o Diálogo...
    assert "Status CRM" not in p["campos"]             # ...NUNCA a etapa
    assert "Falei com a Bea" in p["campos"]["Diálogo"]


def test_plano_estadual_usa_porta_por_nome_sem_cruzar():
    p = plano_obs("estadual", "Ana Lima", "nota")
    assert p["porta"] == "estadual"
    assert p["nome"] == "Ana Lima" and p["texto"] == "nota"
    assert "campos" not in p and "id" not in p         # não usa a porta federal


def test_plano_senador_grava_so_dialogo_por_id():
    # senador AGORA tem porta própria (espelha o federal): grava só o Diálogo, por ID.
    p = plano_obs("senador", "5322", "Falei com o gabinete", atual="")
    assert p["porta"] == "senador"
    assert p["id"] == "5322"                           # casa por ID (CodigoParlamentar)
    assert list(p["campos"].keys()) == ["Diálogo"]     # só o Diálogo...
    assert "Status CRM" not in p["campos"]             # ...NUNCA a etapa
    assert "Falei com o gabinete" in p["campos"]["Diálogo"]


def test_plano_escopo_desconhecido_sem_gravacao():
    # escopo de fato DESCONHECIDO → sem porta (senador deixou de ser exemplo disto)
    assert plano_obs("prefeito", "X", "x")["porta"] is None
    assert plano_obs("", "", "x")["porta"] is None


def test_compor_dialogo_carimba_e_preserva_historico():
    # sem atual: só a nova, carimbada
    assert compor_dialogo("", "primeira", agora="01/01/2026 10:00") == "[01/01/2026 10:00] primeira"
    # com atual: preserva o antigo e anexa a nova embaixo
    out = compor_dialogo("[31/12/2025 09:00] velha", "nova", agora="01/01/2026 10:00")
    assert out == "[31/12/2025 09:00] velha\n[01/01/2026 10:00] nova"
    # texto vazio devolve o atual intacto (não cria linha/carimbo vazio)
    assert compor_dialogo("[x] a", "   ", agora="01/01/2026 10:00") == "[x] a"


def test_federal_preserva_historico_no_plano():
    p = plano_obs("federal", "1", "recente", atual="[antes] contexto")
    d = p["campos"]["Diálogo"]
    assert "[antes] contexto" in d and "recente" in d   # append, não sobrescrita


if __name__ == "__main__":
    test_plano_federal_grava_so_dialogo_por_id()
    test_plano_estadual_usa_porta_por_nome_sem_cruzar()
    test_plano_senador_grava_so_dialogo_por_id()
    test_plano_escopo_desconhecido_sem_gravacao()
    test_compor_dialogo_carimba_e_preserva_historico()
    test_federal_preserva_historico_no_plano()
    print("OK — testes da obs rápida federal/senador passaram.")
