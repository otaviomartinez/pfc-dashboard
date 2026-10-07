"""Ordenação da tela de Prefeituras: melhores leads, alfabética e as lentes.

    python tests/test_prefeituras_ordenacao.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.formato import ORDENS_PREFEITURA, ordenar_prefeituras  # noqa: E402


def _l(mun, temp, mde=None, capag="", pessoal=None, deps=0, porte=0):
    return {"municipio": mun, "temperatura": temp, "mde_percentual": mde, "capag_nota": capag,
            "fiscal": {"pessoal_pct": pessoal}, "deputados_emenda": [{}] * deps, "porte": porte}


LINHAS = [
    _l("Tatuí", "morno", 27.1, "B", 48.0, 2),
    _l("Álvares Machado", "quente", None, "", None, 0),
    _l("Boituva", "quente", 30.2, "A", 41.5, 1),
    _l("Capela do Alto", "bloqueado", 33.0, "C", 39.0, 3),
    _l("Mirassol", "sem_dado", None, "B+", 52.0, 0),
]


def _nomes(criterio, **kw):
    return [x["municipio"] for x in ordenar_prefeituras(LINHAS, criterio, **kw)]


def test_melhores_leads_e_a_leitura_unica():
    assert _nomes("Melhores leads") == ["Boituva", "Álvares Machado", "Tatuí", "Mirassol",
                                        "Capela do Alto"]


def test_alfabetica_ignora_acento():
    assert _nomes("Alfabética (A–Z)") == ["Álvares Machado", "Boituva", "Capela do Alto",
                                          "Mirassol", "Tatuí"]


def test_sem_dado_vai_para_o_fim_em_todo_criterio():
    assert _nomes("Maior aplicação em educação")[-2:] == ["Álvares Machado", "Mirassol"]
    assert _nomes("Mais folga com pessoal")[-1] == "Álvares Machado"
    assert _nomes("Melhor CAPAG")[-1] == "Álvares Machado"


def test_lentes():
    assert _nomes("Maior aplicação em educação")[0] == "Capela do Alto"
    assert _nomes("Melhor CAPAG")[:2] == ["Boituva", "Mirassol"], "A antes de B+"
    assert _nomes("Mais folga com pessoal")[0] == "Capela do Alto", "menor %RCL = mais folga"
    assert _nomes("Mais emendas edu/social")[0] == "Capela do Alto"


def test_expansao_usa_porte_em_melhores_leads():
    linhas = [_l("A", "quente", porte=10), _l("B", "quente", porte=99), _l("C", "morno", porte=999)]
    assert [x["municipio"] for x in ordenar_prefeituras(linhas, "Melhores leads", expansao=True)] \
        == ["B", "A", "C"]


def test_criterio_desconhecido_e_lista_vazia():
    assert _nomes("qualquer") == _nomes("Melhores leads")
    assert ordenar_prefeituras([], "Alfabética (A–Z)") == []
    assert ordenar_prefeituras(None) == []


def test_nao_muda_a_lista_original():
    antes = [x["municipio"] for x in LINHAS]
    ordenar_prefeituras(LINHAS, "Alfabética (A–Z)")
    assert [x["municipio"] for x in LINHAS] == antes


def test_partido_nao_e_criterio():
    """Regra 5d: nenhuma ordem por partido."""
    assert not any("partid" in c.lower() for c in ORDENS_PREFEITURA)


def test_tela_usa_a_funcao():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fonte = open(os.path.join(raiz, "app.py"), encoding="utf-8").read()
    assert "ordenar_prefeituras(vis, ordem)" in fonte
    assert "ordenar_prefeituras(linhas, ordem, expansao=True)" in fonte


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
            print(f"ok  {nome}")
    print("ordenação de prefeituras: todos os testes passaram")
