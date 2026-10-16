"""Score de senador: território (TSE) + histórico + nota do Fábio, sem inventar.

    python tests/test_score_senador.py
"""
import datetime
import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from src import legislatura2027 as L  # noqa: E402
from src import score_senador as S  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "imp_votacao", os.path.join(RAIZ, "scripts", "importar_votacao_municipio_2026.py"))
imp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(imp)

# território de brinquedo: Sorocaba conta inteira (PFC), Votorantim pela metade (vizinha)
PESOS = {"sorocaba": 1.0, "votorantim": 0.5}
TOTAIS = {"sorocaba": 1000, "votorantim": 400, "sao paulo": 8600}   # território = 1.200/10.000 ponderado


def test_sem_nada_e_sem_dado_nunca_zero():
    s = S.calcular(None, None)
    assert s["score"] is None and s["status"] == "sem_dado" and s["medido"] == 0
    assert len(s["falta"]) == 2 and S.rotulo_score(s) == "sem dado"


def test_so_historico_ja_vira_numero_parcial():
    """André hoje: só o cargo anterior -> 17, com o rótulo dizendo o que foi medido."""
    s = S.calcular(None, 17.1, "da ALESP")
    assert (s["score"], s["status"], s["medido"]) == (17, "parcial", 50)
    assert S.rotulo_score(s) == "17 (parcial: só histórico no cargo anterior)"


def test_parte_sem_dado_nao_puxa_para_baixo():
    terr = {"razao": 1.0, "fatia_cand_pct": 12.0, "fatia_geral_pct": 12.0, "votos_pfc": 0,
            "cidades_top": []}
    so_terr = S.calcular(terr, None)               # 25 de 50 medidos
    assert (so_terr["score"], so_terr["status"]) == (50, "parcial")


def test_nao_existe_mais_nota_manual():
    assert set(S.PESOS) == {"territorio", "historico"} and sum(S.PESOS.values()) == 100


def test_completo_soma_os_dois():
    terr = {"razao": 2.0, "fatia_cand_pct": 24.0, "fatia_geral_pct": 12.0, "votos_pfc": 0,
            "cidades_top": []}
    s = S.calcular(terr, 100)
    assert (s["score"], s["status"], s["medido"]) == (100, "completo", 100)
    assert S.rotulo_score(s) == "100"
    meio = S.calcular(dict(terr, razao=1.0), 50)   # 25 + 25
    assert meio["score"] == 50


def test_territorio_tem_teto_no_dobro():
    assert S.pontos_territorio(1.0) == 25 and S.pontos_territorio(2.0) == 50
    assert S.pontos_territorio(5.0) == 50 and S.pontos_territorio(-1) == 0


def test_indice_territorial_ponderado():
    # candidato: 300 em Sorocaba, 100 em Votorantim, 600 em SP = 1.000 votos
    t = S.indice_territorial({"sorocaba": 300, "votorantim": 100, "sao paulo": 600}, TOTAIS, PESOS)
    # dele: (300 + 50) / 1000 = 35%; de todos: (1000 + 200) / 10000 = 12%
    assert round(t["fatia_cand_pct"], 1) == 35.0 and round(t["fatia_geral_pct"], 1) == 12.0
    assert round(t["razao"], 2) == 2.92
    assert t["cidades_top"] == [("sorocaba", 300)], "vizinha não conta como cidade do PFC"


def test_indice_sem_dado():
    assert S.indice_territorial({}, TOTAIS, PESOS) is None
    assert S.indice_territorial({"sorocaba": 1}, TOTAIS, {}) is None


def test_nome_de_municipio_tse_x_ibge():
    assert S.norm_municipio("SANTA BÁRBARA D'OESTE") == S.norm_municipio("Santa Bárbara d'Oeste")
    assert S.norm_municipio("BIRITIBA-MIRIM") == S.norm_municipio("Biritiba Mirim")


def _linha(uf, cargo, mun, num, votos, turno="1", validos=None, urna="FULANO"):
    r = {"SG_UF": uf, "DS_CARGO": cargo, "NM_MUNICIPIO": mun, "CD_MUNICIPIO": "1",
         "NR_CANDIDATO": num, "NM_URNA_CANDIDATO": urna, "NR_TURNO": turno,
         "QT_VOTOS_NOMINAIS": str(votos)}
    if validos is not None:
        r["QT_VOTOS_NOMINAIS_VALIDOS"] = str(validos)
    return r


def test_importador_soma_zonas_e_filtra():
    linhas = [_linha("SP", "SENADOR", "SOROCABA", "111", 100),
              _linha("SP", "SENADOR", "SOROCABA", "111", 50),          # outra zona
              _linha("SP", "DEPUTADO FEDERAL", "SOROCABA", "1111", 999),
              _linha("RJ", "SENADOR", "NITERÓI", "111", 999),
              _linha("SP", "SENADOR", "SOROCABA", "222", 80, validos=70)]
    r = {(x["municipio"], x["numero"]): x["votos"] for x in imp.extrair(linhas)}
    assert r == {("SOROCABA", "111"): 150, ("SOROCABA", "222"): 70}, "válidos têm preferência"


def test_legislatura_usa_o_score_no_senado():
    cands = [{"cargo": "SENADOR", "numero": "111", "nome_urna": "FULANO SENADOR", "nome": "",
              "votos": "1000", "situacao": "Eleito", "resultado_em": "x"}]
    votacao = {"por_candidato": {"111": {"nome_urna": "FULANO SENADOR",
                                         "votos": {"sorocaba": 300, "votorantim": 100, "sao paulo": 600}}},
               "totais": TOTAIS}
    d = L.montar(cands, [], [], [], [], hoje=datetime.date(2026, 10, 16), votacao_senado=votacao,
                 pesos_territorio=PESOS)
    s = d["casas"]["Senado"][0]["score_senador"]
    # território 50 (razão 2,92 > teto), sem histórico: 50 de 50 medidos -> 100 parcial
    assert (s["score"], s["status"], s["medido"]) == (100, "parcial", 50)
    d2 = L.montar(cands, [], [], [], [], hoje=datetime.date(2026, 10, 16))
    assert d2["casas"]["Senado"][0]["score_senador"]["status"] == "sem_dado"
    assert "score_senador" not in (d2["casas"]["ALESP"] or [{}])[0] if d2["casas"]["ALESP"] else True


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
            print(f"ok  {nome}")
    print("score de senador: todos os testes passaram")
