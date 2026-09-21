#!/usr/bin/env python3
"""Contato INSTITUCIONAL das prefeituras, automático, via CNPJ da Receita.

POR QUE ESTA FONTE: o INEP dá telefone de ESCOLA mas não tem e-mail nem o
contato da prefeitura; o TSE mascara e-mail de candidato. Já o cadastro de CNPJ
da Receita Federal traz, para CADA prefeitura, o **e-mail, telefone e endereço
oficiais** — é público, é institucional e é atualizado pelo próprio município.

PIPELINE (roda no GitHub Actions, onde a rede é livre):
  1. SICONFI /entes  -> cod_ibge + CNPJ de cada ente (o SICONFI responde bem
     no runner: foi lá que ele devolveu 489 linhas do Anexo 02).
  2. BrasilAPI /cnpj -> e-mail, telefone e endereço daquele CNPJ.
  3. Grava data/prefeituras/contatos_prefeitura.csv.

NUNCA INVENTA: município sem CNPJ no SICONFI, ou CNPJ que a BrasilAPI não
conhece, simplesmente NÃO entra no CSV — o painel cai para os links de busca.
Campo vazio é ausência, não erro (regra 5c).

    python scripts/importar_contatos_prefeitura.py
"""
import csv
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prefeituras.config import (  # noqa: E402
    carregar_municipios, municipios_da_regiao,
)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(BASE, "data", "prefeituras", "contatos_prefeitura.csv")
ENTES = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/entes"
BRASILAPI = "https://brasilapi.com.br/api/cnpj/v1/"
COLUNAS = ["cod_ibge", "municipio", "cnpj", "razao_social", "email", "telefone",
           "endereco", "cep", "fonte"]


def _json(url: str, timeout: int = 45):
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "pfc-dashboard/1.0 (painel de captacao, uso institucional)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def entes_com_cnpj() -> dict[str, dict]:
    """{cod_ibge: ente} do SICONFI. Imprime os CAMPOS que a API devolve —
    sem isso, um 'cnpj' que mude de nome quebraria em silêncio."""
    try:
        dados = _json(ENTES)
    except Exception as e:
        print(f"  ! SICONFI /entes falhou: {type(e).__name__}: {str(e)[:110]}")
        return {}
    itens = (dados or {}).get("items") or []
    if not itens:
        print("  ! /entes respondeu vazio")
        return {}
    print(f"  /entes: {len(itens)} entes · campos: {list(itens[0].keys())}")
    saida = {}
    for it in itens:
        cod = str(it.get("cod_ibge") or "").strip()
        if cod:
            saida[cod] = it
    return saida


def _campo_cnpj(ente: dict) -> str:
    """CNPJ do ente, qualquer que seja o nome do campo. '' se não houver."""
    for chave, valor in (ente or {}).items():
        if "cnpj" in str(chave).lower():
            so_digitos = "".join(c for c in str(valor) if c.isdigit())
            if len(so_digitos) == 14:
                return so_digitos
    return ""


def consultar_cnpj(cnpj: str, tentativas: int = 3) -> dict | None:
    """Contato do CNPJ na BrasilAPI. None quando não dá (nunca levanta).

    A API pública limita a taxa (429). Em vez de perder o município, espera e
    tenta de novo — 88 consultas numa rodada trimestral cabem folgadas.
    """
    for n in range(tentativas):
        try:
            return _json(BRASILAPI + cnpj, timeout=30)
        except Exception as e:
            transitorio = "429" in str(e) or "500" in str(e) or "timed out" in str(e)
            if n == tentativas - 1 or not transitorio:
                return None
            time.sleep(5 * (n + 1))
    return None


def main() -> int:
    muns = carregar_municipios()
    alvos = {m["cod_ibge"]: m["nome"] for m in muns}
    for regiao in {m["regiao_imediata"] for m in muns}:
        for viz in municipios_da_regiao(regiao):
            alvos.setdefault(viz["cod_ibge"], viz["nome"])
    print(f"== Contatos de prefeitura · {len(alvos)} municípios (11 + vizinhos) ==")

    entes = entes_com_cnpj()
    if not entes:
        print("  sem /entes, não há como descobrir os CNPJs. Nada gravado.")
        return 1

    com_cnpj = {c: _campo_cnpj(e) for c, e in entes.items() if c in alvos}
    com_cnpj = {c: v for c, v in com_cnpj.items() if v}
    print(f"  com CNPJ no SICONFI: {len(com_cnpj)} de {len(alvos)}")
    if not com_cnpj:
        print("  ! nenhum CNPJ encontrado. Veja os campos de /entes acima — o "
              "nome da coluna pode ter mudado. Nada gravado.")
        return 1

    linhas, sem = [], []
    for i, (cod, cnpj) in enumerate(sorted(com_cnpj.items()), 1):
        dados = consultar_cnpj(cnpj)
        if not dados:
            sem.append(alvos[cod])
            continue
        endereco = " ".join(str(x) for x in (
            dados.get("logradouro"), dados.get("numero"), dados.get("bairro"),
            dados.get("municipio"), dados.get("uf")) if x)
        linhas.append({
            "cod_ibge": cod, "municipio": alvos[cod], "cnpj": cnpj,
            "razao_social": str(dados.get("razao_social") or "").strip(),
            "email": str(dados.get("email") or "").strip().lower(),
            "telefone": str(dados.get("ddd_telefone_1") or "").strip(),
            "endereco": " ".join(endereco.split()),
            "cep": str(dados.get("cep") or "").strip(),
            "fonte": "receita-cnpj",
        })
        if i % 20 == 0:
            print(f"    {i}/{len(com_cnpj)}…")
        time.sleep(0.4)          # educado com a API pública

    if not linhas:
        print("  ! nenhuma prefeitura retornou contato. NÃO gravo CSV vazio "
              "(arquivo vazio apagaria o que já funciona).")
        return 1

    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(sorted(linhas, key=lambda x: x["municipio"]))
    com_email = sum(1 for x in linhas if x["email"])
    com_tel = sum(1 for x in linhas if x["telefone"])
    print(f"{len(linhas)} prefeituras gravadas -> {SAIDA}")
    print(f"  com e-mail: {com_email} · com telefone: {com_tel}")
    if sem:
        print(f"  sem retorno da BrasilAPI ({len(sem)}): {', '.join(sem[:8])}"
              + ("…" if len(sem) > 8 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
