"""Teste puro do Relatório Geral de Emendas (Passo 6).

Cobre as funções PURAS de ui/formato.py — sem Streamlit, sem reportlab, sem
Sheets: o builder de linhas (valor rotulado por escopo, sem total) e o resumo
(só contagens). Rodar da raiz do projeto:

    python tests/test_relatorio_geral.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.formato import (  # noqa: E402
    VALOR_CRM,
    VALOR_SUGERIDO,
    itens_relatorio_parlamentares,
    resumo_relatorio_parlamentares,
    rotulo_valor,
)

# Registros MISTOS falsos, no formato de carregar_parlamentares (estadual + federal).
REGS = [
    {"escopo": "estadual", "escopo_nome": "Estadual", "nome": "Ana Lima",
     "partido": "PT", "score": 61, "ader": 55, "chance": 40,
     "temp": "Morno", "status": "Reunião agendada",
     "valor_txt": "R$ 100", "valor_tipo": VALOR_CRM},
    {"escopo": "federal", "escopo_nome": "Federal", "nome": "Vitor Lippi",
     "partido": "PSDB", "score": 97, "ader": 90, "chance": 70,
     "temp": "Muito Quente", "status": "Emenda aprovada",
     "valor_txt": "R$ 900", "valor_tipo": VALOR_SUGERIDO},
    {"escopo": "estadual", "escopo_nome": "Estadual", "nome": "Bruno Sá",
     "partido": "PP", "score": 30, "ader": 20, "chance": 10,
     "temp": "Frio", "status": "Não iniciado",
     "valor_txt": "", "valor_tipo": ""},
]


def test_linhas_rotulam_valor_por_escopo_sem_total():
    """Cada linha rotula o valor pelo SEU tipo; federal sempre 'sugerido'; e não
    há total somando execução com faixa (100 + 900 nunca vira 1000)."""
    linhas = itens_relatorio_parlamentares(REGS)
    assert len(linhas) == 3
    ana, lippi, bruno = linhas

    # rótulo correto por escopo — a barreira da regra de ouro
    assert lippi["valor_rotulo"] == rotulo_valor(VALOR_SUGERIDO) == "valor sugerido (faixa)"
    assert ana["valor_rotulo"] == rotulo_valor(VALOR_CRM) == "registrado no CRM"
    assert bruno["valor_txt"] == "" and bruno["valor_rotulo"] == "sem valor"

    # score federal COPIADO, nunca recalculado (Vitor Lippi = 97)
    assert lippi["score"] == "97"

    # REGRA DE OURO: nenhuma linha carrega campo de total, e o valor exibido é o
    # próprio da linha — jamais a soma de execução estadual com faixa federal.
    for ln in linhas:
        assert "total" not in ln and "valor_total" not in ln
    soma_texto = "".join(ln["valor_txt"] for ln in linhas).replace(".", "").replace(" ", "")
    assert "1000" not in soma_texto


def test_resumo_so_contagens_sem_dinheiro():
    """O resumo é só pipeline (contagens int) — nunca agrega valor."""
    r = resumo_relatorio_parlamentares(REGS)
    assert r == {"total": 3, "em_articulacao": 2, "reunioes": 1, "aprovadas": 1}
    assert all(isinstance(v, int) for v in r.values())
    assert not any(("valor" in k.lower() or "r$" in k.lower()) for k in r)


def test_senador_e_vazio_sao_elegantes():
    """Filtro sem gente (ex.: Senador hoje) → listas/contagens vazias, sem erro."""
    assert itens_relatorio_parlamentares([]) == []
    assert resumo_relatorio_parlamentares([]) == {
        "total": 0, "em_articulacao": 0, "reunioes": 0, "aprovadas": 0}


if __name__ == "__main__":
    test_linhas_rotulam_valor_por_escopo_sem_total()
    test_resumo_so_contagens_sem_dinheiro()
    test_senador_e_vazio_sao_elegantes()
    print("OK — todos os testes do Relatório Geral (Passo 6) passaram.")
