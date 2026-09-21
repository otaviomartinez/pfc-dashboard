#!/usr/bin/env python3
"""Baixa a CAPAG (Tesouro Transparente) e recorta para os municípios do painel.

Roda no GitHub Actions (lá a internet é livre) ou na máquina do usuário:

    python scripts/importar_capag.py [exercicio]

Descobre o arquivo pela API do CKAN (não chuta URL fixa, que muda todo ano),
baixa a planilha, filtra e grava data/prefeituras/capag_<ano>.csv.

REGRA: município sem nota NÃO entra com nota ruim — ele simplesmente não entra,
e o painel mostra "não avaliado" (que é neutro, não é C/D).
"""
import csv
import io
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prefeituras.config import carregar_municipios, normalizar_nome  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA_DIR = os.path.join(BASE, "data", "prefeituras")
CKAN = ("https://www.tesourotransparente.gov.br/ckan/api/3/action/"
        "package_show?id=capag-municipios")
TIMEOUT = 120


def _baixar(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "pfc-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def achar_recurso() -> tuple[str, str] | None:
    """(url, formato) do recurso mais recente em XLSX/CSV, ou None."""
    try:
        pacote = json.loads(_baixar(CKAN).decode("utf-8"))
    except Exception as e:
        print(f"  ! CKAN não respondeu: {type(e).__name__}: {str(e)[:120]}")
        return None
    recursos = (pacote.get("result") or {}).get("resources") or []
    candidatos = [r for r in recursos
                  if str(r.get("format", "")).upper() in ("XLSX", "CSV", "XLS")]
    if not candidatos:
        print(f"  ! nenhum XLSX/CSV entre os {len(recursos)} recursos do dataset")
        return None
    # o mais recente primeiro (o CKAN traz last_modified/created)
    candidatos.sort(key=lambda r: str(r.get("last_modified") or r.get("created") or ""),
                    reverse=True)
    escolhido = candidatos[0]
    return escolhido.get("url", ""), str(escolhido.get("format", "")).upper()


def _linhas_da_planilha(conteudo: bytes, formato: str) -> list[dict]:
    """Linhas como dicts, seja XLSX (via pandas/openpyxl) ou CSV."""
    if formato in ("XLSX", "XLS"):
        import pandas as pd
        df = pd.read_excel(io.BytesIO(conteudo))
        # cabeçalho às vezes começa algumas linhas abaixo: procura a linha que
        # tem 'ibge' em alguma célula e reprocessa a partir dela.
        if not any("ibge" in str(c).lower() for c in df.columns):
            bruto = pd.read_excel(io.BytesIO(conteudo), header=None)
            for i in range(min(12, len(bruto))):
                if any("ibge" in str(v).lower() for v in bruto.iloc[i].tolist()):
                    df = pd.read_excel(io.BytesIO(conteudo), header=i)
                    break
        return df.to_dict("records")
    texto = conteudo.decode("utf-8-sig", errors="replace")
    sep = ";" if texto.count(";") > texto.count(",") else ","
    return list(csv.DictReader(io.StringIO(texto), delimiter=sep))


def _campo(linha: dict, *termos: str):
    """Primeiro valor cuja COLUNA contém todos os termos (sem acento/caixa)."""
    for k, v in linha.items():
        nome = normalizar_nome(k)
        if all(t in nome for t in termos):
            return v
    return None


def main() -> int:
    exercicio = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    print("== CAPAG · descobrindo o arquivo no CKAN do Tesouro ==")
    achado = achar_recurso()
    if not achado:
        return 1
    url, formato = achado
    print(f"  recurso: {formato} · {url[:110]}")
    try:
        conteudo = _baixar(url)
    except Exception as e:
        print(f"  ! download falhou: {type(e).__name__}: {str(e)[:120]}")
        return 1
    print(f"  {len(conteudo)//1024} KB baixados")

    try:
        linhas = _linhas_da_planilha(conteudo, formato)
    except Exception as e:
        print(f"  ! não consegui ler a planilha: {type(e).__name__}: {str(e)[:150]}")
        return 1
    print(f"  {len(linhas)} linhas na planilha")

    alvos = {m["cod_ibge"]: m["nome"] for m in carregar_municipios()}
    saida, ano_visto = [], exercicio
    for linha in linhas:
        cod = _campo(linha, "ibge")
        if cod is None:
            continue
        cod = str(cod).split(".")[0].strip()          # 3510302.0 -> 3510302
        if cod not in alvos:
            continue
        nota = _campo(linha, "capag") or _campo(linha, "nota")
        nota = str(nota or "").strip().upper()
        if nota not in ("A", "B", "C", "D"):
            print(f"  · {alvos[cod]}: sem nota válida ({nota!r}) — fica 'não avaliado'")
            continue
        ano = _campo(linha, "exercicio") or _campo(linha, "ano")
        try:
            ano_visto = int(str(ano).split(".")[0]) if ano else ano_visto
        except ValueError:
            pass
        saida.append({
            "cod_ibge": cod, "municipio": alvos[cod], "nota": nota,
            "endividamento": str(_campo(linha, "endivid") or "").strip(),
            "poupanca": str(_campo(linha, "poupan") or "").strip(),
            "liquidez": str(_campo(linha, "liquid") or "").strip(),
        })

    if not ano_visto:
        import datetime
        ano_visto = datetime.date.today().year - 1
    os.makedirs(SAIDA_DIR, exist_ok=True)
    destino = os.path.join(SAIDA_DIR, f"capag_{ano_visto}.csv")
    with open(destino, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["cod_ibge", "municipio", "nota",
                                          "endividamento", "poupanca", "liquidez"])
        w.writeheader()
        w.writerows(sorted(saida, key=lambda x: x["municipio"]))
    print(f"{len(saida)} de {len(alvos)} municípios com nota -> {destino}")
    if len(saida) < len(alvos):
        print("  (os demais ficam 'não avaliado' no painel — ausência não é nota ruim)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
