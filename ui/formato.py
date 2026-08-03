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


def css_icones_botoes(mapa: dict, rotulos: dict | None = None) -> str:
    """CSS dos botões da sidebar. mapa: {chave do botão: ícone}.

    Faz três coisas, todas escopadas às chaves do mapa:
      1. desenha o ícone (::before do container de markdown, via mask-image);
      2. no modo ícone, esconde o texto do rótulo;
      3. mostra o nome como tooltip no hover (::after do botão), a partir de
         `rotulos` = {chave: nome}.

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
