"""Radar sem lixo: os títulos REAIS que estavam na fila em out/2026.

Cada lixo abaixo foi visto na tela do app; cada bom é edital que o PFC pode
disputar. O crivo único (radar.scorer.motivo_lixo) tem de barrar todos os
primeiros e deixar passar todos os segundos — no radar e na exibição.

    python tests/test_radar_lixo.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from radar import scorer as S  # noqa: E402
from radar.dedup import deduplicar, mesmo_edital  # noqa: E402

LIXO = [
    "Estudantes criam jogos temáticos sobre cyberbullying e inclusão em desafio interescolar",
    "Edital Conta que soma oferece formação gratuita em educação financeira para jovens",
    "Fundação Cecierj abre inscrições para o Curso de Formação Continuada de Professores 2026.3",
    "O mundo diante da crise para atrair, formar e reter professores",
    "Aula ensina como elaborar proposta de captação de recursos",
    "Futuras Cientistas abre inscrições para Imersão Científica 2027",
    "Prêmio de US$ 1 milhão quer mais brasileiros entre os melhores educadores do mundo",
    "Edital Nº 01/2025 – 2VCC",
    "Campus Mobile abre inscrições com viagem ao Vale do Silício entre os prêmios",
    "Boas práticas em empreendedorismo de impacto na saúde",
    "Grupo Equatorial abre chamada com mais de R$ 61 milhões para projetos de eficiência energética",
    "BNDES lança edital de R$ 17,5 milhões para organizações periféricas da Região Norte e do Maranhão",
    "Cantora Iza lança edital Entra na Roda para investir em empreendedores negros",
    "Mulheres na Ciência: inscrições terminam em 8 de agosto",
    "Quase um ano após prêmio mundial, diretor é afastado da Escola Parque dos Sonhos",
    "Prorrogadas as inscrições para a 25ª edição do Prêmio Fundação FEAC de Jornalismo",
    "Prêmio FEAC de Jornalismo anuncia comitê que irá julgar as produções",
    "Museu Ciência e Vida abre inscrições para o Torneio Regional de Robótica (TJR MCV)",
    "4ª Semana Brasileira de Educação Midiática tem inscrições abertas",
    "Santa Luzia do Paruá lança edital para contratar organização especializada em captação internacional",
    # 1ª rodada real com o filtro novo (04/11/2026): editais velhos da FBB, ano/número
    "Edital de Seleção Pública nº 2024/008 – Novo CATAFORTE",
    "Edital de Chamada Pública nº 2023/00132 – Água para Produção",
    "Edital de Seleção Pública n°2014/020 – ECOFORTE – Extrativismo",
    "Edital de Seleção Pública nº 2017/030 ECOFORTE – Redes",
]
BONS = [
    "Zurich Seguros abre edital nacional para apoiar projetos sociais via leis de incentivo fiscal",
    "Instituto Porto abre edital de R$ 400 mil para OSCs da Grande São Paulo e Grande Belo Horizonte",
    "Edital Social Porto 2026 seleciona projetos incentivados em seis estados",
    "Globo e Fundação Roberto Marinho lançam Prêmio LED 2026",
    "Prêmio Pacto Contra a Fome distribuirá R$ 600 mil para iniciativas em território nacional",
    "Edital da Jornada TransformAção de 2026 é lançado",
    "Pague Menos recebe inscrições para edital de apoio a OSCs",
    "Edital Impactarte",
    "Itaú Social abre edital para formação de professores da rede pública",
    "Prêmio LED Globo 2027 abre inscrições com R$ 1,2 milhão em premiação",
    "Plan International Brasil abre edital de R$ 600 mil para igualdade de gênero",
]
HOJE = datetime.date(2026, 11, 4)


def test_todo_lixo_real_e_barrado():
    passaram = [t for t in LIXO if S.avaliar_sinal({"titulo": t, "descricao": ""})[0]]
    assert not passaram, f"lixo que ainda passa: {passaram}"


def test_todo_edital_bom_passa_no_crivo():
    barrados = [(t, S.avaliar_sinal({"titulo": t, "descricao": ""})[1]) for t in BONS
                if not S.avaliar_sinal({"titulo": t, "descricao": ""})[0]]
    assert not barrados, f"edital bom barrado: {barrados}"


def test_edital_de_osc_tem_aderencia_para_entrar():
    """Antes: 'OSCs' e 'projetos sociais' não contavam — aderência 30, fora da fila."""
    for t in ("Pague Menos recebe inscrições para edital de apoio a OSCs",
              "Zurich Seguros abre edital nacional para apoiar projetos sociais via leis de incentivo fiscal"):
        assert S.pontuacao({"titulo": t, "descricao": ""})["score_aderencia"] >= 41, t


def test_premio_sozinho_nao_e_oportunidade():
    assert not S.tem_sinal_de_oportunidade("Diretor premiado em 2025 fala sobre prêmio", "")
    assert S.tem_sinal_de_oportunidade("Prêmio X abre inscrições para organizações", "")
    assert S.tem_sinal_de_oportunidade("Prêmio distribui R$ 100 mil", "")


def test_banco_nacional_nao_e_edital_nacional():
    assert S.e_restrito_fora_sudeste("BNDES (Banco Nacional de Desenvolvimento) lança edital "
                                     "para a Região Norte", "")
    assert not S.e_restrito_fora_sudeste("Edital nacional para organizações de todo o país", "")


def test_termo_curto_exige_palavra_inteira():
    """'stem' casava 'sistema'; 'osc' casaria 'oscila'."""
    assert not S._tem("sistema de gestao que oscila", ["stem", "osc"])
    assert S._tem("programa stem para oscs", ["stem", "oscs"])


def test_edital_de_ano_passado():
    assert S.e_edital_de_ano_passado("Edital Nº 01/2025 – 2VCC", HOJE)
    assert not S.e_edital_de_ano_passado("Edital Nº 03/2026", HOJE)
    assert S.e_edital_de_ano_passado("Edital de Seleção Pública nº 2024/008 – Novo CATAFORTE", HOJE)
    assert not S.e_edital_de_ano_passado("Edital de Seleção Pública nº 2026/004", HOJE)
    assert not S.e_edital_de_ano_passado("Edital Nº 01/2025", datetime.date(2026, 2, 1)), \
        "no começo do ano, o edital do ano anterior ainda pode estar aberto"


def test_valor_em_milhoes():
    assert S._valor_reais("chamada com mais de R$ 61 milhões") == 61_000_000
    assert S._valor_reais("R$ 17,5 milhões") == 17_500_000
    assert S._valor_reais("R$ 400 mil") == 400_000
    assert S._valor_reais("R$ 1 milhão") == 1_000_000


def test_mesmo_edital_de_duas_fontes():
    a = "Zurich Seguros abre edital nacional para apoiar projetos sociais via leis de incentivo fiscal"
    b = "Zurich Seguros abre edital para projetos sociais com incentivo fiscal 29 Set 2026"
    assert mesmo_edital(a, b)
    unicas, dup = deduplicar([{"titulo": b, "url": "https://outra"}], [{"titulo": a, "url": "https://uma"}])
    assert (unicas, dup) == ([], 1)


def test_editais_diferentes_do_mesmo_financiador_nao_colam():
    assert not mesmo_edital(
        "Instituto Porto abre edital de R$ 400 mil para OSCs da Grande São Paulo",
        "Edital Social Porto 2026 seleciona projetos incentivados em seis estados")


def test_formacao_de_professores_institucional_nao_e_curso():
    """Edital PARA projetos de formação de professores é captação; curso é vaga."""
    assert not S.motivo_lixo("Itaú Social abre edital para formação de professores da rede pública")
    assert S.motivo_lixo("Cecierj abre inscrições para o Curso de Formação Continuada de Professores")


def test_tela_usa_o_mesmo_crivo_e_corrige_valor():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fonte = open(os.path.join(raiz, "app.py"), encoding="utf-8").read()
    assert "motivo_lixo(o[\"titulo\"], o[\"desc\"])" in fonte
    assert "mesmo_edital(" in fonte
    from ui.formato import _op_de_novidade
    op = _op_de_novidade({"Título": "Chamada com mais de R$ 61 milhões para projetos",
                          "Valor estimado": "R$ 61 mil"})
    assert op["valor"] == "R$ 61,00 mi", op["valor"]


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
            print(f"ok  {nome}")
    print("radar sem lixo: todos os testes passaram")
