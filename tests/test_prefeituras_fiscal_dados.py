"""Os fatores fiscais REAIS: TCE (pessoal/resultado) + FPM + a tela.

O método fiscal já era testado em test_prefeituras_fiscal.py com valores de
mentira. Aqui o alvo é a LIGAÇÃO com o dado de verdade — que é onde este projeto
já se machucou duas vezes: a fração do TCE (0,2736 lido como 0,27%) e a coluna
errada do SICONFI.

    python tests/test_prefeituras_fiscal_dados.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prefeituras import fiscal, fpm, tce  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_pessoal_do_tce_vira_porcentagem():
    """A coluna é FRAÇÃO. Sem o x100, 38,88% viraria 0,39% e o painel diria que
    nenhuma prefeitura gasta com pessoal."""
    ano = tce.exercicio_com_pessoal()
    assert ano, "o CSV do TCE deveria ter algum ano com pessoal apurado"
    reg = tce.carregar_fiscal(ano)
    assert len(reg) > 500, f"esperava os ~644 municípios de SP, vi {len(reg)}"
    pcts = [r["pessoal_pct"] for r in reg.values() if r["pessoal_pct"] is not None]
    assert pcts, "nenhum pessoal apurado"
    assert 10 < min(pcts) and max(pcts) < 100, \
        f"fora de escala (fração não convertida?): {min(pcts)}–{max(pcts)}"


def test_ano_sem_pessoal_apurado_devolve_none_nao_zero():
    """Ausência é ausência. Zero seria 'gasta nada com pessoal' — uma mentira."""
    anos = tce.exercicios_disponiveis()
    ano_recente = anos[0]
    reg = tce.carregar_fiscal(ano_recente)
    for r in reg.values():
        assert r["pessoal_pct"] is None or r["pessoal_pct"] > 0


def test_resultado_orcamentario_nao_e_chamado_de_caixa():
    """Caixa é o RGF-Anexo 05, que não existe para SP. Confundir os dois seria
    afirmar folga de caixa a partir de outro número."""
    fonte = open(os.path.join(RAIZ, "src", "prefeituras", "fiscal.py"),
                 encoding="utf-8").read()
    assert "sinal_resultado" in fonte
    assert "NÃO é disponibilidade de caixa" in fonte
    s = fiscal.sinal_resultado(-5.5)
    assert s["fator"] == "resultado" and "caixa" not in s["texto"].lower()


def test_resultado_e_informativo_nao_rebaixa_sozinho():
    cap = fiscal.capacidade_fiscal("quente", resultado_pct=-9.0)
    assert cap["temperatura"] == "quente", "déficit sozinho não pode rebaixar"
    assert "vermelho" in cap["resumo"]


def test_fator_ausente_nunca_penaliza():
    """Regra 5c: sem dado ≠ dado ruim."""
    cap = fiscal.capacidade_fiscal("quente")
    assert cap["temperatura"] == "quente"
    assert all(s["nivel"] == "sem_dado" for s in cap["sinais"])
    assert not cap["bloqueio"]


def test_fpm_loader_gracioso_e_descarta_linha_sem_percentual():
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "fpm_2024.csv"), "w", encoding="utf-8") as f:
        f.write("cod_ibge,municipio,exercicio,fpm,receitas_correntes,dependencia_pct,origem\n")
        f.write("3552205,Sorocaba,2024,10,100,10.0,siconfi-dca\n")
        f.write("3520509,Iperó,2024,,,,siconfi-dca\n")
    reg = fpm.carregar(2024, d)
    assert reg["3552205"]["dependencia_pct"] == 10.0
    assert "3520509" not in reg, "linha sem percentual não pode entrar"
    assert fpm.carregar(1999, d) == {}, "ano inexistente -> {} (não quebra a tela)"
    assert fpm.exercicios_disponiveis(d) == [2024]


def test_fpm_repetido_entre_municipios_e_esperado():
    """ARMADILHA DE LEITURA: ver o mesmo FPM em municípios diferentes parece
    coleta quebrada — eu mesmo achei que era, e quase apaguei o CSV bom. O FPM
    é distribuído por COEFICIENTE de faixa de população: mesma faixa, mesmo
    valor. O que varia é o denominador. Este teste existe para que ninguém
    "conserte" o coletor por causa disso."""
    caminho = os.path.join(RAIZ, "data", "prefeituras")
    anos = fpm.exercicios_disponiveis(caminho)
    if not anos:
        return                      # antes da 1ª coleta não há o que checar
    reg = fpm.carregar(anos[0], caminho)
    if len(reg) < 20:
        return
    valores = [r["fpm"] for r in reg.values()]
    assert len(set(valores)) < len(valores), \
        "esperado: valores de FPM repetidos entre municípios da mesma faixa"
    pcts = [r["dependencia_pct"] for r in reg.values()]
    assert len(set(pcts)) > len(pcts) * 0.8, \
        "a dependência final tem de variar — o denominador é próprio de cada um"
    assert 0 < min(pcts) and max(pcts) < 100, f"fora de escala: {min(pcts)}–{max(pcts)}"


def test_importador_fpm_usa_a_coluna_bruta():
    """A resposta do DCA tem duas colunas; 'Deduções - FUNDEB' daria percentual
    inventado."""
    fonte = open(os.path.join(RAIZ, "scripts", "importar_fpm.py"), encoding="utf-8").read()
    assert 'COLUNA_BRUTA = "Receitas Brutas Realizadas"' in fonte
    assert "1.7.1.1.51.0.0" in fonte and "1.0.0.0.00.0.0" in fonte
    assert "if not linhas:" in fonte, "não pode gravar CSV vazio"


def test_tela_mostra_o_bloco_e_diz_o_que_falta():
    app = open(os.path.join(RAIZ, "app.py"), encoding="utf-8").read()
    assert app.count("_render_capacidade_fiscal(") == 3, \
        "1 definição + os 2 dossiês (nossos municípios e expansão)"
    assert "não há fonte pública automática" in app, \
        "a tela é obrigada a dizer que caixa/CAUC não têm fonte"
    assert "exercício {ano}" in app, "todo fator precisa carregar o exercício"


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
            print(f"ok  {nome}")
    print("fatores fiscais reais: todos os testes passaram")
