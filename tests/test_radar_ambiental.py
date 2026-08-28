"""Teste do filtro ambiental/ecologia do radar — radar.scorer.e_ambiental.

Regra: edital sobre meio ambiente/ecologia está FORA do escopo do PFC e deve ser
barrado no pré-filtro (avaliar_sinal). Barra inclusive socioambiental/educação
ambiental. Termos precisos — nunca 'eco' ou 'ambiente' soltos (não pode pegar
'economia', 'ecossistema de inovação', 'ambiente escolar/de aprendizagem').

    python tests/test_radar_ambiental.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from radar.scorer import avaliar_sinal, e_ambiental  # noqa: E402


def _amb(titulo, desc=""):
    return e_ambiental(titulo, desc)


def test_barra_ambiental():
    assert _amb("Edital de preservação ambiental da Mata Atlântica") is True
    assert _amb("Chamada para projetos de educação ambiental") is True
    assert _amb("Prêmio de sustentabilidade ambiental") is True
    assert _amb("Fundo socioambiental para o cerrado") is True
    assert _amb("Projeto de reflorestamento e biodiversidade") is True
    assert _amb("Chamada sobre mudanças climáticas") is True
    assert _amb("Editais de reciclagem e resíduos sólidos") is True
    assert _amb("Iniciativa de ecologia urbana") is True


def test_nao_barra_educacao_ciencia():
    # o que o PFC capta NÃO pode ser barrado por acidente:
    assert _amb("Edital de educação científica para escola pública") is False
    assert _amb("Chamada de impacto social e juventude") is False
    assert _amb("Prêmio de formação de professores") is False


def test_nao_pega_eco_nem_ambiente_soltos():
    # falsos positivos que a régua precisa evitar:
    assert _amb("Edital de economia criativa") is False
    assert _amb("Apoio ao ecossistema de inovação e empreendedorismo") is False
    assert _amb("Projeto sobre o ambiente escolar e de aprendizagem") is False
    assert _amb("Melhoria do ambiente virtual de ensino") is False


def test_avaliar_sinal_descarta_ambiental():
    passa, motivo = avaliar_sinal({
        "titulo": "Edital de conservação ambiental e biodiversidade",
        "descricao": "Inscrições abertas para projetos de preservação.",
    })
    assert passa is False
    assert "ambiental" in motivo or "ecologia" in motivo


if __name__ == "__main__":
    test_barra_ambiental()
    test_nao_barra_educacao_ciencia()
    test_nao_pega_eco_nem_ambiente_soltos()
    test_avaliar_sinal_descarta_ambiental()
    print("OK — filtro ambiental/ecologia do radar passou.")
