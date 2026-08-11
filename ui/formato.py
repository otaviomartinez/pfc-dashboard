"""
ui/formato.py — helpers de formatação e lógica pura do dashboard PFC.

Passo 2 da modularização (extraído de app.py): 49 funções SEM Streamlit e SEM
os globais de runtime (df, TOTAL, modo_conectado, USER) — puras e testáveis.
Ficaram no app.py as que dependem de runtime e as 4 de I/O do radar
(_n_fontes_radar, _ler_candidatas_avaliadas, _atualizar_status_candidata,
_aprovar_fonte_no_config), cujos caminhos usam __file__ e quebrariam em ui/.

Inclui 7 constantes de DADOS puras que os helpers usam. Não importa nada do
app.py (sem ciclo).
"""
import datetime
import html
import json  # noqa: F401
import re
from urllib.parse import quote

import pandas as pd

from src import dados
from src.dados import (
    COL_EMPRESA, COL_SCORE, COL_SEDE, COL_SEMAFORO, COL_SETOR, COL_STATUS,
    COL_UF, COL_VALVO,
)
from ui.estilos import ICONES, _SVG_TRACO


def svg_icone(nome: str, classe: str = "ic") -> str:
    """SVG inline, para onde eu mesmo monto o HTML (itens de Escopo, cards)."""
    return (f"<svg class='{classe}' viewBox='0 0 24 24' fill='none' stroke='currentColor' "
            f"stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>"
            f"{ICONES[nome]}</svg>")


def _mask_url(nome: str) -> str:
    """SVG -> data URI pronta para mask-image."""
    return f"url(\"data:image/svg+xml,{quote(_SVG_TRACO.format(ICONES[nome]), safe='')}\")"


def _icone_url_cor(nome: str, cor: str) -> str:
    """Como _mask_url, mas o SVG sai COLORIDO (stroke na cor) — para o ícone
    aparecer na cor dentro da pastilha via background-image (não mask)."""
    svg = _SVG_TRACO.replace("stroke='black'", f"stroke='{cor}'").format(ICONES[nome])
    return f"url(\"data:image/svg+xml,{quote(svg, safe='')}\")"


def css_icones_botoes(mapa: dict, rotulos: dict | None = None,
                      cores: dict | None = None) -> str:
    """CSS dos botões da sidebar. mapa: {chave do botão: ícone}.

    Faz três coisas, todas escopadas às chaves do mapa:
      1. desenha o ícone (::before do container de markdown, via mask-image);
      2. no modo ícone, esconde o texto do rótulo;
      3. mostra o nome como tooltip no hover (::after do botão), a partir de
         `rotulos` = {chave: nome}.

    `cores` (opcional) = {chave: cor hex}: transforma o ::before dessas chaves
    numa PASTILHA — caixa arredondada com fundo tênue da cor + ícone na cor. É
    ADITIVO: sem `cores`, a saída é byte-idêntica à de antes (Captação intacta).

    Tudo sai enumerado por seletor, e não numa regra genérica para todo botão
    da sidebar, de propósito: sem mask-image o background:currentColor viraria
    um quadrado sólido, e sem ícone o botão ficaria vazio ao esconder o texto.
    Assim, botão fora do mapa continua com o texto e sem ::before — feio, mas
    visível, que é o modo certo de falhar.
    """
    if not mapa:
        return ""
    alvo = "[data-testid='stMarkdownContainer']"
    linhas = [
        ", ".join(f".st-key-{k} .stButton>button {alvo}" for k in mapa) +
        "{display:flex;align-items:center;gap:11px}",
        ", ".join(f".st-key-{k} .stButton>button {alvo}::before" for k in mapa) +
        "{content:'';width:17px;height:17px;flex:none;background:currentColor;opacity:.92;"
        "-webkit-mask-repeat:no-repeat;mask-repeat:no-repeat;"
        "-webkit-mask-size:contain;mask-size:contain;"
        "-webkit-mask-position:center;mask-position:center}",
        # modo ícone: o texto some (o modo expandido devolve em _SIDEBAR_OPEN_CSS)
        ", ".join(f".st-key-{k} .stButton>button {alvo}>p" for k in mapa) +
        "{display:none}",
    ]
    for chave, icone in mapa.items():
        u = _mask_url(icone)
        linhas.append(f".st-key-{chave} .stButton>button {alvo}::before"
                      f"{{-webkit-mask-image:{u};mask-image:{u}}}")
    # PASTILHA colorida por página (aditivo): vira o ::before numa caixa
    # arredondada com fundo tênue da cor + ícone na cor (background-image
    # colorido, mask cancelado). Vem DEPOIS da regra de mask acima, então
    # sobrescreve (mesma especificidade, vence por ordem). Só sai com `cores`.
    if cores:
        for chave in mapa:
            if chave not in cores:
                continue
            cor = cores[chave]
            u = _icone_url_cor(mapa[chave], cor)
            linhas.append(
                f".st-key-{chave} .stButton>button {alvo}::before"
                f"{{width:26px;height:26px;border-radius:8px;flex:none;"
                f"background-color:{cor}26;"
                f"background-image:{u};background-repeat:no-repeat;"
                f"background-position:center;background-size:16px 16px;"
                f"-webkit-mask:none;mask:none;opacity:1;"
                f"box-shadow:inset 0 0 0 1px {cor}2b}}")
    if rotulos:
        # tooltip: balão em ::after, posicionado ao lado do botão. Depende do
        # overflow:visible declarado no bloco SIDEBAR do CSS global — sem ele
        # os 60px cortam o balão.
        chaves = [k for k in mapa if k in rotulos]
        if chaves:
            linhas += [
                ", ".join(f".st-key-{k} .stButton>button" for k in chaves) +
                "{position:relative}",
                ", ".join(f".st-key-{k} .stButton>button::after" for k in chaves) +
                "{position:absolute;left:calc(100% + 12px);top:50%;transform:translateY(-50%);"
                "background:var(--surface2);color:var(--ink);border:1px solid var(--line2);"
                "border-radius:8px;padding:7px 11px;font-size:12.5px;font-weight:500;"
                "white-space:nowrap;pointer-events:none;z-index:1200;"
                "box-shadow:0 8px 24px rgba(0,0,0,.45);display:none}",
                # display, não opacity/visibility: é o padrão que funciona neste projeto
                ", ".join(f".st-key-{k} .stButton>button:hover::after" for k in chaves) +
                "{display:block}",
            ]
            for chave in chaves:
                nome = str(rotulos[chave]).replace("\\", "").replace('"', "'")
                linhas.append(f'.st-key-{chave} .stButton>button::after{{content:"{nome}"}}')
    return "\n".join(linhas)


def slug(texto: str) -> str:
    """'Funil de negociação' -> 'funil-de-negociacao'.

    As chaves dos botões viram classe CSS (st-key-<chave>), então precisam ser
    ASCII e sem espaço — senão o seletor não casa.
    """
    t = str(texto).lower()
    for de, para in (("ãâáà", "a"), ("éêè", "e"), ("íî", "i"), ("óôõ", "o"),
                     ("úü", "u"), ("ç", "c")):
        for c in de:
            t = t.replace(c, para)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def esc(v) -> str:
    return html.escape("" if v is None else str(v))


def texto_ou(v, padrao: str = "—") -> str:
    s = "" if v is None else str(v).strip()
    return esc(s) if s and s.lower() != "nan" else padrao


def brl(v) -> str:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return "—"
    if n <= 0:
        return "—"
    return "R$ " + f"{n:,.0f}".replace(",", ".")


def brl_curto(v) -> str:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return "—"
    if n <= 0:
        return "—"
    if n >= 1_000_000:
        return ("R$ %.2f mi" % (n / 1_000_000)).replace(".", ",")
    if n >= 1_000:
        return "R$ %.0f mil" % (n / 1_000)
    return "R$ %.0f" % n


def sem_cor(sem: str) -> str:
    s = str(sem)
    if "🟢" in s:
        return "var(--green)"
    if "🟡" in s:
        return "var(--orange-2)"
    if "🔴" in s:
        return "var(--red)"
    return "var(--muted)"


def status_classe(status: str) -> str:
    return {"Prospectar": "s-pros", "Monitorar": "s-moni", "Edital": "s-edit",
            "Ativo": "s-ativo", "Mapear": "s-map"}.get(str(status).strip(), "s-map")


def status_badge(status: str) -> str:
    txt = esc(status) if str(status).strip() else "—"
    return f'<span class="stat {status_classe(status)}">{txt}</span>'


def seg_html(score: float, classe: str = "segbar") -> str:
    try:
        s = max(0.0, min(100.0, float(score))) / 100.0
    except (TypeError, ValueError):
        s = 0.0
    pesos = [0.35, 0.25, 0.20, 0.20]
    cores = ["var(--orange)", "var(--green)", "var(--blue)", "var(--muted)"]
    partes = "".join(f'<i style="width:{w * s * 100:.1f}%;background:{c}"></i>'
                     for w, c in zip(pesos, cores))
    return f'<span class="{classe}">{partes}</span>'


def score_chip_cor(score: float) -> str:
    try:
        s = float(score)
    except (TypeError, ValueError):
        s = 0
    if s >= 85:
        return "background:var(--green-soft);color:var(--green-2)"
    if s >= 70:
        return "background:var(--orange-soft);color:var(--orange-2)"
    return "background:rgba(255,255,255,.05);color:var(--muted)"


def score_chip_hex(score: float) -> str:
    """Versão com cores em hex/rgba (o iframe do componente não herda as CSS vars)."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        s = 0
    if s >= 85:
        return "background:rgba(95,177,55,.15);color:#9FD27F"
    if s >= 70:
        return "background:rgba(232,154,60,.14);color:#F0B264"
    return "background:rgba(255,255,255,.05);color:#9098A2"


def verificada_ok(valor: str) -> bool:
    v = str(valor).lower()
    return "verificada" in v and "não" not in v and "nao" not in v


_MESES_PT = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
             "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}


def _parse_data(s):
    """Extrai uma data de textos variados (dd/mm/aaaa, 'set/2026', '30 ago 2026')."""
    s = str(s or "").strip().lower()
    if not s:
        return None
    m = re.search(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return datetime.date(y, mo, d)
        except ValueError:
            return None
    m = re.search(r"(?:(\d{1,2})\s+)?([a-zç]{3})[a-zç]*[/\s.-]+(\d{4})", s)
    if m:
        mo = _MESES_PT.get(m.group(2))
        if mo:
            d = int(m.group(1)) if m.group(1) else 1
            try:
                return datetime.date(int(m.group(3)), mo, d)
            except ValueError:
                return None
    return None


def estilo_plotly(fig, altura=300, legenda=False):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#F2F0E9", family="Inter", size=12),
        margin=dict(l=8, r=8, t=8, b=8), height=altura, showlegend=legenda,
        legend=dict(font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#1F242C", font=dict(color="#F2F0E9", family="Inter"),
                        bordercolor="rgba(255,255,255,.13)"),
    )
    return fig


def lista_orgs_html(sub: pd.DataFrame, limite: int = 60) -> str:
    linhas = ""
    for _, r in sub.head(limite).iterrows():
        linhas += (
            f'<div class="lrow2"><div class="l">'
            f'<span class="sem" style="background:{sem_cor(r[COL_SEMAFORO])}"></span>'
            f'<div><div class="nm">{texto_ou(r[COL_EMPRESA])}</div>'
            f'<div class="sx">{texto_ou(r[COL_SETOR])} · {texto_ou(r[COL_SEDE])}/{texto_ou(r[COL_UF],"")}</div></div></div>'
            f'<div class="rt">{status_badge(r[COL_STATUS])}'
            f'<span class="alvo">{brl_curto(r[COL_VALVO])}</span>'
            f'<span class="sc">{int(r[COL_SCORE])}</span></div></div>'
        )
    if len(sub) > limite:
        linhas += f'<div class="kmore">+ {len(sub) - limite} organizações</div>'
    return linhas or '<div class="kmore">Nenhuma organização.</div>'


_TEMP_COR = {"Muito Quente": "#EC6A8C", "Morno": "#E8B54A",
             "Frio": "#5B9BD5", "Fechado": "#6B7688"}


_TEMP_EMOJI = {"Muito Quente": "🔵", "Morno": "🟡", "Frio": "🔴", "Fechado": "⚫"}


# Ordem canônica de temperatura (mais quente → fechado). Usada pelo termômetro da
# capa e pela ordenação de "negociação mais avançada".
_TEMP_ORDEM = ["Muito Quente", "Morno", "Frio", "Fechado"]


def _temp_nome(valor: str) -> str:
    """Normaliza a temperatura (a planilha traz '🟡 Morno') para o rótulo puro."""
    v = str(valor or "").lower()
    if "quente" in v:
        return "Muito Quente"
    if "morno" in v:
        return "Morno"
    if "frio" in v:
        return "Frio"
    if "fechado" in v:
        return "Fechado"
    return "Frio"


def _status_cor(status: str) -> str:
    s = str(status or "").lower()
    if "aprovada" in s or "andamento" in s:
        return "#4ADE80"
    if "reunião" in s or "reuniao" in s:
        return "#8B7BF0"
    if "não iniciado" in s or "nao iniciado" in s:
        return "#6B7688"
    return "#E8B54A"


def _int0(v) -> int:
    try:
        return int(float(str(v).replace(",", ".")))
    except (TypeError, ValueError):
        return 0


def _deputados_ordenados():
    dfd = dados.carregar_deputados()
    if dfd.empty:
        return []
    deps = []
    for _, r in dfd.iterrows():
        nome = str(r.get("Deputado", "")).strip()
        if not nome:
            continue
        temp = _temp_nome(r.get("Temperatura"))
        deps.append({
            "nome": nome, "partido": str(r.get("Partido", "")).strip() or "—",
            "chance": _int0(r.get("Chance Emenda (0-100)")),
            "ader": _int0(r.get("Aderência PFC (0-100)")),
            "score": _int0(r.get("Score Integrado")),
            "prioridade": str(r.get("Prioridade", "")).strip(),
            "status": str(r.get("Status", "")).strip() or "—",
            "temp": temp, "temp_cor": _TEMP_COR[temp], "temp_emoji": _TEMP_EMOJI[temp],
            "status_cor": _status_cor(r.get("Status")),
            "dialogo": str(r.get("Diálogo", "")).strip(),
            "base": str(r.get("Base Regional", "")).strip(),
            "gabinete": str(r.get("Gabinete ALESP", "")).strip(),
            "telefones": str(r.get("Telefones", "")).strip(),
            "whatsapp": str(r.get("WhatsApp", "")).strip(),
            "email": str(r.get("Email", "")).strip(),
            "instagram": str(r.get("Instagram", "")).strip(),
            "emenda": str(r.get("Emenda/Ação", "")).strip(),
            "valor": str(r.get("Valor", "")).strip(),
            "estrategia": str(r.get("Estratégia PFC", "")).strip(),
            "obs": str(r.get("Observações", "")).strip(),
        })
    deps.sort(key=lambda d: d["score"], reverse=True)
    return deps


def _contagens_emendas(deps) -> dict:
    """Contagens de Emendas — fonte única para o painel E para o card do hub.

    Os critérios são os mesmos dos KPIs do painel, de propósito: se o hub e o
    painel calculassem separado, voltariam a divergir (era o caso do antigo
    "4 diálogos" fixo no código). Mexeu num critério aqui, mudou nos dois.
    """
    status = [str(d.get("status", "")).lower() for d in deps]
    return {
        "deputados": len(deps),
        "reunioes": sum(1 for s in status if s.startswith(("reunião", "reuniao"))),
        "aprovadas": sum(1 for s in status if "aprovada" in s),
    }


# =========================================================================== #
# FUNDAÇÃO UNIFICADA DE PARLAMENTARES (Passo 1 da reorganização "Escopo")
# --------------------------------------------------------------------------- #
# Junta as bases de RELACIONAMENTO (CRM) dos três escopos num formato único, para
# que a Visão geral, o Funil etc. leiam UMA lista só, marcada por escopo.
#
#   estadual → aba 'Deputados'          (_deputados_ordenados)
#   federal  → aba 'Deputados Federais' (_deputados_federais_ordenados)
#   senador  → ainda vazio (o "lugar" já existe; devolve nada sem quebrar)
#
# REGRA DE OURO (não pode quebrar em NENHUMA tela): valor de EXECUÇÃO estadual
# (autorizado/pago, do levantamento) e valor SUGERIDO federal (faixa curada) são
# coisas diferentes — NUNCA somados, NUNCA rotulados como a mesma coisa. Quem
# segura isso é o campo `valor_tipo` de cada registro + o rótulo de rotulo_valor().
# Qualquer soma tem de ser agrupada por valor_tipo; some só dentro do mesmo tipo.
# =========================================================================== #

# Tipos de valor — a barreira que impede misturar execução com sugerido.
VALOR_EXECUCAO = "execucao"   # aut/pago real (estadual, levantamento) — nunca no federal
VALOR_SUGERIDO = "sugerido"   # faixa potencial curada (federal) — nunca é execução
VALOR_CRM = "crm"             # valor negociado anotado no CRM estadual (texto livre)
_VALOR_ROTULO = {
    VALOR_EXECUCAO: "execução (aut/pago)",
    VALOR_SUGERIDO: "valor sugerido (faixa)",
    VALOR_CRM: "registrado no CRM",
    "": "sem valor",
}

# Metadados de cada escopo — fonte única para os selos (Passo 2/3) e o rótulo de
# fonte no contato oficial. Violeta é a cor-mãe do painel; o selo diferencia por
# escopo. Senador já tem o lugar reservado.
ESCOPO_META = {
    "estadual": {"nome": "Estadual", "fonte": "ALESP", "sub": "Deputado estadual"},
    "federal": {"nome": "Federal", "fonte": "Câmara", "sub": "Deputado federal"},
    "senador": {"nome": "Senador", "fonte": "Senado", "sub": "Senador"},
}
ESCOPOS = ("estadual", "federal", "senador")


def rotulo_valor(valor_tipo: str) -> str:
    """Rótulo humano do tipo de valor — o único ponto que nomeia execução vs
    sugerido. Use SEMPRE isto ao exibir um valor, para nunca co-rotular errado."""
    return _VALOR_ROTULO.get(valor_tipo or "", "sem valor")


def _dep_federal_do_row(row) -> dict:
    """Dicionário completo de um deputado federal a partir da linha da aba.
    Score/aderência/chance/valor/estratégia JÁ vêm curados — só normaliza tipos."""
    def g(k):
        return str(row.get(k, "")).strip()

    def ni(k):
        try:
            return int(float(g(k).replace(",", ".") or 0))
        except (TypeError, ValueError):
            return 0
    return {
        "id": g("ID"), "nome": g("Deputado Federal"), "partido": g("Partido"),
        "score": ni("Score Integrado"), "chance": ni("Chance Emenda (0-100)"),
        "ader": ni("Aderência PFC (0-100)"), "base": g("Base Regional"),
        "proximidade": g("Proximidade Territorial"), "gabinete_camara": g("Gabinete Câmara"),
        "endereco_regional": g("Endereço/Escritório Regional"),
        "dialogo": g("Diálogo"), "status": g("Status CRM"),
        "temp_raw": g("Temperatura"), "temp": _temp_nome(g("Temperatura")),
        "telefones": g("Telefones"), "whatsapp": g("WhatsApp"), "email": g("Email"),
        "instagram": g("Instagram"), "emenda": g("Emenda/Ação"),
        "valor_sugerido": g("Valor sugerido"), "estrategia": g("Estratégia PFC"),
        "obs": g("Observações"), "fonte_camara": g("Fonte oficial Câmara"),
        "follow_up": g("Follow-up sugerido"),
    }


def _deputados_federais_ordenados() -> list:
    """Os deputados federais (aba 'Deputados Federais'), ordenados por score.
    Score/estratégia/valor JÁ vêm curados da planilha — nada é recalculado."""
    df = dados.carregar_deputados_federais()
    if df.empty:
        return []
    out = [_dep_federal_do_row(r) for _, r in df.iterrows()]
    out.sort(key=lambda d: d["score"], reverse=True)
    return out


def _parlamentar_estadual(d: dict) -> dict:
    """Registro estadual do CRM (_deputados_ordenados) → formato unificado.
    Chave de escrita = NOME (a porta atualizar_status_deputado casa por nome)."""
    valor = str(d.get("valor", "")).strip()
    temp = d.get("temp") or _temp_nome(d.get("temp"))
    return {
        "escopo": "estadual", "chave": d.get("nome", ""),
        "nome": d.get("nome", ""), "partido": d.get("partido", "") or "—",
        "score": _int0(d.get("score")), "ader": _int0(d.get("ader")),
        "chance": _int0(d.get("chance")),
        "status": d.get("status", "") or "—", "temp": temp,
        "temp_cor": _TEMP_COR.get(temp, "#7C8698"),
        "temp_emoji": _TEMP_EMOJI.get(temp, "⚫"),
        "dialogo": d.get("dialogo", ""), "base": d.get("base", ""),
        "valor_tipo": VALOR_CRM if valor else "", "valor_txt": valor, "valor": valor,
        "status_cor": _status_cor(d.get("status", "")),
        "prioridade": str(d.get("prioridade", "")).strip(),
        "escopo_nome": ESCOPO_META["estadual"]["nome"],
        "telefones": d.get("telefones", ""),
        "contato": {"fonte": ESCOPO_META["estadual"]["fonte"],
                    "gabinete": d.get("gabinete", ""), "telefones": d.get("telefones", ""),
                    "email": d.get("email", ""), "whatsapp": d.get("whatsapp", ""),
                    "instagram": d.get("instagram", "")},
        "estrategia": d.get("estrategia", ""), "emenda": d.get("emenda", ""),
        "obs": d.get("obs", ""), "_raw": d,
    }


def _parlamentar_federal(d: dict) -> dict:
    """Registro federal curado (_dep_federal_do_row) → formato unificado.
    Chave de escrita = ID (a porta atualizar_deputado_federal casa por ID).
    Valor é SEMPRE 'sugerido' (faixa) — nunca vira execução."""
    valor = str(d.get("valor_sugerido", "")).strip()
    temp = d.get("temp") or _temp_nome(d.get("temp_raw"))
    return {
        "escopo": "federal", "chave": d.get("id", ""),
        "nome": d.get("nome", ""), "partido": d.get("partido", "") or "—",
        "score": _int0(d.get("score")), "ader": _int0(d.get("ader")),
        "chance": _int0(d.get("chance")),
        "status": d.get("status", "") or "—", "temp": temp,
        "temp_cor": _TEMP_COR.get(temp, "#7C8698"),
        "temp_emoji": _TEMP_EMOJI.get(temp, "⚫"),
        "dialogo": d.get("dialogo", ""), "base": d.get("base", ""),
        "valor_tipo": VALOR_SUGERIDO if valor else "", "valor_txt": valor,
        # alias `valor` p/ os cards dos diálogos: SEMPRE carimbado "· sugerido" —
        # blindagem extra da regra de ouro (nunca aparece como execução aut/pago).
        "valor": (valor + " · sugerido") if valor else "",
        "status_cor": _status_cor(d.get("status", "")),
        "prioridade": "",
        "escopo_nome": ESCOPO_META["federal"]["nome"],
        "telefones": d.get("telefones", ""),
        "contato": {"fonte": ESCOPO_META["federal"]["fonte"],
                    "gabinete": d.get("gabinete_camara", ""), "telefones": d.get("telefones", ""),
                    "email": d.get("email", ""), "whatsapp": d.get("whatsapp", ""),
                    "instagram": d.get("instagram", "")},
        "estrategia": d.get("estrategia", ""), "emenda": d.get("emenda", ""),
        "obs": d.get("obs", ""), "_raw": d,
    }


def _sen_do_row(row) -> dict:
    """Dicionário completo de um SENADOR a partir da linha da aba 'Senadores'.
    Cópia de _dep_federal_do_row com 3 colunas renomeadas (Senado no lugar de
    Câmara). Score/aderência/chance/valor/estratégia JÁ vêm curados — nada recalcula."""
    def g(k):
        return str(row.get(k, "")).strip()

    def ni(k):
        try:
            return int(float(g(k).replace(",", ".") or 0))
        except (TypeError, ValueError):
            return 0
    return {
        "id": g("ID"), "nome": g("Senador"), "partido": g("Partido"),
        "score": ni("Score Integrado"), "chance": ni("Chance Emenda (0-100)"),
        "ader": ni("Aderência PFC (0-100)"), "base": g("Base Regional"),
        "proximidade": g("Proximidade Territorial"), "gabinete_senado": g("Gabinete Senado"),
        "endereco_regional": g("Endereço/Escritório Regional"),
        "dialogo": g("Diálogo"), "status": g("Status CRM"),
        "temp_raw": g("Temperatura"), "temp": _temp_nome(g("Temperatura")),
        "telefones": g("Telefones"), "whatsapp": g("WhatsApp"), "email": g("Email"),
        "instagram": g("Instagram"), "emenda": g("Emenda/Ação"),
        "valor_sugerido": g("Valor sugerido"), "estrategia": g("Estratégia PFC"),
        "obs": g("Observações"), "fonte_senado": g("Fonte oficial Senado"),
        "follow_up": g("Follow-up sugerido"),
    }


def _senadores_ordenados() -> list:
    """Os senadores (aba 'Senadores'), ordenados por score. Curados — nada é
    recalculado. Aba vazia/inexistente → lista vazia (escopo Senador vazio-elegante)."""
    df = dados.carregar_senadores()
    if df.empty:
        return []
    out = [_sen_do_row(r) for _, r in df.iterrows()]
    out.sort(key=lambda d: d["score"], reverse=True)
    return out


def _parlamentar_senador(d: dict) -> dict:
    """Registro senador curado (_sen_do_row) → formato unificado. Espelha o federal:
    chave = ID (CodigoParlamentar), valor SEMPRE 'sugerido' (faixa, nunca execução),
    score PRESERVADO (não recalcula). escopo/fonte próprios do Senado."""
    valor = str(d.get("valor_sugerido", "")).strip()
    temp = d.get("temp") or _temp_nome(d.get("temp_raw"))
    return {
        "escopo": "senador", "chave": d.get("id", ""),
        "nome": d.get("nome", ""), "partido": d.get("partido", "") or "—",
        "score": _int0(d.get("score")), "ader": _int0(d.get("ader")),
        "chance": _int0(d.get("chance")),
        "status": d.get("status", "") or "—", "temp": temp,
        "temp_cor": _TEMP_COR.get(temp, "#7C8698"),
        "temp_emoji": _TEMP_EMOJI.get(temp, "⚫"),
        "dialogo": d.get("dialogo", ""), "base": d.get("base", ""),
        "valor_tipo": VALOR_SUGERIDO if valor else "", "valor_txt": valor,
        "valor": (valor + " · sugerido") if valor else "",
        "status_cor": _status_cor(d.get("status", "")),
        "prioridade": "",
        "escopo_nome": ESCOPO_META["senador"]["nome"],
        "telefones": d.get("telefones", ""),
        "contato": {"fonte": ESCOPO_META["senador"]["fonte"],
                    "gabinete": d.get("gabinete_senado", ""), "telefones": d.get("telefones", ""),
                    "email": d.get("email", ""), "whatsapp": d.get("whatsapp", ""),
                    "instagram": d.get("instagram", "")},
        "estrategia": d.get("estrategia", ""), "emenda": d.get("emenda", ""),
        "obs": d.get("obs", ""), "_raw": d,
    }


def normalizar_parlamentares(estaduais: list | None, federais: list | None,
                             senadores: list | None = None) -> list:
    """Junta as listas dos três escopos num formato único (função PURA, testável
    com dados falsos — não toca no Sheets). Ordena por score decrescente.
    Cada registro carrega `escopo`, `chave` (p/ rotear a escrita) e `valor_tipo`
    (execução vs sugerido nunca se confundem). `senadores` já normalizados; hoje
    vazio, mas o parâmetro deixa o lugar pronto."""
    out = [_parlamentar_estadual(d) for d in (estaduais or [])]
    out += [_parlamentar_federal(d) for d in (federais or [])]
    out += list(senadores or [])
    out.sort(key=lambda r: r.get("score", 0), reverse=True)
    return out


def carregar_parlamentares(escopo: str = "Geral") -> list:
    """Porta única de leitura unificada dos parlamentares (CRM dos três escopos).
    `escopo`: 'Geral' (padrão, todos) ou 'Estadual'/'Federal'/'Senador' (filtra).
    Lê ao vivo pelas portas de cada base e normaliza. Read-only."""
    registros = normalizar_parlamentares(
        _deputados_ordenados(), _deputados_federais_ordenados(),
        [_parlamentar_senador(d) for d in _senadores_ordenados()])
    alvo = str(escopo or "Geral").strip().lower()
    if alvo in ESCOPOS:
        registros = [r for r in registros if r["escopo"] == alvo]
    return registros


def _e_nao_iniciado(status: str) -> bool:
    """True se a ETAPA é 'Não iniciado' — incluindo status vazio/None (sem etapa =
    não iniciado). Predicado ÚNICO de 'em articulação' (contagem E lista, em todos os
    escopos): em articulação == not _e_nao_iniciado(status). Lê a ETAPA (status),
    NUNCA o Diálogo (observação livre)."""
    s = str(status or "").strip().lower()
    return s == "" or "não iniciado" in s or "nao iniciado" in s


def capa_payload_parlamentares(regs: list, filtro: str | None = None,
                               escopo_sel: str = "Geral") -> dict:
    """Monta o payload da CAPA GERAL (Passo 3) a partir dos registros unificados —
    o MESMO formato que a capa estadual sempre mandou ao componente _emendas_v2
    (hero/kpis/temperatura/deps), agora sobre todos os escopos e com o selo em cada
    card (campos `escopo`/`escopo_nome` que já vêm no registro).

    PURA (sem st) e testável. `filtro` = temperatura selecionada (afeta só a tabela).
    Devolve {payload, top, regs_view, em_articulacao, lista_reunioes, lista_aprovadas}
    para a casca em app.py só renderizar e rotear os cliques.

    Regra de ouro: a capa NÃO exibe nem soma valores nos cards (só chance/aderência/
    status). Score federal é copiado do registro, nunca recalculado."""
    total = len(regs)
    if not total:
        return {"payload": {"deps": [], "hero": {}, "temperatura": [], "kpis": [],
                            "modo": "visao"},
                "top": None, "regs_view": [], "em_articulacao": [],
                "lista_reunioes": [], "lista_aprovadas": []}

    def _st(r):
        return str(r.get("status", "")).lower()
    nao_abordados = sum(1 for r in regs if _e_nao_iniciado(r.get("status")))
    articulacao = total - nao_abordados
    reunioes = sum(1 for r in regs if _st(r).startswith(("reunião", "reuniao")))
    aprovadas = sum(1 for r in regs if "aprovada" in _st(r))
    chance_media = round(sum(r.get("chance", 0) for r in regs) / total) if total else 0

    ordem_temp = {t: i for i, t in enumerate(_TEMP_ORDEM)}
    top = min(regs, key=lambda r: (ordem_temp.get(r["temp"], 9), -r.get("score", 0)))

    cont_temp = {t: 0 for t in _TEMP_ORDEM}
    for r in regs:
        cont_temp[r["temp"]] = cont_temp.get(r["temp"], 0) + 1
    temperatura = [{"nome": t, "emoji": _TEMP_EMOJI[t], "cor": _TEMP_COR[t],
                    "n": cont_temp.get(t, 0), "pct": round(cont_temp.get(t, 0) / total * 100)}
                   for t in _TEMP_ORDEM]

    em_articulacao = [r for r in regs if not _e_nao_iniciado(r.get("status"))]
    lista_reunioes = [r for r in regs if _st(r).startswith(("reunião", "reuniao"))]
    lista_aprovadas = [r for r in regs if "aprovada" in _st(r)]
    regs_view = [r for r in regs if r["temp"] == filtro] if filtro else regs

    fonte_foot = {"Geral": "nos três escopos", "Estadual": "na base ALESP",
                  "Federal": "na Câmara"}.get(escopo_sel, "")
    payload = {
        "modo": "visao", "total": total, "filtro_temp": filtro,
        "temp_ordem": [{"nome": t, "cor": _TEMP_COR[t], "emoji": _TEMP_EMOJI[t]}
                       for t in _TEMP_ORDEM],
        "hero": {"articulacao": articulacao, "total": total, "nao_abordados": nao_abordados,
                 "top": {"nome": top["nome"], "partido": top["partido"],
                         "status": top["status"], "score": top["score"],
                         "temp": top["temp"], "cor": top["temp_cor"],
                         "escopo": top["escopo"], "escopo_nome": top["escopo_nome"]}},
        "temperatura": temperatura,
        "kpis": [
            {"c": "#8B7BF0", "icon": "users", "lab": "Parlamentares", "val": total,
             "foot": fonte_foot},
            {"k": "reunioes", "c": "#E8B54A", "icon": "cal", "lab": "Reuniões ativas",
             "val": reunioes, "foot": "solicitadas ou agendadas · ver quais"},
            {"k": "aprovadas", "c": "#4ADE80", "icon": "check", "lab": "Emendas aprovadas",
             "val": aprovadas,
             "foot": "✓ ver a conquista" if aprovadas else "nenhuma ainda",
             "foot_cor": "#4ADE80" if aprovadas else None},
            {"c": "#EC6A8C", "icon": "money", "lab": "Chance média", "val": chance_media,
             "suffix": "%", "foot": "de emenda no grupo"},
        ],
        "deps": regs_view,
    }
    return {"payload": payload, "top": top, "regs_view": regs_view,
            "em_articulacao": em_articulacao, "lista_reunioes": lista_reunioes,
            "lista_aprovadas": lista_aprovadas}


def _sidebar_toggle_html() -> str:
    """Botão de recolher/expandir no TOPO da sidebar (em fluxo, dentro da barra).
    Clique tratado por delegação (_SIDEBAR_TOGGLE_JS); ícone/rótulo são dirigidos
    por CSS conforme html.pfc-sb-open — sem JS mexendo no innerHTML (não briga
    com o React que recria o elemento)."""
    return (
        '<div class="pfc-sb-toggle" role="button" tabindex="0" '
        'title="Recolher ou expandir a barra lateral" '
        'aria-label="Recolher ou expandir a barra lateral">'
        '<svg class="pfc-ic pfc-ic-abrir" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M13 17l5-5-5-5"/><path d="M6 17l5-5-5-5"/></svg>'
        '<svg class="pfc-ic pfc-ic-fechar" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M11 17l-5-5 5-5"/><path d="M18 17l-5-5 5-5"/></svg>'
        '<span class="pfc-sb-toggle-lbl">Recolher</span>'
        '</div>'
        # divisor: dá respiro e separa o controle dos itens de navegação
        '<div class="pfc-sb-sep"></div>')


def _cards_deputados(lista, extras=()):
    """Cards de deputado para os dialogs. extras = [(rótulo, chave), ...]."""
    html = ""
    for d in lista:
        linhas = "".join(
            f'<div style="font-family:var(--mono);font-size:10px;letter-spacing:.6px;'
            f'text-transform:uppercase;color:var(--dim);margin-top:10px">{lab}</div>'
            f'<div style="font-size:13.5px;color:var(--ink);line-height:1.5">'
            f'{esc(str(d.get(ch) or "—"))}</div>'
            for lab, ch in extras)
        html += (
            f'<div style="background:var(--surface2);border:1px solid var(--line);'
            f'border-left:3px solid {d["temp_cor"]};border-radius:0 12px 12px 0;'
            f'padding:15px 17px;margin-bottom:11px">'
            f'<div style="display:flex;align-items:center;gap:11px;flex-wrap:wrap">'
            f'<span style="font-weight:700;font-size:15px">{esc(d["nome"])}</span>'
            f'<span style="font-family:var(--mono);font-size:11px;color:var(--dim)">'
            f'{esc(d["partido"])} · {d["temp_emoji"]} {esc(d["temp"])}</span>'
            f'<span style="margin-left:auto;background:{d["status_cor"]}22;color:{d["status_cor"]};'
            f'font-size:11.5px;font-weight:600;padding:4px 11px;border-radius:20px;white-space:nowrap">'
            f'{esc(d["status"])}</span></div>{linhas}</div>')
    return html or '<div style="color:var(--muted);font-size:14px">Nenhum deputado nesta condição.</div>'


EMENDA_FUNIL_ETAPAS = ["Não iniciado", "Contato iniciado", "Reunião",
                       "Emenda encaminhada", "Emenda aprovada"]


EMENDA_ETAPA_COR = {"Não iniciado": "#7C8698", "Contato iniciado": "#5B9BD5",
                    "Reunião": "#E8B54A", "Emenda encaminhada": "#8B7BF0",
                    "Emenda aprovada": "#4ADE80"}


def _etapa_de_status(status: str) -> str:
    """Enquadra um Status (livre) do deputado numa das etapas canônicas do funil."""
    s = str(status or "").lower()
    if "aprovada" in s:
        return "Emenda aprovada"
    if "encaminh" in s or "empenh" in s or "protocol" in s:
        return "Emenda encaminhada"
    if "reuni" in s or "negocia" in s or "andamento" in s:
        return "Reunião"
    if any(k in s for k in ("ligac", "ligaç", "contato", "escritor", "assessor",
                            "email", "e-mail", "mensagem", "whats")):
        return "Contato iniciado"
    return "Não iniciado"


def _cor_score(s: float) -> str:
    """Cor semântica do score (mesma régua do design system: 60+, 50-59, <50)."""
    return "var(--sem-high)" if s >= 60 else "var(--sem-mid)" if s >= 50 else "var(--sem-low)"


def _muns_pfc(row: dict, secao: str) -> str:
    """Municípios do PFC onde o deputado atua, como texto legível."""
    if secao == "territorio":
        return str(row.get("municipios_pfc", "") or "")
    diretos = str(row.get("municipios_pfc_diretos", "") or "")
    vizinhos = str(row.get("municipios_vizinhos", "") or "")
    return " · ".join(x for x in (
        (f"direto: {diretos}" if diretos else ""),
        (f"vizinho: {vizinhos}" if vizinhos else "")) if x) or "sem pé no território"


def _puxar_para_crm(row: dict, secao: str) -> dict:
    """Monta a linha do CRM a partir do levantamento e grava (append-only)."""
    score = float(row.get("score_pfc") or row.get("score_expansao") or 0)
    if secao == "territorio":
        aut, pago = row.get("autorizado_pfc", 0), row.get("pago_pfc", 0)
        muns = str(row.get("municipios_pfc", "") or "")
        secao_nome = "Abordar já (território)"
    else:
        aut, pago = row.get("autorizado_geral_edusoc", 0), row.get("pago_geral_edusoc", 0)
        d = str(row.get("municipios_pfc_diretos", "") or "")
        v = str(row.get("municipios_vizinhos", "") or "")
        muns = "; ".join(x for x in (d, v) if x)
        secao_nome = "Cortejar (expansão)"
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    obs = (f"Puxado da Descoberta em {hoje} · {secao_nome}. "
           f"Fatia educação/social {row.get('alinhamento_pct', 0)}%. "
           f"Autorizado {brl(aut)}, pago {brl(pago)} (execução 2023-2025).")
    return dados.adicionar_deputado_crm({
        "Deputado": row.get("deputado", ""),
        "Partido": row.get("partido", ""),
        "Score Integrado": str(round(score)),
        "Base Regional": muns,
        "Status": "Não iniciado",  # ponto de partida; o Fábio preenche o resto
        "Observações": obs,
    })


_MUN_MINUSC = {"de", "do", "da", "dos", "das", "e", "a", "o", "no", "na"}


def _cap_mun(nome: str) -> str:
    """Title-case pt-BR: mantém conectivos minúsculos ('Campina do Monte Alegre')."""
    pal = str(nome).lower().split()
    return " ".join(w if (i > 0 and w in _MUN_MINUSC) else w.capitalize()
                    for i, w in enumerate(pal))


def _fmt_muns(s, limite: int = 3) -> str:
    """Lista de municípios ('SALTO; IPERÓ') -> 'Salto/Iperó' (corta em `limite`)."""
    partes = [_cap_mun(p) for p in str(s or "").replace(";", ",").split(",") if p.strip()]
    if not partes:
        return ""
    if len(partes) <= limite:
        return "/".join(partes)
    return "/".join(partes[:limite]) + f" +{len(partes) - limite}"


def _pct_int(v) -> str:
    try:
        return f"{round(float(v))}%"
    except (TypeError, ValueError):
        return "0%"


def _argumento_abordagem(row: dict, secao: str) -> str:
    """Melhor gancho de abordagem, do argumento mais forte ao mais fraco.
    Só usa dado real do levantamento — se não há gancho, é honesto."""
    def n(k):
        try:
            return float(row.get(k) or 0)
        except (TypeError, ValueError):
            return 0.0

    alinh = n("alinhamento_pct")
    # 1) TERRITÓRIO DIRETO — já financia num município onde o PFC atua
    if secao == "territorio":
        aut, muns = n("autorizado_pfc"), str(row.get("municipios_pfc", "")).strip()
    else:
        aut, muns = n("autorizado_direto"), str(row.get("municipios_pfc_diretos", "")).strip()
    if muns and aut > 0:
        return (f"Já destinou {brl_curto(aut)} a educação/social em {_fmt_muns(muns)}, "
                f"onde o PFC atua — bom gancho para abrir a conversa.")
    if muns:
        return (f"Atua em {_fmt_muns(muns)}, onde o PFC está presente — "
                f"vale sondar a agenda de educação/social.")
    # 2) VIZINHANÇA — financia colado aos nossos municípios (só expansão)
    if secao == "expansao":
        aut_viz = n("autorizado_vizinho")
        muns_viz = str(row.get("municipios_vizinhos", "")).strip()
        if muns_viz and (aut_viz > 0 or n("autorizado_geral_edusoc") > 0):
            valor = aut_viz if aut_viz > 0 else n("autorizado_geral_edusoc")
            return (f"Financia educação/social colada aos nossos municípios ({brl_curto(valor)}) "
                    f"— candidato natural para trazer a {_fmt_muns(muns_viz)}.")
    # 3) ALINHAMENTO PROPORCIONAL alto
    if alinh >= 40:
        return (f"{_pct_int(alinh)} de tudo que destina vai para educação/social "
                f"— perfil fortemente alinhado ao PFC.")
    # 4) VOLUME GERAL alto
    aut_geral = n("autorizado_geral_edusoc") or n("autorizado_pfc")
    if aut_geral >= 1_000_000:
        return (f"Alto volume em educação/social no estado ({brl_curto(aut_geral)}) "
                f"— ainda sem pé nos nossos municípios, mas alvo de cortejo.")
    # 5) FALLBACK HONESTO — nada de forçar
    if alinh > 0:
        return (f"Sem histórico direto nos nossos municípios ainda — mas {_pct_int(alinh)} "
                f"do que destina é educação/social, vale um primeiro contato.")
    return "Sem histórico direto nos nossos municípios ainda — abrir pela pauta do PFC."


def _status_no_crm(nome: str, crm_df) -> str:
    """Status atual do deputado no CRM (aba Deputados), ou 'No CRM' se sem status.
    Casa por slug (tolerante a acento/caixa e nome contido)."""
    if crm_df is None or crm_df.empty or "Deputado" not in crm_df:
        return "No CRM do Fábio"
    alvo = slug(str(nome))
    for _, r in crm_df.iterrows():
        outro = slug(str(r.get("Deputado", "")))
        if outro and (outro == alvo or alvo in outro or outro in alvo):
            return str(r.get("Status", "")).strip() or "No CRM (sem status)"
    return "No CRM do Fábio"


def _sala_no_crm(nome: str, crm_df) -> str:
    """Sala/gabinete do deputado na ALESP, do CRM (coluna 'Gabinete ALESP'), ou
    '' se ausente/vazio. Casa por slug (tolerante a acento/caixa e nome contido),
    igual a _status_no_crm. Diferente do status: quando não há, devolve '' — a
    linha da sala é então OMITIDA graciosamente (dossiê e PDF), nunca 'Sala: —'."""
    if crm_df is None or crm_df.empty or "Deputado" not in crm_df:
        return ""
    alvo = slug(str(nome))
    if not alvo:
        return ""
    for _, r in crm_df.iterrows():
        outro = slug(str(r.get("Deputado", "")))
        if outro and (outro == alvo or alvo in outro or outro in alvo):
            sala = str(r.get("Gabinete ALESP", "")).strip()
            return "" if sala.lower() in ("nan", "none") else sala
    return ""


def _resumo_dep_dados(row: dict, secao: str, no_crm: bool, crm_df) -> dict:
    """Monta o dicionário do resumo pré-reunião (só dado real do levantamento+CRM)."""
    score = float(row.get("score_pfc") or row.get("score_expansao") or 0)
    if secao == "territorio":
        aut, pago = row.get("autorizado_pfc", 0), row.get("pago_pfc", 0)
        onde = "nos municípios do PFC"
        diretos = _fmt_muns(row.get("municipios_pfc", ""), limite=20)
        vizinhos = "—"  # a seção território não avalia vizinhança
    else:
        aut, pago = row.get("autorizado_geral_edusoc", 0), row.get("pago_geral_edusoc", 0)
        onde = "em educação/social no estado"
        diretos = _fmt_muns(row.get("municipios_pfc_diretos", ""), limite=20)
        vizinhos = _fmt_muns(row.get("municipios_vizinhos", ""), limite=20)
    ct = dados.contato_oficial(str(row.get("deputado", ""))) or {}
    return {
        "deputado": row.get("deputado", ""), "partido": row.get("partido", ""),
        "camada": row.get("camada", "") if secao == "expansao" else "No território",
        "score": f"{score:.1f}".replace(".", ","),
        "alinhamento": _pct_int(row.get("alinhamento_pct", 0)),
        "status_crm": (_status_no_crm(str(row.get("deputado", "")), crm_df)
                       if no_crm else "Fora do CRM"),
        "argumento": _argumento_abordagem(row, secao),
        "onde": onde, "autorizado": brl(aut), "pago": brl(pago),
        "municipios_diretos": diretos or "nenhum",
        "municipios_vizinhos": vizinhos or "nenhum",
        "email": ct.get("email", ""), "telefone": ct.get("telefone", ""),
        "pagina": ct.get("pagina", ""),
        # Sala/gabinete na ALESP — vem do CRM (curada pelo Fábio). '' -> omitida.
        "sala": _sala_no_crm(str(row.get("deputado", "")), crm_df),
    }


def _filtrar_descobrir(df, busca: str, partido: str, municipio: str, cols_mun: list):
    """Filtra o ranking por nome (contém), partido (exato) e município do PFC
    onde atua (casa por slug, ignorando acento/caixa). Só leitura — não altera
    dado. 'Todos'/'' desligam o respectivo filtro."""
    if df.empty:
        return df
    out = df
    if busca and busca.strip():
        out = out[out["deputado"].astype(str).str.contains(
            busca.strip(), case=False, na=False, regex=False)]
    if partido and partido != "Todos":
        out = out[out["partido"].astype(str) == partido]
    if municipio and municipio != "Todos":
        alvo = slug(municipio)
        cols = [c for c in cols_mun if c in out.columns]
        out = out[out.apply(
            lambda r: any(alvo in slug(str(r.get(c, ""))) for c in cols), axis=1)]
    return out


_EDUSOC_SLUGS = {"educacao", "assistencia-social"}


def _orfaos_com_candidatos(orfaos_df, base_df, ibge_df, terr_df, exp_df) -> list:
    """Para cada município órfão, os deputados do levantamento que financiam
    educação/social na mesma Região Imediata (IBGE). Ordenados por autorizado na
    região (desc). Função pura — só cruza os dados reais que já temos."""
    if orfaos_df is None or orfaos_df.empty:
        return []
    # deputado (slug) -> (linha do ranking, seção). Território sobrepõe expansão.
    lev = {}
    if exp_df is not None and not exp_df.empty:
        for _, r in exp_df.iterrows():
            lev.setdefault(slug(str(r["deputado"])), (dict(r), "expansao"))
    if terr_df is not None and not terr_df.empty:
        for _, r in terr_df.iterrows():
            lev[slug(str(r["deputado"]))] = (dict(r), "territorio")

    ibge = ibge_df.copy()
    ibge["mslug"] = ibge["municipio"].map(lambda x: slug(str(x)))
    por_mun = {r["mslug"]: (r["regiao_imediata_id"], r["regiao_imediata_nome"])
               for _, r in ibge.iterrows()}
    por_regiao = {}
    for _, r in ibge.iterrows():
        por_regiao.setdefault(r["regiao_imediata_id"], set()).add(r["mslug"])

    base = base_df.copy()
    base["aslug"] = base["area"].map(lambda x: slug(str(x)))
    base["mslug"] = base["municipio"].map(lambda x: slug(str(x)))
    base["aut"] = pd.to_numeric(base["valor_autorizado"], errors="coerce").fillna(0)
    base["pago"] = pd.to_numeric(base["valor_pago"], errors="coerce").fillna(0)
    edusoc = base[base["aslug"].isin(_EDUSOC_SLUGS)]

    resultado = []
    for _, o in orfaos_df.iterrows():
        nome = str(o.get("municipio", "")).strip()
        osl = slug(nome)
        reg = por_mun.get(osl)
        item = {"municipio": nome, "grupo": str(o.get("grupo", "")).strip(),
                "regiao_nome": "", "n_regiao": 0, "candidatos": [],
                "fora_lev": 0, "sem_regiao": reg is None}
        if reg is None:
            resultado.append(item)
            continue
        rid, rnome = reg
        reg_muns = por_regiao.get(rid, set()) - {osl}
        item["regiao_nome"], item["n_regiao"] = rnome, len(reg_muns)
        sub = edusoc[edusoc["mslug"].isin(reg_muns)]
        for dep, g in sub.groupby("deputado"):
            dsl = slug(str(dep))
            if dsl not in lev:
                item["fora_lev"] += 1  # financia a região, mas fora do levantamento
                continue
            row, secao = lev[dsl]
            item["candidatos"].append({
                "deputado": dep, "partido": str(g["partido"].iloc[0]),
                "aut": float(g["aut"].sum()), "pago": float(g["pago"].sum()),
                "muns": sorted({str(m) for m in g["municipio"]}),
                "score": float(row.get("score_pfc") or row.get("score_expansao") or 0),
                "row": row, "secao": secao})
        item["candidatos"].sort(key=lambda c: c["aut"], reverse=True)
        resultado.append(item)
    return resultado


def aviso_contexto_territorios(escopo_sel: str) -> str:
    """Aviso honesto de contexto da tela Territórios em Aberto (Passo 7). Função PURA.

    Territórios é uma análise ESTADUAL por natureza — cruza execução estadual
    georreferenciada (Transparência SP × Regiões Imediatas IBGE); não existe série
    federal/senador equivalente. Então sob esses escopos o conteúdo NÃO muda (segue
    estadual) — só declaramos isso honestamente. Retorna '' para Geral/Estadual (sem
    aviso) e a frase para Federal/Senador. Nunca promete candidatos/série federal."""
    alvo = str(escopo_sel or "Geral").strip().lower()
    nome = {"federal": "Federal", "senador": "Senador"}.get(alvo)
    if not nome:
        return ""
    return (f"Escopo {nome} selecionado: esta análise usa execução ESTADUAL "
            f"georreferenciada (não há série {nome.lower()} equivalente). "
            f"O conteúdo abaixo é sempre estadual.")


# Páginas da sidebar de Emendas → 'modo' de conteúdo. Fonte única (Passo 8), pura
# e testável. Página desconhecida ou LEGADA (ex.: 'Lista' do painel Federal antigo,
# ou 'Deputados', ambas aposentadas) cai em 'visao' — blinda a migração de estado.
_MODO_EMENDA = {"Visão geral": "visao",
                "Descobrir": "descobrir", "Territórios em Aberto": "orfaos",
                "Funil de negociação": "funil", "Relatório": "relatorio",
                "Metodologia": "metodologia"}


def _modo_emenda(page: str) -> str:
    """Modo de conteúdo da página de Emendas; 'visao' para página desconhecida/legada."""
    return _MODO_EMENDA.get(page, "visao")


def metodologia_emendas_conteudo() -> dict:
    """Conteúdo (dados) da Metodologia de Emendas — PURO e testável; a casca (app.py)
    só renderiza. Os pesos do Estadual são os REAIS de config/pfc_municipios.toml
    (fonte de verdade do cálculo em src/emendas.py); se o toml mudar, ATUALIZE aqui.
    Federal/Senador é curado à mão (0–100), NÃO recalculado pelo app."""
    return {
        "golden_rule": (
            "Autorizado e pago são sempre mostrados SEPARADOS, nunca somados. E a "
            "faixa sugerida do Federal/Senador (potencial) NUNCA é somada com a "
            "execução real do Estadual — são réguas e escalas diferentes."
        ),
        "estadual": {
            "resumo": ("Score 0–100 CALCULADO pelo app a partir da execução real de "
                       "emendas (autorizado 2023–2025, Transparência SP), cruzada com os "
                       "municípios do PFC e a vizinhança geográfica (Regiões Imediatas "
                       "IBGE 2017). Sai em duas seções, com réguas diferentes."),
            "grupos": ("Municípios do PFC pesam diferente: Operação ativa = 1,0; "
                       "Tatuí (compromisso assinado, não iniciado) = 0,45."),
            "fator_vizinho": 0.45,
            "secoes": [
                {"nome": "Abordar já (no território)",
                 "formula": "SCORE = 0,30·ALINHAMENTO + 0,45·VOLUME + 0,25·PRESENÇA",
                 "min": "Entra quem tem ≥ 2 emendas edu/social nos municípios do PFC "
                        "(evita inflar o score com uma emenda só).",
                 "pesos": [
                     {"n": "Volume", "w": 45, "cor": "#4ADE80",
                      "desc": "R$ autorizado a educação/social NOS municípios do PFC, "
                              "ponderado pelo peso do grupo. O sinal mais forte — maior peso."},
                     {"n": "Alinhamento", "w": 30, "cor": "#8B7BF0",
                      "desc": "Fatia % das emendas do deputado que vão para educação/social "
                              "(orientação geral; independe do território do PFC)."},
                     {"n": "Presença", "w": 25, "cor": "#5B9BD5",
                      "desc": "Em quantos municípios do PFC ele atua, cada um pelo peso do grupo."},
                 ]},
                {"nome": "Cortejar (expansão)",
                 "formula": "SCORE = 0,40·ALINHAMENTO + 0,45·VOLUME GERAL + 0,15·PROXIMIDADE",
                 "min": "Alvo de expansão precisa de volume geral edu/social ≥ R$ 1 mi; "
                        "≥ R$ 5 mi entra como 'prioritário'.",
                 "pesos": [
                     {"n": "Volume geral", "w": 45, "cor": "#4ADE80",
                      "desc": "R$ autorizado a edu/social em TODO o estado — a 'potência' "
                              "de emenda do deputado na área."},
                     {"n": "Alinhamento", "w": 40, "cor": "#8B7BF0",
                      "desc": "Mesma fatia % edu/social da seção anterior."},
                     {"n": "Proximidade", "w": 15, "cor": "#E8B54A",
                      "desc": "Facilitador em 3 níveis: DIRETO (emenda no próprio município "
                              "do PFC = peso cheio) · VIZINHO (mesma Região Imediata IBGE = "
                              "0,45× o direto) · LONGE (zero)."},
                 ]},
            ],
        },
        "federal_senador": {
            "titulo": "Federal e Senador",
            "resumo": ("Score qualitativo 0–100 CURADO à mão (não recalculado pelo app — "
                       "não há série de execução como no Estadual). Combina três leituras:"),
            "criterios": [
                {"n": "Aderência", "desc": "Fit temático com o PFC: ciência, educação, "
                                           "juventude, inclusão."},
                {"n": "Chance", "desc": "Viabilidade da emenda: poder + máquina + "
                                        "pragmatismo + peso regional."},
                {"n": "Empurrão territorial", "desc": "Base ou atuação em Sorocaba e Região "
                                                      "Metropolitana (RMS) dá um empurrão."},
            ],
            "valor": ("O valor é uma FAIXA SUGERIDA (potencial mín–máx), rotulada "
                      "'sugerido' — nunca execução, nunca somada com o Estadual."),
        },
    }


def explorador_parlamentar_comps(reg: dict) -> dict:
    """Dados do explorador de score da Metodologia (a partir de UM registro do CRM,
    carregar_parlamentares). Componentes REAIS — Aderência e Chance (0–100) — e o
    Score Integrado como total; mesma régua p/ estadual e federal no CRM, sem inventar
    breakdown. PURO/testável. Campo faltante vira 0 (nunca quebra)."""
    return {
        "nome": str(reg.get("nome", "")).strip() or "(sem nome)",
        "escopo_nome": reg.get("escopo_nome", ""),
        "total": _int0(reg.get("score")),
        "comps": [
            {"n": "Aderência", "v": _int0(reg.get("ader")), "c": "#8B7BF0"},
            {"n": "Chance", "v": _int0(reg.get("chance")), "c": "#5B9BD5"},
        ],
    }


def _destino_radar(radar_escolhido) -> str:
    """Mapa raiz do painel a renderizar a partir de session_state['radar_escolhido'].
    Função PURA, testável. None → 'hub' (Central); 'captacao'/'emendas'/'prospeccao'
    → si mesmos; qualquer outro valor (legado/corrompido) → 'hub' (fallback são: o
    usuário re-escolhe na Central, em vez de cair numa tela errada)."""
    if radar_escolhido in ("captacao", "emendas", "prospeccao"):
        return radar_escolhido
    return "hub"


# Tipos de verba da Prospecção — lista FIXA (4, sem "Outro"). Alimenta SÓ o selectbox
# de entrada; a EXIBIÇÃO tolera tipos legados fora da lista (rotulo_tipo_prospeccao),
# então remover um tipo daqui nunca esconde um registro já gravado (ex.: 'OUTRO').
PROSPECCAO_TIPOS = ["Emenda", "Patrocínio", "Prefeitura", "Prêmio"]


def rotulo_tipo_prospeccao(t) -> str:
    """Rótulo de exibição do tipo de verba, TOLERANTE a tipo legado: devolve o tipo
    cru (mesmo fora de PROSPECCAO_TIPOS, ex.: 'OUTRO' de um registro antigo) e '—'
    quando vazio. Não valida nem esconde — a lista canônica é só para a entrada."""
    return str(t or "").strip() or "—"


def linhas_placar_prospeccao(ganhos: list) -> list:
    """Modelo das linhas do placar 'Verba já conquistada' (Prospecção) — uma por
    item na etapa final. PURA (sem st/HTML): monta {nome, sub, valor} a partir dos
    registros; a casca (app.py) escapa e vira HTML. Lista vazia → []. O `sub`
    junta Tipo · Financiador · Previsão (só os não-vazios)."""
    linhas = []
    for it in (ganhos or []):
        sub = " · ".join(x for x in (str(it.get("Tipo", "")).strip(),
                                     str(it.get("Financiador", "")).strip(),
                                     str(it.get("Previsão", "")).strip()) if x)
        linhas.append({
            "nome": str(it.get("Nome", "")).strip() or "(sem nome)",
            "sub": sub,
            "valor": str(it.get("Valor", "")).strip() or "—",
        })
    return linhas


def _funil_emendas_colunas(deps: list) -> list:
    """Monta as colunas do kanban a partir dos deputados, enquadrando cada um na
    sua etapa. card.id = nome (chave da aba); card.status = a etapa (coluna)."""
    colunas = []
    for etapa in EMENDA_FUNIL_ETAPAS:
        cards = [{
            "id": d["nome"], "status": etapa, "nome": d["nome"],
            "setor": d.get("partido") or "—",
            "score": int(d.get("score") or 0),
            "valor": f'{d.get("temp_emoji","")} {d.get("temp","")}'.strip(),
        } for d in deps if _etapa_de_status(d.get("status", "")) == etapa]
        colunas.append({"status": etapa, "cor": EMENDA_ETAPA_COR[etapa], "cards": cards})
    return colunas


# Separador do id de card no funil GERAL (Passo 5). O kanban devolve um único
# `org_id` opaco no drop, então embutimos o ESCOPO junto da CHAVE para rotear a
# escrita sem ambiguidade (nome estadual × ID federal nunca colidem).  (SOH)
# é um caractere de controle que não aparece em nome de deputado nem em ID.
_SEP_ID_CARD = chr(1)  # SOH (U+0001): separa escopo/chave no id do card; nunca em nome/ID


def _id_card_parlamentar(reg: dict) -> str:
    """Codifica o id do card do funil geral como 'escopo\\x01chave'. A `chave` é o
    NOME (estadual) ou o ID (federal) — a MESMA que roteia a escrita no drop."""
    return f'{reg.get("escopo", "")}{_SEP_ID_CARD}{reg.get("chave", "")}'


def _decodificar_id_card(org_id: str) -> tuple:
    """Inverso de _id_card_parlamentar: 'escopo\\x01chave' → (escopo, chave).
    Sem o separador (id legado/estranho), devolve ('', <id cru>) — aí o roteador
    trata como escopo desconhecido e recusa a gravação, sem quebrar."""
    org_id = str(org_id or "")
    if _SEP_ID_CARD in org_id:
        escopo, chave = org_id.split(_SEP_ID_CARD, 1)
        return escopo.strip(), chave.strip()
    return "", org_id.strip()


def compor_dialogo(atual: str, texto: str, agora: str | None = None) -> str:
    """Anexa uma observação DATADA ao Diálogo, preservando o histórico — MESMO
    formato do estadual (dados.anexar_dialogo_deputado): '[dd/mm/aaaa HH:MM] texto'.
    `agora` é injetável (teste). Usado no roteamento FEDERAL da obs rápida, cuja
    porta (atualizar_deputado_federal) grava a célula RAW e NÃO anexa sozinha.
    PURA e testável. Texto vazio devolve o atual intacto."""
    texto = str(texto or "").strip()
    atual = str(atual or "").strip()
    if not texto:
        return atual
    if agora is None:
        agora = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")
    nova = f"[{agora}] {texto}"
    return f"{atual}\n{nova}".strip() if atual else nova


def plano_obs(escopo: str, chave: str, nota: str, atual: str = "") -> dict:
    """Roteamento PURO da observação rápida do funil por escopo. Devolve o que a
    casca (dlg_obs_rapida) deve executar — sem tocar em Streamlit nem no Sheets:

      estadual → {'porta':'estadual','nome':chave,'texto':nota}   (a porta
                 anexar_dialogo_deputado faz o append+carimbo por dentro)
      federal  → {'porta':'federal','id':chave,
                  'campos':{'Diálogo': compor_dialogo(atual,nota)}}  (append+carimbo
                 aqui; grava por ID via atualizar_deputado_federal)
      senador  → {'porta':'senador','id':chave,
                  'campos':{'Diálogo': compor_dialogo(atual,nota)}}  (espelha o
                 federal; grava por ID via atualizar_senador)
      outro    → {'porta': None}   (escopo desconhecido — sem gravação)

    REGRA DE EIXO: a obs grava só o Diálogo (observação); NUNCA 'Status CRM' (etapa)."""
    escopo = str(escopo or "").strip().lower()
    if escopo == "estadual":
        return {"porta": "estadual", "nome": chave, "texto": nota}
    if escopo == "federal":
        return {"porta": "federal", "id": chave,
                "campos": {"Diálogo": compor_dialogo(atual, nota)}}
    if escopo == "senador":
        return {"porta": "senador", "id": chave,
                "campos": {"Diálogo": compor_dialogo(atual, nota)}}
    return {"porta": None}


def funil_parlamentares_colunas(regs: list) -> list:
    """Colunas do kanban do FUNIL GERAL (Passo 5), a partir dos parlamentares já
    unificados (carregar_parlamentares). Função PURA (sem st), testável.

    Cada card leva `id = escopo\\x01chave` (roteia a escrita no drop) e mostra, no
    meta, o PARTIDO · ESCOPO, o SCORE e a TEMPERATURA. REGRA DE OURO: o funil NÃO
    exibe nem soma valor — execução estadual e faixa federal nunca se encontram
    aqui; só status/score/temperatura, escopo a escopo."""
    colunas = []
    for etapa in EMENDA_FUNIL_ETAPAS:
        cards = [{
            "id": _id_card_parlamentar(r), "status": etapa, "nome": r["nome"],
            "setor": f'{r.get("partido") or "—"} · {r.get("escopo_nome", "")}'.strip(" ·"),
            "score": int(r.get("score") or 0),
            "valor": f'{r.get("temp_emoji", "")} {r.get("temp", "")}'.strip(),
        } for r in regs if _etapa_de_status(r.get("status", "")) == etapa]
        colunas.append({"status": etapa, "cor": EMENDA_ETAPA_COR[etapa], "cards": cards})
    return colunas


def _dep_item_relatorio(row: dict, secao: str) -> dict:
    nome = str(row.get("deputado", "")).strip()
    if secao == "territorio":
        aut, pago, score = row.get("autorizado_pfc", 0), row.get("pago_pfc", 0), row.get("score_pfc", 0)
    else:
        aut, pago = row.get("autorizado_geral_edusoc", 0), row.get("pago_geral_edusoc", 0)
        score = row.get("score_expansao", 0)
    ct = dados.contato_oficial(nome)
    return {
        "deputado": nome, "partido": str(row.get("partido", "")).strip() or "—",
        "municipios": _muns_pfc(row, secao),
        "autorizado": brl(aut), "pago": brl(pago),
        "score": str(round(float(score or 0))),
        "email": ct.get("email", ""), "telefone": ct.get("telefone", ""),
    }


def _itens_relatorio_emendas():
    """(território, expansão) do levantamento. Território todo; expansão só os
    alvos prioritários (o conjunto acionável de 'quem cortejar')."""
    terr_df = dados.carregar_ranking_territorio()
    exp_df = dados.carregar_ranking_expansao()
    territorio = [_dep_item_relatorio(r, "territorio") for _, r in terr_df.iterrows()] \
        if not terr_df.empty else []
    if not exp_df.empty:
        pri = exp_df[exp_df["camada"] == "alvo prioritário"] if "camada" in exp_df else exp_df
        expansao = [_dep_item_relatorio(r, "expansao") for _, r in pri.iterrows()]
    else:
        expansao = []
    return territorio, expansao


def _tabela_emendas_html(itens: list) -> str:
    linhas = ""
    for i, d in enumerate(itens, start=1):
        contato = "<br>".join(x for x in (d["email"], d["telefone"])
                              if x and x != "não encontrado") or "—"
        linhas += (
            f'<tr><td class="rp-n">{i}</td>'
            f'<td><div class="rp-nome">{esc(d["deputado"])}</div>'
            f'<div class="rp-sub">{esc(d["partido"])}</div></td>'
            f'<td>{esc(d["municipios"])}</td>'
            f'<td>aut. <b style="color:var(--ink)">{esc(d["autorizado"])}</b><br>'
            f'<span style="color:var(--dim)">pago {esc(d["pago"])}</span></td>'
            f'<td style="font-weight:700;color:#8B7BF0">{esc(d["score"])}</td>'
            f'<td class="rp-sub">{contato}</td></tr>')
    return ('<table class="rp"><tr><th>#</th><th>Deputado</th><th>Municípios do PFC</th>'
            '<th>Educação / social</th><th>Score</th><th>Contato oficial</th></tr>'
            f'{linhas}</table>')


# =========================================================================== #
# RELATÓRIO GERAL de Emendas (Passo 6) — CRM unificado de todos os escopos.
# Funções PURAS (sem st, sem reportlab), testáveis. A regra de ouro vive aqui:
# cada linha carrega o valor JÁ ROTULADO pelo seu valor_tipo (rotulo_valor) e
# NÃO existe campo de total — este relatório lista e CONTA, nunca soma valor.
# --------------------------------------------------------------------------- #
def itens_relatorio_parlamentares(regs: list) -> list:
    """Linhas do relatório geral, uma por parlamentar, a partir dos registros
    unificados (carregar_parlamentares). Cada linha traz `valor_rotulo` do tipo
    correto (execução/sugerido/CRM) — nunca co-rotula errado — e nenhum total."""
    return [{
        "escopo": r.get("escopo", ""),
        "escopo_nome": r.get("escopo_nome", ""),
        "nome": r.get("nome", ""),
        "partido": r.get("partido", "") or "—",
        "score": str(_int0(r.get("score"))),
        "ader": str(_int0(r.get("ader"))),
        "chance": str(_int0(r.get("chance"))),
        "temp": r.get("temp", "") or "—",
        "status": r.get("status", "") or "—",
        "valor_txt": str(r.get("valor_txt", "") or "").strip(),
        "valor_rotulo": rotulo_valor(r.get("valor_tipo", "")),
    } for r in regs]


def resumo_relatorio_parlamentares(regs: list) -> dict:
    """Contagens do relatório geral — SÓ números de pipeline, nunca dinheiro (a
    regra de ouro proíbe agregar valor entre escopos). {total, em_articulacao,
    reunioes, aprovadas}. Mesma leitura de status da capa (Passo 3)."""
    def _s(r):
        return str(r.get("status", "")).lower()
    total = len(regs)
    nao_iniciado = sum(1 for r in regs if "não iniciado" in _s(r) or "nao iniciado" in _s(r))
    reunioes = sum(1 for r in regs if _s(r).startswith(("reunião", "reuniao")))
    aprovadas = sum(1 for r in regs if "aprovada" in _s(r))
    return {"total": total, "em_articulacao": total - nao_iniciado,
            "reunioes": reunioes, "aprovadas": aprovadas}


def _tabela_parlamentares_html(linhas: list) -> str:
    """Tabela HTML da Seção 1 (on-screen), na mesma classe .rp da tela. Valor
    rotulado por linha; sem total (regra de ouro)."""
    corpo = ""
    for i, d in enumerate(linhas, start=1):
        valor = esc(d["valor_txt"]) if d["valor_txt"] else ""
        rot = f'<div class="rp-sub">{esc(d["valor_rotulo"])}</div>'
        corpo += (
            f'<tr><td class="rp-n">{i}</td>'
            f'<td><div class="rp-nome">{esc(d["nome"])}</div>'
            f'<div class="rp-sub">{esc(d["partido"])} · {esc(d["escopo_nome"])}</div></td>'
            f'<td style="font-weight:700;color:#8B7BF0">{esc(d["score"])}</td>'
            f'<td>{esc(d["temp"])}</td>'
            f'<td>{esc(d["status"])}</td>'
            f'<td>{valor}{rot}</td></tr>')
    return ('<table class="rp"><tr><th>#</th><th>Parlamentar</th><th>Score</th>'
            '<th>Temperatura</th><th>Status</th><th>Valor (rotulado)</th></tr>'
            f'{corpo}</table>')


def _data_prazo(prazo):
    """Data do prazo: primeiro ISO (AAAA-MM-DD, como o radar grava), depois
    formatos livres via _parse_data. O ISO precisa vir ANTES porque a regex
    dd/mm/aaaa acharia '26-07-29' dentro de '2026-07-29'."""
    s = str(prazo or "").strip()
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        return _parse_data(s)


def _dias_novidade(nv: dict):
    """Dias restantes da novidade, SEMPRE recalculado da data (a coluna
    'Dias restantes' da planilha congela no dia da gravação e envelhece);
    a coluna é só fallback para prazos não parseáveis."""
    d = _data_prazo(nv.get("Prazo", ""))
    if d:
        return (d - datetime.date.today()).days
    try:
        return int(str(nv.get("Dias restantes", "")).strip())
    except (TypeError, ValueError):
        return None


def _fmt_prazo(prazo: str) -> str:
    """Prazo legível dd/mm; texto livre passa como veio."""
    d = _data_prazo(prazo)
    return d.strftime("%d/%m") if d else (str(prazo).strip() or "—")


def _prazo_confiavel(dias) -> bool:
    """O extrator do radar assume 'próximo ano futuro' quando a data vem sem
    ano — um prazo a 200+ dias (ou vencido há muito) provavelmente é esse
    chute. Uma data errada é pior que nenhuma: fora da janela [-60, 180]
    dias, o app mostra 'prazo a confirmar' em vez do número."""
    return isinstance(dias, int) and -60 <= dias <= 180


def _op_de_novidade(nv: dict) -> dict:
    return {"titulo": str(nv.get("Título", "")).strip() or "(sem título)",
            "fonte": str(nv.get("Fonte", "")).strip() or "Radar",
            "score": int(_score_novidade(nv)),
            "valor": str(nv.get("Valor estimado", "")).strip(),
            "prazo": str(nv.get("Prazo", "")).strip(),
            "dias": _dias_novidade(nv),
            "link": str(nv.get("Link da fonte", "")).strip(),
            "desc": str(nv.get("Descrição", "")).strip(),
            "nv": nv}


def _hoje_sp() -> datetime.date:
    """Hoje em America/São_Paulo (o radar é de SP; o servidor pode estar em UTC).
    Cai para date.today() se o zoneinfo não estiver disponível."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    except Exception:
        return datetime.date.today()


def _op_vencida(op: dict, hoje: datetime.date | None = None) -> bool:
    """True se o item tem prazo CONFIÁVEL (_prazo_confiavel) e a data JÁ PASSOU
    (vencido) relativo a hoje em SP. Itens 'prazo a confirmar' (data não confiável)
    NÃO são vencidos aqui — continuam passando. É o corte final da FILA; o scorer
    não muda. Sem data parseável → não é vencido (na dúvida, mantém)."""
    if not _prazo_confiavel(op.get("dias")):
        return False
    d = _data_prazo(op.get("prazo", ""))
    if d is None:
        return False
    return d < (hoje or _hoje_sp())


def _score_novidade(nv) -> float:
    try:
        return float(str(nv.get("Score Aderência", "")).replace(",", ".") or 0)
    except (TypeError, ValueError):
        return 0.0


def _valor_rel(v) -> str:
    """Valor legível: número vira R$; texto livre do radar ('R$ 80 mil') passa."""
    try:
        n = float(v)
        return brl(n) if n > 0 else "—"
    except (TypeError, ValueError):
        return str(v).strip() or "—"


def _dias_texto(dias) -> str:
    if not isinstance(dias, int):
        return "prazo a confirmar"
    if dias < 0:
        return f"vencida há {-dias} dia(s)"
    if dias == 0:
        return "encerra hoje"
    return f"faltam {dias} dia(s)"
