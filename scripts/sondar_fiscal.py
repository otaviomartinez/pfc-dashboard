#!/usr/bin/env python3
"""SONDA dos dados que faltam para ligar o método fiscal (src/prefeituras/fiscal.py).

NÃO grava nada. Só pergunta às fontes oficiais e IMPRIME o que elas devolvem,
para eu escrever o coletor em cima de evidência — e não de chute. Foi assim que
descobrimos que o SICONFI não publica o Anexo 08 (MDE) e que o e-mail de
prefeitura vem vazio no cadastro de CNPJ.

O fiscal precisa de quatro fatores:
  caixa (RGF-Anexo 05) · pessoal %RCL (RGF-Anexo 01) · FPM · CAUC

Roda no GitHub Actions, onde a rede é livre:
    python scripts/sondar_fiscal.py
"""
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prefeituras.config import carregar_municipios  # noqa: E402
from src.prefeituras import siconfi  # noqa: E402

ANO = 2025
SEPARADOR = "=" * 70


def _get(url: str, timeout: int = 40):
    """Devolve (status, corpo-ou-None). Nunca levanta — a sonda não pode morrer."""
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "pfc-dashboard/1.0 (painel de captacao, uso institucional)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            bruto = r.read().decode("utf-8", "replace")
            try:
                return r.status, json.loads(bruto)
            except Exception:
                return r.status, bruto[:400]
    except Exception as e:
        return getattr(e, "code", 0) or 0, f"{type(e).__name__}: {str(e)[:150]}"


def amostra_rgf(cod, nome, anexo, rotulos_procurados):
    """Imprime QUAIS linhas o anexo devolve — o nome da conta é o que quebra.

    Faz a requisição AQUI (não via siconfi.buscar_rgf) de propósito: aquele
    cliente engole o erro e devolve None, então 'rede bloqueada' e 'API
    respondeu vazio' ficam idênticos. Numa sonda, isso é inaceitável.
    """
    print(f"\n-- {nome} · {anexo} · {ANO} --")
    base = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
    for periodo in (3, 2, 1):          # 3º quadrimestre primeiro (ano fechado)
        url = f"{base}/rgf?" + urllib.parse.urlencode({
            "an_exercicio": ANO, "nr_periodo": periodo,
            "co_tipo_demonstrativo": "RGF", "no_anexo": anexo,
            "co_poder": "E", "id_ente": cod})
        status, corpo = _get(url)
        itens = (corpo or {}).get("items") if isinstance(corpo, dict) else None
        if itens is None:
            print(f"   período {periodo}: status {status} · {str(corpo)[:120]}")
            continue
        if not itens:
            print(f"   período {periodo}: status {status} · items=[] (vazio de verdade)")
            continue
        print(f"   período {periodo}: status {status} · {len(itens)} linhas · "
              f"campos: {sorted(itens[0].keys())}")
        vistos = 0
        for it in itens:
            rotulo, coluna, valor = siconfi._campos(it)
            if any(siconfi._casa(rotulo, t) for t in rotulos_procurados):
                print(f"      · {rotulo[:62]!r} | {coluna[:28]!r} = {valor}")
                vistos += 1
                if vistos >= 6:
                    break
        if not vistos:
            print("      (nenhuma linha com os termos procurados; primeiras 4:)")
            for it in itens[:4]:
                r, c, v = siconfi._campos(it)
                print(f"      · {r[:62]!r} | {c[:28]!r} = {v}")
        return                          # achou período com dado: basta
    print("   NENHUM período trouxe linha.")


def sondar_fpm(cod, nome):
    """FPM: quanto do orçamento vem de repasse. Duas rotas possíveis."""
    print(f"\n-- {nome} · FPM --")
    base = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
    url = f"{base}/dca?" + urllib.parse.urlencode({
        "an_exercicio": ANO - 1, "no_anexo": "DCA-Anexo I-C", "id_ente": cod})
    status, corpo = _get(url)
    itens = (corpo or {}).get("items") if isinstance(corpo, dict) else None
    print(f"   DCA-Anexo I-C (receitas) {ANO-1}: status {status} · "
          f"{len(itens) if itens is not None else '—'} linhas")
    if itens:
        print(f"   campos: {sorted(itens[0].keys())}")
        for it in itens:
            rotulo = str(it.get("conta") or "")
            if "fpm" in rotulo.lower() or "fundo de participacao" in rotulo.lower() \
               or "participação dos munic" in rotulo.lower():
                print(f"      · {rotulo[:70]!r} = {it.get('valor')}")


def sondar_cauc():
    """CAUC: existe endpoint aberto? É o fator DECISIVO (irregular não assina)."""
    print(f"\n{SEPARADOR}\nCAUC — regularidade para transferência voluntária\n{SEPARADOR}")
    candidatos = [
        "https://apidatalake.tesouro.gov.br/ords/transferencias/tt/cauc",
        "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/cauc",
        "https://consultas.tesouro.gov.br/transferencias/cauc/api/situacao",
        "https://apidatalake.tesouro.gov.br/ords/custeio/tt/cauc",
    ]
    for url in candidatos:
        status, corpo = _get(url, timeout=25)
        resumo = corpo if isinstance(corpo, str) else json.dumps(corpo)[:220]
        print(f"  [{status}] {url}\n        {resumo[:220]}")


def main() -> int:
    muns = carregar_municipios()
    amostra = muns[:2]
    print(f"{SEPARADOR}\nSONDA FISCAL · {len(muns)} municípios do PFC · "
          f"amostra: {', '.join(m['nome'] for m in amostra)}\n{SEPARADOR}")

    status, corpo = _get("https://apidatalake.tesouro.gov.br/ords/siconfi/tt/entes")
    n = len((corpo or {}).get("items") or []) if isinstance(corpo, dict) else 0
    print(f"\nrede: /entes -> status {status} · {n} entes")
    if not n:
        print("  ! sem rede para o Tesouro. Tudo abaixo seria 'vazio' por engano.")
        print(f"  ! resposta: {str(corpo)[:160]}")
        return 1

    print(f"\n{SEPARADOR}\nRGF — caixa e pessoal\n{SEPARADOR}")
    for m in amostra:
        amostra_rgf(m["cod_ibge"], m["nome"], "RGF-Anexo 05",
                    ["disponibilidade", "caixa", "obrigac"])
        amostra_rgf(m["cod_ibge"], m["nome"], "RGF-Anexo 01",
                    ["pessoal", "receita corrente liquida", "percentual"])

    print(f"\n{SEPARADOR}\nFPM — dependência de repasse\n{SEPARADOR}")
    for m in amostra:
        sondar_fpm(m["cod_ibge"], m["nome"])

    sondar_cauc()

    print(f"\n{SEPARADOR}\nFim da sonda. Nada foi gravado.\n{SEPARADOR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
