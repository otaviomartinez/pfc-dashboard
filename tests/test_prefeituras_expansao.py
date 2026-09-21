"""Mapa de expansão (Passo 9) — camada pura em ui/formato.py.

CONTEXTO QUE MOTIVOU A RÉGUA: o plano definia o lead quente da expansão como
"abaixo do mínimo de MDE + CAPAG saudável". O dado real derrubou isso — NENHUM
dos 77 vizinhos está abaixo de 25%, e em SP inteiro são 2 de 644 (0,3%). A tela
nasceria vazia. Usamos o outro caminho quente que a seção 0 do plano prevê
("acima com folga + caixa"), reusando temperatura_prefeitura(), que já é testada.

    python tests/test_prefeituras_expansao.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.formato import (  # noqa: E402
    candidatos_expansao, contagens_expansao, faixa_mde, motivo_expansao,
)

VIZ = [{"cod_ibge": "3500101", "nome": "Folga Grande", "regiao_imediata": "Sorocaba"},
       {"cod_ibge": "3500202", "nome": "Folga Pequena", "regiao_imediata": "Sorocaba"},
       {"cod_ibge": "3500303", "nome": "No Limite", "regiao_imediata": "Tatuí"},
       {"cod_ibge": "3500404", "nome": "Sem Caixa", "regiao_imediata": "Tatuí"},
       {"cod_ibge": "3500505", "nome": "Sem Dado", "regiao_imediata": "Registro"}]
MDE = {"3500101": {"percentual": 33.0, "exercicio": 2025, "valor_aplicado": 90e6},
       "3500202": {"percentual": 31.0, "exercicio": 2025, "valor_aplicado": 10e6},
       "3500303": {"percentual": 26.0, "exercicio": 2025, "valor_aplicado": 50e6},
       "3500404": {"percentual": 30.0, "exercicio": 2025, "valor_aplicado": 70e6}}
CAPAG = {"3500101": {"nota": "A"}, "3500202": {"nota": "B"},
         "3500303": {"nota": "B"}, "3500404": {"nota": "C"}}
ANCORAS = {"Sorocaba": ["Iperó"], "Tatuí": ["Tatuí"], "Registro": ["Juquiá"]}


def test_faixa_mde_separa_limite_de_folga():
    """Distinção que situacao_mde não faz e a expansão precisa."""
    assert faixa_mde(24.9) == "abaixo"
    assert faixa_mde(25.0) == "limite"
    assert faixa_mde(28.0) == "limite"      # 28 ainda é limite
    assert faixa_mde(28.1) == "folga"
    assert faixa_mde(None) == "sem_dado"
    assert faixa_mde("abc") == "sem_dado"


def test_ordem_e_por_temperatura_depois_porte():
    linhas = candidatos_expansao(VIZ, MDE, CAPAG, ANCORAS)
    nomes = [x["municipio"] for x in linhas]
    # quentes primeiro, e entre eles o de maior porte na frente
    assert nomes[0] == "Folga Grande" and nomes[1] == "Folga Pequena"
    assert linhas[0]["temperatura"] == "quente"
    # o frio (CAPAG C) vai para o fim, mesmo tendo porte alto
    assert nomes[-1] == "Sem Caixa", nomes


def test_sem_dado_nao_vira_zero_nem_some():
    linhas = candidatos_expansao(VIZ, MDE, CAPAG, ANCORAS)
    sd = next(x for x in linhas if x["municipio"] == "Sem Dado")
    assert sd["faixa"] == "sem_dado"
    assert sd["temperatura"] == "sem_dado"
    assert sd["mde_percentual"] is None        # não virou 0
    assert "Sem índice" in sd["motivo"]


def test_motivo_e_honesto_sem_gancho():
    assert "precisa de despesa" in motivo_expansao("abaixo", "A")
    assert "já é prioridade" in motivo_expansao("folga", "A")
    assert "sem folga" in motivo_expansao("limite", "B")
    # sem caixa confirmada não inventa argumento:
    assert "Sem caixa confirmada" in motivo_expansao("folga", "C")
    assert "Sem caixa confirmada" in motivo_expansao("folga", "")


def test_ancora_cita_municipio_do_pfc_da_mesma_regiao():
    linhas = candidatos_expansao(VIZ, MDE, CAPAG, ANCORAS)
    sor = next(x for x in linhas if x["regiao_imediata"] == "Sorocaba")
    assert "Iperó" in sor["motivo"], sor["motivo"]


def test_contagens():
    c = contagens_expansao(candidatos_expansao(VIZ, MDE, CAPAG, ANCORAS))
    assert c["total"] == 5
    assert c["quentes"] == 2          # as duas com folga + caixa
    assert c["com_caixa"] == 3        # A, B, B
    assert c["limite"] == 1
    assert c["regioes"] == 3


def test_lista_vazia_nao_quebra():
    assert candidatos_expansao([]) == []
    assert contagens_expansao([])["total"] == 0


def test_com_dado_real_os_77_vizinhos_existem():
    """Sanidade contra os arquivos versionados de verdade."""
    from src.prefeituras import tce
    from src.prefeituras.config import carregar_municipios, municipios_da_regiao
    muns = carregar_municipios()
    nossos = {m["cod_ibge"] for m in muns}
    viz = {}
    for regiao in {m["regiao_imediata"] for m in muns}:
        for v in municipios_da_regiao(regiao):
            if v["cod_ibge"] not in nossos:
                viz[v["cod_ibge"]] = v
    assert len(viz) > 50, len(viz)
    linhas = candidatos_expansao(list(viz.values()), tce.carregar(2025), {}, {})
    assert len(linhas) == len(viz)
    # o TCE cobre SP inteiro: todo vizinho tem índice
    assert all(x["mde_percentual"] is not None for x in linhas)


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
    print("OK — mapa de expansão (faixas, ordem, motivo honesto, 77 vizinhos) passou.")
