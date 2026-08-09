"""Testes puros da fundação de dados dos SENADORES (Commit 1) — ui/formato.py.

Prova que:
  - _sen_do_row lê as 3 colunas renomeadas (Senador / Gabinete Senado / Fonte
    oficial Senado) e preserva score/id;
  - _parlamentar_senador normaliza na forma certa (escopo=senador, chave=ID,
    valor_tipo=sugerido, escopo_nome=Senador, contato.fonte=Senado, score preservado);
  - normalizar_parlamentares(senadores=[reg]) inclui e ordena por score junto de
    estadual/federal;
  - aba vazia → _senadores_ordenados()==[] e carregar_parlamentares("Senador")==[].

    python tests/test_senadores.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from ui import formato as F  # noqa: E402
from ui.formato import plano_obs  # noqa: E402


def _row_falsa(**over):
    """Linha falsa da aba 'Senadores' (23 colunas), como get_all_records devolveria."""
    base = {
        "ID": "5322", "Senador": "Ciclano da Silva", "Partido": "XPTO",
        "Score Integrado": "88", "Chance Emenda (0-100)": "84",
        "Aderência PFC (0-100)": "92", "Base Regional": "São Paulo",
        "Proximidade Territorial": "educação; SP", "Gabinete Senado": "Ala 5, Gab 12",
        "Endereço/Escritório Regional": "—", "Diálogo": "", "Status CRM": "Reunião",
        "Temperatura": "🟡 Morno", "Telefones": "61 3303", "WhatsApp": "",
        "Email": "cic@senado.leg.br", "Instagram": "", "Emenda/Ação": "",
        "Valor sugerido": "R$ 200 mil a R$ 400 mil", "Estratégia PFC": "abrir pela educação",
        "Observações": "", "Fonte oficial Senado": "senado.leg.br", "Follow-up sugerido": "",
    }
    base.update(over)
    return base


def test_sen_do_row_le_colunas_renomeadas():
    d = F._sen_do_row(_row_falsa())
    assert d["nome"] == "Ciclano da Silva"          # coluna "Senador"
    assert d["gabinete_senado"] == "Ala 5, Gab 12"  # coluna "Gabinete Senado"
    assert d["fonte_senado"] == "senado.leg.br"     # coluna "Fonte oficial Senado"
    assert d["id"] == "5322" and d["score"] == 88 and d["ader"] == 92


def test_parlamentar_senador_forma_certa():
    reg = F._parlamentar_senador(F._sen_do_row(_row_falsa()))
    assert reg["escopo"] == "senador"
    assert reg["escopo_nome"] == "Senador"
    assert reg["chave"] == "5322"                   # chave = ID (CodigoParlamentar)
    assert reg["valor_tipo"] == F.VALOR_SUGERIDO    # faixa, nunca execução
    assert reg["contato"]["fonte"] == "Senado"
    assert reg["contato"]["gabinete"] == "Ala 5, Gab 12"
    assert reg["score"] == 88                        # PRESERVADO (não recalcula)
    assert "sugerido" in reg["valor"]                # carimbo da regra de ouro
    assert reg["_raw"]["fonte_senado"] == "senado.leg.br"


def test_normalizar_inclui_e_ordena_com_os_outros():
    sen = F._parlamentar_senador(F._sen_do_row(_row_falsa(**{"Score Integrado": "90"})))
    est = {"nome": "Estadual X", "partido": "A", "score": 70, "status": "Reunião",
           "temp": "Morno", "valor": ""}
    fed = {"id": "1", "nome": "Federal Y", "partido": "B", "score": 80, "status": "",
           "temp_raw": "", "valor_sugerido": "R$ 100 mil a R$ 200 mil"}
    out = F.normalizar_parlamentares([est], [fed], [sen])
    assert "senador" in [r["escopo"] for r in out]
    assert [r["score"] for r in out] == [90, 80, 70]   # ordenado desc, escopos misturados
    assert out[0]["escopo"] == "senador"


def test_aba_vazia_senador_fica_vazio():
    # aba inexistente/vazia → _senadores_ordenados []; e o filtro "Senador" → [].
    orig = (F.dados.carregar_senadores, F.dados.carregar_deputados,
            F.dados.carregar_deputados_federais)
    F.dados.carregar_senadores = lambda: pd.DataFrame()
    F.dados.carregar_deputados = lambda: pd.DataFrame()
    F.dados.carregar_deputados_federais = lambda: pd.DataFrame()
    try:
        assert F._senadores_ordenados() == []
        assert F.carregar_parlamentares("Senador") == []
    finally:
        (F.dados.carregar_senadores, F.dados.carregar_deputados,
         F.dados.carregar_deputados_federais) = orig


def test_roteamento_escrita_tres_escopos_nao_cruza():
    """Roteamento da obs rápida (plano_obs) nos 3 escopos, sem cruzar: estadual
    casa por NOME; federal e senador casam por ID (senador espelha o federal, NÃO
    o estadual). É a garantia de que o senador grava na porta certa (atualizar_senador
    por ID no dispatch), sem tocar as portas estadual/federal."""
    est = plano_obs("estadual", "Ana Lima", "n")
    fed = plano_obs("federal", "204534", "n")
    sen = plano_obs("senador", "5322", "n")
    assert est["porta"] == "estadual" and est["nome"] == "Ana Lima" and "id" not in est
    assert fed["porta"] == "federal" and fed["id"] == "204534" and "nome" not in fed
    assert sen["porta"] == "senador" and sen["id"] == "5322" and "nome" not in sen
    # senador tem a MESMA forma do federal (porta+id+campos Diálogo), não a do
    # estadual (porta+nome+texto) — casa por ID, não por nome; e portas distintas.
    assert set(sen) == set(fed) and sen["porta"] != fed["porta"]
    assert list(sen["campos"].keys()) == ["Diálogo"] and "Status CRM" not in sen["campos"]


def test_pdf_resumo_senador_smoke():
    """PDF do senador: com campos preenchidos E quase vazio, gera %PDF válido — a
    omissão graciosa dos contatos vazios não quebra o PDF (espelha o smoke da Sala)."""
    from src import relatorios
    cheio = {
        "senador": "Ciclano da Silva", "partido": "XPTO", "base": "São Paulo",
        "score": "88", "aderencia": "92", "status_crm": "Reunião",
        "argumento": "Encaixe forte pela pauta de educação.",
        "valor_sugerido": "R$ 200 mil a R$ 400 mil", "estrategia": "abrir pela educação",
        "gabinete_senado": "Ala 5, Gab 12", "telefone": "61 3303-0000",
        "email": "cic@senado.leg.br", "fonte_senado": "senado.leg.br",
        "whatsapp": "", "instagram": "",
    }
    vazio = {"senador": "Fulano de Tal"}   # quase tudo ausente → tudo omitido
    b_cheio = relatorios.pdf_resumo_senador(cheio, "08/08/2026")
    b_vazio = relatorios.pdf_resumo_senador(vazio, "08/08/2026")
    assert b_cheio[:4] == b"%PDF" and b_vazio[:4] == b"%PDF"   # ambos válidos
    assert len(b_cheio) > 1200 and len(b_vazio) > 1000         # vazio não quebra


if __name__ == "__main__":
    test_sen_do_row_le_colunas_renomeadas()
    test_parlamentar_senador_forma_certa()
    test_normalizar_inclui_e_ordena_com_os_outros()
    test_aba_vazia_senador_fica_vazio()
    test_roteamento_escrita_tres_escopos_nao_cruza()
    test_pdf_resumo_senador_smoke()
    print("OK — fundação + roteamento + dossiê/PDF dos senadores passaram.")
