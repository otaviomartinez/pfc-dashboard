"""Loaders do painel Prefeituras — CAPAG, MDE e eleitos (TSE).

Todos são GRACIOSOS: arquivo ausente devolve vazio, nunca exceção — o painel
precisa abrir mesmo sem nenhum dado baixado (é exatamente o estado de hoje, com
os domínios do Tesouro e do TSE bloqueados).

Regra crítica coberta aqui: **ausência nunca vira zero nem nota ruim.**

    python tests/test_prefeituras_loaders.py
"""
import csv
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prefeituras import capag, eleitos, mde  # noqa: E402


def _csv_temp(colunas, linhas):
    d = tempfile.mkdtemp()
    caminho = os.path.join(d, "x.csv")
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas)
        w.writeheader()
        w.writerows(linhas)
    return caminho


# ---- CAPAG ---------------------------------------------------------------- #
def test_capag_sem_arquivo_nao_quebra():
    assert capag.carregar(1999) == {}


def test_capag_ausencia_nao_e_nota_ruim():
    assert capag.rotulo_nota("") == capag.ROTULO_SEM_NOTA
    assert capag.rotulo_nota(None) == "não avaliado"
    assert capag.rotulo_nota("A") == "A"
    # o terceiro estado é o ponto: sem nota NÃO é False
    assert capag.nota_saudavel("A") is True
    assert capag.nota_saudavel("B") is True
    assert capag.nota_saudavel("C") is False
    assert capag.nota_saudavel("D") is False
    assert capag.nota_saudavel("") is None
    assert capag.nota_saudavel("Z") is None      # fora da escala = sem nota


# ---- MDE ------------------------------------------------------------------ #
def test_capag_aceita_gradacoes_mas_nao_nd():
    """O Tesouro publica A+, B+, C-... Descartar isso jogava fora nota REAL:
    Cesário Lange ('B+') e Juquiá ('A+') caíam como "não avaliado".
    'N.D.' (não disponível) continua sendo ausência de verdade."""
    assert capag.normalizar_nota("A+") == "A+"
    assert capag.normalizar_nota("b-") == "B-"
    assert capag.rotulo_nota("B+") == "B+"          # mantém a gradação na tela
    assert capag.nota_saudavel("A+") is True
    assert capag.nota_saudavel("B+") is True
    assert capag.nota_saudavel("C-") is False
    # ausência de verdade continua neutra:
    for ausente in ("N.D.", "", None, "Z", "A++"):
        assert capag.normalizar_nota(ausente) == ""
        assert capag.rotulo_nota(ausente) == capag.ROTULO_SEM_NOTA
        assert capag.nota_saudavel(ausente) is None


def test_mde_sem_arquivo_nao_quebra():
    assert mde.carregar(1999) == {}
    assert mde.exercicio_disponivel(1999) in (None, mde.exercicio_disponivel())


def test_mde_linha_sem_percentual_nao_vira_zero():
    caminho = _csv_temp(
        ["cod_ibge", "municipio", "percentual", "valor_aplicado", "receita_base",
         "exercicio", "periodo", "origem"],
        [{"cod_ibge": "3521002", "municipio": "Iperó", "percentual": "27,5",
          "valor_aplicado": "100", "receita_base": "400", "exercicio": "2025",
          "periodo": "6", "origem": "siconfi"},
         {"cod_ibge": "3545209", "municipio": "Salto", "percentual": "",
          "valor_aplicado": "", "receita_base": "", "exercicio": "2025",
          "periodo": "6", "origem": "siconfi"}])
    # aponta o loader para o arquivo temporário
    original = mde.DIR_DADOS
    try:
        mde.DIR_DADOS = os.path.dirname(caminho)
        os.rename(caminho, os.path.join(mde.DIR_DADOS, "mde_2025.csv"))
        dados = mde.carregar(2025)
        assert "3521002" in dados and dados["3521002"]["percentual"] == 27.5
        assert "3545209" not in dados, "município sem percentual virou linha (deveria sumir)"
    finally:
        mde.DIR_DADOS = original


# ---- Eleitos (TSE) -------------------------------------------------------- #
def test_eleitos_sem_arquivo_nao_quebra():
    assert eleitos.carregar("/nao/existe.csv") == []
    assert eleitos.prefeito_de("Iperó", []) is None
    assert eleitos.partidos_do_municipio("Iperó", []) == set()


def test_eleitos_ordena_prefeito_vice_vereador():
    base = [
        {"municipio": "Iperó", "cargo": "VEREADOR", "nome_urna": "Zeca",
         "nome": "José", "partido": "PT"},
        {"municipio": "Iperó", "cargo": "PREFEITO", "nome_urna": "Ana",
         "nome": "Ana Maria", "partido": "PSDB"},
        {"municipio": "Iperó", "cargo": "VICE-PREFEITO", "nome_urna": "Bia",
         "nome": "Beatriz", "partido": "MDB"},
        {"municipio": "Salto", "cargo": "PREFEITO", "nome_urna": "Outro",
         "nome": "Outro", "partido": "PL"},
    ]
    ordem = [e["cargo"] for e in eleitos.por_municipio("Iperó", base)]
    assert ordem == ["PREFEITO", "VICE-PREFEITO", "VEREADOR"]
    assert eleitos.prefeito_de("Iperó", base)["nome_urna"] == "Ana"
    assert eleitos.partidos_do_municipio("Iperó", base) == {"PSDB", "MDB", "PT"}
    # não vaza município vizinho:
    assert all(e["municipio"] == "Iperó" for e in eleitos.por_municipio("Iperó", base))


def test_eleitos_casa_nome_com_acento():
    base = [{"municipio": "São Roque", "cargo": "PREFEITO", "nome_urna": "X",
             "nome": "X", "partido": "PP"}]
    assert eleitos.prefeito_de("sao roque", base)["nome_urna"] == "X"


if __name__ == "__main__":
    test_capag_sem_arquivo_nao_quebra()
    test_capag_ausencia_nao_e_nota_ruim()
    test_capag_aceita_gradacoes_mas_nao_nd()
    test_mde_sem_arquivo_nao_quebra()
    test_mde_linha_sem_percentual_nao_vira_zero()
    test_eleitos_sem_arquivo_nao_quebra()
    test_eleitos_ordena_prefeito_vice_vereador()
    test_eleitos_casa_nome_com_acento()
    print("OK — loaders de Prefeituras (CAPAG, MDE, eleitos) passaram.")
