"""Teste puro do aviso de contexto de Territórios em Aberto (Passo 7).

Cobre a função PURA `aviso_contexto_territorios` de ui/formato.py — sem Streamlit,
sem Sheets. Rodar da raiz do projeto:

    python tests/test_territorios_geral.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.formato import aviso_contexto_territorios  # noqa: E402


def test_sem_aviso_em_geral_e_estadual():
    """Geral e Estadual não mostram aviso (o conteúdo já é estadual)."""
    assert aviso_contexto_territorios("Geral") == ""
    assert aviso_contexto_territorios("Estadual") == ""
    # tolerante a caixa/espaços
    assert aviso_contexto_territorios("  estadual ") == ""


def test_aviso_em_federal_e_senador_cita_escopo_e_e_honesto():
    """Federal/Senador mostram aviso não-vazio, nomeando o escopo e declarando que a
    análise é ESTADUAL e que não há série equivalente — sem prometer nada federal."""
    for escopo in ("Federal", "Senador"):
        av = aviso_contexto_territorios(escopo)
        assert av, f"aviso vazio para {escopo}"
        assert escopo in av                         # nomeia o escopo selecionado
        assert "estadual" in av.lower()             # deixa claro que é execução estadual
        assert "não há série" in av.lower()         # honestidade: não existe série equivalente
        # HONESTIDADE: nunca promete candidatos/dados/série do próprio escopo
        assert "candidato" not in av.lower()


def test_robustez_a_none_e_desconhecido():
    """None e valores fora do conjunto não quebram — tratados como sem aviso."""
    assert aviso_contexto_territorios(None) == ""
    assert aviso_contexto_territorios("") == ""
    assert aviso_contexto_territorios("Municipal") == ""


if __name__ == "__main__":
    test_sem_aviso_em_geral_e_estadual()
    test_aviso_em_federal_e_senador_cita_escopo_e_e_honesto()
    test_robustez_a_none_e_desconhecido()
    print("OK — todos os testes de Territórios em Aberto (Passo 7) passaram.")
