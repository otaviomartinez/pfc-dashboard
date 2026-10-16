#!/usr/bin/env python3
"""Cota parlamentar (CEAP) dos deputados federais de SP -> onde eles circulam.

    python scripts/importar_cota_parlamentar.py [anos...] [--minutos N]

Roda no GitHub Actions (workflow "Mapa da cota parlamentar"): o site da Câmara
é bloqueado no ambiente do assistente. Sem anos, usa o ano atual e o anterior.

FONTE: arquivo oficial da Câmara, um por ano:
  https://www.camara.leg.br/cotas/Ano-<ano>.csv.zip

O QUE FICA (e por quê):
  - só deputados de SP;
  - só notas com CNPJ (empresa) — CPF de pessoa física nunca é gravado;
  - só três categorias que provam PRESENÇA na cidade do fornecedor:
    combustível, alimentação e hospedagem. O escritório de apoio vai num grupo
    à parte, porque conta de luz/telefone vem da sede da empresa;
  - a CIDADE de cada CNPJ vem do cadastro público de empresas (BrasilAPI, com
    minhareceita.org de reserva), guardada num cache para a próxima rodada não
    repetir a consulta.

Saída (data/cota/): presenca_federais_sp.csv (deputado x cidade x grupo, com
número de notas e a data da última), cnpj_municipio.csv (cache) e
coleta_resumo.csv (anos, período, cobertura). Não grava nada se o arquivo da
Câmara vier vazio — apagaria o que já funciona.

TETO DE TEMPO (--minutos, padrão 40): são milhares de CNPJs. O que não der
tempo fica para a próxima rodada; a cobertura sai no resumo e na tela.
"""
from __future__ import annotations

import csv
import datetime
import io
import json
import os
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import zipfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA = os.path.join(BASE, "data", "cota")
SAIDA = os.path.join(PASTA, "presenca_federais_sp.csv")
CACHE = os.path.join(PASTA, "cnpj_municipio.csv")
RESUMO = os.path.join(PASTA, "coleta_resumo.csv")
URL_ANO = "https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip"
BRASILAPI = "https://brasilapi.com.br/api/cnpj/v1/{}"
MINHARECEITA = "https://minhareceita.org/{}"
COLUNAS = ["deputado_id", "deputado", "partido", "municipio", "uf", "grupo", "notas",
           "valor", "primeira_data", "ultima_data"]
UA = {"User-Agent": "pfc-dashboard/1.0 (UFSCar - Programa Futuro Cientista)"}


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def grupo_da_categoria(descricao: str) -> str | None:
    """PURA: 'presenca' | 'escritorio' | None (categoria que não interessa)."""
    d = _norm(descricao)
    if "combust" in d or "alimenta" in d or "hosped" in d:
        return "presenca"
    if "escritorio" in d:
        return "escritorio"
    return None


def _so_digitos(s) -> str:
    return "".join(c for c in str(s or "") if c.isdigit())


def _float(v) -> float:
    s = str(v or "").strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s.replace(",", ".") or 0)
    except ValueError:
        return 0.0


def _col(cab: dict, *nomes) -> str | None:
    """Nome real da coluna, aceitando variações de caixa entre anos."""
    for n in nomes:
        if n.lower() in cab:
            return cab[n.lower()]
    return None


def extrair(linhas) -> list[dict]:
    """PURA: das linhas da Câmara, notas de SP com CNPJ nas categorias úteis.
    Devolve [{deputado_id, deputado, partido, cnpj, grupo, data, valor}]."""
    saida, cab = [], None
    for r in linhas:
        if cab is None:
            cab = {k.lower().strip().lstrip("﻿"): k for k in r.keys()}
            c = {
                "nome": _col(cab, "txNomeParlamentar"), "uf": _col(cab, "sgUF"),
                "partido": _col(cab, "sgPartido"),
                "id": _col(cab, "nuDeputadoId", "ideCadastro"),
                "desc": _col(cab, "txtDescricao"), "cnpj": _col(cab, "txtCNPJCPF"),
                "data": _col(cab, "datEmissao"),
                "valor": _col(cab, "vlrLiquido", "vlrDocumento"),
            }
            faltam = [k for k, v in c.items() if not v]
            if faltam:
                raise ValueError(f"colunas não encontradas no arquivo da Câmara: {faltam}; "
                                 f"cabeçalho: {list(r.keys())[:40]}")
        if str(r.get(c["uf"], "")).strip().upper() != "SP":
            continue
        grupo = grupo_da_categoria(r.get(c["desc"]))
        cnpj = _so_digitos(r.get(c["cnpj"]))
        if not grupo or len(cnpj) != 14:
            continue
        saida.append({"deputado_id": str(r.get(c["id"], "")).strip(),
                      "deputado": str(r.get(c["nome"], "")).strip(),
                      "partido": str(r.get(c["partido"], "")).strip(),
                      "cnpj": cnpj, "grupo": grupo,
                      "data": str(r.get(c["data"], "")).strip()[:10],
                      "valor": _float(r.get(c["valor"]))})
    return saida


def agregar(notas: list[dict], cidade_de: dict) -> list[dict]:
    """PURA: (deputado x cidade x grupo) -> notas, valor, primeira e última data.
    Nota cujo CNPJ ainda não tem cidade fica de fora (entra na cobertura)."""
    soma: dict[tuple, dict] = {}
    for n in notas:
        cid = cidade_de.get(n["cnpj"])
        if not cid or not cid.get("municipio"):
            continue
        k = (n["deputado_id"], n["deputado"], n["partido"], cid["municipio"], cid.get("uf", ""),
             n["grupo"])
        a = soma.setdefault(k, {"notas": 0, "valor": 0.0, "primeira_data": "9999", "ultima_data": ""})
        a["notas"] += 1
        a["valor"] += n["valor"]
        if n["data"]:
            a["primeira_data"] = min(a["primeira_data"], n["data"])
            a["ultima_data"] = max(a["ultima_data"], n["data"])
    return [{"deputado_id": k[0], "deputado": k[1], "partido": k[2], "municipio": k[3],
             "uf": k[4], "grupo": k[5], "notas": a["notas"], "valor": round(a["valor"], 2),
             "primeira_data": "" if a["primeira_data"] == "9999" else a["primeira_data"],
             "ultima_data": a["ultima_data"]}
            for k, a in soma.items()]


# ------------------------------------------------------------------ rede
def _baixar(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _linhas_do_ano(ano: int):
    dados = _baixar(URL_ANO.format(ano=ano))
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        nomes = [n for n in z.namelist() if n.lower().endswith(".csv")]
        for nome in nomes:
            bruto = z.read(nome)
            for enc in ("utf-8-sig", "latin-1"):
                try:
                    texto = bruto.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            yield from csv.DictReader(io.StringIO(texto), delimiter=";")


def _cidade_do_cnpj(cnpj: str) -> dict | None:
    """{'municipio','uf','cod_ibge'} | {} (CNPJ não existe) | None (falha de rede)."""
    for url in (BRASILAPI.format(cnpj), MINHARECEITA.format(cnpj)):
        try:
            j = json.loads(_baixar(url, timeout=30).decode("utf-8"))
            return {"municipio": str(j.get("municipio") or "").strip(),
                    "uf": str(j.get("uf") or "").strip(),
                    "cod_ibge": str(j.get("codigo_municipio_ibge") or "").strip()}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {}
            time.sleep(2 if e.code == 429 else 0)
        except Exception:
            continue
    return None


def _ler_cache() -> dict:
    try:
        with open(CACHE, encoding="utf-8", newline="") as f:
            return {r["cnpj"]: r for r in csv.DictReader(f)}
    except (FileNotFoundError, OSError):
        return {}


def _gravar(caminho: str, colunas: list, linhas: list) -> None:
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas)
        w.writeheader()
        w.writerows(linhas)


def main() -> int:
    args = sys.argv[1:]
    minutos = 40
    if "--minutos" in args:
        i = args.index("--minutos")
        minutos = int(args[i + 1])
        del args[i:i + 2]
    hoje = datetime.date.today()
    anos = [int(a) for a in args if a.strip()] or [hoje.year - 1, hoje.year]

    notas = []
    for ano in anos:
        try:
            linhas = list(_linhas_do_ano(ano))
        except Exception as e:
            print(f"! {ano}: não consegui baixar/ler ({type(e).__name__}: {e})")
            continue
        if linhas:
            print(f"  {ano}: cabeçalho = {list(linhas[0].keys())}")
            cats = {}
            for r in linhas:
                if str(r.get("sgUF", "")).upper() == "SP":
                    d = r.get("txtDescricao", "")
                    cats[d] = cats.get(d, 0) + 1
            print(f"  {ano}: categorias de SP = {sorted(cats.items(), key=lambda x: -x[1])[:20]}")
        sel = extrair(linhas)
        print(f"  {ano}: {len(linhas)} notas no arquivo · {len(sel)} de SP úteis com CNPJ")
        notas += sel
    if not notas:
        print("! Nenhuma nota útil. Nada gravado (o que já existe fica).")
        return 1

    cache = _ler_cache()
    contagem = {}
    for n in notas:
        contagem[n["cnpj"]] = contagem.get(n["cnpj"], 0) + 1
    pendentes = [c for c, _ in sorted(contagem.items(), key=lambda x: -x[1]) if c not in cache]
    print(f"  CNPJs: {len(contagem)} distintos · {len(contagem) - len(pendentes)} no cache · "
          f"{len(pendentes)} a consultar (teto {minutos} min)")
    fim = time.time() + 60 * minutos
    feitos = falhas = 0
    for cnpj in pendentes:
        if time.time() > fim:
            break
        cid = _cidade_do_cnpj(cnpj)
        if cid is None:
            falhas += 1
        else:
            cache[cnpj] = {"cnpj": cnpj, **({"municipio": "", "uf": "", "cod_ibge": ""} | cid)}
            feitos += 1
        if (feitos + falhas) % 200 == 0:
            _gravar(CACHE, ["cnpj", "municipio", "uf", "cod_ibge"], list(cache.values()))
        time.sleep(0.35)
    _gravar(CACHE, ["cnpj", "municipio", "uf", "cod_ibge"],
            sorted(cache.values(), key=lambda r: r["cnpj"]))
    print(f"  consultados agora: {feitos} · falhas de rede: {falhas}")

    linhas = agregar(notas, cache)
    _gravar(SAIDA, COLUNAS, sorted(linhas, key=lambda r: (r["deputado"], r["municipio"], r["grupo"])))
    com_cidade = sum(1 for n in notas if cache.get(n["cnpj"], {}).get("municipio"))
    datas = sorted(n["data"] for n in notas if n["data"])
    resumo = {"anos": " ".join(map(str, anos)), "gerado_em": hoje.isoformat(),
              "periodo_inicio": datas[0] if datas else "", "periodo_fim": datas[-1] if datas else "",
              "notas": len(notas), "notas_com_cidade": com_cidade,
              "cnpjs": len(contagem), "cnpjs_resolvidos": sum(1 for c in contagem if c in cache),
              "deputados": len({n["deputado_id"] for n in notas})}
    _gravar(RESUMO, ["chave", "valor"], [{"chave": k, "valor": v} for k, v in resumo.items()])
    print(f"  -> {SAIDA}: {len(linhas)} linhas · cobertura {com_cidade}/{len(notas)} notas com cidade")
    print("  resumo:", resumo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
