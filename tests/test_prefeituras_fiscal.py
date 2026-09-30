"""Método fiscal revisado — src.prefeituras.fiscal.capacidade_fiscal.

Confere as regras: CAUC irregular bloqueia (override); caixa/pessoal ruins
rebaixam 'quente'→'morno'; FPM alto é só alerta; e — honestidade — fator
ausente vira 'sem dado', nunca penaliza.

    python tests/test_prefeituras_fiscal.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prefeituras.fiscal import capacidade_fiscal  # noqa: E402


def _sinal(res, fator):
    return next(s for s in res["sinais"] if s["fator"] == fator)


def test_cauc_irregular_bloqueia_mesmo_quente():
    r = capacidade_fiscal("quente", caixa=1000, pessoal_pct=40, cauc="irregular")
    assert r["temperatura"] == "bloqueado" and r["bloqueio"] is True
    assert "convênio" in r["resumo"]


def test_sem_dado_nunca_penaliza():
    r = capacidade_fiscal("quente")  # nada informado
    assert r["temperatura"] == "quente" and r["bloqueio"] is False
    assert all(s["nivel"] == "sem_dado" for s in r["sinais"])
    assert "sem ressalvas" in r["resumo"]


def test_caixa_apertado_rebaixa_quente_para_morno():
    r = capacidade_fiscal("quente", caixa=-50, cauc="regular")
    assert r["temperatura"] == "morno"
    assert _sinal(r, "caixa")["nivel"] == "ruim"


def test_pessoal_prudencial_rebaixa_mas_alerta_nao():
    ruim = capacidade_fiscal("quente", pessoal_pct=52.0)     # >= 51.3
    assert ruim["temperatura"] == "morno" and _sinal(ruim, "pessoal")["nivel"] == "ruim"
    alerta = capacidade_fiscal("quente", pessoal_pct=49.0)   # entre alerta e prudencial
    assert alerta["temperatura"] == "quente" and _sinal(alerta, "pessoal")["nivel"] == "alerta"


def test_fpm_alto_e_so_alerta_informativo():
    r = capacidade_fiscal("quente", dependencia_fpm=75, caixa=10, pessoal_pct=30, cauc="regular")
    assert r["temperatura"] == "quente"                      # FPM não rebaixa sozinho
    assert _sinal(r, "fpm")["nivel"] == "alerta"
    assert "FPM" in r["resumo"]


def test_tudo_saudavel_mantem_base():
    r = capacidade_fiscal("quente", caixa=500, pessoal_pct=40, dependencia_fpm=30, cauc="regular")
    assert r["temperatura"] == "quente" and r["bloqueio"] is False
    assert all(_sinal(r, f)["nivel"] == "bom" for f in ("caixa", "pessoal", "fpm", "cauc"))


def test_frio_nao_vira_quente():
    # os fatores novos nunca PROMOVEM; base frio segue frio (só rebaixam/bloqueiam)
    r = capacidade_fiscal("frio", caixa=9999, pessoal_pct=10, cauc="regular")
    assert r["temperatura"] == "frio"


if __name__ == "__main__":
    test_cauc_irregular_bloqueia_mesmo_quente()
    test_sem_dado_nunca_penaliza()
    test_caixa_apertado_rebaixa_quente_para_morno()
    test_pessoal_prudencial_rebaixa_mas_alerta_nao()
    test_fpm_alto_e_so_alerta_informativo()
    test_tudo_saudavel_mantem_base()
    test_frio_nao_vira_quente()
    print("OK — método fiscal revisado (CAUC/caixa/pessoal/FPM, honesto) passou.")
