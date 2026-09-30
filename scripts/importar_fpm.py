#!/usr/bin/env python3
"""Dependência de FPM por município, do SICONFI (DCA-Anexo I-C, receitas).

POR QUE ESTE CAMINHO: a sonda (scripts/sondar_fiscal.py) mostrou que o RGF não
existe no SICONFI para os municípios de SP — mas o DCA existe e traz, na mesma
resposta, o numerador e o denominador:
  numerador   1.7.1.1.51.0.0  Cota-Parte do Fundo de Participação dos Municípios
  denominador 1.0.0.0.00.0.0  Receitas Correntes
ambos na coluna "Receitas Brutas Realizadas" (a outra coluna é "Deduções -
FUNDEB", que NÃO é o valor bruto — pegar a coluna errada daria um percentual
inventado).

Município cujo DCA não traz as duas linhas simplesmente não entra: o painel
mostra "sem dado", que é resposta legítima (regra 5c).

    python scripts/importar_fpm.py [exercicio]
"""
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prefeituras.config import (  # noqa: E402
    carregar_municipios, municipios_da_regiao,
)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA_DIR = os.path.join(BASE, "data", "prefeituras")
URL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca"
ANEXO = "DCA-Anexo I-C"
COLUNA_BRUTA = "Receitas Brutas Realizadas"
CONTA_FPM = "1.7.1.1.51.0.0"
CONTA_RECEITAS_CORRENTES = "1.0.0.0.00.0.0"
COLUNAS = ["cod_ibge", "municipio", "exercicio", "fpm", "receitas_correntes",
           "dependencia_pct", "origem"]


def _json(url: str, timeout: int = 45):
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "pfc-dashboard/1.0 (painel de captacao, uso institucional)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"    ! {type(e).__name__}: {str(e)[:90]}")
        return None


def _valor_bruto(itens, conta_prefixo: str):
    """Valor da conta na coluna BRUTA. None se a linha não vier."""
    for it in itens:
        conta = str(it.get("conta") or "").strip()
        if conta.startswith(conta_prefixo) and str(it.get("coluna") or "") == COLUNA_BRUTA:
            try:
                return float(it.get("valor"))
            except (TypeError, ValueError):
                return None
    return None


def dependencia(cod_ibge: str, exercicio: int) -> dict | None:
    """{fpm, receitas_correntes, dependencia_pct} ou None."""
    dados = _json(f"{URL}?" + urllib.parse.urlencode({
        "an_exercicio": exercicio, "no_anexo": ANEXO, "id_ente": cod_ibge}))
    itens = (dados or {}).get("items") or []
    if not itens:
        return None
    fpm = _valor_bruto(itens, CONTA_FPM)
    receitas = _valor_bruto(itens, CONTA_RECEITAS_CORRENTES)
    if fpm is None or not receitas:      # sem denominador não há percentual
        return None
    return {"fpm": round(fpm, 2), "receitas_correntes": round(receitas, 2),
            "dependencia_pct": round(fpm / receitas * 100, 2)}


def main() -> int:
    exercicio = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].strip() \
        else __import__("datetime").date.today().year - 2   # DCA fecha com atraso
    muns = carregar_municipios()
    alvos = {m["cod_ibge"]: m["nome"] for m in muns}
    for regiao in {m["regiao_imediata"] for m in muns}:
        for viz in municipios_da_regiao(regiao):
            alvos.setdefault(viz["cod_ibge"], viz["nome"])
    print(f"== FPM · exercício {exercicio} · {len(alvos)} municípios ==")

    linhas = []
    for i, (cod, nome) in enumerate(sorted(alvos.items(), key=lambda x: x[1]), 1):
        reg = dependencia(cod, exercicio)
        if reg:
            linhas.append({"cod_ibge": cod, "municipio": nome,
                           "exercicio": exercicio, "origem": "siconfi-dca", **reg})
        if i % 20 == 0:
            print(f"   {i}/{len(alvos)}…")
        time.sleep(0.3)

    if not linhas:
        print("  ! nenhum município trouxe FPM + receita corrente. NÃO gravo CSV "
              f"vazio. Talvez o exercício {exercicio} ainda não esteja fechado — "
              "tente o anterior.")
        return 1

    os.makedirs(SAIDA_DIR, exist_ok=True)
    saida = os.path.join(SAIDA_DIR, f"fpm_{exercicio}.csv")
    with open(saida, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(sorted(linhas, key=lambda x: x["municipio"]))
    pcts = [l["dependencia_pct"] for l in linhas]
    print(f"{len(linhas)} municípios -> {saida}")
    print(f"  dependência de FPM: mín {min(pcts):.1f}% · média "
          f"{sum(pcts)/len(pcts):.1f}% · máx {max(pcts):.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
