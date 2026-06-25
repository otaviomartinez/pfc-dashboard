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

import html
import json
import os

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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
    page_title="PFC · Inteligência de Captação",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="collapsed",
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

PAGES = ["Visão geral", "Ranking", "Radar", "Funil", "Metodologia"]
PAGE_ICONS = {"Visão geral": "📊", "Ranking": "📋", "Radar": "📡",
              "Funil": "🗂️", "Metodologia": "🧮"}

# --------------------------------------------------------------------------- #
# Tema escuro premium + CSS custom
# --------------------------------------------------------------------------- #
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root{
  /* superfícies neutras — o contraste vem do espaço, não da cor */
  --bg:#0A0C0F; --surface:#141820; --surface-2:#1B202A; --surface-3:#232A35; --raise:#1B202A;
  --glass:rgba(20,24,32,.60);
  --line:rgba(255,255,255,.05); --line-2:rgba(255,255,255,.10); --line-3:rgba(255,255,255,.20);
  --text:#E9EBEE; --text-2:#C2C7CE; --muted:#828A94; --dim:#565E68; --white:#FFFFFF;
  /* cores reservadas só para destaques semânticos (status, ações, alertas) */
  --orange:#E89A3C; --orange-2:#F0B264; --orange-soft:rgba(232,154,60,.12);
  --green:#5FB137; --green-2:#9FD27F; --green-soft:rgba(95,177,55,.12);
  --blue:#5B9BD5; --blue-2:#8FBDE6; --blue-soft:rgba(91,155,213,.12);
  --red:#E2574A; --red-2:#EE8076; --red-soft:rgba(226,87,74,.12);
  --r:10px; --r-lg:14px;
  --sh-1:0 1px 2px rgba(0,0,0,.16); --sh-2:0 24px 70px rgba(0,0,0,.50);
  --ease:cubic-bezier(.22,.61,.36,1);
  --disp:'Space Grotesk',system-ui,sans-serif; --body:'Inter',system-ui,sans-serif;
}
html, body, [class*="css"]{font-family:var(--body);line-height:1.6;}
.stApp{
  background:var(--bg);
  background-image:radial-gradient(900px 520px at 85% -15%, rgba(255,255,255,.022), transparent 62%);
}
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

/* ============ fundo cósmico + superfícies táteis ============ */
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"],section.main,[data-testid="stHeader"]{background:transparent!important}
body{background:#0A0C0F}
#pfc-cosmos-layer{position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden}
#pfc-stars{position:absolute;inset:0}
.pfc-nebula{position:absolute;inset:-12%;
  background:radial-gradient(60% 52% at 78% 12%, rgba(91,155,213,.07), transparent 60%),
             radial-gradient(54% 46% at 10% 88%, rgba(232,154,60,.05), transparent 62%),
             radial-gradient(60% 60% at 48% 50%, rgba(255,255,255,.018), transparent 72%);
  animation:pfc-breathe 8s ease-in-out infinite}
@keyframes pfc-breathe{0%,100%{transform:scale(1);opacity:.8}50%{transform:scale(1.05);opacity:1}}
.pfc-spotlight{position:absolute;left:0;top:0;width:400px;height:400px;border-radius:50%;opacity:0;will-change:transform;
  background:radial-gradient(circle,rgba(255,255,255,.06),transparent 60%);transition:opacity .5s ease}
.block-container{position:relative;z-index:1}
.pfc-ink{position:absolute;border-radius:50%;background:rgba(255,255,255,.26);pointer-events:none;z-index:4}
.kpi,.card,.lead,.caso{transform-style:preserve-3d;will-change:transform}
.kpi::after,.card::after,.lead::after,.caso::after{content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none;
  background:radial-gradient(240px circle at var(--mx,50%) var(--my,50%),rgba(255,255,255,.09),transparent 55%);
  opacity:0;transition:opacity .35s var(--ease)}
.kpi:hover::after,.card:hover::after,.lead:hover::after,.caso:hover::after{opacity:1}
.card,.kcol,.lead,.caso,.kpi{box-shadow:var(--sh-1),inset 0 0 0 1px rgba(255,255,255,.018)}
.card:hover,.lead:hover,.caso:hover{box-shadow:0 18px 48px rgba(0,0,0,.5),inset 0 0 0 1px rgba(255,255,255,.06)}
.brand svg,.avatar{will-change:transform}
.login-logo svg{transition:transform .4s var(--ease)}
.login-logo:hover svg .orbit, .brand:hover svg .orbit{animation:spin 9s linear infinite}
@media (prefers-reduced-motion:reduce){
  .pfc-nebula{animation:none}.pfc-spotlight{display:none}
  .kpi,.card,.lead,.caso{transform:none!important}
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# --------------------------------------------------------------------------- #
# Fundo cósmico + micro-interações (canvas de estrelas, nebulosa, estrela
# cadente, spotlight do cursor, ripple, tilt 3D, magnetismo).
# st.markdown remove <script>, então injetamos UM script no documento-pai via
# components.html (mesma origem). Persiste entre reruns e degrada sem erro.
# --------------------------------------------------------------------------- #
_COSMOS_JS = r"""
(function(){
  if(window.__pfcCosmos){return;} window.__pfcCosmos=true;
  var reduce=false; try{reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;}catch(e){}
  var body=document.body;
  var layer=document.createElement('div'); layer.id='pfc-cosmos-layer';
  var neb=document.createElement('div'); neb.className='pfc-nebula'; layer.appendChild(neb);
  var cv=document.createElement('canvas'); cv.id='pfc-stars'; layer.appendChild(cv);
  var spot=document.createElement('div'); spot.className='pfc-spotlight'; layer.appendChild(spot);
  body.insertBefore(layer, body.firstChild);
  var ctx=cv.getContext('2d'); var W=0,H=0; var DPR=Math.min(window.devicePixelRatio||1,2);
  function resize(){W=cv.width=Math.floor(innerWidth*DPR);H=cv.height=Math.floor(innerHeight*DPR);cv.style.width=innerWidth+'px';cv.style.height=innerHeight+'px';}
  resize(); window.addEventListener('resize',resize);
  var N=innerWidth<700?180:380, stars=[], seed=987654321;
  function rnd(){seed=(seed*1664525+1013904223)>>>0; return seed/4294967296;}
  for(var i=0;i<N;i++){stars.push({x:rnd(),y:rnd(),r:rnd()*1.2+0.25,ph:rnd()*6.28,sp:0.4+rnd()*1.1,base:0.22+rnd()*0.5});}
  var shoot=null,lastShoot=0;
  function draw(t){
    ctx.clearRect(0,0,W,H);
    for(var i=0;i<stars.length;i++){var s=stars[i];var op=s.base;if(!reduce){op+=Math.sin(t/1000*s.sp+s.ph)*0.35;}if(op<0.04){op=0.04;}if(op>1){op=1;}ctx.globalAlpha=op;ctx.beginPath();ctx.arc(s.x*W,s.y*H,s.r*DPR,0,6.2832);ctx.fillStyle=(i%23===0?'#9FBEDF':'#ffffff');ctx.fill();}
    ctx.globalAlpha=1;
    if(!reduce){
      if(!shoot && t-lastShoot>(15000+rnd()*6000)){lastShoot=t;var fl=rnd()>0.5;shoot={x:rnd()*W*0.7,y:rnd()*H*0.35,vx:(fl?1:-1)*(7+rnd()*5)*DPR,vy:(3+rnd()*2)*DPR,life:0};}
      if(shoot){var x2=shoot.x-shoot.vx*9,y2=shoot.y-shoot.vy*9;var g=ctx.createLinearGradient(shoot.x,shoot.y,x2,y2);g.addColorStop(0,'rgba(255,255,255,.95)');g.addColorStop(1,'rgba(255,255,255,0)');ctx.strokeStyle=g;ctx.lineWidth=1.8*DPR;ctx.beginPath();ctx.moveTo(shoot.x,shoot.y);ctx.lineTo(x2,y2);ctx.stroke();shoot.x+=shoot.vx*2.4;shoot.y+=shoot.vy*2.4;shoot.life++;if(shoot.life>46||shoot.x<-60||shoot.x>W+60||shoot.y>H+60){shoot=null;}}
    }
    requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);
  if(!reduce){
    var sx=innerWidth/2,sy=innerHeight/2,tx=sx,ty=sy;
    window.addEventListener('mousemove',function(e){tx=e.clientX;ty=e.clientY;spot.style.opacity='1';},{passive:true});
    (function loop(){sx+=(tx-sx)*0.12;sy+=(ty-sy)*0.12;spot.style.transform='translate('+(sx-200)+'px,'+(sy-200)+'px)';requestAnimationFrame(loop);})();
  }
  // ripple
  if(!reduce){document.addEventListener('pointerdown',function(e){
    var el=e.target.closest('button,[role="tab"],.stat,.src-tag,.mtag,[data-testid="stLinkButton"] a'); if(!el){return;}
    var r=el.getBoundingClientRect();var sz=Math.max(r.width,r.height)*1.15;
    var ink=document.createElement('span');ink.className='pfc-ink';
    ink.style.width=ink.style.height=sz+'px';ink.style.left=(e.clientX-r.left-sz/2)+'px';ink.style.top=(e.clientY-r.top-sz/2)+'px';
    ink.style.transform='scale(0)';ink.style.opacity='.5';ink.style.transition='transform .55s cubic-bezier(.22,.61,.36,1),opacity .6s ease';
    var cs=getComputedStyle(el);if(cs.position==='static'){el.style.position='relative';}el.style.overflow='hidden';
    el.appendChild(ink);requestAnimationFrame(function(){ink.style.transform='scale(2.4)';ink.style.opacity='0';});
    setTimeout(function(){if(ink.parentNode){ink.parentNode.removeChild(ink);}},660);
  },true);}
  // tilt 3D + brilho que segue o mouse
  var tiltEl=null;
  if(!reduce){
    document.addEventListener('mousemove',function(e){
      var el=e.target.closest('.kpi,.card,.lead,.caso');
      if(el!==tiltEl){if(tiltEl){tiltEl.style.transform='';}tiltEl=el;}
      if(!el){return;}
      var r=el.getBoundingClientRect();var px=(e.clientX-r.left)/r.width-0.5;var py=(e.clientY-r.top)/r.height-0.5;
      el.style.transform='perspective(820px) rotateX('+(-py*5).toFixed(2)+'deg) rotateY('+(px*5).toFixed(2)+'deg) translateY(-3px)';
      el.style.setProperty('--mx',((px+0.5)*100).toFixed(1)+'%');el.style.setProperty('--my',((py+0.5)*100).toFixed(1)+'%');
    },{passive:true});
    document.addEventListener('mouseout',function(e){if(tiltEl && !tiltEl.contains(e.relatedTarget)){tiltEl.style.transform='';tiltEl=null;}},true);
  }
  // magnetismo na logo e avatar
  if(!reduce){window.addEventListener('mousemove',function(e){
    var els=document.querySelectorAll('.brand svg, .avatar');
    for(var i=0;i<els.length;i++){var el=els[i];var r=el.getBoundingClientRect();var cx=r.left+r.width/2,cy=r.top+r.height/2;
      var dx=e.clientX-cx,dy=e.clientY-cy,d=Math.sqrt(dx*dx+dy*dy);
      if(d<130){var f=(1-d/130)*0.4;el.style.transform='translate('+(dx*f).toFixed(1)+'px,'+(dy*f).toFixed(1)+'px)';}
      else if(el.style.transform){el.style.transform='';}}
  },{passive:true});}
})();
"""
_COSMOS_BOOT = (
    "<script>(function(){try{var P=window.parent;if(!P||!P.document){return;}"
    "if(P.document.getElementById('pfc-cosmos-js')){return;}"
    "var s=P.document.createElement('script');s.id='pfc-cosmos-js';"
    "s.textContent=" + json.dumps(_COSMOS_JS) + ";"
    "P.document.head.appendChild(s);}catch(e){}})();</script>"
)
components.html(_COSMOS_BOOT, height=0)

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
# Cabeçalho com logo, selo de modo e usuário logado
# --------------------------------------------------------------------------- #
def render_header():
    if modo_conectado:
        selo = '<span class="pill ok"><span class="dot"></span> 🟢 Conectado ao Google Sheets</span>'
    else:
        selo = '<span class="pill local">🟠 Modo local (CSV) — escrita desabilitada</span>'
    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.markdown(
            f'<div class="brand">{LOGO_SVG.format(size=42)}'
            '<div><div class="wm">Programa Futuro Cientista</div>'
            '<div class="sub">Inteligência de Captação</div></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<div class="selo-wrap">{selo}</div>', unsafe_allow_html=True)
    with col_b:
        st.markdown(
            f'<div class="userbox"><div class="who">'
            f'<div class="nm">{esc(USER["nome"])}</div>'
            f'<div class="pf">{esc(USER["perfil"])}</div></div>'
            f'<span class="avatar" style="background:{USER["bg"]};border:1px solid {USER["bd"]};'
            f'color:{USER["tx"]}" title="{esc(USER["email"])}">{esc(USER["inicial"])}</span></div>',
            unsafe_allow_html=True,
        )
        sub = st.columns([2, 1])
        with sub[1]:
            if st.button("🔓 Sair", key="logout", use_container_width=True):
                for k in ("user", "page", "login_email", "login_senha"):
                    st.session_state.pop(k, None)
                st.rerun()
    st.markdown('<div class="hr-line"></div>', unsafe_allow_html=True)


render_header()

# --------------------------------------------------------------------------- #
# Barra de navegação (páginas) + breadcrumb
# --------------------------------------------------------------------------- #
nav_cols = st.columns(len(PAGES))
for i, p in enumerate(PAGES):
    rotulo = f"{PAGE_ICONS[p]} {p}" + (f" ({TOTAL})" if p == "Ranking" else "")
    nav_cols[i].button(
        rotulo, key=f"nav_{p}", use_container_width=True,
        type="primary" if st.session_state["page"] == p else "secondary",
        on_click=ir_para, args=(p,),
    )

PAGINA = st.session_state["page"]
breadcrumb("PFC", PAGINA)

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


# =========================================================================== #
# PÁGINA · VISÃO GERAL
# =========================================================================== #
def page_visao():
    st.markdown(
        '<div class="phead"><h1>Painel de captação</h1>'
        f'<p>{TOTAL} organizações monitoradas · clique nos cartões e segmentos para explorar</p></div>',
        unsafe_allow_html=True,
    )

    cont = df[COL_STATUS].value_counts() if TOTAL else pd.Series(dtype=int)
    n_prospectar = int(cont.get("Prospectar", 0))
    n_monitorar = int(cont.get("Monitorar", 0))
    n_edital = int(cont.get("Edital", 0))
    valor_total = float(df[COL_VALVO].sum()) if TOTAL else 0.0
    n_verif = int(df[COL_VERIF].apply(verificada_ok).sum()) if TOTAL else 0

    kpis = [
        ("📚", "Organizações mapeadas", str(TOTAL),
         f"<b>{n_verif}</b> de {TOTAL} fontes verificadas", "Ver breakdown", "breakdown"),
        ("📈", "Em prospecção ativa", str(n_prospectar),
         f"<b>{n_monitorar}</b> monitorando · <b>{n_edital}</b> em edital", "Listar prospecção", "prospeccao"),
        ("💰", "Valor-alvo potencial", brl_curto(valor_total),
         "soma do pipeline de captação", "Top 10 por valor", "valor"),
        ("⚡", "Oportunidades hoje", "4",
         "novas · aguardando revisão", "Abrir Radar", "radar"),
    ]
    cols = st.columns(4)
    for col, (icon, name, val, foot, btn_lab, acao) in zip(cols, kpis):
        with col:
            st.markdown(
                f'<div class="kpi"><div class="lab"><span class="ic">{icon}</span> {name}</div>'
                f'<div class="val">{val}</div><div class="foot">{foot}</div></div>',
                unsafe_allow_html=True,
            )
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

    # ---- Funil clicável + distribuição em gráfico ----
    with esq:
        cores_funil = {s: CORES_STATUS[s] for s in STATUS_FUNIL}
        segs, legs = "", ""
        for s in STATUS_FUNIL:
            n = int(cont.get(s, 0))
            if TOTAL > 0 and n > 0:
                segs += f'<i style="width:{n / TOTAL * 100:.2f}%;background:{cores_funil[s]}" title="{s} · {n}"></i>'
            legs += (f'<span><span class="sw" style="background:{cores_funil[s]}"></span>{s} <b>{n}</b></span>')
        st.markdown(
            f'<div class="card"><div class="card-h"><div><h2>Distribuição do funil</h2>'
            f'<div class="cap">clique numa etapa para ver as organizações</div></div></div>'
            f'<div class="pad"><div class="funil">{segs}</div><div class="fleg">{legs}</div></div></div>',
            unsafe_allow_html=True,
        )
        chip_cols = st.columns(len(STATUS_FUNIL))
        for j, s in enumerate(STATUS_FUNIL):
            n = int(cont.get(s, 0))
            if chip_cols[j].button(f"{s} · {n}", key=f"seg_{s}", use_container_width=True):
                dlg_status_list(s)

    # ---- Distribuição (Plotly donut) ----
    with dir_:
        st.markdown(
            '<div class="card"><div class="card-h"><div><h2>Pipeline por status</h2>'
            '<div class="cap">distribuição das organizações</div></div></div>'
            '<div class="pad" id="pie-pad"></div></div>',
            unsafe_allow_html=True,
        )
        if PLOTLY_OK and TOTAL:
            labels = [s for s in STATUS_FUNIL if int(cont.get(s, 0)) > 0]
            values = [int(cont.get(s, 0)) for s in labels]
            fig = go.Figure(go.Pie(
                labels=labels, values=values, hole=0.58, sort=False,
                marker=dict(colors=[CORES_STATUS[s] for s in labels],
                            line=dict(color="#0A0C0F", width=2)),
                textinfo="label+value",
                hovertemplate="<b>%{label}</b><br>%{value} orgs · %{percent}<extra></extra>",
            ))
            fig.add_annotation(text=f"<b>{TOTAL}</b><br>orgs", showarrow=False,
                               font=dict(size=18, color="#F2F0E9", family="Space Grotesk"))
            st.plotly_chart(estilo_plotly(fig, altura=300), use_container_width=True,
                            config={"displayModeBar": False})
        elif not PLOTLY_OK:
            st.info("Instale o Plotly (`pip install plotly`) para ver o gráfico interativo.")

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
                          label_visibility="collapsed")
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
            if ccols[k].button(rotulo, key=f"cid_{cidade}", use_container_width=True):
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
def page_radar():
    st.markdown(
        '<div class="phead"><h1>Radar de oportunidades</h1>'
        '<p>varredura diária às 06:00 · aprove para enviar à aba “Novidades_pendentes”</p></div>',
        unsafe_allow_html=True,
    )
    LEADS = [
        {"id": "fapesp", "fonte": "FAPESP", "fit": 91, "cls": "hi",
         "titulo": "Difusão e Popularização da Ciência 2026",
         "why": "Foco em ensino básico e divulgação científica — encaixe direto no Clube de Ciências.",
         "descricao": "Apoio a projetos que aproximem ciência e escola pública, com bolsas e recursos.",
         "prazo": "31/08/2026", "valor_estimado": "R$ 80 mil – R$ 200 mil", "link": "https://fapesp.br/"},
        {"id": "itau", "fonte": "Itaú Social", "fit": 88, "cls": "mid",
         "titulo": "Chamada — Equidade na Educação Pública",
         "why": "Público e território aderentes; atua em municípios da região PFC.",
         "descricao": "Apoio a iniciativas que reduzam desigualdades de aprendizagem na rede pública.",
         "prazo": "Fluxo contínuo", "valor_estimado": "R$ 100 mil – R$ 250 mil", "link": "https://www.itausocial.org.br/"},
        {"id": "prosas", "fonte": "Prosas", "fit": 73, "cls": "mid",
         "titulo": "Edital Juventude & Futuro",
         "why": "Aderente à missão, mas valor abaixo do alvo — vale checar contrapartidas.",
         "descricao": "Plataforma agrega editais; esta chamada apoia projetos de juventude e protagonismo.",
         "prazo": "15/07/2026", "valor_estimado": "R$ 30 mil – R$ 60 mil", "link": "https://prosas.com.br/"},
    ]
    LEAD_FILTRADO = {"fonte": "Filtrado", "fit": 22,
                     "titulo": "Cupom de cursos online — plataforma EAD",
                     "why": "produto comercial, não fomento. O radar descartou automaticamente."}
    st.session_state.setdefault("radar_resolvidos", {})

    col_fila, col_lado = st.columns([1.6, 1])
    with col_fila:
        st.markdown(
            '<div class="card-h" style="border:1px solid var(--line);border-bottom:none;'
            'border-radius:16px 16px 0 0;background:var(--surface)"><div><h2>Fila de revisão</h2>'
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
                txt = "✓ Aprovado — enviado à base" if resolvido == "ok" else "✕ Descartado da fila"
                st.markdown(f'<div class="lead" style="opacity:.55"><div class="ttl">{esc(lead["titulo"])}</div>'
                            f'<div class="why" style="color:{cor}">{txt}</div></div>', unsafe_allow_html=True)
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
                             type="primary", disabled=not modo_conectado):
                    res = dados.adicionar_lead_radar({
                        "data": pd.Timestamp.now().strftime("%d/%m/%Y"), "fonte": lead["fonte"],
                        "titulo": lead["titulo"], "descricao": lead["descricao"],
                        "score_aderencia": lead["fit"], "prazo": lead["prazo"],
                        "valor_estimado": lead["valor_estimado"], "link": lead["link"],
                        "status": "Pendente de revisão"})
                    st.session_state.radar_resolvidos[lead["id"]] = "ok"
                    st.session_state["radar_msg"] = res
                    st.toast(res["mensagem"], icon="✅" if res["sucesso"] else "⚠️")
                    st.rerun()
            with b2:
                if st.button("Descartar", key=f"no_{lead['id']}"):
                    st.session_state.radar_resolvidos[lead["id"]] = "no"
                    st.toast("Descartado da fila.", icon="🗑️")
                    st.rerun()

        st.markdown(
            f'<div class="lead rej"><div class="lead-top">'
            f'<span class="src" style="color:var(--red);background:var(--red-soft)">{esc(LEAD_FILTRADO["fonte"])}</span>'
            f'<span class="fit lo">fit {LEAD_FILTRADO["fit"]}</span></div>'
            f'<div class="ttl">{esc(LEAD_FILTRADO["titulo"])}</div>'
            f'<div class="why"><span class="rej-tag">Fora do escopo:</span> {esc(LEAD_FILTRADO["why"])}</div></div>',
            unsafe_allow_html=True,
        )

    with col_lado:
        fontes = ["CAPTA", "Prosas", "ABCR", "CNPq", "FAPESP", "Finep", "CAPES", "Itaú Social",
                  "Fund. Bradesco", "Inst. Lemann", "Fund. Banco do Brasil", "MEC",
                  "Fund. Telefônica", "Sec. Educação SP"]
        chips = "".join(f'<span class="src-tag">{esc(f)}</span>' for f in fontes)
        st.markdown(
            f"""
            <div class="card"><div class="card-h"><div><h2>Fontes monitoradas</h2>
              <div class="cap">{len(fontes)} fontes · última varredura hoje 06:00</div></div></div>
              <div class="pad">{chips}<div class="note">O radar vigia fontes conhecidas e estáveis —
              nada de varrer a internet inteira. Você decide o que entra na base.</div></div></div>
            <div class="card"><div class="card-h"><div><h2>Resumo de hoje</h2><div class="cap">06:00</div></div></div>
              <div class="pad">
                <div class="statline"><span style="color:var(--muted)">Itens varridos</span><b>37</b></div>
                <div class="statline"><span style="color:var(--muted)">Filtrados (fora do escopo)</span><b style="color:var(--red)">33</b></div>
                <div class="statline"><span style="color:var(--muted)">Na sua fila</span><b style="color:var(--green)">4</b></div>
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


# Gráfico de Score orbital interativo (SVG + JS autocontido, instantâneo).
ORBITAL_TEMPLATE = r"""<!doctype html><html><head><meta charset="utf-8"><style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:transparent;font-family:'Inter',system-ui,sans-serif;color:#E9EBEE}
.wrap{background:rgba(20,24,32,.6);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.06);border-radius:14px;overflow:hidden;box-shadow:0 1px 2px rgba(0,0,0,.16),inset 0 0 0 1px rgba(255,255,255,.02)}
.h{padding:18px 20px 13px;border-bottom:1px solid rgba(255,255,255,.06)}
.h h2{font-family:'Space Grotesk';font-weight:600;font-size:15.5px;margin:0}
.h .cap{font-size:12px;color:#565E68;margin-top:3px}
.body{padding:12px 18px 16px}
.orbit-wrap{display:grid;place-items:center}
.arc{cursor:pointer;transition:stroke-width .3s cubic-bezier(.22,.61,.36,1),opacity .3s ease,filter .3s ease}
.dim{opacity:.26}
.cn{font-family:'Space Grotesk';font-weight:700;cursor:pointer;transition:fill .3s ease}
.legend{display:flex;flex-direction:column;gap:7px;margin-top:6px}
.lrow{display:grid;grid-template-columns:12px 1fr auto;align-items:center;gap:9px;padding:7px 10px;border:1px solid rgba(255,255,255,.05);border-radius:9px;cursor:pointer;transition:background .2s ease,border-color .2s ease,transform .15s ease}
.lrow:hover{background:rgba(255,255,255,.04);border-color:rgba(255,255,255,.12);transform:translateX(2px)}
.lrow.sel{background:rgba(255,255,255,.06);border-color:rgba(255,255,255,.18)}
.sw{width:10px;height:10px;border-radius:3px}
.ln{font-size:12.5px;color:#C2C7CE}
.lv{font-family:'Space Grotesk';font-weight:600;font-size:13px}
.tip{position:fixed;pointer-events:none;background:#1F242C;border:1px solid rgba(255,255,255,.14);color:#E9EBEE;font-size:12px;padding:6px 9px;border-radius:7px;opacity:0;transition:opacity .15s ease;z-index:9;white-space:nowrap}
.hint{font-size:11px;color:#565E68;text-align:center;margin-top:9px}
</style></head><body>
<div class="wrap"><div class="h"><h2>Anatomia do Score</h2><div class="cap">anéis clicáveis · exemplo: __NOME__ = __TOTAL__</div></div>
<div class="body">
<div class="orbit-wrap"><svg id="svg" width="208" height="208" viewBox="0 0 200 200" aria-label="Score orbital"></svg></div>
<div class="legend" id="legend"></div>
<div class="hint">clique num anel ou critério para destacar · clique no centro para o total</div>
</div></div><div class="tip" id="tip"></div>
<script>
(function(){
  var DATA=__DATA__, TOTAL=__TOTAL__, RADII=[76,62,48,34], SW=9, NS='http://www.w3.org/2000/svg';
  var svg=document.getElementById('svg'), legend=document.getElementById('legend'), tip=document.getElementById('tip'), sel=-1, arcs=[];
  function el(t,a){var e=document.createElementNS(NS,t);for(var k in a){e.setAttribute(k,a[k]);}return e;}
  var g=el('g',{transform:'rotate(-90 100 100)'}); svg.appendChild(g);
  DATA.forEach(function(d,i){
    var r=RADII[i], C=2*Math.PI*r, len=d.v/100*C;
    g.appendChild(el('circle',{cx:100,cy:100,r:r,fill:'none',stroke:'rgba(255,255,255,.06)','stroke-width':SW}));
    var a=el('circle',{cx:100,cy:100,r:r,fill:'none',stroke:d.c,'stroke-width':SW,'stroke-linecap':'round','stroke-dasharray':len+' '+(C-len)});
    a.setAttribute('class','arc'); a.setAttribute('data-i',i); g.appendChild(a); arcs.push(a);
  });
  var cn=el('text',{x:100,y:99,'text-anchor':'middle','font-size':46,fill:'#9FD27F'}); cn.setAttribute('class','cn'); cn.textContent=TOTAL; svg.appendChild(cn);
  var cl=el('text',{x:100,y:120,'text-anchor':'middle','font-size':12,fill:'#828A94','font-family':'Inter'}); cl.textContent='de 100'; svg.appendChild(cl);
  DATA.forEach(function(d,i){
    var row=document.createElement('div'); row.className='lrow'; row.setAttribute('data-i',i);
    row.innerHTML='<span class="sw" style="background:'+d.c+'"></span><span class="ln">'+d.n+' <span style="color:#565E68">('+d.w+'%)</span></span><span class="lv" style="color:'+d.c+'">'+d.v+'</span>';
    legend.appendChild(row);
  });
  function apply(){
    if(sel<0){ cn.textContent=TOTAL; cn.setAttribute('fill','#9FD27F');
      arcs.forEach(function(a){a.classList.remove('dim');a.setAttribute('stroke-width',SW);a.style.filter='';});
      [].forEach.call(legend.children,function(r){r.classList.remove('sel');});
    } else { var d=DATA[sel]; cn.textContent=d.v; cn.setAttribute('fill',d.c);
      arcs.forEach(function(a,i){ if(i===sel){a.classList.remove('dim');a.setAttribute('stroke-width',SW+3);a.style.filter='drop-shadow(0 0 6px '+d.c+')';} else {a.classList.add('dim');a.setAttribute('stroke-width',SW);a.style.filter='';} });
      [].forEach.call(legend.children,function(r,i){if(i===sel){r.classList.add('sel');}else{r.classList.remove('sel');}});
    }
  }
  function pick(i){ sel=(sel===i?-1:i); apply(); }
  arcs.forEach(function(a){ a.addEventListener('click',function(){pick(+a.getAttribute('data-i'));});
    a.addEventListener('mousemove',function(e){var d=DATA[+a.getAttribute('data-i')];tip.textContent=d.n+' '+d.v;tip.style.opacity='1';tip.style.left=(e.clientX+14)+'px';tip.style.top=(e.clientY+12)+'px';});
    a.addEventListener('mouseleave',function(){tip.style.opacity='0';}); });
  [].forEach.call(legend.children,function(r){ r.addEventListener('click',function(){pick(+r.getAttribute('data-i'));}); });
  cn.addEventListener('click',function(){sel=-1;apply();});
  apply();
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
        topo = df.sort_values(COL_SCORE, ascending=False).iloc[0] if TOTAL else None
        score_topo = int(topo[COL_SCORE]) if topo is not None else 0
        nome_topo = str(topo[COL_EMPRESA]) if topo is not None else "—"
        # Valores por componente: ilustrativos (o MVP usa o Score PFC da planilha).
        comps = [
            {"n": "Aderência", "v": min(99, score_topo + 1), "c": "#E89A3C", "w": 35},
            {"n": "Valor", "v": score_topo, "c": "#5FB137", "w": 25},
            {"n": "Região", "v": max(60, score_topo - 3), "c": "#5B9BD5", "w": 20},
            {"n": "Acionabilidade", "v": max(60, score_topo - 1), "c": "#9AA2AC", "w": 20},
        ]
        orb = (ORBITAL_TEMPLATE
               .replace("__DATA__", json.dumps(comps))
               .replace("__TOTAL__", str(score_topo))
               .replace("__NOME__", html.escape(nome_topo)))
        components.html(orb, height=448)
        st.caption(f"Decomposição ilustrativa de **{nome_topo}** pelos pesos fixos.")
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
# ROTEAMENTO
# =========================================================================== #
ROTAS = {"Visão geral": page_visao, "Ranking": page_ranking, "Radar": page_radar,
         "Funil": page_funil, "Metodologia": page_metodo}
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
