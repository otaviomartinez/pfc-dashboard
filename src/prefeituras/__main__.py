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

from src.prefeituras import siconfi, tce
from src.prefeituras.config import carregar_municipios

# A string de `no_anexo` é o ponto frágil: errada, a API devolve 200 com
# items=[] — vazio SILENCIOSO. Testamos variações conhecidas e ficamos com a
# que responder. O mesmo vale para o exercício (o RREO do 6º bimestre de um ano
# só é publicado no começo do ano seguinte, e nem todo município homologa).
# SÓ o Anexo 08 traz o índice de MDE (Receitas e Despesas com Manutenção e
# Desenvolvimento do Ensino). Varrer todos os anexos foi um erro caro: o Anexo
# 02 (Despesas por Função) entrou como se fosse MDE e produziu percentuais
# falsos. Se o 08 não responder, a resposta correta é "sem dado" — NUNCA um
# número de outro demonstrativo.
ANEXOS_MDE = ["RREO-Anexo 08", "RREO-Anexo 8"]
# Estes são só para DIAGNÓSTICO no log (o que a API oferece), nunca usados
# como fonte do percentual.
ANEXOS_DIAGNOSTICO = ["RREO-Anexo 01", "RREO-Anexo 02", "RREO-Anexo 10"]

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR_DADOS = os.path.join(BASE, "data", "prefeituras")
COLUNAS = ["cod_ibge", "municipio", "percentual", "valor_aplicado", "receita_base",
           "exercicio", "periodo", "origem"]


def vocabulario(cod_ibge: str, exercicio: int) -> None:
    """Descobre os nomes de anexo que a API REALMENTE usa, em vez de chutar.

    As linhas de resposta trazem os campos `anexo` e `demonstrativo`. Buscando um
    anexo que sabidamente responde (o 02), lemos dali a grafia exata — se ela for
    "RREO-Anexo 02", nossa grafia está certa e o Anexo 08 está de fato vazio;
    se for outra, achamos o nome certo sem adivinhação.
    """
    itens = siconfi.buscar_rreo(cod_ibge, exercicio, 6, "RREO-Anexo 02", tentativas=1)
    if not itens:
        print("    (o Anexo 02 também não respondeu; sem vocabulário para comparar)")
        return
    anexos = sorted({str(i.get("anexo", "")) for i in itens if i.get("anexo")})
    demos = sorted({str(i.get("demonstrativo", "")) for i in itens if i.get("demonstrativo")})
    print(f"    grafia REAL de anexo nas respostas: {anexos[:5]}")
    print(f"    demonstrativo: {demos[:3]}")


def varrer_anexo_08(cod_ibge: str) -> None:
    """Procura o Anexo 08 em vários exercícios E períodos.

    O MDE é publicado no 6º bimestre, mas se a entidade lançou noutro período a
    busca fixa em 6 nunca acharia. Isto é DIAGNÓSTICO: só relata.
    """
    print("  procurando o Anexo 08 em outros exercícios/períodos…")
    achou = False
    for exe in (2025, 2024, 2023):
        for per in (6, 5, 4, 3, 2, 1):
            n = len(siconfi.buscar_rreo(cod_ibge, exe, per, "RREO-Anexo 08",
                                        tentativas=1) or [])
            if n:
                print(f"    ACHOU: exercício {exe} · período {per} -> {n} linha(s)")
                achou = True
    if not achou:
        print("    nada em 2023-2025, períodos 1-6. O Anexo 08 não está exposto "
              "para este município.")


def sondar(cod_ibge: str, exercicios: list[int]) -> tuple[str, int] | None:
    """Descobre qual (anexo, exercício) a API realmente responde para um ente.

    DIAGNÓSTICO: sem isto, "sem dado para os 11" não distingue rede caída de
    string de anexo errada de exercício não publicado. Roda só para o primeiro
    município — é uma sondagem, não uma varredura.
    """
    print("  sondando o Anexo 08 (o único que traz MDE)…")
    for exe in exercicios:
        for anexo in ANEXOS_MDE:
            # tentativas=1: são ~20 chamadas de sondagem; retry aqui só atrasa
            itens = siconfi.buscar_rreo(cod_ibge, exe, 6, anexo, tentativas=1)
            n = len(itens or [])
            if not n:
                continue
            mde = siconfi.extrair_mde(itens, exe, 6)
            print(f"    exercício {exe} · {anexo!r} -> {n} linha(s) · "
                  f"MDE={'SIM' if mde else 'não'}")
            if mde:
                return anexo, exe
            # não achou o percentual: mostra as CONTAS que interessam, para eu
            # saber onde mora o MDE (nomes vistos no log, não supostos).
            alvo = ("ensino", "educac", "mde", "manuten", "imposto")
            achadas, outras = [], []
            for it in itens:
                r, c, v = siconfi._campos(it)
                linha = f"{r[:46]!r}/{c[:24]!r}={v}"
                if any(t in r.lower() for t in alvo):
                    if linha not in achadas:
                        achadas.append(linha)
                elif len(outras) < 3:
                    outras.append(linha)
            if achadas:
                print("      CONTAS DE ENSINO/IMPOSTO:", " | ".join(achadas[:8]))
            else:
                print("      amostra:", " | ".join(outras))
    return None


def construir_mde(exercicio: int) -> list[dict]:
    """Uma linha por município COM dado. Quem não tem fica de fora (não vira 0).

    ORDEM DAS FONTES, da mais forte para a mais fraca:
      1. TCE-SP (AUDESP) — índice APURADO pelo Tribunal. O SICONFI não publica
         o Anexo 08 (MDE) para estes municípios, e o TCE publica os 644 de SP.
      2. SICONFI — mantido caso um dia o Anexo 08 apareça.
      3. Arquivo manual — último recurso.
    """
    muns = carregar_municipios()

    # 1) TCE-SP: se tem o exercício pedido, resolve tudo de uma vez.
    dados_tce = tce.carregar(exercicio)
    if not dados_tce:
        for ano in tce.exercicios_disponiveis():
            dados_tce = tce.carregar(ano)
            if dados_tce:
                print(f"  TCE-SP: exercício {exercicio} não existe no arquivo; "
                      f"usando {ano}")
                exercicio = ano
                break
    if dados_tce:
        linhas, sem = [], []
        for mun in muns:
            reg = dados_tce.get(mun["cod_ibge"])
            if not reg:
                sem.append(mun["nome"])
                continue
            linhas.append({"cod_ibge": mun["cod_ibge"], "municipio": mun["nome"],
                           "percentual": reg["percentual"],
                           "valor_aplicado": reg.get("valor_aplicado") or "",
                           "receita_base": "", "exercicio": reg["exercicio"],
                           "periodo": "", "origem": "tce-sp"})
        print(f"  TCE-SP (AUDESP): {len(linhas)} de {len(muns)} municípios, "
              f"exercício {exercicio} — índice APURADO pelo Tribunal")
        if sem:
            print(f"  sem dado no TCE: {', '.join(sem)}")
        if linhas:
            return linhas

    print("  TCE-SP indisponível; tentando SICONFI…")
    anexo, exercicio = siconfi.ANEXO_MDE, exercicio
    achado = sondar(muns[0]["cod_ibge"], [exercicio, exercicio - 1])
    if achado:
        anexo, exercicio = achado
        print(f"  usando {anexo!r} · exercício {exercicio}")
    else:
        # Diagnóstico: mostra o que a API TEM, sem usar como MDE.
        print("  o Anexo 08 não respondeu. O que existe (só informação):")
        for anexo in ANEXOS_DIAGNOSTICO:
            n = len(siconfi.buscar_rreo(muns[0]["cod_ibge"], exercicio, 6,
                                        anexo, tentativas=1) or [])
            print(f"    {anexo!r} -> {n} linha(s)")
        vocabulario(muns[0]["cod_ibge"], exercicio)
        varrer_anexo_08(muns[0]["cod_ibge"])
        print("  -> sem Anexo 08, o MDE fica SEM DADO. Não substituímos por "
              "percentual de outro demonstrativo (foi o erro que inventou "
              "9 municípios 'abaixo do mínimo'). Alternativa sem depender da "
              "API: preencher data/prefeituras_manual/<ano>.csv (ver LEIA-ME).")

    linhas, sem_dado = [], []
    for m in muns:
        itens = siconfi.buscar_rreo(m["cod_ibge"], exercicio, 6, anexo)
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
    if linhas:
        exercicio = int(linhas[0].get("exercicio") or exercicio)
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
