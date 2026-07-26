"""
Geração dos PDFs do **Relatório de Prioridades** (Captação e Emendas).

Esta é uma camada de APRESENTAÇÃO apenas: recebe listas de dicionários já
prontas — o app.py faz a coleta dos dados reais e, no caso da Captação, já
aplica a regra de acurácia de datas (regra 3: data não confiável vira
"prazo a confirmar", nunca um número de dias que pode estar errado). Aqui só
desenhamos o PDF e devolvemos os bytes, mantendo o app desacoplado do reportlab.

Biblioteca: ReportLab (Python puro, sem dependência de sistema — roda igual no
Windows e no deploy do Streamlit Cloud). Saída em memória (BytesIO), pronta para
o st.download_button.

Funções públicas:
    pdf_captacao(itens, gerado_em, resumo=None) -> bytes
    pdf_emendas(territorio, expansao, gerado_em, resumo=None) -> bytes
"""
from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, KeepTogether,
)

# Identidade de marca (mesmas cores do design system do app).
_AMBAR = colors.HexColor("#E8873A")   # Captação
_VIOLETA = colors.HexColor("#8B7BF0")  # Emendas
_TINTA = colors.HexColor("#1A1D23")
_CINZA = colors.HexColor("#6B7688")
_LINHA = colors.HexColor("#D8DCE3")
_ZEBRA = colors.HexColor("#F5F6F8")
_URGENTE = colors.HexColor("#C0442B")  # prazo urgente (impresso, tom mais escuro)
_VERDE = colors.HexColor("#2E9E5B")

_MARGEM = 16 * mm


# --------------------------------------------------------------------------- #
# Estilos de texto
# --------------------------------------------------------------------------- #
def _estilos():
    base = getSampleStyleSheet()["Normal"]
    base.fontName = "Helvetica"
    est = {
        "titulo": ParagraphStyle("titulo", parent=base, fontName="Helvetica-Bold",
                                  fontSize=17, leading=20, textColor=_TINTA),
        "sub": ParagraphStyle("sub", parent=base, fontSize=9.5, leading=13,
                              textColor=_CINZA),
        "secao": ParagraphStyle("secao", parent=base, fontName="Helvetica-Bold",
                                fontSize=12, leading=15, textColor=_TINTA,
                                spaceBefore=6, spaceAfter=2),
        "secao_cap": ParagraphStyle("secao_cap", parent=base, fontSize=8.5,
                                    leading=11, textColor=_CINZA, spaceAfter=6),
        "th": ParagraphStyle("th", parent=base, fontName="Helvetica-Bold",
                             fontSize=7.5, leading=9, textColor=colors.white),
        "cel": ParagraphStyle("cel", parent=base, fontSize=8.5, leading=11,
                              textColor=_TINTA),
        "cel_b": ParagraphStyle("cel_b", parent=base, fontName="Helvetica-Bold",
                                fontSize=8.5, leading=11, textColor=_TINTA),
        "cel_dim": ParagraphStyle("cel_dim", parent=base, fontSize=8, leading=10,
                                  textColor=_CINZA),
        "num": ParagraphStyle("num", parent=base, fontName="Helvetica-Bold",
                              fontSize=9, leading=11, textColor=_TINTA,
                              alignment=TA_RIGHT),
        "vazio": ParagraphStyle("vazio", parent=base, fontSize=9.5, leading=13,
                               textColor=_CINZA, alignment=TA_LEFT),
    }
    return est


def _P(txt, estilo):
    """Paragraph seguro (nunca quebra com None/número)."""
    return Paragraph("" if txt is None else str(txt), estilo)


# --------------------------------------------------------------------------- #
# Documento: cabeçalho de marca (1ª página) + rodapé em todas
# --------------------------------------------------------------------------- #
def _doc(buffer, cor_marca, titulo, gerado_em):
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=_MARGEM, rightMargin=_MARGEM,
        topMargin=_MARGEM, bottomMargin=18 * mm,
        title=titulo, author="Programa Futuro Cientista",
    )

    def _rodape(canvas, d):
        canvas.saveState()
        canvas.setStrokeColor(_LINHA)
        canvas.setLineWidth(0.5)
        y = 12 * mm
        canvas.line(_MARGEM, y, A4[0] - _MARGEM, y)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(_CINZA)
        canvas.drawString(_MARGEM, y - 4 * mm,
                          "Programa Futuro Cientista · UFSCar Sorocaba · uso interno da equipe de captação")
        canvas.drawRightString(A4[0] - _MARGEM, y - 4 * mm,
                               "Gerado em %s · pág. %d" % (gerado_em, d.page))
        canvas.restoreState()

    return doc, _rodape


def _cabecalho(cor_marca, titulo, subtitulo, gerado_em, est):
    """Faixa de topo: barra de acento + nome do PFC + título + data de geração."""
    faixa = Table([[""]], colWidths=[A4[0] - 2 * _MARGEM], rowHeights=[3])
    faixa.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), cor_marca)]))

    marca = _P("PROGRAMA FUTURO CIENTISTA", ParagraphStyle(
        "marca", fontName="Helvetica-Bold", fontSize=8.5, leading=11,
        textColor=cor_marca, spaceBefore=8))
    cab = [faixa, Spacer(1, 6), marca, _P(titulo, est["titulo"]),
           _P(subtitulo, est["sub"]),
           _P("Gerado em %s" % gerado_em, est["sub"]),
           Spacer(1, 10)]
    return cab


# --------------------------------------------------------------------------- #
# CAPTAÇÃO — oportunidades por urgência de prazo
# --------------------------------------------------------------------------- #
def pdf_captacao(itens: list[dict], gerado_em: str, resumo: str | None = None) -> bytes:
    """PDF das oportunidades prioritárias da Captação, ordenadas por urgência.

    Cada item (montado pelo app, já com a regra de acurácia aplicada):
        {nome, instituicao, valor, data_final, dias_txt, urgente(bool),
         confiavel(bool)}
    'data_final'/'dias_txt' já vêm como "a confirmar"/"prazo a confirmar"
    quando a data não é confiável — este módulo apenas imprime o que recebe.
    """
    est = _estilos()
    buffer = BytesIO()
    doc, rodape = _doc(buffer, _AMBAR, "Relatório de Prioridades · Captação", gerado_em)

    story = _cabecalho(_AMBAR, "Relatório de Prioridades — Captação",
                       "Editais e oportunidades ordenados por urgência de prazo",
                       gerado_em, est)
    if resumo:
        story.append(_P(resumo, est["secao_cap"]))

    if not itens:
        story.append(_P("Nenhuma oportunidade com prazo próximo no momento.", est["vazio"]))
        doc.build(story, onFirstPage=rodape, onLaterPages=rodape)
        return buffer.getvalue()

    cabecalho = [_P("#", est["th"]), _P("OPORTUNIDADE / INSTITUIÇÃO", est["th"]),
                 _P("VALOR", est["th"]), _P("DATA FINAL", est["th"]),
                 _P("PRAZO", est["th"])]
    linhas = [cabecalho]
    estilo_linhas = []
    for i, it in enumerate(itens, start=1):
        nome = _P(it.get("nome") or "(sem título)", est["cel_b"])
        inst = _P(it.get("instituicao") or "—", est["cel_dim"])
        bloco_nome = Table([[nome], [inst]], colWidths=[None])
        bloco_nome.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
        confiavel = it.get("confiavel", True)
        data_st = est["cel"] if confiavel else est["cel_dim"]
        prazo_style = est["cel_dim"]
        if it.get("urgente"):
            prazo_style = ParagraphStyle("urg", parent=est["cel_b"], textColor=_URGENTE)
        elif confiavel:
            prazo_style = est["cel"]
        linhas.append([
            _P(i, est["num"]), bloco_nome,
            _P(it.get("valor") or "—", est["cel"]),
            _P(it.get("data_final") or "a confirmar", data_st),
            _P(it.get("dias_txt") or "prazo a confirmar", prazo_style),
        ])
        if i % 2 == 0:
            estilo_linhas.append(("BACKGROUND", (0, i), (-1, i), _ZEBRA))

    largura = A4[0] - 2 * _MARGEM
    tabela = Table(linhas, colWidths=[largura * x for x in (0.05, 0.44, 0.17, 0.16, 0.18)],
                   repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _TINTA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, _LINHA),
    ] + estilo_linhas))
    story.append(tabela)
    story.append(Spacer(1, 8))
    story.append(_P("As oportunidades sem data confiável aparecem como "
                    "\"prazo a confirmar\" — confirme na página oficial antes de agir. "
                    "Uma data errada é pior que nenhuma.", est["secao_cap"]))

    doc.build(story, onFirstPage=rodape, onLaterPages=rodape)
    return buffer.getvalue()


# --------------------------------------------------------------------------- #
# EMENDAS — deputados prioritários a abordar (território primeiro)
# --------------------------------------------------------------------------- #
def _tabela_emendas(secao_itens, est, cor):
    """Uma tabela de deputados. Autorizado e pago SEMPRE separados (nunca somados)."""
    cabecalho = [_P("#", est["th"]), _P("DEPUTADO", est["th"]),
                 _P("MUNICÍPIOS DO PFC", est["th"]),
                 _P("EDUCAÇÃO / SOCIAL", est["th"]), _P("SCORE", est["th"]),
                 _P("CONTATO OFICIAL (ALESP)", est["th"])]
    linhas = [cabecalho]
    estilo_linhas = []
    for i, d in enumerate(secao_itens, start=1):
        dep = _P(d.get("deputado") or "—", est["cel_b"])
        partido = _P(d.get("partido") or "—", est["cel_dim"])
        bloco_dep = Table([[dep], [partido]])
        bloco_dep.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))

        valor = ("<b>Aut.</b> %s<br/><b>Pago</b> %s"
                 % (d.get("autorizado") or "—", d.get("pago") or "—"))
        contato = "<br/>".join(x for x in (
            d.get("email") or "", d.get("telefone") or "") if x and x != "não encontrado") \
            or "não informado"

        linhas.append([
            _P(i, est["num"]), bloco_dep,
            _P(d.get("municipios") or "—", est["cel"]),
            _P(valor, est["cel"]),
            _P(d.get("score") or "—", est["cel_b"]),
            _P(contato, est["cel_dim"]),
        ])
        if i % 2 == 0:
            estilo_linhas.append(("BACKGROUND", (0, i), (-1, i), _ZEBRA))

    largura = A4[0] - 2 * _MARGEM
    tabela = Table(linhas,
                   colWidths=[largura * x for x in (0.05, 0.20, 0.22, 0.19, 0.08, 0.26)],
                   repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _TINTA),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, _LINHA),
    ] + estilo_linhas))
    return tabela


def pdf_emendas(territorio: list[dict], expansao: list[dict], gerado_em: str,
                resumo: str | None = None) -> bytes:
    """PDF dos deputados prioritários a abordar (território primeiro, depois expansão).

    Cada item (montado pelo app a partir do levantamento):
        {deputado, partido, municipios, autorizado, pago, score,
         email, telefone}
    Autorizado e pago vêm já formatados e são impressos SEPARADOS (nunca somados).
    """
    est = _estilos()
    buffer = BytesIO()
    doc, rodape = _doc(buffer, _VIOLETA, "Relatório de Prioridades · Emendas", gerado_em)

    story = _cabecalho(_VIOLETA, "Relatório de Prioridades — Emendas Parlamentares",
                       "Deputados a abordar, do levantamento de execução de emendas (2023–2025)",
                       gerado_em, est)
    if resumo:
        story.append(_P(resumo, est["secao_cap"]))

    story.append(_P("1. Abordar já — atuam no território do PFC", est["secao"]))
    story.append(_P("Deputados que já financiam educação/social dentro dos municípios do "
                    "PFC. Ação imediata.", est["secao_cap"]))
    if territorio:
        story.append(_tabela_emendas(territorio, est, _VIOLETA))
    else:
        story.append(_P("Ninguém no território ainda.", est["vazio"]))

    story.append(Spacer(1, 14))
    story.append(_P("2. Cortejar — alto volume, ainda fora do território", est["secao"]))
    story.append(_P("Alto alinhamento e volume no estado, ainda fora dos nossos municípios "
                    "(ou só de raspão). Alvo de cortejo.", est["secao_cap"]))
    if expansao:
        story.append(_tabela_emendas(expansao, est, _VIOLETA))
    else:
        story.append(_P("Sem candidatos de expansão no momento.", est["vazio"]))

    story.append(Spacer(1, 8))
    story.append(_P("Valores da execução real de emendas estaduais 2023–2025 (Transparência "
                    "SP). Autorizado e pago são exibidos separados — nunca somados. Contato "
                    "oficial da ALESP (gabinete), não o contato pessoal do relacionamento.",
                    est["secao_cap"]))

    doc.build(story, onFirstPage=rodape, onLaterPages=rodape)
    return buffer.getvalue()
