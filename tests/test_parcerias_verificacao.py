"""Verificação do canal de doação/patrocínio dos parceiros.

O PROBLEMA QUE ISTO RESOLVE: os 16 da base-semente vieram com
`fonte = "curadoria inicial (a confirmar)"` — são hipóteses montadas de
conhecimento geral, não levantamento. Diferente dos outros três radares, cujo
dado vem de fonte oficial rastreável (TCE, Tesouro, TSE, ALESP).

O QUE ESTES TESTES TRAVAM: que a verificação nunca vire afirmação maior do que
é. "Canal encontrado" = existe a página. Nunca "tem programa aberto".

    python tests/test_parcerias_verificacao.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import parcerias  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CABECALHO = ("nome,site,status,tipo_canal,direcao,canal_url,canal_titulo,"
             "evidencia,verificado_em\n")


def _csv(corpo: str) -> str:
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                    encoding="utf-8", newline="")
    f.write(CABECALHO + corpo)
    f.close()
    return f.name


def _verificador():
    import importlib.util
    caminho = os.path.join(RAIZ, "scripts", "verificar_parcerias.py")
    spec = importlib.util.spec_from_file_location("_verif", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sem_arquivo_a_tela_diz_que_nao_verificou():
    """Calar seria pior: deixaria a curadoria parecer confirmada."""
    assert parcerias.carregar_verificacao("/nao/existe.csv") == {}
    assert parcerias.rotulo_verificacao(None) == "Canal não verificado ainda."


def test_canal_encontrado_nao_vira_programa_aberto():
    """A frase da tela é obrigada a ressalvar. Uma página institucional não
    prova que há chamada aberta — é o mesmo cuidado da regra 3."""
    frase = parcerias.rotulo_verificacao(
        {"status": "canal encontrado", "tipo_canal": "edital",
         "direcao": "recebe projetos", "verificado_em": "2026-09-30"})
    assert "não** significa programa aberto" in frase
    assert "2026-09-30" in frase, "a tela precisa dizer QUANDO foi visto"


def test_doacao_ao_parceiro_nao_e_apresentada_como_achado_bom():
    """ERRO DA 1ª VERSÃO: "Como doar" foi classificado como canal encontrado.
    Mas é o público doando PARA o parceiro — direção oposta à do PFC, que quer
    RECEBER. A tela é obrigada a dizer isso, senão vira achado falso."""
    frase = parcerias.rotulo_verificacao(
        {"status": "canal encontrado", "tipo_canal": "capta doação",
         "direcao": "direção inversa", "verificado_em": "2026-09-30"})
    assert "não canal para receber projeto" in frase
    assert "doação ao próprio parceiro" in frase


def test_pagina_institucional_nao_vira_canal_de_submissao():
    frase = parcerias.rotulo_verificacao(
        {"status": "canal encontrado", "tipo_canal": "institucional",
         "direcao": "indefinido", "verificado_em": "2026-09-30"})
    assert "Não é canal" in frase


def test_rede_social_nunca_e_canal():
    """O verificador apontou o Instituto Alana para o Facebook, porque o nome
    dele contém "instituto". Perfil não é canal de captação."""
    v = _verificador()
    for url in ("https://pt-br.facebook.com/institutoalana/",
                "https://instagram.com/fundacaox", "https://linkedin.com/company/y"):
        assert v._classificar(url) is None, url
    assert v._classificar("Instituto Alana") is None, \
        "o próprio nome do parceiro não pode virar indício de canal"


def test_cada_falha_tem_frase_propria():
    """Site fora do ar, sem site e nada encontrado são três coisas diferentes
    (regra 5c: sem dado ≠ dado ruim, e cada ausência tem seu rótulo)."""
    frases = {parcerias.rotulo_verificacao({"status": s})
              for s in ("não encontrado", "site não respondeu", "sem site na base")}
    assert len(frases) == 3, f"rótulos colididos: {frases}"


def test_casa_por_nome_normalizado():
    caminho = _csv("Faber-Castell,https://s.com,canal encontrado,edital,"
                   "recebe projetos,https://s.com/e,Editais,Trecho,2026-09-30\n")
    regs = parcerias.carregar_verificacao(caminho)
    assert parcerias.verificacao_de({"nome": "FABER-CASTELL"}, regs)
    assert parcerias.verificacao_de({"nome": "Outra"}, regs) is None
    os.unlink(caminho)


def test_classificador_prioriza_edital_e_ignora_ruido():
    v = _verificador()
    assert v._classificar("Editais abertos")[:2] == ("edital", "recebe projetos")
    assert v._classificar("Apoio a projetos")[1] == "recebe projetos"
    assert v._classificar("Como doar")[1] == "direção inversa"
    assert v._classificar("Sustentabilidade")[0] == "institucional"
    for ruido in ("Trabalhe conosco", "Carrinho de compras", "Política de privacidade"):
        assert v._classificar(ruido) is None, ruido
    assert v._classificar("Home") is None


def test_verificador_nunca_inventa_canal():
    fonte = open(os.path.join(RAIZ, "scripts", "verificar_parcerias.py"),
                 encoding="utf-8").read()
    assert '"status": "não encontrado"' in fonte, "o padrão tem de ser ausência"
    assert "site não respondeu" in fonte
    assert "NÃO PODE" in fonte, "o script precisa dizer o que não pode afirmar"


def test_dossie_mostra_o_bloco_inclusive_quando_nao_achou():
    app = open(os.path.join(RAIZ, "app.py"), encoding="utf-8").read()
    assert "Canal de doação/patrocínio" in app
    assert "rotulo_verificacao(reg)" in app, "a ressalva tem de aparecer sempre"


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
            print(f"ok  {nome}")
    print("verificação de parcerias: todos os testes passaram")
