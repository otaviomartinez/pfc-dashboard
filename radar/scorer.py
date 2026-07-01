"""
Pontuação do radar — mesma lógica de pesos do Score PFC (35/25/20/20).

pontuacao(op) -> {score_aderencia, score_valor, score_regiao,
                  score_acionabilidade, score_total, motivo}
"""
from __future__ import annotations

import re
import unicodedata

# --- Aderência (35%) ---------------------------------------------------------
POSITIVAS_FORTES = [
    "escola publica", "educacao basica", "ensino fundamental", "ensino medio",
    "iniciacao cientifica", "feira de ciencias", "clube de ciencia",
    "permanencia escolar", "tecnologia social", "formacao de professores",
    "equidade educacional",
]
POSITIVAS = POSITIVAS_FORTES + [
    "educacao", "juventude", "vulnerabilidade social", "ciencia", "stem",
    "estudante", "jovem", "cientista", "olimpiada", "projeto de vida",
]
NEGATIVAS = [
    "pos-graduacao", "mestrado", "doutorado", "curso pago", "mensalidade",
    "vestibular preparatorio", "ensino superior privado", "patrocinio esportivo",
    "cupom", "desconto",
]

# --- Região (20%) ------------------------------------------------------------
REGIOES_PFC = [
    "sorocaba", "ipero", "tatui", "salto", "sao roque", "rio claro",
    "coronel macedo", "mirassol", "dois corregos", "corumbatai",
]
REGIOES_AMPLAS = ["sao paulo", "nacional", "todo o brasil", "todo brasil", "em todo o pais"]


# --- Pré-filtro de sinal (roda ANTES da pontuação) ---------------------------
# Dois níveis: sinais FORTES qualificam sozinhos; sinais FRACOS só qualificam
# em conjunto (2+) ou acompanhados de um valor em R$. Isso corta páginas de
# menu/manual (ex.: "Como Submeter Propostas", "Liberação de Recursos") que só
# têm termos genéricos como "recursos"/"proposta".
SINAIS_FORTES = [
    "edital", "chamada pública", "chamada de projetos", "inscrições abertas",
    "seleção de projetos", "seleção pública", "convocatória", "processo seletivo",
]
SINAIS_FRACOS = [
    "recursos", "proposta", "financiamento", "apoio financeiro", "doação",
    "fomento", "bolsa", "candidatura", "prazo de submissão", "chamada",
]
_RE_VALOR = re.compile(r"r\$\s?[\d.,]+")

# Fontes cujas páginas são 100% de editais/chamadas: o CONTEXTO já é prova de
# oportunidade, então itens delas pulam o filtro de sinal (mas a EXCLUSAO ainda
# vale, para barrar menus/manuais que também aparecem nessas páginas).
FONTES_CONTEXTO_EDITAL = {
    "FAPESP", "CNPq", "Finep", "Fundação Banco do Brasil",
    "Itaú Social", "Instituto Unibanco",
    "FEBRACE", "Prêmio Itaú-Unicef", "PORVIR",
}

# Títulos genéricos/administrativos descartados sempre (camada extra de segurança).
# Reforçado com termos de manual/procedimento comuns na FAPESP/CNPq.
EXCLUSAO_TITULOS = [
    "trabalhe conosco", "política de privacidade", "diretivas de privacidade",
    "ir para o conteúdo", "portal do governo brasileiro", "perguntas frequentes",
    "quem somos", "sobre nós", "termos de uso", "fale conosco",
    "café na tv", "café gravação",
    # manual/administrativo (páginas-meio, não editais):
    "como submeter", "submeter propostas", "chamadas de propostas",
    "uso de recursos", "prestação de contas", "liberação de recursos",
    "valores praticados", "importação e exportação", "execução de processos",
    "alterações da concessão", "submissão de relatórios", "sistemática de análise",
    "outros programas",
    # links de menu/seção de fontes de contexto (não são editais):
    "imposto de renda", "editais públicos",
]


def tem_sinal_de_oportunidade(titulo: str, descricao: str) -> bool:
    """Qualifica se houver 1 sinal forte, ou 2+ fracos, ou 1 fraco + valor R$."""
    texto = f"{titulo or ''} {descricao or ''}".lower()
    if any(s in texto for s in SINAIS_FORTES):
        return True
    fracos = sum(1 for s in SINAIS_FRACOS if s in texto)
    if fracos >= 2:
        return True
    if fracos >= 1 and _RE_VALOR.search(texto):
        return True
    return False


def avaliar_sinal(op: dict) -> tuple[bool, str]:
    """Decisão do pré-filtro. Retorna (passa, motivo_descarte).

    Ordem: exclusão (sempre vence) -> fonte de contexto (passe livre) ->
    filtro de sinal forte/fraco (agregadores, institutos, genéricas).
    """
    titulo = op.get("titulo", "")
    if titulo_excluido(titulo):
        return False, "título genérico/administrativo excluído"
    if op.get("fonte", "") in FONTES_CONTEXTO_EDITAL:
        return True, ""
    if tem_sinal_de_oportunidade(titulo, op.get("descricao", "")):
        return True, ""
    return False, "sem sinal de oportunidade"


def titulo_excluido(titulo: str) -> bool:
    """True para títulos genéricos conhecidos (menu/rodapé/FAQ) — descarte direto."""
    t = (titulo or "").lower()
    return any(x in t for x in EXCLUSAO_TITULOS)


def _norm(s: str) -> str:
    """minúsculas sem acentos, para casar palavras-chave de forma robusta."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def _valor_reais(texto: str) -> int:
    """Extrai o MAIOR valor em reais citado (0 se nenhum)."""
    t = _norm(texto)
    maior = 0
    for m in re.finditer(r"r?\$?\s*([\d\.]+(?:,\d+)?)\s*(mil|milhao|milhoes|mi|k)?", t):
        try:
            base = float(m.group(1).replace(".", "").replace(",", "."))
        except ValueError:
            continue
        unid = m.group(2) or ""
        if unid in ("mil", "k"):
            base *= 1_000
        elif unid in ("milhao", "milhoes", "mi"):
            base *= 1_000_000
        if base >= 1_000:
            maior = max(maior, int(base))
    return maior


def _score_aderencia(texto: str):
    t = _norm(texto)
    fortes = sum(1 for k in POSITIVAS_FORTES if k in t)
    pos = sum(1 for k in POSITIVAS if k in t)
    neg = sum(1 for k in NEGATIVAS if k in t)
    # 2+ negativas sem positiva forte => descarte automático (0-20)
    if neg >= 2 and fortes == 0:
        return max(0, 20 - neg * 3), f"{neg} termos fora de escopo, sem aderência forte"
    score = 30 + pos * 11 + fortes * 8 - neg * 20
    score = max(0, min(100, score))
    if fortes:
        motivo = f"aderência forte ({fortes} termo(s)-chave)"
    elif pos:
        motivo = f"aderência parcial ({pos} termo(s))"
    else:
        motivo = "aderência incerta (sem termos-chave)"
    return score, motivo


def _score_valor(op: dict):
    texto = f"{op.get('valor_estimado','')} {op.get('titulo','')} {op.get('descricao','')}"
    v = _valor_reais(texto)
    if v <= 0:
        return 50, "valor não informado"
    if 50_000 <= v <= 300_000:
        return 90, "valor na faixa-alvo"
    if 300_000 < v <= 1_000_000:
        return 75, "valor acima da faixa-alvo"
    if 20_000 <= v < 50_000:
        return 65, "valor abaixo da faixa-alvo"
    if v < 20_000:
        return 40, "valor baixo"
    return 60, "valor muito alto"


def _score_regiao(texto: str):
    t = _norm(texto)
    if any(r in t for r in REGIOES_PFC):
        return 90, "região PFC citada"
    if any(r in t for r in REGIOES_AMPLAS):
        return 80, "abrangência SP/nacional"
    return 50, "região não informada"


def _score_acionabilidade(op: dict):
    score, notas = 40, []
    if op.get("prazo", "").strip():
        score += 30
        notas.append("tem prazo")
    if str(op.get("url", "")).startswith("http"):
        score += 25
        notas.append("link direto")
    if len(op.get("descricao", "")) > 60:
        score += 5
    return min(100, score), "; ".join(notas) or "pouca informação de contato"


def pontuacao(op: dict) -> dict:
    """Pontua uma oportunidade e devolve os 4 componentes + total + motivo."""
    texto = f"{op.get('titulo','')} {op.get('descricao','')}"
    a, ma = _score_aderencia(texto)
    v, mv = _score_valor(op)
    r, mr = _score_regiao(texto)
    ac, mac = _score_acionabilidade(op)
    total = round(0.35 * a + 0.25 * v + 0.20 * r + 0.20 * ac)
    return {
        "score_aderencia": a,
        "score_valor": v,
        "score_regiao": r,
        "score_acionabilidade": ac,
        "score_total": total,
        "motivo": f"{ma}; {mv}; {mr}; {mac}",
    }
