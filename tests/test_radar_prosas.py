"""Prosas pela API pública (nov/2026).

O site é JavaScript; a sonda achou a API que a própria página usa
(/selecao/api/v2/publics/oportunidades, formato JSON:API). O payload abaixo
imita a resposta REAL vista na sonda: `data` com os editais, `included` com o
financiador (incentivador) e as áreas.

    python tests/test_radar_prosas.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from radar import fontes_ancora as fa  # noqa: E402
from radar.scorer import motivo_lixo  # noqa: E402

HOJE = datetime.date(2026, 11, 4)


def _edital(id_, nome, fim, inc_id, areas=()):
    return {
        "id": str(id_), "type": "oportunidades",
        "attributes": {"id": id_, "nome": nome, "encerramento_das_inscricoes": fim,
                       "prazo": "definido"},
        "relationships": {
            "incentivador": {"data": {"type": "incentivadores", "id": str(inc_id)}},
            "area_interesses": {"data": [{"type": "area_interesses", "id": str(a)} for a in areas]},
        },
    }


PAYLOAD = {
    "data": [
        _edital(101, "Parcerias Sustentáveis 2027", "2026-11-06T18:00:00.000-03:00", 1, [7, 8]),
        _edital(102, "EDITAL DE CHAMAMENTO PÚBLICO Nº 26/2026 - Cultura Popular",
                "2026-11-20T18:00:00.000-03:00", 2),
        _edital(103, "Edital Educação 2026", "2026-10-01T18:00:00.000-03:00", 1),
        _edital(104, "Chamamento para OSC da cidade", "2026-12-01T23:59:00.000-03:00", 3, [7]),
        _edital(105, "Edital de apoio a projetos", "2026-12-10T23:59:00.000-03:00", 4),
        _edital(106, "Fundo para projetos sociais", "", 1),
    ],
    "included": [
        {"type": "incentivadores", "id": "1", "attributes": {"nome": "AngloGold Ashanti"}},
        {"type": "incentivadores", "id": "2",
         "attributes": {"nome": "Fundação de Cultura de Mato Grosso do Sul"}},
        {"type": "incentivadores", "id": "3",
         "attributes": {"nome": "Secretaria Municipal de Educação de Sorocaba"}},
        {"type": "incentivadores", "id": "4",
         "attributes": {"nome": "Secretaria Municipal de Cultura - Instituto Cultural de Goiânia"}},
        {"type": "area_interesses", "id": "7", "attributes": {"nome": "Educação"}},
        {"type": "area_interesses", "id": "8", "attributes": {"nome": "Juventude"}},
    ],
}


def _por_url():
    return {i["url"]: i for i in fa.itens_prosas(PAYLOAD, hoje=HOJE)}


def test_edital_aberto_vem_com_prazo_estruturado():
    it = _por_url()["https://prosas.com.br/editais/101"]
    assert it["fonte"] == "Prosas"
    assert it["titulo"] == "Parcerias Sustentáveis 2027"
    assert it["prazo"] == "2026-11-06" and it["dias_restantes"] == 2
    assert "AngloGold Ashanti" in it["descricao"]
    assert "áreas: Educação, Juventude" in it["descricao"]
    assert "inscrições até 06/11/2026" in it["descricao"]


def test_encerrado_fica_de_fora():
    assert "https://prosas.com.br/editais/103" not in _por_url()


def test_orgao_publico_de_outro_estado_fica_de_fora():
    assert "https://prosas.com.br/editais/102" not in _por_url()


def test_orgao_publico_de_cidade_do_pfc_fica():
    assert "https://prosas.com.br/editais/104" in _por_url()


def test_itu_casa_so_palavra_inteira():
    """BUG visto ao escrever: 'itu' solto casava 'instITUto' e salvava a
    secretaria de Goiânia como se fosse da cidade de Itu."""
    assert "https://prosas.com.br/editais/105" not in _por_url()
    assert not fa.prosas_orgao_de_fora("Edital", "Prefeitura da Estância Turística de Itu")


def test_sem_prazo_nao_inventa_data():
    """Regra 3: sem data estruturada, nada de 'faltam X dias'."""
    it = _por_url()["https://prosas.com.br/editais/106"]
    assert it["prazo"] == "" and "dias_restantes" not in it


def test_payload_vazio_ou_estranho_nao_quebra():
    assert fa.itens_prosas({}, hoje=HOJE) == []
    assert fa.itens_prosas(None, hoje=HOJE) == []
    assert fa.itens_prosas({"data": [{"attributes": {}}]}, hoje=HOJE) == []


def test_prosas_registrado_no_radar():
    assert fa.FONTES["Prosas"] is fa.fonte_prosas
    assert fa.URL_DA_FONTE["Prosas"] == "https://prosas.com.br/editais"
    assert "Prosas" not in fa.FONTES_DESATIVADAS
    assert fa.PROSAS_PAUSA >= 30, "o robots.txt do Prosas pede 30 s entre pedidos"


def test_contratacao_de_pessoa_e_lixo():
    """O Prosas lista seleção de PESSOA (contador, parecerista) — não é captação."""
    assert motivo_lixo("EDITAL DE SELEÇÃO SIMPLIFICADA Nº 115/2026 - CONTADORES")
    assert motivo_lixo("Credenciamento de pareceristas 2026")


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
            print(f"ok  {nome}")
    print("Prosas: todos os testes passaram")
