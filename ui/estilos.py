"""
Estilos e assets do dashboard PFC — CSS, JS e SVG embutidos.

Extraído de app.py (passo 1 da modularização): SÓ constantes de apresentação,
sem lógica nem dependência de runtime. As strings são idênticas às originais;
nada de comportamento muda. app.py importa estes nomes de volta.

Ordem preservada de app.py para respeitar as dependências internas
(_SIDEBAR_TOGGLE_JS usa _SIDEBAR_TOGGLE_CORE; _TOPNAV_OFFSET_CSS usa
TOPNAV_ALTURA; _ORF_PIN usa ICONES; _RADAR_V2_JS usa _SELO_JS_FN).
"""
import json  # usado por _SIDEBAR_TOGGLE_JS (json.dumps do core)


_SVG_TRACO = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
              "stroke='black' stroke-width='1.8' stroke-linecap='round' "
              "stroke-linejoin='round'>{}</svg>")


ICONES = {
    "visao-geral": ("<rect x='3' y='3' width='7' height='9' rx='1'/>"
                    "<rect x='14' y='3' width='7' height='5' rx='1'/>"
                    "<rect x='14' y='12' width='7' height='9' rx='1'/>"
                    "<rect x='3' y='16' width='7' height='5' rx='1'/>"),
    "ranking": "<path d='M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01'/>",
    "radar": ("<circle cx='12' cy='12' r='9'/><circle cx='12' cy='12' r='3.5'/>"
              "<path d='M12 12l6-6'/>"),
    "funil": "<path d='M3 4h18l-7 8.5V19l-4 2v-8.5z'/>",
    "metodologia": ("<path d='M4 7h16M4 13h16M4 19h16'/><circle cx='9' cy='7' r='2.2'/>"
                    "<circle cx='16' cy='13' r='2.2'/><circle cx='7' cy='19' r='2.2'/>"),
    "verificacao": "<circle cx='11' cy='11' r='7'/><path d='M20 20l-3.6-3.6'/>",
    "deputados": ("<path d='M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2'/>"
                  "<circle cx='12' cy='7' r='4'/>"),
    "funil-negociacao": ("<rect x='3' y='4' width='5' height='16' rx='1'/>"
                         "<rect x='10' y='4' width='5' height='11' rx='1'/>"
                         "<rect x='17' y='4' width='5' height='7' rx='1'/>"),
    # bússola: tela de planejamento "quem abordar" (descobrir/prospectar)
    "descobrir": ("<circle cx='12' cy='12' r='9'/>"
                  "<path d='M15.5 8.5l-2 5-5 2 2-5z'/>"),
    "trocar-radar": ("<path d='M16 3l4 4-4 4'/><path d='M20 7H8a4 4 0 0 0-4 4'/>"
                     "<path d='M8 21l-4-4 4-4'/><path d='M4 17h12a4 4 0 0 0 4-4'/>"),
    # mesmo traçado do "Sair" da barra superior — os dois falam a mesma língua
    "sair": "<path d='M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9'/>",
    "local": ("<path d='M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z'/>"
              "<circle cx='12' cy='10' r='3'/>"),
    # documento com linhas: Relatório de Prioridades (os dois painéis reusam)
    "relatorio": ("<path d='M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z'/>"
                  "<path d='M14 3v6h6'/><path d='M8 13h8M8 17h6'/>"),
    "bloqueado": ("<rect x='4' y='11' width='16' height='10' rx='2'/>"
                  "<path d='M8 11V7a4 4 0 0 1 8 0v4'/>"),
}


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
/* Header transparente e mínimo — mas SEM escondê-lo por completo, senão some
   junto o botão nativo de reabrir a sidebar (stExpandSidebarButton), deixando
   o usuário preso quando a sidebar recolhe. Escondemos só o que não interessa. */
[data-testid="stHeader"]{background:transparent!important;box-shadow:none!important;}
[data-testid="stToolbar"]{background:transparent!important;}
#MainMenu, footer, [data-testid="stDecoration"], [data-testid="stStatusWidget"],
[data-testid="stToolbarActions"], [data-testid="stMainMenu"],
/* Deploy: na 1.58 fica FORA de stToolbarActions, em elemento próprio — por isso
   escapava das regras acima e sobrepunha o seletor de radar da barra superior. */
[data-testid="stAppDeployButton"], [data-testid="stMainMenuButton"]{display:none!important;}
/* O header sobra como faixa transparente de 60px, largura inteira, z-index 999990:
   invisível, mas roubava o clique do seletor e do avatar da .tn (z-index 1000).
   pointer-events:none devolve o clique à barra; o botão de expandir a sidebar
   reativa o seu (e o clique programático do _SIDEBAR_FIX_JS segue funcionando). */
[data-testid="stHeader"], [data-testid="stToolbar"]{pointer-events:none!important;}
/* botão nativo de reabrir a sidebar: sempre visível e destacado quando ela recolhe */
[data-testid="stExpandSidebarButton"]{display:flex!important;visibility:visible!important;
  pointer-events:auto!important;
  background:var(--surface)!important;border:1px solid var(--line-2)!important;border-radius:9px!important;}
[data-testid="stExpandSidebarButton"] svg, [data-testid="stExpandSidebarButton"] span,
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"]{color:var(--accent)!important;}
[data-testid="stAppViewContainer"]{overflow:visible;}
/* Conteúdo: margens simétricas e uso equilibrado da largura. Como na maquete,
   ocupa a área após a sidebar com padding lateral fixo; o max-width alto só
   evita linhas longas demais em monitores muito largos (aí centraliza). O
   padding lateral do Streamlit (80px) é sobrescrito — era ele que empurrava
   o conteúdo e deixava o vão entre a sidebar e os cards. */
.block-container, [data-testid="stMainBlockContainer"]{
  max-width:1680px!important;margin-left:auto!important;margin-right:auto!important;
  padding-left:36px!important;padding-right:36px!important;
  padding-bottom:3.4rem!important;}
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
/* ATENÇÃO — leia antes de mexer nas regras abaixo.
   A sidebar tem DOIS modos e o padrão é o estreito:
     ÍCONES (60px)   -> este bloco. Só os SVGs, com tooltip no hover.
     EXPANDIDA (250px)-> _SIDEBAR_OPEN_CSS, ativado pela classe html.pfc-sb-open.
   O toggle é CLIENT-SIDE (botão no TOPO da barra -> _SIDEBAR_TOGGLE_JS), SEM
   rerun: o estado vive na classe pfc-sb-open do <html> (não no Python), que
   sobrevive aos reruns. A barra NUNCA some por completo — decisão de projeto:
   nenhum caminho em que o usuário fique sem navegação (o modo "escondida" foi
   aposentado de propósito).
   Especificidade: _SIDEBAR_OPEN_CSS usa "html.pfc-sb-open [data-testid=...]",
   mais específico que este bloco — vence SEM depender da ordem de injeção
   (a antiga fragilidade de ordem deixou de existir).
   Ver: _SIDEBAR_OPEN_CSS, _SIDEBAR_TOGGLE_JS, _preparar_sidebar. */
[data-testid="stSidebar"]{background:var(--surface)!important;border-right:1px solid var(--line);
  width:60px!important;min-width:60px!important;max-width:60px!important;
  transform:none!important;margin-left:0!important;visibility:visible!important;
  transition:none!important}  /* largura NÃO anima por CSS: a setinha anima por timer JS */
[data-testid="stSidebar"][aria-expanded="false"]{transform:none!important;margin-left:0!important}
/* o tooltip do modo ícone precisa vazar dos 60px: nenhum ancestral pode cortar */
[data-testid="stSidebar"],
[data-testid="stSidebar"]>div:first-child,
[data-testid="stSidebar"] [data-testid="stVerticalBlock"],
[data-testid="stSidebar"] .stElementContainer,
[data-testid="stSidebar"] .stButton{overflow:visible!important}
/* O botão nativo de recolher fica escondido porque quem controla a barra é o
   nosso botão no topo do rail (client-side, _SIDEBAR_TOGGLE_JS).
   O botão nativo de REABRIR (stExpandSidebarButton) continua visível e
   estilizado mais abaixo: é a rede de segurança para quando o Streamlit
   colapsa a barra por conta própria (o bug dela sumir). */
[data-testid="stSidebarCollapseButton"]{display:none!important}
[data-testid="stSidebar"]>div:first-child{padding:18px 8px 16px}
/* respiro entre itens: 2px deixava a lista com cara de bloco único */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:6px}

/* ---- modo ÍCONES: some o texto, centraliza, e o nome vira tooltip ---- */
[data-testid="stSidebar"] .stButton>button{justify-content:center!important;padding:10px 0!important}
[data-testid="stSidebar"] .sb-brand{justify-content:center;padding:2px 0 14px}
[data-testid="stSidebar"] .sb-brand .bt{display:none}
/* controle recolher/expandir no TOPO do rail (clique tratado por delegação JS).
   Modo ícone (padrão): só o ícone "abrir" (»), centralizado. O modo expandido
   (html.pfc-sb-open, em _SIDEBAR_OPEN_CSS) troca para o ícone "recolher" («) + rótulo. */
.pfc-sb-toggle{display:flex;align-items:center;justify-content:center;gap:10px;cursor:pointer;
  color:var(--dim);border-radius:9px;padding:9px;margin:2px 0 0;user-select:none;
  border:1px solid transparent;transition:background .15s,color .15s,border-color .15s}
.pfc-sb-toggle:hover{background:rgba(255,255,255,.05);color:var(--ink);border-color:var(--line)}
.pfc-sb-toggle .pfc-ic{width:20px;height:20px;flex:none}
.pfc-sb-toggle .pfc-ic-fechar,.pfc-sb-toggle .pfc-sb-toggle-lbl{display:none}
/* divisor: respiro acima/abaixo, separando o controle do topo dos itens */
.pfc-sb-sep{height:1px;background:var(--line);margin:12px 4px 14px}
/* cabeçalho de seção vira um traço divisor (o rótulo não cabe em 60px) */
[data-testid="stSidebar"] .sb-sec{height:1px;padding:0;margin:12px 6px;overflow:hidden;
  background:var(--line);font-size:0;letter-spacing:0}
/* rodapé: fica só o ponto de status, o texto sai */
[data-testid="stSidebar"] .sb-foot{margin-top:18px;padding:14px 0 4px}
[data-testid="stSidebar"] .sf{justify-content:center;font-size:0;gap:0}
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
/* cabeçalho de seção: o padding-top é o que separa um grupo do anterior */
.sb-sec{font-family:var(--mono);font-size:10.5px;letter-spacing:1.4px;color:var(--dim);
  text-transform:uppercase;padding:22px 8px 9px}
[data-testid="stSidebar"] .stButton>button{width:100%;display:flex;justify-content:flex-start;text-align:left;
  background:transparent;border:none;color:var(--muted);font-size:14px;font-weight:500;
  padding:10px 14px;border-radius:9px;position:relative;box-shadow:none;transition:.15s var(--ease)}
[data-testid="stSidebar"] .stButton>button:hover{color:var(--ink);background:rgba(255,255,255,.03);transform:none}
/* item ATIVO: fundo na cor do acento + barra lateral grossa — "você está aqui" bem claro */
[data-testid="stSidebar"] .stButton>button[kind="primary"]{color:var(--ink);
  background:color-mix(in srgb,var(--accent) 15%,transparent);font-weight:600;
  box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--accent) 26%,transparent)}
[data-testid="stSidebar"] .stButton>button[kind="primary"]:hover{
  background:color-mix(in srgb,var(--accent) 22%,transparent)}
[data-testid="stSidebar"] .stButton>button[kind="primary"]::before{content:"";position:absolute;
  left:0;top:6px;bottom:6px;width:3px;border-radius:0 3px 3px 0;background:var(--accent);
  box-shadow:0 0 10px var(--accent)}
/* escopo desabilitado (Federal/Senadores em breve): visível mas claramente inativo */
[data-testid="stSidebar"] .stButton>button:disabled{opacity:.4;cursor:not-allowed}
.sb-foot{border-top:1px solid var(--line);margin-top:26px;padding:16px 8px 6px}
.sf{font-family:var(--mono);font-size:11px;color:var(--muted);display:flex;align-items:center;
  gap:9px;margin-bottom:9px;letter-spacing:.3px}
.sf .d{width:7px;height:7px;border-radius:50%;flex:none}
/* pontos de status = cor de SAÚDE, não de identidade: verde vivo / vermelho caiu.
   (o .d.o antigo, na cor de marca, foi aposentado para status de conexão) */
.sf .d.g{background:var(--sem-high);box-shadow:0 0 8px var(--sem-high);animation:pulse2 2s infinite}
.sf .d.r{background:var(--sem-urgent);box-shadow:0 0 8px var(--sem-urgent);animation:pulse2 2s infinite}
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


_HUB_CSS = """
.hub{position:fixed;inset:0;z-index:0;font-family:'Space Grotesk',system-ui,sans-serif;
  color:#EEF1F8;overflow:hidden;--ease:cubic-bezier(.16,1,.3,1)}
.hub *{box-sizing:border-box}
.hub-stars{position:absolute;inset:0;z-index:0}
.hub-planet{position:absolute;left:50%;top:74vh;transform:translateX(-50%);
  width:300vw;height:300vw;border-radius:50%;z-index:1;
  background:linear-gradient(180deg,#0e1430,#080c1c 12%,#04060F 28%);
  box-shadow:inset 0 8px 70px rgba(179,171,255,.10)}
.hub-atmo{position:absolute;left:50%;bottom:0;transform:translateX(-50%);
  width:130vw;height:26vh;z-index:1;pointer-events:none;
  background:radial-gradient(ellipse at 50% 100%,rgba(123,107,240,.20),rgba(59,139,208,.06) 45%,transparent 72%)}

.hub-rail{position:absolute;top:0;left:0;height:100vh;width:74px;z-index:40;
  background:linear-gradient(90deg,rgba(8,11,22,.9),rgba(8,11,22,.2));
  -webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);
  border-right:1px solid rgba(255,255,255,.06);
  display:flex;flex-direction:column;padding:22px 0;transition:width .42s var(--ease);overflow:hidden}
.hub-rail:hover{width:238px;background:linear-gradient(90deg,rgba(8,11,22,.98),rgba(8,11,22,.85))}
.hub-rlogo{display:flex;align-items:center;gap:13px;padding:0 20px 30px;white-space:nowrap}
.hub-rings{width:34px;height:34px;position:relative;flex:none}
.hub-rings span{position:absolute;inset:0;border-radius:50%;border:1.5px solid;animation:hub-spin 18s linear infinite}
.hub-rings span:nth-child(1){border-color:transparent #F2911E transparent transparent}
.hub-rings span:nth-child(2){border-color:transparent transparent #5FB137 transparent;inset:5px;animation-duration:12s;animation-direction:reverse}
.hub-rings span:nth-child(3){border-color:#3B8BD0 transparent transparent transparent;inset:10px;animation-duration:8s}
@keyframes hub-spin{to{transform:rotate(360deg)}}
.hub-rlogo b{font-weight:600;font-size:14px;opacity:0;transition:opacity .3s}
.hub-rail:hover .hub-rlogo b{opacity:1}
.hub-ritem{display:flex;align-items:center;gap:15px;padding:13px 22px;color:#5A6278;
  cursor:pointer;transition:.2s;white-space:nowrap}
.hub-ritem:hover{color:#EEF1F8;background:rgba(255,255,255,.04)}
.hub-ritem.on{color:#EEF1F8} .hub-ritem.on svg{stroke:#F2911E}
.hub-ritem svg{width:20px;height:20px;flex:none;fill:none;stroke:currentColor;stroke-width:1.7}
.hub-ritem span{font-size:13.5px;font-weight:500;opacity:0;transition:opacity .3s}
.hub-rail:hover .hub-ritem span{opacity:1}
.hub-rfoot{margin-top:auto;padding:0 22px;white-space:nowrap}
.hub-rstat{font-family:'JetBrains Mono',monospace;font-size:10px;color:#5A6278;
  display:flex;align-items:center;gap:8px;opacity:0;transition:.3s}
.hub-rail:hover .hub-rstat{opacity:1}
.hub-rstat .d{width:6px;height:6px;border-radius:50%;background:#5FB137;
  box-shadow:0 0 8px #5FB137;animation:hub-pulse 2s infinite}
@keyframes hub-pulse{50%{opacity:.4}}

.hub-stage{position:absolute;inset:0;z-index:10;display:flex;flex-direction:column;
  align-items:center;justify-content:center;padding-left:74px}
.hub-title{text-align:center;margin-bottom:46px;opacity:0;animation:hub-up .8s var(--ease) .2s forwards}
.hub-title .eye{font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:4px;
  text-transform:uppercase;color:#5A6278;margin-bottom:14px}
.hub-title h1{font-size:42px;font-weight:700;letter-spacing:-1.6px;color:#EEF1F8}
@keyframes hub-up{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}

.hub-arena{display:flex;align-items:stretch;gap:38px;perspective:2200px}
.hub-card{position:relative;width:440px;border-radius:30px;cursor:pointer;overflow:hidden;
  background:linear-gradient(165deg,rgba(24,30,48,.82),rgba(9,12,22,.8));
  border:1px solid rgba(255,255,255,.1);-webkit-backdrop-filter:blur(16px);backdrop-filter:blur(16px);
  box-shadow:0 44px 90px -34px rgba(0,0,0,.9),inset 0 1px 0 rgba(255,255,255,.09);
  transform-style:preserve-3d;transition:transform .5s var(--ease),box-shadow .5s,border-color .5s;
  display:flex;flex-direction:column;opacity:0}
.hub-card.c1{animation:hub-pop 1s var(--ease) .4s forwards}
.hub-card.c2{animation:hub-pop 1s var(--ease) .54s forwards}
@keyframes hub-pop{from{opacity:0;transform:translateY(40px) scale(.94)}to{opacity:1;transform:none}}
.hub-sheen{position:absolute;inset:0;z-index:3;pointer-events:none;border-radius:26px;
  background:linear-gradient(160deg,rgba(255,255,255,.07),transparent 40%)}
.hub-card.c1:hover{border-color:transparent;
  box-shadow:0 56px 110px -34px rgba(242,145,30,.42),0 0 0 1px rgba(242,145,30,.5),inset 0 1px 0 rgba(255,255,255,.14)}
.hub-card.c2:hover{border-color:transparent;
  box-shadow:0 56px 110px -34px rgba(123,107,240,.5),0 0 0 1px rgba(123,107,240,.55),inset 0 1px 0 rgba(255,255,255,.14)}
.hub-radarbox{padding:44px 0 40px;display:grid;place-items:center;z-index:2}
.hub-radO{width:270px;height:270px;position:relative;transform:translateZ(30px);transition:transform .5s var(--ease)}
.hub-card:hover .hub-radO{transform:translateZ(60px) scale(1.06)}
.hub-radO svg{position:absolute;inset:0;width:100%;height:100%}
.hub-grid{stroke:rgba(255,255,255,.09);fill:none}
.hub-sweep,.hub-sweepfill{transform-origin:center;animation:hub-rsw 4s linear infinite}
.hub-card.c1 .hub-sweep{stroke:#F2911E} .hub-card.c2 .hub-sweep{stroke:#b7abff}
@keyframes hub-rsw{to{transform:rotate(360deg)}}
.hub-blip{opacity:0;animation:hub-bl 4s ease-out infinite}
@keyframes hub-bl{0%,100%{opacity:0}35%{opacity:1}}
.hub-plate{position:relative;z-index:2;padding:26px 30px 34px;border-top:1px solid rgba(255,255,255,.07);
  background:linear-gradient(180deg,rgba(255,255,255,.02),rgba(255,255,255,.045))}
.hub-htag{font-family:'JetBrains Mono',monospace;font-size:11.5px;letter-spacing:2px;
  text-transform:uppercase;margin-bottom:10px}
.hub-card.c1 .hub-htag{color:#ffc061} .hub-card.c2 .hub-htag{color:#b7abff}
.hub-plate h2{font-size:30px;font-weight:700;letter-spacing:-.8px;margin-bottom:20px}
.hub-stats{display:flex;gap:26px;margin-bottom:24px}
.hub-stats .n{font-weight:700;font-size:28px;letter-spacing:-.5px;font-variant-numeric:tabular-nums}
.hub-card.c1 .hub-stats .n{color:#F2911E} .hub-card.c2 .hub-stats .n{color:#b7abff}
.hub-stats .l{font-family:'JetBrains Mono',monospace;font-size:10.5px;color:#5A6278;
  text-transform:uppercase;margin-top:4px}
.hub-enter{display:flex;align-items:center;justify-content:center;gap:10px;font-weight:600;font-size:16.5px;
  padding:16px;border-radius:15px;border:1px solid rgba(255,255,255,.15);transition:.35s var(--ease)}
.hub-card.c1 .hub-enter{color:#ffc061} .hub-card.c2 .hub-enter{color:#b7abff}
.hub-card.c1:hover .hub-enter{background:#F2911E;color:#04060F;border-color:#F2911E}
.hub-card.c2:hover .hub-enter{background:#8B7BF5;color:#fff;border-color:#8B7BF5}
.hub-enter svg{width:17px;height:17px;fill:none;stroke:currentColor;stroke-width:2.3;transition:.35s}
.hub-card:hover .hub-enter svg{transform:translateX(5px)}
@media(max-width:980px){.hub-arena{flex-direction:column;gap:20px;overflow:auto;max-height:80vh}
  .hub-card{width:340px}.hub-title h1{font-size:32px}}
"""


_HUB_JS = r"""
export default function(component){
  const {data, parentElement, setTriggerValue} = component;
  const old = parentElement.querySelector('.hub'); if (old) old.remove();
  const d = data || {}, cap = d.captacao || {}, emd = d.emendas || {};
  const esc = s => String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const plural = (n, um, varios) => (Number(n) === 1 ? um : varios);
  const arrow = '<svg viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg>';

  function radarSVG(cls){
    const blips = cls === 'c1'
      ? [[172,78,0],[80,168,1.3],[176,158,2.5]]
      : [[92,78,0],[170,138,1.6],[98,170,2.8]];
    const cor = cls === 'c1' ? '#F2911E' : '#b7abff';
    let b = '';
    blips.forEach(function(p){ b += '<circle class="hub-blip" cx="'+p[0]+'" cy="'+p[1]+
      '" r="4" fill="'+cor+'" style="animation-delay:'+p[2]+'s"/>'; });
    return '<svg viewBox="0 0 246 246">' +
      '<circle class="hub-grid" cx="123" cy="123" r="118"/>' +
      '<circle class="hub-grid" cx="123" cy="123" r="80"/>' +
      '<circle class="hub-grid" cx="123" cy="123" r="43"/>' +
      '<line class="hub-grid" x1="123" y1="5" x2="123" y2="241"/>' +
      '<line class="hub-grid" x1="5" y1="123" x2="241" y2="123"/>' +
      '<line class="hub-sweep" x1="123" y1="123" x2="123" y2="5" stroke-width="2"/>' +
      '<circle cx="123" cy="123" r="3" fill="'+cor+'"/>' + b + '</svg>';
  }
  function statCells(arr){
    return arr.map(function(s){ return '<div><div class="n">'+esc(s[0])+'</div>'+
      '<div class="l">'+esc(s[1])+'</div></div>'; }).join('');
  }
  function card(cls, radar, tag, titulo, stats){
    return '<div class="hub-card '+cls+'" data-radar="'+radar+'">' +
      '<div class="hub-sheen"></div>' +
      '<div class="hub-radarbox"><div class="hub-radO">'+radarSVG(cls)+'</div></div>' +
      '<div class="hub-plate"><div class="hub-htag">'+esc(tag)+'</div>' +
      '<h2>'+esc(titulo)+'</h2><div class="hub-stats">'+statCells(stats)+'</div>' +
      '<div class="hub-enter">Entrar neste radar '+arrow+'</div></div></div>';
  }

  const root = document.createElement('div'); root.className = 'hub';
  root.innerHTML =
    '<canvas class="hub-stars"></canvas><div class="hub-planet"></div><div class="hub-atmo"></div>' +
    '<aside class="hub-rail"><div class="hub-rlogo">' +
    '<div class="hub-rings"><span></span><span></span><span></span></div><b>Futuro Cientista</b></div>' +
    '<div class="hub-ritem on"><svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/>' +
    '<rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>' +
    '<rect x="14" y="14" width="7" height="7" rx="1"/></svg><span>Central</span></div>' +
    '<div class="hub-ritem" data-radar="captacao"><svg viewBox="0 0 24 24"><path d="M3 21h18M5 21V7l8-4v18"/></svg>' +
    '<span>Captação Privada</span></div>' +
    '<div class="hub-ritem" data-radar="emendas"><svg viewBox="0 0 24 24"><path d="M6 3h12l3 6-9 12L3 9z"/></svg>' +
    '<span>Emendas</span></div>' +
    '<div class="hub-ritem" data-radar="prospeccao"><svg viewBox="0 0 24 24"><path d="M3 4h18l-7 8v6l-4 2v-8z"/></svg>' +
    '<span>Prospecção</span></div>' +
    '<div class="hub-rfoot"><div class="hub-rstat"><span class="d"></span>' + esc(d.status || '') + '</div></div></aside>' +
    '<div class="hub-stage"><div class="hub-title"><div class="eye">Central de Captação</div>' +
    '<h1>Escolha seu radar</h1></div><div class="hub-arena">' +
    card('c1', 'captacao', cap.tag || 'Setor 01 · Recursos privados', 'Captação Privada',
         [[cap.orgs, 'orgs'], [cap.novas, 'novas'], [cap.fontes, 'fontes']]) +
    card('c2', 'emendas', emd.tag || 'Setor 02 · Recursos públicos', 'Emendas Parlamentares',
         [[emd.deputados, plural(emd.deputados, 'deputado', 'deputados')],
          [emd.reunioes, plural(emd.reunioes, 'reunião', 'reuniões')],
          [emd.aprovadas, plural(emd.aprovadas, 'aprovada', 'aprovadas')]]) +
    '</div></div>';
  parentElement.appendChild(root);

  // cliques -> Python (card inteiro ou item da rail)
  root.addEventListener('click', function(e){
    const el = e.target.closest('[data-radar]');
    if (!el) { return; }
    const card = el.closest('.hub-card');
    if (card) { card.style.transition = 'transform .15s'; card.style.transform = 'scale(.97)'; }
    setTriggerValue('escolha', {radar: el.dataset.radar, n: Date.now()});
  });
  // tilt 3D nos cards
  root.querySelectorAll('.hub-card').forEach(function(c){
    c.addEventListener('mousemove', function(e){
      const r = c.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width - .5, py = (e.clientY - r.top) / r.height - .5;
      c.style.transform = 'rotateY(' + (px*10) + 'deg) rotateX(' + (-py*10) + 'deg) translateY(-8px)';
    });
    c.addEventListener('mouseleave', function(){ c.style.transform = ''; });
  });

  // canvas de estrelas — setInterval (o rAF-loop não roda no runtime do módulo v2)
  const cv = root.querySelector('.hub-stars'), g = cv.getContext('2d');
  let W, H, stars = [];
  function rz(){
    W = cv.width = innerWidth; H = cv.height = innerHeight; stars = [];
    const n = Math.min(220, W * H / 8000);
    for (let i = 0; i < n; i++) stars.push({x: Math.random()*W, y: Math.random()*H*.85,
      r: Math.random()*1.2+.3, b: Math.random(), s: Math.random()*.05+.01});
  }
  rz(); window.addEventListener('resize', rz);
  const iv = setInterval(function(){
    g.clearRect(0, 0, W, H);
    for (const s of stars){ s.b += s.s; const a = .25 + Math.abs(Math.sin(s.b))*.65;
      g.beginPath(); g.arc(s.x, s.y, s.r, 0, 7); g.fillStyle = 'rgba(255,255,255,'+a+')'; g.fill(); }
  }, 33);

  return function(){ clearInterval(iv); window.removeEventListener('resize', rz); root.remove(); };
}
"""


_HUB_CHROME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
/* No hub não há sidebar: some com ela e com o botão de expandir (o testid
   stSidebarCollapsedControl / stBaseButton-headerNoPadding é de versões antigas
   do Streamlit; na 1.58 o botão é stExpandSidebarButton). */
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="stExpandSidebarButton"],
button[data-testid="stBaseButton-headerNoPadding"]{display:none!important}
[data-testid="stMainBlockContainer"], .block-container{padding:0!important;max-width:100%!important}
.stApp{background:#04060F!important}
</style>
"""


_EMENDAS_V2_CSS = """
.em{display:flex;flex-direction:column;gap:22px;font-family:'Inter',system-ui,sans-serif;
  color:var(--ink,#F5F7FA);animation:em-fade .4s ease;--accent:#8B7BF0;--accent-dim:rgba(139,123,240,.13)}
@keyframes em-fade{from{opacity:0;transform:translateY(10px)}}
.em .mono{font-family:'JetBrains Mono',monospace}
.em .hero{display:grid;grid-template-columns:1.1fr .9fr;gap:22px}
@media (max-width:1000px){.em .hero{grid-template-columns:1fr}}
.em .lead-card{background:linear-gradient(150deg,var(--surface2,#1C222B),var(--surface,#161A21));
  border:1px solid var(--line,rgba(255,255,255,.06));border-radius:16px;padding:32px 34px;
  display:flex;flex-direction:column;justify-content:space-between;position:relative;overflow:hidden}
.em .lead-card::after{content:"";position:absolute;top:-40%;right:-10%;width:300px;height:300px;
  border-radius:50%;background:radial-gradient(circle,var(--accent-dim),transparent 70%)}
.em .hl-label{font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:1.2px;
  text-transform:uppercase;color:var(--muted,#A4AEBF);margin-bottom:14px;position:relative;z-index:1}
.em .hl-num{font-size:80px;font-weight:800;letter-spacing:-4px;line-height:.9;position:relative;z-index:1}
.em .hl-num .u{font-size:26px;font-weight:600;color:var(--muted,#A4AEBF);letter-spacing:-1px;margin-left:6px}
.em .hl-cap{font-size:15px;color:var(--muted,#A4AEBF);margin-top:10px;position:relative;z-index:1}
.em .hl-headline{position:relative;z-index:1;margin-top:24px;padding-top:22px;
  border-top:1px solid var(--line,rgba(255,255,255,.06))}
.em .hh-lbl{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:1px;
  text-transform:uppercase;color:var(--dim,#6B7688);margin-bottom:10px}
.em .hh-row{display:flex;align-items:center;gap:14px;cursor:pointer}
.em .hh-sc{font-weight:800;font-size:26px;color:#4ADE80;flex:none;font-variant-numeric:tabular-nums}
.em .hh-t{font-size:16px;font-weight:600;line-height:1.3}
.em .hh-m{font-size:12px;color:var(--dim,#6B7688);margin-top:4px}
.em .hh-dl{margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:600;
  padding:8px 12px;border-radius:8px;flex:none;white-space:nowrap}
.em .temp-card{background:var(--surface,#161A21);border:1px solid var(--line,rgba(255,255,255,.06));
  border-radius:16px;padding:26px 28px;display:flex;flex-direction:column}
.em .temp-card h3{font-size:16px;font-weight:600;margin:0 0 4px}
.em .ts{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--dim,#6B7688);
  margin-bottom:22px;letter-spacing:.5px}
.em .trow{display:flex;align-items:center;gap:14px;margin-bottom:18px;cursor:pointer;
  padding:6px 8px;margin-left:-8px;margin-right:-8px;border-radius:9px;transition:.15s}
.em .trow:hover{background:rgba(255,255,255,.04)}
.em .trow:hover .tn{color:var(--ink,#F5F7FA)}
.em .trow.on{background:rgba(139,123,240,.13);box-shadow:inset 0 0 0 1px rgba(139,123,240,.3)}
.em .trow.on .tn{color:var(--ink,#F5F7FA);font-weight:600}
.em .trow:last-child{margin-bottom:0}
/* blocos clicáveis: herói de articulação e KPIs com detalhe */
.em .hl-click{cursor:pointer;border-radius:10px;transition:.15s}
.em .hl-click:hover{background:rgba(255,255,255,.03)}
.em .kpi-click{cursor:pointer;transition:transform .18s cubic-bezier(.16,1,.3,1),border-color .18s}
.em .kpi-click:hover{transform:translateY(-3px);border-color:var(--line2,rgba(255,255,255,.12))}
.em .tdot{width:12px;height:12px;border-radius:50%;flex:none}
.em .tn{flex:1;font-size:14px;color:var(--muted,#A4AEBF);font-weight:500}
.em .tk{width:120px;height:9px;background:rgba(255,255,255,.05);border-radius:6px;overflow:hidden}
.em .tf{display:block;height:100%;border-radius:6px}
.em .tv{font-family:'JetBrains Mono',monospace;font-size:15px;font-weight:700;width:26px;text-align:right;flex:none}
.em .kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}
@media (max-width:1000px){.em .kpis{grid-template-columns:1fr 1fr}}
.em .kpi{position:relative;background:var(--surface,#161A21);border:1px solid var(--line,rgba(255,255,255,.06));
  border-radius:16px;padding:22px 24px;overflow:hidden;--c:#8B7BF0}
.em .kpi::before{content:"";position:absolute;inset:0;border-radius:16px;padding:1.5px;
  background:linear-gradient(145deg,var(--c),transparent 55%);
  -webkit-mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);
  -webkit-mask-composite:xor;mask-composite:exclude;opacity:.55}
.em .kpi::after{content:"";position:absolute;top:-30%;right:-15%;width:130px;height:130px;border-radius:50%;
  background:radial-gradient(circle,var(--c),transparent 70%);opacity:.10;pointer-events:none}
.em .kic{width:42px;height:42px;border-radius:12px;display:grid;place-items:center;margin-bottom:14px;
  position:relative;z-index:1;background:color-mix(in srgb,var(--c) 16%,transparent);
  border:1px solid color-mix(in srgb,var(--c) 30%,transparent)}
.em .kic svg{width:21px;height:21px;fill:none;stroke:var(--c);stroke-width:1.9}
.em .kl{font-family:'JetBrains Mono',monospace;font-size:11.5px;letter-spacing:.8px;text-transform:uppercase;
  color:var(--muted,#A4AEBF);position:relative;z-index:1}
.em .kv{font-weight:800;font-size:38px;letter-spacing:-1.5px;margin-top:10px;
  font-variant-numeric:tabular-nums;position:relative;z-index:1}
.em .kf{font-size:13px;color:var(--dim,#6B7688);margin-top:8px;position:relative;z-index:1}
.em .panel{background:var(--surface,#161A21);border:1px solid var(--line,rgba(255,255,255,.06));
  border-radius:16px;overflow:hidden}
.em .ph{padding:22px 26px 6px}
.em .ph h3{font-size:16px;font-weight:600;margin:0}
.em .psub{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--dim,#6B7688);
  margin-top:4px;letter-spacing:.5px}
.em .tr{display:grid;grid-template-columns:2.2fr 1fr 1fr 1.1fr .7fr auto;gap:16px;align-items:center;
  padding:15px 26px;border-top:1px solid var(--line,rgba(255,255,255,.06));cursor:pointer;transition:.15s}
.em .tr:hover{background:var(--hover,#222834)}
.em .tr.head{cursor:default;font-family:'JetBrains Mono',monospace;font-size:10.5px;letter-spacing:1px;
  text-transform:uppercase;color:var(--dim,#6B7688)}
.em .tr.head:hover{background:none}
.em .dep{display:flex;align-items:center;gap:13px;min-width:0}
.em .dep .tdot{width:9px;height:9px;border-radius:50%;flex:none}
.em .dep .nm{font-weight:600;font-size:14.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.em .dep .sub{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--dim,#6B7688);margin-top:2px}
.em .barcell{display:flex;align-items:center;gap:9px}
.em .bk{flex:1;height:7px;background:rgba(255,255,255,.06);border-radius:5px;overflow:hidden;min-width:32px}
.em .bf{display:block;height:100%;border-radius:5px}
.em .bv{font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:600;width:26px;flex:none;text-align:right}
.em .stpill{font-size:11.5px;font-weight:600;padding:5px 11px;border-radius:20px;width:fit-content;white-space:nowrap}
.em .temp-ic{font-size:19px;text-align:center}
.em .rarrow{color:var(--dim,#6B7688);transition:.2s}
.em .tr:hover .rarrow{color:#8B7BF0;transform:translateX(3px)}
.em .vazio{padding:40px 26px;text-align:center;color:var(--muted,#A4AEBF);font-size:14px}
/* cabeçalho de sub-tela + funil de negociação (kanban por temperatura) */
.em .em-head h2{font-size:20px;font-weight:700;letter-spacing:-.5px;color:var(--ink,#F5F7FA)}
.em .em-head p{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.5px;
  color:var(--dim,#6B7688);margin-top:4px}
.em .kanban{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;align-items:start}
@media (max-width:1000px){.em .kanban{grid-template-columns:1fr 1fr}}
.em .kcol{background:rgba(255,255,255,.02);border:1px solid var(--line,rgba(255,255,255,.06));
  border-radius:14px;padding:14px;display:flex;flex-direction:column}
.em .khead{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600;letter-spacing:.5px;
  text-transform:uppercase;margin-bottom:14px;display:flex;align-items:center;justify-content:space-between}
.em .kct{color:var(--dim,#6B7688)}
.em .kbody{display:flex;flex-direction:column;gap:9px;min-height:60px}
.em .kcard{position:relative;background:var(--surface,#161A21);border:1px solid var(--line,rgba(255,255,255,.06));
  border-radius:11px;padding:12px 12px 12px 15px;cursor:pointer;overflow:hidden;--c:#8B7BF0;
  transition:transform .15s cubic-bezier(.16,1,.3,1),border-color .15s}
.em .kcard::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--c)}
.em .kcard:hover{border-color:var(--line2,rgba(255,255,255,.12));transform:translateY(-2px)}
.em .kcard .kn{font-size:13.5px;font-weight:600;margin-bottom:3px}
.em .kcard .km{font-family:'JetBrains Mono',monospace;font-size:10.5px;color:var(--dim,#6B7688)}
.em .kvazio{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--dim,#6B7688);
  text-align:center;padding:10px;border:1px dashed var(--line2,rgba(255,255,255,.12));border-radius:9px}
/* SELO DE ESCOPO (Passo 3) — violeta é a cor-mãe do painel; três sub-selos da
   MESMA família, visualmente distintos: estadual (violeta), federal (azul-violeta),
   senador (magenta-violeta). Diz de qual escopo é cada parlamentar na capa geral. */
.em .selo{display:inline-block;font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:700;
  letter-spacing:.5px;text-transform:uppercase;padding:1px 6px;border-radius:20px;margin-right:7px;
  border:1px solid;vertical-align:middle;position:relative;top:-1px;white-space:nowrap}
.em .selo-estadual{color:#8B7BF0;background:rgba(139,123,240,.14);border-color:rgba(139,123,240,.42)}
.em .selo-federal{color:#5B9BD5;background:rgba(91,155,213,.14);border-color:rgba(91,155,213,.42)}
.em .selo-senador{color:#C08BF0;background:rgba(192,139,240,.14);border-color:rgba(192,139,240,.42)}
"""


_EMENDAS_V2_JS = r"""
export default function(component){
  const {data, parentElement, setTriggerValue} = component;
  const old = parentElement.querySelector('.em'); if (old) old.remove();
  const d = data || {}, deps = d.deps || [], modo = d.modo || 'visao';
  const esc = s => String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  // selo de escopo (Passo 3): violeta cor-mãe, sub-selo por escopo. Vazio se o
  // registro não trouxer escopo (mantém compatível com payloads antigos).
  const seloHTML = p => (p && p.escopo)
    ? '<span class="selo selo-' + esc(p.escopo) + '">' + esc(p.escopo_nome || p.escopo) + '</span>'
    : '';
  const root = document.createElement('div'); root.className = 'em';

  const ICON = {
    users: '<path d="M16 21v-2a4 4 0 0 0-8 0v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"/>',
    cal: '<path d="M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/>',
    check: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14M22 4 12 14.01l-3-3"/>',
    money: '<path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>'
  };

  function linhaDep(p, i){
    return '<div class="tr" data-i="' + i + '">' +
      '<div class="dep"><span class="tdot" style="background:' + p.temp_cor + ';box-shadow:0 0 8px ' + p.temp_cor +
      '"></span><div style="min-width:0"><div class="nm">' + esc(p.nome) + '</div>' +
      '<div class="sub">' + seloHTML(p) + esc(p.partido) + (p.prioridade ? ' · ' + esc(p.prioridade) : '') + '</div></div></div>' +
      '<div class="barcell"><span class="bk"><span class="bf" style="background:#8B7BF0;width:' +
      p.chance + '%"></span></span><span class="bv">' + p.chance + '</span></div>' +
      '<div class="barcell"><span class="bk"><span class="bf" style="background:#4ADE80;width:' +
      p.ader + '%"></span></span><span class="bv">' + p.ader + '</span></div>' +
      '<div><span class="stpill" style="background:' + p.status_cor + '22;color:' + p.status_cor + '">' +
      esc(p.status) + '</span></div>' +
      '<div class="temp-ic">' + p.temp_emoji + '</div><div class="rarrow">→</div></div>';
  }
  function tabelaHTML(titulo, sub){
    let rows = '';
    deps.forEach(function(p, i){ rows += linhaDep(p, i); });
    if (!deps.length) {
      rows = '<div class="vazio">Base de deputados não encontrada. Confira <b>data/deputados_estaduais.csv</b>.</div>';
    }
    return '<div class="panel"><div class="ph"><h3>' + esc(titulo) + '</h3>' +
      '<div class="psub">' + esc(sub) + '</div></div>' +
      '<div class="tr head"><div>Deputado</div><div>Chance emenda</div><div>Aderência PFC</div>' +
      '<div>Status</div><div>Temp.</div><div></div></div>' + rows + '</div>';
  }
  function kanbanHTML(){
    let cols = '';
    (d.temp_ordem || []).forEach(function(c){
      const membros = deps.map(function(p, i){ return {p: p, i: i}; })
        .filter(function(x){ return x.p.temp === c.nome; });
      let cards = '';
      membros.forEach(function(x){
        cards += '<div class="kcard" data-i="' + x.i + '" style="--c:' + c.cor + '">' +
          '<div class="kn">' + esc(x.p.nome) + '</div>' +
          '<div class="km">' + esc(x.p.partido) + ' · chance ' + x.p.chance + '</div></div>';
      });
      if (!membros.length) { cards = '<div class="kvazio">nenhum</div>'; }
      cols += '<div class="kcol"><div class="khead" style="color:' + c.cor + '">' +
        '<span>' + c.emoji + ' ' + esc(c.nome) + '</span><span class="kct">' + membros.length + '</span></div>' +
        '<div class="kbody">' + cards + '</div></div>';
    });
    return '<div class="em-head"><h2>Funil de negociação</h2>' +
      '<p class="mono">DEPUTADOS POR TEMPERATURA · CLIQUE NUM CARD PARA O DOSSIÊ</p></div>' +
      '<div class="kanban">' + cols + '</div>';
  }

  if (modo === 'visao') {
    // hero
    const h = d.hero || {}, top = h.top;
    let topHtml = '';
    if (top) {
      topHtml = '<div class="hh-row" data-act="top"><span class="hh-sc">' + esc(top.score) +
        '</span><div style="min-width:0"><div class="hh-t">' + esc(top.nome) + '</div>' +
        '<div class="mono hh-m">' + seloHTML(top) + esc(top.partido) + ' · ' + esc(top.status) + '</div></div>' +
        '<span class="hh-dl" style="color:' + top.cor + ';background:' + top.cor + '1a;border:1px solid ' +
        top.cor + '4d">' + esc(top.temp).toUpperCase() + '</span></div>';
    }
    const lead = '<div class="lead-card"><div class="hl-click" data-act="articulacao">' +
      '<div class="hl-label">Deputados em articulação</div>' +
      '<div class="hl-num tnum"><span data-c="' + (h.articulacao || 0) + '">0</span>' +
      '<span class="u">de ' + (h.total || 0) + '</span></div>' +
      '<div class="hl-cap">com contato iniciado · ' + (h.nao_abordados || 0) + ' ainda não abordados</div></div>' +
      '<div class="hl-headline"><div class="hh-lbl">Negociação mais avançada</div>' + topHtml + '</div></div>';
    let trows = '';
    (d.temperatura || []).forEach(function(t){
      const on = (d.filtro_temp === t.nome);
      trows += '<div class="trow' + (on ? ' on' : '') + '" data-act="temp" data-t="' + esc(t.nome) +
        '"><span class="tdot" style="background:' + t.cor + '"></span>' +
        '<span class="tn">' + t.emoji + ' ' + esc(t.nome) + '</span>' +
        '<span class="tk"><span class="tf" style="background:' + t.cor + ';width:' + t.pct + '%"></span></span>' +
        '<span class="tv">' + t.n + '</span></div>';
    });
    const temp = '<div class="temp-card"><h3>Temperatura das negociações</h3>' +
      '<div class="ts">CLIQUE NUMA FAIXA PARA FILTRAR A TABELA</div>' + trows + '</div>';
    root.innerHTML = '<div class="hero">' + lead + temp + '</div>';
    let kpis = '';
    (d.kpis || []).forEach(function(k){
      const val = (k.suffix != null)
        ? '<div class="kv">' + esc(k.val) + '<span style="font-size:20px;color:var(--muted,#A4AEBF)">' + k.suffix + '</span></div>'
        : '<div class="kv tnum" data-c="' + k.val + '">0</div>';
      kpis += '<div class="kpi' + (k.k ? ' kpi-click' : '') + '" style="--c:' + k.c + '"' +
        (k.k ? ' data-act="kpi" data-k="' + k.k + '"' : '') +
        '><div class="kic"><svg viewBox="0 0 24 24">' +
        (ICON[k.icon] || '') + '</svg></div><div class="kl">' + esc(k.lab) + '</div>' + val +
        '<div class="kf"' + (k.foot_cor ? ' style="color:' + k.foot_cor + '"' : '') + '>' + esc(k.foot) + '</div></div>';
    });
    root.insertAdjacentHTML('beforeend', '<div class="kpis">' + kpis + '</div>');
    root.insertAdjacentHTML('beforeend',
      tabelaHTML('Deputados por prioridade', 'ORDENADOS POR SCORE INTEGRADO · CLIQUE PARA ABRIR O DOSSIÊ'));
  } else if (modo === 'deputados') {
    root.insertAdjacentHTML('beforeend',
      tabelaHTML('Todos os deputados', (d.total || deps.length) + ' DEPUTADOS · ALESP · CLIQUE PARA ABRIR O DOSSIÊ'));
  } else if (modo === 'funil') {
    root.insertAdjacentHTML('beforeend', kanbanHTML());
  }

  parentElement.appendChild(root);

  root.addEventListener('click', function(e){
    const act = e.target.closest('[data-act]');
    if (act) {
      setTriggerValue('acao', {t: act.dataset.act, k: act.dataset.k || null,
                               temp: act.dataset.t || null, n: Date.now()});
      return;
    }
    const el = e.target.closest('[data-i]');
    if (!el) { return; }
    setTriggerValue('acao', {t: 'dep', i: +el.dataset.i, n: Date.now()});
  });
  // animações (setInterval/timeout — rAF-loop não roda no runtime v2)
  root.querySelectorAll('[data-c]').forEach(function(el){
    const alvo = +el.dataset.c; const t0 = Date.now(), dur = 900;
    const iv = setInterval(function(){
      const p = Math.min(1, (Date.now() - t0) / dur);
      el.textContent = String(Math.round(alvo * (1 - Math.pow(1 - p, 3))));
      if (p >= 1) { clearInterval(iv); }
    }, 16);
  });
  // barras (termômetro/chance/aderência) já vêm com width no HTML; o "crescer"
  // é keyframe scaleX (transition:width trava o computed no shadow DOM do v2).
  return function(){ root.remove(); };
}
"""


_EMENDAS_CHROME_CSS = """
<style>
/* item ativo da sidebar em violeta (sobrescreve o âmbar do tema global) */
[data-testid="stSidebar"] .stButton>button[kind="primary"]{
  background:rgba(139,123,240,.15)!important;
  box-shadow:inset 0 0 0 1px rgba(139,123,240,.28)!important}
[data-testid="stSidebar"] .stButton>button[kind="primary"]:hover{
  background:rgba(139,123,240,.22)!important}
[data-testid="stSidebar"] .stButton>button[kind="primary"]::before{
  background:#8B7BF0!important;box-shadow:0 0 10px #8B7BF0!important}
.em-brand .bt small{color:#8B7BF0!important}
.em-rings span:nth-child(1){border-color:transparent #8B7BF0 transparent transparent!important}
.em-rings span:nth-child(3){border-color:#5B9BD5 transparent transparent transparent!important}
.topbar .cr b{color:#8B7BF0}
.topbar .live{color:#8B7BF0;background:rgba(139,123,240,.12);border-color:rgba(139,123,240,.3)}
.topbar .avatar2{background:linear-gradient(135deg,#8B7BF0,#c0b5ff)}
/* itens de Escopo (informativos). Vivem num st.markdown só, então o gap do
   stVerticalBlock não os alcança: o respiro vem do margin-bottom, alinhado
   com os 6px de gap dos botões acima para o ritmo não quebrar na metade. */
.esc-item{display:flex;align-items:center;gap:11px;padding:10px 14px;border-radius:9px;
  font-size:13.5px;font-weight:500;margin-bottom:6px;position:relative}
.esc-item:last-child{margin-bottom:0}
.esc-item .ic{width:17px;height:17px;flex:none;opacity:.92}
.esc-item .esc-leg{margin-left:auto;font-family:var(--mono);font-size:10px;
  letter-spacing:.4px;text-transform:uppercase}
.esc-item.esc-on{background:rgba(139,123,240,.13);color:var(--ink);
  box-shadow:inset 0 0 0 1px rgba(139,123,240,.28)}
.esc-item.esc-on::before{content:"";position:absolute;left:0;top:6px;bottom:6px;width:3px;
  border-radius:0 3px 3px 0;background:#8B7BF0;box-shadow:0 0 10px #8B7BF0}
.esc-item.esc-on .esc-leg{color:#8B7BF0}
.esc-item.esc-off{color:var(--dim);opacity:.6}
.esc-item.esc-off .esc-leg{color:var(--dim)}
/* modo ÍCONE (padrão): fica só o SVG, centralizado. O nome vem do title nativo
   — aqui não dá para usar o balão em ::after, que já é a barrinha do item ativo. */
.esc-item{justify-content:center;padding:10px 0;gap:0}
.esc-item .esc-nome, .esc-item .esc-leg{display:none}
/* ====== Control de ESCOPO — pill tabs escuras (Opção A, flat) ======
   Escopado por .st-key-emenda_escopo_filtro: mira SÓ o segmented_control de escopo
   das Emendas (os 5 usos compartilham a key e só um renderiza por vez). Puro estilo
   — o widget st.segmented_control e a chave emenda_escopo_filtro seguem intactos.
   Validado no DOM do Streamlit 1.58 (ativo=kind segmented_controlActive; opções em
   button:nth-of-type 1..4 = Geral/Estadual/Federal/Senador). */
.st-key-emenda_escopo_filtro [data-testid="stButtonGroup"]>div{
  display:inline-flex;gap:2px;background:#1a1a24;border:none;border-radius:12px;padding:4px}
.st-key-emenda_escopo_filtro [data-testid="stButtonGroup"] button{
  border:none!important;box-shadow:none!important;background:transparent!important;
  color:#9a97b5!important;font-weight:400!important;border-radius:9px!important;
  padding:6px 13px!important;min-height:0!important}
.st-key-emenda_escopo_filtro [data-testid="stButtonGroup"] button:hover{
  background:#ffffff10!important;color:#c9c6e0!important}
.st-key-emenda_escopo_filtro [data-testid="stButtonGroup"] button[kind="segmented_controlActive"]{
  background:#8B7BF0!important;color:#17123a!important;font-weight:500!important}
.st-key-emenda_escopo_filtro [data-testid="stButtonGroup"] button[kind="segmented_controlActive"]:hover{
  background:#8B7BF0!important;color:#17123a!important}
/* ponto colorido (8px) antes do label — só nas pills INATIVAS; "Geral" (1ª) não tem */
.st-key-emenda_escopo_filtro [data-testid="stButtonGroup"] button[kind="segmented_control"]:nth-of-type(2)::before,
.st-key-emenda_escopo_filtro [data-testid="stButtonGroup"] button[kind="segmented_control"]:nth-of-type(3)::before,
.st-key-emenda_escopo_filtro [data-testid="stButtonGroup"] button[kind="segmented_control"]:nth-of-type(4)::before{
  content:"";flex:0 0 auto;width:8px;height:8px;border-radius:50%;margin-right:7px}
.st-key-emenda_escopo_filtro [data-testid="stButtonGroup"] button[kind="segmented_control"]:nth-of-type(2)::before{background:#8B7BF0}
.st-key-emenda_escopo_filtro [data-testid="stButtonGroup"] button[kind="segmented_control"]:nth-of-type(3)::before{background:#5B9BD5}
.st-key-emenda_escopo_filtro [data-testid="stButtonGroup"] button[kind="segmented_control"]:nth-of-type(4)::before{background:#C08BF0}
</style>
"""


_SIDEBAR_FIX_JS = """
<script>
(function(){
  var P = window.parent; if(!P || !P.document){ return; }
  function visivel(){
    var sb = P.document.querySelector('[data-testid="stSidebar"]');
    if(!sb){ return false; }
    var r = sb.getBoundingClientRect();
    return r.left >= 0 && r.width > 100;
  }
  var n = 0;
  var iv = setInterval(function(){
    n++;
    if(visivel() || n > 25){ clearInterval(iv); return; }
    var btn = P.document.querySelector('[data-testid="stExpandSidebarButton"]');
    if(btn){ btn.click(); }
  }, 180);
})();
</script>
"""


_SIDEBAR_OPEN_CSS = """
<style>
html.pfc-sb-open [data-testid="stSidebar"]{
  width:250px!important;min-width:250px!important;max-width:250px!important}
html.pfc-sb-open [data-testid="stSidebar"]>div:first-child{padding-left:14px!important;padding-right:14px!important}
/* controle de recolher no topo: no modo expandido, ícone «-recolher + rótulo, à esquerda */
html.pfc-sb-open [data-testid="stSidebar"] .pfc-sb-toggle{justify-content:flex-start;padding:9px 11px}
html.pfc-sb-open [data-testid="stSidebar"] .pfc-sb-toggle .pfc-ic-abrir{display:none}
html.pfc-sb-open [data-testid="stSidebar"] .pfc-sb-toggle .pfc-ic-fechar{display:block}
html.pfc-sb-open [data-testid="stSidebar"] .pfc-sb-toggle .pfc-sb-toggle-lbl{display:inline;
  font-family:'Inter',system-ui,sans-serif;font-size:12.5px;font-weight:600;letter-spacing:.2px}
/* devolve o texto dos botões e alinha à esquerda */
html.pfc-sb-open [data-testid="stSidebar"] .stButton>button{justify-content:flex-start!important;
  padding:10px 14px!important}
html.pfc-sb-open [data-testid="stSidebar"] .stButton>button [data-testid="stMarkdownContainer"]>p{display:block!important}
/* com o nome à vista, o tooltip vira ruído */
html.pfc-sb-open [data-testid="stSidebar"] .stButton>button::after{display:none!important}
/* marca, cabeçalho de seção e rodapé voltam ao formato com texto */
html.pfc-sb-open [data-testid="stSidebar"] .sb-brand{justify-content:flex-start;padding:2px 8px 14px}
html.pfc-sb-open [data-testid="stSidebar"] .sb-brand .bt{display:block}
html.pfc-sb-open [data-testid="stSidebar"] .sb-sec{height:auto;padding:22px 8px 9px;margin:0;background:none;
  font-size:10.5px;letter-spacing:1.4px;overflow:visible}
html.pfc-sb-open [data-testid="stSidebar"] .sb-foot{margin-top:26px;padding:16px 8px 6px}
html.pfc-sb-open [data-testid="stSidebar"] .sf{justify-content:flex-start;font-size:11px;gap:9px}
/* Escopo (só Emendas): volta o nome e a legenda */
html.pfc-sb-open [data-testid="stSidebar"] .esc-item{justify-content:flex-start;padding:10px 14px;gap:11px}
html.pfc-sb-open [data-testid="stSidebar"] .esc-item .esc-nome{display:inline}
html.pfc-sb-open [data-testid="stSidebar"] .esc-item .esc-leg{display:inline;margin-left:auto}
</style>
"""


_SIDEBAR_TOGGLE_CORE = r"""
(function(){
  if (window.__pfcSbCoreOn) { return; }   // idempotente no realm do pai
  window.__pfcSbCoreOn = true;
  var doc = document, html = document.documentElement, DUR = 260, CLS = 'pfc-sb-open';
  function sb(){ return doc.querySelector('[data-testid="stSidebar"]'); }
  function inl(s, w){
    if(w == null){ s.style.removeProperty('width'); s.style.removeProperty('min-width'); s.style.removeProperty('max-width'); return; }
    s.style.setProperty('width', w + 'px', 'important');
    s.style.setProperty('min-width', w + 'px', 'important');
    s.style.setProperty('max-width', w + 'px', 'important');
  }
  function toggle(){
    var s = sb(); if(!s || window.__pfcSbAnim){ return; }
    var w0 = Math.round(s.getBoundingClientRect().width);
    var abrir = !html.classList.contains(CLS), para = abrir ? 250 : 60;
    s.style.setProperty('transition', 'none', 'important');   // anima por timer, não por CSS
    inl(s, w0);                              // congela na largura atual
    html.classList.toggle(CLS, abrir);       // conteúdo/ícone/rótulo (CSS) + largura de descanso
    window.__pfcSbAnim = true;
    var ini = Date.now();
    var iv = setInterval(function(){         // timer no realm do PAI (persistente)
      var p = Math.min(1, (Date.now() - ini) / DUR);
      var e = 1 - Math.pow(1 - p, 3);        // easeOutCubic
      inl(s, Math.round(w0 + (para - w0) * e));
      if(p >= 1){ clearInterval(iv); window.__pfcSbAnim = false; inl(s, null); }
    }, 16);
  }
  // DELEGAÇÃO: o botão .pfc-sb-toggle é recriado pelo React a cada render, mas o
  // clique (inclusive no ícone interno) sempre borbulha até este listener do pai.
  doc.addEventListener('click', function(e){
    var alvo = (e.target && e.target.closest) ? e.target.closest('.pfc-sb-toggle') : null;
    if(alvo){ e.preventDefault(); toggle(); }
  }, true);
})();
"""


_SIDEBAR_TOGGLE_JS = (
    "<script>\n(function(){\n"
    "  var P = window.parent; if(!P || !P.document){ return; }\n"
    "  if(P.__pfcSbInstalled){ return; }\n"
    "  P.__pfcSbInstalled = true;\n"
    "  var sc = P.document.createElement('script');\n"
    "  sc.textContent = " + json.dumps(_SIDEBAR_TOGGLE_CORE) + ";\n"
    "  P.document.head.appendChild(sc);\n"
    "})();\n</script>"
)


_DESCOBRIR_CSS = """
<style>
.dd-intro{font-size:13.5px;color:var(--muted);margin:2px 0 4px;max-width:70ch}
.dd-legend{display:flex;gap:18px;flex-wrap:wrap;font-size:11.5px;color:var(--muted);
  margin:10px 0 16px;font-family:var(--mono);letter-spacing:.2px}
.dd-legend span{display:flex;align-items:center;gap:6px}
.dd-legend .sw{width:9px;height:9px;border-radius:3px;display:inline-block}
.dd-sec{font-family:var(--mono);font-size:11px;letter-spacing:1px;text-transform:uppercase;
  color:var(--dim);margin:20px 0 10px;display:flex;align-items:center;gap:10px}
.dd-sec b{color:#b7abff;font-weight:600}
.dd-sec .ln{flex:1;height:1px;background:var(--line)}
/* Linha-card violeta CLICÁVEL por inteiro. O truque: um botão transparente
   (chave dd_) é posicionado sobre a linha toda e captura o clique -> abre o
   dossiê. O botão "Puxar" (chave crm_) fica com z-index maior, então continua
   sendo a exceção clicável. Mesmo tratamento visual dos glowcards do painel. */
[data-testid="stHorizontalBlock"]:has(.dd-cell){
  position:relative;overflow:hidden;box-sizing:border-box;cursor:pointer;
  background:var(--surface);border:1px solid var(--line);border-left:3px solid #8B7BF0;
  border-radius:14px;padding:8px 10px 8px 16px;margin-bottom:10px;min-height:62px;
  align-items:stretch;box-shadow:var(--sh-1);
  transition:transform .18s var(--ease),border-color .18s var(--ease),box-shadow .18s var(--ease)}
[data-testid="stHorizontalBlock"]:has(.dd-cell)::after{content:"";position:absolute;
  top:-45%;right:-6%;width:150px;height:150px;border-radius:50%;pointer-events:none;opacity:0;
  background:radial-gradient(circle,rgba(139,123,240,.18),transparent 70%);
  transition:opacity .2s var(--ease)}
[data-testid="stHorizontalBlock"]:has(.dd-cell):hover{transform:translateY(-2px);
  border-color:rgba(139,123,240,.5);box-shadow:0 8px 22px -6px rgba(139,123,240,.24)}
[data-testid="stHorizontalBlock"]:has(.dd-cell):hover::after{opacity:1}
/* colunas com a mesma altura; conteúdo centrado */
[data-testid="stHorizontalBlock"]:has(.dd-cell)>[data-testid="stColumn"]{display:flex;flex-direction:column}
[data-testid="stHorizontalBlock"]:has(.dd-cell) [data-testid="stVerticalBlock"]{flex:1;justify-content:center}
/* OVERLAY: o container do botão dd_ cobre a linha inteira, invisível mas clicável */
[data-testid="stHorizontalBlock"]:has(.dd-cell) [class*="st-key-dd_"]{
  position:absolute;inset:0;z-index:4;margin:0;padding:0}
[data-testid="stHorizontalBlock"]:has(.dd-cell) [class*="st-key-dd_"] .stButton,
[data-testid="stHorizontalBlock"]:has(.dd-cell) [class*="st-key-dd_"] button{
  height:100%;width:100%;min-height:0;border:none;background:transparent;box-shadow:none}
[data-testid="stHorizontalBlock"]:has(.dd-cell) [class*="st-key-dd_"] button{opacity:0;cursor:pointer}
/* o botão Puxar fica ACIMA do overlay -> continua clicável (a exceção) */
[data-testid="stHorizontalBlock"]:has(.dd-cell) [class*="st-key-crm_"]{position:relative;z-index:5}
/* card = flex horizontal de 3 células (nome | score | autorizado) */
.dd-cell{min-width:0;display:flex;align-items:center;gap:20px}
.dd-nomecol{flex:3;min-width:0} .dd-scorecol{flex:0 0 60px} .dd-valcol{flex:2.2;min-width:0}
.dd-nomecol,.dd-scorecol,.dd-valcol{display:flex;flex-direction:column;justify-content:center;gap:3px}
.dd-top{display:flex;align-items:center;min-width:0;white-space:nowrap;overflow:hidden}
.dd-nome{font-weight:700;font-size:14.5px;color:var(--ink);overflow:hidden;text-overflow:ellipsis}
.dd-sub{font-family:var(--mono);font-size:11px;color:var(--dim);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dd-fabio{font-size:9.5px;font-weight:600;padding:2px 8px;border-radius:20px;vertical-align:middle;
  background:rgba(139,123,240,.16);color:#b7abff;margin-left:9px;letter-spacing:.3px}
/* SELO DE ESCOPO na Descobrir (Passo 4) — mesmas cores da capa: violeta cor-mãe,
   sub-selos distintos. Diz de qual escopo é o card (e, por tabela, que tipo de
   valor ele mostra: estadual=execução aut/pago, federal=valor sugerido). */
.dd-selo{font-family:var(--mono);font-size:9px;font-weight:700;letter-spacing:.4px;text-transform:uppercase;
  padding:2px 7px;border-radius:20px;margin-right:8px;border:1px solid;white-space:nowrap;flex:none}
.dd-selo-estadual{color:#8B7BF0;background:rgba(139,123,240,.14);border-color:rgba(139,123,240,.42)}
.dd-selo-federal{color:#5B9BD5;background:rgba(91,155,213,.14);border-color:rgba(91,155,213,.42)}
.dd-selo-senador{color:#C08BF0;background:rgba(192,139,240,.14);border-color:rgba(192,139,240,.42)}
.dd-score{font-family:var(--disp);font-weight:700;font-size:22px;line-height:1.1}
.dd-val{font-size:13px;color:var(--text-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dd-val b{font-family:var(--disp);color:var(--ink)}
/* boxes do dossiê */
.dd-box{background:var(--surface2);border:1px solid var(--line);border-radius:12px;padding:15px 16px}
.dd-box.aut{border-left:3px solid #8B7BF0} .dd-box.pago{border-left:3px solid var(--sem-high)}
.dd-box .k{font-family:var(--mono);font-size:9.5px;letter-spacing:.7px;text-transform:uppercase;color:var(--dim)}
.dd-box .v{font-family:var(--disp);font-size:23px;font-weight:800;margin-top:7px}
.dd-box .n{font-size:11px;color:var(--muted);margin-top:4px}
</style>
"""


_ORFAOS_CSS = """
<style>
.orf-card{background:linear-gradient(135deg,rgba(139,123,240,.10),rgba(139,123,240,.02));
  border:1px solid rgba(139,123,240,.30);border-left:3px solid #8B7BF0;border-radius:14px;
  padding:18px 20px;margin:16px 0}
.orf-h{display:flex;align-items:center;gap:10px;font-size:18px;font-weight:700;color:var(--ink)}
/* trava o tamanho do pin: SVG sem width/height fixo estica e vira fundo gigante
   no runtime dos componentes v2. flex:none impede o flex de alongá-lo. */
.orf-h svg{width:20px;height:20px;flex:none}
.orf-sub{font-family:var(--mono);font-size:11px;letter-spacing:.4px;color:var(--dim);
  margin-top:6px;text-transform:uppercase}
.orf-msg{font-size:13.5px;color:var(--muted);margin:12px 0 4px}
.orf-cand{display:flex;align-items:center;justify-content:space-between;gap:12px;
  background:var(--surface2);border:1px solid var(--line);border-radius:10px;
  padding:10px 14px;margin-top:8px}
.orf-cand .nome{font-weight:600;color:var(--ink);font-size:14px}
.orf-cand .sub{font-family:var(--mono);font-size:11px;color:var(--dim);margin-top:2px}
.orf-val{text-align:right;font-size:12.5px;color:var(--ink);white-space:nowrap}
.orf-val b{color:#b7abff}
.orf-none{font-size:13.5px;color:var(--muted);background:var(--surface2);
  border:1px dashed var(--line2);border-radius:10px;padding:12px 14px;margin-top:8px}
</style>
"""


_ORF_PIN = ("<svg width='20' height='20' viewBox='0 0 24 24' fill='none' "
            "stroke='#b7abff' stroke-width='1.8' stroke-linecap='round' "
            "stroke-linejoin='round' style='flex:none'>" + ICONES["local"] + "</svg>")


TOPNAV_ALTURA = 54


_TOPNAV_CSS = """
.tn{position:fixed;top:0;left:0;right:0;height:54px;z-index:1000;
  display:flex;align-items:center;justify-content:space-between;gap:16px;padding:0 22px;
  background:rgba(22,26,33,.86);-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);
  border-bottom:1px solid var(--line,rgba(255,255,255,.06));
  font-family:'Inter',system-ui,sans-serif;--acc:#E8873A;--acc-soft:rgba(232,135,58,.14)}
.tn *{box-sizing:border-box}
.tn-left{display:flex;align-items:center;gap:13px;min-width:0}
.tn-crumb{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.8px;
  color:var(--dim,#6B7688);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tn-crumb b{color:var(--acc);font-weight:600}
.tn-right{display:flex;align-items:center;gap:14px;flex:none}

/* seletor (pill que abre o menu) */
.tn-sel{position:relative}
.tn-pill{display:flex;align-items:center;gap:10px;height:38px;padding:0 12px 0 13px;
  background:var(--acc-soft);border:1px solid color-mix(in srgb,var(--acc) 34%,transparent);
  border-radius:10px;cursor:pointer;transition:.18s cubic-bezier(.16,1,.3,1);
  font-family:'Inter',system-ui,sans-serif;color:var(--ink,#F5F7FA)}
.tn-pill:hover{background:color-mix(in srgb,var(--acc) 20%,transparent);
  border-color:color-mix(in srgb,var(--acc) 55%,transparent)}
.tn-dot{width:8px;height:8px;border-radius:50%;background:var(--acc);
  box-shadow:0 0 8px var(--acc);flex:none}
.tn-name{font-size:13.5px;font-weight:600;white-space:nowrap}
.tn-chev{width:15px;height:15px;flex:none;fill:none;stroke:var(--muted,#A4AEBF);stroke-width:2;
  transition:transform .2s}
.tn.open .tn-chev{transform:rotate(180deg)}

/* menu dropdown — controlado por display (visibility+transition tinha
   comportamento anômalo no shadow DOM do componente v2) */
.tn-menu{display:none;position:absolute;top:46px;right:0;width:248px;padding:7px;
  background:#1C222B;border:1px solid var(--line2,rgba(255,255,255,.12));border-radius:13px;
  box-shadow:0 24px 60px -18px rgba(0,0,0,.75),inset 0 1px 0 rgba(255,255,255,.05);
  transform-origin:top right;z-index:1001}
.tn.open .tn-menu{display:block;animation:tn-in .18s cubic-bezier(.16,1,.3,1)}
@keyframes tn-in{from{opacity:0;transform:translateY(-6px) scale(.98)}to{opacity:1;transform:none}}
.tn-lbl{font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:1.2px;
  text-transform:uppercase;color:var(--dim,#6B7688);padding:8px 10px 6px}
.tn-item{display:flex;align-items:center;gap:11px;width:100%;padding:9px 10px;border:none;
  background:none;border-radius:9px;cursor:pointer;color:var(--muted,#A4AEBF);
  font-family:'Inter',system-ui,sans-serif;font-size:13.5px;font-weight:500;text-align:left;
  transition:.14s}
.tn-item:hover{background:rgba(255,255,255,.055);color:var(--ink,#F5F7FA)}
.tn-item .rdot{width:8px;height:8px;border-radius:50%;flex:none}
.tn-item .rdot.amber{background:#E8873A;box-shadow:0 0 7px rgba(232,135,58,.7)}
.tn-item .rdot.violet{background:#8B7BF0;box-shadow:0 0 7px rgba(139,123,240,.7)}
.tn-item .nm{flex:1}
.tn-item .ck{width:15px;height:15px;flex:none;fill:none;stroke:var(--acc);stroke-width:2.4}
.tn-item svg.ic{width:16px;height:16px;flex:none;fill:none;stroke:currentColor;stroke-width:1.8}
.tn-item.cur{color:var(--ink,#F5F7FA);font-weight:600}
.tn-item.danger:hover{background:rgba(240,102,63,.12);color:#F0663F}
.tn-sep{height:1px;background:var(--line,rgba(255,255,255,.07));margin:6px 4px}

.tn-avatar{width:36px;height:36px;border-radius:10px;display:grid;place-items:center;
  font-weight:700;font-size:13.5px;color:#15161F;flex:none;
  background:linear-gradient(135deg,var(--acc),color-mix(in srgb,var(--acc) 40%,#ffffff))}
"""


_TOPNAV_JS = r"""
export default function(component){
  const {data, parentElement, setTriggerValue} = component;
  const old = parentElement.querySelector('.tn'); if (old) old.remove();
  const d = data || {}, radar = d.radar || 'captacao';
  const esc = s => String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  const acc = radar === 'emendas' ? '#8B7BF0' : '#E8873A';
  const accSoft = radar === 'emendas' ? 'rgba(139,123,240,.14)' : 'rgba(232,135,58,.14)';
  const nomeAtual = radar === 'emendas' ? 'Emendas Parlamentares' : 'Captação Privada';
  const ck = '<svg class="ck" viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5"/></svg>';
  const chev = '<svg class="tn-chev" viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg>';
  const iHub = '<svg class="ic" viewBox="0 0 24 24"><path d="M3 12l9-9 9 9M5 10v10h14V10"/></svg>';
  const iOut = '<svg class="ic" viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>';

  const root = document.createElement('div');
  root.className = 'tn';
  root.style.setProperty('--acc', acc);
  root.style.setProperty('--acc-soft', accSoft);

  function item(radarKey, label, cls){
    const atual = radarKey === radar;
    return '<button class="tn-item' + (atual ? ' cur' : '') + '" data-act="radar" data-v="' + radarKey + '">' +
      '<span class="rdot ' + cls + '"></span><span class="nm">' + label + '</span>' +
      (atual ? ck : '') + '</button>';
  }

  // A sidebar é recolhida/expandida pela SETINHA na borda da própria barra
  // (client-side puro, sem rerun — ver _SIDEBAR_TOGGLE_JS), não mais por aqui.
  root.innerHTML =
    '<div class="tn-left">' +
    '<div class="tn-crumb"><b>' + esc((nomeAtual || '').toUpperCase()) + '</b>' +
    (d.crumb ? ' · ' + esc(d.crumb) : '') + '</div></div>' +
    '<div class="tn-right"><div class="tn-sel">' +
    '<button class="tn-pill" data-act="toggle"><span class="tn-dot"></span>' +
    '<span class="tn-name">' + esc(nomeAtual) + '</span>' + chev + '</button>' +
    '<div class="tn-menu">' +
    '<div class="tn-lbl">Radar</div>' +
    item('captacao', 'Captação Privada', 'amber') +
    item('emendas', 'Emendas Parlamentares', 'violet') +
    '<div class="tn-sep"></div>' +
    '<button class="tn-item" data-act="hub">' + iHub + '<span class="nm">Voltar à Central</span></button>' +
    '<button class="tn-item danger" data-act="sair">' + iOut + '<span class="nm">Sair</span></button>' +
    '</div></div>' +
    '<span class="tn-avatar" title="' + esc(d.email || '') + '">' + esc(d.inicial || '') + '</span>' +
    '</div>';
  parentElement.appendChild(root);

  function fechar(){ root.classList.remove('open'); }
  root.addEventListener('click', function(e){
    const el = e.target.closest('[data-act]');
    if (!el) { return; }
    const act = el.dataset.act;
    if (act === 'toggle') { root.classList.toggle('open'); return; }
    fechar();
    setTriggerValue('acao', {t: act, v: el.dataset.v || null, n: Date.now()});
  });
  // fecha ao clicar fora — composedPath() enxerga através do shadow DOM, senão o
  // alvo chega ao document reapontado para o host e fecharíamos no próprio clique.
  const onDoc = function(e){
    const path = e.composedPath ? e.composedPath() : [];
    if (path.indexOf(root) !== -1) { return; }  // clique dentro do componente
    fechar();
  };
  document.addEventListener('click', onDoc, true);

  return function(){ document.removeEventListener('click', onDoc, true); root.remove(); };
}
"""


_TOPNAV_OFFSET_CSS = f"""
<style>
[data-testid="stMainBlockContainer"], .block-container{{padding-top:calc({TOPNAV_ALTURA}px + 1.4rem)!important}}
[data-testid="stSidebar"] > div:first-child{{padding-top:calc({TOPNAV_ALTURA}px + 14px)!important}}
</style>
"""


_SELO_V2_CSS = """
.gr{stroke:rgba(255,255,255,.09);fill:none}
.swf{transform-origin:center;animation:sw 4s linear infinite}
.swl{transform-origin:center;animation:sw 4s linear infinite;stroke:var(--accent,#E8873A)}
@keyframes sw{to{transform:rotate(360deg)}}
.radar-selo{position:relative;display:flex;align-items:center;gap:22px;overflow:hidden;
  background:linear-gradient(150deg,var(--surface2,#1C222B),var(--surface,#161A21));
  border:1px solid var(--line,rgba(255,255,255,.06));border-radius:16px;padding:20px 26px}
.radar-selo::before{content:"";position:absolute;inset:0;border-radius:16px;padding:1.5px;
  background:linear-gradient(145deg,var(--sem-info,#5B9BD5),transparent 55%);
  -webkit-mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);
  -webkit-mask-composite:xor;mask-composite:exclude;opacity:.4}
.rs-mini{width:84px;height:84px;flex:none;position:relative;z-index:1}
.rs-mini svg{width:100%;height:100%;display:block}
.rs-main{position:relative;z-index:1;min-width:0}
.rs-live{display:inline-flex;align-items:center;gap:6px;font-family:'JetBrains Mono',monospace;
  font-size:10px;letter-spacing:.5px;color:var(--sem-high,#4ADE80);background:rgba(74,222,128,.08);
  border:1px solid rgba(74,222,128,.22);padding:3px 9px;border-radius:6px;margin-bottom:9px}
.rs-live .d{width:6px;height:6px;border-radius:50%;background:var(--sem-high,#4ADE80);
  box-shadow:0 0 8px var(--sem-high,#4ADE80)}
.rs-num{font-size:34px;font-weight:800;letter-spacing:-1.5px;line-height:1;font-variant-numeric:tabular-nums}
.rs-num b{color:var(--accent,#E8873A)}
.rs-num .u{font-size:15px;font-weight:600;color:var(--muted,#A4AEBF);letter-spacing:-.5px;margin-left:7px}
.rs-cap{font-size:13.5px;color:var(--muted,#A4AEBF);margin-top:7px}
.rs-stats{margin-left:auto;display:flex;gap:26px;position:relative;z-index:1;flex:none}
.rs-stat{text-align:center}
/* "encerrando" clicável: leva aos editais que estão fechando */
.rs-stat.rs-click{cursor:pointer;border-radius:9px;padding:4px 10px;margin:-4px -2px;transition:.15s}
.rs-stat.rs-click:hover{background:rgba(240,102,63,.12)}
.rs-stat .n{font-size:24px;font-weight:800;font-variant-numeric:tabular-nums;letter-spacing:-.5px}
.rs-stat .l{font-family:'JetBrains Mono',monospace;font-size:9.5px;letter-spacing:.6px;
  text-transform:uppercase;color:var(--dim,#6B7688);margin-top:4px}
@media (max-width:820px){.rs-stats{display:none}}
"""


_SELO_JS_FN = r"""
  function miniRadar(scores){
    let dots = '';
    (scores || []).slice(0, 16).forEach(function(sc, i){
      const ang = i * 2.399963;
      const r = 52 - Math.max(0, Math.min(100, sc)) * 0.42;
      const cx = (60 + r * Math.cos(ang)).toFixed(1);
      const cy = (60 + r * Math.sin(ang)).toFixed(1);
      const cor = sem(sc);
      dots += '<circle cx="' + cx + '" cy="' + cy + '" r="2.1" fill="' + cor + '"/>';
    });
    return '<svg viewBox="0 0 120 120" aria-hidden="true">' +
      '<defs><radialGradient id="rsg"><stop offset="0" stop-color="rgba(232,135,58,.32)"/>' +
      '<stop offset="1" stop-color="rgba(232,135,58,0)"/></radialGradient></defs>' +
      '<circle class="gr" cx="60" cy="60" r="56"/><circle class="gr" cx="60" cy="60" r="37"/>' +
      '<circle class="gr" cx="60" cy="60" r="18"/>' +
      '<line class="gr" x1="60" y1="4" x2="60" y2="116"/><line class="gr" x1="4" y1="60" x2="116" y2="60"/>' +
      '<path class="swf" d="M60 60 L60 4 A56 56 0 0 1 100 22 Z" fill="url(#rsg)"/>' +
      '<line class="swl" x1="60" y1="60" x2="60" y2="4" stroke-width="1.6"/>' +
      '<circle cx="60" cy="60" r="2.6" fill="var(--accent,#E8873A)"/>' + dots + '</svg>';
  }
  function seloHTML(d){
    const f = d.foot || {};
    return '<div class="radar-selo"><div class="rs-mini">' + miniRadar(d.scores) + '</div>' +
      '<div class="rs-main"><span class="rs-live"><span class="d"></span>RADAR AO VIVO</span>' +
      '<div class="rs-num"><b>' + (f.fila || 0) + '</b><span class="u">na fila</span></div>' +
      '<div class="rs-cap">oportunidades distribuídas por aderência ao PFC</div></div>' +
      '<div class="rs-stats">' +
      '<div class="rs-stat' + ((f.encerrando||0)>0?' rs-click':'') + '"' +
        ((f.encerrando||0)>0?' data-act="encerrando" title="Ver os editais que estão encerrando"':'') +
      '><div class="n" style="color:var(--sem-urgent,#F0663F)">' + (f.encerrando || 0) +
      '</div><div class="l">encerrando</div></div>' +
      '<div class="rs-stat"><div class="n">' + (f.fontes || 0) + '</div><div class="l">fontes</div></div>' +
      '</div></div>';
  }
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
/* card "mais aderente" isolado (o número da fila migrou para o selo) */
.lead-solo{padding:24px 30px}
.lead-solo .hl-headline{margin-top:0;padding-top:0;border-top:none}
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
  border-radius:16px;padding:26px 28px;min-width:0}
.panel h3{font-size:16px;font-weight:600;margin:0 0 4px}
.panel .psub{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--dim,#6B7688);
  margin-bottom:22px;letter-spacing:.5px}
.fb{display:flex;align-items:center;gap:16px;margin-bottom:18px;cursor:pointer}
.fb:last-child{margin-bottom:0}
.fb:hover .n{color:var(--ink,#F5F7FA)}
.fb:hover .tk{outline:1px solid var(--line2,rgba(255,255,255,.12));outline-offset:2px}
.fb .n{font-size:14px;color:var(--muted,#A4AEBF);width:96px;flex:none;font-weight:500}
.fb .tk{flex:1;min-width:0;height:11px;background:rgba(255,255,255,.05);border-radius:6px;overflow:hidden}
.fb .fl{display:block;height:100%;border-radius:6px}
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
__SELO_FN__
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

  // ---- radar: agora um SELO compacto (o mini-radar é decorativo, não ferramenta) ----
  // o número da fila e o resumo ficam no selo; abaixo, só a oportunidade-destaque.
  const heroCard = h.top
    ? '<div class="lead-card lead-solo">' + topHtml + '</div>'
    : '';
  root.innerHTML = seloHTML(d) + heroCard;

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
      '<span class="tk"><span class="fl" style="background:' + s.cor + ';width:' + s.pct +
      '%"></span></span><span class="v tnum">' + s.n + '</span></div>';
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
  // barras já vêm com width no HTML; o "crescer" é feito por keyframe scaleX
  // (transition:width trava o computed no shadow DOM do componente v2).
  return function(){ root.remove(); };
}
"""


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


_RADAR_V2_CSS = """
.rv{font-family:'Inter',system-ui,sans-serif;color:var(--ink,#F5F7FA);animation:rv-fade .4s ease}
@keyframes rv-fade{from{opacity:0;transform:translateY(10px)}}
.rlist{display:flex;flex-direction:column;gap:9px}
.rlist-head{display:grid;grid-template-columns:54px 1fr 130px 128px 22px;gap:14px;align-items:center;
  padding:2px 20px 6px;font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.8px;
  text-transform:uppercase;color:var(--dim,#6B7688)}
.rlist-head .r{text-align:right}
.ritem{position:relative;display:grid;grid-template-columns:54px 1fr 130px 128px 22px;gap:14px;
  align-items:center;background:var(--surface,#161A21);border:1px solid var(--line,rgba(255,255,255,.06));
  border-radius:13px;padding:15px 20px;cursor:pointer;overflow:hidden;transition:.16s cubic-bezier(.16,1,.3,1);
  --c:var(--sem-mid,#E8B54A)}
.ritem::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--c)}
.ritem:hover{border-color:var(--line2,rgba(255,255,255,.12));transform:translateX(3px);background:var(--hover,#222834)}
.ri-sc{font-weight:800;font-size:25px;text-align:center;font-variant-numeric:tabular-nums;color:var(--c)}
.ri-main{min-width:0}
.ri-nome{font-size:14.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.3}
.ri-fonte{margin-top:5px}
.ri-fonte .src{font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:600;letter-spacing:.6px;
  color:var(--sem-info,#5B9BD5);background:rgba(91,155,213,.1);padding:3px 8px;border-radius:5px}
.ri-val{font-family:'JetBrains Mono',monospace;font-size:12.5px;font-weight:600;color:var(--muted,#A4AEBF);
  text-align:right;white-space:nowrap}
.ri-prazo{font-family:'JetBrains Mono',monospace;font-size:11.5px;font-weight:600;text-align:right;
  white-space:nowrap}
.ri-prazo.u{color:var(--sem-urgent,#F0663F)}
.ri-prazo.s{color:var(--accent,#E8873A)}
.ri-prazo.n{color:var(--dim,#6B7688)}
.ri-arrow{color:var(--dim,#6B7688);transition:.18s;text-align:center}
.ritem:hover .ri-arrow{color:var(--accent,#E8873A);transform:translateX(3px)}
.rv-mais{font-family:'JetBrains Mono',monospace;font-size:11.5px;color:var(--dim,#6B7688);
  text-align:center;padding:12px;border:1px dashed var(--line2,rgba(255,255,255,.12));border-radius:11px;margin-top:4px}
.rv-vazio{background:var(--surface,#161A21);border:1px solid var(--line,rgba(255,255,255,.06));
  border-radius:14px;padding:34px 20px;text-align:center;color:var(--muted,#A4AEBF);font-size:14px}
.rv-vazio .ic{font-size:28px;margin-bottom:8px}
@media (max-width:820px){
  .rlist-head,.ritem{grid-template-columns:44px 1fr 96px}
  .rlist-head .cval,.ritem .ri-val{display:none}
  .ri-arrow{display:none}.rlist-head .carrow{display:none}
}
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
__SELO_FN__
  const root = document.createElement('div'); root.className = 'rv';

  // lista protagonista (ordenada por aderência)
  let lista = '';
  itens.forEach(function(o, i){
    lista += '<div class="ritem" style="--c:' + sem(o.score) + '" data-act="op" data-i="' + i + '">' +
      '<div class="ri-sc">' + esc(o.score) + '</div>' +
      '<div class="ri-main"><div class="ri-nome">' + esc(o.titulo) + '</div>' +
      '<div class="ri-fonte"><span class="src">' + esc(o.fonte).toUpperCase() + '</span></div></div>' +
      '<div class="ri-val">' + esc(o.valor || '—') + '</div>' +
      '<div class="ri-prazo ' + o.badge_cls + '"' +
      (o.badge_tip ? ' title="' + esc(o.badge_tip) + '"' : '') + '>' + esc(o.badge_txt) + '</div>' +
      '<div class="ri-arrow">→</div></div>';
  });
  if (d.ocultos > 0) {
    lista += '<div class="rv-mais">+ ' + d.ocultos + ' na fila · aprove ou descarte para ver as próximas</div>';
  }
  let corpo;
  if (!itens.length) {
    corpo = '<div class="rv-vazio"><div class="ic">🛰️</div>' +
      '<div><b>Nenhuma oportunidade nova no momento</b></div>' +
      '<div style="font-size:12.5px;color:var(--dim,#6B7688);margin-top:6px">O radar roda todo dia às 06:00 ' +
      'e coloca aqui os editais que passam no filtro.</div></div>';
  } else {
    corpo = '<div class="rlist-head"><span>Score</span><span>Oportunidade · fonte</span>' +
      '<span class="r cval">Valor</span><span class="r">Prazo</span><span class="carrow"></span></div>' +
      '<div class="rlist">' + lista + '</div>';
  }

  root.innerHTML = seloHTML(d) + '<div style="height:22px"></div>' + corpo;
  parentElement.appendChild(root);

  root.addEventListener('click', function(e){
    const el = e.target.closest('[data-act]');
    if (!el) { return; }
    setTriggerValue('acao', {t: el.dataset.act, i: +el.dataset.i, n: Date.now()});
  });
  return function(){ root.remove(); };
}
""".replace("__SELO_FN__", _SELO_JS_FN)


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
.fb .tk{flex:1;min-width:0;height:11px;background:rgba(255,255,255,.05);border-radius:6px;overflow:hidden}
.fb .fl{display:block;height:100%;border-radius:6px}
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
      '<span class="tk"><span class="fl" style="background:' + r.cor + ';width:' + r.w +
      '%"></span></span><span class="v">' + r.w + '%</span></div>';
  });
  root.innerHTML = '<div class="panel"><h3>' + esc(d.titulo || '') + '</h3>' +
    '<div class="psub">' + esc(d.sub || '') + '</div>' + fbs + '</div>';
  parentElement.appendChild(root);
  // barras já vêm com width no HTML; o "crescer" é feito por keyframe scaleX
  // (transition:width trava o computed no shadow DOM do componente v2).
  return function(){ root.remove(); };
}
"""
