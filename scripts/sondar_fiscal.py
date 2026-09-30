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


def varrer_rgf(cod, nome):
    """RGF com 2025 veio 'items=[] de verdade'. Isso pode ser: ano ainda não
    publicado, grafia do anexo, ou o co_poder. Varre as três hipóteses — é o
    mesmo procedimento que provou que o Anexo 08 (MDE) não existe no SICONFI."""
    print(f"\n-- {nome} · varredura RGF --")
    base = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
    achou = []
    for ano in (2024, 2023, 2025):
        for anexo in ("RGF-Anexo 01", "RGF-Anexo 05", "RGF-Anexo 06"):
            for periodo in (3, 2):
                for poder in ("E", None):
                    params = {"an_exercicio": ano, "nr_periodo": periodo,
                              "co_tipo_demonstrativo": "RGF", "no_anexo": anexo,
                              "id_ente": cod}
                    if poder:
                        params["co_poder"] = poder
                    status, corpo = _get(f"{base}/rgf?" + urllib.parse.urlencode(params))
                    itens = (corpo or {}).get("items") if isinstance(corpo, dict) else None
                    if itens:
                        achou.append((ano, anexo, periodo, poder, len(itens), itens))
                        print(f"   ACHOU {ano} {anexo} per{periodo} "
                              f"poder={poder or '(sem)'} -> {len(itens)} linhas")
                        break
                if achou and achou[-1][:3] == (ano, anexo, periodo):
                    break
    if not achou:
        print("   NADA em 2023/2024/2025 x anexos 01/05/06 x períodos 2/3 x com e sem co_poder.")
        return
    for (_a, anexo, _p, _pd, _n, itens) in achou[:2]:
        print(f"   amostra de {anexo} · campos: {sorted(itens[0].keys())}")
        for it in itens[:8]:
            r, c, v = siconfi._campos(it)
            print(f"      · {r[:58]!r} | {c[:30]!r} = {v}")


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
        colunas = sorted({str(i.get("coluna") or "") for i in itens})
        print(f"   colunas disponíveis: {colunas}")
        for it in itens:
            rotulo = str(it.get("conta") or "")
            baixo = rotulo.lower()
            interessa = ("participação dos munic" in baixo or "fpm" in baixo
                         or baixo.strip().startswith("1.0.0.0.00.0.0")
                         or "receitas correntes" in baixo
                         or "receita corrente" in baixo)
            if interessa:
                print(f"      · {rotulo[:58]!r} | {str(it.get('coluna'))[:26]!r} "
                      f"= {it.get('valor')}")


def sondar_cauc():
    """CAUC: existe endpoint aberto? É o fator DECISIVO (irregular não assina)."""
    print(f"\n{SEPARADOR}\nCAUC — regularidade para transferência voluntária\n{SEPARADOR}")
    candidatos = [
        "https://apidatalake.tesouro.gov.br/ords/transferencias/tt/cauc",
        "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/cauc",
        "https://consultas.tesouro.gov.br/transferencias/cauc/api/situacao",
        "https://apidatalake.tesouro.gov.br/ords/custeio/tt/cauc",
        # Transferegov (sucessor do SICONV) publica API aberta de convênios;
        # se houver adimplência/CAUC em algum lugar, é o candidato mais forte.
        "https://api.transferegov.gestao.gov.br/cauc",
        "https://api.transferegov.gestao.gov.br/convenios",
        "https://api.transferegov.gestao.gov.br/cadastro/proponentes?limit=1",
        "https://api.transferegov.gestao.gov.br/convenios/convenio?limit=1",
        "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/",
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
        varrer_rgf(m["cod_ibge"], m["nome"])

    print(f"\n{SEPARADOR}\nFPM — dependência de repasse\n{SEPARADOR}")
    for m in amostra:
        sondar_fpm(m["cod_ibge"], m["nome"])

    sondar_cauc()

    print(f"\n{SEPARADOR}\nFim da sonda. Nada foi gravado.\n{SEPARADOR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
