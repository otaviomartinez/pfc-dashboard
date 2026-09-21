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
        xls = pd.ExcelFile(io.BytesIO(conteudo))
        print("  abas:", xls.sheet_names)
        # NÃO escolher a aba pelo NOME. A pasta tem várias abas "CAPAG *", e a
        # "CAPAG Ano Base 2025" é a de INDICADORES (Dívida Consolidada, DPC-2…),
        # sem lista de municípios — escolhê-la pelo nome quebrou a coleta. A aba
        # certa é a que, ao ser lida, REALMENTE tem coluna de código de município
        # E coluna de nota. Validamos antes de aceitar.
        def _cab_valido(celulas):
            tem_cod = any(("ibge" in x) or ("codigo" in x and "municipio" in x)
                          for x in celulas)
            tem_nota = any(("capag" in x) or x.startswith("nota") for x in celulas)
            return tem_cod and tem_nota

        candidatas = ([a for a in xls.sheet_names if "capag" in str(a).lower()]
                      + [a for a in xls.sheet_names if "capag" not in str(a).lower()])
        for aba in candidatas:
            try:
                bruto = pd.read_excel(xls, sheet_name=aba, header=None, nrows=40)
            except Exception:
                continue
            for i in range(min(30, len(bruto))):
                celulas = [normalizar_nome(v) for v in bruto.iloc[i].tolist()]
                if _cab_valido(celulas):
                    df = pd.read_excel(xls, sheet_name=aba, header=i)
                    print(f"  aba {aba!r}, cabeçalho na linha {i} (validado: "
                          "tem código de município e nota)")
                    return df.to_dict("records")
        print("  ! nenhuma aba tem código de município + nota. Abas vistas acima.")
        return []
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


def _codigo(linha: dict):
    """Código do município. A planilha do Tesouro chama de "Código Município
    Completo" — SEM a palavra "IBGE", que era o único termo que procurávamos
    antes (por isso 0 de 11 casavam). Descoberto no log do Actions."""
    for termos in (("ibge",), ("codigo", "municipio"), ("cod", "mun"), ("codigo",)):
        v = _campo(linha, *termos)
        if v is not None:
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

    # DIAGNÓSTICO: sem isto, "0 de 11" não diz NADA sobre o porquê. Com as
    # colunas e uma linha de exemplo no log, dá para consertar na próxima rodada.
    if linhas:
        print("  colunas encontradas:", list(linhas[0].keys())[:18])
        exemplo = {k: v for k, v in list(linhas[0].items())[:8]}
        print("  1ª linha (amostra):", exemplo)

    alvos = {m["cod_ibge"]: m["nome"] for m in carregar_municipios()}
    # Alguns arquivos do Tesouro usam o código IBGE de 6 dígitos (sem o dígito
    # verificador). Indexa pelos dois para casar nos dois formatos.
    alvos6 = {cod[:6]: cod for cod in alvos}
    saida, ano_visto = [], exercicio
    for linha in linhas:
        cod = _codigo(linha)
        if cod is None:
            continue
        cod = str(cod).split(".")[0].strip()          # 3510302.0 -> 3510302
        if cod not in alvos:
            cod = alvos6.get(cod[:6], "") if len(cod) >= 6 else ""
            if not cod:
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
            # Metodologia do Tesouro: Indicador 1 = endividamento,
            # 2 = poupança corrente, 3 = liquidez. Na planilha as notas vêm como
            # "Nota 1/2/3" (visto no log), não pelos nomes por extenso.
            "endividamento": str(_campo(linha, "endivid")
                                 or _campo(linha, "nota 1") or "").strip(),
            "poupanca": str(_campo(linha, "poupan")
                            or _campo(linha, "nota 2") or "").strip(),
            "liquidez": str(_campo(linha, "liquid")
                            or _campo(linha, "nota 3") or "").strip(),
        })

    if not ano_visto:
        import datetime
        ano_visto = datetime.date.today().year - 1
    if not saida:
        # Não grava CSV vazio (ele seria commitado sem acrescentar nada) e sai
        # com 1, para o passo ficar VERMELHO no Actions — sinal visível.
        print("NENHUM dos 11 municípios casou. Compare o código do painel com a "
              "coluna de IBGE impressa acima. Nada foi gravado.")
        return 1
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
