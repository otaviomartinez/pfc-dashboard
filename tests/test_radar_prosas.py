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
        _edital(107, "Prêmio Educação para Gentileza e Generosidade 2026 Escolas",
                "2026-12-15T23:59:00.000-03:00", 1, [7, 9]),
        _edital(108, "BIP: Reciclagem", "2026-12-15T23:59:00.000-03:00", 1, [9]),
        _edital(109, "Edital 03/2026-DRI/UEMS. Edital de fluxo contínuo",
                "2026-12-04T23:59:00.000-03:00", 5, [7]),
        _edital(110, "Edital PROEX 2026", "2026-12-04T23:59:00.000-03:00", 6, [7]),
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
        {"type": "area_interesses", "id": "9", "attributes": {"nome": "Meio Ambiente"}},
        {"type": "incentivadores", "id": "5",
         "attributes": {"nome": "Universidade Estadual de Mato Grosso do Sul - UEMS"}},
        {"type": "incentivadores", "id": "6",
         "attributes": {"nome": "Universidade Federal de São Carlos"}},
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
    assert "inscrições abertas até 06/11/2026" in it["descricao"]


def test_titulo_sem_edital_ganha_sinal_pela_inscricao_aberta():
    """1ª rodada real: 44 itens do Prosas, só 1 com sinal — títulos como
    "Parcerias Sustentáveis 2027" não dizem "edital". A inscrição aberta (fato
    do sistema do Prosas) é o sinal."""
    from radar.scorer import tem_sinal_de_oportunidade
    it = _por_url()["https://prosas.com.br/editais/101"]
    assert tem_sinal_de_oportunidade(it["titulo"], it["descricao"])


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


def test_meio_ambiente_entre_varias_areas_nao_barra():
    """1ª leitura real: 13 editais caíram como 'ambiental' só porque "Meio
    Ambiente" era UMA das áreas aceitas — inclusive um prêmio de educação."""
    from radar.scorer import motivo_lixo
    it = _por_url()["https://prosas.com.br/editais/107"]
    assert "Meio Ambiente" not in it["descricao"]
    assert not motivo_lixo(it["titulo"], it["descricao"])


def test_area_so_ambiental_continua_barrada():
    from radar.scorer import motivo_lixo
    it = _por_url()["https://prosas.com.br/editais/108"]
    assert motivo_lixo(it["titulo"], it["descricao"])


def test_edital_interno_de_universidade_de_fora_sai_e_a_de_sp_fica():
    urls = _por_url()
    assert "https://prosas.com.br/editais/109" not in urls, "UEMS (MS): edital interno"
    assert "https://prosas.com.br/editais/110" in urls, "UFSCar: a casa do PFC"


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
    # resgatado na 2ª chance da 1ª rodada real (04/11) — era lixo:
    assert motivo_lixo("EDITAL DE CREDENCIAMENTO Nº 002/2026/FETEC PROFISSIONAIS CULTURAIS ESP")


def test_selo_encerrado_no_comeco_do_titulo():
    """Também resgatado na 2ª chance de 04/11 (Fundo Brasil)."""
    assert motivo_lixo("Encerrado Edital Geral 2026 – Fortalecendo Direitos e Gestando um Mundo")


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
            print(f"ok  {nome}")
    print("Prosas: todos os testes passaram")
