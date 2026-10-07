"""Legislatura 2027 — a bancada eleita em 2026, lida pelo olho do PFC.

Junta três coisas que já existem e NÃO recalcula nenhuma delas:
  1. o resultado oficial do TRE-SP (src/eleicoes.py, data/eleicoes/);
  2. o levantamento de emendas ESTADUAIS (rankings território/expansão, score e
     autorizado/pago já calculados por src/emendas.py);
  3. o levantamento de emendas FEDERAIS (data/emendas_federais_score_execucao.csv,
     empenhado/pago edu-social por deputado).

Pergunta que a tela responde: "a partir de 1º/fev/2027, com quem eu falo — e em
que ordem?". A ORDEM é por faixas, não por uma nota nova:
  1  já investe no território do PFC (histórico de emenda edu/social nos nossos municípios)
  2  histórico edu/social forte, fora do território
  3  tem mandato hoje, mas sem emenda edu/social no levantamento
  4  chega em 2027 (sem histórico — a relação começa do zero)
  5  a conferir (o nome casa com mais de um candidato)
Dentro da faixa: o score que JÁ existe (estadual ou federal) e, sem ele, os votos.
Partido é campo factual do documento — nunca entra na ordem (regra 5d).

E a outra metade da transição: quem SAI (não reeleito) e tem histórico segue
indicando as emendas do Orçamento 2027 até 31/jan — é a última janela.

PURO: sem rede, sem Streamlit. `carregar_fontes()` lê os CSVs; `montar()` decide.
"""
from __future__ import annotations

import csv
import datetime
import os

from src import eleicoes

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(BASE, "data")
CSV_TITULARES = os.path.join(_DATA, "deputados_alesp_titulares.csv")
CSV_TERRITORIO = os.path.join(_DATA, "emendas_ranking_pfc_territorio.csv")
CSV_EXPANSAO = os.path.join(_DATA, "emendas_ranking_pfc_expansao.csv")
CSV_FEDERAL = os.path.join(_DATA, "emendas_federais_score_execucao.csv")

POSSE = datetime.date(2027, 2, 1)
CASAS = {"DEPUTADO ESTADUAL": "ALESP", "DEPUTADO FEDERAL": "Câmara", "SENADOR": "Senado"}

FAIXAS = {
    1: "Já investe no território do PFC",
    2: "Histórico edu/social forte, fora do território",
    3: "Mandato atual, sem emenda edu/social no levantamento",
    4: "Chega em 2027",
    5: "A conferir",
}
ORIGENS = {
    "reeleito": "Reeleito",
    "outra_casa": "Muda de casa",
    "novo": "Novo",
    "a_conferir": "A conferir",
}


# ---------------------------------------------------------------- leitura
def _ler(caminho: str) -> list[dict]:
    try:
        with open(caminho, encoding="utf-8-sig", newline="") as f:
            return [dict(r) for r in csv.DictReader(f)]
    except (FileNotFoundError, OSError):
        return []


def carregar_fontes() -> dict:
    """Tudo o que `montar` precisa, lido do disco. Arquivo ausente -> lista vazia."""
    return {"candidatos": eleicoes.carregar(), "titulares": _ler(CSV_TITULARES),
            "territorio": _ler(CSV_TERRITORIO), "expansao": _ler(CSV_EXPANSAO),
            "federal": _ler(CSV_FEDERAL)}


# ---------------------------------------------------------------- formato
_MINUSC = {"da", "de", "do", "das", "dos", "e"}


def nome_bonito(s) -> str:
    """'EDUARDO MATARAZZO DA SILVA' -> 'Eduardo Matarazzo da Silva'."""
    palavras = str(s or "").split()
    return " ".join(p.lower() if i and p.lower() in _MINUSC else p.capitalize()
                    for i, p in enumerate(palavras))


def partido_curto(cand: dict) -> str:
    """Sigla quando o documento permite; federação pela abreviação oficial que o
    próprio nome traz ("… - FE BRASIL"); senão o nome como está. Nunca deduzido."""
    if cand.get("sigla"):
        return cand["sigla"]
    p = str(cand.get("partido") or "").strip()
    if " - " in p:
        return p.rsplit(" - ", 1)[1].strip()
    return p


def _num(v) -> float:
    try:
        return float(str(v).replace(",", ".")) if str(v).strip() else 0.0
    except ValueError:
        return 0.0


def _brl(v) -> str:
    n = _num(v)
    if n >= 1e6:
        return ("R$ %.1f mi" % (n / 1e6)).replace(".", ",")
    if n >= 1e3:
        return "R$ %d mil" % round(n / 1e3)
    return "R$ %d" % round(n)


def votos_curto(v) -> str:
    """1956238 -> '1,96 mi'; 86893 -> '86,9 mil'; 950 -> '950'."""
    n = _num(v)
    if n >= 1e6:
        return ("%.2f mi" % (n / 1e6)).replace(".", ",")
    if n >= 1e3:
        return ("%.1f mil" % (n / 1e3)).replace(".", ",")
    return "%d" % n


def _muns(txt, limite: int = 3) -> str:
    lista = [nome_bonito(m.strip()) for m in str(txt or "").replace(";", ",").split(",") if m.strip()]
    if len(lista) > limite:
        return ", ".join(lista[:limite]) + f" e mais {len(lista) - limite}"
    return ", ".join(lista)


# ---------------------------------------------------------------- histórico
def _historico_estadual(nome: str, territorio: dict, expansao: dict) -> dict | None:
    """Do levantamento estadual (2023-25). Autorizado e pago SEPARADOS."""
    chave = eleicoes._norm(nome)
    if chave in territorio:
        r = territorio[chave]
        return {"fonte": "estadual", "secao": "territorio", "casa": "ALESP",
                "score": _num(r.get("score_pfc")), "autorizado": _num(r.get("autorizado_pfc")),
                "pago": _num(r.get("pago_pfc")), "municipios": r.get("municipios_pfc", ""),
                "alinhamento": _num(r.get("alinhamento_pct"))}
    if chave in expansao:
        r = expansao[chave]
        muns = r.get("municipios_pfc_diretos") or r.get("municipios_vizinhos") or ""
        return {"fonte": "estadual", "secao": "expansao", "casa": "ALESP",
                "score": _num(r.get("score_expansao")),
                "autorizado": _num(r.get("autorizado_geral_edusoc")),
                "pago": _num(r.get("pago_geral_edusoc")), "municipios": muns,
                "alinhamento": _num(r.get("alinhamento_pct")),
                "camada": r.get("camada", "")}
    return None


def _historico_federal(nome: str, federal: dict) -> dict | None:
    """Do levantamento federal: EMPENHADO e PAGO edu/social, separados."""
    r = federal.get(eleicoes._norm(nome))
    if not r:
        return None
    n_pfc = int(_num(r.get("n_municipios_pfc")))
    return {"fonte": "federal", "secao": "territorio" if n_pfc else "expansao", "casa": "Câmara",
            "score": _num(r.get("score_execucao")), "empenhado": _num(r.get("edusoc_empenhado")),
            "pago": _num(r.get("edusoc_pago")), "municipios": r.get("municipios_pfc", ""),
            "alinhamento": round(_num(r.get("fracao_edusoc")) * 100, 1)}


def _faixa(origem: str, hist: dict | None) -> int:
    if origem == "a_conferir":
        return 5
    if origem == "novo":
        return 4
    if not hist:
        return 3
    return 1 if hist["secao"] == "territorio" else 2


def gancho(p: dict) -> str:
    """Uma frase, só com dado real. Sem histórico, diz isso — nunca inventa."""
    txt = _gancho(p)
    return txt[:1].upper() + txt[1:]


def _gancho(p: dict) -> str:
    h, origem = p.get("historico"), p.get("origem")
    pre = ""
    if origem == "outra_casa" and h:
        pre = f"Vem da {h['casa']}: "
    if origem == "a_conferir":
        return "O nome casa com mais de um candidato — confira antes de procurar."
    if origem == "novo":
        return ("Sem histórico de emendas: a relação começa do zero — "
                "o melhor momento é antes da posse.")
    if not h:
        return "Tem mandato hoje, mas não aparece com emenda edu/social no levantamento 2023-25."
    muns = _muns(h.get("municipios"))
    if h["fonte"] == "estadual":
        if h["secao"] == "territorio":
            return f"{pre}já indicou {_brl(h['autorizado'])} (autorizado) em edu/social para {muns}."
        return (f"{pre}{_brl(h['autorizado'])} autorizados em edu/social "
                f"({h['alinhamento']:.0f}% do que indicou), ainda fora dos nossos municípios.")
    if h["secao"] == "territorio":
        return f"{pre}{_brl(h['empenhado'])} empenhados em edu/social, com emenda em {muns}."
    return (f"{pre}{_brl(h['empenhado'])} empenhados em edu/social "
            f"({h['alinhamento']:.0f}% do que indicou), ainda fora dos nossos municípios.")


def gancho_saida(s: dict) -> str:
    """Quem não se reelegeu e tem histórico: ainda indica o Orçamento 2027."""
    h = s["historico"]
    valor = (f"{_brl(h['autorizado'])} autorizados" if h["fonte"] == "estadual"
             else f"{_brl(h['empenhado'])} empenhados")
    onde = (f" para {_muns(h.get('municipios'))}" if h["secao"] == "territorio" and h.get("municipios")
            else ", fora dos nossos municípios")
    return (f"Mandato até 31/jan: ainda indica emendas do Orçamento 2027. "
            f"Histórico: {valor} em edu/social{onde}.")


# ---------------------------------------------------------------- montagem
def _situacoes(nomes: list[str], cargo: str, candidatos: list[dict], casa_atual: str):
    """{(cargo_eleito, numero): vínculo} + lista de situações de quem está hoje."""
    vinculo, todos = {}, []
    for n in nomes:
        s = eleicoes.situacao_2026(n, cargo, candidatos)
        todos.append((n, s))
        if s["status"] in ("reeleito", "eleito_outro_cargo"):
            vinculo[(s["cargo_2027"], s["numero"])] = {
                "nome_atual": n, "casa_atual": casa_atual,
                "origem": "reeleito" if s["status"] == "reeleito" else "outra_casa"}
        elif s["status"] == "a_conferir":
            for c in s["possiveis"]:
                if eleicoes.eleito(c):
                    vinculo.setdefault((c["cargo"], c["numero"]), {
                        "nome_atual": n, "casa_atual": casa_atual, "origem": "a_conferir"})
    return vinculo, todos


def montar(candidatos, titulares, territorio, expansao, federal, hoje=None) -> dict:
    """A legislatura 2027 inteira, pronta para a tela. PURA."""
    hoje = hoje or datetime.date.today()
    terr = {eleicoes._norm(r.get("deputado")): r for r in territorio}
    expa = {eleicoes._norm(r.get("deputado")): r for r in expansao}
    fede = {eleicoes._norm(r.get("deputado")): r for r in federal}
    nomes_alesp = [r.get("nome_parlamentar", "") for r in titulares if r.get("nome_parlamentar")]
    contato = {eleicoes._norm(r.get("nome_parlamentar")): r for r in titulares}
    nomes_fed = [r.get("deputado", "") for r in federal if r.get("deputado")]

    v_est, sit_est = _situacoes(nomes_alesp, "DEPUTADO ESTADUAL", candidatos, "ALESP")
    v_fed, sit_fed = _situacoes(nomes_fed, "DEPUTADO FEDERAL", candidatos, "Câmara")
    vinculo = {**v_fed, **v_est}

    def _hist(nome_atual, casa_atual):
        if not nome_atual:
            return None
        if casa_atual == "ALESP":
            return _historico_estadual(nome_atual, terr, expa)
        return _historico_federal(nome_atual, fede)

    casas = {"ALESP": [], "Câmara": [], "Senado": []}
    for cargo, casa in CASAS.items():
        for c in eleicoes.eleitos(candidatos, cargo):
            v = vinculo.get((c.get("cargo"), c.get("numero")), {})
            origem = v.get("origem", "novo")
            nome_atual = v.get("nome_atual", "")
            hist = _hist(nome_atual, v.get("casa_atual")) if origem != "a_conferir" else None
            of = contato.get(eleicoes._norm(nome_atual), {}) if v.get("casa_atual") == "ALESP" else {}
            p = {
                "chave": f"{casa}-{c.get('numero')}", "casa": casa, "cargo": cargo,
                "numero": c.get("numero", ""),
                # quem já está nas nossas listas aparece com o nome que a tela já usa
                "nome": (nome_atual if origem in ("reeleito", "outra_casa")
                         else nome_bonito(c.get("nome_urna") or c.get("nome"))),
                "nome_urna": nome_bonito(c.get("nome_urna")),
                "nome_civil": nome_bonito(c.get("nome")), "partido": partido_curto(c),
                "partido_oficial": c.get("partido", ""), "votos": int(_num(c.get("votos"))),
                "pct": _num(c.get("pct_votos")), "situacao_tse": c.get("situacao", ""),
                "origem": origem, "nome_atual": nome_atual, "casa_atual": v.get("casa_atual", ""),
                "historico": hist,
                "contato_oficial": ({"email": of.get("email_oficial", ""),
                                     "telefone": of.get("telefone_gabinete", ""),
                                     "pagina": of.get("pagina_alesp", "")}
                                    if of and origem == "reeleito" else {}),
            }
            p["origem_rotulo"] = (f"Vem da {p['casa_atual']}" if origem == "outra_casa"
                                  else "Novo na ALESP" if origem == "novo" and casa == "ALESP"
                                  else "Fora da lista atual" if origem == "novo"
                                  else ORIGENS[origem])
            p["faixa"] = _faixa(origem, hist)
            p["faixa_rotulo"] = FAIXAS[p["faixa"]]
            p["gancho"] = gancho(p)
            casas[casa].append(p)
        casas[casa].sort(key=lambda p: (p["faixa"], -(p["historico"] or {}).get("score", 0), -p["votos"]))

    # Quem SAI e tem histórico: última janela (Orçamento 2027, até 31/jan).
    saindo = []
    for casa_atual, situacoes in (("ALESP", sit_est), ("Câmara", sit_fed)):
        for n, s in situacoes:
            if s["status"] != "nao_eleito":
                continue
            h = _hist(n, casa_atual)
            if not h:
                continue
            saindo.append({"nome": n, "casa": casa_atual, "historico": h,
                           "votos": int(_num(s.get("votos"))),
                           "evidencia": nome_bonito(s.get("nome_urna") or s.get("nome_civil")),
                           "faixa": 1 if h["secao"] == "territorio" else 2})
        for r in saindo:
            r.setdefault("gancho", gancho_saida(r))
    saindo.sort(key=lambda r: (r["faixa"], -r["historico"]["score"]))

    sem_confirmacao = [{"nome": n, "casa": casa, "possiveis": s["possiveis"], "status": s["status"]}
                  for casa, sits in (("ALESP", sit_est), ("Câmara", sit_fed))
                  for n, s in sits if s["status"] in ("a_conferir", "nao_encontrado")]

    def _cont(lista):
        return {o: sum(1 for p in lista if p["origem"] == o) for o in ORIGENS} | {"total": len(lista)}

    hoje_alesp = {st: sum(1 for _, s in sit_est if s["status"] == st)
                  for st in eleicoes.ROTULOS}
    resultado_em = next((c.get("resultado_em") for c in candidatos if c.get("resultado_em")), "")
    return {
        "resultado_em": resultado_em,
        "dias_posse": (POSSE - hoje).days,
        "casas": casas,
        "contagens": {casa: _cont(lista) for casa, lista in casas.items()},
        "alesp_hoje": hoje_alesp,
        "saindo": saindo,
        "sem_confirmacao": sem_confirmacao,
    }


def dossie_texto(p: dict) -> list[tuple[str, str]]:
    """Linhas (rótulo, valor) do dossiê — compartilhadas pela tela e testáveis."""
    linhas = [("Cargo em 2027", f"{p['cargo'].title()} · {p['casa']}"),
              ("Votos (TRE-SP)", f"{p['votos']:,}".replace(",", ".") +
               (f" · {p['pct']:.2f}% dos válidos".replace(".", ",") if p.get("pct") else "")),
              ("Partido / federação", p.get("partido_oficial") or p.get("partido") or "—"),
              ("Nome na urna", p.get("nome_urna") or "—"),
              ("Nome civil", p.get("nome_civil") or "—"),
              ("Situação no TSE", p.get("situacao_tse") or "—")]
    if p.get("nome_atual"):
        linhas.append(("Mandato hoje", f"{p['nome_atual']} · {p['casa_atual']}"))
    return linhas
