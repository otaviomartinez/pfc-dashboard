"""Camada PURA do painel Prefeituras — ui/formato.py (Passo 5).

Trava as regras de negócio do plano: a tabela MDE x CAPAG, a honestidade de
período (percentual sem exercício não existe), a ausência como estado neutro e
o gancho que NUNCA inventa.

    python tests/test_prefeituras_puro.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.formato import (  # noqa: E402
    AVISO_PREFEITURAS, contagens_prefeituras, deputados_do_municipio,
    gancho_prefeitura, normalizar_prefeituras, ponte_partidaria, rotulo_mde,
    situacao_mde, temperatura_prefeitura,
)

MUNS = [{"nome": "Iperó", "cod_ibge": "3521002", "grupo": "Operação ativa",
         "regiao_imediata": "Sorocaba"},
        {"nome": "Salto", "cod_ibge": "3545209", "grupo": "Operação ativa",
         "regiao_imediata": "Sorocaba"}]


# ---- situacao_mde --------------------------------------------------------- #
def test_situacao_mde_tres_estados():
    assert situacao_mde(27.4) == "cumpriu"
    assert situacao_mde(25.0) == "cumpriu"        # 25 exato cumpre o mínimo
    assert situacao_mde(24.99) == "nao_cumpriu"
    assert situacao_mde(None) == "sem_dado"
    assert situacao_mde("") == "sem_dado"
    assert situacao_mde("abc") == "sem_dado"


# ---- tabela do plano ------------------------------------------------------ #
def test_tabela_estrategica_do_plano():
    # abaixo de 25 + caixa (A/B) = quente
    assert temperatura_prefeitura("nao_cumpriu", "A", 22) == "quente"
    assert temperatura_prefeitura("nao_cumpriu", "B", 22) == "quente"
    # acima com folga (>28) + caixa = quente
    assert temperatura_prefeitura("cumpriu", "A", 30) == "quente"
    # acima no limite (25-28) = morno
    assert temperatura_prefeitura("cumpriu", "A", 26) == "morno"
    assert temperatura_prefeitura("cumpriu", "B", 28) == "morno"   # 28 não é folga
    # C/D = frio, qualquer que seja o MDE
    assert temperatura_prefeitura("nao_cumpriu", "C", 20) == "frio"
    assert temperatura_prefeitura("cumpriu", "D", 33) == "frio"
    # MDE não declarado = sem_dado, NUNCA inferido
    assert temperatura_prefeitura("sem_dado", "A", None) == "sem_dado"
    assert temperatura_prefeitura("sem_dado", "C", None) == "sem_dado"


def test_capag_ausente_nunca_promove_a_quente():
    """Sem nota não dá para AFIRMAR caixa — então no máximo morno."""
    assert temperatura_prefeitura("nao_cumpriu", "", 20) == "morno"
    assert temperatura_prefeitura("cumpriu", None, 35) == "morno"


# ---- honestidade de período ----------------------------------------------- #
def test_percentual_sem_exercicio_nao_existe():
    assert rotulo_mde(27.4, 2025, 6) == "27,4% em 2025 · 6º bim."
    assert rotulo_mde(27.4, 2025) == "27,4% em 2025"
    assert rotulo_mde(27.4, None) == "sem dado"          # número solto não publica
    assert "2025" in rotulo_mde(None, 2025)
    assert rotulo_mde(None, None) == "sem dado"


# ---- cruzamentos ---------------------------------------------------------- #
def test_deputados_do_municipio_reusa_o_ranking():
    rk = [{"deputado": "Valdomiro Lopes", "municipios_pfc": "MIRASSOL"},
          {"deputado": "Fulano", "municipios_pfc": "IPERÓ, SALTO"},
          {"deputado": "Sicrano", "municipios_pfc": "SOROCABA · IPERO"}]
    nomes = {d["deputado"] for d in deputados_do_municipio("Iperó", rk)}
    assert nomes == {"Fulano", "Sicrano"}, nomes   # casa com e sem acento, ',' e '·'
    assert deputados_do_municipio("Guareí", rk) == []


def test_ponte_partidaria_so_cruza_o_que_existe_nos_dois_lados():
    locais = [{"cargo": "PREFEITO", "nome_urna": "Ana", "partido": "PSDB"},
              {"cargo": "VEREADOR", "nome_urna": "Zeca", "partido": "PT"}]
    crm = [{"deputado": "Dep X", "partido": "PT"}, {"deputado": "Dep Y", "partido": "PL"}]
    pontes = ponte_partidaria(locais, crm)
    assert [p["partido"] for p in pontes] == ["PT"]     # PSDB e PL não cruzam
    assert pontes[0]["parlamentares"][0]["deputado"] == "Dep X"
    assert ponte_partidaria([], crm) == [] and ponte_partidaria(locais, []) == []


# ---- gancho --------------------------------------------------------------- #
def test_gancho_prioridade_1_abaixo_do_minimo_com_caixa():
    g = gancho_prefeitura("Iperó", "nao_cumpriu", 22.0, "A", [], [], 2025)
    assert "ABAIXO" in g and "MDE" in g and "Iperó" in g


def test_gancho_prioridade_2_acima_com_folga():
    g = gancho_prefeitura("Salto", "cumpriu", 31.0, "B", [], [], 2025)
    assert "prioridade" in g.lower() and "31,0%" in g


def test_gancho_prioridade_3_ponte_via_deputado():
    g = gancho_prefeitura("Iperó", "cumpriu", 26.0, "A",
                          [{"deputado": "Valdomiro Lopes"}], [], 2025)
    assert "ponte já existe" in g and "Valdomiro Lopes" in g


def test_gancho_prioridade_4_alinhamento_partidario():
    pontes = [{"partido": "PT", "locais": [{"nome_urna": "Ana"}],
               "parlamentares": [{"deputado": "Dep X"}]}]
    g = gancho_prefeitura("Salto", "cumpriu", 26.0, "A", [], pontes, 2025)
    assert "Alinhamento partidário" in g and "Ana" in g and "Dep X" in g


def test_gancho_honesto_quando_nao_ha_nada():
    g = gancho_prefeitura("Guareí", "sem_dado", None, "", [], [], 2025)
    assert "Sem dado" in g and ("SIOPE" in g or "TCE" in g)
    g2 = gancho_prefeitura("Guareí", "cumpriu", 26.0, "C", [], [], 2025)
    assert "Sem gancho forte" in g2          # nunca fabrica um gancho


# ---- normalizacao --------------------------------------------------------- #
def test_normalizar_sem_nenhum_dado_mantem_os_municipios():
    """Município sem dado NÃO some do painel — sumir seria esconder o problema."""
    linhas = normalizar_prefeituras(MUNS)
    assert len(linhas) == 2
    for l in linhas:
        assert l["situacao_mde"] == "sem_dado"
        assert l["temperatura"] == "sem_dado"
        assert l["capag_rotulo"] == "não avaliado"
        assert l["gancho"]


def test_normalizar_junta_tudo():
    linhas = normalizar_prefeituras(
        MUNS,
        mde={"3521002": {"percentual": 22.0, "exercicio": 2025, "periodo": 6}},
        capag={"3521002": {"nota": "A"}},
        eleitos=[{"municipio": "Iperó", "cargo": "PREFEITO", "nome_urna": "Ana",
                  "nome": "Ana M", "partido": "PT"},
                 {"municipio": "Iperó", "cargo": "VEREADOR", "nome_urna": "Zeca",
                  "nome": "José", "partido": "PT"}],
        ranking=[{"deputado": "Dep X", "municipios_pfc": "IPERÓ"}],
        crm_parlamentares=[{"deputado": "Dep X", "partido": "PT"}])
    ip = next(l for l in linhas if l["municipio"] == "Iperó")
    assert ip["temperatura"] == "quente"
    assert ip["prefeito"] == "Ana" and ip["prefeito_partido"] == "PT"
    assert ip["n_vereadores"] == 1
    assert [d["deputado"] for d in ip["deputados_emenda"]] == ["Dep X"]
    assert ip["pontes"] and ip["pontes"][0]["partido"] == "PT"
    # Salto ficou sem nada e continua na lista, como "sem dado"
    sa = next(l for l in linhas if l["municipio"] == "Salto")
    assert sa["situacao_mde"] == "sem_dado"


def test_contagens():
    linhas = normalizar_prefeituras(
        MUNS, mde={"3521002": {"percentual": 22.0, "exercicio": 2025}},
        capag={"3521002": {"nota": "A"}})
    c = contagens_prefeituras(linhas)
    assert c["total"] == 2 and c["quentes"] == 1 and c["sem_dado"] == 1


def test_aviso_da_regra_de_ouro_existe_e_e_honesto():
    assert "não verba disponível" in AVISO_PREFEITURAS
    assert "saúde fiscal" in AVISO_PREFEITURAS


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
    print("OK — camada pura de Prefeituras (tabela MDE x CAPAG, gancho, pontes) passou.")
