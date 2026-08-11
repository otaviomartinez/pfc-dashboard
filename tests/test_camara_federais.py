"""Teste do parser + dedup do scraper de federais da Câmara (Frente 2).

PURO (sem rede): usa uma amostra no ESQUEMA REAL da API v2/deputados. O fetch ao
vivo (buscar_deputados_sp) roda na máquina com internet — não é exercitado aqui.
    python tests/test_camara_federais.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.camara_federais import dedup_novos, parse_deputado  # noqa: E402

# Amostra no formato REAL de https://dadosabertos.camara.leg.br/api/v2/deputados
AMOSTRA = [
    {"id": 204554, "uri": "https://dadosabertos.camara.leg.br/api/v2/deputados/204554",
     "nome": "Fulano de Tal", "siglaPartido": "PL",
     "uriPartido": "https://dadosabertos.camara.leg.br/api/v2/partidos/37906",
     "siglaUf": "SP", "idLegislatura": 57,
     "urlFoto": "https://www.camara.leg.br/internet/deputado/bandep/204554.jpg",
     "email": "dep.fulano@camara.leg.br"},
    {"id": 74848, "nome": "Vitor Lippi", "siglaPartido": "PSDB", "siglaUf": "SP",
     "idLegislatura": 57, "urlFoto": "", "email": None},   # email None → ""
]


def test_parse_mapeia_campos_reais():
    d = parse_deputado(AMOSTRA[0])
    assert d["id"] == "204554" and d["nome"] == "Fulano de Tal"
    assert d["partido"] == "PL" and d["uf"] == "SP"
    assert d["email"] == "dep.fulano@camara.leg.br"
    assert d["fonte"] == "camara-api"
    # NÃO traz score/aderência/chance (base é curada) — só dados crus
    assert "score" not in d and "ader" not in d and "chance" not in d


def test_parse_campo_ausente_ou_none_vira_vazio():
    d = parse_deputado(AMOSTRA[1])
    assert d["email"] == "" and d["foto"] == ""   # None/ausente → "", nunca quebra
    assert parse_deputado({})["id"] == ""


def test_dedup_remove_existentes_e_repetidos():
    scraped = [parse_deputado(x) for x in AMOSTRA]
    # Vitor Lippi (74848) já está na base curada → sai; sobra só o 204554
    novos = dedup_novos(scraped, existentes_ids={"74848"})
    assert [d["id"] for d in novos] == ["204554"]
    # dedup interno: id repetido na paginação não duplica
    dobrado = scraped + [parse_deputado(AMOSTRA[0])]
    assert len(dedup_novos(dobrado, existentes_ids=set())) == 2
    # ids como int no "existentes" também casam (normaliza p/ str)
    assert dedup_novos(scraped, existentes_ids={74848, 204554}) == []


if __name__ == "__main__":
    test_parse_mapeia_campos_reais()
    test_parse_campo_ausente_ou_none_vira_vazio()
    test_dedup_remove_existentes_e_repetidos()
    print("OK — parser + dedup do scraper da Câmara (Frente 2) passaram.")
