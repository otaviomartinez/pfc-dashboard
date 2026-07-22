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

/* ---------- aba Verificação (maquete: listra âmbar + confirmar/pular) ---------- */
.vbar{height:10px;border-radius:6px;background:var(--line-2);overflow:hidden;margin:8px 0 2px}
.vbar i{display:block;height:100%;border-radius:6px;background:linear-gradient(90deg,#E8873A,#4ADE80);transition:width .7s var(--ease)}
.vprog-lab{display:flex;align-items:baseline;justify-content:space-between;gap:10px}
.vprog-lab .big{font-weight:700;font-size:22px;color:var(--ink);letter-spacing:-.4px}
.vprog-lab .pct{font-family:var(--mono);font-weight:600;font-size:14px;color:var(--sem-high)}
.vhead{display:flex;align-items:center;gap:11px;min-width:0}
.vhead .nm{font-weight:600;font-size:14.5px;color:var(--ink)}
.vhead .st{font-family:var(--mono);font-size:11px;color:var(--sem-mid);letter-spacing:.3px;
  text-transform:uppercase;margin-top:3px}
.vcur{font-family:var(--mono);font-size:11px;color:var(--dim);word-break:break-all;margin-top:2px}
.vbadge2{font-family:var(--mono);font-size:10.5px;font-weight:600;letter-spacing:.5px;
  text-transform:uppercase;padding:4px 10px;border-radius:7px;border:1px solid transparent;white-space:nowrap}
.vb-nao{background:rgba(232,181,74,.1);color:var(--sem-mid);border-color:rgba(232,181,74,.3)}
.vb-pend{background:rgba(232,181,74,.1);color:var(--sem-mid);border-color:rgba(232,181,74,.3)}
/* card do item com listra âmbar de atenção (container com key vcard_*) */
[class*="st-key-vcard_"]{position:relative;overflow:hidden;
  background:var(--surface)!important;border:1px solid var(--line)!important;border-radius:14px!important}
[class*="st-key-vcard_"]::before{content:"";position:absolute;
  left:0;top:0;bottom:0;width:3px;background:var(--sem-mid);z-index:1}
/* botões: confirmar sólido verde, pular fantasma (maquete .vbtn) */
[class*="st-key-vok_"] button{background:var(--sem-high);color:#0A2417;border:none;
  font-weight:600;font-size:13px;border-radius:9px}
[class*="st-key-vok_"] button:hover{background:var(--sem-high);color:#0A2417;filter:brightness(1.1);transform:none}
[class*="st-key-vok_"] button:disabled{opacity:.4}
[class*="st-key-vno_"] button{background:none;border:1px solid var(--line2);color:var(--muted);
  font-weight:600;font-size:13px;border-radius:9px}
[class*="st-key-vno_"] button:hover{color:var(--ink);border-color:var(--line2);background:none;transform:none}

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
.st-key-seg_Monitorar button{--dot:#939BA5} .st-key-seg_Edital button{--dot:#E8873A}
.st-key-seg_Ativo button{--dot:#4ADE80}
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
    <circle cx="21" cy="21" r="18" fill="none" stroke="#5B9BD5" stroke-opacity=".55" stroke-width="1.4"/>
    <circle cx="21" cy="21" r="11.5" fill="none" stroke="#5B9BD5" stroke-opacity=".32" stroke-width="1.2"/>
    <circle cx="21" cy="3.2" r="2.2" fill="#5B9BD5"/><circle cx="38.4" cy="24" r="1.9" fill="#5B9BD5" fill-opacity=".8"/>
  </g>
  <g stroke="#4ADE80" stroke-width="1.7" stroke-linecap="round">
    <line x1="21" y1="13.5" x2="21" y2="28.5"/><line x1="13.5" y1="21" x2="28.5" y2="21"/>
    <line x1="15.7" y1="15.7" x2="26.3" y2="26.3"/><line x1="26.3" y1="15.7" x2="15.7" y2="26.3"/>
  </g>
  <circle cx="21" cy="21" r="2.6" fill="#4ADE80"/>
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


CORES_STATUS = {"Mapear": "#7C8698", "Prospectar": "#E8873A", "Monitorar": "#5B9BD5",
                "Edital": "#E8B54A", "Ativo": "#4ADE80"}


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
            marker=dict(color="#4ADE80", line=dict(color="rgba(255,255,255,.1)", width=1)),
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
# VISÃO GERAL · maquete pfc_app_v3 (Custom Component v2 bidirecional)
# ---------------------------------------------------------------------------
# Um único componente v2 renderiza a tela (herói + radar-scópio + glowcards +
# legenda + painéis). Cliques viajam ao Python via setTriggerValue('acao', …)
# e abrem dialogs/navegação reais. Montado no DOM (shadow root, sem iframe);
# as CSS vars do tema (:root) atravessam o shadow boundary por herança.
# =========================================================================== #
ATIVAS = ["Iperó", "Tatuí", "Salto", "São Roque", "Rio Claro", "Coronel Macedo", "Mirassol"]
PROXIMAS = ["Dois Córregos", "Corumbataí"]
EVENTOS = {"Iperó": "Feira de Ciências · ago/2026", "Tatuí": "Clube de Ciências · jul/2026",
           "Salto": "Mostra STEM · set/2026", "São Roque": "Maratona PFC · out/2026",
           "Rio Claro": "Olimpíada · ago/2026", "Coronel Macedo": "Visita técnica · jul/2026",
           "Mirassol": "Roda de mentoria · set/2026", "Dois Córregos": "Implantação · 2024",
           "Corumbataí": "Implantação · 2024"}

CORES_ETAPA = {"Mapear": "var(--sem-low,#7C8698)", "Prospectar": "var(--accent,#E8873A)",
               "Monitorar": "var(--sem-info,#5B9BD5)", "Edital": "var(--sem-mid,#E8B54A)",
               "Ativo": "var(--sem-high,#4ADE80)"}


def _n_fontes_radar() -> int:
    """Fontes monitoradas: âncoras do radar + genéricas ativas do config."""
    n = 31
    try:
        from radar.fontes_ancora import FONTES as _FA
        n = len(_FA)
    except Exception:
        pass
    try:
        with open(_CONFIG_FONTES, encoding="utf-8") as f:
            cfg = json.load(f)
        n += sum(1 for e in cfg if isinstance(e, dict) and e.get("ativo", True)
                 and str(e.get("url", "")).startswith("http")
                 and "exemplo.org" not in str(e.get("url", "")))
    except Exception:
        pass
    return n


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


@st.dialog("Detalhe da oportunidade", width="large")
def dlg_oportunidade(op: dict):
    breadcrumb("Visão geral", "Oportunidade")
    score = op.get("score")
    sc_html = (f'<span style="font-weight:800;font-size:30px;color:var(--accent);'
               f'font-variant-numeric:tabular-nums">{int(score)}</span>'
               if score is not None else "")
    meta = op.get("fonte", "")
    if op.get("prazo") and _prazo_confiavel(op.get("dias")):
        meta += f" · encerra {_fmt_prazo(op['prazo'])}"
    elif op.get("prazo"):
        meta += " · prazo a confirmar"
    st.markdown(
        f'<div style="display:flex;align-items:flex-start;gap:14px">{sc_html}'
        f'<div><div style="font-size:18px;font-weight:600;line-height:1.3">{esc(op.get("titulo"))}</div>'
        f'<div style="font-family:var(--mono);font-size:12px;color:var(--dim);margin-top:6px">{esc(meta)}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    linhas = []
    if score is not None:
        linhas.append(("Aderência ao PFC", f"{int(score)} / 100"))
    linhas.append(("Valor", op.get("valor") or "—"))
    dias = op.get("dias")
    prazo_v = _fmt_prazo(op.get("prazo", ""))
    if op.get("prazo") and not _prazo_confiavel(dias):
        prazo_v += ' <span style="color:var(--dim)">(a confirmar)</span>'
    linhas.append(("Prazo de inscrição", prazo_v))
    if _prazo_confiavel(dias):
        cor = "var(--sem-urgent)" if dias <= 7 else "var(--accent)"
        linhas.append(("Tempo restante",
                       f'<b style="color:{cor}">faltam {dias} dias</b>' if dias >= 0
                       else f'<b style="color:var(--sem-urgent)">vencida há {-dias} dias</b>'))
    elif str(op.get("prazo", "")).strip():
        # data possivelmente estimada (ano assumido) — não mostrar número
        linhas.append(("Tempo restante",
                       '<span style="color:var(--dim)">prazo a confirmar na página oficial</span>'))
    linhas.append(("Fonte", op.get("fonte") or "—"))
    corpo = "".join(
        f'<div style="margin-bottom:16px"><div style="font-family:var(--mono);font-size:11px;'
        f'letter-spacing:1px;text-transform:uppercase;color:var(--dim);margin-bottom:6px">{lab}</div>'
        f'<div style="font-size:15px;color:var(--ink)">{val}</div></div>'
        for lab, val in linhas)
    st.markdown(corpo, unsafe_allow_html=True)
    if op.get("desc"):
        st.markdown(f'<div style="font-size:13px;color:var(--muted);line-height:1.6;'
                    f'border-top:1px solid var(--line);padding-top:14px">{esc(op["desc"][:400])}</div>',
                    unsafe_allow_html=True)
    if str(op.get("link", "")).startswith("http"):
        st.link_button("↗ Abrir página oficial", op["link"], use_container_width=True)
    if op.get("nv") is not None:
        if not modo_conectado:
            st.caption(HINT_ESCRITA)
        b1, b2 = st.columns(2)
        with b1:
            if st.button("✓ Aprovar e mover à base", key="dlgop_ok", type="primary",
                         use_container_width=True, disabled=not modo_conectado):
                res = dados.aprovar_novidade(op["nv"])
                st.toast(res["mensagem"], icon="✅" if res["sucesso"] else "⚠️")
                st.rerun()
        with b2:
            if st.button("Descartar", key="dlgop_no", use_container_width=True,
                         disabled=not modo_conectado):
                res = dados.descartar_novidade(op["nv"])
                st.toast(res["mensagem"], icon="🗑️" if res["sucesso"] else "⚠️")
                st.rerun()


@st.dialog("Cobertura regional", width="large")
def dlg_cobertura():
    breadcrumb("Visão geral", "Cobertura")
    st.markdown(f"#### 🗺️ {len(ATIVAS)} municípios ativos · {len(PROXIMAS)} em implantação")
    st.caption("Clique num município para ver as organizações do território.")
    todas = [(c, True) for c in ATIVAS] + [(c, False) for c in PROXIMAS]
    cols = st.columns(3)
    for i, (cidade, ativa) in enumerate(todas):
        slug = re.sub(r"[^0-9A-Za-z]+", "_", cidade)
        with cols[i % 3]:
            if st.button(("📍 " if ativa else "🆕 ") + cidade, key=f"cid_{slug}",
                         use_container_width=True):
                st.session_state["abrir_cidade"] = (cidade, ativa)
                st.rerun()


# CSS do radar-scópio, compartilhado entre Visão Geral e Radar.
_SCOPE_V2_CSS = """
.scope-card{position:relative;background:var(--surface,#161A21);border:1px solid var(--line,rgba(255,255,255,.06));
  border-radius:16px;padding:26px 28px;display:flex;flex-direction:column;overflow:hidden}
.scope-card::before{content:"";position:absolute;inset:0;border-radius:16px;padding:1.5px;
  background:linear-gradient(145deg,var(--sem-info,#5B9BD5),transparent 55%);
  -webkit-mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);
  -webkit-mask-composite:xor;mask-composite:exclude;opacity:.4}
.sc-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;position:relative;z-index:1}
.scope-card h3{font-size:16px;font-weight:600;margin:0}
.sc-live{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--sem-high,#4ADE80);
  display:flex;align-items:center;gap:6px}
.sc-live .d{width:6px;height:6px;border-radius:50%;background:var(--sem-high,#4ADE80);
  box-shadow:0 0 8px var(--sem-high,#4ADE80)}
.sc-sub{font-family:'JetBrains Mono',monospace;font-size:10.5px;color:var(--dim,#6B7688);
  letter-spacing:.5px;margin-bottom:14px;position:relative;z-index:1}
.scopevis{flex:1;display:grid;place-items:center;min-height:0;position:relative;z-index:1}
.scopevis svg{width:100%;height:auto;max-height:300px}
.gr{stroke:rgba(255,255,255,.09);fill:none}
.swf{transform-origin:center;animation:sw 4s linear infinite}
.swl{transform-origin:center;animation:sw 4s linear infinite;stroke:var(--accent,#E8873A)}
@keyframes sw{to{transform:rotate(360deg)}}
.blip-hit{cursor:pointer}
.scope-foot{display:flex;justify-content:space-between;gap:12px;margin-top:18px;padding-top:18px;
  border-top:1px solid var(--line,rgba(255,255,255,.06));font-family:'JetBrains Mono',monospace;
  font-size:11.5px;color:var(--muted,#A4AEBF);position:relative;z-index:1}
.scope-foot b{font-weight:700}
"""

_VISAO_V2_CSS = """
.vw{display:flex;flex-direction:column;gap:22px;font-family:'Inter',system-ui,sans-serif;
  color:var(--ink,#F5F7FA);animation:vw-fade .4s ease}
@keyframes vw-fade{from{opacity:0;transform:translateY(10px)}}
.mono{font-family:'JetBrains Mono',monospace}
.tnum{font-variant-numeric:tabular-nums}

/* hero */
.hero{display:grid;grid-template-columns:1.1fr .9fr;gap:22px}
@media (max-width:1000px){.hero{grid-template-columns:1fr}}
.lead-card{position:relative;background:linear-gradient(150deg,var(--surface2,#1C222B),var(--surface,#161A21));
  border:1px solid var(--line,rgba(255,255,255,.06));border-radius:16px;padding:32px 34px;
  display:flex;flex-direction:column;justify-content:space-between;overflow:hidden}
.lead-card::before{content:"";position:absolute;inset:0;border-radius:16px;padding:1.5px;
  background:linear-gradient(145deg,var(--accent,#E8873A),transparent 50%);
  -webkit-mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);
  -webkit-mask-composite:xor;mask-composite:exclude;opacity:.6}
.lead-card::after{content:"";position:absolute;top:-40%;right:-10%;width:320px;height:320px;
  border-radius:50%;background:radial-gradient(circle,var(--accent-dim,rgba(232,135,58,.12)),transparent 70%)}
.hl-top{position:relative;z-index:1}
.hl-label{font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:1.2px;
  text-transform:uppercase;color:var(--muted,#A4AEBF);margin-bottom:14px}
.hl-num{font-size:80px;font-weight:800;letter-spacing:-4px;line-height:.9}
.hl-num .u{font-size:26px;font-weight:600;color:var(--muted,#A4AEBF);letter-spacing:-1px;margin-left:6px}
.hl-cap{font-size:15px;color:var(--muted,#A4AEBF);margin-top:10px}
.hl-headline{position:relative;z-index:1;margin-top:24px;padding-top:22px;
  border-top:1px solid var(--line,rgba(255,255,255,.06))}
.hh-lbl{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:1px;
  text-transform:uppercase;color:var(--dim,#6B7688);margin-bottom:10px}
.hh-row{display:flex;align-items:center;gap:14px;cursor:pointer}
.hh-sc{font-weight:800;font-size:26px;color:var(--accent,#E8873A);flex:none;font-variant-numeric:tabular-nums}
.hh-t{font-size:16px;font-weight:600;line-height:1.3}
.hh-m{font-size:12px;color:var(--dim,#6B7688);margin-top:4px}
.hh-dl{margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:12.5px;font-weight:600;
  color:var(--sem-urgent,#F0663F);background:rgba(240,102,63,.1);border:1px solid rgba(240,102,63,.3);
  padding:8px 12px;border-radius:8px;flex:none;white-space:nowrap}
.hh-dl.ok{color:var(--accent,#E8873A);background:var(--accent-dim,rgba(232,135,58,.12));
  border-color:rgba(232,135,58,.3)}

/* glowcards */
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}
@media (max-width:1000px){.kpis{grid-template-columns:1fr 1fr}}
.glowcard{position:relative;background:var(--surface,#161A21);border:1px solid var(--line,rgba(255,255,255,.06));
  border-radius:16px;padding:22px 24px;cursor:pointer;transition:.25s;overflow:hidden;--c:var(--accent,#E8873A)}
.glowcard::before{content:"";position:absolute;inset:0;border-radius:16px;padding:1.5px;
  background:linear-gradient(145deg,var(--c),transparent 55%);
  -webkit-mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);
  -webkit-mask-composite:xor;mask-composite:exclude;opacity:.55;transition:.25s}
.glowcard::after{content:"";position:absolute;top:-30%;right:-15%;width:140px;height:140px;
  border-radius:50%;background:radial-gradient(circle,var(--c),transparent 70%);opacity:.10;
  transition:.25s;pointer-events:none}
.glowcard:hover{transform:translateY(-4px)}
.glowcard:hover::before{opacity:1}
.glowcard:hover::after{opacity:.2}
.gc-ic{width:44px;height:44px;border-radius:12px;display:grid;place-items:center;margin-bottom:16px;
  position:relative;z-index:1;background:color-mix(in srgb,var(--c) 16%,transparent);
  border:1px solid color-mix(in srgb,var(--c) 30%,transparent)}
.gc-ic svg{width:22px;height:22px;fill:none;stroke:var(--c);stroke-width:1.9}
.gc-lab{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.8px;
  text-transform:uppercase;color:var(--muted,#A4AEBF);position:relative;z-index:1}
.gc-val{font-weight:800;font-size:40px;letter-spacing:-1.8px;margin-top:8px;line-height:1;
  position:relative;z-index:1;font-variant-numeric:tabular-nums}
.gc-val.small{font-size:29px;letter-spacing:-1px}
.gc-foot{font-size:13px;color:var(--dim,#6B7688);margin-top:10px;position:relative;z-index:1}
.gc-foot .up{color:var(--sem-high,#4ADE80);font-weight:600}

/* legenda */
.cmean{display:flex;gap:20px;flex-wrap:wrap;padding:14px 18px;background:var(--surface,#161A21);
  border:1px solid var(--line,rgba(255,255,255,.06));border-radius:12px;
  font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted,#A4AEBF)}
.cmean b{color:var(--dim,#6B7688);font-weight:500;margin-right:4px}
.cmean .m{display:flex;align-items:center;gap:7px}
.cmean .m i{width:9px;height:9px;border-radius:3px;display:inline-block}

/* painéis */
.detail{display:grid;grid-template-columns:1.4fr 1fr;gap:22px}
@media (max-width:1000px){.detail{grid-template-columns:1fr}}
.panel{position:relative;background:var(--surface,#161A21);border:1px solid var(--line,rgba(255,255,255,.06));
  border-radius:16px;padding:26px 28px}
.panel h3{font-size:16px;font-weight:600;margin:0 0 4px}
.panel .psub{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--dim,#6B7688);
  margin-bottom:22px;letter-spacing:.5px}
.fb{display:flex;align-items:center;gap:16px;margin-bottom:18px;cursor:pointer}
.fb:last-child{margin-bottom:0}
.fb:hover .n{color:var(--ink,#F5F7FA)}
.fb:hover .tk{outline:1px solid var(--line2,rgba(255,255,255,.12));outline-offset:2px}
.fb .n{font-size:14px;color:var(--muted,#A4AEBF);width:96px;flex:none;font-weight:500}
.fb .tk{flex:1;height:11px;background:rgba(255,255,255,.05);border-radius:6px;overflow:hidden}
.fb .fl{height:100%;border-radius:6px;width:0;transition:width 1.1s cubic-bezier(.16,1,.3,1)}
.fb .v{font-size:16px;font-weight:700;width:34px;text-align:right;flex:none;font-variant-numeric:tabular-nums}
.prazos .pr{display:flex;align-items:center;gap:14px;padding:14px 0;
  border-bottom:1px solid var(--line,rgba(255,255,255,.06));cursor:pointer}
.prazos .pr:first-of-type{padding-top:0}
.prazos .pr:last-child{border:none;padding-bottom:0}
.prazos .pr:hover{background:rgba(255,255,255,.03);border-radius:10px;padding-left:8px;margin:0 -8px}
.pr .days{font-weight:800;font-size:22px;width:44px;flex:none;text-align:center;font-variant-numeric:tabular-nums}
.pr .days.u{color:var(--sem-urgent,#F0663F)}
.pr .days.s{color:var(--accent,#E8873A)}
.pr .info{flex:1;min-width:0}
.pr .info .t{font-size:14px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pr .info .m{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--dim,#6B7688);margin-top:3px}
.pr-vazio{font-size:13px;color:var(--dim,#6B7688);padding:8px 0}
"""

_VISAO_V2_JS = r"""
export default function(component){
  const {data, parentElement, setTriggerValue} = component;
  const old = parentElement.querySelector('.vw'); if (old) old.remove();
  const d = data || {};
  const esc = s => String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  const sem = s => s >= 60 ? 'var(--sem-high,#4ADE80)' : s >= 50 ? 'var(--sem-mid,#E8B54A)'
    : 'var(--sem-low,#7C8698)';
  const ICONES = {
    org: '<path d="M3 21h18M5 21V7l8-4v18M19 21V11l-6-3"/>',
    pros: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    money: '<path d="M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
    globe: '<circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20"/>'
  };
  const root = document.createElement('div'); root.className = 'vw';

  // ---- hero: métrica-herói + mais aderente ----
  const h = d.hero || {};
  let topHtml = '';
  if (h.top) {
    const t = h.top;
    let dl = '';
    if (Number.isFinite(t.dias)) {
      dl = '<span class="hh-dl' + (t.dias <= 7 ? '' : ' ok') + '">' + t.dias + ' DIAS</span>';
    }
    topHtml = '<div class="hl-headline"><div class="hh-lbl">Mais aderente ao PFC agora</div>' +
      '<div class="hh-row" data-act="hero"><span class="hh-sc tnum">' + esc(t.score) + '</span>' +
      '<div style="min-width:0"><div class="hh-t">' + esc(t.titulo) + '</div>' +
      '<div class="mono hh-m">' + esc(t.meta) + '</div></div>' + dl + '</div></div>';
  }

  // ---- scope: blips por aderência ----
  let blips = '';
  (d.blips || []).forEach(function(b, i){
    const ang = i * 2.399963;                       // ângulo áureo: espalha sem colidir
    const r = 140 - Math.max(0, Math.min(100, b.score)) * 1.2;  // + score = + perto do centro
    const cx = (150 + r * Math.cos(ang)).toFixed(1);
    const cy = (150 + r * Math.sin(ang)).toFixed(1);
    const cor = sem(b.score);
    const raio = (4 + b.score / 25).toFixed(1);
    blips += '<circle cx="' + cx + '" cy="' + cy + '" r="' + raio + '" fill="' + cor +
      '" class="blip-hit" data-act="blip" data-i="' + i + '" style="filter:drop-shadow(0 0 6px ' +
      cor + ')"><title>' + esc(b.fonte) + ' · ' + esc(b.score) + '</title></circle>';
  });
  const f = d.foot || {};
  const scope =
    '<div class="scope-card"><div class="sc-head"><h3>Radar de oportunidades</h3>' +
    '<div class="sc-live"><span class="d"></span>ao vivo</div></div>' +
    '<div class="sc-sub">PROXIMIDADE DO CENTRO = MAIOR ADERÊNCIA · CLIQUE NUM PONTO</div>' +
    '<div class="scopevis"><svg viewBox="0 0 300 300">' +
    '<defs><radialGradient id="sfv"><stop offset="0" stop-color="rgba(232,135,58,.3)"/>' +
    '<stop offset="1" stop-color="rgba(232,135,58,0)"/></radialGradient></defs>' +
    '<circle class="gr" cx="150" cy="150" r="144"/><circle class="gr" cx="150" cy="150" r="98"/>' +
    '<circle class="gr" cx="150" cy="150" r="52"/>' +
    '<line class="gr" x1="150" y1="6" x2="150" y2="294"/><line class="gr" x1="6" y1="150" x2="294" y2="150"/>' +
    '<path class="swf" d="M150 150 L150 6 A144 144 0 0 1 252 48 Z" fill="url(#sfv)"/>' +
    '<line class="swl" x1="150" y1="150" x2="150" y2="6" stroke-width="2"/>' +
    '<circle cx="150" cy="150" r="4" fill="var(--accent,#E8873A)"/>' + blips + '</svg></div>' +
    '<div class="scope-foot"><span><b style="color:var(--accent,#E8873A)">' + (f.fila || 0) +
    '</b> na fila</span><span><b style="color:var(--sem-urgent,#F0663F)">' + (f.encerrando || 0) +
    '</b> encerrando</span><span><b>' + (f.fontes || 0) + '</b> fontes</span></div></div>';

  root.innerHTML =
    '<div class="hero"><div class="lead-card"><div class="hl-top">' +
    '<div class="hl-label">Oportunidades no radar hoje</div>' +
    '<div class="hl-num tnum"><span data-c="' + (h.num || 0) + '">0</span>' +
    '<span class="u">novas</span></div>' +
    '<div class="hl-cap">' + esc(h.cap || '') + '</div></div>' + topHtml + '</div>' +
    scope + '</div>';

  // ---- glowcards ----
  let kpis = '';
  (d.kpis || []).forEach(function(k){
    const val = (k.txt != null)
      ? '<div class="gc-val' + (String(k.txt).length > 6 ? ' small' : '') + '">' + esc(k.txt) + '</div>'
      : '<div class="gc-val tnum" data-c="' + k.val + '">0</div>';
    kpis += '<div class="glowcard" style="--c:' + k.c + '" data-act="kpi" data-k="' + k.k + '">' +
      '<div class="gc-ic"><svg viewBox="0 0 24 24">' + (ICONES[k.icon] || '') + '</svg></div>' +
      '<div class="gc-lab">' + esc(k.lab) + '</div>' + val +
      '<div class="gc-foot">' + k.foot + '</div></div>';
  });
  root.insertAdjacentHTML('beforeend', '<div class="kpis">' + kpis + '</div>');

  // ---- legenda ----
  root.insertAdjacentHTML('beforeend',
    '<div class="cmean"><b>Cor = aderência:</b>' +
    '<span class="m"><i style="background:var(--sem-high,#4ADE80)"></i>Alta (60+)</span>' +
    '<span class="m"><i style="background:var(--sem-mid,#E8B54A)"></i>Média (50–59)</span>' +
    '<span class="m"><i style="background:var(--sem-low,#7C8698)"></i>Baixa (&lt;50)</span>' +
    '<span class="m"><i style="background:var(--sem-urgent,#F0663F)"></i>Prazo urgente</span></div>');

  // ---- painéis: pipeline + prazos ----
  let fbs = '';
  (d.stages || []).forEach(function(s){
    fbs += '<div class="fb" data-act="stage" data-k="' + esc(s.nome) + '">' +
      '<span class="n">' + esc(s.nome) + '</span>' +
      '<span class="tk"><span class="fl" data-w="' + s.pct + '" style="background:' + s.cor +
      '"></span></span><span class="v tnum">' + s.n + '</span></div>';
  });
  let prs = '';
  (d.prazos || []).forEach(function(p, i){
    prs += '<div class="pr" data-act="prazo" data-i="' + i + '">' +
      '<span class="days ' + (p.dias <= 7 ? 'u' : 's') + '">' + p.dias + '</span>' +
      '<div class="info"><div class="t">' + esc(p.titulo) + '</div>' +
      '<div class="m">' + esc(p.meta) + '</div></div></div>';
  });
  if (!prs) { prs = '<div class="pr-vazio">Nenhum edital com data-limite próxima. ✨</div>'; }
  root.insertAdjacentHTML('beforeend',
    '<div class="detail"><div class="panel"><h3>Pipeline por etapa</h3>' +
    '<div class="psub">' + (d.total_orgs || 0) + ' ORGANIZAÇÕES · CLIQUE PARA VER A ETAPA</div>' +
    fbs + '</div>' +
    '<div class="panel prazos"><h3>Prazos próximos</h3>' +
    '<div class="psub">EDITAIS QUE ESTÃO PARA ENCERRAR</div>' + prs + '</div></div>');

  parentElement.appendChild(root);

  // ---- cliques -> Python ----
  root.addEventListener('click', function(e){
    const el = e.target.closest('[data-act]');
    if (!el) { return; }
    setTriggerValue('acao', {t: el.dataset.act, k: el.dataset.k || null,
                             i: el.dataset.i != null ? +el.dataset.i : null, n: Date.now()});
  });

  // ---- animações: count-up + barras (setInterval/setTimeout — o rAF não
  // dispara no runtime do módulo v2, como na própria maquete) ----
  root.querySelectorAll('[data-c]').forEach(function(el){
    const alvo = +el.dataset.c; const t0 = Date.now(), dur = 900;
    const iv = setInterval(function(){
      const p = Math.min(1, (Date.now() - t0) / dur);
      el.textContent = String(Math.round(alvo * (1 - Math.pow(1 - p, 3))));
      if (p >= 1) { clearInterval(iv); }
    }, 16);
  });
  setTimeout(function(){
    root.querySelectorAll('.fl').forEach(function(fl, i){
      fl.style.transitionDelay = (i * 90) + 'ms';
      fl.style.width = fl.dataset.w + '%';
    });
  }, 60);
  return function(){ root.remove(); };
}
"""

_visao_v2 = components_v2.component("pfc_visao", css=_SCOPE_V2_CSS + _VISAO_V2_CSS,
                                    js=_VISAO_V2_JS)


# =========================================================================== #
# PÁGINA · VISÃO GERAL
# =========================================================================== #
def page_visao():
    # cidade escolhida dentro do dlg_cobertura abre na rerun seguinte
    pend = st.session_state.pop("abrir_cidade", None)
    if pend:
        dlg_cidade(pend[0], ativa=pend[1], evento=EVENTOS.get(pend[0], "A definir"))

    cont = df[COL_STATUS].value_counts() if TOTAL else pd.Series(dtype=int)
    n_prospectar = int(cont.get("Prospectar", 0))
    valor_total = float(df[COL_VALVO].sum()) if TOTAL else 0.0
    n_verif = int(df[COL_VERIF].apply(verificada_ok).sum()) if TOTAL else 0
    pct_pros = round(n_prospectar / TOTAL * 100) if TOTAL else 0

    # fila real do radar (Sheets), ordenada por aderência
    fila = sorted(dados.carregar_novidades_pendentes(), key=_score_novidade, reverse=True)
    ops = [_op_de_novidade(nv) for nv in fila]
    n_fontes = _n_fontes_radar()
    encerrando = sum(1 for o in ops if isinstance(o["dias"], int) and 0 <= o["dias"] <= 7)

    blip_items = ops[:12]
    top = ops[0] if ops else None

    # prazos próximos: novidades com prazo CONFIÁVEL + editais da base (45 dias)
    prazo_items, vistos = [], set()
    for o in ops:
        if _prazo_confiavel(o["dias"]) and o["dias"] >= 0:
            prazo_items.append(o)
            vistos.add(o["titulo"].lower())
    for e in _editais_proximos(45):
        if str(e["nome"]).lower() in vistos:
            continue
        prazo_items.append({"titulo": str(e["nome"]), "fonte": "Base PFC", "score": None,
                            "valor": brl_curto(e.get("valor")), "prazo": e["data"].isoformat(),
                            "dias": e["dias"], "link": str(e.get("link", "")), "desc": "", "nv": None})
    prazo_items.sort(key=lambda o: o["dias"])
    prazo_items = prazo_items[:4]

    def _meta(o):
        m = str(o["fonte"]).upper()
        if o.get("prazo") and _prazo_confiavel(o.get("dias")):
            m += f" · encerra {_fmt_prazo(o['prazo'])}"
        elif o.get("prazo"):
            m += " · prazo a confirmar"
        return m

    payload = {
        "hero": {"num": len(ops),
                 "cap": f"de {n_fontes} fontes monitoradas · aguardando revisão",
                 "top": ({"titulo": top["titulo"], "score": top["score"],
                          "dias": (top["dias"] if _prazo_confiavel(top["dias"])
                                   and top["dias"] >= 0 else None),
                          "meta": _meta(top)} if top else None)},
        "blips": [{"score": o["score"], "fonte": o["fonte"]} for o in blip_items],
        "foot": {"fila": len(ops), "encerrando": encerrando, "fontes": n_fontes},
        "kpis": [
            {"k": "rk", "c": "var(--sem-info,#5B9BD5)", "icon": "org", "lab": "Organizações",
             "val": TOTAL, "txt": None,
             "foot": f"<span class='up'>{n_verif}</span> fontes verificadas"},
            {"k": "fn", "c": "var(--accent,#E8873A)", "icon": "pros", "lab": "Em prospecção",
             "val": n_prospectar, "txt": None, "foot": f"{pct_pros}% do pipeline"},
            {"k": "valor", "c": "var(--sem-high,#4ADE80)", "icon": "money", "lab": "Valor-alvo",
             "val": None, "txt": brl_curto(valor_total), "foot": "potencial estimado"},
            {"k": "cobertura", "c": "var(--sem-mid,#E8B54A)", "icon": "globe", "lab": "Cobertura",
             "val": len(ATIVAS) + len(PROXIMAS), "txt": None, "foot": "municípios · SP"},
        ],
        "total_orgs": TOTAL,
        "stages": [{"nome": s, "n": int(cont.get(s, 0)),
                    "pct": round(int(cont.get(s, 0)) / TOTAL * 100, 1) if TOTAL else 0,
                    "cor": CORES_ETAPA[s]} for s in STATUS_FUNIL],
        "prazos": [{"titulo": o["titulo"], "dias": o["dias"], "meta": _meta(o)}
                   for o in prazo_items],
    }

    res = _visao_v2(data=payload, key="visao_v2", on_acao_change=lambda: None)
    ac = getattr(res, "acao", None)
    if isinstance(ac, dict):
        t, k, i = ac.get("t"), ac.get("k"), ac.get("i")
        if t == "kpi":
            if k == "rk":
                ir_para("Ranking")
                st.rerun()
            elif k == "fn":
                ir_para("Funil")
                st.rerun()
            elif k == "valor":
                dlg_valor_top10()
            elif k == "cobertura":
                dlg_cobertura()
        elif t == "hero" and top:
            dlg_oportunidade(top)
        elif t == "blip" and isinstance(i, int) and 0 <= i < len(blip_items):
            dlg_oportunidade(blip_items[i])
        elif t == "prazo" and isinstance(i, int) and 0 <= i < len(prazo_items):
            dlg_oportunidade(prazo_items[i])
        elif t == "stage" and k in STATUS_FUNIL:
            dlg_status_list(k)


# =========================================================================== #
# PÁGINA · RANKING (maquete: tabela com ponto por score; linha abre o dossiê)
# =========================================================================== #
_RANKING_V2_CSS = """
.rk{font-family:'Inter',system-ui,sans-serif;color:var(--ink,#F5F7FA);animation:rk-fade .4s ease}
@keyframes rk-fade{from{opacity:0;transform:translateY(10px)}}
.tbl{background:var(--surface,#161A21);border:1px solid var(--line,rgba(255,255,255,.06));
  border-radius:16px;overflow:hidden}
.tr{display:grid;grid-template-columns:2.4fr 1fr 1.1fr 1fr auto;gap:16px;align-items:center;
  padding:16px 24px;border-bottom:1px solid var(--line,rgba(255,255,255,.06));cursor:pointer;transition:.15s}
.tr:last-child{border-bottom:none}
.tr:hover{background:var(--hover,#222834)}
.tr.head{cursor:default;font-family:'JetBrains Mono',monospace;font-size:10.5px;letter-spacing:1px;
  text-transform:uppercase;color:var(--dim,#6B7688)}
.tr.head:hover{background:none}
.org{display:flex;align-items:center;gap:13px;min-width:0}
.org .sd{width:9px;height:9px;border-radius:50%;flex:none}
.org .nm{font-weight:600;font-size:14.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.org .sub{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--dim,#6B7688);
  margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.score{font-weight:800;font-size:19px;font-variant-numeric:tabular-nums}
.pill{font-size:12px;font-weight:600;padding:5px 12px;border-radius:20px;width:fit-content;white-space:nowrap}
.val{font-weight:600;font-variant-numeric:tabular-nums;font-size:13.5px}
.rarrow{color:var(--dim,#6B7688);transition:.2s}
.tr:hover .rarrow{color:var(--accent,#E8873A);transform:translateX(3px)}
.rk-foot{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--dim,#6B7688);
  padding:12px 24px;border-top:1px solid var(--line,rgba(255,255,255,.06))}
.rk-vazio{padding:26px 24px;text-align:center;color:var(--muted,#A4AEBF);font-size:14px}
"""

_RANKING_V2_JS = r"""
export default function(component){
  const {data, parentElement, setTriggerValue} = component;
  const old = parentElement.querySelector('.rk'); if (old) old.remove();
  const d = data || {}, rows = d.rows || [];
  const esc = s => String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  // limiares de Score PFC de organização (mesmos dos chips/kanban do app)
  const sem = s => s >= 85 ? 'var(--sem-high,#4ADE80)' : s >= 70 ? 'var(--sem-mid,#E8B54A)'
    : 'var(--sem-low,#7C8698)';
  const root = document.createElement('div'); root.className = 'rk';
  let html = '<div class="tbl"><div class="tr head"><div>Organização</div><div>Score PFC</div>' +
    '<div>Status</div><div>Valor-alvo</div><div></div></div>';
  rows.forEach(function(o, i){
    const c = sem(o.score);
    html += '<div class="tr" data-i="' + i + '">' +
      '<div class="org"><span class="sd" style="background:' + c + ';box-shadow:0 0 8px ' + c + '"></span>' +
      '<div style="min-width:0"><div class="nm">' + esc(o.nome) + '</div>' +
      '<div class="sub">' + esc(String(o.setor).toUpperCase()) + '</div></div></div>' +
      '<div class="score" style="color:' + c + '">' + esc(o.score) + '</div>' +
      '<div><span class="pill" style="background:' + o.cor_status + '22;color:' + o.cor_status + '">' +
      esc(o.status) + '</span></div>' +
      '<div class="val">' + esc(o.valor) + '</div><div class="rarrow">→</div></div>';
  });
  if (!rows.length) {
    html += '<div class="rk-vazio">Nenhuma organização encontrada — ajuste a busca ou o filtro.</div>';
  }
  if (d.restantes > 0) {
    html += '<div class="rk-foot">+ ' + d.restantes + ' organizações · refine a busca para ver mais</div>';
  }
  html += '</div>';
  root.innerHTML = html;
  parentElement.appendChild(root);
  root.addEventListener('click', function(e){
    const el = e.target.closest('.tr[data-i]');
    if (!el) { return; }
    setTriggerValue('acao', {i: +el.dataset.i, n: Date.now()});
  });
  return function(){ root.remove(); };
}
"""

_ranking_v2 = components_v2.component("pfc_ranking", css=_RANKING_V2_CSS, js=_RANKING_V2_JS)


def page_ranking():
    st.markdown(
        '<div class="phead"><h1>Ranking de captação</h1>'
        '<p>ordenado por Score PFC · busca e filtro ao vivo · clique na linha para abrir o dossiê</p></div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([3, 1.6, 1])
    with c1:
        busca = st.text_input("Buscar", key="rk_busca",
                              placeholder="Buscar organização ou setor…",
                              label_visibility="collapsed")
    with c2:
        filtro_status = st.selectbox("Status", ["Todos"] + STATUS_FUNIL, key="rk_status",
                                     label_visibility="collapsed")
    with c3:
        if st.button("🔄 Atualizar", key="rk_refresh", use_container_width=True,
                     help="Recarrega os dados (limpa o cache de 60s)"):
            dados.limpar_caches()
            st.rerun()

    rank = df.sort_values(COL_SCORE, ascending=False).copy() if TOTAL else df.copy()
    if busca and busca.strip() and TOTAL:
        q = busca.strip().lower()
        rank = rank[rank[COL_EMPRESA].str.lower().str.contains(q, na=False)
                    | rank[COL_SETOR].str.lower().str.contains(q, na=False)]
    if filtro_status != "Todos":
        rank = rank[rank[COL_STATUS] == filtro_status]

    top = rank.head(30)
    rows = [{"nome": str(r[COL_EMPRESA]), "setor": texto_ou(r[COL_SETOR]),
             "score": int(r[COL_SCORE]), "status": str(r[COL_STATUS]).strip() or "—",
             "cor_status": CORES_STATUS.get(str(r[COL_STATUS]).strip(), "#7C8698"),
             "valor": brl_curto(r[COL_VALVO])}
            for _, r in top.iterrows()]

    res = _ranking_v2(data={"rows": rows, "restantes": max(0, len(rank) - len(top))},
                      key="ranking_v2", on_acao_change=lambda: None)
    ac = getattr(res, "acao", None)
    if isinstance(ac, dict) and isinstance(ac.get("i"), int) and 0 <= ac["i"] < len(top):
        mostrar_dossie(top.iloc[ac["i"]].to_dict())


# =========================================================================== #
# PÁGINA · RADAR (maquete pfc_app_v3: scópio à esquerda + fila à direita)
# =========================================================================== #
def _score_novidade(nv) -> float:
    try:
        return float(str(nv.get("Score Aderência", "")).replace(",", ".") or 0)
    except (TypeError, ValueError):
        return 0.0


_RADAR_V2_CSS = """
.rv{font-family:'Inter',system-ui,sans-serif;color:var(--ink,#F5F7FA);animation:rv-fade .4s ease}
@keyframes rv-fade{from{opacity:0;transform:translateY(10px)}}
.radar-layout{display:grid;grid-template-columns:1fr 1fr;gap:22px;align-items:start}
@media (max-width:1000px){.radar-layout{grid-template-columns:1fr}}
.rlist{display:flex;flex-direction:column;gap:12px}
.ritem{position:relative;background:var(--surface,#161A21);border:1px solid var(--line,rgba(255,255,255,.06));
  border-radius:14px;padding:18px 20px;display:flex;gap:16px;align-items:center;cursor:pointer;
  transition:.2s;overflow:hidden;--c:var(--sem-mid,#E8B54A)}
.ritem::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--c)}
.ritem:hover{border-color:var(--line2,rgba(255,255,255,.12));transform:translateX(3px)}
.ritem .rsc{font-weight:800;font-size:24px;width:46px;text-align:center;flex:none;
  font-variant-numeric:tabular-nums;color:var(--c)}
.ritem .rb{flex:1;min-width:0}
.ritem .rtop{display:flex;align-items:center;gap:10px;margin-bottom:4px;min-width:0}
.ritem .src{font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:600;letter-spacing:.8px;
  color:var(--sem-info,#5B9BD5);background:rgba(91,155,213,.1);padding:4px 9px;border-radius:5px;
  flex:none;white-space:nowrap}
.ritem .rt{font-size:14.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ritem .rm{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--dim,#6B7688);margin-top:3px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ritem .rdl{font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:600;flex:none;
  text-align:right;white-space:nowrap}
.ritem .rdl.u{color:var(--sem-urgent,#F0663F)}
.ritem .rdl.s{color:var(--accent,#E8873A)}
.ritem .rdl.n{color:var(--dim,#6B7688)}
.rv-vazio{background:var(--surface,#161A21);border:1px solid var(--line,rgba(255,255,255,.06));
  border-radius:14px;padding:28px 20px;text-align:center;color:var(--muted,#A4AEBF);font-size:14px}
.rv-vazio .ic{font-size:26px;margin-bottom:8px}
.rv-mais{font-family:'JetBrains Mono',monospace;font-size:11.5px;color:var(--dim,#6B7688);
  text-align:center;padding:10px;border:1px dashed var(--line2,rgba(255,255,255,.12));border-radius:10px}
"""

_RADAR_V2_JS = r"""
export default function(component){
  const {data, parentElement, setTriggerValue} = component;
  const old = parentElement.querySelector('.rv'); if (old) old.remove();
  const d = data || {}, itens = d.itens || [];
  const esc = s => String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  const sem = s => s >= 60 ? 'var(--sem-high,#4ADE80)' : s >= 50 ? 'var(--sem-mid,#E8B54A)'
    : 'var(--sem-low,#7C8698)';
  const root = document.createElement('div'); root.className = 'rv';

  // ---- scópio (mesma geometria da Visão Geral) ----
  let blips = '';
  itens.slice(0, d.max_blips || 14).forEach(function(o, i){
    const ang = i * 2.399963;
    const r = 140 - Math.max(0, Math.min(100, o.score)) * 1.2;
    const cx = (150 + r * Math.cos(ang)).toFixed(1);
    const cy = (150 + r * Math.sin(ang)).toFixed(1);
    const cor = sem(o.score);
    const raio = (4 + o.score / 25).toFixed(1);
    blips += '<circle cx="' + cx + '" cy="' + cy + '" r="' + raio + '" fill="' + cor +
      '" class="blip-hit" data-act="op" data-i="' + i + '" style="filter:drop-shadow(0 0 6px ' +
      cor + ')"><title>' + esc(o.fonte) + ' · ' + esc(o.score) + '</title></circle>';
  });
  const f = d.foot || {};
  const scope =
    '<div class="scope-card"><div class="sc-head"><h3>Radar de oportunidades</h3>' +
    '<div class="sc-live"><span class="d"></span>ao vivo</div></div>' +
    '<div class="sc-sub">PROXIMIDADE DO CENTRO = MAIOR ADERÊNCIA · CLIQUE NUM PONTO</div>' +
    '<div class="scopevis"><svg viewBox="0 0 300 300">' +
    '<defs><radialGradient id="sfr"><stop offset="0" stop-color="rgba(232,135,58,.3)"/>' +
    '<stop offset="1" stop-color="rgba(232,135,58,0)"/></radialGradient></defs>' +
    '<circle class="gr" cx="150" cy="150" r="144"/><circle class="gr" cx="150" cy="150" r="98"/>' +
    '<circle class="gr" cx="150" cy="150" r="52"/>' +
    '<line class="gr" x1="150" y1="6" x2="150" y2="294"/><line class="gr" x1="6" y1="150" x2="294" y2="150"/>' +
    '<path class="swf" d="M150 150 L150 6 A144 144 0 0 1 252 48 Z" fill="url(#sfr)"/>' +
    '<line class="swl" x1="150" y1="150" x2="150" y2="6" stroke-width="2"/>' +
    '<circle cx="150" cy="150" r="4" fill="var(--accent,#E8873A)"/>' + blips + '</svg></div>' +
    '<div class="scope-foot"><span><b style="color:var(--accent,#E8873A)">' + (f.fila || 0) +
    '</b> na fila</span><span><b style="color:var(--sem-urgent,#F0663F)">' + (f.encerrando || 0) +
    '</b> encerrando</span><span><b>' + (f.fontes || 0) + '</b> fontes</span></div></div>';

  // ---- fila (lista à direita) ----
  let lista = '';
  itens.forEach(function(o, i){
    lista += '<div class="ritem" style="--c:' + sem(o.score) + '" data-act="op" data-i="' + i + '">' +
      '<div class="rsc">' + esc(o.score) + '</div>' +
      '<div class="rb"><div class="rtop"><span class="src">' + esc(o.fonte).toUpperCase() +
      '</span><span class="rt">' + esc(o.titulo) + '</span></div>' +
      '<div class="rm">' + esc(o.meta) + '</div></div>' +
      '<div class="rdl ' + o.badge_cls + '"' +
      (o.badge_tip ? ' title="' + esc(o.badge_tip) + '"' : '') + '>' + esc(o.badge_txt) + '</div></div>';
  });
  if (d.ocultos > 0) {
    lista += '<div class="rv-mais">+ ' + d.ocultos + ' na fila · aprove ou descarte para ver as próximas</div>';
  }
  if (!itens.length) {
    lista = '<div class="rv-vazio"><div class="ic">🛰️</div>' +
      '<div><b>Nenhuma oportunidade nova no momento</b></div>' +
      '<div style="font-size:12.5px;color:var(--dim,#6B7688);margin-top:6px">O radar roda todo dia às 06:00 ' +
      'e coloca aqui os editais que passam no filtro.</div></div>';
  }

  root.innerHTML = '<div class="radar-layout">' + scope +
    '<div class="rlist">' + lista + '</div></div>';
  parentElement.appendChild(root);

  root.addEventListener('click', function(e){
    const el = e.target.closest('[data-act]');
    if (!el) { return; }
    setTriggerValue('acao', {t: el.dataset.act, i: +el.dataset.i, n: Date.now()});
  });
  return function(){ root.remove(); };
}
"""

_radar_v2 = components_v2.component("pfc_radar", css=_SCOPE_V2_CSS + _RADAR_V2_CSS,
                                    js=_RADAR_V2_JS)

_RADAR_MAX_LISTA = 30  # itens visíveis na fila (o restante fica indicado no rodapé)


def page_radar():
    _mostrar_resultado(st.session_state.pop("radar_msg", None))
    if not modo_conectado:
        st.caption(HINT_ESCRITA + " — aprovar/descartar grava na aba Novidades_pendentes.")

    fila = sorted(dados.carregar_novidades_pendentes(), key=_score_novidade, reverse=True)
    ops = [_op_de_novidade(nv) for nv in fila]
    visiveis = ops[:_RADAR_MAX_LISTA]
    n_fontes = _n_fontes_radar()
    encerrando = sum(1 for o in ops if _prazo_confiavel(o["dias"]) and 0 <= o["dias"] <= 7)

    def _badge(o):
        """'X DIAS' só com data confiável; estimada vira 'prazo a confirmar'."""
        dias, tem_prazo = o["dias"], bool(str(o["prazo"]).strip())
        if _prazo_confiavel(dias):
            if dias < 0:
                return "VENCIDA", "u", f"prazo encerrou há {-dias} dia(s)"
            return f"{dias} DIAS", ("u" if dias <= 7 else "s"), ""
        if tem_prazo:
            return "PRAZO A CONFIRMAR", "n", "data possivelmente estimada — confira na página oficial"
        return "SEM PRAZO", "n", ""

    def _meta_radar(o):
        partes = []
        if o["valor"]:
            partes.append(f"valor: {o['valor']}")
        if _prazo_confiavel(o["dias"]) and o["dias"] >= 0:
            partes.append(f"encerra {_fmt_prazo(o['prazo'])}")
        return " · ".join(partes) or "sem valor informado"

    itens = []
    for o in visiveis:
        txt, cls, tip = _badge(o)
        itens.append({"score": o["score"], "fonte": o["fonte"], "titulo": o["titulo"],
                      "meta": _meta_radar(o), "badge_txt": txt, "badge_cls": cls,
                      "badge_tip": tip})

    res = _radar_v2(data={"itens": itens, "ocultos": max(0, len(ops) - len(visiveis)),
                          "max_blips": 14,
                          "foot": {"fila": len(ops), "encerrando": encerrando,
                                   "fontes": n_fontes}},
                    key="radar_v2", on_acao_change=lambda: None)
    ac = getattr(res, "acao", None)
    if isinstance(ac, dict) and ac.get("t") == "op":
        i = ac.get("i")
        if isinstance(i, int) and 0 <= i < len(visiveis):
            dlg_oportunidade(visiveis[i])


# =========================================================================== #
# PÁGINA · FUNIL
# =========================================================================== #
# Cores das colunas do kanban (paleta da maquete pfc_app_v3).
ACENTOS_HEX = {"Mapear": "#7C8698", "Prospectar": "#E8873A", "Monitorar": "#5B9BD5",
               "Edital": "#E8B54A", "Ativo": "#4ADE80"}


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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:transparent;font-family:'Inter',system-ui,sans-serif;color:#E9EBEE}
.wrap{background:rgba(20,24,32,.6);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.06);border-radius:14px;overflow:hidden;box-shadow:0 1px 2px rgba(0,0,0,.16),inset 0 0 0 1px rgba(255,255,255,.02)}
.h{padding:18px 20px 13px;border-bottom:1px solid rgba(255,255,255,.06)}
.h h2{font-family:'Inter';font-weight:600;font-size:15.5px;margin:0}
.h .cap{font-size:12px;color:#565E68;margin-top:3px}
.body{padding:14px 18px 18px}
.orbit-wrap{display:grid;place-items:center}
#arc{transition:stroke .35s ease;cursor:default}
.cn{font-family:'Inter';font-weight:600;transition:fill .35s ease}
.chips{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:14px}
.chip{display:inline-flex;align-items:center;gap:7px;padding:7px 12px;border:1px solid rgba(255,255,255,.07);border-radius:999px;cursor:pointer;font-size:12.5px;color:#C2C7CE;background:rgba(255,255,255,.015);transition:background .22s ease,border-color .22s ease,transform .15s ease,color .22s ease}
.chip:hover{background:rgba(255,255,255,.05);border-color:rgba(255,255,255,.16);transform:translateY(-2px);color:#fff}
.chip.sel{background:rgba(255,255,255,.08);border-color:rgba(255,255,255,.24);color:#fff}
.chip .dot{width:8px;height:8px;border-radius:50%;flex:none}
.chip b{font-family:'Inter';font-weight:600}
.hint{font-size:11px;color:#565E68;text-align:center;margin-top:11px}
</style></head><body>
<div class="wrap"><div class="h"><h2>Anatomia do Score</h2><div class="cap" id="cap">__NOME__</div></div>
<div class="body">
<div class="orbit-wrap"><svg id="svg" width="206" height="206" viewBox="0 0 200 200" aria-label="Score">
  <defs><linearGradient id="grad" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#E8873A"/><stop offset="1" stop-color="#4ADE80"/></linearGradient></defs>
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
# Painel de pesos do score no estilo da maquete (barras animadas .fb/.fl).
_PESOS_V2_CSS = """
.mp{font-family:'Inter',system-ui,sans-serif;color:var(--ink,#F5F7FA);animation:mp-fade .4s ease}
@keyframes mp-fade{from{opacity:0;transform:translateY(10px)}}
.panel{background:var(--surface,#161A21);border:1px solid var(--line,rgba(255,255,255,.06));
  border-radius:16px;padding:26px 28px}
.panel h3{font-size:16px;font-weight:600;margin:0 0 4px}
.psub{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--dim,#6B7688);
  margin-bottom:22px;letter-spacing:.5px}
.fb{display:flex;align-items:center;gap:16px;margin-bottom:18px}
.fb:last-child{margin-bottom:0}
.fb .n{font-size:14px;color:var(--muted,#A4AEBF);width:130px;flex:none;font-weight:500}
.fb .tk{flex:1;height:11px;background:rgba(255,255,255,.05);border-radius:6px;overflow:hidden}
.fb .fl{height:100%;border-radius:6px;width:0;transition:width 1.1s cubic-bezier(.16,1,.3,1)}
.fb .v{font-size:16px;font-weight:700;width:44px;text-align:right;flex:none;font-variant-numeric:tabular-nums}
"""

_PESOS_V2_JS = r"""
export default function(component){
  const {data, parentElement} = component;
  const old = parentElement.querySelector('.mp'); if (old) old.remove();
  const d = data || {};
  const esc = s => String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  const root = document.createElement('div'); root.className = 'mp';
  let fbs = '';
  (d.rows || []).forEach(function(r){
    fbs += '<div class="fb"><span class="n">' + esc(r.n) + '</span>' +
      '<span class="tk"><span class="fl" data-w="' + r.w + '" style="background:' + r.cor +
      '"></span></span><span class="v">' + r.w + '%</span></div>';
  });
  root.innerHTML = '<div class="panel"><h3>' + esc(d.titulo || '') + '</h3>' +
    '<div class="psub">' + esc(d.sub || '') + '</div>' + fbs + '</div>';
  parentElement.appendChild(root);
  setTimeout(function(){
    root.querySelectorAll('.fl').forEach(function(fl, i){
      fl.style.transitionDelay = (i * 90) + 'ms';
      fl.style.width = fl.dataset.w + '%';
    });
  }, 60);
  return function(){ root.remove(); };
}
"""

_pesos_v2 = components_v2.component("pfc_pesos", css=_PESOS_V2_CSS, js=_PESOS_V2_JS)


def page_metodo():
    st.markdown(
        '<div class="phead"><h1>Como o Score PFC é calculado</h1>'
        '<p>quatro componentes, pesos fixos, origem rastreável — explore cada um</p></div>',
        unsafe_allow_html=True,
    )
    componentes = [
        ("🎯 Aderência ao DNA", 35, "var(--orange)", "#E8873A",
         "Mede o quanto a causa da organização conversa com o DNA do PFC: ciência, STEM, "
         "educação pública, permanência escolar e projeto de vida. É o maior peso porque "
         "sem aderência de missão a parceria não se sustenta, por mais dinheiro que exista.",
         "Ex.: uma fundação que financia Clubes de Ciência e feiras científicas = aderência altíssima."),
        ("💰 Capacidade & fit de valor", 25, "var(--green)", "#4ADE80",
         "Avalia a capacidade financeira do parceiro e se o ticket típico dele cabe no que o "
         "PFC precisa captar. Premia organizações com histórico de investimento social e faixa "
         "de valor compatível com os projetos do programa.",
         "Ex.: instituto com editais de R$ 100–300 mil casa melhor que um patrocínio pontual de R$ 5 mil."),
        ("🗺️ Proximidade regional", 20, "var(--blue)", "#5B9BD5",
         "Pondera a presença do parceiro nos municípios onde o PFC atua (Iperó, Tatuí, Salto, "
         "Sorocaba e região). Proximidade geográfica reduz atrito logístico e aumenta a chance "
         "de visitas, eventos e engajamento local.",
         "Ex.: empresa com unidade em Sorocaba pontua mais que uma sediada fora do estado."),
        ("⚡ Acionabilidade", 20, "var(--muted)", "#7C8698",
         "Mede o quão fácil é agir AGORA: existe canal de contato claro, edital aberto, "
         "porta de entrada conhecida? Premia oportunidades destravadas e penaliza as que "
         "exigem meses de prospecção fria.",
         "Ex.: edital com inscrições abertas e contato do ESG mapeado = acionabilidade alta."),
    ]
    _pesos_v2(data={"titulo": "Pesos do algoritmo",
                    "sub": "SCORE = 0,35·ADERÊNCIA + 0,25·VALOR + 0,20·REGIÃO + 0,20·AÇÃO",
                    "rows": [{"n": "Aderência", "w": 35, "cor": "#E8873A"},
                             {"n": "Valor", "w": 25, "cor": "#5B9BD5"},
                             {"n": "Região", "w": 20, "cor": "#E8B54A"},
                             {"n": "Acionabilidade", "w": 20, "cor": "#4ADE80"}]},
              key="pesos_v2")

    st.markdown("#### Detalhe por critério — clique para expandir")
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
            {"n": "Aderência", "v": min(100, score_sel), "c": "#E8873A"},
            {"n": "Fit", "v": max(0, score_sel - 2), "c": "#4ADE80"},
            {"n": "Região", "v": max(0, score_sel - 4), "c": "#5B9BD5"},
            {"n": "Ação", "v": max(0, score_sel - 3), "c": "#7C8698"},
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
            '<p style="font-family:var(--mono);font-size:12.5px;color:var(--text);line-height:1.9">'
            'SCORE = 0,35·ADERÊNCIA<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ 0,25·VALOR'
            '<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ 0,20·REGIÃO'
            '<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ 0,20·AÇÃO</p>'
            '<div class="divider"></div>'
            '<p style="font-size:12.5px;color:var(--muted);line-height:1.7">'
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
        with st.container(border=True, key=f"vcard_{oid}"):
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
