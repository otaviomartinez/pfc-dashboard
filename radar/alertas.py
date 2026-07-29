"""
Alerta de editais por e-mail — passo pós-gravação do radar.

Lê os inscritos (aba 'Inscritos Alerta') e a fila (aba 'Novidades_pendentes'),
seleciona editais com data CONFIÁVEL a <=14 dias do prazo, ainda não vencidos e
ainda NÃO alertados (coluna 'Alertado em' vazia), e manda UM e-mail-resumo por
inscrito, ordenado por urgência. Marca 'Alertado em' com a data para não repetir.

ENVIO SEMANAL: o radar roda todo dia (06:00) para descobrir editais novos, mas o
e-mail só sai às SEGUNDAS-FEIRAS, pelo calendário de BRASÍLIA (o Actions roda em
UTC; usar a data UTC dispararia no dia errado perto da virada). Nos outros dias o
passo não monta nem envia nada — e, como não marca 'Alertado em', os editais
elegíveis ficam guardados e entram no e-mail da segunda seguinte.

INVARIANTE CRÍTICA: nada aqui pode derrubar o radar. `executar_alertas` é
blindada por try/except (e o main.py ainda a chama dentro de outro try/except);
falta de secrets, falha de SMTP ou erro de rede => pula silenciosamente,
devolvendo um resumo com o motivo. O radar NUNCA falha por causa do e-mail.

Credenciais (só ambiente / GitHub Secrets, NUNCA no git):
    GMAIL_SENDER          -> e-mail remetente (conta Gmail)
    GMAIL_APP_PASSWORD    -> Senha de App do Gmail (16 caracteres)
"""
from __future__ import annotations

import datetime
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.utils import formataddr

ABA_PENDENTES = "Novidades_pendentes"
ABA_INSCRITOS = "Inscritos Alerta"
COL_ALERTADO = "Alertado em"
ALERTA_MAX_DIAS = 14  # avisa quando faltarem <= 14 dias (e ainda não venceu)
DIA_DE_ENVIO = 0      # 0 = segunda-feira (datetime.date.weekday())
TZ_BRASILIA = "America/Sao_Paulo"


# --------------------------------------------------------------------------- #
# Dia do envio (semanal, no calendário de Brasília)
# --------------------------------------------------------------------------- #
def hoje_brasilia() -> datetime.date:
    """Data de HOJE no fuso de Brasília.

    O radar roda no GitHub Actions em UTC: às 06:00 de Brasília já são 09:00 UTC
    do mesmo dia, mas depender da data UTC deixaria o envio a um passo de cair no
    dia errado se o horário do cron mudar. Sem a base de fusos (tzdata), cai no
    offset fixo -03:00, que é o de Brasília o ano todo desde 2019 (sem horário
    de verão)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo(TZ_BRASILIA)).date()
    except Exception:
        return (datetime.datetime.now(datetime.timezone.utc)
                - datetime.timedelta(hours=3)).date()


def e_dia_de_envio(hoje: datetime.date | None = None) -> bool:
    """True só na SEGUNDA-FEIRA (calendário de Brasília) — o e-mail é semanal."""
    hoje = hoje or hoje_brasilia()
    return hoje.weekday() == DIA_DE_ENVIO


# --------------------------------------------------------------------------- #
# Seleção (função pura — testável sem rede)
# --------------------------------------------------------------------------- #
def _dias_restantes(prazo_iso, hoje: datetime.date):
    """Dias até o prazo a partir do ISO (AAAA-MM-DD) que o radar grava; None se
    o prazo não for uma data confiável (vazio / 'a confirmar' / não-ISO)."""
    try:
        d = datetime.date.fromisoformat(str(prazo_iso or "").strip())
    except ValueError:
        return None
    return (d - hoje).days


def selecionar_editais(registros: list[dict], hoje: datetime.date | None = None) -> list[dict]:
    """Editais a alertar HOJE, ordenados por urgência (menos dias primeiro).

    Regras (todas obrigatórias): status 'Pendente de revisão'; data CONFIÁVEL
    (Prazo é ISO válido) a 0..ALERTA_MAX_DIAS dias (não vencido); ainda NÃO
    alertado (coluna 'Alertado em' vazia). Pura: não toca em rede/Sheets.
    """
    hoje = hoje or hoje_brasilia()
    selec = []
    for r in registros:
        if str(r.get("Status aprovação", "")).strip().lower() != "pendente de revisão":
            continue
        if str(r.get(COL_ALERTADO, "")).strip():
            continue  # já alertado — não repete
        dias = _dias_restantes(r.get("Prazo", ""), hoje)
        if dias is None or not (0 <= dias <= ALERTA_MAX_DIAS):
            continue
        selec.append((dias, r))
    selec.sort(key=lambda x: x[0])
    return [{"titulo": str(r.get("Título", "")).strip() or "(sem título)",
             "dias": dias,
             "prazo": str(r.get("Prazo", "")).strip(),
             "valor": str(r.get("Valor estimado", "")).strip(),
             "link": str(r.get("Link da fonte", "")).strip(),
             "fonte": str(r.get("Fonte", "")).strip(),
             "_row": r} for dias, r in selec]


def _fmt_prazo(prazo_iso: str) -> str:
    try:
        return datetime.date.fromisoformat(str(prazo_iso or "").strip()).strftime("%d/%m/%Y")
    except ValueError:
        return str(prazo_iso or "").strip() or "?"


def montar_email(editais: list[dict], hoje: datetime.date | None = None) -> tuple[str, str]:
    """(assunto, corpo) do e-mail-resumo. Um item por linha, urgência primeiro."""
    hoje = hoje or hoje_brasilia()
    n = len(editais)
    plural = "edital" if n == 1 else "editais"
    assunto = f"[PFC] {n} {plural} com prazo em até {ALERTA_MAX_DIAS} dias"
    linhas = [f"Editais de captação com prazo próximo "
              f"(radar de {hoje.strftime('%d/%m/%Y')}):", ""]
    for e in editais:
        urg = "vence HOJE" if e["dias"] == 0 else f"faltam {e['dias']} dia(s)"
        item = f"• {e['titulo']} — {urg} (prazo {_fmt_prazo(e['prazo'])})"
        if e["valor"]:
            item += f" — {e['valor']}"
        linhas.append(item)
        if e["fonte"]:
            linhas.append(f"  Fonte: {e['fonte']}")
        if e["link"]:
            linhas.append(f"  {e['link']}")
        linhas.append("")
    linhas.append("— Radar de Captação do PFC. Para sair da lista, use o botão "
                  "\"Sair da lista\" no painel de Captação.")
    return assunto, "\n".join(linhas)


# --------------------------------------------------------------------------- #
# Envio (Gmail SMTP) e marcação anti-repetição
# --------------------------------------------------------------------------- #
def _enviar_gmail(sender: str, senha: str, destinatarios: list[str],
                  assunto: str, corpo: str) -> int:
    """Envia um e-mail individual para cada destinatário (não expõe a lista).
    Devolve quantos foram enviados. Exceção sobe para o chamador tratar."""
    enviados = 0
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=30) as s:
        s.login(sender, senha)
        for dest in destinatarios:
            msg = MIMEText(corpo, "plain", "utf-8")
            msg["Subject"] = assunto
            msg["From"] = formataddr(("Radar PFC", sender))
            msg["To"] = dest
            s.sendmail(sender, [dest], msg.as_string())
            enviados += 1
    return enviados


def _ler_inscritos(sh) -> list[str]:
    """E-mails ATIVOS da aba 'Inscritos Alerta' ([] se não existir/erro)."""
    try:
        if ABA_INSCRITOS not in [w.title for w in sh.worksheets()]:
            return []
        registros = sh.worksheet(ABA_INSCRITOS).get_all_records()
    except Exception:
        return []
    ativos = []
    for r in registros:
        email = str(r.get("Email", "")).strip()
        ativo = str(r.get("Ativo", "")).strip().lower()
        if email and ativo not in ("não", "nao", "false", "0", "inativo"):
            ativos.append(email)
    return ativos


def _garantir_coluna_alertado(ws) -> None:
    """Cria a coluna 'Alertado em' no fim do cabeçalho se ainda não existir."""
    cab = ws.row_values(1)
    if COL_ALERTADO not in cab:
        ws.update_cell(1, len(cab) + 1, COL_ALERTADO)


def _marcar_alertados(ws, editais: list[dict], registros: list[dict],
                      hoje: datetime.date) -> int:
    """Escreve a data de hoje na coluna 'Alertado em' de cada edital alertado.
    Casa a linha por IDENTIDADE do dict lido (registros[i] == _row) — sem
    ambiguidade de título/link duplicado. Devolve quantas linhas marcou."""
    import gspread
    _garantir_coluna_alertado(ws)
    cab = [str(c).strip() for c in ws.row_values(1)]
    col_alertado = cab.index(COL_ALERTADO) + 1
    hoje_iso = hoje.isoformat()
    celulas = []
    for e in editais:
        rownum = next((i for i, r in enumerate(registros, start=2) if r is e["_row"]), None)
        if rownum is not None:
            celulas.append(gspread.Cell(rownum, col_alertado, hoje_iso))
    if celulas:
        ws.update_cells(celulas, value_input_option="RAW")
    return len(celulas)


# --------------------------------------------------------------------------- #
# Orquestração blindada
# --------------------------------------------------------------------------- #
def executar_alertas(sh, hoje: datetime.date | None = None, enviar: bool = True,
                     destinatarios_override: list[str] | None = None,
                     ignorar_dia: bool = False) -> dict:
    """Passo de alerta completo. NUNCA levanta exceção.

    sh = objeto Spreadsheet (gspread). Devolve um resumo:
      {selecionados, assunto, corpo, inscritos, enviados, marcados, erro, pulado}

    O e-mail é SEMANAL: fora da segunda-feira (calendário de Brasília) o passo
    não monta nem envia, e não marca nada — os elegíveis esperam a próxima
    segunda. `pulado` diz o motivo quando isso acontece.

    enviar=False  -> modo TESTE: seleciona e monta o e-mail, mas NÃO envia e NÃO
                     marca (não escreve NADA no Sheets — nem a coluna).
    ignorar_dia=True -> só para teste/preview: mostra o e-mail que sairia,
                     mesmo num dia que não é segunda.
    destinatarios_override -> lista de e-mails para teste (ignora os inscritos).
    """
    hoje = hoje or hoje_brasilia()
    resumo = {"selecionados": [], "assunto": "", "corpo": "", "inscritos": 0,
              "enviados": 0, "marcados": 0, "erro": None, "pulado": None,
              "dia_de_envio": e_dia_de_envio(hoje)}
    try:
        ws = sh.worksheet(ABA_PENDENTES)
        registros = ws.get_all_records()
        editais = selecionar_editais(registros, hoje)
        resumo["selecionados"] = editais
        if not editais:
            return resumo  # nada a alertar hoje

        # ENVIO SEMANAL: fora de segunda não monta, não envia e não marca.
        # (ignorar_dia libera só o preview de teste, que nunca escreve.)
        if not resumo["dia_de_envio"] and not ignorar_dia:
            resumo["pulado"] = ("hoje não é segunda-feira — envio semanal; "
                                f"{len(editais)} edital(is) aguardando a próxima")
            return resumo

        assunto, corpo = montar_email(editais, hoje)
        resumo["assunto"], resumo["corpo"] = assunto, corpo

        destinatarios = (destinatarios_override
                         if destinatarios_override is not None else _ler_inscritos(sh))
        resumo["inscritos"] = len(destinatarios)

        if not enviar:
            return resumo  # modo teste: para aqui, sem tocar no Sheets
        if not destinatarios:
            return resumo  # ninguém inscrito -> não marca (tenta de novo amanhã)

        sender = os.environ.get("GMAIL_SENDER", "").strip()
        senha = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
        if not sender or not senha:
            resumo["erro"] = "secrets_ausentes"  # sem credencial -> pula, não marca
            return resumo

        resumo["enviados"] = _enviar_gmail(sender, senha, destinatarios, assunto, corpo)
        # Só marca DEPOIS de enviar com sucesso (senão o alerta se perderia).
        if resumo["enviados"] > 0:
            resumo["marcados"] = _marcar_alertados(ws, editais, registros, hoje)
        return resumo
    except Exception as e:  # noqa: BLE001 — blindagem: o radar não pode cair
        resumo["erro"] = f"{type(e).__name__}: {str(e)[:120]}"
        return resumo
