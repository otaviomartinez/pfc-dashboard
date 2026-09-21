"""Escolha da aba da planilha CAPAG — scripts/importar_capag.py.

Regressão de um erro caro: a pasta do Tesouro tem várias abas com "CAPAG" no
nome. A 'CAPAG Ano Base 2025' é a de INDICADORES (Dívida Consolidada, DPC-2…),
SEM lista de municípios; a lista está na 'Prévia da CAPAG'. Escolher a aba pelo
NOME pegou a errada e zerou a coleta.

Regra: não escolher por nome — VALIDAR. Só serve a aba cujo cabeçalho tem
coluna de código de município E coluna de nota.

Precisa de pandas + openpyxl (openpyxl NÃO está no requirements.txt do app; ele
é instalado só no runner do GitHub). Sem ele, o teste se declara pulado.

    python tests/test_prefeituras_capag_aba.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _planilha_falsa():
    """Imita as DUAS abas reais vistas no log do Actions."""
    import pandas as pd
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        # a que enganou: indicadores, sem municípios
        pd.DataFrame([["", "", "Coluna", "Dívida Consolidada", "Receita Corrente Líquida"],
                      ["", "", 129, 130, "DPC-2"]]).to_excel(
            w, sheet_name="CAPAG Ano Base 2025", header=False, index=False)
        # a boa: cabeçalho na linha 2, colunas reais
        pd.DataFrame([
            ["Relatório CAPAG", "", "", "", "", "", ""],
            ["", "", "", "", "", "", ""],
            ["Código Município Completo", "Nome_Município", "UF", "CAPAG",
             "Indicador 1", "Nota 1", "Nota 2"],
            [3510302, "Capela do Alto", "SP", "B", 0.04, "A", "C"],
            [3521002, "Iperó", "SP", "A", 0.03, "A", "A"],
            [1100015, "Alta Floresta D'Oeste", "RO", "C", 0.9, "C", "C"],
        ]).to_excel(w, sheet_name="Prévia da CAPAG", header=False, index=False)
    return buf.getvalue()


def test_escolhe_a_aba_com_municipios_e_ignora_a_de_indicadores():
    import scripts.importar_capag as ic
    linhas = ic._linhas_da_planilha(_planilha_falsa(), "XLSX")
    assert linhas, "nenhuma linha lida — pegou a aba errada"
    colunas = set(linhas[0].keys())
    assert "Código Município Completo" in colunas, colunas
    assert "Dívida Consolidada" not in colunas, "pegou a aba de indicadores"


def test_extrai_codigo_e_nota_dos_municipios_do_pfc():
    import scripts.importar_capag as ic
    linhas = ic._linhas_da_planilha(_planilha_falsa(), "XLSX")
    alvos = {m["cod_ibge"]: m["nome"] for m in ic.carregar_municipios()}
    achados = {}
    for linha in linhas:
        cod = ic._codigo(linha)
        if cod is None:
            continue
        cod = str(cod).split(".")[0].strip()
        if cod in alvos:
            achados[alvos[cod]] = str(ic._campo(linha, "capag") or "").strip()
    assert achados == {"Capela do Alto": "B", "Iperó": "A"}, achados
    # município de outro estado não entra
    assert "Alta Floresta D'Oeste" not in achados


if __name__ == "__main__":
    try:
        import openpyxl  # noqa: F401
        import pandas  # noqa: F401
    except ImportError:
        print("OK — (pulado: precisa de pandas+openpyxl, que só existem no runner)")
        raise SystemExit(0)
    test_escolhe_a_aba_com_municipios_e_ignora_a_de_indicadores()
    test_extrai_codigo_e_nota_dos_municipios_do_pfc()
    print("OK — seleção validada da aba do CAPAG (ignora a de indicadores) passou.")
