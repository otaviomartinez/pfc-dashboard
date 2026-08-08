"""Teste puro do helper _sala_no_crm — sala/gabinete ALESP a partir do CRM.

Prova que:
  - acha a sala por nome EXATO;
  - acha por nome VARIANTE (acento/caixa e nome contido, ex.: 'Danilo Balas' ↔
    'Agente Federal Danilo Balas');
  - devolve '' quando o deputado está FORA do CRM (omissão graciosa);
  - devolve '' quando a sala está VAZIA (ou 'nan'/'none');
  - devolve '' para df None/vazio/sem coluna 'Deputado'.

    python tests/test_sala_alesp.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

from ui.formato import _sala_no_crm  # noqa: E402

CRM = pd.DataFrame([
    {"Deputado": "Professora Bebel", "Gabinete ALESP": "Sala 255"},
    {"Deputado": "Agente Federal Danilo Balas", "Gabinete ALESP": "Gab. 1107"},
    {"Deputado": "Fulano Sem Sala", "Gabinete ALESP": ""},
    {"Deputado": "Sicrano Nan", "Gabinete ALESP": "nan"},
])


def test_acha_por_nome_exato():
    assert _sala_no_crm("Professora Bebel", CRM) == "Sala 255"


def test_acha_por_nome_variante_normalizado():
    # caixa/acento diferentes + nome CONTIDO (o CRM tem o prefixo 'Agente Federal')
    assert _sala_no_crm("danilo balas", CRM) == "Gab. 1107"
    assert _sala_no_crm("PROFESSORA BEBEL", CRM) == "Sala 255"


def test_fora_do_crm_devolve_vazio():
    assert _sala_no_crm("Deputado Inexistente", CRM) == ""


def test_sala_vazia_ou_nan_devolve_vazio():
    assert _sala_no_crm("Fulano Sem Sala", CRM) == ""
    assert _sala_no_crm("Sicrano Nan", CRM) == ""


def test_df_degenerado_devolve_vazio():
    assert _sala_no_crm("Professora Bebel", None) == ""
    assert _sala_no_crm("Professora Bebel", pd.DataFrame()) == ""
    assert _sala_no_crm("Professora Bebel", pd.DataFrame([{"X": 1}])) == ""
    assert _sala_no_crm("", CRM) == ""


if __name__ == "__main__":
    test_acha_por_nome_exato()
    test_acha_por_nome_variante_normalizado()
    test_fora_do_crm_devolve_vazio()
    test_sala_vazia_ou_nan_devolve_vazio()
    test_df_degenerado_devolve_vazio()
    print("OK — testes de _sala_no_crm (sala ALESP, omissão graciosa) passaram.")
