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
from urllib.parse import quote, quote_plus

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import streamlit.components.v2 as components_v2

from src import dados
from src import relatorios
from src.dados import (
    COL_CANAL, COL_CHANCE, COL_EDITAL, COL_EMPRESA, COL_ENCAIXE, COL_ID,
    COL_INSTITUTO, COL_JANELA, COL_MODALIDADE, COL_OBS, COL_PRESENCA,
    COL_PRIORIDADE, COL_PROPOSTA, COL_PROX_ACAO, COL_PUBLICO, COL_REGIAO,
    COL_RESP, COL_SCORE, COL_SEDE, COL_SEMAFORO, COL_SETOR, COL_SOCIAL,
    COL_STATUS, COL_SUBSETOR, COL_TIPO, COL_UF, COL_URL, COL_VALVO, COL_VERIF,
    COL_VMAX, COL_VMIN, STATUS_FUNIL,
)

# --- Estilos/assets (CSS, JS, SVG) extraídos para ui/estilos.py ---
from ui.estilos import (
    _SVG_TRACO,
    ICONES,
    CSS,
    LOGO_SVG,
    _HUB_CSS,
    _HUB_JS,
    _HUB_CHROME_CSS,
    _EMENDAS_V2_CSS,
    _EMENDAS_V2_JS,
    _EMENDAS_CHROME_CSS,
    _SIDEBAR_FIX_JS,
    _SIDEBAR_OPEN_CSS,
    _SIDEBAR_TOGGLE_CORE,
    _SIDEBAR_TOGGLE_JS,
    _DESCOBRIR_CSS,
    _ORFAOS_CSS,
    _ORF_PIN,
    TOPNAV_ALTURA,
    _TOPNAV_CSS,
    _TOPNAV_JS,
    _TOPNAV_OFFSET_CSS,
    _SELO_V2_CSS,
    _SELO_JS_FN,
    _VISAO_V2_CSS,
    _VISAO_V2_JS,
    _RANKING_V2_CSS,
    _RANKING_V2_JS,
    _RADAR_V2_CSS,
    _RADAR_V2_JS,
    ORBITAL_TEMPLATE,
    EMAIL_COPY_TEMPLATE,
    _PESOS_V2_CSS,
    _PESOS_V2_JS,
)

# --- Helpers de formatação/lógica pura extraídos para ui/formato.py ---
from ui.formato import (
    EMENDA_ETAPA_COR,
    EMENDA_FUNIL_ETAPAS,
    _TEMP_COR,
    _TEMP_EMOJI,
    _TEMP_ORDEM,
    _temp_nome,
    _argumento_abordagem,
    _cap_mun,
    _cards_deputados,
    _contagens_emendas,
    _cor_score,
    _decodificar_id_card,
    _deputados_federais_ordenados,
    _deputados_ordenados,
    _dias_texto,
    _etapa_de_status,
    _filtrar_descobrir,
    _fmt_prazo,
    _funil_emendas_colunas,
    _itens_relatorio_emendas,
    _modo_emenda,
    _muns_pfc,
    _op_de_novidade,
    _orfaos_com_candidatos,
    _parse_data,
    _prazo_confiavel,
    _puxar_para_crm,
    _resumo_dep_dados,
    _score_novidade,
    _sidebar_toggle_html,
    _tabela_emendas_html,
    _tabela_parlamentares_html,
    _valor_rel,
    aviso_contexto_territorios,
    brl,
    brl_curto,
    capa_payload_parlamentares,
    carregar_parlamentares,
    css_icones_botoes,
    esc,
    estilo_plotly,
    funil_parlamentares_colunas,
    itens_relatorio_parlamentares,
    lista_orgs_html,
    plano_obs,
    resumo_relatorio_parlamentares,
    score_chip_cor,
    score_chip_hex,
    seg_html,
    sem_cor,
    slug,
    status_badge,
    svg_icone,
    texto_ou,
    verificada_ok,
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

PAGES = ["Visão geral", "Ranking", "Radar", "Funil", "Relatório", "Metodologia", "Verificação"]

# --------------------------------------------------------------------------- #
# Ícones SVG da sidebar (design system: SVG limpo, nunca emoji)
# ---------------------------------------------------------------------------
# O rótulo de st.button é texto puro — não aceita HTML. Então o ícone entra por
# CSS: cada botão vira alvo pela classe st-key-<chave> que o Streamlit põe no
# container, e o SVG é desenhado como mask-image. Usar mask (e não background)
# faz o ícone herdar a COR do texto: cinza no item normal, claro no item ativo,
# sem precisar de uma segunda cópia do arquivo.
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# Tema escuro premium + CSS custom
# --------------------------------------------------------------------------- #
st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Helpers de formatação
# --------------------------------------------------------------------------- #


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


CORES_STATUS = {"Mapear": "#7C8698", "Prospectar": "#E8873A", "Monitorar": "#5B9BD5",
                "Edital": "#8B7BF0", "Ativo": "#4ADE80"}


# --------------------------------------------------------------------------- #
# Navegação (controlada por session_state -> permite navegação programática)
# --------------------------------------------------------------------------- #
def ir_para(pagina: str):
    st.session_state["page"] = pagina


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


# =========================================================================== #
# HUB DE ENTRADA (maquete pfc_hub_v4) — porta de entrada após o login
# ---------------------------------------------------------------------------
# Fundo cósmico + horizonte de planeta + dois cards (Captação laranja /
# Emendas violeta). Custom Component v2 bidirecional: o clique num card
# devolve a escolha ao Python (setTriggerValue), que grava em
# session_state["radar_escolhido"] e entra no painel correspondente.
# =========================================================================== #


_hub_component = components_v2.component("pfc_hub", css=_HUB_CSS, js=_HUB_JS)


def render_hub():
    """Renderiza a Central e trata a escolha do radar (grava e entra no painel)."""
    st.markdown(_HUB_CHROME_CSS, unsafe_allow_html=True)
    try:
        novas = len(dados.carregar_novidades_pendentes())
    except Exception:
        novas = 0
    try:
        from radar.fontes_ancora import FONTES as _FA
        n_fontes = len(_FA)
    except Exception:
        n_fontes = 31
    # Emendas: os mesmos números do painel, pela mesma função de contagem.
    # Sem a base de deputados (o CSV fica fora do git, então é o caso do deploy),
    # zera em vez de inventar — número errado no hub queima a confiança no resto.
    try:
        em = _contagens_emendas(_deputados_ordenados())
    except Exception:
        em = {"deputados": 0, "reunioes": 0, "aprovadas": 0}
    payload = {
        "status": "SHEETS AO VIVO · 06:00" if modo_conectado else "MODO LOCAL · CSV",
        "captacao": {"orgs": TOTAL, "novas": novas, "fontes": n_fontes,
                     "tag": "Setor 01 · Recursos privados"},
        "emendas": {**em, "tag": "Setor 02 · Recursos públicos"},
    }
    res = _hub_component(data=payload, key="hub", on_escolha_change=lambda: None)
    esc = getattr(res, "escolha", None)
    if isinstance(esc, dict) and esc.get("radar") in ("captacao", "emendas", "prospeccao"):
        st.session_state["radar_escolhido"] = esc["radar"]
        st.rerun()


# =========================================================================== #
# RADAR 2 · EMENDAS PARLAMENTARES (maquete pfc_emendas_v2, identidade violeta)
# ---------------------------------------------------------------------------
# CRM de relacionamento com deputados (não é radar automático). Lê a base
# local de deputados estaduais (dados.carregar_deputados). O campo "Diálogo"
# é SENSÍVEL: só é renderizado para usuário logado (guard explícito), nunca
# numa view pública.
# =========================================================================== #


@st.dialog("Dossiê do deputado", width="large")
def dlg_deputado(dep: dict):
    breadcrumb("Emendas", dep["nome"])
    st.markdown(
        f'<div style="font-size:20px;font-weight:700;color:var(--ink)">{esc(dep["nome"])}</div>'
        f'<div style="font-family:var(--mono);font-size:12px;color:var(--dim);margin-top:6px">'
        f'{esc(dep["partido"])} · ALESP · {esc(dep["base"]) or "base regional —"}</div>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    c1.markdown(
        f'<div style="background:var(--surface2);border:1px solid var(--line);border-radius:12px;padding:16px">'
        f'<div style="font-family:var(--mono);font-size:10px;letter-spacing:.8px;text-transform:uppercase;'
        f'color:var(--dim);margin-bottom:8px">Chance de emenda</div>'
        f'<div style="font-size:26px;font-weight:800;color:#8B7BF0">{dep["chance"]}%</div></div>',
        unsafe_allow_html=True)
    c2.markdown(
        f'<div style="background:var(--surface2);border:1px solid var(--line);border-radius:12px;padding:16px">'
        f'<div style="font-family:var(--mono);font-size:10px;letter-spacing:.8px;text-transform:uppercase;'
        f'color:var(--dim);margin-bottom:8px">Aderência PFC</div>'
        f'<div style="font-size:26px;font-weight:800;color:#4ADE80">{dep["ader"]}</div></div>',
        unsafe_allow_html=True)

    st.markdown(
        f'<div style="margin-top:18px"><div style="font-family:var(--mono);font-size:11px;letter-spacing:1px;'
        f'text-transform:uppercase;color:var(--dim);margin-bottom:8px">Status da negociação</div>'
        f'<span class="stpill" style="background:{dep["status_cor"]}22;color:{dep["status_cor"]};'
        f'font-size:12px;font-weight:600;padding:6px 13px;border-radius:20px">'
        f'{dep["temp_emoji"]} {esc(dep["status"])} · {esc(dep["temp"])}</span></div>',
        unsafe_allow_html=True)

    # ---- DIÁLOGO (sensível) — só para usuário autenticado ----
    st.markdown('<div style="font-family:var(--mono);font-size:11px;letter-spacing:1px;'
                'text-transform:uppercase;color:var(--dim);margin:20px 0 8px">'
                'Diálogo · andamento da negociação</div>', unsafe_allow_html=True)
    if st.session_state.get("user"):
        dlg = dep["dialogo"] or "Sem anotações de diálogo ainda."
        st.markdown(
            f'<div style="background:var(--surface2);border:1px solid var(--line);'
            f'border-left:3px solid #8B7BF0;border-radius:0 10px 10px 0;padding:14px 16px;'
            f'font-size:14px;line-height:1.6;color:var(--muted);font-style:italic">'
            f'{esc(dlg)}</div>'
            '<div style="font-size:11px;color:var(--dim);margin-top:7px">'
            '🔒 Informação de articulação restrita · visível apenas para a equipe logada</div>',
            unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-size:13px;color:var(--dim)">🔒 Conteúdo restrito.</div>',
                    unsafe_allow_html=True)

    # ---- contato + estratégia ----
    contatos = []
    if dep["gabinete"]:
        contatos.append(f"Gabinete ALESP: {esc(dep['gabinete'])}")
    if dep["telefones"]:
        contatos.append(f"Tel.: {esc(dep['telefones'])}")
    if dep["whatsapp"]:
        contatos.append(f"WhatsApp: {esc(dep['whatsapp'])}")
    if dep["email"]:
        contatos.append(f"E-mail: {esc(dep['email'])}")
    if dep["instagram"]:
        contatos.append(f"Instagram: {esc(dep['instagram'])}")
    linhas = [("Contato", "<br>".join(contatos) or "—"),
              ("Emenda / ação", esc(dep["emenda"]) or "—"),
              ("Valor pretendido", esc(dep["valor"]) or "—"),
              ("Estratégia PFC", esc(dep["estrategia"]) or "—")]
    corpo = "".join(
        f'<div style="margin-top:18px"><div style="font-family:var(--mono);font-size:11px;'
        f'letter-spacing:1px;text-transform:uppercase;color:var(--dim);margin-bottom:7px">{lab}</div>'
        f'<div style="font-size:14px;color:var(--ink);line-height:1.6">{val}</div></div>'
        for lab, val in linhas)
    st.markdown(corpo, unsafe_allow_html=True)

    # ---- CONTATO OFICIAL (público, ALESP) — buscado POR NOME, separado dos
    # campos pessoais/de assessor acima. Puxar do Descobrir não preenche os
    # campos pessoais, então sem isto o card ficava com contato vazio ("—"). É
    # só-leitura (regra 1): o mesmo casamento por nome do dossiê da Descobrir.
    ct = dados.contato_oficial(str(dep["nome"]))
    st.markdown('<div style="margin-top:18px;font-family:var(--mono);font-size:11px;'
                'letter-spacing:1px;text-transform:uppercase;color:var(--dim);margin-bottom:7px">'
                'Contato oficial · ALESP</div>', unsafe_allow_html=True)
    _tem_ct = ct and (ct.get("email") not in ("", "não encontrado")
                      or ct.get("telefone") not in ("", "não encontrado")
                      or ct.get("pagina"))
    if not _tem_ct:
        st.markdown('<div style="font-size:13px;color:var(--dim)">Não encontrado na lista de '
                    'titulares da ALESP.</div>', unsafe_allow_html=True)
    else:
        def _campo_ofc(rot, val, link=None):
            if not val or val == "não encontrado":
                v = '<span style="color:var(--dim)">não encontrado</span>'
            elif link:
                v = f'<a href="{esc(link)}" target="_blank" style="color:#b7abff">{esc(val)}</a>'
            else:
                v = esc(val)
            return (f'<div style="display:flex;gap:8px;font-size:13px;margin-bottom:5px">'
                    f'<span style="font-family:var(--mono);font-size:10px;letter-spacing:.5px;'
                    f'text-transform:uppercase;color:var(--dim);min-width:78px;padding-top:2px">'
                    f'{rot}</span><span style="color:var(--ink)">{v}</span></div>')
        email = ct.get("email", "")
        pag = ct.get("pagina", "")
        st.markdown(
            '<div style="background:var(--surface2);border:1px solid var(--line);'
            'border-left:3px solid #8B7BF0;border-radius:0 10px 10px 0;padding:12px 15px">'
            + _campo_ofc("Email", email,
                         link=(f"mailto:{email}" if email and email != "não encontrado" else None))
            + _campo_ofc("Telefone", ct.get("telefone", ""))
            + _campo_ofc("Página", "abrir no site da ALESP" if pag else "", link=pag)
            + '</div>'
            '<div style="font-size:11px;color:var(--dim);margin-top:6px">Contato público de '
            'gabinete (ALESP), preenchido por código — separado dos contatos pessoais/de '
            'assessor acima.</div>', unsafe_allow_html=True)

    # ---- EDIÇÃO (sensível) — só para usuário autenticado (regra 4) ----------
    # Grava pela porta única dados.atualizar_deputado: só as células que MUDARAM,
    # preservando o resto (regra 2). O Status usa as MESMAS 5 etapas do funil,
    # então dossiê e drag-and-drop escrevem o mesmo campo, sem divergir (regra 3).
    # Os contatos OFICIAIS da ALESP não entram aqui: são só-leitura (regra 1).
    if st.session_state.get("user"):
        nome = dep["nome"]
        etapa_atual = _etapa_de_status(dep["status"])
        idx_status = EMENDA_FUNIL_ETAPAS.index(etapa_atual) if etapa_atual in EMENDA_FUNIL_ETAPAS else 0
        idx_temp = _TEMP_ORDEM.index(dep["temp"]) if dep["temp"] in _TEMP_ORDEM else 0

        st.markdown('<div style="margin-top:22px;padding-top:18px;'
                    'border-top:1px solid var(--line);font-family:var(--mono);font-size:11px;'
                    'letter-spacing:1px;text-transform:uppercase;color:#8B7BF0">'
                    '✎ Atualizar relacionamento</div>', unsafe_allow_html=True)

        ce1, ce2 = st.columns(2)
        novo_status = ce1.selectbox("Status · etapa do funil", EMENDA_FUNIL_ETAPAS,
                                    index=idx_status, key=f"ed_status_{nome}")
        nova_temp = ce2.selectbox("Temperatura", _TEMP_ORDEM,
                                  index=idx_temp, key=f"ed_temp_{nome}")
        novo_dialogo = st.text_area("Diálogo · anotações de negociação",
                                    value=dep["dialogo"], height=130,
                                    key=f"ed_dialogo_{nome}")
        nova_obs = st.text_area("Registro de reunião / próximos passos",
                                value=dep["obs"], height=90, key=f"ed_obs_{nome}")

        if st.button("Salvar alterações", type="primary", use_container_width=True,
                     key=f"ed_salvar_{nome}"):
            campos = {}
            if novo_status != etapa_atual:
                campos["Status"] = novo_status
            if nova_temp != dep["temp"]:
                campos["Temperatura"] = f"{_TEMP_EMOJI[nova_temp]} {nova_temp}"
            if novo_dialogo.strip() != dep["dialogo"]:
                campos["Diálogo"] = novo_dialogo.strip()
            if nova_obs.strip() != dep["obs"]:
                campos["Observações"] = nova_obs.strip()

            if not campos:
                st.info("Nenhuma alteração para salvar.")
            else:
                res = dados.atualizar_deputado(nome, campos)
                if res.get("sucesso"):
                    st.success(f"✓ {res['mensagem']} Os demais campos foram preservados.")
                    st.toast("Deputado atualizado no Google Sheets.")
                    st.caption("Feche este dossiê para ver a base e o funil já atualizados.")
                else:
                    st.warning(res.get("mensagem", "Não foi possível gravar."))
        st.caption("🔒 Edição restrita à equipe logada · grava direto na aba Deputados do "
                   "Google Sheets. Contatos oficiais da ALESP são só-leitura.")
    else:
        st.caption("ℹ️ A edição do relacionamento (diálogo, status, temperatura) é restrita "
                   "à equipe logada.")


@st.dialog("Observação rápida", width="small")
def dlg_obs_rapida(escopo: str, chave: str):
    """Mini-editor aberto ao CLICAR num card do funil de Emendas (estadual OU
    federal). Anexa uma observação DATADA ao MESMO campo Diálogo que o dossiê edita
    (sensível → só logado). NÃO toca em status/etapa, temperatura nem contatos:
    grava só o Diálogo. Roteia a gravação por escopo (plano_obs)."""
    if not st.session_state.get("user"):
        st.warning("🔒 Conteúdo restrito à equipe logada.")
        return
    # Diálogo atual (contexto read-only) da base CERTA por escopo: estadual casa
    # por nome (aba Deputados); federal por ID (aba Deputados Federais).
    if escopo == "federal":
        dep = next((d for d in _deputados_federais_ordenados()
                    if str(d.get("id")) == str(chave)), None)
        nome = (dep or {}).get("nome") or str(chave)
        aba = "Deputados Federais"
    else:
        dep = next((d for d in _deputados_ordenados() if d["nome"] == chave), None)
        nome = str(chave)
        aba = "Deputados"
    atual = (dep or {}).get("dialogo", "")
    st.markdown(
        f'<div style="font-size:16px;font-weight:700;color:var(--ink)">{esc(nome)}</div>'
        f'<div style="font-family:var(--mono);font-size:11px;color:var(--dim);margin-top:3px">'
        f'Anota no diálogo · aparece no dossiê</div>', unsafe_allow_html=True)
    if atual:
        st.markdown(
            '<div style="font-family:var(--mono);font-size:10px;letter-spacing:.8px;'
            'text-transform:uppercase;color:var(--dim);margin:14px 0 6px">Diálogo atual</div>'
            f'<div style="background:var(--surface2);border:1px solid var(--line);'
            f'border-left:3px solid #8B7BF0;border-radius:0 8px 8px 0;padding:10px 12px;'
            f'font-size:12.5px;line-height:1.55;color:var(--muted);font-style:italic;'
            f'max-height:150px;overflow-y:auto;white-space:pre-wrap">{esc(atual)}</div>',
            unsafe_allow_html=True)

    nota = st.text_area("Nova observação", height=120, key=f"obsrap_txt_{escopo}_{chave}",
                        placeholder="Ex.: Ligação com o assessor — pediu proposta por e-mail até sexta.")
    if st.button("Salvar observação", type="primary", use_container_width=True,
                 key=f"obsrap_save_{escopo}_{chave}"):
        if not nota.strip():
            st.info("Escreva uma observação antes de salvar.")
        else:
            plano = plano_obs(escopo, chave, nota.strip(), atual)
            if plano["porta"] == "estadual":
                res = dados.anexar_dialogo_deputado(plano["nome"], plano["texto"])
            elif plano["porta"] == "federal":
                res = dados.atualizar_deputado_federal(plano["id"], plano["campos"])
            else:
                res = {"sucesso": False, "mensagem": "Escopo sem gravação de observação."}
            if res.get("sucesso"):
                st.success("✓ Observação anexada ao diálogo — visível também no dossiê.")
                st.toast(f"Salvo na aba {aba}.")
                st.caption("Feche para voltar ao funil.")
            else:
                st.warning(res.get("mensagem", "Não foi possível gravar."))
    st.caption("🔒 Grava no campo Diálogo (sensível) · não altera status, temperatura nem contatos.")


_emendas_v2 = components_v2.component("pfc_emendas", css=_EMENDAS_V2_CSS, js=_EMENDAS_V2_JS)


def _preparar_sidebar():
    """Prepara a sidebar: CSS do modo expandido (por classe), recuperação do bug
    de não-montar, e a SETINHA client-side de recolher/expandir.

    O estado do expandir/recolher NÃO é do Python: vive na classe pfc-sb-open do
    <html> (client-side, sem rerun). Por isso o CSS do modo aberto é injetado
    SEMPRE (a classe é que decide se aplica), e a recuperação roda SEMPRE — a
    barra nunca fica escondida por completo (o modo ícone é o padrão).
    """
    st.markdown(_SIDEBAR_OPEN_CSS, unsafe_allow_html=True)
    components.html(_SIDEBAR_FIX_JS, height=0)
    components.html(_SIDEBAR_TOGGLE_JS, height=0)


@st.dialog("Emendas aprovadas", width="large")
def dlg_emendas_aprovadas(lista):
    breadcrumb("Emendas", "Aprovadas")
    st.markdown(f'#### ✅ {len(lista)} emenda(s) aprovada(s)')
    st.caption("Recurso já destinado — a conquista concreta da articulação até aqui.")
    st.markdown(_cards_deputados(lista, [("Valor da emenda", "valor"),
                                         ("Destino / ação", "emenda"),
                                         ("Base regional", "base"),
                                         ("Estratégia PFC", "estrategia")]),
                unsafe_allow_html=True)


@st.dialog("Reuniões ativas", width="large")
def dlg_reunioes_ativas(lista):
    breadcrumb("Emendas", "Reuniões ativas")
    st.markdown(f'#### 📅 {len(lista)} reunião(ões) solicitada(s) ou agendada(s)')
    st.caption("Onde a articulação está em movimento — acompanhe o retorno de cada gabinete.")
    # o Diálogo é sensível: só para usuário logado (o painel já é autenticado)
    extras = [("Diálogo · andamento", "dialogo")] if st.session_state.get("user") else []
    extras += [("Emenda / ação pretendida", "emenda"), ("Contato", "telefones")]
    st.markdown(_cards_deputados(lista, extras), unsafe_allow_html=True)


@st.dialog("Deputados em articulação", width="large")
def dlg_em_articulacao(lista):
    breadcrumb("Emendas", "Em articulação")
    st.markdown(f'#### 🤝 {len(lista)} deputado(s) com contato iniciado')
    st.caption("Todos que já saíram do 'não iniciado' — ordenados por score integrado.")
    extras = [("Diálogo · andamento", "dialogo")] if st.session_state.get("user") else []
    extras += [("Emenda / ação pretendida", "emenda"), ("Base regional", "base")]
    st.markdown(_cards_deputados(lista, extras), unsafe_allow_html=True)


# Navegação do painel de Emendas — páginas próprias. O escopo (Geral/Estadual/
# Federal/Senador) vive no segmented control de CONTEÚDO (emenda_escopo_filtro),
# não na sidebar (Passo 8). "Descobrir" é planejamento, separado do CRM.
EMENDA_PAGES = ["Visão geral", "Descobrir", "Territórios em Aberto",
                "Funil de negociação", "Relatório"]
# chave do botão -> ícone (a chave vira a classe st-key-<chave> que o CSS usa)
EMENDA_ICONES = {"emnav_visao-geral": "visao-geral",
                 "emnav_descobrir": "descobrir",
                 "emnav_territorios-em-aberto": "local",
                 "emnav_funil-de-negociacao": "funil-negociacao",
                 "emnav_relatorio": "relatorio",
                 "emenda_trocar": "trocar-radar", "emenda_logout": "sair"}
# chave do botão -> nome no tooltip do modo ícone
EMENDA_ROTULOS = {**{f"emnav_{slug(p)}": p for p in EMENDA_PAGES},
                  "emenda_trocar": "Trocar radar", "emenda_logout": "Sair"}


def ir_para_emenda(pagina: str):
    # Passo 8: só navega de página. O escopo virou eixo único (emenda_escopo_filtro,
    # no conteúdo) — a sidebar não escreve mais emenda_escopo.
    st.session_state["emenda_page"] = pagina


def render_sidebar_emendas():
    _preparar_sidebar()
    atual = st.session_state.get("emenda_page", "Visão geral")
    with st.sidebar:
        st.markdown(f"<style>{css_icones_botoes(EMENDA_ICONES, EMENDA_ROTULOS)}</style>",
                    unsafe_allow_html=True)
        st.markdown(_sidebar_toggle_html(), unsafe_allow_html=True)  # recolher/expandir no topo
        st.markdown(
            '<div class="sb-brand em-brand"><div class="rings em-rings"><span></span><span></span><span></span></div>'
            '<div class="bt">Futuro Cientista<small>EMENDAS PARLAMENTARES</small></div></div>',
            unsafe_allow_html=True,
        )
        # Passo 8: a sidebar é SÓ navegação de página (EMENDA_PAGES, sempre as 6). O
        # escopo (Geral/Estadual/Federal/Senador) é escolhido pelo segmented control
        # DENTRO de cada tela (emenda_escopo_filtro) — não há mais seção "Escopo" aqui,
        # nem ramo Federal. O conteúdo federal vem pelas telas unificadas.
        st.markdown('<div class="sb-sec">Articulação</div>', unsafe_allow_html=True)
        n_est = _contagens_emendas(_deputados_ordenados())["deputados"]
        n_deps = n_est + len(_deputados_federais_ordenados())
        for p in EMENDA_PAGES:
            st.button(p, key=f"emnav_{slug(p)}", use_container_width=True,
                      type="primary" if atual == p else "secondary",
                      on_click=ir_para_emenda, args=(p,))
        # Status de conexão = cor de saúde (verde vivo / vermelho caiu), igual ao
        # Captação. A contagem (estaduais + federais) desce para a 2ª linha.
        conn = ('<div class="sf"><span class="d g"></span>SHEETS CONECTADO</div>'
                if modo_conectado else
                '<div class="sf"><span class="d r"></span>MODO LOCAL · CSV</div>')
        st.markdown(f'<div class="sb-foot">{conn}'
                    f'<div class="sf"><span class="d n"></span>{n_deps} PARLAMENTARES · ALESP + CÂMARA</div></div>',
                    unsafe_allow_html=True)
        if st.button("Trocar radar", key="emenda_trocar", use_container_width=True):
            st.session_state["radar_escolhido"] = None
            st.rerun()
        if st.button("Sair", key="emenda_logout", use_container_width=True):
            for k in ("user", "page", "login_email", "login_senha", "radar_escolhido"):
                st.session_state.pop(k, None)
            st.rerun()


# =========================================================================== #
# TELA "DESCOBRIR DEPUTADOS" — planejamento de captação
# ---------------------------------------------------------------------------
# Lê o levantamento de emendas (rankings gerados por src/emendas.py) e mostra
# quem abordar. NÃO é o CRM dos 16 do Fábio — é a lista de prospecção. Duas
# seções: "Abordar já" (território) e "Cortejar" (expansão, em 2 camadas).
# Regra dura: AUTORIZADO (proposta) e PAGO (execução) sempre separados e
# rotulados — nunca somados. A ação de puxar pro CRM é o próximo passo (ainda
# não existe aqui).
# =========================================================================== #


def _linha_descobrir(row: dict, secao: str, idx, no_crm: bool) -> None:
    """Uma linha-card de deputado. secao ∈ {'territorio','expansao'}.
    O card INTEIRO é clicável (abre o dossiê) via um botão transparente sobreposto;
    o botão "Puxar" fica por cima como a exceção. Na linha, só o autorizado — o
    pago vs autorizado vive no dossiê. `no_crm` = checagem LIVE contra o CRM."""
    score = float(row.get("score_pfc") or row.get("score_expansao") or 0)
    aut = row.get("autorizado_pfc" if secao == "territorio" else "autorizado_geral_edusoc", 0)
    fatia = row.get("alinhamento_pct", 0)
    c_info, c_acao = st.columns([7, 1.15])
    c_info.markdown(
        '<div class="dd-cell">'
        f'<div class="dd-nomecol"><div class="dd-top">{_dd_selo("estadual", "Estadual")}'
        f'<span class="dd-nome">{esc(row["deputado"])}</span>'
        + ('<span class="dd-fabio">NO CRM</span>' if no_crm else "")
        + f'</div><div class="dd-sub">{esc(row.get("partido", ""))} · fatia edu/social {esc(fatia)}%</div></div>'
        f'<div class="dd-scorecol"><div class="dd-score" style="color:{_cor_score(score)}">{round(score)}</div>'
        f'<div class="dd-sub">score</div></div>'
        f'<div class="dd-valcol"><div class="dd-val">aut. <b>{brl_curto(aut)}</b></div>'
        f'<div class="dd-sub">{esc(_muns_pfc(row, secao))}</div></div>'
        '</div>',
        unsafe_allow_html=True)
    # botão transparente que cobre o card inteiro (o CSS o sobrepõe) -> abre o dossiê
    if c_info.button(f"Abrir dossiê de {row['deputado']}", key=f"dd_{secao}_{idx}",
                     use_container_width=True):
        dlg_descobrir_deputado(dict(row), secao)
    # Puxar para o CRM: grava DIRETO. Se já está no CRM, desabilitado (não duplica).
    if no_crm:
        c_acao.button("no CRM", key=f"crm_{secao}_{idx}", disabled=True, use_container_width=True,
                      help="Este deputado já está no CRM do Fábio.")
    elif c_acao.button("Puxar", key=f"crm_{secao}_{idx}", use_container_width=True,
                       help="Grava este deputado como nova linha no CRM (direto, sem confirmação)."):
        res = _puxar_para_crm(dict(row), secao)
        if res.get("sucesso"):
            st.toast(f"{row['deputado']} puxado para o CRM.")
        elif res.get("motivo") == "duplicado":
            st.toast(f"{row['deputado']} já estava no CRM — não dupliquei.")
        else:
            st.toast(f"Não deu para puxar: {res.get('mensagem') or res.get('motivo')}")
        st.rerun()


def _dd_selo(escopo: str, nome: str) -> str:
    """Selo de escopo para os cards da Descobrir (mesma família violeta da capa)."""
    return f'<span class="dd-selo dd-selo-{esc(escopo)}">{esc(nome)}</span>'


def _linha_descobrir_federal(dep: dict, idx) -> None:
    """Card de deputado FEDERAL na Descobrir — mesmo estilo .dd-cell, com selo
    Federal e valor SUGERIDO (faixa), NUNCA execução (regra de ouro). O card
    inteiro abre o dossiê federal. Sem 'Puxar': o federal já é curado na sua
    própria aba (Deputados Federais)."""
    val = str(dep.get("valor_sugerido", "")).strip() or "—"
    c_info, _c = st.columns([7, 1.15])
    c_info.markdown(
        '<div class="dd-cell">'
        f'<div class="dd-nomecol"><div class="dd-top">{_dd_selo("federal", "Federal")}'
        f'<span class="dd-nome">{esc(dep.get("nome", ""))}</span></div>'
        f'<div class="dd-sub">{esc(dep.get("partido", ""))} · {esc(dep.get("base", "") or "base regional —")}</div></div>'
        f'<div class="dd-scorecol"><div class="dd-score" style="color:{_cor_score(dep.get("score", 0))}">'
        f'{dep.get("score", 0)}</div><div class="dd-sub">score</div></div>'
        f'<div class="dd-valcol"><div class="dd-val">sugerido <b>{esc(val)}</b></div>'
        f'<div class="dd-sub">valor sugerido · faixa</div></div>'
        '</div>', unsafe_allow_html=True)
    if c_info.button(f"Abrir dossiê de {dep.get('nome', '')}", key=f"dd_fed_{idx}",
                     use_container_width=True):
        dlg_deputado_federal(dict(dep))


def _filtra_feds_descobrir(feds: list, busca: str, f_part: str) -> list:
    """Aplica a busca (nome) e o filtro de partido aos federais. O filtro de
    município é do levantamento estadual — não se aplica aos federais."""
    b = str(busca or "").strip().lower()
    out = []
    for d in feds:
        if b and b not in str(d.get("nome", "")).lower():
            continue
        if f_part and f_part != "Todos" and str(d.get("partido", "")).strip() != f_part:
            continue
        out.append(d)
    return out


# --------------------------------------------------------------------------- #
# "Melhor argumento de abordagem" — frase-gancho composta do dado do
# levantamento. Escolhe o argumento MAIS FORTE (território direto > vizinhança >
# alinhamento proporcional > volume geral); nunca inventa — se não há gancho
# forte, diz algo honesto. Só composição de texto (sem IA, sem fonte nova).
# --------------------------------------------------------------------------- #


@st.dialog("Dossiê do deputado", width="large")
def dlg_descobrir_deputado(row: dict, secao: str) -> None:
    breadcrumb("Descobrir", str(row.get("deputado", "")))
    score = float(row.get("score_pfc") or row.get("score_expansao") or 0)
    no_crm = dados.deputado_no_crm(str(row.get("deputado", "")))  # checagem LIVE
    camada = row.get("camada", "") if secao == "expansao" else "No território"
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">'
        f'<span style="font-size:20px;font-weight:700;color:var(--ink)">{esc(row.get("deputado",""))}</span>'
        f'<span style="font-family:var(--mono);font-size:12px;color:var(--dim)">{esc(row.get("partido",""))} · ALESP</span>'
        + (f'<span class="dd-fabio">JÁ NO CRM DO FÁBIO</span>' if no_crm else
           '<span class="dd-fabio" style="background:rgba(124,134,152,.16);color:var(--muted)">FORA DO CRM</span>')
        + f'</div>'
        f'<div style="font-family:var(--mono);font-size:11px;color:var(--dim);margin-top:8px">'
        f'{esc(camada)} · score <b style="color:{_cor_score(score)}">{("%.1f"%score).replace(".",",")}</b> '
        f'· fatia educação/social {esc(row.get("alinhamento_pct",0))}%</div>',
        unsafe_allow_html=True)

    # ---- Resumo pré-reunião (PDF imprimível) — reusa o ReportLab dos relatórios ----
    try:
        _pdf_resumo = relatorios.pdf_resumo_deputado(
            _resumo_dep_dados(row, secao, no_crm, dados.carregar_deputados()),
            datetime.date.today().strftime("%d/%m/%Y"))
        st.download_button(
            "Resumo para reunião (PDF)", data=_pdf_resumo,
            file_name=f"resumo-reuniao-{slug(str(row.get('deputado','')))}.pdf",
            mime="application/pdf", use_container_width=True,
            key=f"pdf_dep_{slug(str(row.get('deputado','')))}",
            help="Página limpa com tudo do deputado, para imprimir e levar à reunião.")
    except Exception as e:  # PDF nunca derruba o dossiê
        st.caption(f"Não consegui gerar o PDF agora: {e}")

    # ---- MELHOR GANCHO DE ABORDAGEM — a 1ª coisa que o Fábio lê ----
    _chat_svg = ('<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#b7abff" '
                 'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" '
                 'style="vertical-align:-2px;margin-right:6px"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 '
                 '2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>')
    st.markdown(
        '<div style="background:linear-gradient(135deg,rgba(139,123,240,.16),rgba(139,123,240,.03));'
        'border:1px solid rgba(139,123,240,.34);border-left:3px solid #8B7BF0;border-radius:12px;'
        'padding:14px 16px;margin:18px 0 4px">'
        f'<div style="font-family:var(--mono);font-size:10px;letter-spacing:1px;text-transform:uppercase;'
        f'color:#b7abff;margin-bottom:7px">{_chat_svg}Melhor gancho de abordagem</div>'
        f'<div style="font-size:15.5px;line-height:1.5;color:var(--ink);font-weight:500">'
        f'{esc(_argumento_abordagem(row, secao))}</div></div>',
        unsafe_allow_html=True)

    # ---- AUTORIZADO x PAGO — sempre separados e rotulados ----
    if secao == "territorio":
        aut, pago = row.get("autorizado_pfc", 0), row.get("pago_pfc", 0)
        onde = "nos municípios do PFC"
    else:
        aut, pago = row.get("autorizado_geral_edusoc", 0), row.get("pago_geral_edusoc", 0)
        onde = "em educação/social no estado"
    c1, c2 = st.columns(2)
    c1.markdown(f'<div class="dd-box aut"><div class="k">Autorizado · proposta</div>'
                f'<div class="v" style="color:#b7abff">{brl(aut)}</div>'
                f'<div class="n">{onde}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="dd-box pago"><div class="k">Pago · execução confirmada</div>'
                f'<div class="v" style="color:var(--sem-high)">{brl(pago)}</div>'
                f'<div class="n">{onde}</div></div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:11.5px;color:var(--dim);margin-top:8px">'
                'Autorizado é <b>proposta</b>; pago é <b>execução confirmada</b>. São medidas '
                'diferentes — nunca somadas.</div>', unsafe_allow_html=True)

    # ---- pegada territorial ----
    st.markdown('<div style="font-family:var(--mono);font-size:11px;letter-spacing:1px;'
                'text-transform:uppercase;color:var(--dim);margin:20px 0 8px">'
                'Municípios do PFC</div>', unsafe_allow_html=True)
    if secao == "territorio":
        _linha_mun("Onde atua (direto)", row.get("municipios_pfc", ""), "#8B7BF0")
    else:
        _linha_mun("Direto — no nosso município", row.get("municipios_pfc_diretos", ""), "#8B7BF0",
                   valor=row.get("autorizado_direto", 0))
        _linha_mun("Vizinho — mesma Região Imediata (IBGE)", row.get("municipios_vizinhos", ""),
                   "#5B9BD5", valor=row.get("autorizado_vizinho", 0))

    # ---- contatos OFICIAIS (públicos, ALESP) — separados dos pessoais do CRM ----
    ct = dados.contato_oficial(str(row.get("deputado", "")))
    st.markdown('<div style="font-family:var(--mono);font-size:11px;letter-spacing:1px;'
                'text-transform:uppercase;color:var(--dim);margin:20px 0 8px">'
                'Contato oficial · ALESP</div>', unsafe_allow_html=True)
    if not ct or (ct.get("email") in ("", "não encontrado") and not ct.get("pagina")):
        st.markdown('<div style="font-size:13px;color:var(--dim)">Não encontrado na '
                    'lista de titulares da ALESP.</div>', unsafe_allow_html=True)
    else:
        def _campo(rot, val, link=None):
            if not val or val == "não encontrado":
                corpo = '<span style="color:var(--dim)">não encontrado</span>'
            elif link:
                corpo = f'<a href="{esc(link)}" target="_blank" style="color:#b7abff">{esc(val)}</a>'
            else:
                corpo = esc(val)
            return (f'<div style="display:flex;gap:8px;font-size:13px;margin-bottom:5px">'
                    f'<span style="font-family:var(--mono);font-size:10px;letter-spacing:.5px;'
                    f'text-transform:uppercase;color:var(--dim);min-width:78px;padding-top:2px">'
                    f'{rot}</span><span style="color:var(--ink)">{corpo}</span></div>')
        email = ct.get("email", "")
        st.markdown(
            '<div style="background:var(--surface2);border:1px solid var(--line);'
            'border-left:3px solid #8B7BF0;border-radius:0 10px 10px 0;padding:12px 15px">'
            + _campo("Email", email, link=(f"mailto:{email}" if email and email != "não encontrado" else None))
            + _campo("Telefone", ct.get("telefone", ""))
            + _campo("Página", "abrir no site da ALESP" if ct.get("pagina") else "", link=ct.get("pagina"))
            + '</div>'
            '<div style="font-size:11px;color:var(--dim);margin-top:6px">Contato público de '
            'gabinete. Os contatos pessoais/de assessor ficam no CRM (tela Deputados).</div>',
            unsafe_allow_html=True)

    st.caption("Levantamento de execução (Transparência SP · Power BI 2023-2025).")
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if no_crm:
        st.caption("✓ Já está no CRM do Fábio — o dossiê de negociação vive na tela Deputados.")
    elif st.button("Puxar para o CRM", key=f"dlg_crm_{slug(str(row.get('deputado','')))}",
                   type="primary", use_container_width=True,
                   help="Grava como nova linha no CRM, direto. O Fábio preenche diálogo, "
                        "temperatura e status."):
        res = _puxar_para_crm(row, secao)
        if res.get("sucesso"):
            st.toast(f"{row.get('deputado','')} puxado para o CRM.")
        elif res.get("motivo") == "duplicado":
            st.toast(f"{row.get('deputado','')} já estava no CRM — não dupliquei.")
        else:
            st.toast(f"Não deu para puxar: {res.get('mensagem') or res.get('motivo')}")
        st.rerun()


def _linha_mun(rotulo: str, municipios, cor: str, valor=None) -> None:
    txt = str(municipios or "").strip()
    valor_txt = (f' · autorizado {brl_curto(valor)}' if valor and float(valor or 0) > 0 else "")
    corpo = esc(txt) if txt else '<span style="color:var(--dim)">nenhum</span>'
    st.markdown(
        f'<div style="background:var(--surface2);border:1px solid var(--line);'
        f'border-left:3px solid {cor};border-radius:0 10px 10px 0;padding:11px 14px;margin-bottom:8px">'
        f'<div style="font-family:var(--mono);font-size:10px;letter-spacing:.5px;text-transform:uppercase;'
        f'color:var(--dim)">{esc(rotulo)}{valor_txt}</div>'
        f'<div style="font-size:13.5px;color:var(--ink);line-height:1.5;margin-top:5px">{corpo}</div></div>',
        unsafe_allow_html=True)


@st.cache_data(ttl=600, show_spinner=False)
def _municipios_pfc_lista() -> list:
    """Municípios do PFC (lista canônica do config), para o filtro da Descobrir."""
    try:
        import tomllib
        caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "config", "pfc_municipios.toml")
        with open(caminho, "rb") as f:
            cfg = tomllib.load(f)
        muns = []
        for g in cfg.get("grupos", []):
            muns += [str(m).strip() for m in g.get("municipios", []) if str(m).strip()]
        return sorted(set(muns))
    except Exception:
        return []


def render_descobrir() -> None:
    """Descobrir GERAL (Passo 4): junta o levantamento estadual (execução real,
    território/expansão) com os federais curados (valor sugerido), sob o mesmo
    controle de Escopo da Visão geral. Cada card leva o selo do seu escopo; o
    valor SEMPRE sai com o rótulo do seu tipo — execução (aut/pago estadual) e
    sugerido (faixa federal) NUNCA se somam nem se confundem."""
    st.markdown(_DESCOBRIR_CSS, unsafe_allow_html=True)

    # ---- Controle de Escopo (compartilha o estado com a Visão geral) ----
    st.session_state.setdefault("emenda_escopo_filtro", "Geral")
    escopo_sel = st.segmented_control(
        "Escopo", options=["Geral", "Estadual", "Federal", "Senador"],
        key="emenda_escopo_filtro", label_visibility="collapsed") or "Geral"
    st.caption("Escopo · Geral junta os três · Estadual / Federal / Senador filtram.")
    if escopo_sel == "Senador":
        st.markdown(
            '<div class="dd-intro">Escopo <b>Senador</b> ainda sem cadastro. O lugar já '
            'existe — quando a tabela do Fábio entrar, os senadores aparecem aqui na mesma '
            'descoberta. Nada quebra por estar vazio.</div>', unsafe_allow_html=True)
        return

    mostra_est = escopo_sel in ("Geral", "Estadual")
    mostra_fed = escopo_sel in ("Geral", "Federal")

    # ---- Fontes por escopo: estadual = levantamento (execução); federal = curado ----
    terr = dados.carregar_ranking_territorio() if mostra_est else pd.DataFrame()
    exp = dados.carregar_ranking_expansao() if mostra_est else pd.DataFrame()
    feds = _deputados_federais_ordenados() if mostra_fed else []
    if mostra_est and terr.empty and exp.empty and not mostra_fed:
        st.info("Levantamento ainda não gerado. Rode `python -m src.emendas` para "
                "produzir os rankings em `data/`.")
        return

    st.markdown(
        '<div class="dd-intro">Quem abordar para emendas de educação e assistência social. '
        'Estaduais vêm da <b>execução real</b> 2023-2025 (Transparência SP · autorizado/pago); '
        'federais são a <b>curadoria</b> do Fábio (valor <b>sugerido</b>, faixa). Cada card '
        'marca o seu escopo. O botão <b>Puxar</b> grava o estadual no CRM na hora.</div>'
        '<div class="dd-legend">'
        '<span><span class="sw" style="background:var(--sem-high)"></span>score 60+ · forte</span>'
        '<span><span class="sw" style="background:var(--sem-mid)"></span>50–59 · médio</span>'
        '<span><span class="sw" style="background:var(--sem-low)"></span>&lt;50 · fraco</span>'
        + ('<span><span class="sw" style="background:#8B7BF0"></span>Estadual · autorizado/pago</span>'
           '<span><span class="sw" style="background:#5B9BD5"></span>Federal · valor sugerido</span>'
           if escopo_sel == "Geral" else "")
        + '</div>', unsafe_allow_html=True)

    # ---- Busca e filtros (partidos de todos os escopos visíveis) ----
    partidos = set()
    if mostra_est:
        partidos |= set(terr.get("partido", pd.Series(dtype=str)).dropna())
        partidos |= set(exp.get("partido", pd.Series(dtype=str)).dropna())
    if mostra_fed:
        partidos |= {str(d.get("partido", "")).strip() for d in feds
                     if str(d.get("partido", "")).strip()}
    partidos = sorted(partidos)

    if mostra_est:  # o filtro de município é do levantamento estadual
        fc1, fc2, fc3 = st.columns([2, 1.2, 1.5])
    else:
        fc1, fc2 = st.columns([2, 1.5])
        fc3 = None
    busca = fc1.text_input("Buscar parlamentar", key="dd_busca",
                           placeholder="digite parte do nome…")
    f_part = fc2.selectbox("Partido", ["Todos"] + partidos, key="dd_partido")
    f_mun = (fc3.selectbox("Município do PFC onde atua", ["Todos"] + _municipios_pfc_lista(),
                           key="dd_municipio") if fc3 is not None else "Todos")

    if mostra_est:
        terr = _filtrar_descobrir(terr, busca, f_part, f_mun, ["municipios_pfc"])
        exp = _filtrar_descobrir(exp, busca, f_part, f_mun, ["municipios_pfc_diretos"])
    if mostra_fed:
        feds = _filtra_feds_descobrir(feds, busca, f_part)

    if (busca and busca.strip()) or f_part != "Todos" or (f_mun and f_mun != "Todos"):
        partes = []
        if mostra_est:
            partes.append(f"{len(terr)} em Abordar já · {len(exp)} em Cortejar")
        if mostra_fed:
            partes.append(f"{len(feds)} federais")
        st.caption("Filtro ativo · " + " · ".join(partes) + ". Limpe os campos para ver todos.")

    # Checagem LIVE contra o CRM atual (não o flag estático do ranking, que fica
    # velho assim que se puxa alguém): decide o selo "NO CRM" e trava a duplicata.
    crm = dados.carregar_deputados()
    no_crm = lambda nome: dados.deputado_no_crm(nome, crm)  # noqa: E731

    def _aba_territorio():
        st.markdown('<div class="dd-intro">Já financiam educação/social <b>dentro</b> dos '
                    'municípios do PFC. Ação imediata.</div>', unsafe_allow_html=True)
        if terr.empty:
            st.caption("Ninguém no território ainda.")
        for i, row in terr.iterrows():
            _linha_descobrir(row, "territorio", i, no_crm(row["deputado"]))

    def _aba_expansao():
        st.markdown('<div class="dd-intro">Alto alinhamento e volume no estado, ainda '
                    '<b>fora</b> dos nossos municípios (ou só de raspão). Alvo de cortejo — '
                    'emenda se redireciona a cada ciclo.</div>', unsafe_allow_html=True)
        pri = exp[exp["camada"] == "alvo prioritário"] if "camada" in exp else exp
        dem = exp[exp["camada"] == "demais candidatos"] if "camada" in exp else exp.iloc[0:0]
        st.markdown(f'<div class="dd-sec"><b>Alvos prioritários</b> · R$ 5 mi+ em edu/social '
                    f'· {len(pri)}<span class="ln"></span></div>', unsafe_allow_html=True)
        for i, row in pri.iterrows():
            _linha_descobrir(row, "expansao", i, no_crm(row["deputado"]))
        st.markdown(f'<div class="dd-sec"><b>Demais candidatos</b> · {len(dem)}'
                    f'<span class="ln"></span></div>', unsafe_allow_html=True)
        for i, row in dem.iterrows():
            _linha_descobrir(row, "expansao", i, no_crm(row["deputado"]))

    def _aba_federal():
        st.markdown('<div class="dd-intro">Deputados federais de SP, curados à mão. O valor é '
                    'faixa <b>sugerida</b> (potencial de emenda), <b>não</b> execução. Já ficam '
                    'no CRM Federal (aba própria) — por isso não têm "Puxar".</div>',
                    unsafe_allow_html=True)
        if not feds:
            st.caption("Nenhum federal para este filtro.")
        for i, dep in enumerate(feds):
            _linha_descobrir_federal(dep, i)

    # ---- Render por escopo ----
    if escopo_sel == "Federal":
        _aba_federal()
    elif escopo_sel == "Estadual":
        aba1, aba2 = st.tabs([f"Abordar já · {len(terr)}", f"Cortejar · {len(exp)}"])
        with aba1:
            _aba_territorio()
        with aba2:
            _aba_expansao()
    else:  # Geral — os três num só lugar, cada aba com o seu escopo
        aba1, aba2, aba3 = st.tabs([f"Abordar já · {len(terr)}",
                                    f"Cortejar · {len(exp)}", f"Federais · {len(feds)}"])
        with aba1:
            _aba_territorio()
        with aba2:
            _aba_expansao()
        with aba3:
            _aba_federal()


# =========================================================================== #
# TELA "MUNICÍPIOS ÓRFÃOS" — oportunidade de captação
# ---------------------------------------------------------------------------
# Municípios do PFC que NÃO recebem NENHUMA emenda de educação/social. Para cada
# um, cruza com o levantamento e mostra os deputados que já atuam na REGIÃO
# (mesma Região Imediata do IBGE) e são candidatos a levar emenda para lá.
# Só dado real: se um órfão não tem candidato plausível no levantamento, diz isso
# honestamente. AUTORIZADO e PAGO sempre separados (nunca somados).
# =========================================================================== #


def render_orfaos() -> None:
    st.markdown(_ORFAOS_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="dd-intro"><b>Territórios em aberto</b>: municípios do PFC onde '
        '<b>ninguém</b> financia educação ou assistência social hoje. Para cada um, os '
        'deputados que já atuam na mesma região (Região Imediata · IBGE) — os candidatos a '
        'levar emenda para lá. Baseado na execução real de 2023–2025 (Transparência SP).</div>',
        unsafe_allow_html=True)

    # Filtro de escopo compartilhado (Passos 3-6), default Geral. Territórios é uma
    # análise ESTADUAL por natureza: o conteúdo abaixo NÃO muda por escopo — sob
    # Federal/Senador só declaramos isso honestamente (aviso_contexto_territorios).
    st.session_state.setdefault("emenda_escopo_filtro", "Geral")
    escopo_sel = st.segmented_control(
        "Escopo", options=["Geral", "Estadual", "Federal", "Senador"],
        key="emenda_escopo_filtro", label_visibility="collapsed") or "Geral"
    aviso = aviso_contexto_territorios(escopo_sel)
    if aviso:
        st.info(aviso)

    # Carga + cruzamento BLINDADOS: qualquer falha (CSV ausente no deploy, módulo
    # de dados defasado, erro de leitura) cai num estado vazio elegante — a tela
    # NUNCA derruba o app. Era exatamente a causa do AttributeError em produção:
    # a chamada ao loader acontecia sem proteção.
    itens = None
    try:
        orfaos = dados.carregar_municipios_orfaos()
        base = dados.carregar_emendas_base()
        ibge = dados.carregar_regioes_ibge()
        terr = dados.carregar_ranking_territorio()
        exp = dados.carregar_ranking_expansao()
        if not base.empty and not ibge.empty:
            itens = _orfaos_com_candidatos(orfaos, base, ibge, terr, exp)
    except Exception:
        itens = None

    if itens is None:
        st.markdown(
            '<div class="orf-none">Levantamento de emendas ainda não disponível aqui. '
            'Gere os dados com <code>python -m src.emendas</code> e recarregue a página.</div>',
            unsafe_allow_html=True)
        return
    if not itens:
        st.markdown(
            '<div class="orf-none">Nenhum território em aberto — todos os municípios do PFC '
            'já recebem emenda de educação/social.</div>', unsafe_allow_html=True)
        return

    for it in itens:
        muni = esc(it["municipio"])
        grupo = f' · {esc(it["grupo"])}' if it["grupo"] else ""
        regiao = (f'Região {esc(it["regiao_nome"])} · {it["n_regiao"]} municípios vizinhos'
                  if not it["sem_regiao"] else "região não mapeada no IBGE")
        st.markdown(
            f'<div class="orf-card"><div class="orf-h">{_ORF_PIN}'
            f'Ninguém financia educação/social em {muni}</div>'
            f'<div class="orf-sub">{regiao}{grupo}</div>'
            f'<div class="orf-msg">Deputados que já atuam na região e são candidatos a '
            f'mudar isso:</div></div>',
            unsafe_allow_html=True)

        if not it["candidatos"]:
            extra = (f' ({it["fora_lev"]} financia(m) a região, mas está(ão) fora do '
                     f'levantamento — não são titulares aproveitáveis)'
                     if it["fora_lev"] else "")
            st.markdown(
                f'<div class="orf-none">Nenhum deputado do levantamento financia '
                f'educação/social na região de {muni} — sem candidato óbvio pelo dado '
                f'atual{extra}.</div>', unsafe_allow_html=True)
            continue

        for j, c in enumerate(it["candidatos"]):
            muns_reg = "/".join(_cap_mun(m) for m in c["muns"][:3]) + (
                f' +{len(c["muns"]) - 3}' if len(c["muns"]) > 3 else "")
            st.markdown(
                f'<div class="orf-cand"><div>'
                f'<div class="nome">{esc(c["deputado"])} '
                f'<span style="color:var(--dim);font-weight:400">· {esc(c["partido"])}</span></div>'
                f'<div class="sub">score {round(c["score"])} · atua em {esc(muns_reg)}</div></div>'
                f'<div class="orf-val"><b>aut. {brl_curto(c["aut"])}</b><br/>'
                f'pago {brl_curto(c["pago"])} · edu/social na região</div></div>',
                unsafe_allow_html=True)
            if st.button(f"Abrir dossiê de {c['deputado']}",
                         key=f"orf_{slug(it['municipio'])}_{j}", use_container_width=True):
                dlg_descobrir_deputado(dict(c["row"]), c["secao"])
        if it["fora_lev"]:
            st.caption(f"+ {it['fora_lev']} deputado(s) financiam a região mas estão fora "
                       "do levantamento (não titulares em exercício) — não listados como "
                       "candidatos aproveitáveis.")


def _mostrar_resultado(res):
    """Banner de resultado (verde/amarelo) a partir de {sucesso, mensagem}.
    Definido AQUI (e não lá embaixo) porque o painel de Emendas é renderizado
    antes daquele ponto do módulo — usado pelos dois funis (Emendas e Captação)."""
    if not res:
        return
    (st.success if res.get("sucesso") else st.warning)(
        res.get("mensagem", "Operação concluída."))


def render_funil_emendas() -> None:
    """Funil de negociação GERAL (Passo 5) — todos os escopos no MESMO kanban
    drag-and-drop (o mesmo componente da Captação). Arrastar ROTEIA a escrita pela
    ORIGEM do card: estadual grava a coluna Status por NOME (aba Deputados);
    federal grava Status CRM por ID (aba Deputados Federais). Nunca soma valores."""
    _mostrar_resultado(st.session_state.pop("kanban_emendas_msg", None))

    # Mesmo seletor de escopo da Visão geral (Passo 3), estado COMPARTILHADO
    # (emenda_escopo_filtro): a escolha do usuário acompanha ele entre as telas.
    st.session_state.setdefault("emenda_escopo_filtro", "Geral")
    escopo_sel = st.segmented_control(
        "Escopo", options=["Geral", "Estadual", "Federal", "Senador"],
        key="emenda_escopo_filtro", label_visibility="collapsed") or "Geral"

    regs = carregar_parlamentares(escopo_sel)
    if not regs:
        # Senador ainda não tem base (vazio elegante); idem qualquer filtro sem gente.
        st.info("Escopo Senador ainda sem base — em breve." if escopo_sel == "Senador"
                else "Nenhum parlamentar neste escopo.")
        return

    conectado = dados.deputados_conectado()
    colunas = funil_parlamentares_colunas(regs)
    if not KANBAN_DND_OK or not conectado:
        # fallback estático (mesmo espírito do funil de Captação)
        cols_html = ""
        for c in colunas:
            cards = "".join(
                f'<div class="kcard"><div class="kn">{esc(cd["nome"])}</div>'
                f'<div class="ks">{esc(cd["setor"])}</div></div>' for cd in c["cards"][:8]) \
                or '<div class="kmore">vazio</div>'
            cols_html += (f'<div class="kcol"><div class="kcol-h">'
                          f'<span><span class="accent" style="background:{c["cor"]}"></span>{esc(c["status"])}</span>'
                          f'<span class="ct">{len(c["cards"])}</span></div>'
                          f'<div class="kbody">{cards}</div></div>')
        st.markdown(f'<div class="kan">{cols_html}</div>', unsafe_allow_html=True)
        st.caption("Arrastar-e-soltar disponível só com o Google Sheets conectado "
                   "(a etapa grava direto na aba do parlamentar)." if not conectado
                   else "Arrastar-e-soltar indisponível neste ambiente.")
        return

    # `clicavel` só quando logado; a observação rápida (conteúdo sensível) só existe
    # no ESTADUAL — o gate por escopo é no Python, porque o flag do componente vale
    # para o quadro inteiro. Sem login, o card não emite clique — arrastar segue igual.
    pode_anotar = bool(st.session_state.get("user"))
    resultado = _kanban_component(colunas=colunas, editable=True, clicavel=pode_anotar,
                                  key="kanban_emendas", default=None)
    if isinstance(resultado, dict):
        nonce = resultado.get("nonce")
        if nonce and nonce != st.session_state.get("kanban_emendas_nonce"):
            st.session_state["kanban_emendas_nonce"] = nonce
            # id do card = escopo + chave (nome estadual OU id federal). Decodifica
            # ANTES de tudo, para rotear tanto o clique quanto o arraste.
            escopo, chave = _decodificar_id_card(resultado.get("org_id", ""))
            # CLIQUE (sem arraste): observação rápida — só estadual, só logado.
            # Tratado ANTES do arraste porque não traz novo_status.
            if resultado.get("action") == "click":
                if chave and pode_anotar and escopo in ("estadual", "federal"):
                    dlg_obs_rapida(escopo, chave)
                return
            novo = str(resultado.get("novo_status", "")).strip()
            # ===== ROTEAMENTO POR ORIGEM DO CARD (Passo 5) =====
            if not chave or novo not in EMENDA_FUNIL_ETAPAS:
                res = {"sucesso": False, "mensagem": "Movimento inválido (etapa fora do funil)."}
            elif escopo == "estadual":               # chave = NOME  → aba Deputados
                res = dados.atualizar_status_deputado(chave, novo)
            elif escopo == "federal":                # chave = ID    → aba Deputados Federais
                res = dados.atualizar_deputado_federal(chave, {"Status CRM": novo})
            else:                                    # senador/futuro: ainda sem gravação
                res = {"sucesso": False,
                       "mensagem": "Escopo ainda sem gravação (ex.: Senador) — etapa não salva."}
            st.session_state["kanban_emendas_msg"] = res
            st.toast(res.get("mensagem", ""))
            st.rerun()  # sucesso confirma a coluna; falha faz o card voltar à origem


# =========================================================================== #
# PROSPECÇÃO · funil de captação manual (emenda / prêmio / patrocínio / outro)
# --------------------------------------------------------------------------- #
# >>> ETAPAS DO FUNIL — LUGAR FÁCIL DE EDITAR. O Fábio pode renomear à vontade;
# "Aprovada" e "Assinada" ele confirmou, "Indicada"/"Paga" são reconstrução do
# ciclo. Mude os nomes aqui (e as cores, se quiser) — o funil e o formulário
# seguem sozinhos. As chaves de PROSPECCAO_ETAPA_COR têm de bater com a lista.
PROSPECCAO_ETAPAS = ["Indicada", "Aprovada", "Assinada", "Paga"]
PROSPECCAO_ETAPA_COR = {"Indicada": "#7C8698", "Aprovada": "#5B9BD5",
                        "Assinada": "#E8B54A", "Paga": "#4ADE80"}
PROSPECCAO_TIPOS = ["Emenda", "Prêmio", "Patrocínio", "Outro"]

# Placar de verba conquistada (verde = etapa final, mesma cor do "Paga").
_PROSPECCAO_PLACAR_CSS = """
<style>
.plc{background:linear-gradient(135deg,rgba(74,222,128,.13),rgba(74,222,128,.02));
  border:1px solid rgba(74,222,128,.32);border-left:3px solid #4ADE80;border-radius:16px;
  padding:20px 22px;margin:6px 0 4px}
.plc-lbl{font-family:var(--mono);font-size:11px;letter-spacing:1.2px;text-transform:uppercase;color:#4ADE80}
.plc-total{font-size:38px;font-weight:800;color:var(--ink);line-height:1.05;margin-top:5px;
  font-variant-numeric:tabular-nums}
.plc-cap{font-size:12.5px;color:var(--muted);margin-top:5px}
.plc-list{margin-top:14px;display:flex;flex-direction:column}
.plc-row{display:flex;align-items:center;justify-content:space-between;gap:14px;
  padding:10px 0;border-top:1px solid var(--line)}
.plc-nome{font-weight:600;color:var(--ink);font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.plc-sub{font-family:var(--mono);font-size:11px;color:var(--dim);margin-top:2px}
.plc-val{font-weight:700;color:#4ADE80;font-size:15px;white-space:nowrap;font-variant-numeric:tabular-nums}
.plc-vazio{margin-top:12px;font-size:13px;color:var(--muted);border-top:1px solid var(--line);padding-top:12px}
</style>
"""


def _prospeccao_etapa_de(status: str) -> str:
    """Enquadra o Status numa etapa canônica (fora da lista cai na primeira)."""
    s = str(status or "").strip()
    return s if s in PROSPECCAO_ETAPAS else PROSPECCAO_ETAPAS[0]


def _funil_prospeccao_colunas(itens: list) -> list:
    """Colunas do kanban a partir dos itens. card.id = ID (chave da aba);
    card.cor = cor da etapa (o kanban esconde 'SCORE' quando o card traz cor)."""
    colunas = []
    for etapa in PROSPECCAO_ETAPAS:
        cards = []
        for it in itens:
            if _prospeccao_etapa_de(it.get("Status", "")) != etapa:
                continue
            resumo = " · ".join(x for x in (str(it.get("Valor", "")).strip(),
                                            str(it.get("Previsão", "")).strip()) if x)
            cards.append({"id": str(it.get("ID", "")).strip(), "status": etapa,
                          "nome": str(it.get("Nome", "")).strip() or "(sem nome)",
                          "setor": str(it.get("Tipo", "")).strip() or "—",
                          "valor": resumo or "—", "cor": PROSPECCAO_ETAPA_COR[etapa]})
        colunas.append({"status": etapa, "cor": PROSPECCAO_ETAPA_COR[etapa], "cards": cards})
    return colunas


def _prospeccao_conquistado(itens: list) -> tuple:
    """Verba JÁ CONQUISTADA = itens na etapa FINAL do funil (a última de
    PROSPECCAO_ETAPAS, hoje 'Paga'). Lê os MESMOS dados da Prospecção — não é
    base separada. Devolve (total_em_reais, lista de itens ganhos)."""
    final = PROSPECCAO_ETAPAS[-1]
    ganhos = [it for it in itens if _prospeccao_etapa_de(it.get("Status", "")) == final]
    total = sum(dados._valor_para_reais(it.get("Valor", "")) for it in ganhos)
    return total, ganhos


def render_prospeccao():
    """Painel próprio de Prospecção: formulário de registro + funil por etapa
    (MESMO kanban drag-and-drop do funil de deputados). Arrastar grava só o
    Status na aba Prospecção, sem tocar nos outros campos."""
    top = st.columns([4, 1])
    top[0].markdown(
        '<div class="phead"><h1 style="color:var(--ink)">Prospecção</h1>'
        '<p>Toda verba que o PFC está buscando — emendas, prêmios, patrocínios — '
        'registrada à mão e acompanhada por etapa.</p></div>', unsafe_allow_html=True)
    if top[1].button("← Central", use_container_width=True, key="prosp_voltar"):
        st.session_state["radar_escolhido"] = None
        st.rerun()
    if not modo_conectado:
        st.caption(HINT_ESCRITA + " — registrar e arrastar gravam na aba Prospecção.")

    # ---- itens lidos UMA vez (os mesmos dados alimentam o placar e o funil) ----
    df_p = dados.carregar_prospeccao()
    itens = df_p.to_dict("records") if not df_p.empty else []

    # ---- PARTE 2 · PLACAR: verba JÁ CONQUISTADA (itens na etapa final) ----
    total_ganho, ganhos = _prospeccao_conquistado(itens)
    etapa_final = PROSPECCAO_ETAPAS[-1]
    if ganhos:
        linhas = ""
        for it in ganhos:
            sub = " · ".join(x for x in (str(it.get("Tipo", "")).strip(),
                             str(it.get("Financiador", "")).strip(),
                             str(it.get("Previsão", "")).strip()) if x)
            linhas += (f'<div class="plc-row"><div style="flex:1;min-width:0">'
                       f'<div class="plc-nome">{esc(str(it.get("Nome", "")))}</div>'
                       f'<div class="plc-sub">{esc(sub)}</div></div>'
                       f'<div class="plc-val">{esc(str(it.get("Valor", "")).strip() or "—")}</div></div>')
    else:
        linhas = (f'<div class="plc-vazio">Nenhuma verba na etapa "{esc(etapa_final)}" ainda. '
                  f'Arraste um item até lá quando o dinheiro entrar — ele vira vitória aqui.</div>')
    st.markdown(
        _PROSPECCAO_PLACAR_CSS +
        '<div class="plc"><div class="plc-head"><div>'
        '<div class="plc-lbl">🏆 Verba já conquistada</div>'
        f'<div class="plc-total">{brl(total_ganho) if total_ganho else "R$ 0"}</div>'
        f'<div class="plc-cap">{len(ganhos)} item(ns) na etapa final · "{esc(etapa_final)}"</div>'
        f'</div></div><div class="plc-list">{linhas}</div></div>', unsafe_allow_html=True)

    # ---- formulário de inserção manual ----
    with st.expander("➕ Registrar nova verba", expanded=False):
        with st.form("form_prospeccao", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            nome = c1.text_input("Nome / origem", placeholder="Emenda Vitor Lippi · Prêmio X…")
            tipo = c2.selectbox("Tipo", PROSPECCAO_TIPOS)
            c3, c4 = st.columns(2)
            valor = c3.text_input("Valor", placeholder="R$ 50 mil")
            financiador = c4.text_input("Deputado / financiador", placeholder="quando aplicável")
            c5, c6 = st.columns(2)
            previsao = c5.text_input("Previsão / data esperada",
                                     placeholder="setembro · após a eleição · pode deixar vazio")
            status = c6.selectbox("Status", PROSPECCAO_ETAPAS)
            obs = st.text_area("Observações", height=70)
            enviar = st.form_submit_button("Adicionar à prospecção", type="primary",
                                           use_container_width=True, disabled=not modo_conectado)
        if enviar:
            res = dados.adicionar_prospeccao({
                "Nome": nome, "Tipo": tipo, "Valor": valor, "Financiador": financiador,
                "Previsão": previsao, "Status": status, "Observações": obs})
            (st.success if res["sucesso"] else st.error)(res["mensagem"])
            if res["sucesso"]:
                st.rerun()

    # ---- PARTE 1 · funil por etapa (reusa o kanban do funil de deputados) ----
    _mostrar_resultado(st.session_state.pop("kanban_prosp_msg", None))
    st.markdown('<div style="font-family:var(--mono);font-size:11px;letter-spacing:1px;'
                'text-transform:uppercase;color:var(--dim);margin:8px 0 10px">'
                f'{len(itens)} verba(s) em prospecção · arraste um card para mudar a etapa</div>',
                unsafe_allow_html=True)
    colunas = _funil_prospeccao_colunas(itens)

    if not KANBAN_DND_OK or not modo_conectado:
        cols_html = ""
        for c in colunas:
            cards = "".join(
                f'<div class="kcard"><div class="kn">{esc(cd["nome"])}</div>'
                f'<div class="ks">{esc(cd["setor"])} · {esc(cd["valor"])}</div></div>'
                for cd in c["cards"][:12]) or '<div class="kmore">vazio</div>'
            cols_html += (f'<div class="kcol"><div class="kcol-h"><span>'
                          f'<span class="accent" style="background:{c["cor"]}"></span>{esc(c["status"])}</span>'
                          f'<span class="ct">{len(c["cards"])}</span></div>'
                          f'<div class="kbody">{cards}</div></div>')
        st.markdown(f'<div class="kan">{cols_html}</div>', unsafe_allow_html=True)
        st.caption("Arrastar-e-soltar disponível só com o Google Sheets conectado (a etapa "
                   "grava na aba Prospecção)." if not modo_conectado
                   else "Arrastar-e-soltar indisponível neste ambiente.")
        return

    resultado = _kanban_component(colunas=colunas, editable=True, clicavel=False,
                                  key="kanban_prosp", default=None)
    if isinstance(resultado, dict):
        nonce = resultado.get("nonce")
        if nonce and nonce != st.session_state.get("kanban_prosp_nonce"):
            st.session_state["kanban_prosp_nonce"] = nonce
            id_ = str(resultado.get("org_id", "")).strip()   # id do card = ID do item
            novo = str(resultado.get("novo_status", "")).strip()
            if id_ and novo in PROSPECCAO_ETAPAS:
                res = dados.atualizar_status_prospeccao(id_, novo)
                st.session_state["kanban_prosp_msg"] = res
                st.toast(res.get("mensagem", ""))
            else:
                st.session_state["kanban_prosp_msg"] = {
                    "sucesso": False, "mensagem": "Movimento inválido (etapa fora do funil)."}
            st.rerun()  # sucesso confirma a coluna; falha faz o card voltar à origem


# --------------------------------------------------------------------------- #
# RELATÓRIO DE PRIORIDADES · EMENDAS (tela + PDF)
# ---------------------------------------------------------------------------
# Puxa dados REAIS do levantamento (rankings território/expansão) + o contato
# OFICIAL da ALESP. Território primeiro (quem já atua nos municípios do PFC),
# depois os alvos prioritários de expansão. Autorizado e pago sempre separados
# (nunca somados). A coleta alimenta a tela E o PDF (relatorios.pdf_emendas).
# --------------------------------------------------------------------------- #


def render_relatorio_emendas():
    st.markdown(
        '<div class="phead" style="margin-bottom:6px"><h1 style="color:var(--ink)">'
        'Relatório de Prioridades</h1></div>', unsafe_allow_html=True)

    # Filtro de escopo compartilhado (Passos 3/5), default Geral: o relatório e o
    # botão de imprimir passam a cobrir todos os escopos, respeitando a escolha.
    st.session_state.setdefault("emenda_escopo_filtro", "Geral")
    escopo_sel = st.segmented_control(
        "Escopo", options=["Geral", "Estadual", "Federal", "Senador"],
        key="emenda_escopo_filtro", label_visibility="collapsed") or "Geral"

    # Seção 1 = CRM por escopo (unificado); Seção 2 = levantamento de execução,
    # SÓ quando o escopo inclui estadual (Geral/Estadual).
    regs = carregar_parlamentares(escopo_sel)
    linhas = itens_relatorio_parlamentares(regs)
    cont = resumo_relatorio_parlamentares(regs)
    inclui_estadual = escopo_sel in ("Geral", "Estadual")
    territorio, expansao = _itens_relatorio_emendas() if inclui_estadual else ([], [])

    if not linhas and not territorio and not expansao:
        st.info("Escopo Senador ainda sem base — em breve." if escopo_sel == "Senador"
                else "Sem parlamentares no CRM deste escopo e levantamento ainda não "
                     "gerado (rode `python -m src.emendas`).")
        return

    agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    resumo = (f"{cont['total']} parlamentar(es) · {cont['em_articulacao']} em articulação · "
              f"{cont['reunioes']} reunião(ões) · {cont['aprovadas']} aprovada(s).")
    top = st.columns([3, 1])
    top[0].caption(f"🗓️ Gerado em {agora} · {resumo}")
    # UM único botão de imprimir: um PDF com as duas seções, respeitando o filtro.
    pdf = relatorios.pdf_parlamentares(
        linhas, resumo, agora, escopo_sel=escopo_sel,
        levantamento=(territorio, expansao) if inclui_estadual else None)
    top[1].download_button(
        "⬇ Baixar PDF", data=pdf,
        file_name=f"PFC_Relatorio_Emendas_{slug(escopo_sel)}_{datetime.date.today():%Y-%m-%d}.pdf",
        mime="application/pdf", use_container_width=True)

    st.markdown(
        '<style>'
        '.rp{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}'
        '.rp th{font-family:var(--mono);font-size:10px;letter-spacing:.6px;text-transform:uppercase;'
        'color:var(--dim);text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}'
        '.rp td{padding:11px 10px;border-bottom:1px solid var(--line);color:var(--muted);vertical-align:top}'
        '.rp .rp-n{font-family:var(--mono);color:var(--dim);width:34px}'
        '.rp .rp-nome{color:var(--ink);font-weight:600}'
        '.rp .rp-sub{font-family:var(--mono);font-size:11px;color:var(--dim);margin-top:2px}'
        '</style>', unsafe_allow_html=True)

    # ===== Seção 1 — CRM por escopo (todos os escopos do filtro) =====
    st.markdown('<div style="font-weight:700;font-size:15px;color:var(--ink);margin-top:8px">'
                '1. Parlamentares no CRM</div>'
                '<div style="font-size:12.5px;color:var(--dim);margin:2px 0 4px">Cada valor é '
                'rotulado pelo seu tipo (execução · sugerido · CRM) e nunca é somado entre '
                'escopos.</div>', unsafe_allow_html=True)
    st.markdown(_tabela_parlamentares_html(linhas) if linhas
                else '<div style="color:var(--dim);font-size:13px">Nenhum parlamentar neste escopo.</div>',
                unsafe_allow_html=True)

    # ===== Seção 2 — levantamento de execução (estadual), quando aplicável =====
    if inclui_estadual and (territorio or expansao):
        st.markdown('<div style="font-weight:700;font-size:15px;color:var(--ink);margin-top:22px">'
                    '2. Levantamento de execução — quem abordar (estadual)</div>'
                    '<div style="font-size:12.5px;color:var(--dim);margin:2px 0 4px">Execução real '
                    '2023–2025 (Transparência SP). Autorizado e pago separados, nunca somados.</div>',
                    unsafe_allow_html=True)
        st.markdown('<div style="font-weight:600;font-size:13px;color:var(--ink);margin-top:10px">'
                    '2.1 Abordar já — território do PFC</div>', unsafe_allow_html=True)
        st.markdown(_tabela_emendas_html(territorio) if territorio
                    else '<div style="color:var(--dim);font-size:13px">Ninguém no território ainda.</div>',
                    unsafe_allow_html=True)
        st.markdown('<div style="font-weight:600;font-size:13px;color:var(--ink);margin-top:14px">'
                    '2.2 Cortejar — fora do território</div>', unsafe_allow_html=True)
        st.markdown(_tabela_emendas_html(expansao) if expansao
                    else '<div style="color:var(--dim);font-size:13px">Sem alvos de expansão.</div>',
                    unsafe_allow_html=True)
        st.caption("Contato oficial da ALESP (gabinete) — não o pessoal do relacionamento.")


def _argumento_federal(dep: dict) -> str:
    """Melhor gancho de abordagem do FEDERAL, do sinal mais forte ao mais fraco,
    só com dado real (base regional, proximidade, aderência, estratégia). Sem
    gancho territorial, é honesto — nunca inventa."""
    base = str(dep.get("base", "")).strip()
    prox = str(dep.get("proximidade", "")).strip()
    ader = dep.get("ader", 0)
    terr = slug(f"{base} {prox}")
    # município do PFC OU a região-sede (Sorocaba/RMS) citados no território?
    termos = _municipios_pfc_lista() + ["Sorocaba", "Região Metropolitana de Sorocaba", "RMS"]
    tem_regiao = any(slug(t) and slug(t) in terr for t in termos)
    if tem_regiao:
        extra = f" Aderência {ader}/100." if ader else ""
        return (f"Base em {base or prox} — território-sede do PFC (Sorocaba/RMS), "
                f"encaixe territorial forte.{extra}")
    if prox:
        return (f"Proximidade territorial: {prox}. Vale abrir pela agenda regional do PFC.")
    if ader >= 80:
        return (f"Aderência ao PFC alta ({ader}/100) — perfil fortemente alinhado, "
                f"mesmo sem base direta na nossa região.")
    if str(dep.get("estrategia", "")).strip():
        return f"Abordagem sugerida (curada): {dep['estrategia'].strip()[:170]}"
    return ("Sem gancho territorial forte pelos dados atuais — abrir pela pauta de "
            "educação científica do PFC.")


def _resumo_federal_dados(dep: dict) -> dict:
    """Dicionário para o PDF federal (relatorios.pdf_resumo_federal)."""
    return {
        "deputado": dep["nome"], "partido": dep["partido"], "base": dep["base"],
        "score": str(dep["score"]), "aderencia": str(dep["ader"]),
        "status_crm": dep.get("status") or "—", "argumento": _argumento_federal(dep),
        "valor_sugerido": dep["valor_sugerido"], "estrategia": dep["estrategia"],
        "gabinete_camara": dep["gabinete_camara"], "telefone": dep["telefones"],
        "email": dep["email"], "fonte_camara": dep["fonte_camara"],
        "whatsapp": dep["whatsapp"], "instagram": dep["instagram"],
    }


@st.dialog("Dossiê do deputado federal", width="large")
def dlg_deputado_federal(dep: dict) -> None:
    breadcrumb("Federal", dep["nome"])
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">'
        f'<span style="font-size:20px;font-weight:700;color:var(--ink)">{esc(dep["nome"])}</span>'
        f'<span style="font-family:var(--mono);font-size:12px;color:var(--dim)">'
        f'{esc(dep["partido"])} · Câmara · {esc(dep["base"]) or "base —"}</span></div>'
        f'<div style="font-family:var(--mono);font-size:11px;color:var(--dim);margin-top:8px">'
        f'score <b style="color:{_cor_score(dep["score"])}">{dep["score"]}</b> · '
        f'aderência {dep["ader"]}/100 · chance de emenda {dep["chance"]}%</div>',
        unsafe_allow_html=True)

    # PDF resumo (federal) — reusa o ReportLab dos relatórios.
    try:
        _pdf = relatorios.pdf_resumo_federal(_resumo_federal_dados(dep),
                                             datetime.date.today().strftime("%d/%m/%Y"))
        st.download_button("Resumo para reunião (PDF)", data=_pdf,
                           file_name=f"resumo-federal-{slug(dep['nome'])}.pdf",
                           mime="application/pdf", use_container_width=True,
                           key=f"pdf_fed_{slug(dep['nome'])}",
                           help="Página limpa com tudo do deputado federal, para levar à reunião.")
    except Exception as e:  # PDF nunca derruba o dossiê
        st.caption(f"Não consegui gerar o PDF agora: {e}")

    # Melhor gancho de abordagem.
    st.markdown(
        '<div style="background:linear-gradient(135deg,rgba(139,123,240,.16),rgba(139,123,240,.03));'
        'border:1px solid rgba(139,123,240,.34);border-left:3px solid #8B7BF0;border-radius:12px;'
        'padding:14px 16px;margin:18px 0 4px">'
        '<div style="font-family:var(--mono);font-size:10px;letter-spacing:1px;text-transform:uppercase;'
        'color:#b7abff;margin-bottom:7px">Melhor gancho de abordagem</div>'
        f'<div style="font-size:15.5px;line-height:1.5;color:var(--ink);font-weight:500">'
        f'{esc(_argumento_federal(dep))}</div></div>', unsafe_allow_html=True)

    # Valor SUGERIDO (faixa/potencial) — nunca pago/autorizado.
    st.markdown(
        '<div class="dd-box aut" style="margin-top:14px"><div class="k">Valor sugerido · potencial</div>'
        f'<div class="v" style="color:#b7abff">{esc(dep["valor_sugerido"]) or "—"}</div>'
        '<div class="n">faixa de potencial de emenda (mín–máx), curada à mão — não é execução</div></div>',
        unsafe_allow_html=True)

    # Estratégia + emenda/ação + gabinete.
    linhas = [("Estratégia PFC", esc(dep["estrategia"]) or "—"),
              ("Emenda / ação sugerida", esc(dep["emenda"]) or "—"),
              ("Gabinete / sala · Câmara", esc(dep["gabinete_camara"]) or "—"),
              ("Base regional", esc(dep["base"]) or "—")]
    st.markdown("".join(
        f'<div style="margin-top:16px"><div style="font-family:var(--mono);font-size:11px;'
        f'letter-spacing:1px;text-transform:uppercase;color:var(--dim);margin-bottom:6px">{lab}</div>'
        f'<div style="font-size:14px;color:var(--ink);line-height:1.6">{val}</div></div>'
        for lab, val in linhas), unsafe_allow_html=True)

    # Diálogo (sensível) — só logado.
    st.markdown('<div style="font-family:var(--mono);font-size:11px;letter-spacing:1px;'
                'text-transform:uppercase;color:var(--dim);margin:18px 0 8px">'
                'Diálogo · andamento da negociação</div>', unsafe_allow_html=True)
    if st.session_state.get("user"):
        dlg = dep["dialogo"] or "Sem anotações de diálogo ainda."
        st.markdown(f'<div style="background:var(--surface2);border:1px solid var(--line);'
                    f'border-left:3px solid #8B7BF0;border-radius:0 10px 10px 0;padding:14px 16px;'
                    f'font-size:14px;line-height:1.6;color:var(--muted);font-style:italic">'
                    f'{esc(dlg)}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-size:13px;color:var(--dim)">🔒 Conteúdo restrito.</div>',
                    unsafe_allow_html=True)

    # Contato oficial · Câmara (público). WhatsApp/Instagram com ressalva "a validar".
    st.markdown('<div style="margin-top:18px;font-family:var(--mono);font-size:11px;'
                'letter-spacing:1px;text-transform:uppercase;color:var(--dim);margin-bottom:7px">'
                'Contato oficial · Câmara</div>', unsafe_allow_html=True)

    def _cf(rot, val, link=None, ressalva=False):
        if not str(val).strip():
            v = '<span style="color:var(--dim)">—</span>'
        elif link:
            v = f'<a href="{esc(link)}" target="_blank" style="color:#b7abff">{esc(val)}</a>'
        else:
            v = esc(val)
        if ressalva:
            v += ' <span style="color:var(--sem-mid);font-size:11px">(a validar)</span>'
        return (f'<div style="display:flex;gap:8px;font-size:13px;margin-bottom:5px">'
                f'<span style="font-family:var(--mono);font-size:10px;letter-spacing:.5px;'
                f'text-transform:uppercase;color:var(--dim);min-width:88px;padding-top:2px">{rot}</span>'
                f'<span style="color:var(--ink)">{v}</span></div>')
    email = dep["email"]
    _wa = dep["whatsapp"]
    _ig = dep["instagram"]
    _val = lambda x: str(x).strip().lower() in ("a validar", "avalidar", "validar")
    st.markdown(
        '<div style="background:var(--surface2);border:1px solid var(--line);'
        'border-left:3px solid #8B7BF0;border-radius:0 10px 10px 0;padding:12px 15px">'
        + _cf("Gabinete/sala", dep["gabinete_camara"])
        + _cf("Telefone", dep["telefones"])
        + _cf("Email", email, link=(f"mailto:{email}" if email else None))
        + _cf("Página", "abrir no site da Câmara" if dep["fonte_camara"] else "", link=dep["fonte_camara"])
        + (_cf("WhatsApp", _wa, ressalva=_val(_wa)) if _wa else "")
        + (_cf("Instagram", _ig, ressalva=_val(_ig)) if _ig else "")
        + '</div>'
        '<div style="font-size:11px;color:var(--dim);margin-top:6px">Contato público de gabinete '
        '(Câmara). WhatsApp/Instagram marcados <b>a validar</b> não são confirmados.</div>',
        unsafe_allow_html=True)

    # ---- EDIÇÃO do CRM (sensível) — grava por ID na aba Deputados Federais ----
    if st.session_state.get("user"):
        etapa_atual = _etapa_de_status(dep["status"])
        idx_status = (EMENDA_FUNIL_ETAPAS.index(etapa_atual)
                      if etapa_atual in EMENDA_FUNIL_ETAPAS else 0)
        idx_temp = _TEMP_ORDEM.index(dep["temp"]) if dep["temp"] in _TEMP_ORDEM else 0
        k = slug(dep["nome"])
        st.markdown('<div style="margin-top:22px;padding-top:18px;border-top:1px solid var(--line);'
                    'font-family:var(--mono);font-size:11px;letter-spacing:1px;text-transform:uppercase;'
                    'color:#8B7BF0">✎ Atualizar relacionamento</div>', unsafe_allow_html=True)
        ce1, ce2 = st.columns(2)
        novo_status = ce1.selectbox("Status · etapa do funil", EMENDA_FUNIL_ETAPAS,
                                    index=idx_status, key=f"edf_status_{k}")
        nova_temp = ce2.selectbox("Temperatura", _TEMP_ORDEM, index=idx_temp, key=f"edf_temp_{k}")
        novo_dialogo = st.text_area("Diálogo · anotações de negociação", value=dep["dialogo"],
                                    height=120, key=f"edf_dialogo_{k}")
        nova_obs = st.text_area("Registro de reunião / próximos passos", value=dep["obs"],
                                height=80, key=f"edf_obs_{k}")
        if st.button("Salvar alterações", type="primary", use_container_width=True,
                     key=f"edf_salvar_{k}"):
            campos = {}
            if novo_status != etapa_atual:
                campos["Status CRM"] = novo_status
            if nova_temp != dep["temp"]:
                campos["Temperatura"] = f"{_TEMP_EMOJI[nova_temp]} {nova_temp}"
            if novo_dialogo.strip() != dep["dialogo"]:
                campos["Diálogo"] = novo_dialogo.strip()
            if nova_obs.strip() != dep["obs"]:
                campos["Observações"] = nova_obs.strip()
            if not campos:
                st.info("Nenhuma alteração para salvar.")
            else:
                res = dados.atualizar_deputado_federal(dep["id"], campos)
                if res.get("sucesso"):
                    st.success(f"✓ {res['mensagem']} Os demais campos foram preservados.")
                    st.toast("Deputado federal atualizado no Google Sheets.")
                    st.caption("Feche o dossiê para ver a lista e o funil já atualizados.")
                else:
                    st.warning(res.get("mensagem", "Não foi possível gravar."))
        st.caption("🔒 Edição restrita à equipe logada · grava na aba Deputados Federais. "
                   "Score/estratégia/contato oficial não se editam aqui.")
    else:
        st.caption("ℹ️ A edição do relacionamento é restrita à equipe logada.")


def _abrir_dossie_parlamentar(r: dict) -> None:
    """Abre o dossiê CERTO conforme o escopo do registro unificado (usa o _raw
    original, então cada dossiê recebe exatamente o dicionário que já esperava)."""
    if r.get("escopo") == "federal":
        dlg_deputado_federal(dict(r["_raw"]))
    else:
        dlg_deputado(dict(r["_raw"]))


def _render_capa_geral(escopo_sel: str) -> None:
    """CAPA GERAL da Visão geral (Passo 3): o MESMO layout rico da capa estadual
    (herói, KPIs, termômetro, tabela por prioridade), agora alimentado pela
    fundação unificada — todos os escopos juntos, cada linha com o SELO de escopo.

    Só troca a fonte de dados (carregar_parlamentares) e adiciona os selos; a
    lógica de herói/KPIs/termômetro (pura) vive em capa_payload_parlamentares.
    Score federal nunca recalculado. A capa NÃO exibe nem soma valores
    (chance/aderência/status só) — a regra de ouro fica naturalmente respeitada
    aqui; onde há valor (dossiê e diálogos) ele já sai rotulado pelo seu tipo."""
    regs = carregar_parlamentares(escopo_sel)
    if not regs:
        _emendas_v2(data={"deps": [], "hero": {}, "temperatura": [], "kpis": [], "modo": "visao"},
                    key="emendas_v2", on_acao_change=lambda: None)
        st.info("Nenhum parlamentar neste escopo ainda.")
        return

    filtro = st.session_state.get("emenda_filtro_temp")
    ctx = capa_payload_parlamentares(regs, filtro, escopo_sel)
    top = ctx["top"]
    regs_view = ctx["regs_view"]

    if filtro:
        c1, c2 = st.columns([3, 1])
        c1.markdown(
            f'<div style="display:flex;align-items:center;gap:9px;font-size:13.5px;color:var(--ink)">'
            f'<span style="font-family:var(--mono);font-size:10.5px;letter-spacing:.6px;'
            f'text-transform:uppercase;color:var(--dim)">Filtrando por</span>'
            f'<span style="background:{_TEMP_COR[filtro]}22;color:{_TEMP_COR[filtro]};font-weight:600;'
            f'padding:4px 12px;border-radius:20px">{_TEMP_EMOJI[filtro]} {esc(filtro)} · '
            f'{len(regs_view)} parlamentar(es)</span></div>',
            unsafe_allow_html=True)
        if c2.button("✕ Limpar filtro", key="em_limpar_filtro", use_container_width=True):
            st.session_state.pop("emenda_filtro_temp", None)
            st.rerun()

    res = _emendas_v2(data=ctx["payload"], key="emendas_v2", on_acao_change=lambda: None)
    ac = getattr(res, "acao", None)
    if not isinstance(ac, dict):
        return
    if ac.get("n") == st.session_state.get("_emenda_nonce"):
        return  # já processado neste ciclo
    st.session_state["_emenda_nonce"] = ac.get("n")
    t, i = ac.get("t"), ac.get("i")
    if t == "dep" and isinstance(i, int) and 0 <= i < len(regs_view):
        _abrir_dossie_parlamentar(regs_view[i])
    elif t == "top":
        _abrir_dossie_parlamentar(top)
    elif t == "kpi" and ac.get("k") == "aprovadas":
        dlg_emendas_aprovadas(ctx["lista_aprovadas"])
    elif t == "kpi" and ac.get("k") == "reunioes":
        dlg_reunioes_ativas(ctx["lista_reunioes"])
    elif t == "articulacao":
        dlg_em_articulacao(ctx["em_articulacao"])
    elif t == "temp" and ac.get("temp") in _TEMP_ORDEM:
        novo = ac["temp"]
        # clicar na faixa já ativa desliga o filtro
        if st.session_state.get("emenda_filtro_temp") == novo:
            st.session_state.pop("emenda_filtro_temp", None)
        else:
            st.session_state["emenda_filtro_temp"] = novo
        st.rerun()


def render_emendas():
    """Painel do radar de Emendas Parlamentares (CRM de deputados)."""
    st.markdown(_EMENDAS_CHROME_CSS, unsafe_allow_html=True)
    # Passo 8: eixo de estado ÚNICO. O escopo é escolhido pelo segmented control de
    # CONTEÚDO (emenda_escopo_filtro) em cada tela — não mais pela sidebar. O antigo
    # emenda_escopo e o early-return pro painel Federal foram aposentados; o conteúdo
    # federal chega pelas telas unificadas (filtro=Federal/Geral).
    emenda_page = st.session_state.setdefault("emenda_page", "Visão geral")
    modo = _modo_emenda(emenda_page)
    render_topnav("emendas", emenda_page.upper())
    render_sidebar_emendas()

    hora = datetime.datetime.now().hour
    saud = "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"
    primeiro = USER["nome"].split()[0]
    subttl = {"Visão geral": "Articulação política",
              "Descobrir": "Levantamento de emendas · quem abordar",
              "Territórios em Aberto": "Oportunidade de captação · sem emenda edu/social",
              "Funil de negociação": "Negociações por temperatura",
              "Relatório": "Relatório de Prioridades · quem abordar"}.get(emenda_page, "")
    st.markdown(
        f'<div class="topbar"><div>'
        f'<div class="hi">{saud}, {esc(primeiro)}</div>'
        f'<div class="cr" style="margin-top:6px">{esc(subttl)}</div></div>'
        f'<div class="tr-r"><div class="live">ALESP + CÂMARA</div></div></div>'
        '<div class="hr-line"></div>',
        unsafe_allow_html=True,
    )

    # Tela de PLANEJAMENTO (levantamento de emendas), separada do CRM dos 16.
    if modo == "descobrir":
        render_descobrir()
        return
    # Municípios do PFC sem emenda edu/social + candidatos da região.
    if modo == "orfaos":
        render_orfaos()
        return
    # Funil de negociação com drag-and-drop (grava a etapa na aba Deputados).
    if modo == "funil":
        render_funil_emendas()
        return
    # Relatório de Prioridades: quem abordar (do levantamento), tela + PDF.
    if modo == "relatorio":
        render_relatorio_emendas()
        return

    # ===== Visão geral = CAPA GERAL (todos os escopos juntos) =====
    # Controle de Escopo no topo do CONTEÚDO (não na sidebar). Geral (padrão) mostra
    # os três escopos na MESMA capa rica, com o selo de escopo em cada linha;
    # Estadual/Federal filtram; Senador = vazio elegante.
    if modo == "visao":
        st.session_state.setdefault("emenda_escopo_filtro", "Geral")
        escopo_sel = st.segmented_control(
            "Escopo", options=["Geral", "Estadual", "Federal", "Senador"],
            key="emenda_escopo_filtro", label_visibility="collapsed") or "Geral"
        st.caption("Escopo · Geral junta os três · Estadual / Federal / Senador filtram.")
        if escopo_sel == "Senador":
            st.markdown(_DESCOBRIR_CSS, unsafe_allow_html=True)
            st.markdown(
                '<div class="dd-intro">Escopo <b>Senador</b> ainda sem cadastro. O lugar já '
                'existe — quando a tabela do Fábio entrar, os senadores aparecem aqui na '
                'mesma capa geral. Nada quebra por estar vazio.</div>', unsafe_allow_html=True)
            return
        _render_capa_geral(escopo_sel)
        return


# =========================================================================== #
# BARRA DE NAVEGAÇÃO SUPERIOR FIXA (global, sempre visível)
# ---------------------------------------------------------------------------
# Fica no topo de todas as telas, independente da sidebar — rede de segurança
# para nunca ficar preso. Traz um seletor de radar estilo Linear/Notion:
# mostra o radar atual e, ao clicar, abre um menu para trocar de radar, voltar
# ao hub ou sair. Componente v2 bidirecional; as ações voltam ao Python.
# Acento por área: âmbar (Captação) · violeta (Emendas).
# =========================================================================== #


_topnav_v2 = components_v2.component("pfc_topnav", css=_TOPNAV_CSS, js=_TOPNAV_JS)


def render_topnav(radar_atual: str, crumb: str = ""):
    """Barra fixa no topo com o seletor de radar. Trata trocar/hub/sair.
    (A sidebar é controlada pela setinha client-side, não pela topnav.)"""
    st.markdown(_TOPNAV_OFFSET_CSS, unsafe_allow_html=True)
    res = _topnav_v2(
        data={"radar": radar_atual, "crumb": crumb,
              "inicial": USER.get("inicial", ""), "email": USER.get("email", "")},
        key="topnav", on_acao_change=lambda: None)
    ac = getattr(res, "acao", None)
    if not isinstance(ac, dict):
        return
    if ac.get("n") == st.session_state.get("_topnav_nonce"):
        return  # já processado (evita reprocessar no rerun seguinte)
    st.session_state["_topnav_nonce"] = ac.get("n")
    t = ac.get("t")
    if t == "radar" and ac.get("v") in ("captacao", "emendas") and ac["v"] != radar_atual:
        st.session_state["radar_escolhido"] = ac["v"]
        st.rerun()
    elif t == "hub":
        st.session_state["radar_escolhido"] = None
        st.rerun()
    elif t == "sair":
        for k in ("user", "page", "login_email", "login_senha", "radar_escolhido"):
            st.session_state.pop(k, None)
        st.rerun()


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
# Hub de entrada: escolha do radar antes do painel (Central de Captação).
# radar_escolhido: None -> hub · "emendas" -> placeholder · "captacao" -> painel
# --------------------------------------------------------------------------- #
st.session_state.setdefault("radar_escolhido", None)
if st.session_state["radar_escolhido"] is None:
    render_hub()
    st.stop()
if st.session_state["radar_escolhido"] == "emendas":
    render_emendas()
    st.stop()
if st.session_state["radar_escolhido"] == "prospeccao":
    render_prospeccao()
    st.stop()


# --------------------------------------------------------------------------- #
# Sidebar de navegação (maquete pfc_app_v3) + top bar
# --------------------------------------------------------------------------- #
_n_naoverif = int((~df[COL_VERIF].apply(verificada_ok)).sum()) if TOTAL else 0
NAV_SECOES = [("Operação", ["Visão geral", "Radar", "Ranking", "Funil", "Relatório"]),
              ("Dados", ["Metodologia", "Verificação"])]
# chave do botão -> ícone (mesma mecânica da sidebar de Emendas)
NAV_ICONES = {**{f"nav_{slug(p)}": slug(p) for p in PAGES},
              "trocar_radar": "trocar-radar", "logout": "sair"}
# chave do botão -> nome no tooltip do modo ícone
NAV_ROTULOS = {**{f"nav_{slug(p)}": p for p in PAGES},
               "trocar_radar": "Trocar radar", "logout": "Sair"}


def _rotulo_nav(p: str) -> str:
    rotulo = p
    if p == "Ranking":
        rotulo += f" · {TOTAL}"
    elif p == "Verificação" and _n_naoverif:
        rotulo += f" · {_n_naoverif}"
    return rotulo


def render_sidebar():
    _preparar_sidebar()
    with st.sidebar:
        st.markdown(f"<style>{css_icones_botoes(NAV_ICONES, NAV_ROTULOS)}</style>",
                    unsafe_allow_html=True)
        st.markdown(_sidebar_toggle_html(), unsafe_allow_html=True)  # recolher/expandir no topo
        st.markdown(
            '<div class="sb-brand"><div class="rings"><span></span><span></span><span></span></div>'
            '<div class="bt">Futuro Cientista<small>CAPTAÇÃO PRIVADA</small></div></div>',
            unsafe_allow_html=True,
        )
        for secao, paginas in NAV_SECOES:
            st.markdown(f'<div class="sb-sec">{secao}</div>', unsafe_allow_html=True)
            for p in paginas:
                st.button(_rotulo_nav(p), key=f"nav_{slug(p)}", use_container_width=True,
                          type="primary" if st.session_state["page"] == p else "secondary",
                          on_click=ir_para, args=(p,))
        status = ('<div class="sf"><span class="d g"></span>SHEETS CONECTADO</div>'
                  if modo_conectado else
                  '<div class="sf"><span class="d r"></span>MODO LOCAL · CSV</div>')
        st.markdown(f'<div class="sb-foot">{status}'
                    '<div class="sf"><span class="d n"></span>ÚLTIMO SCAN · 06:00</div></div>',
                    unsafe_allow_html=True)
        if st.button("Trocar radar", key="trocar_radar", use_container_width=True):
            st.session_state["radar_escolhido"] = None
            st.rerun()
        if st.button("Sair", key="logout", use_container_width=True):
            for k in ("user", "page", "login_email", "login_senha", "radar_escolhido"):
                st.session_state.pop(k, None)
            st.rerun()


def render_header():
    # Cabeçalho da página (rola com o conteúdo). Breadcrumb e avatar agora vivem
    # na barra fixa superior (render_topnav), então aqui fica só a saudação + live.
    hora = datetime.datetime.now().hour
    saud = "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"
    primeiro = USER["nome"].split()[0]
    live = ('<div class="live"><span class="d"></span>RADAR ATIVO</div>' if modo_conectado
            else '<div class="live off">MODO LOCAL · CSV</div>')
    st.markdown(
        f'<div class="topbar"><div>'
        f'<div class="hi">{saud}, {esc(primeiro)}</div></div>'
        f'<div class="tr-r">{live}</div></div>'
        '<div class="hr-line"></div>',
        unsafe_allow_html=True,
    )


render_topnav("captacao", st.session_state["page"].upper())
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

# Cor semântica por etapa (hex direto — dentro dos componentes v2/shadow DOM,
# hex é mais robusto que var()). Mapear=cinza · Prospectar=âmbar ·
# Monitorar=azul · Edital=violeta · Ativo=verde (paleta da maquete).
CORES_ETAPA = {"Mapear": "#7C8698", "Prospectar": "#E8873A",
               "Monitorar": "#5B9BD5", "Edital": "#8B7BF0",
               "Ativo": "#4ADE80"}


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


@st.dialog("Oportunidades encerrando", width="large")
def dlg_encerrando(items: list):
    """Lista TODAS as oportunidades que estão encerrando (prazo confiável a até 7
    dias), da que fecha antes à que fecha depois. Cada uma com seus dados e o
    link oficial — mostra todas de uma vez (não colapsa numa só)."""
    breadcrumb("Visão geral", "Encerrando")
    if not items:
        st.info("Nenhuma oportunidade com prazo confiável nos próximos 7 dias.")
        return
    st.markdown(f'<div style="font-size:13px;color:var(--muted);margin-bottom:4px">'
                f'{len(items)} edital(is) com prazo confiável em até 7 dias — '
                f'do que fecha antes ao que fecha depois.</div>', unsafe_allow_html=True)
    for it in items:
        dias = it.get("dias")
        cor = "var(--sem-urgent)" if isinstance(dias, int) and dias <= 3 else "var(--accent)"
        dias_txt = ("vence hoje" if dias == 0 else f"faltam {dias} dias") \
            if isinstance(dias, int) else "prazo a confirmar"
        valor = str(it.get("valor", "")).strip()
        st.markdown(
            f'<div style="border:1px solid var(--line);border-left:3px solid {cor};'
            f'border-radius:0 10px 10px 0;padding:12px 15px;margin-top:10px">'
            f'<div style="font-size:15px;font-weight:600;color:var(--ink);line-height:1.35">'
            f'{esc(it.get("titulo",""))}</div>'
            f'<div style="font-family:var(--mono);font-size:11px;color:var(--dim);margin-top:6px">'
            f'{esc(it.get("fonte",""))} · encerra {esc(_fmt_prazo(it.get("prazo","")))} · '
            f'<b style="color:{cor}">{dias_txt}</b>'
            + (f' · {esc(valor)}' if valor else "") + '</div></div>',
            unsafe_allow_html=True)
        if str(it.get("link", "")).startswith("http"):
            st.link_button("↗ Abrir página oficial", it["link"], use_container_width=True)


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


_visao_v2 = components_v2.component("pfc_visao", css=_SELO_V2_CSS + _VISAO_V2_CSS,
                                    js=_VISAO_V2_JS.replace("__SELO_FN__", _SELO_JS_FN))


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
    # Encerrando = prazo confiável a até 7 dias. Guarda a LISTA (não só a contagem)
    # para o clique no "N encerrando" mostrar TODAS, não só a primeira.
    encerrando_items = sorted((o for o in ops if isinstance(o["dias"], int)
                               and 0 <= o["dias"] <= 7), key=lambda o: o["dias"])
    encerrando = len(encerrando_items)

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
        "scores": [o["score"] for o in ops[:16]],
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
        elif t == "prazo" and isinstance(i, int) and 0 <= i < len(prazo_items):
            dlg_oportunidade(prazo_items[i])
        elif t == "encerrando" and encerrando_items:
            # clicar no "N encerrando" mostra TODAS as que estão fechando (não só uma)
            dlg_encerrando(encerrando_items)
        elif t == "stage" and k in STATUS_FUNIL:
            dlg_status_list(k)


# =========================================================================== #
# PÁGINA · RANKING (maquete: tabela com ponto por score; linha abre o dossiê)
# =========================================================================== #


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


_radar_v2 = components_v2.component("pfc_radar", css=_SELO_V2_CSS + _RADAR_V2_CSS,
                                    js=_RADAR_V2_JS)

_RADAR_MAX_LISTA = 40  # itens visíveis na lista (o restante fica indicado no rodapé)


def _ordenar_ops(ops: list, modo: str) -> list:
    """Ordena as oportunidades do radar pelo critério escolhido.

    'Dias restantes' = os que fecham ANTES primeiro. A ordem é: abertos por prazo
    crescente (o que encerra antes no topo) -> vencidos (mais recentes primeiro)
    -> 'prazo a confirmar' (sem data confiável) por ÚLTIMO. Assim os que estão
    encerrando ficam à vista, e os sem data não somem nem quebram a ordenação.
    'Valor' = maiores primeiro. 'Score' = relevância (padrão)."""
    if modo == "Dias restantes":
        def _chave(o):
            d = o["dias"]
            if _prazo_confiavel(d):
                return (0, d) if d >= 0 else (1, -d)  # abertos; depois vencidos
            return (2, 0)  # 'a confirmar' no fim
        return sorted(ops, key=_chave)
    if modo == "Valor":
        return sorted(ops, key=lambda o: dados._valor_para_reais(o.get("valor", "")), reverse=True)
    return sorted(ops, key=lambda o: _score_novidade(o["nv"]), reverse=True)


def page_radar():
    _mostrar_resultado(st.session_state.pop("radar_msg", None))
    if not modo_conectado:
        st.caption(HINT_ESCRITA + " — aprovar/descartar grava na aba Novidades_pendentes.")

    ordem = st.radio(
        "Ordenar por", ["Score", "Dias restantes", "Valor"], horizontal=True, key="radar_ordem",
        help="Score = relevância · Dias restantes = os que fecham antes primeiro "
             "(prazo a confirmar vai para o fim) · Valor = maiores primeiro")
    ops = [_op_de_novidade(nv) for nv in dados.carregar_novidades_pendentes()]
    scores_spark = sorted((o["score"] for o in ops), reverse=True)[:16]  # sparkline por score
    ops = _ordenar_ops(ops, ordem)
    visiveis = ops[:_RADAR_MAX_LISTA]
    n_fontes = _n_fontes_radar()
    encerrando = sum(1 for o in ops if _prazo_confiavel(o["dias"]) and 0 <= o["dias"] <= 7)

    def _badge(o):
        """'X DIAS' só com data confiável; estimada vira 'prazo a confirmar'."""
        dias, tem_prazo = o["dias"], bool(str(o["prazo"]).strip())
        if _prazo_confiavel(dias):
            if dias < 0:
                return "VENCIDA", "u", f"prazo encerrou há {-dias} dia(s)"
            return f"{dias} dias", ("u" if dias <= 7 else "s"), ""
        if tem_prazo:
            return "a confirmar", "n", "data possivelmente estimada — confira na página oficial"
        return "sem prazo", "n", ""

    itens = []
    for o in visiveis:
        txt, cls, tip = _badge(o)
        itens.append({"score": o["score"], "fonte": o["fonte"], "titulo": o["titulo"],
                      "valor": o["valor"], "badge_txt": txt, "badge_cls": cls, "badge_tip": tip})

    res = _radar_v2(data={"itens": itens, "ocultos": max(0, len(ops) - len(visiveis)),
                          "scores": scores_spark,
                          "foot": {"fila": len(ops), "encerrando": encerrando,
                                   "fontes": n_fontes}},
                    key="radar_v2", on_acao_change=lambda: None)
    ac = getattr(res, "acao", None)
    if isinstance(ac, dict):
        if ac.get("t") == "op":
            i = ac.get("i")
            if isinstance(i, int) and 0 <= i < len(visiveis):
                dlg_oportunidade(visiveis[i])
        elif ac.get("t") == "encerrando":
            # clicar no "N encerrando" reordena a lista pelos que fecham antes
            st.session_state["radar_ordem"] = "Dias restantes"
            st.rerun()

    # Cadastro no alerta de editais por e-mail (o radar 06:00 envia os avisos).
    with st.expander("Receber alertas de editais por e-mail"):
        st.caption("Avisamos por e-mail quando um edital com data confiável estiver a "
                   "14 dias ou menos do prazo. Um aviso por edital, sem repetição.")
        with st.form("form_alerta_editais", clear_on_submit=True):
            email_in = st.text_input("Seu e-mail", placeholder="voce@exemplo.com")
            c1, c2 = st.columns(2)
            inscrever = c1.form_submit_button("Inscrever", use_container_width=True)
            sair = c2.form_submit_button("Sair da lista", use_container_width=True)
        if inscrever or sair:
            res_al = (dados.adicionar_inscrito if inscrever else dados.desinscrever)(email_in)
            (st.success if res_al["sucesso"] else st.error)(res_al["mensagem"])


# =========================================================================== #
# PÁGINA · FUNIL
# =========================================================================== #
# Cores das colunas do kanban (paleta da maquete pfc_app_v3).
ACENTOS_HEX = {"Mapear": "#7C8698", "Prospectar": "#E8873A", "Monitorar": "#5B9BD5",
               "Edital": "#8B7BF0", "Ativo": "#4ADE80"}


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


# --------------------------------------------------------------------------- #
# RELATÓRIO DE PRIORIDADES · CAPTAÇÃO (tela + PDF)
# ---------------------------------------------------------------------------
# Puxa dados REAIS: fila do Radar (novidades pendentes) + editais da base
# (status 'Edital') e da aba Editais_Privados. Respeita a regra de acurácia
# (regra 3): data fora da janela confiável vira "prazo a confirmar", nunca um
# número de dias que pode estar chutado. A coleta é única e alimenta a tela E
# o PDF (relatorios.pdf_captacao) — as duas visões nunca divergem.
# --------------------------------------------------------------------------- #


def _itens_relatorio_captacao() -> list[dict]:
    """Lista unificada de oportunidades COM prazo, ordenada por urgência.
    Fontes reais: fila do Radar + editais da base/privados. Dedupe por nome."""
    hoje = datetime.date.today()
    brutos = []
    for nv in dados.carregar_novidades_pendentes():
        op = _op_de_novidade(nv)
        if str(op.get("prazo", "")).strip():
            brutos.append((op["titulo"], op["fonte"], op["valor"], op["prazo"], op["dias"]))
    for e in _coletar_editais():
        if not (e.get("data") or str(e.get("raw", "")).strip()):
            continue
        dias = (e["data"] - hoje).days if e.get("data") else None
        brutos.append((e["nome"], "Base de captação", e.get("valor", 0),
                       e.get("raw", ""), dias))

    vistos, itens = set(), []
    for nome, inst, valor, prazo, dias in brutos:
        chave = str(nome).strip().lower()
        if not chave or chave in vistos:
            continue
        # Já vencido com data confiável não é prioridade "perto do prazo": fora.
        # (Datas fora da janela confiável — inclusive chutes de ano — caem como
        # "a confirmar", nunca como um número de dias que pode estar errado.)
        if _prazo_confiavel(dias) and isinstance(dias, int) and dias < 0:
            continue
        vistos.add(chave)
        futuro = _prazo_confiavel(dias) and isinstance(dias, int) and dias >= 0
        itens.append({
            "nome": str(nome).strip(), "instituicao": str(inst).strip(),
            "valor": _valor_rel(valor),
            "data_final": _fmt_prazo(prazo) if futuro else "a confirmar",
            "dias_txt": _dias_texto(dias) if futuro else "prazo a confirmar",
            "urgente": bool(futuro and dias <= 7),
            "confiavel": futuro,
            "_ordem": dias if futuro else 10 ** 6,
        })
    itens.sort(key=lambda it: it["_ordem"])
    return itens


def page_relatorio():
    st.markdown(
        '<div class="phead"><h1>Relatório de Prioridades</h1>'
        '<p>oportunidades da Captação ordenadas por urgência de prazo — na tela e em PDF</p></div>',
        unsafe_allow_html=True,
    )
    itens = _itens_relatorio_captacao()
    agora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    n_conf = sum(1 for it in itens if it["confiavel"])
    resumo = (f"{len(itens)} oportunidade(s) com prazo · {n_conf} com data confiável · "
              f"{len(itens) - n_conf} a confirmar.")

    top = st.columns([3, 1])
    top[0].caption(f"🗓️ Gerado em {agora} · {resumo}")
    if itens:
        pdf = relatorios.pdf_captacao(itens, agora, resumo=resumo)
        top[1].download_button("⬇ Baixar PDF", data=pdf,
                               file_name=f"PFC_Prioridades_Captacao_{datetime.date.today():%Y-%m-%d}.pdf",
                               mime="application/pdf", use_container_width=True)

    if not itens:
        st.info("Nenhuma oportunidade com prazo cadastrado no momento. "
                "Assim que o Radar trouxer editais com data, eles aparecem aqui.")
        return

    linhas = ""
    for i, it in enumerate(itens, start=1):
        cor = "#F0663F" if it["urgente"] else ("var(--ink)" if it["confiavel"] else "var(--dim)")
        linhas += (
            f'<tr><td class="rp-n">{i}</td>'
            f'<td><div class="rp-nome">{esc(it["nome"])}</div>'
            f'<div class="rp-sub">{esc(it["instituicao"])}</div></td>'
            f'<td>{esc(it["valor"])}</td>'
            f'<td>{esc(it["data_final"])}</td>'
            f'<td style="color:{cor};font-weight:600">{esc(it["dias_txt"])}</td></tr>')
    st.markdown(
        '<style>'
        '.rp{width:100%;border-collapse:collapse;font-size:13.5px;margin-top:6px}'
        '.rp th{font-family:var(--mono);font-size:10px;letter-spacing:.6px;text-transform:uppercase;'
        'color:var(--dim);text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}'
        '.rp td{padding:11px 10px;border-bottom:1px solid var(--line);color:var(--muted);vertical-align:top}'
        '.rp .rp-n{font-family:var(--mono);color:var(--dim);width:34px}'
        '.rp .rp-nome{color:var(--ink);font-weight:600}'
        '.rp .rp-sub{font-family:var(--mono);font-size:11px;color:var(--dim);margin-top:2px}'
        '</style>'
        '<table class="rp"><tr><th>#</th><th>Oportunidade / Instituição</th><th>Valor</th>'
        f'<th>Data final</th><th>Prazo</th></tr>{linhas}</table>',
        unsafe_allow_html=True)
    st.caption("Só prazos que ainda vão vencer. As linhas em cinza são \"prazo a confirmar\": "
               "a data não é confiável e não mostramos um número de dias que pode estar "
               "errado. As urgentes (≤ 7 dias) aparecem em vermelho. Já vencidos ficam de "
               "fora. Uma data errada é pior que nenhuma.")


# =========================================================================== #
# PÁGINA · METODOLOGIA
# =========================================================================== #


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
         "Funil": page_funil, "Relatório": page_relatorio,
         "Metodologia": page_metodo, "Verificação": page_verificacao}
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
