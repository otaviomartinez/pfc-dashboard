"""
Dashboard de Inteligência de Captação (PFC)
===========================================
App Streamlit sincronizado com Google Sheets (ao vivo) com fallback para CSV.

Rodar:  streamlit run app.py
"""
from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from src import dados
from src.dados import (
    COL_CANAL, COL_CHANCE, COL_EDITAL, COL_EMPRESA, COL_ENCAIXE, COL_ID,
    COL_INSTITUTO, COL_JANELA, COL_MODALIDADE, COL_OBS, COL_PRESENCA,
    COL_PRIORIDADE, COL_PROPOSTA, COL_PROX_ACAO, COL_PUBLICO, COL_REGIAO,
    COL_RESP, COL_SCORE, COL_SEDE, COL_SEMAFORO, COL_SETOR, COL_SOCIAL,
    COL_STATUS, COL_SUBSETOR, COL_TIPO, COL_UF, COL_URL, COL_VALVO, COL_VERIF,
    COL_VMAX, COL_VMIN, STATUS_FUNIL,
)

# --------------------------------------------------------------------------- #
# Configuração da página
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="PFC · Inteligência de Captação",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --------------------------------------------------------------------------- #
# Tema escuro + CSS custom (paleta derivada da logo do PFC)
# --------------------------------------------------------------------------- #
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root{
  --bg:#0B0D10; --surface:#13161B; --surface-2:#191D24; --raise:#1F242C;
  --line:rgba(255,255,255,.07); --line-2:rgba(255,255,255,.13);
  --text:#F2F0E9; --muted:#969CA6; --dim:#666C75;
  --orange:#F2911E; --orange-2:#FFB454; --orange-soft:rgba(242,145,30,.13);
  --green:#5FB137; --green-2:#A6DD86; --green-soft:rgba(95,177,55,.14);
  --blue:#3B8BD0; --blue-2:#86C0EC; --blue-soft:rgba(59,139,208,.14);
  --red:#E25640; --red-soft:rgba(226,86,64,.14);
  --r:10px; --r-lg:14px;
  --disp:'Space Grotesk',system-ui,sans-serif; --body:'Inter',system-ui,sans-serif;
}
html, body, [class*="css"]{font-family:var(--body);}
.stApp{
  background:var(--bg);
  background-image:radial-gradient(1000px 560px at 80% -10%, rgba(59,139,208,.07), transparent 60%),
                   radial-gradient(720px 440px at 4% 2%, rgba(242,145,30,.05), transparent 55%);
}
/* Neutraliza a barra fixa do Streamlit (que sobrepunha/cortava a logo) */
[data-testid="stHeader"]{display:none;height:0;}
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"]{display:none!important;}
[data-testid="stAppViewContainer"]{overflow:visible;}
[data-testid="stAppViewContainer"] > .main, .main .block-container{overflow:visible;}
.block-container{max-width:1240px;padding-top:2.4rem!important;padding-bottom:3rem;margin:0 auto;}
@media (min-width:1700px){.block-container{max-width:1320px;}}
h1,h2,h3,h4{font-family:var(--disp);letter-spacing:-.01em;color:var(--text);}

/* ---------- header ---------- */
.brand{display:flex;align-items:center;gap:13px;overflow:visible;min-width:0;flex-wrap:nowrap}
.brand svg{flex:none;display:block}
.brand>div{min-width:0}
.brand .wm{font-family:var(--disp);font-weight:700;font-size:15px;letter-spacing:.04em;color:var(--orange);line-height:1.2;text-transform:uppercase;white-space:nowrap}
.brand .sub{font-size:12.5px;color:var(--muted)}
.topR{display:flex;align-items:center;gap:12px;justify-content:flex-end;flex-wrap:wrap}
.pill{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;font-weight:500;padding:6px 12px;border-radius:999px}
.pill.ok{background:var(--green-soft);border:1px solid rgba(95,177,55,.32);color:var(--green-2)}
.pill.local{background:var(--orange-soft);border:1px solid rgba(242,145,30,.32);color:var(--orange-2)}
.selo-wrap{margin:10px 0 2px}
.dot{width:7px;height:7px;border-radius:50%;background:currentColor;animation:pulse 2.4s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(95,177,55,.45)}70%{box-shadow:0 0 0 7px rgba(95,177,55,0)}100%{box-shadow:0 0 0 0 rgba(95,177,55,0)}}
.date{font-size:13px;color:var(--muted)}
.avatar{width:34px;height:34px;border-radius:50%;background:var(--orange-soft);border:1px solid rgba(242,145,30,.35);color:var(--orange-2);display:grid;place-items:center;font-family:var(--disp);font-weight:600;font-size:13px}
.hr-line{height:1px;background:var(--line);margin:14px 0 4px}

/* ---------- tabs ---------- */
.stTabs [data-baseweb="tab-list"]{gap:2px;border-bottom:1px solid var(--line);}
.stTabs [data-baseweb="tab"]{background:transparent;color:var(--muted);font-family:var(--body);font-weight:500;font-size:14px;padding:10px 16px;}
.stTabs [data-baseweb="tab"]:hover{color:var(--text);}
.stTabs [aria-selected="true"]{color:var(--orange-2)!important;}
.stTabs [data-baseweb="tab-highlight"]{background:var(--orange)!important;height:2px;}
.stTabs [data-baseweb="tab-border"]{background:transparent;}

/* ---------- phead ---------- */
.phead h1{font-family:var(--disp);font-weight:600;font-size:24px;margin-bottom:2px}
.phead p{color:var(--muted);font-size:13.5px;margin:0 0 4px}

/* ---------- cards & kpis ---------- */
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-lg);overflow:hidden;margin-bottom:16px}
.card-h{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:15px 18px 13px;border-bottom:1px solid var(--line)}
.card-h h2{font-family:var(--disp);font-weight:600;font-size:15.5px;margin:0}
.card-h .cap{font-size:12px;color:var(--dim);margin-top:1px}
.pad{padding:16px 18px}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:16px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-lg);padding:16px 17px;position:relative;overflow:hidden}
.kpi::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--accent,var(--blue))}
.kpi .lab{display:flex;align-items:center;gap:7px;font-size:12.5px;color:var(--muted);font-weight:500}
.kpi .val{font-family:var(--disp);font-weight:600;font-size:31px;letter-spacing:-.02em;margin:9px 0 2px;line-height:1}
.kpi .foot{font-size:12px;color:var(--dim)} .kpi .foot b{color:var(--muted);font-weight:500}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media (max-width:900px){.kpis{grid-template-columns:repeat(2,1fr)}.g2{grid-template-columns:1fr}}

/* ---------- funil bar ---------- */
.funil{display:flex;height:13px;border-radius:6px;overflow:hidden;margin:4px 0 14px}
.funil i{display:block;height:100%}
.fleg{display:flex;flex-wrap:wrap;gap:14px}
.fleg span{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted)}
.fleg .sw{width:9px;height:9px;border-radius:3px} .fleg b{color:var(--text);font-family:var(--disp);font-weight:600}
.muni{display:flex;flex-wrap:wrap;gap:8px}
.mtag{font-size:12px;color:var(--text);background:var(--surface-2);border:1px solid var(--line);padding:6px 12px;border-radius:999px;display:inline-flex;align-items:center;gap:7px}
.mtag .pin{width:5px;height:5px;border-radius:50%;background:var(--green)}
.mtag.next{border-style:dashed;color:var(--muted)} .mtag.next .pin{background:var(--orange)}

/* ---------- ranking rows ---------- */
.org{display:flex;align-items:center;gap:11px}
.sem{width:9px;height:9px;border-radius:50%;flex:none}
.org .nm{font-weight:500;color:var(--text);font-size:14px}
.org .st{font-size:11.5px;color:var(--dim)}
.scorecell{display:flex;align-items:center;gap:11px}
.scoreN{font-family:var(--disp);font-weight:600;font-size:17px;width:26px}
.segbar{flex:1;max-width:118px;height:7px;border-radius:4px;background:var(--line-2);display:flex;overflow:hidden;gap:1.5px}
.segbar i{display:block;height:100%}
.stat{font-size:11.5px;font-weight:500;padding:3px 9px;border-radius:6px;white-space:nowrap}
.s-pros{background:var(--orange-soft);color:var(--orange-2)}
.s-moni{background:var(--blue-soft);color:var(--blue-2)}
.s-edit{background:var(--green-soft);color:var(--green-2)}
.s-map{background:rgba(255,255,255,.05);color:var(--muted)}
.alvo{font-family:var(--disp);font-weight:500;text-align:right;color:var(--text);white-space:nowrap;font-size:13.5px}
.rkhead{display:grid;grid-template-columns:2.4fr 1.5fr 1fr 1fr;gap:8px;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--dim);font-weight:600;padding:6px 4px 2px}
.rkhead .r{text-align:right}
[data-testid="stHorizontalBlock"]:has(.org){border-bottom:1px solid var(--line);padding:2px 0;align-items:center}

/* ---------- kanban ---------- */
.kan{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;align-items:start}
@media (max-width:900px){.kan{grid-template-columns:1fr 1fr}}
.kcol{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-lg);overflow:hidden}
.kcol-h{display:flex;align-items:center;justify-content:space-between;padding:11px 13px;border-bottom:1px solid var(--line);font-size:12.5px;font-weight:600}
.kcol-h .ct{font-family:var(--disp);font-size:11px;color:var(--muted);background:var(--surface-2);padding:1px 7px;border-radius:999px}
.kcol-h .accent{width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:7px;vertical-align:middle}
.kbody{padding:10px;display:flex;flex-direction:column;gap:9px;min-height:60px}
.kcard{background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:10px 11px}
.kcard .kn{font-size:12.5px;font-weight:500;line-height:1.3}
.kcard .ks{font-size:11px;color:var(--dim);margin-top:2px}
.kcard .kf{display:flex;align-items:center;justify-content:space-between;margin-top:8px}
.kchip{font-family:var(--disp);font-weight:600;font-size:11px;padding:1px 7px;border-radius:6px}
.kval{font-size:11px;color:var(--muted)}
.kmore{font-size:11.5px;color:var(--dim);text-align:center;padding:6px;border:1px dashed var(--line-2);border-radius:8px}

/* ---------- radar leads ---------- */
.lead{padding:14px 16px;border:1px solid var(--line);border-radius:12px;background:var(--surface);margin-bottom:10px}
.lead-top{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:6px}
.src{display:inline-flex;align-items:center;gap:6px;font-size:11px;font-weight:600;letter-spacing:.03em;color:var(--blue);background:var(--blue-soft);padding:3px 9px;border-radius:6px;text-transform:uppercase}
.fit{font-family:var(--disp);font-weight:600;font-size:13px}
.fit.hi{color:var(--green)} .fit.mid{color:var(--orange-2)} .fit.lo{color:var(--red)}
.lead .ttl{font-weight:500;font-size:13.5px;color:var(--text);margin-bottom:3px}
.lead .why{font-size:12px;color:var(--muted);line-height:1.45}
.lead .meta{font-size:12px;color:var(--muted);margin-top:8px}
.lead .meta b{color:var(--text);font-weight:500}
.lead.rej{background:var(--red-soft);border-color:rgba(226,86,64,.3)}
.lead.rej .ttl{color:var(--muted);text-decoration:line-through}
.rej-tag{font-size:11px;color:var(--red);font-weight:500}
.srclink{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;color:var(--blue-2)!important;text-decoration:none;background:var(--blue-soft);border:1px solid rgba(59,139,208,.3);padding:7px 11px;border-radius:9px;margin-top:8px}
.src-tag{display:inline-block;font-size:11px;color:var(--blue-2);background:var(--blue-soft);border:1px solid rgba(59,139,208,.22);padding:4px 9px;border-radius:7px;margin:0 5px 6px 0}
.note{font-size:11.5px;color:var(--dim);line-height:1.5;margin-top:10px}
.statline{display:flex;justify-content:space-between;font-size:13px;padding:3px 0}
.statline b{font-family:var(--disp)}

/* ---------- methodology ---------- */
.legend{display:flex;flex-direction:column;gap:13px}
.lrow{display:grid;grid-template-columns:1fr auto;align-items:center;gap:10px}
.lrow .nm{font-size:13px;color:var(--text);display:flex;align-items:center;gap:8px}
.lrow .nm .sw{width:9px;height:9px;border-radius:3px;flex:none}
.lrow .wt{font-family:var(--disp);font-weight:600;font-size:13px;color:var(--muted)}
.ltrack{grid-column:1/-1;height:5px;border-radius:3px;background:var(--line-2);overflow:hidden;margin-top:-4px}
.ltrack i{display:block;height:100%;border-radius:3px}
.divider{height:1px;background:var(--line);margin:15px 0}
.sub{display:grid;grid-template-columns:150px 1fr 32px;align-items:center;gap:10px;font-size:12px;margin-bottom:9px}
.sub .l{color:var(--muted)}
.sub .t2{height:6px;border-radius:3px;background:var(--line-2);overflow:hidden}
.sub .t2 i{display:block;height:100%;border-radius:3px}
.sub .n{font-family:var(--disp);font-weight:600;color:var(--text);text-align:right}

/* ---------- dialog (dossiê) ---------- */
.dr-eyebrow{display:flex;align-items:center;gap:8px;font-size:11.5px;color:var(--dim);margin-bottom:6px}
.dr-sub{font-size:12.5px;color:var(--muted);margin:2px 0 6px}
.dr-score{font-family:var(--disp);font-weight:700;font-size:28px;line-height:1}
.dr-score small{font-size:13px;color:var(--muted);font-weight:400}
.dr-seg{height:8px;border-radius:5px;background:var(--line-2);display:flex;overflow:hidden;gap:2px;margin-top:8px}
.dr-seg i{display:block;height:100%}
.dr-sec h3{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--orange-2);font-weight:600;margin:14px 0 8px}
.frow{display:grid;grid-template-columns:130px 1fr;gap:10px;padding:4px 0;font-size:13px}
.frow .fl{color:var(--muted);font-size:12.5px}
.frow .fv{color:var(--text)}
.fblock .fl{color:var(--muted);font-size:12px;margin:6px 0 3px}
.fblock .fv{color:var(--text);font-size:13px;line-height:1.5;background:var(--surface-2);border:1px solid var(--line);border-radius:9px;padding:10px 12px}
.vbadge{font-size:11px;font-weight:500;padding:2px 9px;border-radius:6px;margin-left:8px}
.vb-ok{background:var(--green-soft);color:var(--green-2)} .vb-no{background:var(--orange-soft);color:var(--orange-2)}
.ncard{background:var(--surface-2);border:1px solid var(--line);border-left:2px solid var(--blue);border-radius:10px;padding:9px 12px;margin-bottom:8px;font-size:12.5px;color:var(--text);line-height:1.5;white-space:pre-wrap}

/* ---------- streamlit widget polish ---------- */
.stButton>button{border-radius:9px;border:1px solid var(--line-2);background:var(--surface-2);color:var(--text);font-size:12.5px;padding:5px 12px;}
.stButton>button:hover{border-color:var(--orange);color:var(--orange-2);}
div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] div{font-size:13px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Helpers de formatação
# --------------------------------------------------------------------------- #
def esc(v) -> str:
    return html.escape("" if v is None else str(v))


def texto_ou(v, padrao: str = "—") -> str:
    """Devolve o texto escapado ou o padrão quando vazio/ausente."""
    s = "" if v is None else str(v).strip()
    return esc(s) if s and s.lower() != "nan" else padrao


def brl(v) -> str:
    """R$ 175.000 (formato pt-BR) ou — quando ausente."""
    try:
        n = float(v)
    except (TypeError, ValueError):
        return "—"
    if n <= 0:
        return "—"
    return "R$ " + f"{n:,.0f}".replace(",", ".")


def brl_curto(v) -> str:
    """Forma curta: R$ 175 mil / R$ 8,28 mi."""
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
    return {
        "Prospectar": "s-pros",
        "Monitorar": "s-moni",
        "Edital": "s-edit",
        "Ativo": "s-edit",
        "Mapear": "s-map",
    }.get(str(status).strip(), "s-map")


def status_badge(status: str) -> str:
    txt = esc(status) if str(status).strip() else "—"
    return f'<span class="stat {status_classe(status)}">{txt}</span>'


def seg_html(score: float, classe: str = "segbar") -> str:
    """Decomposição visual do score pelos 4 pesos fixos (ilustrativa)."""
    try:
        s = max(0.0, min(100.0, float(score))) / 100.0
    except (TypeError, ValueError):
        s = 0.0
    pesos = [0.35, 0.25, 0.20, 0.20]
    cores = ["var(--orange)", "var(--green)", "var(--blue)", "var(--muted)"]
    partes = "".join(
        f'<i style="width:{w * s * 100:.1f}%;background:{c}"></i>'
        for w, c in zip(pesos, cores)
    )
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


def verificada_ok(valor: str) -> bool:
    v = str(valor).lower()
    return "verificada" in v and "não" not in v and "nao" not in v


# --------------------------------------------------------------------------- #
# Carregamento de dados (modo_conectado decide o selo e a escrita)
# --------------------------------------------------------------------------- #
df, modo_conectado = dados.carregar_empresas()
TOTAL = len(df)
HINT_ESCRITA = "🔒 Conecte ao Google Sheets para habilitar escrita."


# --------------------------------------------------------------------------- #
# Cabeçalho com selo de modo logo abaixo da logo
# --------------------------------------------------------------------------- #
def render_header():
    if modo_conectado:
        selo = '<span class="pill ok"><span class="dot"></span> 🟢 Conectado ao Google Sheets</span>'
    else:
        selo = '<span class="pill local">🟠 Modo local (CSV) — escrita desabilitada</span>'
    hoje = pd.Timestamp.now().strftime("%d/%m/%Y")
    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.markdown(
            """
            <div class="brand">
              <svg width="40" height="40" viewBox="0 0 42 42" aria-hidden="true">
                <circle cx="21" cy="21" r="18" fill="none" stroke="#3B8BD0" stroke-opacity=".55" stroke-width="1.4"/>
                <circle cx="21" cy="21" r="11.5" fill="none" stroke="#3B8BD0" stroke-opacity=".32" stroke-width="1.2"/>
                <g stroke="#5FB137" stroke-width="1.7" stroke-linecap="round">
                  <line x1="21" y1="13.5" x2="21" y2="28.5"/><line x1="13.5" y1="21" x2="28.5" y2="21"/>
                  <line x1="15.7" y1="15.7" x2="26.3" y2="26.3"/><line x1="26.3" y1="15.7" x2="15.7" y2="26.3"/>
                </g>
                <circle cx="21" cy="21" r="2.6" fill="#5FB137"/>
              </svg>
              <div>
                <div class="wm">Programa Futuro Cientista</div>
                <div class="sub">Inteligência de Captação</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        # Selo de modo — logo ABAIXO da logo do PFC.
        st.markdown(f'<div class="selo-wrap">{selo}</div>', unsafe_allow_html=True)
    with col_b:
        st.markdown(
            f'<div class="topR"><span class="date">{hoje}</span>'
            f'<span class="avatar" title="Fábio de Lima Leite">FL</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown('<div class="hr-line"></div>', unsafe_allow_html=True)


render_header()

if df.empty:
    st.warning("Nenhuma organização encontrada na base. Verifique o arquivo "
               "`data/empresas.csv` ou a planilha do Google Sheets.")


# --------------------------------------------------------------------------- #
# Callbacks de escrita (rodam ANTES do corpo: o cache já estará limpo na releitura)
# --------------------------------------------------------------------------- #
def _cb_mudar_status(org_id, sel_key):
    novo = st.session_state.get(sel_key)
    st.session_state[f"status_msg_{org_id}"] = dados.atualizar_status(org_id, novo)


def _cb_salvar_obs(org_id, ta_key):
    texto = st.session_state.get(ta_key, "")
    res = dados.salvar_observacao(org_id, texto)
    st.session_state[f"obs_msg_{org_id}"] = res
    if res.get("sucesso"):
        st.session_state[ta_key] = ""  # limpa o campo após salvar


def _mostrar_resultado(res: dict | None):
    if not res:
        return
    if res.get("sucesso"):
        st.success(res.get("mensagem", "Operação concluída."))
    else:
        st.warning(res.get("mensagem", "Não foi possível concluir."))


# --------------------------------------------------------------------------- #
# Dossiê (st.dialog) — todos os campos + salvar observação + mudar status
# --------------------------------------------------------------------------- #
@st.dialog("Dossiê da organização", width="large")
def mostrar_dossie(org: dict):
    org_id = org.get(COL_ID)

    # Re-busca a organização na base atual (reflete escritas recém-gravadas).
    base = dados.carregar_empresas()[0]
    if not base.empty:
        m = base[base[COL_ID].astype(str).str.strip() == str(org_id).strip()]
        if not m.empty:
            org = m.iloc[0].to_dict()

    nome = str(org.get(COL_EMPRESA, "")).strip()
    score = float(org.get(COL_SCORE, 0) or 0)
    cor_score = "var(--green)" if score >= 85 else "var(--orange-2)" if score >= 70 else "var(--muted)"
    faixa = "—"
    if brl(org.get(COL_VMIN)) != "—" and brl(org.get(COL_VMAX)) != "—":
        faixa = f"{brl(org.get(COL_VMIN))} – {brl(org.get(COL_VMAX))}"
    chance = org.get(COL_CHANCE, 0)
    chance_txt = f"{int(float(chance))}%" if str(chance).strip() not in ("", "0", "0.0") else "—"
    vok = verificada_ok(org.get(COL_VERIF))
    url = str(org.get(COL_URL, "")).strip()
    url_ok = url.startswith("http")

    # Cabeçalho do dossiê
    st.markdown(
        f"""
        <div class="dr-eyebrow"><span style="width:8px;height:8px;border-radius:50%;
            background:{sem_cor(org.get(COL_SEMAFORO))};display:inline-block"></span>
            {texto_ou(org.get(COL_PRIORIDADE))} · {texto_ou(org.get(COL_SETOR))}</div>
        <h2 style="margin:0;font-size:21px">{esc(nome) or '—'}</h2>
        <div class="dr-sub">{esc(' · '.join([s for s in [str(org.get(COL_INSTITUTO,'')).strip(),
            str(org.get(COL_SUBSETOR,'')).strip()] if s]) or '—')}</div>
        <div style="display:flex;align-items:center;gap:16px;margin-top:6px">
          <div class="dr-score" style="color:{cor_score}">{int(score)}<small> / 100</small></div>
          <div style="flex:1">{seg_html(score, classe='dr-seg')}</div>
        </div>
        <div style="font-size:10.5px;color:var(--dim);margin-top:4px">
            decomposição ilustrativa: aderência · valor · região · acionabilidade</div>
        """,
        unsafe_allow_html=True,
    )

    # Seções de campos
    st.markdown(
        f"""
        <div class="dr-sec">
          <h3>📈 Captação</h3>
          <div class="frow"><span class="fl">Tipo</span><span class="fv">{texto_ou(org.get(COL_TIPO))}</span></div>
          <div class="frow"><span class="fl">Modalidade</span><span class="fv">{texto_ou(org.get(COL_MODALIDADE))}</span></div>
          <div class="frow"><span class="fl">Chance de êxito</span><span class="fv">{chance_txt}</span></div>
          <div class="frow"><span class="fl">Faixa de valor</span><span class="fv">{faixa}</span></div>
          <div class="frow"><span class="fl">Valor-alvo</span><span class="fv">{brl(org.get(COL_VALVO))}</span></div>
          <div class="frow"><span class="fl">Janela</span><span class="fv">{texto_ou(org.get(COL_JANELA))}</span></div>
          <div class="frow"><span class="fl">Edital / programa</span><span class="fv">{texto_ou(org.get(COL_EDITAL))}</span></div>
        </div>
        <div class="dr-sec">
          <h3>🎯 Alinhamento com o PFC</h3>
          <div class="fblock"><div class="fl">Público-alvo</div><div class="fv">{texto_ou(org.get(COL_PUBLICO))}</div></div>
          <div class="fblock"><div class="fl">Encaixe com o PFC</div><div class="fv">{texto_ou(org.get(COL_ENCAIXE))}</div></div>
          <div class="fblock"><div class="fl">Proposta recomendada</div><div class="fv">{texto_ou(org.get(COL_PROPOSTA))}</div></div>
        </div>
        <div class="dr-sec">
          <h3>📍 Território</h3>
          <div class="frow"><span class="fl">Presença PFC</span><span class="fv">{texto_ou(org.get(COL_PRESENCA))}</span></div>
          <div class="frow"><span class="fl">Região</span><span class="fv">{texto_ou(org.get(COL_REGIAO))}</span></div>
          <div class="frow"><span class="fl">Sede</span><span class="fv">{texto_ou(org.get(COL_SEDE))}</span></div>
          <div class="frow"><span class="fl">UF</span><span class="fv">{texto_ou(org.get(COL_UF))}</span></div>
        </div>
        <div class="dr-sec">
          <h3>✉️ Contato &amp; próxima ação</h3>
          <div class="fblock"><div class="fl">Próxima ação</div><div class="fv">{texto_ou(org.get(COL_PROX_ACAO))}</div></div>
          <div class="frow"><span class="fl">Responsável</span><span class="fv">{texto_ou(org.get(COL_RESP))}</span></div>
          <div class="frow"><span class="fl">Canal</span><span class="fv">{texto_ou(org.get(COL_CANAL))}</span></div>
          <div class="frow"><span class="fl">Social</span><span class="fv">{texto_ou(org.get(COL_SOCIAL))}</span></div>
        </div>
        <div class="dr-sec">
          <h3>🔗 Fonte <span class="vbadge {'vb-ok' if vok else 'vb-no'}">{'✓ verificado' if vok else 'a verificar'}</span></h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if url_ok:
        st.markdown(
            f'<a class="srclink" href="{esc(url)}" target="_blank" rel="noopener">↗ {esc(url)}</a>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="font-size:12.5px;color:var(--orange-2)">Site oficial ainda a confirmar.</div>',
            unsafe_allow_html=True,
        )

    # ----- Status (grava ao mudar) -----
    st.markdown('<div class="dr-sec"><h3>🔄 Mudar status (grava na planilha)</h3></div>',
                unsafe_allow_html=True)
    opcoes = list(STATUS_FUNIL)
    atual = str(org.get(COL_STATUS, "")).strip()
    if atual and atual not in opcoes:
        opcoes.append(atual)
    idx = opcoes.index(atual) if atual in opcoes else 0
    key_status = f"status_{org_id}"
    st.selectbox(
        "Status", opcoes, index=idx, key=key_status,
        on_change=_cb_mudar_status, args=(org_id, key_status),
        disabled=not modo_conectado, label_visibility="collapsed",
    )
    _mostrar_resultado(st.session_state.pop(f"status_msg_{org_id}", None))
    if not modo_conectado:
        st.caption(HINT_ESCRITA)

    # ----- Observações (salva na coluna Observações) -----
    st.markdown('<div class="dr-sec"><h3>💬 Observações</h3></div>', unsafe_allow_html=True)
    obs = str(org.get(COL_OBS, "")).strip()
    if obs and obs != "—":
        for linha in obs.split("\n"):
            if linha.strip():
                st.markdown(f'<div class="ncard">{esc(linha.strip())}</div>',
                            unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-size:12px;color:var(--dim)">Nenhuma observação ainda.</div>',
                    unsafe_allow_html=True)

    key_obs = f"obs_{org_id}"
    st.text_area(
        "Adicionar observação", key=key_obs,
        placeholder="Adicionar uma observação sobre esta organização…",
        label_visibility="collapsed", disabled=not modo_conectado,
    )
    st.button(
        "➕ Salvar observação", key=f"btn_obs_{org_id}", use_container_width=True,
        on_click=_cb_salvar_obs, args=(org_id, key_obs), disabled=not modo_conectado,
    )
    _mostrar_resultado(st.session_state.pop(f"obs_msg_{org_id}", None))
    if not modo_conectado:
        st.caption(HINT_ESCRITA)


# --------------------------------------------------------------------------- #
# ABAS
# --------------------------------------------------------------------------- #
aba_visao, aba_rank, aba_radar, aba_funil, aba_metodo = st.tabs(
    ["📊 Visão geral", f"📋 Ranking ({TOTAL})", "📡 Radar", "🗂️ Funil", "🧮 Metodologia"]
)

# ===================== ABA 1 · VISÃO GERAL ================================== #
with aba_visao:
    st.markdown(
        '<div class="phead"><h1>Painel de captação</h1>'
        f'<p>{TOTAL} organizações monitoradas · priorização por Score PFC auditável</p></div>',
        unsafe_allow_html=True,
    )

    n_prospectar = int((df[COL_STATUS] == "Prospectar").sum())
    n_monitorar = int((df[COL_STATUS] == "Monitorar").sum())
    n_edital = int((df[COL_STATUS] == "Edital").sum())
    valor_total = float(df[COL_VALVO].sum()) if TOTAL else 0.0
    n_verif = int(df[COL_VERIF].apply(verificada_ok).sum()) if TOTAL else 0
    oportunidades_hoje = 4

    st.markdown(
        f"""
        <div class="kpis">
          <div class="kpi" style="--accent:var(--blue)">
            <div class="lab">📚 Organizações mapeadas</div>
            <div class="val">{TOTAL}</div>
            <div class="foot"><b>{n_verif}</b> de {TOTAL} fontes verificadas</div>
          </div>
          <div class="kpi" style="--accent:var(--orange)">
            <div class="lab">📈 Em prospecção ativa</div>
            <div class="val">{n_prospectar}</div>
            <div class="foot"><b>{n_monitorar}</b> em monitoramento · <b>{n_edital}</b> em edital</div>
          </div>
          <div class="kpi" style="--accent:var(--green)">
            <div class="lab">💰 Valor-alvo potencial</div>
            <div class="val">{brl_curto(valor_total)}</div>
            <div class="foot">soma do pipeline de captação</div>
          </div>
          <div class="kpi" style="--accent:var(--orange)">
            <div class="lab">⚡ Oportunidades hoje</div>
            <div class="val" style="color:var(--orange-2)">{oportunidades_hoje}</div>
            <div class="foot">novas · aguardando sua revisão</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Distribuição do funil + cobertura regional
    cont = df[COL_STATUS].value_counts() if TOTAL else pd.Series(dtype=int)
    cores_funil = {"Mapear": "var(--dim)", "Prospectar": "var(--orange)",
                   "Monitorar": "var(--blue)", "Edital": "var(--green)",
                   "Ativo": "var(--green-2)"}
    segs, legs = "", ""
    for s in STATUS_FUNIL:
        n = int(cont.get(s, 0))
        if TOTAL > 0 and n > 0:
            pct = n / TOTAL * 100
            segs += f'<i style="width:{pct:.2f}%;background:{cores_funil[s]}" title="{s} · {n}"></i>'
        legs += (f'<span><span class="sw" style="background:{cores_funil[s]}"></span>'
                 f'{s} <b>{n}</b></span>')
    outros = int(TOTAL - sum(int(cont.get(s, 0)) for s in STATUS_FUNIL))
    if outros > 0:
        legs += f'<span><span class="sw" style="background:var(--muted)"></span>Outros <b>{outros}</b></span>'

    sedes_distintas = (df[COL_SEDE].replace("", pd.NA).dropna().nunique() if TOTAL else 0)
    municipios_pfc = ["Iperó", "Tatuí", "Salto", "São Roque", "Rio Claro",
                      "Coronel Macedo", "Mirassol"]
    proximos = ["Dois Córregos · 2024", "Corumbataí · 2024"]
    tags = "".join(f'<span class="mtag"><span class="pin"></span>{esc(m)}</span>'
                   for m in municipios_pfc)
    tags += "".join(f'<span class="mtag next"><span class="pin"></span>{esc(m)}</span>'
                    for m in proximos)

    st.markdown(
        f"""
        <div class="g2">
          <div class="card">
            <div class="card-h"><div><h2>Distribuição do funil</h2>
              <div class="cap">status atual das {TOTAL} organizações</div></div></div>
            <div class="pad">
              <div class="funil">{segs}</div>
              <div class="fleg">{legs}</div>
            </div>
          </div>
          <div class="card">
            <div class="card-h"><div><h2>Cobertura regional</h2>
              <div class="cap">{sedes_distintas} municípios-sede distintos na base ·
              {len(municipios_pfc)} municípios parceiros do PFC</div></div></div>
            <div class="pad"><div class="muni">{tags}</div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ===================== ABA 2 · RANKING ===================================== #
with aba_rank:
    st.markdown(
        '<div class="phead"><h1>Ranking de captação</h1>'
        '<p>ordenado por Score PFC · busca e filtro ao vivo · abra o dossiê de cada organização</p></div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([3, 1.6, 1])
    with c1:
        busca = st.text_input("Buscar", placeholder="Buscar organização ou setor…",
                              label_visibility="collapsed")
    with c2:
        filtro_status = st.selectbox("Status", ["Todos"] + STATUS_FUNIL,
                                     label_visibility="collapsed")
    with c3:
        if st.button("🔄 Atualizar", use_container_width=True,
                     help="Recarrega os dados do Google Sheets / CSV (limpa o cache de 60s)"):
            dados.limpar_caches()
            st.rerun()

    rank = df.sort_values(COL_SCORE, ascending=False).copy() if TOTAL else df.copy()
    if busca.strip() and TOTAL:
        q = busca.strip().lower()
        mask = (rank[COL_EMPRESA].str.lower().str.contains(q, na=False)
                | rank[COL_SETOR].str.lower().str.contains(q, na=False))
        rank = rank[mask]
    if filtro_status != "Todos":
        rank = rank[rank[COL_STATUS] == filtro_status]

    st.caption(f"{len(rank)} organização(ões) · mostrando as primeiras 30 por score")
    st.markdown(
        '<div class="rkhead"><span>Organização</span><span>Score PFC</span>'
        '<span>Status</span><span class="r">Valor-alvo</span></div>',
        unsafe_allow_html=True,
    )

    for i, (_, row) in enumerate(rank.head(30).iterrows()):
        cA, cB, cC, cD, cE = st.columns([2.4, 1.5, 1, 1, 0.9])
        with cA:
            st.markdown(
                f'<div class="org"><span class="sem" style="background:{sem_cor(row[COL_SEMAFORO])}"></span>'
                f'<div><div class="nm">{texto_ou(row[COL_EMPRESA])}</div>'
                f'<div class="st">{texto_ou(row[COL_SETOR])}</div></div></div>',
                unsafe_allow_html=True,
            )
        with cB:
            st.markdown(
                f'<div class="scorecell"><span class="scoreN">{int(row[COL_SCORE])}</span>'
                f'{seg_html(row[COL_SCORE])}</div>',
                unsafe_allow_html=True,
            )
        with cC:
            st.markdown(status_badge(row[COL_STATUS]), unsafe_allow_html=True)
        with cD:
            st.markdown(f'<div class="alvo">{brl_curto(row[COL_VALVO])}</div>',
                        unsafe_allow_html=True)
        with cE:
            if st.button("Ver dossiê", key=f"dos_{row[COL_ID]}_{i}"):
                mostrar_dossie(row.to_dict())

    if len(rank) > 30:
        st.markdown(
            f'<div class="pad" style="color:var(--dim);font-size:12px">'
            f'+ {len(rank) - 30} organizações na base filtrada · refine a busca para ver mais</div>',
            unsafe_allow_html=True,
        )

# ===================== ABA 3 · RADAR ======================================= #
with aba_radar:
    st.markdown(
        '<div class="phead"><h1>Radar de oportunidades</h1>'
        '<p>varredura diária às 06:00 · aprove para enviar à aba “Novidades_pendentes”</p></div>',
        unsafe_allow_html=True,
    )

    LEADS = [
        {"id": "fapesp", "fonte": "FAPESP", "fit": 91, "cls": "hi",
         "titulo": "Difusão e Popularização da Ciência 2026",
         "why": "Foco em ensino básico e divulgação científica — encaixe direto no Clube de Ciências e na Maratona.",
         "descricao": "Apoio a projetos que aproximem ciência e escola pública, com bolsas e recursos para divulgação científica na educação básica.",
         "prazo": "31/08/2026", "valor_estimado": "R$ 80 mil – R$ 200 mil", "link": "https://fapesp.br/"},
        {"id": "itau", "fonte": "Itaú Social", "fit": 88, "cls": "mid",
         "titulo": "Chamada — Equidade na Educação Pública",
         "why": "Público e território aderentes; atua em municípios da região PFC.",
         "descricao": "Apoio a iniciativas que reduzam desigualdades de aprendizagem na rede pública, com foco em permanência escolar.",
         "prazo": "Fluxo contínuo", "valor_estimado": "R$ 100 mil – R$ 250 mil", "link": "https://www.itausocial.org.br/"},
        {"id": "prosas", "fonte": "Prosas", "fit": 73, "cls": "mid",
         "titulo": "Edital Juventude & Futuro",
         "why": "Aderente à missão, mas valor previsto abaixo do alvo — vale checar contrapartidas.",
         "descricao": "Plataforma agrega editais de empresas e fundações; esta chamada apoia projetos de juventude e protagonismo.",
         "prazo": "15/07/2026", "valor_estimado": "R$ 30 mil – R$ 60 mil", "link": "https://prosas.com.br/"},
    ]
    LEAD_FILTRADO = {
        "fonte": "Filtrado", "fit": 22,
        "titulo": "Cupom de cursos online — plataforma EAD",
        "why": "produto comercial, não fomento. O radar descartou automaticamente.",
    }

    if "radar_resolvidos" not in st.session_state:
        st.session_state.radar_resolvidos = {}

    col_fila, col_lado = st.columns([1.6, 1])

    with col_fila:
        st.markdown(
            '<div class="card-h" style="border:1px solid var(--line);border-bottom:none;'
            'border-radius:14px 14px 0 0;background:var(--surface)"><div><h2>Fila de revisão</h2>'
            '<div class="cap">3 novas hoje · aprove ou descarte</div></div></div>',
            unsafe_allow_html=True,
        )
        _mostrar_resultado(st.session_state.pop("radar_msg", None))
        if not modo_conectado:
            st.caption(HINT_ESCRITA + " (aprovar grava na aba Novidades_pendentes)")

        for lead in LEADS:
            resolvido = st.session_state.radar_resolvidos.get(lead["id"])
            if resolvido:
                cor = "var(--green)" if resolvido == "ok" else "var(--red)"
                txt = ("✓ Aprovado — enviado à base" if resolvido == "ok"
                       else "✕ Descartado da fila")
                st.markdown(
                    f'<div class="lead" style="opacity:.55"><div class="ttl">{esc(lead["titulo"])}</div>'
                    f'<div class="why" style="color:{cor}">{txt}</div></div>',
                    unsafe_allow_html=True,
                )
                continue

            st.markdown(
                f"""
                <div class="lead">
                  <div class="lead-top"><span class="src">{esc(lead["fonte"])}</span>
                    <span class="fit {lead["cls"]}">fit {lead["fit"]}</span></div>
                  <div class="ttl">{esc(lead["titulo"])}</div>
                  <div class="why">{esc(lead["why"])}</div>
                  <div class="meta"><b>Fonte:</b> {esc(lead["fonte"])}</div>
                  <div class="meta"><b>Descrição:</b> {esc(lead["descricao"])}</div>
                  <div class="meta"><b>Prazo:</b> {esc(lead["prazo"])} · <b>Valor estimado:</b> {esc(lead["valor_estimado"])} · <b>Score aderência:</b> {lead["fit"]}</div>
                  <a class="srclink" href="{esc(lead["link"])}" target="_blank" rel="noopener">↗ Fonte: {esc(lead["link"])}</a>
                </div>
                """,
                unsafe_allow_html=True,
            )
            b1, b2, _sp = st.columns([1.3, 1, 1.7])
            with b1:
                if st.button("✓ Aprovar e mover à base", key=f"ok_{lead['id']}",
                             disabled=not modo_conectado):
                    lead_dict = {
                        "data": pd.Timestamp.now().strftime("%d/%m/%Y"),
                        "fonte": lead["fonte"],
                        "titulo": lead["titulo"],
                        "descricao": lead["descricao"],
                        "score_aderencia": lead["fit"],
                        "prazo": lead["prazo"],
                        "valor_estimado": lead["valor_estimado"],
                        "link": lead["link"],
                        "status": "Pendente de revisão",
                    }
                    res = dados.adicionar_lead_radar(lead_dict)
                    st.session_state.radar_resolvidos[lead["id"]] = "ok"
                    st.session_state["radar_msg"] = res
                    st.toast(res["mensagem"], icon="✅" if res["sucesso"] else "⚠️")
                    st.rerun()
            with b2:
                if st.button("Descartar", key=f"no_{lead['id']}"):
                    st.session_state.radar_resolvidos[lead["id"]] = "no"
                    st.toast("Descartado da fila.", icon="🗑️")
                    st.rerun()

        # Item fora do escopo (demonstra o filtro)
        st.markdown(
            f"""
            <div class="lead rej">
              <div class="lead-top"><span class="src" style="color:var(--red);background:var(--red-soft)">{esc(LEAD_FILTRADO["fonte"])}</span>
                <span class="fit lo">fit {LEAD_FILTRADO["fit"]}</span></div>
              <div class="ttl">{esc(LEAD_FILTRADO["titulo"])}</div>
              <div class="why"><span class="rej-tag">Fora do escopo:</span> {esc(LEAD_FILTRADO["why"])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_lado:
        fontes = ["CAPTA", "Prosas", "ABCR", "CNPq", "FAPESP", "Finep", "CAPES",
                  "Itaú Social", "Fund. Bradesco", "Inst. Lemann",
                  "Fund. Banco do Brasil", "MEC", "Fund. Telefônica", "Sec. Educação SP"]
        chips = "".join(f'<span class="src-tag">{esc(f)}</span>' for f in fontes)
        st.markdown(
            f"""
            <div class="card">
              <div class="card-h"><div><h2>Fontes monitoradas</h2>
                <div class="cap">{len(fontes)} fontes · última varredura hoje 06:00</div></div></div>
              <div class="pad">{chips}
                <div class="note">O radar vigia fontes conhecidas e estáveis — nada de varrer
                a internet inteira. Você decide o que entra na base.</div>
              </div>
            </div>
            <div class="card">
              <div class="card-h"><div><h2>Resumo de hoje</h2><div class="cap">06:00</div></div></div>
              <div class="pad">
                <div class="statline"><span style="color:var(--muted)">Itens varridos</span><b>37</b></div>
                <div class="statline"><span style="color:var(--muted)">Filtrados (fora do escopo)</span><b style="color:var(--red)">33</b></div>
                <div class="statline"><span style="color:var(--muted)">Na sua fila</span><b style="color:var(--green)">4</b></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ===================== ABA 4 · FUNIL ======================================= #
with aba_funil:
    st.markdown(
        '<div class="phead"><h1>Funil de relacionamento</h1>'
        '<p>organizações distribuídas por status · 5 etapas do mapeamento à execução</p></div>',
        unsafe_allow_html=True,
    )
    st.caption("💡 Para mover uma organização de etapa, abra o **dossiê** dela no Ranking "
               "e altere o **Status** (a mudança é gravada na planilha).")

    acentos = {"Mapear": "var(--dim)", "Prospectar": "var(--orange)",
               "Monitorar": "var(--blue)", "Edital": "var(--green)",
               "Ativo": "var(--green-2)"}
    colunas_html = ""
    for s in STATUS_FUNIL:
        grupo = (df[df[COL_STATUS] == s].sort_values(COL_SCORE, ascending=False)
                 if TOTAL else df)
        n = len(grupo)
        cards = ""
        for _, row in grupo.head(4).iterrows():
            cards += (
                f'<div class="kcard"><div class="kn">{texto_ou(row[COL_EMPRESA])}</div>'
                f'<div class="ks">{texto_ou(row[COL_SETOR])}</div>'
                f'<div class="kf"><span class="kchip" style="{score_chip_cor(row[COL_SCORE])}">'
                f'{int(row[COL_SCORE])}</span>'
                f'<span class="kval">{brl_curto(row[COL_VALVO])}</span></div></div>'
            )
        if n > 4:
            cards += f'<div class="kmore">+ {n - 4} organizações</div>'
        if n == 0:
            cards = '<div class="kmore">vazio</div>'
        colunas_html += (
            f'<div class="kcol"><div class="kcol-h">'
            f'<span><span class="accent" style="background:{acentos[s]}"></span>{s}</span>'
            f'<span class="ct">{n}</span></div><div class="kbody">{cards}</div></div>'
        )
    st.markdown(f'<div class="kan">{colunas_html}</div>', unsafe_allow_html=True)

# ===================== ABA 5 · METODOLOGIA ================================= #
with aba_metodo:
    st.markdown(
        '<div class="phead"><h1>Como o Score PFC é calculado</h1>'
        '<p>quatro componentes, pesos fixos, origem rastreável</p></div>',
        unsafe_allow_html=True,
    )

    topo = df.sort_values(COL_SCORE, ascending=False).iloc[0] if TOTAL else None
    nome_topo = texto_ou(topo[COL_EMPRESA]) if topo is not None else "—"
    score_topo = int(topo[COL_SCORE]) if topo is not None else 0
    pesos = [("Aderência ao DNA", 35, "var(--orange)"),
             ("Capacidade & fit de valor", 25, "var(--green)"),
             ("Proximidade regional", 20, "var(--blue)"),
             ("Acionabilidade", 20, "var(--muted)")]

    legenda = ""
    for nome, w, cor in pesos:
        legenda += (
            f'<div class="lrow"><span class="nm"><span class="sw" style="background:{cor}"></span>'
            f'{nome}</span><span class="wt">{w}%</span>'
            f'<span class="ltrack"><i style="width:{w}%;background:{cor}"></i></span></div>'
        )

    subs = ""
    for nome, w, cor in pesos:
        subs += (
            f'<div class="sub"><span class="l">{nome} ({w}%)</span>'
            f'<span class="t2"><i style="width:{score_topo}%;background:{cor}"></i></span>'
            f'<span class="n">{score_topo}</span></div>'
        )

    st.markdown(
        f"""
        <div class="g2">
          <div class="card">
            <div class="card-h"><div><h2>Pesos &amp; leitura</h2>
              <div class="cap">os mesmos critérios valem para as {TOTAL} organizações e para o radar</div></div></div>
            <div class="pad">
              <div class="legend">{legenda}</div>
              <div class="divider"></div>
              <p style="font-size:12.5px;color:var(--muted);line-height:1.6">
                <b style="color:var(--text)">Fórmula:</b> Score = 0,35·Aderência + 0,25·Valor +
                0,20·Região + 0,20·Acionabilidade. No MVP, o app usa a coluna
                <code>Score PFC</code> já existente na planilha; esta aba documenta e
                visualiza a fórmula de forma auditável.</p>
            </div>
          </div>
          <div class="card">
            <div class="card-h"><div><h2>Anatomia do score</h2>
              <div class="cap">exemplo · {nome_topo} = {score_topo}</div></div></div>
            <div class="pad">
              <div style="text-align:center;margin:6px 0 16px">
                <div style="font-family:var(--disp);font-weight:700;font-size:46px;color:var(--green)">{score_topo}</div>
                <div style="font-size:11.5px;color:var(--dim)">de 100 · maior score da base</div>
              </div>
              {subs}
              <div class="note">Quando alguém perguntar “por que {score_topo}?”, a resposta está aqui —
              defensável em reunião, sem número arbitrário. (Decomposição ilustrativa pelos pesos fixos.)</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------------- #
# Rodapé
# --------------------------------------------------------------------------- #
modo_txt = ("Conectado ao Google Sheets (leitura e escrita ao vivo)" if modo_conectado
            else "Modo local (CSV) — somente leitura. Conecte o Google Sheets para sincronizar.")
st.markdown(
    f'<div class="hr-line" style="margin-top:26px"></div>'
    f'<div style="display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap;'
    f'font-size:11.5px;color:var(--dim)"><span>Dashboard de Inteligência de Captação · PFC</span>'
    f'<span>{modo_txt}</span></div>',
    unsafe_allow_html=True,
)
