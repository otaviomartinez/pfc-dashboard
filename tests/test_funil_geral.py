"""Teste puro do Funil Geral (Passo 5).

Cobre as funções PURAS de ui/formato.py — sem Streamlit runtime e sem Google
Sheets: o codec do id de card (round-trip escopo/chave) e o builder de colunas.
Rodar da raiz do projeto:

    python tests/test_funil_geral.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.formato import (  # noqa: E402
    EMENDA_FUNIL_ETAPAS,
    _decodificar_id_card,
    _id_card_parlamentar,
    funil_parlamentares_colunas,
)


def test_roundtrip_id_card():
    """O id embute escopo+chave e volta idêntico — nome com acento/espaço e ID."""
    # Estadual: chave = NOME (com acento e espaço)
    reg_e = {"escopo": "estadual", "chave": "João da Conceição Ávila"}
    assert _decodificar_id_card(_id_card_parlamentar(reg_e)) == \
        ("estadual", "João da Conceição Ávila")
    # Federal: chave = ID numérico
    reg_f = {"escopo": "federal", "chave": "204534"}
    assert _decodificar_id_card(_id_card_parlamentar(reg_f)) == ("federal", "204534")
    # id legado/sem separador → escopo vazio, chave crua (o roteador recusa a escrita)
    assert _decodificar_id_card("Fulano de Tal") == ("", "Fulano de Tal")
    # robustez: None não quebra
    assert _decodificar_id_card(None) == ("", "")


def test_funil_colunas_bucketiza_rotula_e_respeita_regra_de_ouro():
    """Cards caem na etapa certa, o id decodifica para a origem certa e NENHUM
    valor monetário/soma aparece no funil (regra de ouro)."""
    regs = [
        {"escopo": "estadual", "chave": "Ana Lima", "nome": "Ana Lima",
         "partido": "PT", "escopo_nome": "Estadual", "score": 72,
         "temp_emoji": "🔵", "temp": "Muito Quente", "status": "Reunião agendada"},
        {"escopo": "federal", "chave": "999", "nome": "Bruno Sá",
         "partido": "PP", "escopo_nome": "Federal", "score": 55,
         "temp_emoji": "🟡", "temp": "Morno", "status": "Emenda aprovada",
         # campos de valor que NÃO podem vazar para o card do funil:
         "valor_sugerido": "R$ 2 mi", "valor": "R$ 2 mi · sugerido"},
    ]
    colunas = funil_parlamentares_colunas(regs)
    por_etapa = {c["status"]: c["cards"] for c in colunas}

    # bucketização por _etapa_de_status
    assert [c["nome"] for c in por_etapa["Reunião"]] == ["Ana Lima"]
    assert [c["nome"] for c in por_etapa["Emenda aprovada"]] == ["Bruno Sá"]

    # cada id decodifica para (escopo, chave) — a base do roteamento da escrita
    ana = por_etapa["Reunião"][0]
    bruno = por_etapa["Emenda aprovada"][0]
    assert _decodificar_id_card(ana["id"]) == ("estadual", "Ana Lima")
    assert _decodificar_id_card(bruno["id"]) == ("federal", "999")

    # o escopo aparece no meta (setor) e o card mostra TEMPERATURA, não dinheiro
    assert "Estadual" in ana["setor"] and "Federal" in bruno["setor"]
    assert ana["valor"] == "🔵 Muito Quente"
    assert bruno["valor"] == "🟡 Morno"

    # REGRA DE OURO: nenhum valor monetário/"sugerido" no card e nenhuma soma/total
    for c in colunas:
        assert "total" not in c
        for card in c["cards"]:
            v = card["valor"].lower()
            assert "sugerido" not in v and "r$" not in v

    # estrutura: as 5 etapas na ordem canônica, sem card perdido nem duplicado
    assert [c["status"] for c in colunas] == EMENDA_FUNIL_ETAPAS
    assert sum(len(c["cards"]) for c in colunas) == len(regs)


def test_escopo_desconhecido_nao_e_roteavel():
    """Card de escopo sem gravação (ex.: futuro senador) decodifica, mas o escopo
    não casa com estadual/federal — o roteador (em app.py) cai no else e recusa."""
    reg_s = {"escopo": "senador", "chave": "SEN-1", "nome": "Zeca",
             "partido": "—", "escopo_nome": "Senador", "score": 0,
             "temp_emoji": "⚫", "temp": "Fechado", "status": "Não iniciado"}
    colunas = funil_parlamentares_colunas([reg_s])
    card = colunas[0]["cards"][0]  # "Não iniciado"
    escopo, chave = _decodificar_id_card(card["id"])
    assert (escopo, chave) == ("senador", "SEN-1")
    assert escopo not in ("estadual", "federal")  # → else do roteador: não grava


if __name__ == "__main__":
    test_roundtrip_id_card()
    test_funil_colunas_bucketiza_rotula_e_respeita_regra_de_ouro()
    test_escopo_desconhecido_nao_e_roteavel()
    print("OK — todos os testes do Funil Geral (Passo 5) passaram.")
