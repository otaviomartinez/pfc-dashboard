"""Cadastro de escolas do INEP — src/prefeituras/escolas.py + canais oficiais.

POR QUE ESTA FONTE: o TSE mascara e-mail de candidato (8.329 de 8.329 eleitos de
SP vêm "NÃO DIVULGÁVEL") e o Censo Escolar só traz contagem de matrícula. O
Catálogo de Escolas é um CADASTRO: endereço e telefone reais, por escola — e é o
contato mais acionável, porque o programa do PFC acontece dentro da escola.

    python tests/test_prefeituras_escolas.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prefeituras import escolas  # noqa: E402
from src.prefeituras.config import carregar_municipios  # noqa: E402
from ui.formato import canais_oficiais  # noqa: E402


def test_arquivo_versionado():
    assert os.path.isfile(escolas.CSV_ESCOLAS), f"falta {escolas.CSV_ESCOLAS}"


def test_cobre_os_onze_com_telefone():
    for m in carregar_municipios():
        r = escolas.resumo_municipio(m["nome"])
        assert r["total"] > 0, f"{m['nome']} sem escolas"
        assert r["com_telefone"] > 0, f"{m['nome']} sem nenhum telefone"


def test_so_publicas_por_padrao():
    """O PFC atua na rede pública; listar privada só poluiria."""
    for e in escolas.por_municipio("Sorocaba")[:40]:
        assert e["dependencia"] in ("Municipal", "Estadual", "Federal"), e


def test_municipais_vem_primeiro():
    """É com a prefeitura que o convênio é assinado."""
    lista = escolas.por_municipio("Iperó")
    deps = [e["dependencia"] for e in lista]
    assert deps[0] == "Municipal"
    assert deps == sorted(deps, key=lambda d: {"Municipal": 0, "Estadual": 1}.get(d, 9))


def test_campos_de_contato_preenchidos():
    e = escolas.por_municipio("Iperó")[0]
    assert e["nome"] and e["inep"]
    assert e["endereco"], "endereço vazio"
    assert e["telefone"].startswith("("), e["telefone"]


def test_loader_gracioso():
    assert escolas.por_municipio("Iperó", "/nao/existe.csv") == []
    assert escolas.resumo_municipio("Iperó", "/nao/existe.csv")["total"] == 0
    assert escolas.por_municipio("Cidade Inexistente") == []


def test_casa_nome_com_acento():
    assert escolas.resumo_municipio("ipero")["total"] == \
           escolas.resumo_municipio("Iperó")["total"]


# ---- canais oficiais ------------------------------------------------------ #
def test_canais_nao_inventam_dominio():
    """Inventar o site da prefeitura seria publicar informação falsa."""
    canais = canais_oficiais("Iperó")
    assert canais and len(canais) >= 4
    for c in canais:
        assert c["url"].startswith("https://"), c
        # ou é busca, ou é um domínio oficial conhecido (TCE) — nunca um chute
        assert ("google.com/search" in c["url"]
                or "tce.sp.gov.br" in c["url"]), c["url"]


def test_esic_vem_primeiro():
    """É o canal que a prefeitura é OBRIGADA a responder — vale para os 88."""
    canais = canais_oficiais("Guareí")
    assert "e-SIC" in canais[0]["rotulo"]
    assert "obrigada por lei" in canais[0]["nota"]


def test_canais_vazio_sem_municipio():
    assert canais_oficiais("") == []
    assert canais_oficiais(None) == []


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
    print("OK — escolas do INEP (contato por município) e canais oficiais passaram.")
