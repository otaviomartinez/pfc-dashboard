"""Ranking da Captação: segunda chance no radar + Prioridade no app.

DOIS FUROS REAIS, vistos no log da rodada de 07/10/2026:
  1. 284 itens extraídos, 36 com sinal, SÓ 2 na fila — 25 barrados por
     aderência. O veredito era dado pelo título da listagem; a página só era
     lida para quem já tinha passado. "Chamada Pública 03/2026" caía às cegas.
  2. O radar calcula prazo e valor, mas a planilha guarda só a nota de TEMA, e
     o app ordenava só por ela: edital fechando em 6 dias ficava atrás de
     notícia sem data com nota 2 pontos maior.

    python tests/test_radar_ranking.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from radar import main as radar_main  # noqa: E402
from radar.scorer import texto_sem_termos  # noqa: E402
from ui.formato import prioridade_oportunidade  # noqa: E402


# ---------------------------------------------------------------- 2ª chance
def test_texto_magro_e_reconhecido():
    assert texto_sem_termos("Chamada Pública 03/2026 — inscrições abertas")
    assert not texto_sem_termos("Edital para organizações da sociedade civil")
    assert not texto_sem_termos("Bolsa de mestrado"), "negativa: reprovado de verdade"
    assert not texto_sem_termos("Olimpíada de matemática — medalha"), "de aluno: idem"


def _pagina_falsa(conteudo_por_titulo):
    """Simula a leitura da página: troca a descrição pelo 1º parágrafo."""
    lidas = []

    def enriquecer(lote, maximo=25):
        for op in lote[:maximo]:
            lidas.append(op["titulo"])
            if op["titulo"] in conteudo_por_titulo:
                op["descricao"] = conteudo_por_titulo[op["titulo"]]
        return {"tentadas": len(lote[:maximo]), "enriquecidas": 0,
                "com_prazo": 0, "com_valor": 0}
    return enriquecer, lidas


def test_resgata_quem_era_do_tema_e_so_tinha_titulo_magro():
    magro = {"titulo": "Chamada Pública 03/2026", "descricao": "", "fonte": "X",
             "url": "https://x.org/c03"}
    enriquecer, lidas = _pagina_falsa({
        "Chamada Pública 03/2026":
            "Apoio a projetos de iniciação científica em escola pública para "
            "juventude em situação de vulnerabilidade social, com foco em "
            "educação básica e formação de professores."})
    resg, resto, magros, _ = radar_main.segunda_chance([magro], enriquecer=enriquecer)
    assert lidas == ["Chamada Pública 03/2026"]
    assert resg and resg[0] is magro, "página do tema -> volta para a fila"
    assert "2ª chance" in magro["motivo"]
    assert resto == []


def test_pagina_fora_do_tema_continua_barrada():
    magro = {"titulo": "Edital 12/2026", "descricao": "", "url": "https://y.org"}
    enriquecer, _ = _pagina_falsa({"Edital 12/2026": "Venda de imóveis da prefeitura."})
    resg, resto, _, _ = radar_main.segunda_chance([magro], enriquecer=enriquecer)
    assert resg == [] and resto == [magro], "ler a página não é passe livre"


def test_reprovado_de_verdade_nem_tem_a_pagina_lida():
    reprovado = {"titulo": "Bolsa de mestrado 2026", "descricao": "", "url": "https://z"}
    enriquecer, lidas = _pagina_falsa({})
    resg, resto, magros, _ = radar_main.segunda_chance([reprovado], enriquecer=enriquecer)
    assert lidas == [] and magros == [] and resto == [reprovado]


def test_teto_de_paginas_respeitado():
    lote = [{"titulo": f"Chamada {i}", "descricao": "", "url": f"https://w/{i}"}
            for i in range(40)]
    enriquecer, lidas = _pagina_falsa({})
    radar_main.segunda_chance(lote, maximo=25, enriquecer=enriquecer)
    assert len(lidas) == 25, "o workflow tem 20 min; o teto protege o tempo"


def test_resumo_da_rodada_roda_com_e_sem_segunda_chance():
    """BUG REAL da 1ª versão: o resumo é uma função SEPARADA de executar(), e a
    linha nova leu `magros` como se estivesse lá dentro -> NameError no fim da
    rodada de 07/10 (depois de gravar, então a fila entrou, mas o workflow
    ficou vermelho). Os testes da segunda_chance passavam: ninguém chamava o
    resumo. Agora chama."""
    import contextlib
    import io as _io
    resg = [{"fonte": "Capta", "titulo": "Chamada Pública 03/2026"}]
    base = dict(ancora_ok=1, generica_ok=1, brutos=[], com_sinal=[], descartados=[],
                unicas=[], filtradas=[], falhas={}, n_cand=0, destino="teste",
                stats_enr={"tentadas": 0, "enriquecidas": 0, "com_prazo": 0, "com_valor": 0})
    out = _io.StringIO()
    with contextlib.redirect_stdout(out):
        radar_main._resumo(**base, segunda={"magros": resg, "resgatadas": resg,
                                            "stats": {"tentadas": 1}})
        radar_main._resumo(**base)          # rodada antiga, sem o parâmetro
    texto = out.getvalue()
    assert "2ª chance: 1 itens de texto magro · 1 páginas lidas · 1 resgatados" in texto
    assert "Chamada Pública 03/2026" in texto


# ---------------------------------------------------------------- Prioridade
def test_edital_que_fecha_logo_passa_noticia_sem_data():
    edital = {"score": 70, "dias": 6, "valor": ""}
    noticia = {"score": 72, "dias": None, "valor": ""}
    assert prioridade_oportunidade(edital) > prioridade_oportunidade(noticia)


def test_prazo_a_confirmar_nao_ganha_urgencia():
    """Regra 3: data incerta não vira urgência. 400 dias = chute de ano."""
    assert prioridade_oportunidade({"score": 60, "dias": 400, "valor": ""}) == 60
    assert prioridade_oportunidade({"score": 60, "dias": None, "valor": ""}) == 60


def test_vencido_nao_pontua_e_valor_soma_pouco():
    assert prioridade_oportunidade({"score": 60, "dias": -3, "valor": ""}) == 60
    assert prioridade_oportunidade({"score": 60, "dias": None, "valor": "R$ 80 mil"}) == 65


def test_app_usa_prioridade_como_padrao_nas_duas_listas():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = open(os.path.join(raiz, "app.py"), encoding="utf-8").read()
    assert '["Prioridade", "Score", "Dias restantes", "Valor"]' in app
    assert app.count("prioridade_oportunidade(o)") >= 2, \
        "painel inicial e tela do Radar na mesma ordem"
    assert 'ops.sort(key=lambda o: o["score"], reverse=True)' not in app


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
            print(f"ok  {nome}")
    print("ranking da Captação: todos os testes passaram")
