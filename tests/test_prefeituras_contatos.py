"""Contato institucional da prefeitura — src/prefeituras/contatos.py.

POR QUE EXISTE: o dossiê tinha só LINKS DE BUSCA; o usuário pediu o contato
pronto na tela. A fonte automática é o cadastro de CNPJ da Receita (e-mail,
telefone e endereço que a própria prefeitura mantém). Estes testes travam as
três garantias que importam: o loader nunca derruba o painel quando o arquivo
não existe, linha sem contato nenhum não entra (regra 5c: ausência é ausência,
não um campo vazio fingindo dado), e o dossiê renderiza o bloco sozinho.

    python tests/test_prefeituras_contatos.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prefeituras import contatos  # noqa: E402

CABECALHO = "cod_ibge,municipio,cnpj,razao_social,email,telefone,endereco,cep,fonte\n"


def _csv(corpo: str) -> str:
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                    encoding="utf-8", newline="")
    f.write(CABECALHO + corpo)
    f.close()
    return f.name


def test_arquivo_ausente_nao_quebra():
    """Antes da primeira rodada do workflow o CSV não existe — e está tudo bem."""
    assert contatos.carregar("/caminho/que/nao/existe.csv") == {}
    assert contatos.por_municipio("Sorocaba", "/caminho/que/nao/existe.csv") is None


def test_linha_sem_email_e_sem_telefone_e_descartada():
    caminho = _csv(
        "3552205,Sorocaba,46634044000174,MUNICIPIO DE SOROCABA,gab@sorocaba.sp.gov.br,1532345000,Rua X 1,18000-000,receita-cnpj\n"
        "3520509,Iperó,,PREFEITURA DE IPERO,,,Rua Y 2,18560-000,receita-cnpj\n")
    reg = contatos.carregar(caminho)
    os.unlink(caminho)
    assert "3552205" in reg
    assert "3520509" not in reg, "linha sem e-mail E sem telefone não serve para contato"


def test_so_telefone_basta():
    """Telefone sem e-mail ainda é contato acionável."""
    caminho = _csv("3520509,Iperó,11111111111111,PREFEITURA DE IPERO,,1532661000,Rua Y 2,18560-000,receita-cnpj\n")
    reg = contatos.carregar(caminho)
    os.unlink(caminho)
    assert reg["3520509"]["telefone"] == "1532661000"
    assert reg["3520509"]["email"] == ""


def test_busca_por_codigo_ibge():
    """O dossiê tenta primeiro pelo código: casamento exato, sem grafia."""
    caminho = _csv("3520509,Ipero,11111111111111,PREFEITURA DE IPERO,pref@ipero.sp.gov.br,,Rua Y,18560-000,receita-cnpj\n")
    assert contatos.por_codigo("3520509", caminho)["email"] == "pref@ipero.sp.gov.br"
    assert contatos.por_codigo(3520509, caminho) is not None, "aceita int"
    assert contatos.por_codigo("9999999", caminho) is None
    assert contatos.por_codigo("", caminho) is None
    os.unlink(caminho)


def test_busca_por_nome_ignora_acento_e_caixa():
    caminho = _csv("3520509,Iperó,11111111111111,PREFEITURA DE IPERO,pref@ipero.sp.gov.br,,Rua Y,18560-000,receita-cnpj\n")
    for nome in ("Iperó", "ipero", "IPERO", " Iperó "):
        assert contatos.por_municipio(nome, caminho), nome
    assert contatos.por_municipio("Votorantim", caminho) is None
    os.unlink(caminho)


def test_importador_nunca_grava_csv_vazio():
    """CSV vazio apagaria o contato que já estava funcionando."""
    fonte = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "scripts", "importar_contatos_prefeitura.py"),
                 encoding="utf-8").read()
    assert "if not linhas:" in fonte
    assert fonte.index("if not linhas:") < fonte.index("os.makedirs")


def test_dossies_mostram_o_contato_automatico():
    """Os DOIS dossiês (nossos municípios e expansão) trazem o bloco pronto."""
    app = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "app.py"), encoding="utf-8").read()
    assert app.count("<h4>Contato oficial da prefeitura</h4>") == 2
    assert app.count("from src.prefeituras import contatos as _contatos") == 2


def test_workflow_coleta_os_contatos():
    wf = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           ".github", "workflows", "prefeituras.yml"),
              encoding="utf-8").read()
    assert "importar_contatos_prefeitura.py" in wf
    assert "continue-on-error: true" in wf


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
            print(f"ok  {nome}")
    print("todos os testes de contatos passaram")
