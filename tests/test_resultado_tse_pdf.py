"""Resultado oficial 2026 a partir dos PDFs do TRE-SP (SISTOT) + casamento de nomes.

Os trechos abaixo são copiados do texto real dos relatórios (pdftotext -layout),
com as três armadilhas do documento: nome quebrado em duas linhas, "% Votos"
que é do PARTIDO e federação sem partido individual.

    python tests/test_resultado_tse_pdf.py
"""
import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from src import eleicoes  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "imp_pdf", os.path.join(RAIZ, "scripts", "importar_resultado_tse_pdf.py"))
imp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(imp)

POR_PARTIDO = """\
                           Justiça Eleitoral/SP                                                                 04/10/2026
                           OFICIAL
Cargo: Deputado Estadual

AGIR                                                     Votos            % Votos      Destinação de votos   Situação da
                                                       computados      computados **                         totalização

36111 - JEFFERSON ELOY                                   2.341             0.06         Anulado sub judice    Não eleito

FEDERAÇÃO BRASIL DA ESPERANÇA - FE BRASIL              Votos          % Votos      Destinação de votos    Situação da
                                                       computados      computados **                         totalização
*13633 - LEONARDO DOS REIS ADORNO BECKER              122.158          15.68              Válido          Eleito por QP
GRANDINI
*13131 - EMIDIO PEREIRA DE SOUZA                      108.275          15.68              Válido          Eleito por QP
Resultado em 04/10/2026 - 22:58:07
"""

ELEITOS = """\
Cargo: Deputado Estadual
13633 - LEONARDO GRANDINI              122.158         0.52%          Válido   *Eleito por QP
13131 - EMIDIO DE SOUZA                108.275         0.46%          Válido   *Eleito por QP
Resultado em 04/10/2026 - 22:58:07
"""


def _registros():
    pp, quando = imp.ler_relatorio(POR_PARTIDO, por_partido=True)
    el, _ = imp.ler_relatorio(ELEITOS, por_partido=False)
    return {r["numero"]: r for r in imp.juntar(el, pp, quando)}


def test_nome_quebrado_em_duas_linhas_e_juntado():
    assert _registros()["13633"]["nome"] == "LEONARDO DOS REIS ADORNO BECKER GRANDINI"


def test_percentual_do_partido_nao_vira_do_candidato():
    r = _registros()
    assert r["13633"]["pct_votos"] == "0.52", "o % vem do relatório de ELEITOS"
    assert r["36111"]["pct_votos"] == "", "15.68/0.06 é a fatia do partido — não entra"


def test_federacao_nao_deduz_partido_pelo_numero():
    r = _registros()["13633"]
    assert r["partido"] == "FEDERAÇÃO BRASIL DA ESPERANÇA - FE BRASIL"
    assert r["sigla"] == "", "13 não vira 'PT' por dedução"


def test_partido_isolado_ganha_sigla_so_quando_inequivoca():
    assert _registros()["36111"]["sigla"] == "AGIR"


def test_urna_civil_votos_situacao_e_carimbo():
    r = _registros()["13633"]
    assert (r["nome_urna"], r["votos"], r["situacao"]) == ("LEONARDO GRANDINI", 122158, "Eleito por QP")
    assert r["resultado_em"] == "04/10/2026 - 22:58:07"
    assert r["cargo"] == "DEPUTADO ESTADUAL"


def test_sub_judice_fica_registrado():
    assert _registros()["36111"]["destinacao"] == "Anulado sub judice"


def _c(cargo, numero, urna, nome, sit="Eleito por QP"):
    return {"cargo": cargo, "numero": numero, "nome_urna": urna, "nome": nome, "situacao": sit}


def test_titulo_nao_faz_pai_virar_filho():
    """'Capitão Telhada' (ALESP) não é 'CORONEL TELHADA' (o pai, na Câmara)."""
    cands = [_c("DEPUTADO FEDERAL", "1190", "CORONEL TELHADA", "PAULO ADRIANO LOPES LUCINDA TELHADA")]
    assert eleicoes.situacao_2026("Capitão Telhada", "DEPUTADO ESTADUAL", cands)["status"] == "nao_encontrado"


def test_urna_com_duas_formas_vale_pelas_duas():
    """O filho é "TELHADINHA - CAPITÃO TELHADA" na urna — e é ele, não o pai."""
    cands = [_c("DEPUTADO FEDERAL", "1100", "CORONEL TELHADA", "PAULO ADRIANO LOPES LUCINDA TELHADA"),
             _c("DEPUTADO ESTADUAL", "11190", "TELHADINHA - CAPITÃO TELHADA", "RAFAEL HENRIQUE CANO TELHADA")]
    s = eleicoes.situacao_2026("Capitão Telhada", "DEPUTADO ESTADUAL", cands)
    assert (s["status"], s["numero"]) == ("reeleito", "11190")


def test_jr_vale_junior():
    cands = [_c("DEPUTADO ESTADUAL", "10699", "", "PAULO ALVES CORREA JUNIOR", "Suplente")]
    assert eleicoes.situacao_2026("Paulo Correa Jr", "DEPUTADO ESTADUAL", cands)["status"] == "nao_eleito"


def test_conferido_a_mao_so_casa_com_aquele_numero():
    cands = [_c("DEPUTADO ESTADUAL", "13110", "BARBA", "TEONILIO MONTEIRO DA COSTA"),
             _c("DEPUTADO ESTADUAL", "99999", "TEONILIO BARBA", "OUTRA PESSOA")]
    s = eleicoes.situacao_2026("Teonilio Barba", "DEPUTADO ESTADUAL", cands)
    assert (s["status"], s["numero"]) == ("reeleito", "13110")


def test_igual_vence_parecidos():
    cands = [_c("DEPUTADO ESTADUAL", "1", "RAFAEL SILVA", "RAFAEL DA SILVA"),
             _c("DEPUTADO ESTADUAL", "2", "RAFA", "RAFAEL PEREIRA DA SILVA", "Não eleito")]
    s = eleicoes.situacao_2026("Rafael Silva", "DEPUTADO ESTADUAL", cands)
    assert s["status"] == "reeleito" and s["numero"] == "1"


def test_nome_civil_com_palavras_no_meio():
    cands = [_c("DEPUTADO ESTADUAL", "3", "GIRIBONI", "EDSON DE OLIVEIRA GIRIBONI", "Não eleito")]
    s = eleicoes.situacao_2026("Edson Giriboni", "DEPUTADO ESTADUAL", cands)
    assert s["status"] == "nao_eleito"
    assert "31/jan/2027" in s["rotulo"], "não reeleito segue no mandato até a posse"


def test_apelido_explicito():
    cands = [_c("DEPUTADO ESTADUAL", "4", "", "ELISABETH SAHAO", "Suplente")]
    assert eleicoes.situacao_2026("Beth Sahão", "DEPUTADO ESTADUAL", cands)["status"] == "nao_eleito"


def test_nome_civil_no_meio_nao_e_a_mesma_pessoa():
    """'Ricardo Salles' não é 'JORGE RICARDO SALLES RAMOS' (536 votos)."""
    cands = [_c("DEPUTADO FEDERAL", "7016", "", "JORGE RICARDO SALLES RAMOS", "Não eleito")]
    assert eleicoes.situacao_2026("Ricardo Salles", "DEPUTADO FEDERAL", cands)["status"] == "nao_encontrado"


def test_particula_nao_conta_como_palavra():
    cands = [_c("DEPUTADO FEDERAL", "4422", "", "CARLOS ALBERTO DA CUNHA", "Suplente")]
    assert eleicoes.situacao_2026("Delegado Da Cunha", "DEPUTADO FEDERAL", cands)["status"] == "nao_encontrado"


def test_nao_eleito_em_outro_cargo_so_pelo_civil_fica_a_conferir():
    """Homônimo não eleito em OUTRO cargo: mostra o possível, não afirma."""
    cands = [_c("DEPUTADO ESTADUAL", "44033", "", "MILTON VIEIRA", "Suplente")]
    s = eleicoes.situacao_2026("Milton Vieira", "DEPUTADO FEDERAL", cands)
    assert s["status"] == "a_conferir"
    assert s["possiveis"][0]["numero"] == "44033"


def test_troca_de_casa():
    cands = [_c("SENADOR", "222", "ANDRÉ DO PRADO", "", "Eleito")]
    s = eleicoes.situacao_2026("André do Prado", "DEPUTADO ESTADUAL", cands)
    assert s["status"] == "eleito_outro_cargo" and s["cargo_2027"] == "SENADOR"


def test_resultado_real_bate_com_o_documento():
    """Se o CSV oficial existe, os eleitos têm de bater com o que o TRE-SP diz."""
    if not os.path.isfile(eleicoes.CSV_RESULTADO):
        return
    cands = eleicoes.carregar()
    assert [len(eleicoes.eleitos(cands, c)) for c in eleicoes.CARGOS] == [94, 70, 2]
    assert all(c["nome_urna"] for c in cands if eleicoes.eleito(c))


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
            print(f"ok  {nome}")
    print("resultado TSE (PDF): todos os testes passaram")
