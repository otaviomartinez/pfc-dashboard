"""Eleição 2026: importador do TSE + cruzamento com quem está HOJE no cargo.

O arquivo do TSE é o mesmo formato do de 2024 (que já funcionou aqui): latin-1,
';', colunas DS_CARGO / DS_SIT_TOT_TURNO / NM_URNA_CANDIDATO. Estes testes usam
um zip montado nesse formato, porque o resultado real ainda precisa ser baixado
no navegador.

    python tests/test_eleicao_2026.py
"""
import csv
import io
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import eleicoes  # noqa: E402
import importlib.util  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "imp_eleicao", os.path.join(RAIZ, "scripts", "importar_eleicao_2026.py"))
imp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(imp)

CAMPOS = ["SG_UF", "DS_CARGO", "SQ_CANDIDATO", "NR_CANDIDATO", "NM_CANDIDATO",
          "NM_URNA_CANDIDATO", "SG_PARTIDO", "DS_SIT_TOT_TURNO"]
LINHAS = [
    ["SP", "SENADOR", "1", "221", "ANDRE ANTONIO DO PRADO", "ANDRÉ DO PRADO", "PL", "ELEITO"],
    ["SP", "DEPUTADO ESTADUAL", "2", "22123", "DANILO BALAS SILVA", "DANILO BALAS", "PL", "ELEITO POR QP"],
    ["SP", "DEPUTADO ESTADUAL", "3", "13123", "MARIA DA SILVA", "PROFESSORA MARIA", "PT", "SUPLENTE"],
    ["SP", "DEPUTADO ESTADUAL", "4", "50123", "JOAO NOVO SOUZA", "JOÃO NOVO", "PSOL", "ELEITO POR MÉDIA"],
    ["SP", "DEPUTADO FEDERAL", "5", "1234", "CARLOS LIMA", "CARLOS LIMA", "PSD", "ELEITO"],
    ["RJ", "DEPUTADO ESTADUAL", "6", "1", "FORA DE SP", "FORA", "PL", "ELEITO"],
    ["SP", "GOVERNADOR", "7", "10", "ALGUEM", "ALGUEM", "X", "2º TURNO"],
]


def _zip(linhas, situacao_vazia=False):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_ALL)
    w.writerow(CAMPOS)
    for l in linhas:
        l = list(l)
        if situacao_vazia:
            l[-1] = "#NULO#"
        w.writerow(l)
    caminho = tempfile.mktemp(suffix=".zip")
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("consulta_cand_2026_SP.csv", buf.getvalue().encode("latin-1"))
    return caminho


def _candidatos():
    return imp.extrair(imp._linhas_do_zip(_zip(LINHAS)))


def test_so_sp_e_so_os_tres_cargos():
    cands = _candidatos()
    assert {c["cargo"] for c in cands} == {"SENADOR", "DEPUTADO ESTADUAL", "DEPUTADO FEDERAL"}
    assert all(c["nome"] != "FORA DE SP" for c in cands), "RJ não entra"
    assert not any("CPF" in k.upper() or "MAIL" in k.upper() for k in cands[0]), \
        "só o mínimo público"


def test_acentos_do_tse_sobrevivem_ao_latin1():
    nomes = {c["nome_urna"] for c in _candidatos()}
    assert "ANDRÉ DO PRADO" in nomes and "JOÃO NOVO" in nomes


def test_arquivo_sem_resultado_e_recusado():
    """O TSE atualiza o arquivo em lotes. Gravar antes da totalização daria uma
    lista em que ninguém foi eleito."""
    cands = imp.extrair(imp._linhas_do_zip(_zip(LINHAS, situacao_vazia=True)))
    assert cands and not imp.tem_resultado(cands)
    assert imp.tem_resultado(_candidatos())


def test_deputado_estadual_que_virou_senador():
    """Caso real: André do Prado está na nossa lista da ALESP e foi eleito
    senador. O painel tem de dizer isso — sem tirá-lo da lista antes de 1º/fev."""
    s = eleicoes.situacao_2026("André do Prado", "DEPUTADO ESTADUAL", _candidatos())
    assert s["status"] == "eleito_outro_cargo" and s["cargo_2027"] == "SENADOR"


def test_nome_parlamentar_diferente_da_urna():
    """A ALESP chama de "Agente Federal Danilo Balas" quem a urna chama de
    "DANILO BALAS" — o mesmo caso que já existia no CRM."""
    s = eleicoes.situacao_2026("Agente Federal Danilo Balas", "DEPUTADO ESTADUAL", _candidatos())
    assert s["status"] == "reeleito"


def test_suplente_e_nao_reeleito_mas_segue_no_mandato():
    s = eleicoes.situacao_2026("Professora Maria", "DEPUTADO ESTADUAL", _candidatos())
    assert s["status"] == "nao_eleito"
    assert "31/jan/2027" in s["rotulo"], "a tela tem de dizer até quando ele manda"


def test_ausente_nao_vira_nao_concorreu():
    """Não achar o nome pode ser só grafia diferente — nunca afirmar que não
    concorreu."""
    s = eleicoes.situacao_2026("Fulano Inexistente", "DEPUTADO ESTADUAL", _candidatos())
    assert s["status"] == "nao_encontrado"
    assert "não concorreu" not in s["rotulo"].lower()


def test_uma_palavra_so_e_ambigua_demais():
    """'Carlos' não pode casar com 'CARLOS LIMA' — seria afirmar sem base."""
    s = eleicoes.situacao_2026("Carlos", "DEPUTADO FEDERAL", _candidatos())
    assert s["status"] == "nao_encontrado"


def test_dois_compativeis_vira_a_conferir():
    cands = _candidatos() + [{"sq_candidato": "9", "cargo": "DEPUTADO ESTADUAL",
                              "nome_urna": "DANILO BALAS", "nome": "DANILO BALAS JUNIOR",
                              "partido": "X", "situacao": "SUPLENTE"}]
    s = eleicoes.situacao_2026("Danilo Balas", "DEPUTADO ESTADUAL", cands)
    assert s["status"] == "a_conferir", "na dúvida, não afirma"


def test_bancada_nova():
    novos = eleicoes.novos_eleitos(_candidatos(), "DEPUTADO ESTADUAL",
                                   ["Agente Federal Danilo Balas", "André do Prado"])
    assert [c["nome_urna"] for c in novos] == ["JOÃO NOVO"]


def test_posse_e_1_de_fevereiro_para_os_tres_cargos():
    """A ALESP mudou: até 2023 a posse era em 15 de março."""
    assert eleicoes.POSSE_2027 == "2027-02-01"


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
            print(f"ok  {nome}")
    print("eleição 2026: todos os testes passaram")
