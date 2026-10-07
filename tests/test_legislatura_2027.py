"""Legislatura 2027: bancada eleita x histórico de emendas, sem recalcular nada.

    python tests/test_legislatura_2027.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import legislatura2027 as L  # noqa: E402

HOJE = datetime.date(2026, 10, 7)


def _c(cargo, numero, urna, nome, votos, sit="Eleito por QP", partido="PARTIDO LIBERAL", sigla="PL"):
    return {"cargo": cargo, "numero": numero, "nome_urna": urna, "nome": nome, "votos": str(votos),
            "situacao": sit, "partido": partido, "sigla": sigla, "pct_votos": "0.5",
            "resultado_em": "04/10/2026 - 22:58:07"}


CANDS = [
    _c("DEPUTADO ESTADUAL", "40000", "VALDOMIRO LOPES", "VALDOMIRO LOPES DA SILVA", 86893),
    _c("DEPUTADO ESTADUAL", "22000", "FULANO NOVO", "FULANO NOVO DOS SANTOS", 300000),
    _c("DEPUTADO ESTADUAL", "13000", "", "ELISABETH SAHAO", 66572, sit="Suplente"),
    _c("DEPUTADO ESTADUAL", "45000", "SEM HISTORICO", "SEM HISTORICO", 50000),
    _c("DEPUTADO FEDERAL", "2222", "MARCIO ALVINO", "MARCIO ALVINO", 261325),
    _c("SENADOR", "222", "ANDRÉ DO PRADO", "", 12703089, partido="", sigla=""),
]
FONTES = dict(
    candidatos=CANDS,
    titulares=[{"nome_parlamentar": "Valdomiro Lopes", "email_oficial": "v@al.sp.gov.br",
                "telefone_gabinete": "(11) 1", "pagina_alesp": "https://al"},
               {"nome_parlamentar": "Beth Sahão"}, {"nome_parlamentar": "André do Prado"},
               {"nome_parlamentar": "Sem Historico"}],
    territorio=[{"deputado": "Valdomiro Lopes", "score_pfc": "87.5", "autorizado_pfc": "409297",
                 "pago_pfc": "409297", "municipios_pfc": "MIRASSOL", "alinhamento_pct": "43"},
                {"deputado": "Beth Sahão", "score_pfc": "71", "autorizado_pfc": "200000",
                 "pago_pfc": "100000", "municipios_pfc": "TATUÍ", "alinhamento_pct": "30"}],
    expansao=[{"deputado": "André do Prado", "score_expansao": "60", "autorizado_geral_edusoc": "1900000",
               "pago_geral_edusoc": "1000000", "alinhamento_pct": "5"}],
    federal=[{"deputado": "Marcio Alvino", "score_execucao": "100", "edusoc_empenhado": "29620329",
              "edusoc_pago": "28132194", "n_municipios_pfc": "1", "municipios_pfc": "JUQUIÁ",
              "fracao_edusoc": "0.27"}],
)


def _d():
    return L.montar(**FONTES, hoje=HOJE)


def test_ordem_por_faixa_territorio_primeiro():
    alesp = _d()["casas"]["ALESP"]
    assert [p["nome"] for p in alesp] == ["Valdomiro Lopes", "Sem Historico", "Fulano Novo"]
    assert [p["faixa"] for p in alesp] == [1, 3, 4]


def test_novo_nao_ganha_historico_nem_contato_inventado():
    novo = _d()["casas"]["ALESP"][-1]
    assert novo["origem"] == "novo" and novo["historico"] is None and novo["contato_oficial"] == {}
    assert "começa do zero" in novo["gancho"]


def test_reeleito_traz_contato_oficial_e_autorizado_separado_do_pago():
    v = _d()["casas"]["ALESP"][0]
    assert v["contato_oficial"]["email"] == "v@al.sp.gov.br"
    assert v["historico"]["autorizado"] == 409297 and v["historico"]["pago"] == 409297
    assert "autorizado" in v["gancho"] and "Mirassol" in v["gancho"]


def test_troca_de_casa_leva_o_historico_da_casa_de_origem():
    andre = _d()["casas"]["Senado"][0]
    assert andre["origem"] == "outra_casa" and andre["origem_rotulo"] == "Vem da ALESP"
    assert andre["historico"]["fonte"] == "estadual"
    assert andre["gancho"].startswith("Vem da ALESP")


def test_federal_usa_empenhado_nunca_autorizado():
    m = _d()["casas"]["Câmara"][0]
    assert m["historico"]["fonte"] == "federal" and "empenhados" in m["gancho"]
    assert "autorizado" not in m["historico"]


def test_quem_sai_com_historico_e_a_ultima_janela():
    saindo = _d()["saindo"]
    assert [s["nome"] for s in saindo] == ["Beth Sahão"]
    assert saindo[0]["evidencia"] == "Elisabeth Sahao", "a tela mostra COMO casou"


def test_contagem_e_posse():
    d = _d()
    assert d["contagens"]["ALESP"]["total"] == 3 and d["contagens"]["ALESP"]["novo"] == 1
    assert d["dias_posse"] == (datetime.date(2027, 2, 1) - HOJE).days == 117
    assert d["resultado_em"].startswith("04/10/2026")


def test_partido_nunca_entra_na_ordem():
    """Mesmo histórico, partidos diferentes: a ordem só muda pelos votos."""
    import copy
    f = copy.deepcopy(FONTES)
    for c in f["candidatos"]:
        if c["numero"] == "22000":
            c["sigla"], c["partido"] = "PT", "PARTIDO DOS TRABALHADORES"
    a = [p["nome"] for p in L.montar(**FONTES, hoje=HOJE)["casas"]["ALESP"]]
    b = [p["nome"] for p in L.montar(**f, hoje=HOJE)["casas"]["ALESP"]]
    assert a == b


def test_partido_curto_nao_deduz():
    assert L.partido_curto({"partido": "FEDERAÇÃO BRASIL DA ESPERANÇA - FE BRASIL"}) == "FE BRASIL"
    assert L.partido_curto({"partido": "FEDERAÇÃO PSOL REDE"}) == "FEDERAÇÃO PSOL REDE"
    assert L.partido_curto({"partido": "PARTIDO LIBERAL", "sigla": "PL"}) == "PL"


def test_sem_arquivo_nada_quebra():
    d = L.montar([], [], [], [], [], hoje=HOJE)
    assert d["contagens"]["ALESP"]["total"] == 0 and d["saindo"] == []


def test_dados_reais_batem_94_70_2():
    d = L.montar(**L.carregar_fontes(), hoje=HOJE)
    if not d["resultado_em"]:
        return
    assert [d["contagens"][c]["total"] for c in ("ALESP", "Câmara", "Senado")] == [94, 70, 2]


def test_aba_e_so_leitura_e_esta_na_sidebar():
    """A aba não escreve em lugar nenhum: nada de porta de escrita do Sheets."""
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fonte = open(os.path.join(raiz, "app.py"), encoding="utf-8").read()
    ini = fonte.index("# LEGISLATURA 2027 — a bancada eleita")
    fim = fonte.index("# PAINEL PREFEITURAS — a terceira perna")
    trecho = fonte[ini:fim]
    for porta in ("adicionar_", "atualizar_", "anexar_", "gravar", "append_row", "update_cell"):
        assert porta not in trecho, f"a aba 2027 não pode escrever ({porta})"
    assert '"Legislatura 2027"' in fonte[fonte.index("EMENDA_PAGES = "):][:200]
    assert 'modo == "legislatura"' in fonte


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
            print(f"ok  {nome}")
    print("legislatura 2027: todos os testes passaram")
