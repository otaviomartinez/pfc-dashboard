"""Construtor offline do painel Prefeituras.

    python -m src.prefeituras [exercicio]

Consulta o SICONFI para os municípios de config/pfc_prefeituras.toml e grava
data/prefeituras/mde_<ano>.csv. Se a API não responder (rede bloqueada, ente sem
publicação), cai para data/prefeituras_manual/<ano>.csv|xlsx.

Nunca inventa: município sem dado NÃO entra no CSV com zero — ele simplesmente
fica de fora, e o app rotula "sem dado do exercício X".
"""
from __future__ import annotations

import csv
import datetime
import os
import sys

from src.prefeituras import siconfi
from src.prefeituras.config import carregar_municipios

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR_DADOS = os.path.join(BASE, "data", "prefeituras")
COLUNAS = ["cod_ibge", "municipio", "percentual", "valor_aplicado", "receita_base",
           "exercicio", "periodo", "origem"]


def construir_mde(exercicio: int) -> list[dict]:
    """Uma linha por município COM dado. Quem não tem fica de fora (não vira 0)."""
    linhas, sem_dado = [], []
    for m in carregar_municipios():
        itens = siconfi.buscar_rreo(m["cod_ibge"], exercicio, 6, siconfi.ANEXO_MDE)
        mde = siconfi.extrair_mde(itens, exercicio, 6) if itens else None
        origem = "siconfi"
        if mde is None:                                  # degrada para o manual
            mde = siconfi.mde_do_manual(m["cod_ibge"], exercicio)
            origem = "manual"
        if mde is None:
            sem_dado.append(m["nome"])
            continue
        linhas.append({"cod_ibge": m["cod_ibge"], "municipio": m["nome"],
                       "percentual": mde["percentual"],
                       "valor_aplicado": mde.get("valor_aplicado") or "",
                       "receita_base": mde.get("receita_base") or "",
                       "exercicio": mde["exercicio"], "periodo": mde.get("periodo") or "",
                       "origem": origem})
    if sem_dado:
        print(f"  sem dado de MDE ({len(sem_dado)}): {', '.join(sem_dado)}")
        print("  -> o painel vai rotular 'sem dado do exercício "
              f"{exercicio}' para esses. Nenhum foi preenchido com zero.")
    return linhas


def main() -> int:
    exercicio = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.date.today().year - 1
    print(f"== Painel Prefeituras · construindo MDE do exercício {exercicio} ==")
    linhas = construir_mde(exercicio)
    if not linhas:
        # Não grava CSV vazio: ele seria commitado a cada rodada sem acrescentar
        # nada, e o painel já trata ausência de arquivo como "sem dado". Sai com
        # código 1 para o passo aparecer VERMELHO no Actions — sinal visível de
        # que a coleta não trouxe dado, em vez de um arquivo vazio silencioso.
        print("NENHUM dado obtido. Provável causa: rede bloqueada para o Tesouro, "
              "exercício ainda não publicado, ou string de no_anexo desatualizada. "
              "Nada foi gravado; o painel segue em 'sem dado'.")
        return 1
    os.makedirs(DIR_DADOS, exist_ok=True)
    destino = os.path.join(DIR_DADOS, f"mde_{exercicio}.csv")
    with open(destino, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(linhas)
    print(f"{len(linhas)} município(s) com dado -> {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
