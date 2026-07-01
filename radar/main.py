"""
Orquestração do Radar de Descoberta.

Fluxo: fontes-âncora (Camada 1) + fontes genéricas (Camada 2) + descoberta
(Camada 3, em paralelo) -> pontuação -> filtro (>=40) -> deduplicação ->
gravação em Novidades_pendentes (ou preview_local.csv sem credenciais).

Rodar:  python -m radar.main
Credenciais (GitHub Secrets / ambiente): GCP_SERVICE_ACCOUNT_JSON, SPREADSHEET_KEY
"""
from __future__ import annotations

import csv
import datetime
import json
import os
import threading

from radar import dedup, descoberta
from radar.fontes_ancora import ANCORA_URLS, FONTES
from radar.fontes_genericas import dominio_de, extrair_generico
from radar.scorer import avaliar_sinal, pontuacao

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config_fontes.json")
PREVIEW_CSV = os.path.join(BASE, "preview_local.csv")
FILTRADOS_CSV = os.path.join(BASE, "log_filtrados.csv")
DESCARTADO_CSV = os.path.join(BASE, "log_descartado_sem_sinal.csv")
CANDIDATAS_CSV = os.path.join(BASE, "fontes_candidatas.csv")

LIMIAR_FILA = 45  # score_total mínimo para entrar na fila
ABA = "Novidades_pendentes"
# Mesmo cabeçalho de src/dados.py (mantido aqui para não importar Streamlit).
HEADERS = ["Data", "Fonte", "Título", "Descrição", "Score Aderência",
           "Prazo", "Valor estimado", "Link da fonte", "Status aprovação"]


# --------------------------------------------------------------------------- #
# Coleta (com isolamento por fonte)
# --------------------------------------------------------------------------- #
def coletar_ancoras():
    """Roda as 18 fontes-âncora isoladas. Devolve (itens, n_ok, falhas)."""
    itens, falhas, n_ok = [], {}, 0
    for nome, func in FONTES.items():
        try:
            achados = func() or []
            itens.extend(achados)
            n_ok += 1
        except Exception as e:  # falha em uma nunca derruba as outras
            falhas[nome] = f"{type(e).__name__}: {str(e)[:80]}"
    return itens, n_ok, falhas


def coletar_genericas():
    """Roda as fontes ativas de config_fontes.json via extrator genérico."""
    itens, n_ok, falhas = [], 0, {}
    for entrada in _ler_config():
        nome = entrada.get("nome", entrada.get("url", "?"))
        url = entrada.get("url", "")
        try:
            itens.extend(extrair_generico(url) or [])
            n_ok += 1
        except Exception as e:
            falhas[nome] = f"{type(e).__name__}: {str(e)[:80]}"
    return itens, n_ok, falhas


def _ler_config():
    """Entradas de config válidas e ativas (ignora exemplos/desativadas)."""
    try:
        with open(CONFIG, encoding="utf-8") as f:
            dados = json.load(f)
    except Exception:
        return []
    ativas = []
    for e in dados if isinstance(dados, list) else []:
        url = str(e.get("url", ""))
        if e.get("ativo", True) and url.startswith("http") and "exemplo.org" not in url:
            ativas.append(e)
    return ativas


# --------------------------------------------------------------------------- #
# Gravação
# --------------------------------------------------------------------------- #
def _conectar_worksheet():
    """Worksheet 'Novidades_pendentes' via credenciais de ambiente, ou None."""
    js = os.environ.get("GCP_SERVICE_ACCOUNT_JSON")
    key = os.environ.get("SPREADSHEET_KEY")
    if not js or not key:
        return None
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        info = json.loads(js)
        escopos = ["https://www.googleapis.com/auth/spreadsheets",
                   "https://www.googleapis.com/auth/drive"]
        cliente = gspread.authorize(Credentials.from_service_account_info(info, scopes=escopos))
        sh = cliente.open_by_key(key)
        try:
            ws = sh.worksheet(ABA)
        except Exception:
            ws = sh.add_worksheet(title=ABA, rows=1000, cols=len(HEADERS))
            ws.append_row(HEADERS)
        if not ws.row_values(1):
            ws.append_row(HEADERS)
        return ws
    except Exception as e:
        print(f"  ! Falha ao conectar no Google Sheets: {type(e).__name__}: {str(e)[:90]}")
        return None


def _linha(op) -> list:
    return [
        op.get("data_encontrada", datetime.date.today().isoformat()),
        op.get("fonte", ""), op.get("titulo", ""), op.get("descricao", ""),
        op.get("score_aderencia", ""), op.get("prazo", ""),
        op.get("valor_estimado", ""), op.get("url", ""), "Pendente de revisão",
    ]


def _existentes_da_planilha(ws):
    try:
        return [{"titulo": r.get("Título", ""), "url": r.get("Link da fonte", "")}
                for r in ws.get_all_records()]
    except Exception:
        return []


def _salvar_csv(caminho, cabecalho, linhas):
    try:
        with open(caminho, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(cabecalho)
            w.writerows(linhas)
    except Exception as e:
        print(f"  ! Não consegui gravar {os.path.basename(caminho)}: {e}")


# --------------------------------------------------------------------------- #
# Orquestração
# --------------------------------------------------------------------------- #
def executar():
    print("== Radar de Descoberta ==")

    # Camada 3 em paralelo (não bloqueia a coleta principal).
    conhecidos = {dominio_de(u) for u in ANCORA_URLS}
    conhecidos |= {dominio_de(e.get("url", "")) for e in _ler_config()}
    resultado_desc = {"n": 0}

    def _rodar_descoberta():
        try:
            resultado_desc["n"] = descoberta.descobrir_candidatas(
                ANCORA_URLS, conhecidos, CANDIDATAS_CSV)
        except Exception:
            resultado_desc["n"] = 0

    t_desc = threading.Thread(target=_rodar_descoberta, daemon=True)
    t_desc.start()

    # Camadas 1 e 2.
    ancora_itens, ancora_ok, ancora_falhas = coletar_ancoras()
    generica_itens, generica_ok, generica_falhas = coletar_genericas()
    brutos = ancora_itens + generica_itens

    # PRÉ-FILTRO DE SINAL — descarta lixo institucional ANTES de pontuar.
    # (fontes de contexto-edital ganham passe livre; exclusão sempre vale.)
    com_sinal, descartados = [], []
    for op in brutos:
        passa, motivo = avaliar_sinal(op)
        if passa:
            com_sinal.append(op)
        else:
            descartados.append((op, motivo))

    # Pontuação + separação (só o que passou no filtro de sinal).
    fila, filtradas = [], []
    for op in com_sinal:
        op.update(pontuacao(op))
        (fila if op["score_total"] >= LIMIAR_FILA else filtradas).append(op)
    fila.sort(key=lambda o: o["score_total"], reverse=True)

    # Deduplicação contra a fila existente.
    ws = _conectar_worksheet()
    existentes = _existentes_da_planilha(ws) if ws else []
    unicas, n_dups = dedup.deduplicar(fila, existentes)

    # Gravação (Sheets ou preview local).
    destino = "Google Sheets (Novidades_pendentes)"
    if ws is not None:
        for op in unicas:
            try:
                ws.append_row(_linha(op), value_input_option="USER_ENTERED")
            except Exception as e:
                print(f"  ! Falha ao gravar '{op.get('titulo','')[:40]}': {e}")
    else:
        destino = "preview_local.csv (sem credenciais Google)"
        _salvar_csv(PREVIEW_CSV, HEADERS, [_linha(o) for o in unicas])

    # Log de filtradas (passaram no sinal, mas score < limiar).
    _salvar_csv(FILTRADOS_CSV, ["data", "fonte", "titulo", "url", "score_total", "motivo"],
                [[o.get("data_encontrada", ""), o.get("fonte", ""), o.get("titulo", ""),
                  o.get("url", ""), o.get("score_total", ""), o.get("motivo", "")]
                 for o in filtradas])

    # Log de descartados no pré-filtro de sinal (auditoria do filtro).
    _salvar_csv(DESCARTADO_CSV, ["data", "fonte", "titulo", "url", "motivo"],
                [[o.get("data_encontrada", ""), o.get("fonte", ""), o.get("titulo", ""),
                  o.get("url", ""), motivo] for o, motivo in descartados])

    # Aguarda a descoberta terminar (com folga) sem travar o processo.
    t_desc.join(timeout=90)

    _resumo(ancora_ok, generica_ok, brutos, com_sinal, descartados, unicas, filtradas,
            {**ancora_falhas, **generica_falhas}, resultado_desc["n"], destino)


def _resumo(ancora_ok, generica_ok, brutos, com_sinal, descartados, unicas, filtradas,
            falhas, n_cand, destino):
    print("\n---------------- RESUMO ----------------")
    print(f"{ancora_ok} fontes-âncora + {generica_ok} fontes genéricas varridas")
    print(f"{len(brutos)} itens extraídos · {len(com_sinal)} com sinal de oportunidade · "
          f"{len(descartados)} descartados sem sinal")
    print(f"{len(unicas)} na fila (score >= {LIMIAR_FILA}) · {len(filtradas)} filtradas (score baixo)")
    print(f"Destino da fila: {destino}")
    print(f"{n_cand} novas fontes candidatas descobertas -> "
          f"{os.path.basename(CANDIDATAS_CSV)}")
    if falhas:
        print(f"Falhas por fonte ({len(falhas)}):")
        for nome, err in falhas.items():
            print(f"   - {nome}: {err}")
    else:
        print("Nenhuma falha de fonte.")
    print("----------------------------------------")


if __name__ == "__main__":
    executar()
