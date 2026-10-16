"""Score de SENADOR (0-100) — próprio, porque senador não é deputado.

O score dos deputados estaduais mede emenda JÁ executada nas cidades do PFC.
Senador eleito em 2026 ainda não tem emenda como senador, e a base dele é o
estado inteiro. Então o score olha duas coisas, só de dado público, meio a meio:

  território  50  quanto da votação dele veio das cidades do PFC e vizinhas,
                  comparado ao peso dessas cidades no total de votos do estado
                  (TSE, votação por município — arquivo baixado à mão);
  histórico   50  o score que ele JÁ tem no cargo anterior, no levantamento
                  do dashboard (ALESP ou Câmara) — reaproveitado, nunca
                  recalculado.
(Até out/2026 havia uma 3ª parte, a nota do Fábio; saiu a pedido: o score
precisa aparecer sem depender de preenchimento manual.)

REGRA DE HONESTIDADE (a mesma do "sem dado ≠ dado ruim"): parte sem dado NÃO
vale zero — fica de fora, e o score é calculado sobre a parte medida, com o
rótulo "parcial". Sem nenhuma parte medida, não há número: "sem dado".

PURO: sem rede, sem Streamlit.
"""
from __future__ import annotations

import csv
import os
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_VOTACAO = os.path.join(BASE, "data", "eleicoes", "votacao_senador_municipio_2026.csv")

PESOS = {"territorio": 50, "historico": 50}
ROTULOS = {"territorio": "Território eleitoral", "historico": "Histórico no cargo anterior"}
# Razão a partir da qual o território vale os pontos cheios: ter, nas nossas
# cidades, o DOBRO da fatia que elas têm no estado. Razão 1,0 = ele foi votado
# aqui na mesma proporção que no resto do estado = metade dos pontos.
RAZAO_TETO = 2.0
FALTA = {
    "territorio": "baixar no TSE a votação por município de 2026 "
                  "(scripts/importar_votacao_municipio_2026.py)",
    "historico": "sem emenda no levantamento do cargo anterior",
}


def norm_municipio(s) -> str:
    """'SANTA BÁRBARA D'OESTE' e 'Santa Bárbara d'Oeste' viram a mesma chave;
    hífen e apóstrofo viram espaço ('BIRITIBA-MIRIM' = 'Biritiba Mirim')."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    for ch in "-'’`":
        s = s.replace(ch, " ")
    return " ".join(s.split())


# ---------------------------------------------------------------- território
def pesos_territorio_padrao() -> dict:
    """{municipio_norm: peso} = cidades do PFC (peso do grupo) + vizinhas da
    mesma Região Imediata (peso-base x fator_vizinho). Lê a MESMA configuração
    do ranking de emendas (config/pfc_municipios.toml) — um território só."""
    try:
        from src import emendas
        cfg = emendas.carregar_config_pfc()
        viz = emendas.mapear_vizinhos(cfg, emendas.carregar_regioes_ibge())
    except Exception:
        return {}
    fator = float(cfg.get("score_expansao", {}).get("fator_vizinho", 0.45))
    pesos = {norm_municipio(m): float(p) for m, p in cfg["peso_por_municipio"].items()}
    for m, base in viz.items():
        pesos.setdefault(norm_municipio(m), float(base) * fator)
    return pesos


def carregar_votacao(caminho: str | None = None) -> dict:
    """{'por_candidato': {numero: {nome_urna, votos: {mun_norm: n}}},
        'totais': {mun_norm: n}}. Sem arquivo -> {} (território fica sem dado)."""
    caminho = caminho or CSV_VOTACAO
    try:
        with open(caminho, encoding="utf-8-sig", newline="") as f:
            linhas = list(csv.DictReader(f))
    except (FileNotFoundError, OSError):
        return {}
    por_cand, totais = {}, {}
    for r in linhas:
        mun, num = norm_municipio(r.get("municipio")), str(r.get("numero", "")).strip()
        try:
            v = int(float(r.get("votos") or 0))
        except ValueError:
            continue
        if not mun or not num:
            continue
        c = por_cand.setdefault(num, {"nome_urna": r.get("nome_urna", ""), "votos": {}})
        c["votos"][mun] = c["votos"].get(mun, 0) + v
        totais[mun] = totais.get(mun, 0) + v
    return {"por_candidato": por_cand, "totais": totais} if por_cand else {}


def indice_territorial(votos_cand: dict, totais: dict, pesos: dict) -> dict | None:
    """Quanto o candidato é mais (ou menos) votado no território do PFC do que
    o território pesa no estado. Ponderado pelo peso de cada cidade.

    razao = (fatia dos votos DELE vinda do território) / (fatia dos votos de
    TODOS vinda do território). 1,0 = proporcional; 2,0 = o dobro.
    """
    total_cand, total_geral = sum(votos_cand.values()), sum(totais.values())
    if not total_cand or not total_geral or not pesos:
        return None
    no_terr_cand = sum(v * pesos[m] for m, v in votos_cand.items() if m in pesos)
    no_terr_geral = sum(v * pesos[m] for m, v in totais.items() if m in pesos)
    if not no_terr_geral:
        return None
    fatia_cand = no_terr_cand / total_cand
    fatia_geral = no_terr_geral / total_geral
    top = sorted(((m, v) for m, v in votos_cand.items() if m in pesos and pesos[m] >= 1.0),
                 key=lambda x: -x[1])[:3]
    return {"razao": fatia_cand / fatia_geral, "fatia_cand_pct": 100 * fatia_cand,
            "fatia_geral_pct": 100 * fatia_geral,
            "votos_pfc": sum(v for m, v in votos_cand.items() if pesos.get(m, 0) >= 1.0),
            "cidades_top": top}


def pontos_territorio(razao: float) -> float:
    return PESOS["territorio"] * min(max(razao, 0.0), RAZAO_TETO) / RAZAO_TETO


# ---------------------------------------------------------------- score
def calcular(territorio: dict | None, historico_score: float | None,
             historico_fonte: str = "") -> dict:
    """O score de um senador. Cada argumento None = parte SEM DADO.

    Devolve {score, status, medido, partes, falta}:
      score   int 0-100 sobre os pontos medidos, ou None (nada medido);
      status  'completo' | 'parcial' | 'sem_dado';
      medido  quantos dos 100 pontos foram medidos;
      partes  [{parte, rotulo, peso, pontos, texto}] — pontos None = sem dado.
    """
    partes = []
    if territorio:
        r = territorio["razao"]
        partes.append(("territorio", pontos_territorio(r),
                       f"{territorio['fatia_cand_pct']:.1f}% dos votos dele vieram do território "
                       f"do PFC, que tem {territorio['fatia_geral_pct']:.1f}% dos votos do estado "
                       f"(razão {r:.2f}; 1,00 = proporcional)".replace(".", ",")))
    else:
        partes.append(("territorio", None, "sem dado: " + FALTA["territorio"]))
    if historico_score is not None:
        partes.append(("historico", PESOS["historico"] * min(max(historico_score, 0), 100) / 100,
                       f"score {historico_score:.0f} no levantamento {historico_fonte}".strip()))
    else:
        partes.append(("historico", None, "sem dado: " + FALTA["historico"]))

    medidas = [(k, p) for k, p, _ in partes if p is not None]
    medido = sum(PESOS[k] for k, _ in medidas)
    falta = [ROTULOS[k] for k, p, _ in partes if p is None]
    if medidas:
        score = round(100 * sum(p for _, p in medidas) / medido)
        status = "completo" if medido == 100 else "parcial"
    else:
        score, status = None, "sem_dado"
    return {"score": score, "status": status, "medido": medido, "falta": falta,
            "partes": [{"parte": k, "rotulo": ROTULOS[k], "peso": PESOS[k],
                        "pontos": None if p is None else round(p, 1), "texto": t}
                       for k, p, t in partes]}


def rotulo_score(s: dict) -> str:
    """'72' · '17 (parcial: só histórico no cargo anterior)' · 'sem dado'."""
    if s["score"] is None:
        return "sem dado"
    if s["status"] == "parcial":
        so = [x["rotulo"].lower() for x in s["partes"] if x["pontos"] is not None]
        return f"{s['score']} (parcial: só {' e '.join(so)})"
    return str(s["score"])
