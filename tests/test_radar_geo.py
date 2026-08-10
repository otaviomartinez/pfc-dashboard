"""Teste do filtro geográfico do radar — radar.scorer.e_restrito_fora_sudeste.

Barra editais RESTRITOS a região/estado fora de SP/Sudeste. Recall > precisão:
na dúvida MANTÉM. Não barra 'sul' solto ('zona sul', 'sul de Minas' = Sudeste),
nacional, ou textos que citem SP/Sudeste (mesmo listando outras regiões).

    python tests/test_radar_geo.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from radar.scorer import avaliar_sinal, e_restrito_fora_sudeste  # noqa: E402


def _barra(titulo, desc=""):
    return e_restrito_fora_sudeste(titulo, desc)


def test_barra_restritos_fora_do_sudeste():
    assert _barra("Edital exclusivo para a Bahia")
    assert _barra("Chamada para municípios do Ceará")
    assert _barra("Programa restrito a organizações do Nordeste")
    assert _barra("Apoio a projetos sediados no Amazonas")
    assert _barra("Seleção voltada para a região Sul")
    assert _barra("Recursos destinados exclusivamente aos estados do Nordeste")
    assert _barra("Fomento", "Iniciativa somente para o semiárido nordestino")
    assert _barra("Edital com sede no Maranhão para projetos locais")
    assert _barra("Chamada limitada a municípios de Goiás")


def test_nao_barra_nacional_ou_sudeste():
    assert not _barra("Edital nacional de educação científica")
    assert not _barra("Chamada para projetos em São Paulo e na Bahia")   # cita SP → mantém
    assert not _barra("Prêmio para escolas do Sudeste")
    assert not _barra("Apoio a organizações de Sorocaba e região")
    assert not _barra("Edital para o interior paulista")
    assert not _barra("Programa em âmbito nacional, com foco no Nordeste")  # nacional → mantém


def test_nao_barra_sul_solto_nem_sudeste_states():
    assert not _barra("Projeto de educação na zona sul da capital")
    assert not _barra("Iniciativa no sul de Minas Gerais")               # Sudeste
    assert not _barra("Edital exclusivo para o estado do Rio de Janeiro")  # RJ é Sudeste
    assert not _barra("Chamada para o norte de São Paulo")               # cita SP → mantém


def test_marcador_sem_regiao_nao_barra():
    # marcador de restrição, mas sem âncora regional fora do Sudeste por perto:
    assert not _barra("Edital exclusivo para projetos de robótica educacional")
    assert not _barra("Programa restrito a organizações sem fins lucrativos")


def test_regiao_longe_do_marcador_nao_barra():
    # 'exclusivo' e 'nordeste' existem, mas distantes (não é a restrição) → mantém.
    t = ("Conteúdo exclusivo para inscritos sobre metodologias ativas de ensino. "
         "Em um trecho posterior, o material cita boas práticas observadas no Nordeste "
         "brasileiro como inspiração para todo o país.")
    assert not _barra(t)


def test_integra_no_avaliar_sinal():
    # um edital real, com sinal de oportunidade, mas restrito ao Nordeste → barrado
    # pelo pré-filtro com o motivo geográfico.
    op = {"titulo": "Edital de apoio a projetos", "descricao": "chamada pública "
          "exclusiva para organizações da Bahia e de Pernambuco"}
    passa, motivo = avaliar_sinal(op)
    assert passa is False
    assert "fora de SP" in motivo or "São Paulo" in motivo
    # e um nacional com o mesmo sinal continua passando:
    op2 = {"titulo": "Edital nacional de apoio a projetos",
           "descricao": "chamada pública para organizações de todo o Brasil"}
    assert avaliar_sinal(op2)[0] is True


if __name__ == "__main__":
    test_barra_restritos_fora_do_sudeste()
    test_nao_barra_nacional_ou_sudeste()
    test_nao_barra_sul_solto_nem_sudeste_states()
    test_marcador_sem_regiao_nao_barra()
    test_regiao_longe_do_marcador_nao_barra()
    test_integra_no_avaliar_sinal()
    print("OK — filtro geográfico do radar (fora de SP/Sudeste) passou.")
