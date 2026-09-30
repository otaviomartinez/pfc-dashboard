"""Radar de Parcerias — base curada + camada pura (PASSO 1).

    python tests/test_parcerias.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parcerias import (  # noqa: E402
    carregar_parcerias,
    filtrar_parcerias,
    gancho_parceria,
    parceiros_por_modulo,
    parse_modulos,
    status_disponiveis,
    tipos_disponiveis,
)


def test_seed_carrega_com_campos():
    rows = carregar_parcerias()
    assert len(rows) >= 10, "esperava a lista-semente curada"
    for r in rows:
        assert r.get("nome"), "parceiro sem nome"
        assert r.get("modulos_lista"), f"{r['nome']} sem módulo"
        # regra de ouro: base é de candidatos, nunca parceria confirmada
        assert "ativa" not in str(r.get("status", "")).lower()


def test_parse_modulos():
    assert parse_modulos("2;3;4") == [2, 3, 4]
    assert parse_modulos("1") == [1]
    assert parse_modulos("3;3;2") == [2, 3]     # ordena e dedup
    assert parse_modulos("") == []
    assert parse_modulos("1, 2") == [1, 2]       # tolera vírgula/espaço
    assert parse_modulos("abc") == []            # não-numérico não quebra


def test_filtra_por_modulo():
    rows = carregar_parcerias()
    m1 = filtrar_parcerias(rows, modulo=1)
    assert m1, "esperava parceiros do módulo 1"
    assert all(1 in r["modulos_lista"] for r in m1)
    m4 = filtrar_parcerias(rows, modulo=4)
    assert all(4 in r["modulos_lista"] for r in m4)


def test_filtra_por_tipo_status_e_busca():
    rows = carregar_parcerias()
    empresas = filtrar_parcerias(rows, tipo="empresa")
    assert empresas and all(r["tipo"] == "empresa" for r in empresas)
    # busca por nome (ignora acento/caixa)
    achou = filtrar_parcerias(rows, busca="unicef")
    assert any("UNICEF" in r["nome"] for r in achou)
    # 'Todos' é neutro
    assert len(filtrar_parcerias(rows, modulo="Todos", tipo="Todos", status="Todos")) == len(rows)


def test_por_modulo_agrupa():
    rows = carregar_parcerias()
    grupos = parceiros_por_modulo(rows)
    assert set(grupos.keys()) >= {1, 2, 3, 4}
    # Faber-Castell (material) tem de cair no módulo 1
    nomes_m1 = {r["nome"] for r in grupos[1]}
    assert "Faber-Castell" in nomes_m1


def test_filtros_listam_valores():
    rows = carregar_parcerias()
    assert "empresa" in tipos_disponiveis(rows)
    assert any("abordar" in s.lower() for s in status_disponiveis(rows))


def test_preparar_normaliza_linhas_do_sheets():
    from src.parcerias import preparar
    out = preparar([{"nome": "X", "modulos": "2;3"}, {"nome": "Y", "modulos": ""}])
    assert out[0]["modulos_lista"] == [2, 3]
    assert out[1]["modulos_lista"] == []


def test_dados_parcerias_constantes_e_validacao():
    # P4: constantes + rejeições que acontecem ANTES de qualquer conexão/escrita.
    # NÃO chama caminho que grava (este ambiente pode estar conectado ao Sheets
    # de produção — teste jamais deve escrever lá).
    from src import dados
    assert dados.PARCERIA_STATUS[0] == "a abordar"
    assert dados.HEADERS_PARCERIAS[0] == "ID"
    assert dados.atualizar_status_parceria("", "em contato")["sucesso"] is False   # id vazio
    r = dados.atualizar_status_parceria("1", "banana")                              # status inválido
    assert r["sucesso"] is False and "inválido" in r["mensagem"].lower()


def test_gancho_honesto():
    # usa o campo curado quando existe
    r = {"como_abordar": "Buscar doação de cadernos", "foco": "material escolar", "tipo": "empresa"}
    assert gancho_parceria(r) == "Buscar doação de cadernos"
    # sem curado, compõe do foco/tipo — nunca inventa contato
    r2 = {"como_abordar": "", "foco": "direito da criança", "tipo": "fundação"}
    g = gancho_parceria(r2)
    assert "direito da criança" in g and "fundação" in g
    # vazio total → mensagem honesta de candidato
    assert "abordar" in gancho_parceria({}).lower()


if __name__ == "__main__":
    test_seed_carrega_com_campos()
    test_parse_modulos()
    test_filtra_por_modulo()
    test_filtra_por_tipo_status_e_busca()
    test_por_modulo_agrupa()
    test_filtros_listam_valores()
    test_preparar_normaliza_linhas_do_sheets()
    test_dados_parcerias_constantes_e_validacao()
    test_gancho_honesto()
    print("OK — Radar de Parcerias PASSO 1: base curada + camada pura passou.")
