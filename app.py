"""
Dashboard de Inteligência de Captação (PFC) — product-grade
============================================================
App Streamlit com login, navegação por páginas, KPIs clicáveis, modais
interativos, gráficos Plotly e sincronização ao vivo com Google Sheets
(fallback automático para CSV).

Rodar:  streamlit run app.py
Login demo:  fabio@pfc.org / pfc2026   ·   otavio@pfc.org / pfc2026
"""
from __future__ import annotations

import datetime
import html
import json
import os
import re
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import streamlit.components.v2 as components_v2

from src import dados
from src.dados import (
    COL_CANAL, COL_CHANCE, COL_EDITAL, COL_EMPRESA, COL_ENCAIXE, COL_ID,
    COL_INSTITUTO, COL_JANELA, COL_MODALIDADE, COL_OBS, COL_PRESENCA,
    COL_PRIORIDADE, COL_PROPOSTA, COL_PROX_ACAO, COL_PUBLICO, COL_REGIAO,
    COL_RESP, COL_SCORE, COL_SEDE, COL_SEMAFORO, COL_SETOR, COL_SOCIAL,
    COL_STATUS, COL_SUBSETOR, COL_TIPO, COL_UF, COL_URL, COL_VALVO, COL_VERIF,
    COL_VMAX, COL_VMIN, STATUS_FUNIL,
)

try:
    import plotly.graph_objects as go
    PLOTLY_OK = True
except Exception:
    PLOTLY_OK = False

# Componente de drag-and-drop do funil (HTML5 nativo, sem dependências externas).
_KANBAN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kanban_component")
try:
    _kanban_component = components.declare_component("kanban_pfc", path=_KANBAN_DIR)
    KANBAN_DND_OK = os.path.isfile(os.path.join(_KANBAN_DIR, "index.html"))
except Exception:
    _kanban_component = None
    KANBAN_DND_OK = False

# --------------------------------------------------------------------------- #
# Configuração da página
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="PFC · Captação Privada",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------- #
# Usuários de teste (login)
# --------------------------------------------------------------------------- #
USERS = {
    "fabio@pfc.org": {
        "senha": "pfc2026", "nome": "Fábio Leite", "inicial": "FL",
        "perfil": "Coordenador de Captação",
        "bg": "rgba(255,255,255,.06)", "bd": "rgba(255,255,255,.16)", "tx": "#E9EBEE",
    },
    "otavio@pfc.org": {
        "senha": "pfc2026", "nome": "Otávio Martinez", "inicial": "OM",
        "perfil": "Analista de Dados",
        "bg": "rgba(255,255,255,.06)", "bd": "rgba(255,255,255,.16)", "tx": "#E9EBEE",
    },
}

PAGES = ["Visão geral", "Ranking", "Radar", "Funil", "Metodologia", "Verificação"]
PAGE_ICONS = {"Visão geral": "📊", "Ranking": "📋", "Radar": "📡",
              "Funil": "🗂️", "Metodologia": "🧮", "Verificação": "🔍"}

# --------------------------------------------------------------------------- #
# Tema escuro premium + CSS custom
# --------------------------------------------------------------------------- #
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');
:root{
  /* ==== DESIGN SYSTEM (maquete pfc_app_v3) ==== */
  --bg:#0E1116; --surface:#161A21; --surface2:#1C222B; --hover:#222834;
  --line:rgba(255,255,255,.06); --line2:rgba(255,255,255,.12);
  --ink:#F5F7FA; --muted:#A4AEBF; --dim:#6B7688;
  --accent:#E8873A; --accent-dim:rgba(232,135,58,.12);
  --sem-high:#4ADE80; --sem-mid:#E8B54A; --sem-low:#7C8698;
  --sem-urgent:#F0663F; --sem-info:#5B9BD5;
  --mono:'JetBrains Mono',monospace;
  --body:'Inter',system-ui,sans-serif; --disp:'Inter',system-ui,sans-serif;
  --r-sm:9px; --r:11px; --r-lg:16px; --r-xl:16px;
  --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px; --sp-5:22px; --sp-6:32px;
  --sh-1:0 1px 2px rgba(0,0,0,.16); --sh-2:0 24px 70px rgba(0,0,0,.50);
  --ease:cubic-bezier(.16,1,.3,1);
  /* ==== aliases legados: as telas atuais herdam a paleta nova sem retrabalho ==== */
  --surface-2:var(--surface2); --surface-3:var(--hover); --raise:var(--surface2);
  --glass:rgba(22,26,33,.78);
  --line-2:var(--line2); --line-3:rgba(255,255,255,.20);
  --text:var(--ink); --text-2:#C9D2DF; --white:#FFFFFF;
  --orange:var(--accent); --orange-2:#F0A869; --orange-soft:var(--accent-dim);
  --green:var(--sem-high); --green-2:#86EBAC; --green-soft:rgba(74,222,128,.12);
  --blue:var(--sem-info); --blue-2:#8FBDE6; --blue-soft:rgba(91,155,213,.12);
  --red:var(--sem-urgent); --red-2:#F58A6C; --red-soft:rgba(240,102,63,.12);
  --acc-white:#FFFFFF; --acc-orange:var(--accent); --acc-blue:var(--sem-info); --acc-green:var(--sem-high);
  --acc-orange-soft:var(--accent-dim); --acc-blue-soft:rgba(91,155,213,.14); --acc-green-soft:rgba(74,222,128,.14);
}
html, body, [class*="css"]{font-family:var(--body);line-height:1.6;}
.mono{font-family:var(--mono)} .tnum{font-variant-numeric:tabular-nums}
.stApp{background:var(--bg);}
/* Neutraliza a barra fixa do Streamlit (que sobrepunha/cortava a logo) */
[data-testid="stHeader"]{display:none;height:0;}
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"]{display:none!important;}
[data-testid="stAppViewContainer"]{overflow:visible;}
.block-container{max-width:1280px;padding-top:2.4rem!important;padding-bottom:3.4rem;margin:0 auto;}
@media (min-width:1700px){.block-container{max-width:1380px;}}
h1,h2,h3,h4{font-family:var(--disp);letter-spacing:-.01em;color:var(--text);}

/* ---------- header ---------- */
.brand{display:flex;align-items:center;gap:14px;overflow:visible;min-width:0;flex-wrap:nowrap}
.brand svg{flex:none;display:block}
.brand>div{min-width:0}
.brand .wm{font-family:var(--disp);font-weight:600;font-size:15px;letter-spacing:.05em;color:var(--text);line-height:1.2;text-transform:uppercase;white-space:nowrap}
.brand .sub{font-size:12.5px;color:var(--muted)}
.brand:hover svg .orbit{animation:spin 9s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.selo-wrap{margin:12px 0 2px}
.pill{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;font-weight:500;padding:6px 13px;border-radius:999px}
.pill.ok{background:var(--green-soft);border:1px solid rgba(95,177,55,.32);color:var(--green-2)}
.pill.local{background:var(--orange-soft);border:1px solid rgba(242,145,30,.32);color:var(--orange-2)}
.dot{width:7px;height:7px;border-radius:50%;background:currentColor;animation:pulse 2.4s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(95,177,55,.45)}70%{box-shadow:0 0 0 7px rgba(95,177,55,0)}100%{box-shadow:0 0 0 0 rgba(95,177,55,0)}}
.userbox{display:flex;align-items:center;gap:11px;justify-content:flex-end}
.userbox .who{text-align:right;line-height:1.25}
.userbox .who .nm{font-size:13.5px;font-weight:600;color:var(--text)}
.userbox .who .pf{font-size:11.5px;color:var(--muted)}
.avatar{width:40px;height:40px;border-radius:50%;display:grid;place-items:center;font-family:var(--disp);font-weight:700;font-size:14px;flex:none;transition:transform .2s var(--ease)}
.avatar:hover{transform:scale(1.08)}
.hr-line{height:1px;background:var(--line);margin:14px 0 6px}
.bcrumb{font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.07em;margin:4px 0 18px}
.bcrumb b{color:var(--text-2);font-weight:600}

/* ---------- phead ---------- */
.phead h1{font-family:var(--disp);font-weight:600;font-size:25px;margin-bottom:3px}
.phead p{color:var(--muted);font-size:13.5px;margin:0 0 6px}

/* ---------- cards (glass + depth) ---------- */
.card{background:var(--glass);backdrop-filter:blur(9px);-webkit-backdrop-filter:blur(9px);
  border:1px solid var(--line);border-radius:var(--r-lg);overflow:hidden;margin-bottom:18px;box-shadow:var(--sh-1)}
.card-h{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:20px 24px 15px;border-bottom:1px solid var(--line)}
.card-h h2{font-family:var(--disp);font-weight:600;font-size:15.5px;margin:0;letter-spacing:.01em}
.card-h .cap{font-size:12px;color:var(--dim);margin-top:3px}
.pad{padding:22px 24px}

/* ---------- KPIs clicáveis ---------- */
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:var(--r-lg) var(--r-lg) 0 0;
  padding:22px 22px 20px;position:relative;overflow:hidden;box-shadow:var(--sh-1);
  transition:transform .26s var(--ease),border-color .26s var(--ease),background .26s var(--ease)}
.kpi::before{content:"";position:absolute;left:0;top:0;bottom:0;width:2px;background:var(--accent,rgba(255,255,255,.16));transition:width .26s var(--ease),background .26s var(--ease)}
.kpi .lab{display:flex;align-items:center;gap:8px;font-size:12.5px;color:var(--muted);font-weight:500}
.kpi .lab .ic{display:inline-block;transition:transform .24s var(--ease)}
.kpi .val{font-family:var(--disp);font-weight:600;font-size:34px;letter-spacing:-.02em;margin:14px 0 4px;line-height:1;color:var(--text)}
.kpi .foot{font-size:12px;color:var(--dim)} .kpi .foot b{color:var(--text-2);font-weight:600}
.kpi:hover{border-color:var(--line-2);transform:translateY(-2px)}
.kpi:hover::before{width:3px;background:rgba(255,255,255,.32)}
.kpi:hover .ic{transform:scale(1.18)}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media (max-width:900px){.g2{grid-template-columns:1fr}}

/* ---------- funil bar ---------- */
.funil{display:flex;height:14px;border-radius:7px;overflow:hidden;margin:6px 0 16px;box-shadow:inset 0 0 0 1px var(--line)}
.funil i{display:block;height:100%;transition:filter .2s var(--ease)}
.fleg{display:flex;flex-wrap:wrap;gap:14px}
.fleg span{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted)}
.fleg .sw{width:9px;height:9px;border-radius:3px} .fleg b{color:var(--text);font-family:var(--disp);font-weight:600}

/* ---------- ranking rows ---------- */
.org{display:flex;align-items:center;gap:13px;padding:8px 22px 8px 4px;min-width:0}
.org>div{min-width:0;flex:1}
.sem{width:8px;height:8px;border-radius:50%;flex:none;opacity:.9}
.org .nm{font-weight:600;color:var(--text);font-size:14px;line-height:1.4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.org .st{font-size:11.5px;color:var(--dim);margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.scorecell{display:flex;align-items:center;gap:12px;padding-left:8px}
.scoreN{font-family:var(--disp);font-weight:600;font-size:18px;width:28px;color:var(--text)}
.segbar{flex:1;max-width:116px;height:6px;border-radius:4px;background:var(--line-2);display:flex;overflow:hidden;gap:1.5px}
.segbar i{display:block;height:100%}
.stat{font-size:11.5px;font-weight:600;padding:3px 11px;border-radius:7px;white-space:nowrap;border:1px solid transparent}
.s-pros{background:var(--blue-soft);color:var(--blue-2);border-color:rgba(91,155,213,.22)}
.s-moni{background:rgba(255,255,255,.05);color:var(--text-2)}
.s-edit{background:var(--orange-soft);color:var(--orange-2);border-color:rgba(232,154,60,.22)}
.s-ativo{background:var(--green-soft);color:var(--green-2);border-color:rgba(95,177,55,.22)}
.s-map{background:rgba(255,255,255,.035);color:var(--muted)}
.alvo{font-family:var(--disp);font-weight:600;text-align:right;color:var(--text);white-space:nowrap;font-size:13.5px}
.rkhead{display:grid;grid-template-columns:2.4fr 1.5fr 1fr 1fr;gap:8px;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--dim);font-weight:600;padding:8px 4px 2px}
.rkhead .r{text-align:right}
[data-testid="stHorizontalBlock"]:has(.org){border-bottom:1px solid var(--line);padding:6px 6px;align-items:center;min-height:64px;border-radius:8px;transition:background .22s var(--ease)}
[data-testid="stHorizontalBlock"]:has(.org.odd){background:rgba(255,255,255,.013)}
[data-testid="stHorizontalBlock"]:has(.org):hover{background:rgba(255,255,255,.05)}

/* ---------- list rows (modais) ---------- */
.lrow2{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:9px 12px;border:1px solid var(--line);
  border-radius:10px;background:var(--surface-2);margin-bottom:7px;transition:transform .16s var(--ease),border-color .16s var(--ease)}
.lrow2:hover{transform:translateX(3px);border-color:var(--line-2)}
.lrow2 .l{display:flex;align-items:center;gap:9px;min-width:0}
.lrow2 .nm{font-weight:600;font-size:13px;color:var(--text)}
.lrow2 .sx{font-size:11px;color:var(--dim)}
.lrow2 .rt{display:flex;align-items:center;gap:12px;flex:none}
.lrow2 .sc{font-family:var(--disp);font-weight:700;color:var(--orange-2);font-size:14px}

/* ---------- kanban ---------- */
.kan{display:grid;grid-template-columns:repeat(5,1fr);gap:13px;align-items:start}
@media (max-width:900px){.kan{grid-template-columns:1fr 1fr}}
.kcol{background:var(--glass);backdrop-filter:blur(9px);border:1px solid var(--line);border-radius:var(--r-lg);overflow:hidden;box-shadow:var(--sh-1)}
.kcol-h{display:flex;align-items:center;justify-content:space-between;padding:12px 14px;border-bottom:1px solid var(--line);font-size:12.5px;font-weight:700}
.kcol-h .ct{font-family:var(--disp);font-size:11px;color:var(--muted);background:var(--surface-2);padding:2px 8px;border-radius:999px}
.kcol-h .accent{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:8px;vertical-align:middle}
.kbody{padding:11px;display:flex;flex-direction:column;gap:10px;min-height:60px}
.kcard{background:var(--surface-2);border:1px solid var(--line);border-radius:11px;padding:11px 12px;transition:transform .2s var(--ease),border-color .2s var(--ease),box-shadow .2s var(--ease)}
.kcard:hover{transform:translateY(-2px);border-color:var(--line-2);box-shadow:0 6px 16px rgba(0,0,0,.25)}
.kcard .kn{font-size:12.5px;font-weight:600;line-height:1.3}
.kcard .ks{font-size:11px;color:var(--dim);margin-top:2px}
.kcard .kf{display:flex;align-items:center;justify-content:space-between;margin-top:9px}
.kchip{font-family:var(--disp);font-weight:700;font-size:11px;padding:2px 8px;border-radius:7px}
.kval{font-size:11px;color:var(--muted)}
.kmore{font-size:11.5px;color:var(--dim);text-align:center;padding:7px;border:1px dashed var(--line-2);border-radius:9px}

/* ---------- radar leads ---------- */
.lead{padding:15px 17px;border:1px solid var(--line);border-radius:13px;background:var(--glass);backdrop-filter:blur(9px);margin-bottom:12px;box-shadow:var(--sh-1);transition:transform .2s var(--ease),border-color .2s var(--ease)}
.lead:hover{transform:translateY(-2px);border-color:var(--line-2)}
.lead-top{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:7px}
.src{display:inline-flex;align-items:center;gap:6px;font-size:11px;font-weight:700;letter-spacing:.03em;color:var(--blue);background:var(--blue-soft);padding:3px 10px;border-radius:7px;text-transform:uppercase}
.fit{font-family:var(--disp);font-weight:700;font-size:13px}
.fit.hi{color:var(--green)} .fit.mid{color:var(--orange-2)} .fit.lo{color:var(--red)}
.lead .ttl{font-weight:600;font-size:14px;color:var(--text);margin-bottom:3px}
.lead .why{font-size:12.5px;color:var(--muted);line-height:1.5}
.lead .meta{font-size:12px;color:var(--muted);margin-top:8px}
.lead .meta b{color:var(--text);font-weight:600}
.lead.rej{background:var(--red-soft);border-color:rgba(226,86,64,.3)}
.lead.rej .ttl{color:var(--muted);text-decoration:line-through}
.rej-tag{font-size:11px;color:var(--red);font-weight:600}
.srclink{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;color:var(--blue-2)!important;text-decoration:none;background:var(--blue-soft);border:1px solid rgba(59,139,208,.3);padding:8px 12px;border-radius:9px;margin-top:9px;transition:.16s var(--ease)}
.srclink:hover{border-color:rgba(59,139,208,.6);transform:translateY(-1px)}
.src-tag{display:inline-block;font-size:11px;color:var(--blue-2);background:var(--blue-soft);border:1px solid rgba(59,139,208,.22);padding:4px 10px;border-radius:8px;margin:0 6px 7px 0}
.note{font-size:11.5px;color:var(--dim);line-height:1.55;margin-top:11px}
.statline{display:flex;justify-content:space-between;font-size:13px;padding:4px 0}
.statline b{font-family:var(--disp)}

/* ---------- methodology ---------- */
.legend{display:flex;flex-direction:column;gap:14px}
.lrow{display:grid;grid-template-columns:1fr auto;align-items:center;gap:10px}
.lrow .nm{font-size:13px;color:var(--text);display:flex;align-items:center;gap:8px}
.lrow .nm .sw{width:9px;height:9px;border-radius:3px;flex:none}
.lrow .wt{font-family:var(--disp);font-weight:700;font-size:13px;color:var(--muted)}
.ltrack{grid-column:1/-1;height:5px;border-radius:3px;background:var(--line-2);overflow:hidden;margin-top:-5px}
.ltrack i{display:block;height:100%;border-radius:3px}
.divider{height:1px;background:var(--line);margin:16px 0}
.miniex{font-size:12px;color:var(--blue-2);background:var(--blue-soft);border:1px solid rgba(59,139,208,.25);border-radius:9px;padding:9px 12px;margin-top:9px;line-height:1.5}
.caso{background:var(--surface-2);border:1px solid var(--line);border-radius:13px;padding:14px 15px;height:100%;box-shadow:var(--sh-1);transition:transform .2s var(--ease),border-color .2s var(--ease)}
.caso:hover{transform:translateY(-3px);border-color:var(--line-2)}
.caso .ch{display:flex;align-items:center;justify-content:space-between;margin-bottom:7px}
.caso .cn{font-weight:600;font-size:13.5px}
.caso .cs{font-family:var(--disp);font-weight:700;font-size:20px}
.caso .cw{font-size:12px;color:var(--muted);line-height:1.5}

/* ---------- dialog (modal premium) ---------- */
[data-testid="stDialog"] > div{backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);background:rgba(8,10,13,.5)!important;}
[data-testid="stDialog"] [role="dialog"]{border:1px solid var(--line-2)!important;border-radius:var(--r-lg)!important;
  box-shadow:var(--sh-2)!important;background:rgba(20,24,32,.92)!important;backdrop-filter:blur(12px)!important;-webkit-backdrop-filter:blur(12px)!important;padding-top:6px!important;}
.dr-eyebrow{display:flex;align-items:center;gap:8px;font-size:11.5px;color:var(--dim);margin-bottom:6px}
.dr-sub{font-size:12.5px;color:var(--muted);margin:2px 0 6px}
.dr-score{font-family:var(--disp);font-weight:700;font-size:30px;line-height:1}
.dr-score small{font-size:13px;color:var(--muted);font-weight:400}
.dr-seg{height:8px;border-radius:5px;background:var(--line-2);display:flex;overflow:hidden;gap:2px;margin-top:8px}
.dr-seg i{display:block;height:100%}
.dr-sec h3{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-2);font-weight:600;margin:20px 0 11px}
.frow{display:grid;grid-template-columns:130px 1fr;gap:10px;padding:5px 0;font-size:13px}
.frow .fl{color:var(--muted);font-size:12.5px}
.frow .fv{color:var(--text)}
.fblock .fl{color:var(--muted);font-size:12px;margin:7px 0 3px}
.fblock .fv{color:var(--text);font-size:13px;line-height:1.55;background:var(--surface-2);border:1px solid var(--line);border-radius:9px;padding:11px 13px}
.vbadge{font-size:11px;font-weight:600;padding:2px 9px;border-radius:6px;margin-left:8px}
.vb-ok{background:var(--green-soft);color:var(--green-2)} .vb-no{background:var(--orange-soft);color:var(--orange-2)}
.ncard{background:var(--surface-2);border:1px solid var(--line);border-left:2px solid var(--blue);border-radius:10px;padding:10px 13px;margin-bottom:8px;font-size:12.5px;color:var(--text);line-height:1.55;white-space:pre-wrap}

/* ---------- login ---------- */
.login-logo{display:flex;flex-direction:column;align-items:center;gap:10px;margin:6px 0 4px}
.login-logo .wm{font-family:var(--disp);font-weight:600;font-size:16px;letter-spacing:.06em;color:var(--text);text-transform:uppercase}
.login-logo .sub{font-size:13px;color:var(--muted)}
.login-h{font-family:var(--disp);font-weight:600;font-size:19px;text-align:center;margin:12px 0 2px}
.login-p{font-size:12.5px;color:var(--muted);text-align:center;margin-bottom:6px}

/* ---------- streamlit widget polish ---------- */
/* botões: neutros, quase transparentes; hover clareia (branco) */
.stButton>button{border-radius:9px;border:1px solid var(--line-2);background:transparent;color:var(--text-2);
  font-size:13px;font-weight:500;padding:9px 16px;transition:all .24s var(--ease);}
.stButton>button:hover{border-color:var(--line-3);color:var(--white);background:rgba(255,255,255,.035);transform:translateY(-1px);}
.stButton>button:active{transform:translateY(0) scale(.99);}
.stButton>button[kind="primary"]{background:rgba(255,255,255,.06);border-color:var(--line-3);color:var(--white);font-weight:600;}
.stButton>button[kind="primary"]:hover{background:rgba(255,255,255,.11);border-color:rgba(255,255,255,.30);}
/* link button (fonte oficial) — âncora nativa, estilo neutro */
[data-testid="stLinkButton"] a{border-radius:9px!important;border:1px solid var(--line-2)!important;background:transparent!important;color:var(--blue-2)!important;font-size:13px!important;font-weight:500!important;transition:all .24s var(--ease)!important;}
[data-testid="stLinkButton"] a:hover{border-color:rgba(91,155,213,.5)!important;color:var(--white)!important;background:rgba(91,155,213,.08)!important;transform:translateY(-1px);}
/* expanders: minimalistas */
div[data-testid="stExpander"]{border:1px solid var(--line);border-radius:12px;background:var(--surface);margin-bottom:12px;overflow:hidden;box-shadow:none;transition:border-color .24s var(--ease);}
div[data-testid="stExpander"]:hover{border-color:var(--line-2);}
div[data-testid="stExpander"] summary{font-family:var(--disp);font-weight:600;font-size:13.5px;padding:15px 18px;transition:color .2s var(--ease);}
div[data-testid="stExpander"] summary:hover{color:var(--white);}
/* inputs: cinza escuro, foco em azul (só na borda) */
div[data-baseweb="input"], div[data-baseweb="textarea"]{background:var(--surface-2)!important;border:1px solid var(--line-2)!important;border-radius:9px!important;transition:border-color .22s var(--ease),box-shadow .22s var(--ease)!important;}
div[data-baseweb="input"]:focus-within, div[data-baseweb="textarea"]:focus-within{border-color:var(--blue)!important;box-shadow:0 0 0 1px rgba(91,155,213,.35)!important;}
div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea{background:transparent!important;color:var(--text)!important;font-size:13px;}
div[data-baseweb="select"]>div{background:var(--surface-2)!important;border-color:var(--line-2)!important;border-radius:9px!important;transition:border-color .22s var(--ease)!important;}
div[data-baseweb="select"]>div:focus-within{border-color:var(--blue)!important;}
.stTextInput label, .stSelectbox label{color:var(--muted)!important;font-size:12.5px!important;}

/* ============ fundo (maquete: flat e sóbrio, sem camada cósmica) ============ */
body{background:var(--bg)}
.card,.kcol,.lead,.caso,.kpi{box-shadow:var(--sh-1),inset 0 0 0 1px rgba(255,255,255,.018)}
.card:hover,.lead:hover,.caso:hover{box-shadow:0 18px 48px rgba(0,0,0,.45),inset 0 0 0 1px rgba(255,255,255,.06)}
.login-logo svg{transition:transform .4s var(--ease)}
.login-logo:hover svg .orbit{animation:spin 9s linear infinite}

/* ---------- aba Verificação ---------- */
.vbar{height:10px;border-radius:6px;background:var(--line-2);overflow:hidden;margin:8px 0 2px}
.vbar i{display:block;height:100%;border-radius:6px;background:linear-gradient(90deg,#E89A3C,#5FB137);transition:width .7s var(--ease)}
.vprog-lab{display:flex;align-items:baseline;justify-content:space-between;gap:10px}
.vprog-lab .big{font-family:var(--disp);font-weight:600;font-size:22px;color:var(--text)}
.vprog-lab .pct{font-family:var(--disp);font-weight:600;font-size:14px;color:var(--green-2)}
.vhead{display:flex;align-items:center;gap:11px;min-width:0}
.vhead .nm{font-weight:600;font-size:14px;color:var(--text)}
.vhead .st{font-size:11.5px;color:var(--dim)}
.vcur{font-size:11.5px;color:var(--dim);word-break:break-all;margin-top:2px}
.vbadge2{font-size:11px;font-weight:600;padding:2px 9px;border-radius:7px;border:1px solid transparent;white-space:nowrap}
.vb-nao{background:var(--red-soft);color:var(--red-2);border-color:rgba(226,87,74,.25)}
.vb-pend{background:var(--orange-soft);color:var(--orange-2);border-color:rgba(232,154,60,.25)}

/* ============ Visão Geral · widgets nativos estilizados via st-key ============ */
/* alerta de prazos: faixa âmbar com acento à esquerda */
.st-key-alerta_prazos button{width:100%;justify-content:flex-start;text-align:left;
  background:linear-gradient(90deg,rgba(242,145,30,.10),rgba(242,145,30,.015) 70%);
  border:1px solid rgba(242,145,30,.30);border-left:3px solid var(--acc-orange);
  color:var(--orange-2);font-weight:600;font-size:13px;border-radius:var(--r-lg);padding:11px 16px}
.st-key-alerta_prazos button:hover{border-color:rgba(242,145,30,.55);border-left-color:var(--acc-orange);
  background:linear-gradient(90deg,rgba(242,145,30,.16),rgba(242,145,30,.03) 70%);color:#FFD9A8;transform:none}
/* ações sob os KPIs: links fantasmas, discretos */
[class*="st-key-kpi_"] button{width:100%;border:1px solid var(--line);background:rgba(255,255,255,.014);
  color:var(--dim);font-size:12px;font-weight:500;padding:7px 12px;border-radius:var(--r)}
[class*="st-key-kpi_"] button:hover{color:var(--text);border-color:var(--line-3);
  background:rgba(255,255,255,.05);transform:translateY(-1px)}
/* chips das etapas do funil: pílulas com ponto colorido por status */
[class*="st-key-seg_"] button{border-radius:999px;font-size:11.5px;font-weight:500;color:var(--muted);
  border:1px solid var(--line);background:rgba(255,255,255,.014);padding:6px 6px;white-space:nowrap;min-height:0}
[class*="st-key-seg_"] button p{white-space:nowrap;font-size:11.5px}
[class*="st-key-seg_"] button::before{content:"";width:7px;height:7px;border-radius:50%;
  background:var(--dot,#4A515A);display:inline-block;margin-right:7px;flex:none}
[class*="st-key-seg_"] button:hover{color:var(--white);border-color:var(--line-3);
  background:rgba(255,255,255,.05);transform:translateY(-1px)}
.st-key-seg_Mapear button{--dot:#4A515A} .st-key-seg_Prospectar button{--dot:#6E7681}
.st-key-seg_Monitorar button{--dot:#939BA5} .st-key-seg_Edital button{--dot:#E89A3C}
.st-key-seg_Ativo button{--dot:#5FB137}
/* botões de município: pílulas com hover azul */
[class*="st-key-cid_"] button{border-radius:999px;font-size:12.5px;font-weight:500;color:var(--text-2);
  border:1px solid var(--line-2);background:rgba(255,255,255,.014);padding:8px 12px}
[class*="st-key-cid_"] button:hover{color:var(--white);border-color:rgba(59,139,208,.5);
  background:var(--acc-blue-soft);transform:translateY(-1px);box-shadow:0 0 18px rgba(59,139,208,.10)}
/* select do filtro de cobertura: pílula compacta */
.st-key-filtro_cobertura div[data-baseweb="select"]>div{border-radius:999px!important;
  background:rgba(255,255,255,.02)!important;border-color:var(--line-2)!important}
.st-key-filtro_cobertura div[data-baseweb="select"]>div:hover{border-color:var(--line-3)!important}

/* ============ SIDEBAR (maquete pfc_app_v3) ============ */
[data-testid="stSidebar"]{background:var(--surface)!important;border-right:1px solid var(--line);
  width:250px!important;min-width:250px!important}
[data-testid="stSidebar"]>div:first-child{padding:18px 14px 16px}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:2px}
.sb-brand{display:flex;align-items:center;gap:12px;padding:2px 8px 14px}
.rings{width:36px;height:36px;position:relative;flex:none}
.rings span{position:absolute;inset:0;border-radius:50%;border:1.7px solid;animation:spin 20s linear infinite}
.rings span:nth-child(1){border-color:transparent var(--accent) transparent transparent}
.rings span:nth-child(2){border-color:transparent transparent var(--sem-high) transparent;inset:6px;
  animation-duration:13s;animation-direction:reverse}
.rings span:nth-child(3){border-color:var(--sem-info) transparent transparent transparent;inset:12px;animation-duration:9s}
.sb-brand .bt{font-weight:700;font-size:15.5px;letter-spacing:-.2px;line-height:1.1;color:var(--ink)}
.sb-brand .bt small{display:block;font-family:var(--mono);font-size:10px;color:var(--accent);
  letter-spacing:.5px;margin-top:4px;font-weight:500}
.sb-sec{font-family:var(--mono);font-size:10.5px;letter-spacing:1.4px;color:var(--dim);
  text-transform:uppercase;padding:16px 8px 7px}
[data-testid="stSidebar"] .stButton>button{width:100%;display:flex;justify-content:flex-start;text-align:left;
  background:transparent;border:none;color:var(--muted);font-size:14px;font-weight:500;
  padding:10px 14px;border-radius:9px;position:relative;box-shadow:none;transition:.15s var(--ease)}
[data-testid="stSidebar"] .stButton>button:hover{color:var(--ink);background:rgba(255,255,255,.03);transform:none}
[data-testid="stSidebar"] .stButton>button[kind="primary"]{color:var(--ink);
  background:rgba(255,255,255,.03);font-weight:600}
[data-testid="stSidebar"] .stButton>button[kind="primary"]::before{content:"";position:absolute;
  left:0;top:7px;bottom:7px;width:3px;border-radius:0 3px 3px 0;background:var(--accent)}
.sb-foot{border-top:1px solid var(--line);margin-top:16px;padding:14px 8px 2px}
.sf{font-family:var(--mono);font-size:11px;color:var(--muted);display:flex;align-items:center;
  gap:9px;margin-bottom:9px;letter-spacing:.3px}
.sf .d{width:7px;height:7px;border-radius:50%;flex:none}
.sf .d.g{background:var(--sem-high);box-shadow:0 0 8px var(--sem-high);animation:pulse2 2s infinite}
.sf .d.o{background:var(--accent);box-shadow:0 0 8px var(--accent)}
.sf .d.n{background:var(--dim)}
@keyframes pulse2{50%{opacity:.4}}

/* ============ TOP BAR (maquete) ============ */
.topbar{display:flex;align-items:center;justify-content:space-between;gap:16px}
.topbar .cr{font-family:var(--mono);font-size:11px;color:var(--dim);letter-spacing:.8px;margin-bottom:6px}
.topbar .cr b{color:var(--accent);font-weight:600}
.topbar .hi{font-size:26px;font-weight:700;letter-spacing:-.6px;color:var(--ink);line-height:1.15}
.topbar .tr-r{display:flex;align-items:center;gap:14px;flex:none}
.live{display:flex;align-items:center;gap:8px;font-family:var(--mono);font-size:12px;color:var(--sem-high);
  background:rgba(74,222,128,.08);border:1px solid rgba(74,222,128,.22);padding:9px 14px;border-radius:9px}
.live .d{width:7px;height:7px;border-radius:50%;background:var(--sem-high);
  box-shadow:0 0 8px var(--sem-high);animation:pulse2 2s infinite}
.live.off{color:var(--accent);background:var(--accent-dim);border-color:rgba(232,135,58,.3)}
.avatar2{width:42px;height:42px;border-radius:11px;display:grid;place-items:center;font-weight:700;
  font-size:15px;color:#111;background:linear-gradient(135deg,var(--accent),#F0A869);flex:none}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


LOGO_SVG = """
<svg width="{size}" height="{size}" viewBox="0 0 42 42" aria-hidden="true">
  <g class="orbit" style="transform-origin:21px 21px">
    <circle cx="21" cy="21" r="18" fill="none" stroke="#3B8BD0" stroke-opacity=".55" stroke-width="1.4"/>
    <circle cx="21" cy="21" r="11.5" fill="none" stroke="#3B8BD0" stroke-opacity=".32" stroke-width="1.2"/>
    <circle cx="21" cy="3.2" r="2.2" fill="#3B8BD0"/><circle cx="38.4" cy="24" r="1.9" fill="#3B8BD0" fill-opacity=".8"/>
  </g>
  <g stroke="#5FB137" stroke-width="1.7" stroke-linecap="round">
    <line x1="21" y1="13.5" x2="21" y2="28.5"/><line x1="13.5" y1="21" x2="28.5" y2="21"/>
    <line x1="15.7" y1="15.7" x2="26.3" y2="26.3"/><line x1="26.3" y1="15.7" x2="15.7" y2="26.3"/>
  </g>
  <circle cx="21" cy="21" r="2.6" fill="#5FB137"/>
</svg>
"""


# --------------------------------------------------------------------------- #
# Helpers de formatação
# --------------------------------------------------------------------------- #
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


def _coletar_editais():
    """Editais candidatos: organizações em status 'Edital' + aba Editais_Privados."""
    itens = []
    try:
        for _, r in df[df[COL_STATUS] == "Edital"].iterrows():
            dt = _parse_data(r.get(COL_JANELA)) or _parse_data(r.get(COL_EDITAL))
            itens.append({"nome": str(r[COL_EMPRESA]), "data": dt, "valor": r[COL_VALVO],
                          "link": str(r.get(COL_URL, "")), "raw": str(r.get(COL_JANELA, ""))})
    except Exception:
        pass
    try:
        ed = dados.carregar_editais_privados()
        if not ed.empty:
            low = {c.lower(): c for c in ed.columns}

            def get(row, *keys):
                for k in keys:
                    if k in low and str(row.get(low[k], "")).strip():
                        return row.get(low[k])
                return ""
            for _, r in ed.iterrows():
                praw = get(r, "prazo", "data", "data-limite", "data limite", "janela")
                itens.append({"nome": str(get(r, "nome", "edital", "organização", "organizacao") or "Edital"),
                              "data": _parse_data(praw), "valor": get(r, "valor", "valor estimado") or 0,
                              "link": str(get(r, "link", "url", "fonte") or ""), "raw": str(praw)})
    except Exception:
        pass
    return itens


def _editais_proximos(dias_max=15):
    """Editais com data-limite entre hoje e dias_max, ordenados por urgência."""
    hoje = datetime.date.today()
    out = []
    for e in _coletar_editais():
        if e["data"] is None:
            continue
        d = (e["data"] - hoje).days
        if 0 <= d <= dias_max:
            e = dict(e)
            e["dias"] = d
            out.append(e)
    out.sort(key=lambda x: x["dias"])
    return out


def breadcrumb(*partes):
    cor = " <span style='color:var(--dim)'>›</span> ".join(
        (f"<b>{esc(p)}</b>" if i == len(partes) - 1 else esc(p))
        for i, p in enumerate(partes))
    st.markdown(f'<div class="bcrumb">{cor}</div>', unsafe_allow_html=True)


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


CORES_STATUS = {"Mapear": "#4A515A", "Prospectar": "#6E7681", "Monitorar": "#939BA5",
                "Edital": "#E89A3C", "Ativo": "#5FB137"}


# --------------------------------------------------------------------------- #
# Navegação (controlada por session_state -> permite navegação programática)
# --------------------------------------------------------------------------- #
def ir_para(pagina: str):
    st.session_state["page"] = pagina


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


# =========================================================================== #
# LOGIN
# =========================================================================== #
def tela_login():
    _a, mid, _b = st.columns([1, 1.25, 1])
    with mid:
        st.markdown(
            f'<div class="login-logo">{LOGO_SVG.format(size=58)}'
            '<div class="wm">Programa Futuro Cientista</div>'
            '<div class="sub">Inteligência de Captação</div></div>',
            unsafe_allow_html=True,
        )
        # st.form: e-mail e senha são enviados juntos no submit (commit atômico,
        # Enter envia) — evita corrida de estado e torna o login robusto.
        with st.form("login_form", border=True):
            st.markdown('<div class="login-h">🔐 Entrar no painel</div>'
                        '<div class="login-p">Acesso restrito à equipe de captação</div>',
                        unsafe_allow_html=True)
            email = st.text_input("E-mail", placeholder="voce@pfc.org", key="login_email")
            senha = st.text_input("Senha", type="password", placeholder="••••••••",
                                  key="login_senha")
            entrar = st.form_submit_button("Entrar  →", type="primary",
                                           use_container_width=True)
        if entrar:
            u = USERS.get((email or "").strip().lower())
            if u and senha == u["senha"]:
                st.session_state["user"] = {
                    "nome": u["nome"], "email": (email or "").strip().lower(),
                    "inicial": u["inicial"], "perfil": u["perfil"],
                    "bg": u["bg"], "bd": u["bd"], "tx": u["tx"],
                }
                st.session_state["page"] = "Visão geral"
                st.session_state.pop("login_err", None)
                st.rerun()
            else:
                st.session_state["login_err"] = True
        if st.session_state.get("login_err"):
            st.error("E-mail ou senha incorretos. Tente novamente.")
        st.caption("🧪 Demo — fabio@pfc.org · otavio@pfc.org  (senha: pfc2026)")


# Gate de autenticação: nada carrega antes do login.
if "user" not in st.session_state:
    tela_login()
    st.stop()

USER = st.session_state["user"]
st.session_state.setdefault("page", "Visão geral")

# --------------------------------------------------------------------------- #
# Carregamento de dados (após login)
# --------------------------------------------------------------------------- #
df, modo_conectado = dados.carregar_empresas()
TOTAL = len(df)
HINT_ESCRITA = "🔒 Conecte ao Google Sheets para habilitar escrita."


# --------------------------------------------------------------------------- #
# Sidebar de navegação (maquete pfc_app_v3) + top bar
# --------------------------------------------------------------------------- #
_n_naoverif = int((~df[COL_VERIF].apply(verificada_ok)).sum()) if TOTAL else 0
NAV_SECOES = [("Operação", ["Visão geral", "Radar", "Ranking", "Funil"]),
              ("Dados", ["Metodologia", "Verificação"])]


def _rotulo_nav(p: str) -> str:
    rotulo = f"{PAGE_ICONS[p]} {p}"
    if p == "Ranking":
        rotulo += f" · {TOTAL}"
    elif p == "Verificação" and _n_naoverif:
        rotulo += f" · {_n_naoverif}"
    return rotulo


def render_sidebar():
    with st.sidebar:
        st.markdown(
            '<div class="sb-brand"><div class="rings"><span></span><span></span><span></span></div>'
            '<div class="bt">Futuro Cientista<small>CAPTAÇÃO PRIVADA</small></div></div>',
            unsafe_allow_html=True,
        )
        for secao, paginas in NAV_SECOES:
            st.markdown(f'<div class="sb-sec">{secao}</div>', unsafe_allow_html=True)
            for p in paginas:
                st.button(_rotulo_nav(p), key=f"nav_{p}", use_container_width=True,
                          type="primary" if st.session_state["page"] == p else "secondary",
                          on_click=ir_para, args=(p,))
        status = ('<div class="sf"><span class="d g"></span>SHEETS CONECTADO</div>'
                  if modo_conectado else
                  '<div class="sf"><span class="d o"></span>MODO LOCAL · CSV</div>')
        st.markdown(f'<div class="sb-foot">{status}'
                    '<div class="sf"><span class="d n"></span>ÚLTIMO SCAN · 06:00</div></div>',
                    unsafe_allow_html=True)
        if st.button("🔓 Sair", key="logout", use_container_width=True):
            for k in ("user", "page", "login_email", "login_senha"):
                st.session_state.pop(k, None)
            st.rerun()


def render_header():
    hora = datetime.datetime.now().hour
    saud = "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"
    primeiro = USER["nome"].split()[0]
    live = ('<div class="live"><span class="d"></span>RADAR ATIVO</div>' if modo_conectado
            else '<div class="live off">MODO LOCAL · CSV</div>')
    st.markdown(
        f'<div class="topbar"><div>'
        f'<div class="cr"><b>CAPTAÇÃO PRIVADA</b> · {esc(st.session_state["page"].upper())}</div>'
        f'<div class="hi">{saud}, {esc(primeiro)}</div></div>'
        f'<div class="tr-r">{live}'
        f'<span class="avatar2" title="{esc(USER["email"])}">{esc(USER["inicial"])}</span></div></div>'
        '<div class="hr-line"></div>',
        unsafe_allow_html=True,
    )


render_sidebar()
render_header()
PAGINA = st.session_state["page"]

if df.empty:
    st.warning("Nenhuma organização encontrada na base. Verifique o CSV ou a planilha.")


# --------------------------------------------------------------------------- #
# Callbacks de escrita (rodam ANTES do corpo: cache já limpo na releitura)
# --------------------------------------------------------------------------- #
def _cb_mudar_status(org_id, sel_key):
    novo = st.session_state.get(sel_key)
    st.session_state[f"status_msg_{org_id}"] = dados.atualizar_status(org_id, novo)


def _cb_salvar_obs(org_id, ta_key):
    res = dados.salvar_observacao(org_id, st.session_state.get(ta_key, ""))
    st.session_state[f"obs_msg_{org_id}"] = res
    if res.get("sucesso"):
        st.session_state[ta_key] = ""


def _mostrar_resultado(res):
    if not res:
        return
    (st.success if res.get("sucesso") else st.warning)(
        res.get("mensagem", "Operação concluída."))


# =========================================================================== #
# MODAIS (st.dialog)
# =========================================================================== #
@st.dialog("Editais fechando em breve", width="large")
def dlg_prazos(prox):
    breadcrumb("Visão geral", "Prazos de editais")
    if not prox:
        st.caption("Nenhum edital com data-limite nos próximos 15 dias.")
        return
    st.markdown(f"#### ⏰ {len(prox)} edital(is) fechando em até 15 dias")
    for e in prox:
        dias = e["dias"]
        cor = "var(--red)" if dias < 7 else "var(--orange-2)" if dias < 15 else "var(--muted)"
        if dias == 0:
            quando = "fecha hoje"
        elif dias == 1:
            quando = "fecha amanhã"
        else:
            quando = f"fecha em {dias} dias"
        link = ""
        if str(e.get("link", "")).startswith("http"):
            link = (f'<a href="{esc(e["link"])}" target="_blank" rel="noopener" '
                    f'style="color:var(--blue-2);text-decoration:none">abrir ›</a>')
        st.markdown(
            f'<div class="lrow2"><div class="l"><div>'
            f'<div class="nm">{esc(e["nome"])}</div>'
            f'<div class="sx" style="color:{cor};font-weight:600">{quando}</div></div></div>'
            f'<div class="rt"><span class="alvo">{brl_curto(e.get("valor"))}</span>{link}</div></div>',
            unsafe_allow_html=True,
        )
    st.caption("ℹ️ Datas lidas das organizações em status “Edital” e da aba Editais_Privados.")


@st.dialog("Breakdown do pipeline", width="large")
def dlg_breakdown():
    breadcrumb("Visão geral", "Organizações mapeadas")
    st.markdown(f"#### 🗂️ {TOTAL} organizações por status")
    cont = df[COL_STATUS].value_counts()
    for s in STATUS_FUNIL:
        n = int(cont.get(s, 0))
        pct = (n / TOTAL * 100) if TOTAL else 0
        st.markdown(
            f'<div style="margin:9px 0 3px;display:flex;justify-content:space-between;font-size:13px">'
            f'<span style="color:var(--text)">{status_badge(s)}</span>'
            f'<span style="color:var(--muted)"><b style="color:var(--text);font-family:var(--disp)">{n}</b> · {pct:.0f}%</span></div>'
            f'<div class="ltrack" style="height:8px"><i style="width:{pct:.1f}%;background:{CORES_STATUS[s]}"></i></div>',
            unsafe_allow_html=True,
        )
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("📋 Ver ranking completo  →", type="primary", use_container_width=True):
        ir_para("Ranking")
        st.rerun()


@st.dialog("Organizações por status", width="large")
def dlg_status_list(status):
    breadcrumb("Visão geral", status)
    sub = df[df[COL_STATUS] == status].sort_values(COL_SCORE, ascending=False)
    st.markdown(f"#### {status_badge(status)} &nbsp; {len(sub)} organizações",
                unsafe_allow_html=True)
    q = st.text_input("Busca rápida", placeholder="filtrar por nome ou setor…",
                      key=f"q_{status}", label_visibility="collapsed")
    if q.strip():
        ql = q.strip().lower()
        sub = sub[sub[COL_EMPRESA].str.lower().str.contains(ql, na=False)
                  | sub[COL_SETOR].str.lower().str.contains(ql, na=False)]
    st.markdown(lista_orgs_html(sub), unsafe_allow_html=True)


@st.dialog("Top organizações por valor-alvo", width="large")
def dlg_valor_top10():
    breadcrumb("Visão geral", "Valor-alvo")
    top = df.sort_values(COL_VALVO, ascending=False).head(10)
    total = float(df[COL_VALVO].sum())
    st.markdown(f"#### 💰 Pipeline total: {brl_curto(total)} · top 10 por valor-alvo")
    if PLOTLY_OK and not top.empty:
        fig = go.Figure(go.Bar(
            x=top[COL_VALVO][::-1], y=top[COL_EMPRESA][::-1], orientation="h",
            marker=dict(color="#5FB137", line=dict(color="rgba(255,255,255,.1)", width=1)),
            hovertemplate="<b>%{y}</b><br>Valor-alvo: R$ %{x:,.0f}<extra></extra>",
        ))
        fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,.06)", zeroline=False)
        fig.update_yaxes(showgrid=False)
        st.plotly_chart(estilo_plotly(fig, altura=360), use_container_width=True,
                        config={"displayModeBar": False})
    else:
        st.markdown(lista_orgs_html(top, limite=10), unsafe_allow_html=True)


@st.dialog("Atuação no município", width="large")
def dlg_cidade(cidade, ativa=True, evento="A definir"):
    breadcrumb("Visão geral", "Cobertura regional", cidade)
    mask = (df[COL_SEDE].str.contains(cidade, case=False, na=False)
            | df[COL_REGIAO].str.contains(cidade, case=False, na=False))
    sub = df[mask].sort_values(COL_SCORE, ascending=False)
    benef = 120 + (len(cidade) * 37) % 480  # estimativa de demonstração
    st.markdown(f"#### 🗺️ {esc(cidade)} "
                f"<span class='vbadge {'vb-ok' if ativa else 'vb-no'}'>"
                f"{'município ativo' if ativa else 'expansão 2024'}</span>",
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="kpi" style="--accent:var(--orange);border-radius:12px">'
                f'<div class="lab">Organizações atuando</div><div class="val">{len(sub)}</div></div>',
                unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi" style="--accent:var(--green);border-radius:12px">'
                f'<div class="lab">Beneficiários (estim.)</div><div class="val">~{benef}</div></div>',
                unsafe_allow_html=True)
    c3.markdown(f'<div class="kpi" style="--accent:var(--blue);border-radius:12px">'
                f'<div class="lab">Próximo evento PFC</div>'
                f'<div class="val" style="font-size:18px;padding-top:9px">{esc(evento)}</div></div>',
                unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown("**Organizações ligadas a este território**")
    if sub.empty:
        st.caption("Nenhuma organização com sede/região citando este município na base. "
                   "Boa oportunidade de mapeamento!")
    else:
        st.markdown(lista_orgs_html(sub, limite=30), unsafe_allow_html=True)
    st.caption("ℹ️ Beneficiários e próximo evento são estimativas de demonstração.")


@st.dialog("Dossiê da organização", width="large")
def mostrar_dossie(org: dict):
    org_id = org.get(COL_ID)
    base = dados.carregar_empresas()[0]
    if not base.empty:
        m = base[base[COL_ID].astype(str).str.strip() == str(org_id).strip()]
        if not m.empty:
            org = m.iloc[0].to_dict()

    breadcrumb("Ranking", str(org.get(COL_EMPRESA, "")).strip() or "Dossiê")
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

    st.markdown(
        f"""
        <div class="dr-eyebrow"><span style="width:8px;height:8px;border-radius:50%;
            background:{sem_cor(org.get(COL_SEMAFORO))};display:inline-block"></span>
            {texto_ou(org.get(COL_PRIORIDADE))} · {texto_ou(org.get(COL_SETOR))}</div>
        <h2 style="margin:0;font-size:22px">{esc(nome) or '—'}</h2>
        <div class="dr-sub">{esc(' · '.join([s for s in [str(org.get(COL_INSTITUTO,'')).strip(),
            str(org.get(COL_SUBSETOR,'')).strip()] if s]) or '—')}</div>
        <div style="display:flex;align-items:center;gap:16px;margin-top:8px">
          <div class="dr-score" style="color:{cor_score}">{int(score)}<small> / 100</small></div>
          <div style="flex:1">{seg_html(score, classe='dr-seg')}</div>
        </div>
        <div style="font-size:10.5px;color:var(--dim);margin-top:4px">
            decomposição ilustrativa: aderência · valor · região · acionabilidade</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="dr-sec"><h3>📈 Captação</h3>
          <div class="frow"><span class="fl">Tipo</span><span class="fv">{texto_ou(org.get(COL_TIPO))}</span></div>
          <div class="frow"><span class="fl">Modalidade</span><span class="fv">{texto_ou(org.get(COL_MODALIDADE))}</span></div>
          <div class="frow"><span class="fl">Chance de êxito</span><span class="fv">{chance_txt}</span></div>
          <div class="frow"><span class="fl">Faixa de valor</span><span class="fv">{faixa}</span></div>
          <div class="frow"><span class="fl">Valor-alvo</span><span class="fv">{brl(org.get(COL_VALVO))}</span></div>
          <div class="frow"><span class="fl">Janela</span><span class="fv">{texto_ou(org.get(COL_JANELA))}</span></div>
          <div class="frow"><span class="fl">Edital / programa</span><span class="fv">{texto_ou(org.get(COL_EDITAL))}</span></div>
        </div>
        <div class="dr-sec"><h3>🎯 Alinhamento com o PFC</h3>
          <div class="fblock"><div class="fl">Público-alvo</div><div class="fv">{texto_ou(org.get(COL_PUBLICO))}</div></div>
          <div class="fblock"><div class="fl">Encaixe com o PFC</div><div class="fv">{texto_ou(org.get(COL_ENCAIXE))}</div></div>
          <div class="fblock"><div class="fl">Proposta recomendada</div><div class="fv">{texto_ou(org.get(COL_PROPOSTA))}</div></div>
        </div>
        <div class="dr-sec"><h3>📍 Território</h3>
          <div class="frow"><span class="fl">Presença PFC</span><span class="fv">{texto_ou(org.get(COL_PRESENCA))}</span></div>
          <div class="frow"><span class="fl">Região</span><span class="fv">{texto_ou(org.get(COL_REGIAO))}</span></div>
          <div class="frow"><span class="fl">Sede</span><span class="fv">{texto_ou(org.get(COL_SEDE))}</span></div>
          <div class="frow"><span class="fl">UF</span><span class="fv">{texto_ou(org.get(COL_UF))}</span></div>
        </div>
        <div class="dr-sec"><h3>✉️ Contato &amp; próxima ação</h3>
          <div class="fblock"><div class="fl">Próxima ação</div><div class="fv">{texto_ou(org.get(COL_PROX_ACAO))}</div></div>
          <div class="frow"><span class="fl">Responsável</span><span class="fv">{texto_ou(org.get(COL_RESP))}</span></div>
          <div class="frow"><span class="fl">Canal</span><span class="fv">{texto_ou(org.get(COL_CANAL))}</span></div>
          <div class="frow"><span class="fl">Social</span><span class="fv">{texto_ou(org.get(COL_SOCIAL))}</span></div>
        </div>
        <div class="dr-sec"><h3>🔗 Fonte <span class="vbadge {'vb-ok' if vok else 'vb-no'}">{'✓ verificado' if vok else 'a verificar'}</span></h3></div>
        """,
        unsafe_allow_html=True,
    )
    if url_ok:
        # st.link_button = âncora nativa garantidamente clicável (abre em nova aba).
        st.link_button("↗ Abrir fonte oficial", url, use_container_width=True)
        st.caption(url)
    else:
        st.markdown('<div style="font-size:12.5px;color:var(--orange-2)">Site oficial ainda a confirmar.</div>',
                    unsafe_allow_html=True)

    st.markdown('<div class="dr-sec"><h3>🔄 Mudar status (grava na planilha)</h3></div>',
                unsafe_allow_html=True)
    opcoes = list(STATUS_FUNIL)
    atual = str(org.get(COL_STATUS, "")).strip()
    if atual and atual not in opcoes:
        opcoes.append(atual)
    idx = opcoes.index(atual) if atual in opcoes else 0
    key_status = f"status_{org_id}"
    st.selectbox("Status", opcoes, index=idx, key=key_status,
                 on_change=_cb_mudar_status, args=(org_id, key_status),
                 disabled=not modo_conectado, label_visibility="collapsed")
    _mostrar_resultado(st.session_state.pop(f"status_msg_{org_id}", None))
    if not modo_conectado:
        st.caption(HINT_ESCRITA)

    st.markdown('<div class="dr-sec"><h3>💬 Observações</h3></div>', unsafe_allow_html=True)
    obs = str(org.get(COL_OBS, "")).strip()
    if obs and obs != "—":
        for linha in obs.split("\n"):
            if linha.strip():
                st.markdown(f'<div class="ncard">{esc(linha.strip())}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-size:12px;color:var(--dim)">Nenhuma observação ainda.</div>',
                    unsafe_allow_html=True)
    key_obs = f"obs_{org_id}"
    st.text_area("Adicionar observação", key=key_obs,
                 placeholder="Adicionar uma observação sobre esta organização…",
                 label_visibility="collapsed", disabled=not modo_conectado)
    st.button("➕ Salvar observação", key=f"btn_obs_{org_id}", use_container_width=True,
              on_click=_cb_salvar_obs, args=(org_id, key_obs), disabled=not modo_conectado)
    _mostrar_resultado(st.session_state.pop(f"obs_msg_{org_id}", None))
    if not modo_conectado:
        st.caption(HINT_ESCRITA)

    # ----- E-mail de abordagem (template local em Python, sem IA) -----
    st.markdown('<div class="dr-sec"><h3>✉️ E-mail de abordagem</h3></div>', unsafe_allow_html=True)
    gen_key = f"email_show_{org_id}"
    if st.button("✉️ Gerar e-mail de abordagem", key=f"genmail_{org_id}", use_container_width=True):
        st.session_state[gen_key] = True
    if st.session_state.get(gen_key):
        setor_e = str(org.get(COL_SETOR, "")).strip() or "seu setor"
        encaixe_e = str(org.get(COL_ENCAIXE, "")).strip()
        if not encaixe_e or encaixe_e == "—":
            encaixe_e = "promover ciência, educação e projeto de vida para jovens da rede pública"
        assunto = f"Parceria {nome} × Programa Futuro Cientista (PFC/UFSCar)"
        corpo = (
            f"Prezados(as) da {nome},\n\n"
            "Meu nome é [Seu nome] e represento o Programa Futuro Cientista (PFC), "
            "tecnologia social certificada pela Fundação Banco do Brasil. O PFC adota "
            "cientificamente jovens da escola pública — acompanhando-os do 6º ano até a "
            "universidade — por meio de mentoria, ciência e projeto de vida.\n\n"
            f"Acompanhamos o trabalho da {nome} no setor de {setor_e} e enxergamos uma "
            f"conexão natural com a nossa missão: {encaixe_e}. Acreditamos que uma parceria "
            "pode ampliar o impacto de ambos junto a esses estudantes.\n\n"
            "Gostaríamos de propor uma breve conversa para apresentar o programa e explorar "
            "formas de colaboração. Teria disponibilidade nas próximas semanas?\n\n"
            "Desde já agradeço a atenção.\n\n"
            "Atenciosamente,\n[Seu nome]\nPrograma Futuro Cientista (PFC) · UFSCar"
        )
        st.text_input("Assunto sugerido", value=assunto, key=f"email_subj_{org_id}")
        lbl = "Rascunho do e-mail (edite a vontade)"
        st.text_area(lbl, value=corpo, key=f"email_body_{org_id}", height=300)
        copy_html = (EMAIL_COPY_TEMPLATE
                     .replace("__FALLBACK__", json.dumps(corpo))
                     .replace("__LABEL__", json.dumps(lbl)))
        components.html(copy_html, height=46)


# =========================================================================== #
# COMPONENTES v2 · VISÃO GERAL
# ---------------------------------------------------------------------------
# st.components.v2 monta o HTML direto no DOM do app (shadow root, sem
# iframe): altura automática (height="content"), sem corte nem scroll
# interno. As fontes (Space Grotesk/Inter) são herdadas do documento e as
# cores de texto usam var(--st-text-color) com fallback para o token local.
# Só visuais nesta rodada — os cliques continuam nos widgets nativos.
# =========================================================================== #
_KPI_V2_CSS = """
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem}
@media (max-width:900px){.kpi-grid{grid-template-columns:1fr 1fr}}
.kpi-card{position:relative;overflow:hidden;border-radius:14px;padding:20px 20px 18px;
  background:linear-gradient(180deg,rgba(255,255,255,.045),rgba(255,255,255,.008) 60%),#0D1119;
  border:1px solid rgba(255,255,255,.07);opacity:0;transform:translateY(10px);
  transition:transform .3s cubic-bezier(.22,.61,.36,1),border-color .3s,box-shadow .3s,opacity .45s ease}
.kpi-card.in{opacity:1;transform:none}
.kpi-card::before{content:"";position:absolute;left:0;right:0;top:0;height:1px;
  background:linear-gradient(90deg,transparent,var(--acc),transparent);opacity:.28;transition:opacity .3s}
.kpi-card:hover{transform:translateY(-3px);
  border-color:rgba(255,255,255,.18);
  border-color:color-mix(in srgb,var(--acc) 38%,rgba(255,255,255,.12));
  box-shadow:0 12px 34px rgba(0,0,0,.45),0 0 0 1px var(--glow),0 0 30px var(--glow)}
.kpi-card:hover::before{opacity:.85}
.kpi-top{display:flex;align-items:center;gap:8px}
.kpi-ic{font-size:13px;line-height:1;opacity:.95}
.kpi-lab{font-family:'Inter',system-ui,sans-serif;font-size:10.5px;font-weight:600;
  letter-spacing:.12em;text-transform:uppercase;color:#828A94;white-space:nowrap;
  overflow:hidden;text-overflow:ellipsis}
.kpi-val{font-family:'Space Grotesk',system-ui,sans-serif;font-weight:600;font-size:37px;
  letter-spacing:-.02em;line-height:1;font-variant-numeric:tabular-nums;
  color:var(--acc);margin:15px 0 7px}
.kpi-foot{font-family:'Inter',system-ui,sans-serif;font-size:12px;color:#565E68}
.kpi-foot b{color:#C2C7CE;font-weight:600}
"""

_KPI_V2_JS = """
export default function(component){
  const {data, parentElement} = component;
  const old = parentElement.querySelector('.kpi-grid'); if (old) old.remove();
  const grid = document.createElement('div'); grid.className = 'kpi-grid';
  const items = (data && data.items) || [];
  items.forEach(function(k, i){
    const card = document.createElement('div'); card.className = 'kpi-card';
    card.style.setProperty('--acc', k.accent);
    card.style.setProperty('--glow', k.glow);
    card.innerHTML =
      '<div class="kpi-top"><span class="kpi-ic">' + k.icon + '</span>' +
      '<span class="kpi-lab" title="' + k.label + '">' + k.label + '</span></div>' +
      '<div class="kpi-val">' + k.value + '</div>' +
      '<div class="kpi-foot">' + k.foot + '</div>';
    grid.appendChild(card);
    setTimeout(function(){ card.classList.add('in'); }, 60 + i * 90);
    if (Number.isFinite(k.num)) {           // count-up só para valores inteiros
      const el = card.querySelector('.kpi-val');
      const t0 = performance.now(), dur = 950;
      (function step(){
        const p = Math.min(1, (performance.now() - t0) / dur);
        const e = 1 - Math.pow(1 - p, 3);
        el.textContent = String(Math.round(k.num * e));
        if (p < 1) { requestAnimationFrame(step); }
      })();
    }
  });
  parentElement.appendChild(grid);
  return function(){ grid.remove(); };
}
"""

_FUNIL_V2_CSS = """
.fb-card{background:rgba(13,17,25,.62);border:1px solid rgba(255,255,255,.06);border-radius:16px;
  overflow:hidden;-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);
  box-shadow:0 1px 2px rgba(0,0,0,.16),inset 0 0 0 1px rgba(255,255,255,.018)}
.fb-h{padding:18px 22px 14px;border-bottom:1px solid rgba(255,255,255,.05)}
.fb-h h2{font-family:'Space Grotesk',system-ui,sans-serif;font-weight:600;font-size:15.5px;
  margin:0;color:var(--st-text-color,#E9EBEE)}
.fb-h .cap{font-family:'Inter',system-ui,sans-serif;font-size:12px;color:#565E68;margin-top:3px}
.fb-body{padding:20px 22px 22px;display:flex;flex-direction:column;gap:15px}
.fb-row{display:grid;grid-template-columns:100px 1fr 92px;align-items:center;gap:12px;
  font-family:'Inter',system-ui,sans-serif}
.fb-name{font-size:12.5px;font-weight:500;color:#C2C7CE;display:flex;align-items:center;gap:8px;white-space:nowrap}
.fb-dot{width:8px;height:8px;border-radius:3px;flex:none;background:var(--c)}
.fb-track{position:relative;height:9px;border-radius:6px;background:rgba(255,255,255,.045);
  overflow:hidden;box-shadow:inset 0 0 0 1px rgba(255,255,255,.03)}
.fb-fill{position:absolute;top:0;bottom:0;left:0;width:0;border-radius:6px;background:var(--c);
  transition:width 1s cubic-bezier(.22,.61,.36,1)}
.fb-fill::after{content:"";position:absolute;inset:0;border-radius:6px;
  background:linear-gradient(90deg,transparent 38%,rgba(255,255,255,.25) 50%,transparent 62%);
  background-size:220% 100%;background-position:180% 0;
  animation:fb-shine 2.4s ease-in-out 1.15s 2}
@keyframes fb-shine{to{background-position:-80% 0}}
.fb-num{text-align:right;font-size:12px;color:#565E68;white-space:nowrap}
.fb-num b{font-family:'Space Grotesk',system-ui,sans-serif;font-weight:600;font-size:14px;
  color:var(--st-text-color,#E9EBEE);font-variant-numeric:tabular-nums}
"""

_FUNIL_V2_JS = """
export default function(component){
  const {data, parentElement} = component;
  const old = parentElement.querySelector('.fb-card'); if (old) old.remove();
  const d = data || {}, rows = d.rows || [];
  const card = document.createElement('div'); card.className = 'fb-card';
  let body = '';
  rows.forEach(function(r){
    body += '<div class="fb-row" style="--c:' + r.cor + '">' +
      '<span class="fb-name"><span class="fb-dot"></span>' + r.status + '</span>' +
      '<span class="fb-track"><span class="fb-fill" data-w="' + r.pct + '"></span></span>' +
      '<span class="fb-num"><b>' + r.n + '</b> · ' + r.pct_lab + '%</span></div>';
  });
  card.innerHTML = '<div class="fb-h"><h2>' + d.titulo + '</h2>' +
    '<div class="cap">' + d.cap + '</div></div>' +
    '<div class="fb-body">' + body + '</div>';
  parentElement.appendChild(card);
  const fills = card.querySelectorAll('.fb-fill');
  requestAnimationFrame(function(){ requestAnimationFrame(function(){
    fills.forEach(function(f, i){
      f.style.transitionDelay = (i * 110) + 'ms';
      f.style.width = f.getAttribute('data-w') + '%';
    });
  }); });
  return function(){ card.remove(); };
}
"""

_DONUT_V2_CSS = """
.dn-card{background:rgba(13,17,25,.62);border:1px solid rgba(255,255,255,.06);border-radius:16px;
  overflow:hidden;-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);
  box-shadow:0 1px 2px rgba(0,0,0,.16),inset 0 0 0 1px rgba(255,255,255,.018)}
.dn-h{padding:18px 22px 14px;border-bottom:1px solid rgba(255,255,255,.05)}
.dn-h h2{font-family:'Space Grotesk',system-ui,sans-serif;font-weight:600;font-size:15.5px;
  margin:0;color:var(--st-text-color,#E9EBEE)}
.dn-h .cap{font-family:'Inter',system-ui,sans-serif;font-size:12px;color:#565E68;margin-top:3px}
.dn-body{padding:16px 20px 20px;display:grid;place-items:center;gap:12px}
.dn-svgwrap{display:grid;place-items:center}
.dn-svgwrap svg .seg{transition:filter .25s ease}
.dn-svgwrap svg .seg:hover{filter:brightness(1.3)}
.dn-total{font-family:'Space Grotesk',system-ui,sans-serif;font-weight:600;font-variant-numeric:tabular-nums}
.dn-leg{display:flex;flex-wrap:wrap;gap:8px 16px;justify-content:center;font-family:'Inter',system-ui,sans-serif}
.dn-leg span{display:inline-flex;align-items:center;gap:7px;font-size:12px;color:#828A94}
.dn-leg i{width:8px;height:8px;border-radius:3px;flex:none}
.dn-leg b{font-family:'Space Grotesk',system-ui,sans-serif;font-weight:600;
  color:var(--st-text-color,#E9EBEE);font-variant-numeric:tabular-nums}
"""

_DONUT_V2_JS = """
export default function(component){
  const {data, parentElement} = component;
  const old = parentElement.querySelector('.dn-card'); if (old) old.remove();
  const d = data || {}, segs = d.segs || [], total = d.total || 0;
  const NS = 'http://www.w3.org/2000/svg';
  const R = 72, C = 2 * Math.PI * R, GAP = segs.length > 1 ? 3 : 0;
  const card = document.createElement('div'); card.className = 'dn-card';
  card.innerHTML = '<div class="dn-h"><h2>' + d.titulo + '</h2>' +
    '<div class="cap">' + d.cap + '</div></div>' +
    '<div class="dn-body"><div class="dn-svgwrap"></div><div class="dn-leg"></div></div>';
  parentElement.appendChild(card);

  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', '0 0 200 200');
  svg.setAttribute('width', '212'); svg.setAttribute('height', '212');
  const ring = document.createElementNS(NS, 'circle');
  ring.setAttribute('cx', 100); ring.setAttribute('cy', 100); ring.setAttribute('r', R);
  ring.setAttribute('fill', 'none'); ring.setAttribute('stroke', 'rgba(255,255,255,.05)');
  ring.setAttribute('stroke-width', 13);
  svg.appendChild(ring);

  let start = 0;
  const arcs = segs.map(function(s){
    const len = Math.max(0, s.frac * C - GAP);
    const c = document.createElementNS(NS, 'circle');
    c.setAttribute('class', 'seg');
    c.setAttribute('cx', 100); c.setAttribute('cy', 100); c.setAttribute('r', R);
    c.setAttribute('fill', 'none'); c.setAttribute('stroke', s.cor);
    c.setAttribute('stroke-width', 13);
    c.setAttribute('stroke-dasharray', '0 ' + C);
    c.setAttribute('stroke-dashoffset', -start);
    c.setAttribute('transform', 'rotate(-90 100 100)');
    const tip = document.createElementNS(NS, 'title');
    tip.textContent = s.label + ' \\u00b7 ' + s.n;
    c.appendChild(tip);
    svg.appendChild(c);
    const arc = { el: c, start: start, len: len };
    start += s.frac * C;
    return arc;
  });

  const num = document.createElementNS(NS, 'text');
  num.setAttribute('x', 100); num.setAttribute('y', 96);
  num.setAttribute('text-anchor', 'middle'); num.setAttribute('dominant-baseline', 'central');
  num.setAttribute('font-size', 44); num.setAttribute('fill', '#FFFFFF');
  num.setAttribute('class', 'dn-total'); num.textContent = '0';
  svg.appendChild(num);
  const sub = document.createElementNS(NS, 'text');
  sub.setAttribute('x', 100); sub.setAttribute('y', 126);
  sub.setAttribute('text-anchor', 'middle');
  sub.setAttribute('font-size', 11); sub.setAttribute('fill', '#828A94');
  sub.setAttribute('font-family', 'Inter, system-ui, sans-serif');
  sub.textContent = d.sub || '';
  svg.appendChild(sub);
  card.querySelector('.dn-svgwrap').appendChild(svg);

  const leg = card.querySelector('.dn-leg');
  segs.forEach(function(s){
    const item = document.createElement('span');
    item.innerHTML = '<i style="background:' + s.cor + '"></i>' + s.label + ' <b>' + s.n + '</b>';
    leg.appendChild(item);
  });

  const t0 = performance.now(), dur = 1000;   // desenho sequencial dos arcos
  (function step(){
    const p = Math.min(1, (performance.now() - t0) / dur);
    const e = 1 - Math.pow(1 - p, 3);
    arcs.forEach(function(a){
      const vis = Math.max(0, Math.min(a.len, e * C - a.start));
      a.el.setAttribute('stroke-dasharray', vis + ' ' + (C - vis));
    });
    num.textContent = String(Math.round(total * e));
    if (p < 1) { requestAnimationFrame(step); }
  })();
  return function(){ card.remove(); };
}
"""

_kpis_v2 = components_v2.component("pfc_kpis", css=_KPI_V2_CSS, js=_KPI_V2_JS)
_funil_v2 = components_v2.component("pfc_funil_barras", css=_FUNIL_V2_CSS, js=_FUNIL_V2_JS)
_donut_v2 = components_v2.component("pfc_donut", css=_DONUT_V2_CSS, js=_DONUT_V2_JS)


# =========================================================================== #
# PÁGINA · VISÃO GERAL
# =========================================================================== #
def page_visao():
    st.markdown(
        '<div class="phead"><h1>Painel de captação</h1>'
        f'<p>{TOTAL} organizações monitoradas · clique nos cartões e segmentos para explorar</p></div>',
        unsafe_allow_html=True,
    )

    # ---- Alerta de prazos de editais (próximos 15 dias) ----
    prox = _editais_proximos(15)
    if prox:
        urgentes = sum(1 for e in prox if e["dias"] < 7)
        rotulo = (f"⏰ {len(prox)} edital(is) fecham nos próximos 15 dias"
                  + (f"  ·  {urgentes} em menos de 7 dias" if urgentes else "")
                  + "  —  ver lista")
        if st.button(rotulo, key="alerta_prazos", use_container_width=True):
            dlg_prazos(prox)
    else:
        st.markdown(
            '<div style="border:1px solid var(--line);border-radius:12px;background:var(--surface);'
            'padding:11px 16px;font-size:13px;color:var(--muted);margin-bottom:6px">'
            '⏰ Nenhum edital fechando em breve · pipeline sob controle</div>',
            unsafe_allow_html=True,
        )

    cont = df[COL_STATUS].value_counts() if TOTAL else pd.Series(dtype=int)
    n_prospectar = int(cont.get("Prospectar", 0))
    n_monitorar = int(cont.get("Monitorar", 0))
    n_edital = int(cont.get("Edital", 0))
    valor_total = float(df[COL_VALVO].sum()) if TOTAL else 0.0
    n_verif = int(df[COL_VERIF].apply(verificada_ok).sum()) if TOTAL else 0

    # KPIs em Custom Component v2 (visual); as ações continuam nos botões nativos.
    kpi_cards = [
        {"icon": "📚", "label": "Organizações mapeadas", "value": str(TOTAL), "num": TOTAL,
         "foot": f"<b>{n_verif}</b> de {TOTAL} fontes verificadas",
         "accent": "#FFFFFF", "glow": "rgba(255,255,255,.10)"},
        {"icon": "📈", "label": "Em prospecção ativa", "value": str(n_prospectar), "num": n_prospectar,
         "foot": f"<b>{n_monitorar}</b> monitorando · <b>{n_edital}</b> em edital",
         "accent": "#F2911E", "glow": "rgba(242,145,30,.16)"},
        {"icon": "💰", "label": "Valor-alvo potencial", "value": brl_curto(valor_total), "num": None,
         "foot": "soma do pipeline de captação",
         "accent": "#3B8BD0", "glow": "rgba(59,139,208,.16)"},
        {"icon": "⚡", "label": "Oportunidades hoje", "value": "4", "num": 4,
         "foot": "novas · aguardando revisão",
         "accent": "#5FB137", "glow": "rgba(95,177,55,.16)"},
    ]
    _kpis_v2(data={"items": kpi_cards}, key="kpis_visao")

    acoes = [("Ver breakdown", "breakdown"), ("Listar prospecção", "prospeccao"),
             ("Top 10 por valor", "valor"), ("Abrir Radar", "radar")]
    cols = st.columns(4)
    for col, (btn_lab, acao) in zip(cols, acoes):
        with col:
            if st.button(btn_lab, key=f"kpi_{acao}", use_container_width=True):
                if acao == "breakdown":
                    dlg_breakdown()
                elif acao == "prospeccao":
                    dlg_status_list("Prospectar")
                elif acao == "valor":
                    dlg_valor_top10()
                elif acao == "radar":
                    ir_para("Radar")
                    st.rerun()

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    esq, dir_ = st.columns([1.15, 1])

    # ---- Funil por etapa: barras animadas (componente v2) + chips clicáveis ----
    with esq:
        fun_rows = []
        for s in STATUS_FUNIL:
            n = int(cont.get(s, 0))
            pct = (n / TOTAL * 100) if TOTAL else 0.0
            fun_rows.append({"status": s, "n": n, "pct": round(pct, 1),
                             "pct_lab": f"{pct:.0f}", "cor": CORES_STATUS[s]})
        _funil_v2(data={"titulo": "Distribuição do funil",
                        "cap": "barras por etapa · clique num chip para ver as organizações",
                        "rows": fun_rows}, key="funil_visao")
        chip_cols = st.columns(len(STATUS_FUNIL))
        for j, s in enumerate(STATUS_FUNIL):
            n = int(cont.get(s, 0))
            if chip_cols[j].button(f"{s} · {n}", key=f"seg_{s}", use_container_width=True):
                dlg_status_list(s)

    # ---- Donut de status: SVG clean com total no centro (componente v2) ----
    with dir_:
        segs = [{"label": s, "n": int(cont.get(s, 0)),
                 "frac": (int(cont.get(s, 0)) / TOTAL) if TOTAL else 0.0,
                 "cor": CORES_STATUS[s]}
                for s in STATUS_FUNIL if int(cont.get(s, 0)) > 0]
        _donut_v2(data={"titulo": "Pipeline por status",
                        "cap": "distribuição das organizações",
                        "total": TOTAL, "sub": "organizações", "segs": segs},
                  key="donut_visao")

    # ---- Cobertura regional interativa ----
    st.markdown(
        '<div class="phead" style="margin-top:6px"><h2 style="font-size:18px">🗺️ Cobertura regional</h2>'
        '<p>municípios com atuação do PFC · clique numa cidade para ver detalhes</p></div>',
        unsafe_allow_html=True,
    )
    ATIVAS = ["Iperó", "Tatuí", "Salto", "São Roque", "Rio Claro", "Coronel Macedo", "Mirassol"]
    PROXIMAS = ["Dois Córregos", "Corumbataí"]
    EVENTOS = {"Iperó": "Feira de Ciências · ago/2026", "Tatuí": "Clube de Ciências · jul/2026",
               "Salto": "Mostra STEM · set/2026", "São Roque": "Maratona PFC · out/2026",
               "Rio Claro": "Olimpíada · ago/2026", "Coronel Macedo": "Visita técnica · jul/2026",
               "Mirassol": "Roda de mentoria · set/2026", "Dois Córregos": "Implantação · 2024",
               "Corumbataí": "Implantação · 2024"}
    filtro = st.selectbox("Filtro de cobertura",
                          ["Apenas ativas", "Todas", "Próximas (2024)"],
                          key="filtro_cobertura", label_visibility="collapsed")
    if filtro == "Apenas ativas":
        cidades = [(c, True) for c in ATIVAS]
    elif filtro == "Próximas (2024)":
        cidades = [(c, False) for c in PROXIMAS]
    else:
        cidades = [(c, True) for c in ATIVAS] + [(c, False) for c in PROXIMAS]

    n_por_linha = 5
    for inicio in range(0, len(cidades), n_por_linha):
        linha = cidades[inicio:inicio + n_por_linha]
        ccols = st.columns(n_por_linha)
        for k, (cidade, ativa) in enumerate(linha):
            rotulo = ("📍 " if ativa else "🆕 ") + cidade
            # key sem espaço/acento -> classe st-key-cid_* válida p/ CSS
            slug = re.sub(r"[^0-9A-Za-z]+", "_", cidade)
            if ccols[k].button(rotulo, key=f"cid_{slug}", use_container_width=True):
                dlg_cidade(cidade, ativa=ativa, evento=EVENTOS.get(cidade, "A definir"))


# =========================================================================== #
# PÁGINA · RANKING
# =========================================================================== #
def page_ranking():
    st.markdown(
        '<div class="phead"><h1>Ranking de captação</h1>'
        '<p>ordenado por Score PFC · busca e filtro ao vivo · abra o dossiê completo</p></div>',
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
                     help="Recarrega os dados (limpa o cache de 60s)"):
            dados.limpar_caches()
            st.rerun()

    rank = df.sort_values(COL_SCORE, ascending=False).copy() if TOTAL else df.copy()
    if busca.strip() and TOTAL:
        q = busca.strip().lower()
        rank = rank[rank[COL_EMPRESA].str.lower().str.contains(q, na=False)
                    | rank[COL_SETOR].str.lower().str.contains(q, na=False)]
    if filtro_status != "Todos":
        rank = rank[rank[COL_STATUS] == filtro_status]

    st.caption(f"{len(rank)} organização(ões) · mostrando as primeiras 30 por score")
    st.markdown('<div class="rkhead"><span>Organização</span><span>Score PFC</span>'
                '<span>Status</span><span class="r">Valor-alvo</span></div>',
                unsafe_allow_html=True)

    for i, (_, row) in enumerate(rank.head(30).iterrows()):
        cA, cB, cC, cD, cE = st.columns([2.7, 1.45, 1, 1, 0.95], gap="medium")
        paridade = "odd" if i % 2 else "even"
        with cA:
            st.markdown(
                f'<div class="org {paridade}"><span class="sem" style="background:{sem_cor(row[COL_SEMAFORO])}"></span>'
                f'<div><div class="nm">{texto_ou(row[COL_EMPRESA])}</div>'
                f'<div class="st">{texto_ou(row[COL_SETOR])}</div></div></div>',
                unsafe_allow_html=True)
        with cB:
            st.markdown(f'<div class="scorecell"><span class="scoreN">{int(row[COL_SCORE])}</span>'
                        f'{seg_html(row[COL_SCORE])}</div>', unsafe_allow_html=True)
        with cC:
            st.markdown(status_badge(row[COL_STATUS]), unsafe_allow_html=True)
        with cD:
            st.markdown(f'<div class="alvo">{brl_curto(row[COL_VALVO])}</div>', unsafe_allow_html=True)
        with cE:
            if st.button("Ver dossiê", key=f"dos_{row[COL_ID]}_{i}"):
                mostrar_dossie(row.to_dict())

    if len(rank) > 30:
        st.markdown(
            f'<div class="pad" style="color:var(--dim);font-size:12px">'
            f'+ {len(rank) - 30} organizações · refine a busca para ver mais</div>',
            unsafe_allow_html=True,
        )


# =========================================================================== #
# PÁGINA · RADAR
# =========================================================================== #
def _score_novidade(nv) -> float:
    try:
        return float(str(nv.get("Score Aderência", "")).replace(",", ".") or 0)
    except (TypeError, ValueError):
        return 0.0


def page_radar():
    st.markdown(
        '<div class="phead"><h1>Radar de oportunidades</h1>'
        '<p>fila real gravada pelo radar automático · aprove para virar Edital na base</p></div>',
        unsafe_allow_html=True,
    )

    fila = sorted(dados.carregar_novidades_pendentes(), key=_score_novidade, reverse=True)
    total = len(fila)

    col_fila, col_lado = st.columns([1.6, 1])
    with col_fila:
        cap = f"{total} nova(s) · aprove ou descarte" if total else "sem novidades pendentes"
        st.markdown(
            '<div class="card-h" style="border:1px solid var(--line);border-bottom:none;'
            'border-radius:16px 16px 0 0;background:var(--surface)"><div><h2>Fila de revisão</h2>'
            f'<div class="cap">{esc(cap)}</div></div></div>',
            unsafe_allow_html=True,
        )
        _mostrar_resultado(st.session_state.pop("radar_msg", None))
        if not modo_conectado:
            st.caption(HINT_ESCRITA + " — aprovar/descartar grava na aba Novidades_pendentes.")

        if not fila:
            st.markdown(
                '<div class="lead" style="text-align:center;padding:26px 18px">'
                '<div style="font-size:26px;margin-bottom:6px">🛰️</div>'
                '<div class="ttl">Nenhuma oportunidade nova no momento</div>'
                '<div class="why">O radar roda todo dia às 06:00 e coloca aqui os editais '
                'que passam no filtro. Volte mais tarde.</div></div>',
                unsafe_allow_html=True,
            )
        else:
            for i, nv in enumerate(fila):
                fonte = str(nv.get("Fonte", "")).strip() or "Fonte"
                titulo = str(nv.get("Título", "")).strip() or "(sem título)"
                desc = str(nv.get("Descrição", "")).strip()
                desc_trunc = (desc[:200].rstrip() + "…") if len(desc) > 200 else desc
                prazo = str(nv.get("Prazo", "")).strip()
                valor = str(nv.get("Valor estimado", "")).strip()
                link = str(nv.get("Link da fonte", "")).strip()
                sc = _score_novidade(nv)
                cls = "hi" if sc >= 70 else "mid" if sc >= 45 else "lo"

                metas = [f"<b>Fonte:</b> {esc(fonte)}"]
                if prazo:
                    metas.append(f"<b>Prazo:</b> {esc(prazo)}")
                if valor:
                    metas.append(f"<b>Valor:</b> {esc(valor)}")
                link_html = (f'<a class="srclink" href="{esc(link)}" target="_blank" '
                             f'rel="noopener">↗ {esc(link)}</a>') if link.startswith("http") else ""
                desc_html = f'<div class="why">{esc(desc_trunc)}</div>' if desc_trunc else ""

                st.markdown(
                    f'<div class="lead"><div class="lead-top">'
                    f'<span class="src">{esc(fonte)}</span>'
                    f'<span class="fit {cls}">score {int(sc)}</span></div>'
                    f'<div class="ttl">{esc(titulo)}</div>{desc_html}'
                    f'<div class="meta">{" · ".join(metas)}</div>{link_html}</div>',
                    unsafe_allow_html=True,
                )
                b1, b2, _sp = st.columns([1.3, 1, 1.7])
                with b1:
                    if st.button("✓ Aprovar (vira Edital)", key=f"rad_ok_{i}",
                                 type="primary", disabled=not modo_conectado):
                        res = dados.aprovar_novidade(nv)
                        st.session_state["radar_msg"] = res
                        st.toast(res["mensagem"], icon="✅" if res["sucesso"] else "⚠️")
                        st.rerun()
                with b2:
                    if st.button("Descartar", key=f"rad_no_{i}", disabled=not modo_conectado):
                        res = dados.descartar_novidade(nv)
                        st.session_state["radar_msg"] = res
                        st.toast(res["mensagem"], icon="🗑️" if res["sucesso"] else "⚠️")
                        st.rerun()

    with col_lado:
        fontes = ["Prosas", "ABCR", "Obs. 3º Setor", "Mapa OSC (IPEA)", "CNPq", "FAPESP",
                  "Finep", "Fund. Banco do Brasil", "Itaú Social", "Inst. Unibanco",
                  "Fund. Telefônica", "Fund. Lemann", "Inst. Ayrton Senna", "Inst. CPFL",
                  "GIFE", "Fund. Bradesco", "Fund. Roberto Marinho", "Parque Tec. Sorocaba"]
        chips = "".join(f'<span class="src-tag">{esc(f)}</span>' for f in fontes)
        st.markdown(
            f"""
            <div class="card"><div class="card-h"><div><h2>Fontes monitoradas</h2>
              <div class="cap">{len(fontes)} fontes · varredura diária às 06:00</div></div></div>
              <div class="pad">{chips}<div class="note">O radar vigia fontes conhecidas e estáveis —
              nada de varrer a internet inteira. Você decide o que entra na base.</div></div></div>
            <div class="card"><div class="card-h"><div><h2>Sua fila agora</h2>
              <div class="cap">itens aguardando revisão</div></div></div>
              <div class="pad">
                <div class="statline"><span style="color:var(--muted)">Pendentes de revisão</span>
                  <b style="color:var(--green)">{total}</b></div>
                <div class="note">Aprovar cria um card em <b>Edital</b> no Funil/Ranking;
                descartar apenas remove da fila.</div>
              </div></div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================================== #
# PÁGINA · FUNIL
# =========================================================================== #
ACENTOS_HEX = {"Mapear": "#4A515A", "Prospectar": "#6E7681", "Monitorar": "#939BA5",
               "Edital": "#E89A3C", "Ativo": "#5FB137"}


def _kanban_estatico():
    """Fallback sem drag-and-drop (caso o componente não esteja disponível)."""
    acentos = {"Mapear": "var(--dim)", "Prospectar": "var(--orange)", "Monitorar": "var(--blue)",
               "Edital": "var(--green)", "Ativo": "var(--green-2)"}
    colunas_html = ""
    for s in STATUS_FUNIL:
        grupo = df[df[COL_STATUS] == s].sort_values(COL_SCORE, ascending=False) if TOTAL else df
        n = len(grupo)
        cards = ""
        for _, row in grupo.head(6).iterrows():
            cards += (f'<div class="kcard"><div class="kn">{texto_ou(row[COL_EMPRESA])}</div>'
                      f'<div class="ks">{texto_ou(row[COL_SETOR])}</div>'
                      f'<div class="kf"><span class="kchip" style="{score_chip_cor(row[COL_SCORE])}">'
                      f'{int(row[COL_SCORE])}</span><span class="kval">{brl_curto(row[COL_VALVO])}</span></div></div>')
        if n > 6:
            cards += f'<div class="kmore">+ {n - 6} organizações</div>'
        if n == 0:
            cards = '<div class="kmore">vazio</div>'
        colunas_html += (f'<div class="kcol"><div class="kcol-h">'
                         f'<span><span class="accent" style="background:{acentos[s]}"></span>{s}</span>'
                         f'<span class="ct">{n}</span></div><div class="kbody">{cards}</div></div>')
    st.markdown(f'<div class="kan">{colunas_html}</div>', unsafe_allow_html=True)
    st.caption("ℹ️ Arrastar-e-soltar indisponível neste ambiente. "
               "Abra o **dossiê** de uma organização no Ranking para mudar o status.")


def page_funil():
    st.markdown(
        '<div class="phead"><h1>Funil de relacionamento</h1>'
        '<p>arraste os cards entre as colunas para mudar o status — grava direto na planilha</p></div>',
        unsafe_allow_html=True,
    )
    st.caption("🖱️ Arraste um card para outra coluna para mudar o **Status**. "
               "Também é possível mudar pelo **dossiê** (Ranking).")
    _mostrar_resultado(st.session_state.pop("kanban_msg", None))

    if not KANBAN_DND_OK:
        _kanban_estatico()
        return

    # Monta os dados das 5 colunas (todos os cards) para o componente.
    colunas = []
    for s in STATUS_FUNIL:
        grupo = df[df[COL_STATUS] == s].sort_values(COL_SCORE, ascending=False) if TOTAL else df.iloc[0:0]
        cards = [{
            "id": str(row[COL_ID]),
            "status": s,
            "nome": str(row[COL_EMPRESA]),
            "setor": str(row[COL_SETOR]) or "—",
            "score": int(row[COL_SCORE]),
            "chip": score_chip_hex(row[COL_SCORE]),
            "valor": brl_curto(row[COL_VALVO]),
        } for _, row in grupo.iterrows()]
        colunas.append({"status": s, "cor": ACENTOS_HEX[s], "cards": cards})

    resultado = _kanban_component(colunas=colunas, editable=bool(modo_conectado),
                                  key="kanban_dnd", default=None)

    # Processa um drop novo (identificado pelo nonce) -> grava e re-renderiza.
    if isinstance(resultado, dict):
        nonce = resultado.get("nonce")
        if nonce and nonce != st.session_state.get("kanban_nonce"):
            st.session_state["kanban_nonce"] = nonce
            oid = str(resultado.get("org_id", "")).strip()
            novo = str(resultado.get("novo_status", "")).strip()
            if oid and novo in STATUS_FUNIL:
                res = dados.atualizar_status(oid, novo)
                st.session_state["kanban_msg"] = res
                st.toast(res.get("mensagem", ""), icon="✅" if res.get("sucesso") else "⚠️")
            else:
                st.session_state["kanban_msg"] = {
                    "sucesso": False, "mensagem": "Movimento inválido (status fora dos 5 permitidos)."}
            # Re-renderiza: sucesso confirma a nova coluna; falha faz o card voltar à origem.
            st.rerun()

    if not modo_conectado:
        st.caption(HINT_ESCRITA + " — ao arrastar em modo CSV o app mostra um aviso e o card volta.")


# Gráfico de Score: donut único elegante + chips clicáveis (SVG/JS autocontido).
ORBITAL_TEMPLATE = r"""<!doctype html><html><head><meta charset="utf-8"><style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:transparent;font-family:'Inter',system-ui,sans-serif;color:#E9EBEE}
.wrap{background:rgba(20,24,32,.6);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.06);border-radius:14px;overflow:hidden;box-shadow:0 1px 2px rgba(0,0,0,.16),inset 0 0 0 1px rgba(255,255,255,.02)}
.h{padding:18px 20px 13px;border-bottom:1px solid rgba(255,255,255,.06)}
.h h2{font-family:'Space Grotesk';font-weight:600;font-size:15.5px;margin:0}
.h .cap{font-size:12px;color:#565E68;margin-top:3px}
.body{padding:14px 18px 18px}
.orbit-wrap{display:grid;place-items:center}
#arc{transition:stroke .35s ease;cursor:default}
.cn{font-family:'Space Grotesk';font-weight:600;transition:fill .35s ease}
.chips{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:14px}
.chip{display:inline-flex;align-items:center;gap:7px;padding:7px 12px;border:1px solid rgba(255,255,255,.07);border-radius:999px;cursor:pointer;font-size:12.5px;color:#C2C7CE;background:rgba(255,255,255,.015);transition:background .22s ease,border-color .22s ease,transform .15s ease,color .22s ease}
.chip:hover{background:rgba(255,255,255,.05);border-color:rgba(255,255,255,.16);transform:translateY(-2px);color:#fff}
.chip.sel{background:rgba(255,255,255,.08);border-color:rgba(255,255,255,.24);color:#fff}
.chip .dot{width:8px;height:8px;border-radius:50%;flex:none}
.chip b{font-family:'Space Grotesk';font-weight:600}
.hint{font-size:11px;color:#565E68;text-align:center;margin-top:11px}
</style></head><body>
<div class="wrap"><div class="h"><h2>Anatomia do Score</h2><div class="cap" id="cap">__NOME__</div></div>
<div class="body">
<div class="orbit-wrap"><svg id="svg" width="206" height="206" viewBox="0 0 200 200" aria-label="Score">
  <defs><linearGradient id="grad" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#E89A3C"/><stop offset="1" stop-color="#5FB137"/></linearGradient></defs>
  <circle cx="100" cy="100" r="80" fill="none" stroke="rgba(255,255,255,.06)" stroke-width="10"/>
  <circle id="arc" cx="100" cy="100" r="80" fill="none" stroke="url(#grad)" stroke-width="10" stroke-linecap="round"
          transform="rotate(-90 100 100)"/>
  <text id="cn" class="cn" x="100" y="100" text-anchor="middle" dominant-baseline="central" font-size="52" fill="#E9EBEE">__TOTAL__</text>
  <text x="100" y="130" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#828A94" font-family="Inter">de 100</text>
</svg></div>
<div class="chips" id="chips"></div>
<div class="hint">clique num critério para destacar · clique de novo para o total</div>
</div></div>
<script>
(function(){
  var DATA=__DATA__, TOTAL=__TOTAL__, NS='http://www.w3.org/2000/svg';
  var arc=document.getElementById('arc'), cn=document.getElementById('cn'), chipsEl=document.getElementById('chips');
  var R=80, C=2*Math.PI*R, sel=-1, curShown=0;
  function setArc(v){ var len=Math.max(0,Math.min(100,v))/100*C; arc.setAttribute('stroke-dasharray', len+' '+(C-len)); }
  function tween(to){ var from=curShown, t0=performance.now(), dur=520;
    function step(t){ var p=Math.min(1,(t-t0)/dur), e=1-Math.pow(1-p,3); var val=from+(to-from)*e; cn.textContent=Math.round(val); setArc(val); if(p<1){requestAnimationFrame(step);} else {curShown=to;} }
    requestAnimationFrame(step); }
  DATA.forEach(function(d,i){
    var c=document.createElement('div'); c.className='chip'; c.setAttribute('data-i',i);
    c.innerHTML='<span class="dot" style="background:'+d.c+'"></span>'+d.n+' <b>'+d.v+'</b>';
    chipsEl.appendChild(c);
  });
  function apply(){
    [].forEach.call(chipsEl.children,function(c,i){if(i===sel){c.classList.add('sel');}else{c.classList.remove('sel');}});
    if(sel<0){ cn.setAttribute('fill','#E9EBEE'); arc.setAttribute('stroke','url(#grad)'); tween(TOTAL); }
    else { var d=DATA[sel]; cn.setAttribute('fill',d.c); arc.setAttribute('stroke',d.c); tween(d.v); }
  }
  function pick(i){ sel=(sel===i?-1:i); apply(); }
  [].forEach.call(chipsEl.children,function(c){ c.addEventListener('click',function(){pick(+c.getAttribute('data-i'));}); });
  setArc(0); tween(TOTAL);
})();
</script></body></html>"""


# Botão "Copiar" do e-mail (copia o texto editado do text_area; fallback = rascunho).
EMAIL_COPY_TEMPLATE = r"""<!doctype html><html><head><meta charset="utf-8"><style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@500&display=swap');
*{box-sizing:border-box;margin:0;padding:0}html,body{background:transparent}
#cp{font-family:'Inter',system-ui,sans-serif;font-size:13px;font-weight:500;color:#C2C7CE;background:rgba(255,255,255,.04);
  border:1px solid rgba(255,255,255,.12);border-radius:9px;padding:8px 14px;cursor:pointer;transition:all .2s ease}
#cp:hover{color:#fff;border-color:rgba(255,255,255,.28);background:rgba(255,255,255,.08)}
</style></head><body>
<button id="cp">📋 Copiar e-mail</button>
<script>
(function(){
  var b=document.getElementById('cp'), FALLBACK=__FALLBACK__, LABEL=__LABEL__;
  function legacy(t){var x=document.createElement('textarea');x.value=t;x.style.position='fixed';x.style.opacity='0';document.body.appendChild(x);x.focus();x.select();try{document.execCommand('copy');}catch(e){}document.body.removeChild(x);}
  b.addEventListener('click',function(){
    var txt=FALLBACK;
    try{var ta=window.parent.document.querySelector('textarea[aria-label="'+LABEL+'"]');if(ta&&ta.value){txt=ta.value;}}catch(e){}
    try{if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(txt)['catch'](function(){legacy(txt);});}else{legacy(txt);}}catch(e){legacy(txt);}
    b.textContent='✓ Copiado!';setTimeout(function(){b.textContent='📋 Copiar e-mail';},1500);
  });
})();
</script></body></html>"""


# =========================================================================== #
# PÁGINA · METODOLOGIA
# =========================================================================== #
def page_metodo():
    st.markdown(
        '<div class="phead"><h1>Como o Score PFC é calculado</h1>'
        '<p>quatro componentes, pesos fixos, origem rastreável — explore cada um</p></div>',
        unsafe_allow_html=True,
    )
    componentes = [
        ("🎯 Aderência ao DNA", 35, "var(--orange)", "#F2911E",
         "Mede o quanto a causa da organização conversa com o DNA do PFC: ciência, STEM, "
         "educação pública, permanência escolar e projeto de vida. É o maior peso porque "
         "sem aderência de missão a parceria não se sustenta, por mais dinheiro que exista.",
         "Ex.: uma fundação que financia Clubes de Ciência e feiras científicas = aderência altíssima."),
        ("💰 Capacidade & fit de valor", 25, "var(--green)", "#5FB137",
         "Avalia a capacidade financeira do parceiro e se o ticket típico dele cabe no que o "
         "PFC precisa captar. Premia organizações com histórico de investimento social e faixa "
         "de valor compatível com os projetos do programa.",
         "Ex.: instituto com editais de R$ 100–300 mil casa melhor que um patrocínio pontual de R$ 5 mil."),
        ("🗺️ Proximidade regional", 20, "var(--blue)", "#3B8BD0",
         "Pondera a presença do parceiro nos municípios onde o PFC atua (Iperó, Tatuí, Salto, "
         "Sorocaba e região). Proximidade geográfica reduz atrito logístico e aumenta a chance "
         "de visitas, eventos e engajamento local.",
         "Ex.: empresa com unidade em Sorocaba pontua mais que uma sediada fora do estado."),
        ("⚡ Acionabilidade", 20, "var(--muted)", "#969CA6",
         "Mede o quão fácil é agir AGORA: existe canal de contato claro, edital aberto, "
         "porta de entrada conhecida? Premia oportunidades destravadas e penaliza as que "
         "exigem meses de prospecção fria.",
         "Ex.: edital com inscrições abertas e contato do ESG mapeado = acionabilidade alta."),
    ]
    st.markdown("#### Pesos & leitura — clique para expandir cada critério")
    for nome, w, var, _hex, desc, exemplo in componentes:
        with st.expander(f"{nome}  ·  {w}%"):
            st.markdown(
                f'<div class="ltrack" style="height:6px;margin:2px 0 12px">'
                f'<i style="width:{w}%;background:{var}"></i></div>'
                f'<div style="font-size:13px;color:var(--text);line-height:1.65">{esc(desc)}</div>'
                f'<div class="miniex">💡 {esc(exemplo)}</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    g1, g2 = st.columns([1, 1])
    with g1:
        nomes = df.sort_values(COL_SCORE, ascending=False)[COL_EMPRESA].tolist() if TOTAL else ["—"]
        escolha = st.selectbox("Ver score de:", nomes, index=0, key="score_org")
        sel = df[df[COL_EMPRESA] == escolha]
        score_sel = int(sel.iloc[0][COL_SCORE]) if not sel.empty else 0
        nome_sel = escolha
        # Sub-componentes ILUSTRATIVOS derivados do Score PFC real da empresa.
        # TODO: trocar pela leitura de colunas reais (ex.: "Score Aderência",
        # "Score Fit", ...) na planilha quando esses dados existirem.
        comps = [
            {"n": "Aderência", "v": min(100, score_sel), "c": "#E89A3C"},
            {"n": "Fit", "v": max(0, score_sel - 2), "c": "#5FB137"},
            {"n": "Região", "v": max(0, score_sel - 4), "c": "#5B9BD5"},
            {"n": "Ação", "v": max(0, score_sel - 3), "c": "#9AA2AC"},
        ]
        orb = (ORBITAL_TEMPLATE
               .replace("__DATA__", json.dumps(comps))
               .replace("__TOTAL__", str(score_sel))
               .replace("__NOME__", html.escape(nome_sel)))
        components.html(orb, height=470)
        st.caption("Sub-componentes ilustrativos derivados do Score PFC da planilha.")
    with g2:
        st.markdown(
            '<div class="card"><div class="card-h"><div><h2>Fórmula</h2>'
            '<div class="cap">transparente e auditável</div></div></div><div class="pad">'
            '<div class="legend">'
            + "".join(
                f'<div class="lrow"><span class="nm"><span class="sw" style="background:{c}"></span>{n}</span>'
                f'<span class="wt">{w}%</span><span class="ltrack"><i style="width:{w}%;background:{c}"></i></span></div>'
                for n, w, c in [("Aderência ao DNA", 35, "var(--orange)"),
                                ("Capacidade & fit de valor", 25, "var(--green)"),
                                ("Proximidade regional", 20, "var(--blue)"),
                                ("Acionabilidade", 20, "var(--muted)")])
            + '</div><div class="divider"></div>'
            '<p style="font-size:12.5px;color:var(--muted);line-height:1.7">'
            '<b style="color:var(--text)">Score = 0,35·Aderência + 0,25·Valor + 0,20·Região + 0,20·Acionabilidade.</b><br>'
            'No MVP, o app usa a coluna <code>Score PFC</code> já existente na planilha; esta aba '
            'documenta e visualiza a fórmula para que qualquer número seja defensável em reunião.</p>'
            '</div></div>',
            unsafe_allow_html=True,
        )

    # ---- Casos de uso do Score ----
    st.markdown('<div class="phead" style="margin-top:4px">'
                '<h2 style="font-size:18px">📌 Casos de uso do Score</h2>'
                '<p>organizações reais da base e por que pontuaram assim</p></div>',
                unsafe_allow_html=True)
    casos_def = {
        "John Deere": "Agro + educação de juventude, proximidade histórica com o PFC e ticket alto: "
                      "aderência e acionabilidade no topo.",
        "Instituto 3M": "Ciência e STEM no centro da atuação, presença em Campinas/Sorocaba e fonte "
                        "verificada — forte em aderência e região.",
        "Fundação Telefônica Vivo": "Competências digitais e formação docente, atuação nacional e "
                                    "porta de entrada clara: alto fit e acionabilidade.",
        "Instituto Coca-Cola Brasil": "Projeto de vida e empregabilidade jovem na região metropolitana "
                                      "de SP, com programa estruturado para piloto.",
    }
    casos = []
    if TOTAL:
        idx = df.set_index(df[COL_EMPRESA].astype(str))
        for nome, motivo in casos_def.items():
            if nome in idx.index:
                linha = idx.loc[nome]
                if isinstance(linha, pd.DataFrame):
                    linha = linha.iloc[0]
                casos.append((nome, int(linha[COL_SCORE]), str(linha[COL_SETOR]), motivo))
    if not casos:
        casos = [("John Deere", 95, "Agronegócio", casos_def["John Deere"]),
                 ("Instituto 3M", 92, "Indústria/Tec.", casos_def["Instituto 3M"]),
                 ("Fundação Telefônica Vivo", 90, "Telecom", casos_def["Fundação Telefônica Vivo"]),
                 ("Instituto Coca-Cola Brasil", 88, "Bebidas", casos_def["Instituto Coca-Cola Brasil"])]
    cs = st.columns(len(casos))
    for col, (nome, score, setor, motivo) in zip(cs, casos):
        cor = "var(--green-2)" if score >= 85 else "var(--orange-2)" if score >= 70 else "var(--muted)"
        col.markdown(
            f'<div class="caso"><div class="ch"><span class="cn">{esc(nome)}</span>'
            f'<span class="cs" style="color:{cor}">{score}</span></div>'
            f'<div style="font-size:11px;color:var(--dim);margin-bottom:7px">{esc(setor)}</div>'
            f'<div class="cw">{esc(motivo)}</div></div>',
            unsafe_allow_html=True,
        )


# =========================================================================== #
# FONTES SUGERIDAS PELO RADAR (aba Verificação)
# ---------------------------------------------------------------------------
# radar/avaliar_candidatas.py grava fichas em candidatas_avaliadas.csv; aqui
# o usuário confirma com 1 clique: aprovar adiciona a URL sugerida ao
# config_fontes.json (Camada 2 do radar) — arquivos locais, planilha intocada.
# =========================================================================== #
_RADAR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "radar")
_AVALIADAS_CSV = os.path.join(_RADAR_DIR, "candidatas_avaliadas.csv")
_CONFIG_FONTES = os.path.join(_RADAR_DIR, "config_fontes.json")


def _ler_candidatas_avaliadas() -> pd.DataFrame:
    try:
        return pd.read_csv(_AVALIADAS_CSV, dtype=str).fillna("")
    except Exception:
        return pd.DataFrame()


def _atualizar_status_candidata(dominio: str, novo_status: str) -> bool:
    try:
        df_c = pd.read_csv(_AVALIADAS_CSV, dtype=str).fillna("")
        df_c.loc[df_c["dominio"] == dominio, "status"] = novo_status
        df_c.to_csv(_AVALIADAS_CSV, index=False, encoding="utf-8")
        return True
    except Exception:
        return False


def _aprovar_fonte_no_config(nome: str, url: str) -> bool:
    """Acrescenta a fonte ao config_fontes.json (Camada 2), sem duplicar URL."""
    try:
        try:
            with open(_CONFIG_FONTES, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = []
        if not isinstance(cfg, list):
            cfg = []
        urls = {str(e.get("url", "")).rstrip("/") for e in cfg}
        if url.rstrip("/") not in urls:
            cfg.append({"nome": nome, "url": url,
                        "categoria": "radar-sugerida", "ativo": True})
            with open(_CONFIG_FONTES, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _secao_fontes_sugeridas():
    df_c = _ler_candidatas_avaliadas()
    if df_c.empty or "status" not in df_c.columns:
        return
    pend = df_c[df_c["status"] == "pendente"].copy()
    pend["aderencia_n"] = pd.to_numeric(pend.get("aderencia"), errors="coerce").fillna(0)
    sug = pend[pend["veredito"].isin(["recomendada", "talvez"])]
    sug = sug.sort_values(["veredito", "aderencia_n"], ascending=[True, False])

    st.markdown(
        '<div class="phead" style="margin-top:18px"><h2 style="font-size:18px">'
        '📡 Novas fontes sugeridas pelo radar</h2>'
        '<p>o radar descobre e avalia; você só confirma — aprovar liga a fonte na Camada 2</p></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<span class="pill {"ok" if len(sug) else "local"}" style="margin-bottom:10px">'
        f'{len(sug)} fonte(s) sugerida(s) aguardando sua confirmação</span>',
        unsafe_allow_html=True,
    )
    if sug.empty:
        st.caption("Nenhuma sugestão pendente. Rode `python -m radar.avaliar_candidatas` "
                   "após uma varredura do radar para gerar novas fichas.")
        return

    for _, r in sug.iterrows():
        dom = str(r["dominio"])
        slug = re.sub(r"[^0-9A-Za-z]+", "_", dom)
        verd = str(r["veredito"])
        v_cls, v_txt = (("vb-ok", "recomendada") if verd == "recomendada"
                        else ("vb-no", "talvez"))
        editais_txt = ("✓ parece listar editais" if str(r["tem_editais"]) == "True"
                       else "sem seção de editais aparente")
        st.markdown(
            f'<div class="lead" style="margin-bottom:8px"><div class="lead-top">'
            f'<span class="src">{esc(dom)}</span>'
            f'<span class="vbadge {v_cls}">{v_txt}</span></div>'
            f'<div class="ttl">{texto_ou(r["nome"], dom)}</div>'
            f'<div class="meta">aderência <b>{int(float(r["aderencia_n"]))}</b> · '
            f'{esc(editais_txt)} · <b>{esc(r["mencoes"])}</b> menção(ões) · '
            f'<a href="{esc(r["url_sugerida"])}" target="_blank" rel="noopener" '
            f'style="color:var(--blue-2);text-decoration:none">abrir página sugerida ↗</a>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        b1, b2, _sp = st.columns([1.4, 1, 2.6])
        with b1:
            if st.button("✓ Aprovar como fonte", key=f"fnt_ok_{slug}", type="primary"):
                ok = (_aprovar_fonte_no_config(str(r["nome"]) or dom, str(r["url_sugerida"]))
                      and _atualizar_status_candidata(dom, "aprovada"))
                st.toast("Fonte adicionada à Camada 2 do radar." if ok
                         else "Não consegui gravar — veja os arquivos do radar.",
                         icon="✅" if ok else "⚠️")
                st.rerun()
        with b2:
            if st.button("✗ Descartar", key=f"fnt_no_{slug}"):
                ok = _atualizar_status_candidata(dom, "descartada")
                st.toast("Sugestão descartada." if ok else "Não consegui gravar.",
                         icon="🗑️" if ok else "⚠️")
                st.rerun()

    n_desc = int((pend["veredito"] == "descartar").sum())
    if n_desc:
        st.caption(f"➕ {n_desc} candidata(s) com veredito automático “descartar” "
                   "(baixa aderência e sem editais) ficam fora desta lista.")


# =========================================================================== #
# PÁGINA · VERIFICAÇÃO (saneamento da base)
# =========================================================================== #
def page_verificacao():
    st.markdown(
        '<div class="phead"><h1>Verificação de fontes</h1>'
        '<p>saneie a base: confirme o site oficial de cada organização e marque como verificada</p></div>',
        unsafe_allow_html=True,
    )

    n_verif = int(df[COL_VERIF].apply(verificada_ok).sum()) if TOTAL else 0
    pct = (n_verif / TOTAL * 100) if TOTAL else 0
    st.markdown(
        f'<div class="card"><div class="pad">'
        f'<div class="vprog-lab"><span class="big">{n_verif}/{TOTAL} verificadas</span>'
        f'<span class="pct">{pct:.0f}%</span></div>'
        f'<div class="vbar"><i style="width:{pct:.1f}%"></i></div></div></div>',
        unsafe_allow_html=True,
    )
    if not modo_conectado:
        st.caption(HINT_ESCRITA + " — marcar verificada/pendente grava na coluna Fonte verificada.")

    nao = (df[~df[COL_VERIF].apply(verificada_ok)].sort_values(COL_SCORE, ascending=False)
           if TOTAL else df.iloc[0:0])
    if nao.empty:
        st.success("🎉 Todas as fontes da base estão verificadas. Nada a sanear!")
        _secao_fontes_sugeridas()
        return

    st.session_state.setdefault("verif_n", 10)
    mostrados = nao.head(st.session_state["verif_n"])
    st.caption(f"{len(nao)} organização(ões) a verificar (por Score PFC) · mostrando {len(mostrados)}")

    for _, row in mostrados.iterrows():
        oid = row[COL_ID]
        nome = str(row[COL_EMPRESA])
        url_atual = str(row[COL_URL]).strip()
        pend = "pendente" in str(row[COL_VERIF]).lower()
        badge = ('<span class="vbadge2 vb-pend">verificação pendente</span>' if pend
                 else '<span class="vbadge2 vb-nao">não verificada</span>')
        google = f"https://www.google.com/search?q={quote_plus(nome)}+site+oficial"
        with st.container(border=True):
            st.markdown(
                f'<div style="display:flex;align-items:center;justify-content:space-between;gap:10px">'
                f'<div class="vhead"><span class="sem" style="background:{sem_cor(row[COL_SEMAFORO])}"></span>'
                f'<div><div class="nm">{texto_ou(nome)}</div>'
                f'<div class="st">{texto_ou(row[COL_SETOR])} · Score {int(row[COL_SCORE])}</div></div></div>'
                f'{badge}</div>'
                + (f'<div class="vcur">URL atual sugerido: {esc(url_atual)}</div>'
                   if url_atual.startswith("http") else '<div class="vcur">Sem URL sugerido.</div>'),
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns([1, 2])
            with c1:
                st.link_button("🔍 Buscar fonte oficial", google, use_container_width=True)
            with c2:
                url_val = st.text_input(
                    "URL real", key=f"vurl_{oid}", placeholder="https://site-oficial.org.br/…",
                    label_visibility="collapsed", disabled=not modo_conectado)
            b1, b2 = st.columns(2)
            with b1:
                if st.button("✓ Marcar como verificada", key=f"vok_{oid}",
                             use_container_width=True, disabled=not modo_conectado):
                    res = dados.marcar_fonte(oid, "Verificada", url_val)
                    st.toast(res["mensagem"], icon="✅" if res["sucesso"] else "⚠️")
                    if res["sucesso"]:
                        st.rerun()
            with b2:
                if st.button("✗ Não encontrei", key=f"vno_{oid}",
                             use_container_width=True, disabled=not modo_conectado):
                    res = dados.marcar_fonte(oid, "Verificação pendente")
                    st.toast(res["mensagem"], icon="✅" if res["sucesso"] else "⚠️")
                    if res["sucesso"]:
                        st.rerun()

    if len(nao) > len(mostrados):
        if st.button(f"▾ Mostrar mais ({len(nao) - len(mostrados)} restantes)",
                     key="verif_more", use_container_width=True):
            st.session_state["verif_n"] += 10
            st.rerun()

    _secao_fontes_sugeridas()


# =========================================================================== #
# ROTEAMENTO
# =========================================================================== #
ROTAS = {"Visão geral": page_visao, "Ranking": page_ranking, "Radar": page_radar,
         "Funil": page_funil, "Metodologia": page_metodo, "Verificação": page_verificacao}
ROTAS.get(PAGINA, page_visao)()

# --------------------------------------------------------------------------- #
# Rodapé
# --------------------------------------------------------------------------- #
modo_txt = ("Conectado ao Google Sheets (leitura e escrita ao vivo)" if modo_conectado
            else "Modo local (CSV) — somente leitura. Conecte o Google Sheets para sincronizar.")
st.markdown(
    f'<div class="hr-line" style="margin-top:28px"></div>'
    f'<div style="display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap;'
    f'font-size:11.5px;color:var(--dim)"><span>Dashboard de Inteligência de Captação · PFC · '
    f'logado como {esc(USER["nome"])}</span><span>{modo_txt}</span></div>',
    unsafe_allow_html=True,
)
