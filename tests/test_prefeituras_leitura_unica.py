"""Leitura ÚNICA da prefeitura — ui.formato.leitura_prefeitura.

O PROBLEMA QUE ISTO FECHA: havia dois cálculos de temperatura. A lista, o
placar, o filtro e a ordenação usavam só MDE+CAPAG; o dossiê usava o método
fiscal por cima. Bastava uma cidade cruzar o limite prudencial de pessoal numa
coleta para a lista dizer "quente" e o dossiê dizer "morno". Hoje nenhum dos 88
municípios está nesse caso — por isso o bug era invisível, e por isso o teste
existe: ele simula a cidade que um dia vai cruzar a linha.

    python tests/test_prefeituras_leitura_unica.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.formato import (  # noqa: E402
    ORDEM_TEMPERATURA, TEMPERATURA_PREF_ROTULO, candidatos_expansao,
    contagens_prefeituras, leitura_prefeitura, normalizar_prefeituras,
)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUN = [{"cod_ibge": "3500000", "nome": "Cidade Teste", "regiao_imediata": "Sorocaba"}]
MDE = {"3500000": {"percentual": 32.0, "exercicio": 2025, "origem": "tce-sp"}}
CAPAG_A = {"3500000": {"nota": "A"}}


def test_sem_fatores_e_igual_a_base():
    """Sem dado fiscal, a leitura é exatamente a de antes (MDE+CAPAG)."""
    l = leitura_prefeitura("cumpriu", "A", 32.0)
    assert l["temperatura"] == l["temperatura_base"] == "quente"
    assert not l["bloqueio"]


def test_pessoal_no_prudencial_rebaixa_e_a_lista_ve_isso():
    """O caso que gerava a contradição: agora a LINHA já sai rebaixada, e a
    lista, o placar e o dossiê leem o mesmo campo."""
    fiscal = {"3500000": {"pessoal_pct": 52.0, "exercicio_tce": 2024}}
    linha = normalizar_prefeituras(MUN, MDE, CAPAG_A, fiscal=fiscal)[0]
    assert linha["temperatura_base"] == "quente"
    assert linha["temperatura"] == "morno", "a lista tem de mostrar o rebaixamento"
    assert linha["fiscal"]["temperatura"] == linha["temperatura"], \
        "dossiê e lista lendo valores diferentes é o bug que este teste trava"
    assert contagens_prefeituras([linha])["mornos"] == 1


def test_cauc_irregular_bloqueia_em_todo_lugar():
    fiscal = {"3500000": {"cauc": "irregular"}}
    linha = normalizar_prefeituras(MUN, MDE, CAPAG_A, fiscal=fiscal)[0]
    assert linha["temperatura"] == "bloqueado"
    assert contagens_prefeituras([linha])["bloqueados"] == 1
    assert "bloqueado" in TEMPERATURA_PREF_ROTULO, "selo não pode sair em branco"
    assert ORDEM_TEMPERATURA["bloqueado"] > ORDEM_TEMPERATURA["frio"], \
        "bloqueado vai para o fim da fila: não pode assinar convênio"


def test_fator_ausente_nunca_penaliza():
    """Regra 5c: sem dado ≠ dado ruim."""
    fiscal = {"3500000": {"pessoal_pct": None, "resultado_pct": None}}
    linha = normalizar_prefeituras(MUN, MDE, CAPAG_A, fiscal=fiscal)[0]
    assert linha["temperatura"] == "quente"


def test_expansao_usa_a_mesma_leitura():
    viz = [{"cod_ibge": "3500000", "nome": "Vizinha", "regiao_imediata": "Sorocaba"}]
    fiscal = {"3500000": {"pessoal_pct": 52.0}}
    l = candidatos_expansao(viz, MDE, CAPAG_A, fiscal=fiscal)[0]
    assert l["temperatura_base"] == "quente" and l["temperatura"] == "morno"


def test_app_nao_recalcula_por_fora():
    """Se o app voltar a chamar capacidade_fiscal por conta própria, os dois
    cálculos voltam a existir — e a contradição volta junto."""
    import re
    app = open(os.path.join(RAIZ, "app.py"), encoding="utf-8").read()
    # a chamada de CÁLCULO (não o nome da função que desenha o bloco)
    assert not re.search(r"(?<!_render_)capacidade_fiscal\(", app), \
        "a leitura é decidida só em ui.formato"
    assert "def _render_capacidade_fiscal(linha: dict):" in app
    assert 'ordem = {"quente": 0, "morno": 1, "sem_dado": 2, "frio": 3}' not in app, \
        "ordem local divergente da ORDEM_TEMPERATURA"


def test_dados_reais_lista_e_dossie_concordam():
    """Nos 11 municípios reais, com os fatores reais, cada linha carrega uma
    leitura só — e o campo da lista é o mesmo do dossiê."""
    from src.prefeituras import capag, mde, tce
    from src.prefeituras.config import carregar_municipios
    ano = tce.exercicio_com_pessoal()
    fis = {c: {"pessoal_pct": r["pessoal_pct"], "resultado_pct": r["resultado_pct"],
               "exercicio_tce": r["exercicio"]}
           for c, r in (tce.carregar_fiscal(ano) if ano else {}).items()}
    linhas = normalizar_prefeituras(
        carregar_municipios(), mde.carregar(mde.exercicio_disponivel()),
        capag.carregar(capag.exercicio_disponivel()), fiscal=fis)
    assert len(linhas) == 11
    for l in linhas:
        assert l["temperatura"] == l["fiscal"]["temperatura"], l["municipio"]


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
            print(f"ok  {nome}")
    print("leitura única: todos os testes passaram")
