"""Mapa da cota parlamentar: o que é presença, o que é escritório, o que fica fora.

    python tests/test_cota_parlamentar.py
"""
import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from src import cota_parlamentar as C  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "imp_cota", os.path.join(RAIZ, "scripts", "importar_cota_parlamentar.py"))
imp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(imp)


def _nota(uf="SP", desc="COMBUSTÍVEIS E LUBRIFICANTES.", cnpj="12.345.678/0001-90", nome="FULANO",
          data="2026-08-14T00:00:00", valor="150,00", did="111"):
    return {"﻿txNomeParlamentar": nome, "sgUF": uf, "sgPartido": "PL", "nuDeputadoId": did,
            "txtDescricao": desc, "txtCNPJCPF": cnpj, "datEmissao": data, "vlrLiquido": valor}


def test_categorias():
    assert imp.grupo_da_categoria("COMBUSTÍVEIS E LUBRIFICANTES.") == "presenca"
    assert imp.grupo_da_categoria("FORNECIMENTO DE ALIMENTAÇÃO DO PARLAMENTAR") == "presenca"
    assert imp.grupo_da_categoria("HOSPEDAGEM ,EXCETO DO PARLAMENTAR NO DISTRITO FEDERAL.") == "presenca"
    assert imp.grupo_da_categoria("MANUTENÇÃO DE ESCRITÓRIO DE APOIO À ATIVIDADE PARLAMENTAR") == "escritorio"
    assert imp.grupo_da_categoria("PASSAGEM AÉREA - SIGEPA") is None
    assert imp.grupo_da_categoria("DIVULGAÇÃO DA ATIVIDADE PARLAMENTAR.") is None


def test_extrai_so_sp_com_cnpj_e_nunca_cpf():
    linhas = [_nota(), _nota(uf="RJ"), _nota(cnpj="123.456.789-01"),
              _nota(desc="PASSAGEM AÉREA - SIGEPA")]
    r = imp.extrair(linhas)
    assert len(r) == 1
    assert r[0]["cnpj"] == "12345678000190" and r[0]["data"] == "2026-08-14" and r[0]["valor"] == 150.0
    assert r[0]["deputado"] == "FULANO", "o BOM no nome da 1ª coluna não pode quebrar"


def test_coluna_faltando_avisa():
    try:
        imp.extrair([{"outra": "x"}])
    except ValueError as e:
        assert "colunas não encontradas" in str(e)
    else:
        raise AssertionError("deveria recusar arquivo sem as colunas")


def test_agrega_por_cidade_e_deixa_de_fora_cnpj_sem_cidade():
    notas = imp.extrair([_nota(data="2026-03-01"), _nota(data="2026-08-14"),
                         _nota(cnpj="98765432000110")])
    cidade = {"12345678000190": {"municipio": "SOROCABA", "uf": "SP"}}
    r = imp.agregar(notas, cidade)
    assert len(r) == 1
    assert (r[0]["municipio"], r[0]["notas"], r[0]["primeira_data"], r[0]["ultima_data"]) == \
        ("SOROCABA", 2, "2026-03-01", "2026-08-14")


def _linha(dep, mun, n, grupo="presenca", ultima="2026-08-01", did=None, uf="SP"):
    return {"deputado_id": did or dep, "deputado": dep, "partido": "X", "municipio": mun, "uf": uf,
            "grupo": grupo, "notas": str(n), "ultima_data": ultima}


PFC, VIZ = {"sorocaba", "salto"}, {"votorantim"}


def test_classes_e_ordem():
    linhas = [_linha("Ana", "SOROCABA", 4), _linha("Ana", "SÃO PAULO", 30),
              _linha("Bia", "VOTORANTIM", 3), _linha("Caio", "SALTO", 1),
              _linha("Duda", "SÃO PAULO", 50)]
    m = C.montar_mapa(linhas, PFC, VIZ)
    assert [(d["deputado"], d["classe"]) for d in m] == [
        ("Ana", "frequenta_pfc"), ("Bia", "frequenta_vizinhas"), ("Caio", "passa_regiao"),
        ("Duda", "sem_registro")]
    assert m[0]["notas_sp"] == 34 and m[0]["cidades_pfc"] == [("Sorocaba", 4, "2026-08-01")]


def test_vizinha_conta_na_ordem_com_o_fator_de_vizinhanca():
    """Muitas notas em Sorocaba (vizinha) passam à frente de poucas numa cidade do PFC."""
    m = C.montar_mapa([_linha("Lippi", "SALTO", 3), _linha("Lippi", "VOTORANTIM", 150),
                       _linha("Rosas", "SOROCABA", 38)], {"salto", "sorocaba"}, {"votorantim"})
    assert [d["deputado"] for d in m] == ["Lippi", "Rosas"]
    assert m[0]["presenca"] == 3 + 0.45 * 150


def test_escritorio_nao_conta_como_presenca():
    m = C.montar_mapa([_linha("Ana", "SOROCABA", 10, grupo="escritorio")], PFC, VIZ)
    assert m[0]["classe"] == "sem_registro" and m[0]["escritorio"] == [("Sorocaba", 10)]


def test_fora_de_sp_nao_entra():
    m = C.montar_mapa([_linha("Ana", "SOROCABA", 5, uf="MG")], PFC, VIZ)
    assert m[0]["notas_pfc"] == 0


def test_visao_por_cidade():
    m = C.montar_mapa([_linha("Ana", "SOROCABA", 4, ultima="2026-07-01"),
                       _linha("Bia", "SOROCABA", 6, ultima="2026-09-01"),
                       _linha("Bia", "VOTORANTIM", 2)], PFC, VIZ)
    c = C.por_cidade(m)
    assert c[0]["cidade"] == "Sorocaba" and c[0]["total_notas"] == 10
    assert [x[0] for x in c[0]["deputados"]] == ["Bia", "Ana"]
    assert len(C.por_cidade(m, incluir_vizinhas=True)) == 2


def test_territorio_padrao_e_o_do_ranking():
    pfc, viz = C.territorio_padrao()
    assert "mirassol" in pfc and not (pfc & viz)


def test_cidade_com_o_nome_oficial_do_ibge():
    """O cadastro de CNPJ grava 'SAO ROQUE'; a tela mostra 'São Roque'."""
    m = C.montar_mapa([_linha("Ana", "SAO ROQUE", 3), _linha("Ana", "CAPELA DO ALTO", 1)],
                      {"sao roque", "capela do alto"}, set())
    assert [c for c, _, _ in m[0]["cidades_pfc"]] == ["São Roque", "Capela do Alto"]
    assert m[0]["notas_regiao"] == 4


def test_data_br():
    assert C.data_br("2026-08-14") == "14/08/2026" and C.data_br("") == ""


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
            print(f"ok  {nome}")
    print("cota parlamentar: todos os testes passaram")
