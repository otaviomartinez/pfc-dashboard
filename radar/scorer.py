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
    "iniciacao cientifica", "clube de ciencia",
    "permanencia escolar", "tecnologia social", "formacao de professores",
    "equidade educacional",
]
# ELEGIBILIDADE do PFC (conceito AMPLO, não tema estreito). O PFC é educação
# científica, mas é uma OSC que se candidata a muita coisa: educação, ciência,
# juventude, impacto social, desenvolvimento comunitário, inovação, formação,
# terceiro setor amplo, cultura educativa. Tudo isso é "dinheiro que o PFC pode
# captar" e deve pontuar como aderente. O que NÃO cabe (bem-estar animal, saúde
# hospitalar, aldeia indígena específica) sai no pré-filtro (ver NAO_ELEGIVEL);
# e QUEM participa (estudante/olimpíada) sai por NEGATIVAS_ALUNO — não aqui.
POSITIVAS = POSITIVAS_FORTES + [
    "educacao", "juventude", "vulnerabilidade social", "ciencia", "stem",
    "projeto de vida", "impacto social", "comunitario",
    "comunidade", "desenvolvimento comunitario", "terceiro setor",
    "sociedade civil", "organizacoes sociais", "organizacao social", "inovacao",
    "formacao", "empreendedorismo", "periferia", "inclusao", "direitos humanos",
    "cultura educativa", "assistencia social",
]
# AMBIENTAL / ECOLOGIA (fora do escopo do PFC, por decisão do Fábio): meio
# ambiente, preservação, biodiversidade, clima etc. NÃO tem a ver com educação
# científica — barra no pré-filtro (avaliar_sinal) e não some com socioambiental
# (que saiu das POSITIVAS). Termos PRECISOS de propósito: nada de "eco" solto
# (pegaria "economia"/"ecossistema de inovação") nem "ambiente" solto (pegaria
# "ambiente escolar/de aprendizagem/virtual"). "ambiental"/"ambientais" (com -al)
# é quase sempre meio ambiente; clima só nas formas compostas ("mudança
# climática", nunca "clima escolar/organizacional").
AMBIENTAL = [
    "meio ambiente", "ambiental", "ambientais", "socioambiental", "socio-ambiental",
    "ecologia", "ecologic", "biodiversidade", "preservacao ambiental",
    "conservacao ambiental", "unidade de conservacao", "reflorestamento",
    "desmatamento", "reciclagem", "residuos solidos", "coleta seletiva",
    "flora", "mata atlantica", "poluicao", "recursos hidricos", "bacia hidrografica",
    "climatic", "acao climatica", "justica climatica", "comunicacao climatica",
    "mudanca climatica", "mudancas climaticas", "emergencia climatica",
    "crise climatica", "aquecimento global", "credito de carbono",
    "neutralidade de carbono", "energia renovavel", "energias renovaveis",
    "sustentabilidade ambiental",
]
NEGATIVAS = [
    "pos-graduacao", "mestrado", "doutorado", "curso pago", "mensalidade",
    "vestibular preparatorio", "ensino superior privado", "patrocinio esportivo",
    "cupom", "desconto",
]
# OPORTUNIDADE PARA ALUNO (não é captação): olimpíadas, competições, premiação
# de estudantes, bolsa/vaga para participante. O PFC CAPTA recurso para a
# organização — quem premia/inscreve alunos é a missão, não a captação. Estes
# sinais barram o item no pré-filtro (avaliar_sinal) e derrubam a aderência.
NEGATIVAS_ALUNO = [
    "olimpiada", "olimpiadas", "olimpico", "medalha", "medalhista", "medalhistas",
    "estudantes premiados", "alunos premiados", "estudante premiado",
    "premiacao de estudante", "premia estudantes", "premia os estudantes",
    "premia alunos", "bolsa para aluno", "bolsa para estudante",
    "bolsa de estudo", "inscricao de participante", "inscricoes de participantes",
    "competicao estudantil", "gabarito", "prova classificatoria",
    # feira/mostra científica: EVENTO que aluno/escola participa, não captação
    # (as fontes de feira já saíram; isto pega feiras que vêm por outras fontes):
    "feira de ciencias", "feira cientifica", "feira de ciencia",
    "mostra cientifica", "mostra de ciencias", "feira de educacao",
]
# INAPLICÁVEL ao PFC (não é falta de tema — é falta de elegibilidade): editais
# que o PFC genuinamente não tem como concorrer. Régua estreita DE PROPÓSITO: só
# o inequivocamente fora (bem-estar animal; saúde hospitalar/clínica específica;
# recorte étnico/aldeia indígena específico). NÃO inclui "impacto social",
# "comunitário", "cultura", "ambiente" genéricos — nesses o PFC PODE se
# candidatar, então ficam. Barra no pré-filtro (avaliar_sinal).
NAO_ELEGIVEL = [
    # bem-estar animal
    "bem-estar animal", "bem estar animal", "protecao animal", "causa animal",
    "resgate animal", "abrigo animal", "fauna", "veterinari",
    # saúde hospitalar / clínica específica (não "educação em saúde")
    "hospital", "hospitalar", "oncolog", "cancer", "leito", "uti ",
    "cirurgi", "doenca rara", "cuidados paliativos", "ambulatori",
    # recorte étnico/aldeia indígena específico
    "indigena", "indigenas", "aldeia", "povos originarios", "terra indigena",
]
# PRÊMIO PARA PESSOA FÍSICA (não é captação da OSC): prêmio cujo laureado é um
# INDIVÍDUO nomeado — professor/educador/jornalista. Quem recebe é a pessoa, não
# a organização; o PFC capta prêmio INSTITUCIONAL (para o projeto/organização).
# Régua estreita de propósito: só casa o prêmio-a-indivíduo, NUNCA "formação de
# professores" (que é edital institucional e segue em POSITIVAS). Barra no
# pré-filtro (avaliar_sinal).
NEGATIVAS_PESSOA_FISICA = [
    "premio professor", "premio ao professor", "premio para professor",
    "premio educador", "premio ao educador", "premio para educador",
    "melhor educador", "melhor professor", "educador nota", "professor nota",
    "premio jornalista", "premio ao jornalista", "melhor jornalista",
    "personalidade do ano",
]
# EDIÇÃO PASSADA / INSCRIÇÕES ENCERRADAS: listas de prêmio carregam muita coisa
# de 2025 já fechada e notícia de resultado. Barram no pré-filtro dois grupos de
# sinais textuais (o vencido-há-muito por prazo já cai em prazos.py):
#  1) fechamento explícito das inscrições;
#  2) anúncio de RESULTADO (edição passada). Aqui a régua é estreita para não
#     barrar edital ABERTO que só descreve o prêmio ("os vencedores receberão"):
#     só casa frase de resultado consumado ("conheça os vencedores", "aos
#     vencedores", "ganhadores do prêmio"), não a palavra "vencedores" solta.
ENCERRADO = [
    # 1) fechamento explícito
    "inscricoes encerradas", "inscricao encerrada", "encerradas as inscricoes",
    "encerrada as inscricoes", "inscricoes encerram-se", "prazo encerrado",
    "edital encerrado", "chamada encerrada", "selecao encerrada",
    "inscricoes se encerraram",
    # 2) anúncio de resultado (edição passada). Ancorado em VERBO de anúncio para
    #    não pegar edital aberto que só descreve o benefício ("reconhecimento aos
    #    vencedores", "os vencedores receberão"): a frase precisa afirmar o
    #    resultado consumado, não a promessa.
    "conheca os vencedores", "conheca os ganhadores", "conheca os premiados",
    "anuncia os vencedores", "anuncia os ganhadores", "anunciados os vencedores",
    "premiacao destaca", "entrega premiacao aos", "entrega da premiacao aos",
    "vencedores da edicao", "ganhadores da edicao", "conheca as vencedoras",
]

# --- Região (20%) ------------------------------------------------------------
REGIOES_PFC = [
    "sorocaba", "ipero", "tatui", "salto", "sao roque", "rio claro",
    "coronel macedo", "mirassol", "dois corregos", "corumbatai",
]
REGIOES_AMPLAS = ["sao paulo", "nacional", "todo o brasil", "todo brasil",
                  "em todo o pais", "todo o pais"]

# --- Restrição geográfica (fora de SP/Sudeste) -------------------------------
# O PFC é do estado de SP (Sudeste). Barra editais RESTRITOS a outra macro-região
# ou estado fora do Sudeste. RECALL > PRECISÃO: só barra quando um MARCADOR de
# restrição ('exclusivo/somente/apenas/restrito/municípios do…') aparece PERTO de
# uma âncora regional fora do Sudeste — NUNCA na palavra 'sul' solta ('zona sul',
# 'sul de Minas' = Sudeste). Na dúvida, MANTÉM. Tudo normalizado (_norm, sem acento).
INCLUI_SUDESTE_NACIONAL = REGIOES_PFC + REGIOES_AMPLAS + [
    "sudeste", "paulista", "ambito nacional", "territorio nacional",
    "todas as regioes", "todos os estados", "qualquer estado", "qualquer regiao",
    "todo o territorio",
    # outros estados do Sudeste (o PFC é SP, mas Sudeste é "mantém" por decisão do
    # filtro): protege sub-regiões tipo "nordeste de Minas", "norte fluminense",
    # "noroeste mineiro" de serem barradas pela âncora macro-regional forte abaixo.
    "minas gerais", "mineiro", "mineira", "rio de janeiro", "fluminense",
    "carioca", "espirito santo", "capixaba",
]
# Macro-regiões FORTES: fora do Sudeste de forma inequívoca — barram pela simples
# MENÇÃO (não precisam de marcador colado), depois de descartar quem cita
# SP/Sudeste/nacional acima. Pega "organizações do Norte e Nordeste", "programa do
# semiárido" etc. — casos em que a restrição vem por "do/para <região>", sem uma
# palavra tipo "exclusivo" por perto.
ANCORAS_FORA_SUDESTE_FORTES = [
    "nordeste", "centro-oeste", "centro oeste", "norte e nordeste",
    "regiao norte", "regiao sul", "regiao nordeste", "regiao centro-oeste",
    "estados do norte", "estados do nordeste", "estados do sul",
    "semiarido", "sertao", "amazonia legal", "regiao amazonica",
]
# Estados fora do Sudeste também barram pela simples MENÇÃO (nome de estado é
# inequívoco). FORA daqui de propósito: 'parana' (casa 'paranapanema'/
# 'paranapiacaba', que são de SP) e 'acre' (casa 'massacre') — esses seguem só no
# modo com marcador (ANCORAS_FORA_SUDESTE). Sub-região de estado do Sudeste já é
# protegida pelo INCLUI (minas/rio de janeiro/espirito santo).
ESTADOS_FORA_SUDESTE_FORTES = [
    "bahia", "ceara", "pernambuco", "maranhao", "piaui", "rio grande do norte",
    "paraiba", "alagoas", "sergipe", "amazonas", "rondonia", "roraima",
    "amapa", "tocantins", "goias", "mato grosso", "mato grosso do sul",
    "distrito federal", "santa catarina", "rio grande do sul",
]
ANCORAS_FORA_SUDESTE = [
    # macro-regiões (NÃO 'sul'/'norte' soltos — falso positivo)
    "nordeste", "centro-oeste", "centro oeste", "amazonia legal", "regiao amazonica",
    "semiarido", "sertao", "regiao norte", "regiao sul",
    "estados do norte", "estados do nordeste", "estados do sul",
    # estados fora do Sudeste (evita 'para'=preposição e 'acre'=subst. de 'massacre')
    "bahia", "ceara", "pernambuco", "maranhao", "piaui", "rio grande do norte",
    "paraiba", "alagoas", "sergipe", "amazonas", "rondonia", "roraima",
    "amapa", "tocantins", "goias", "mato grosso", "mato grosso do sul",
    "distrito federal", "parana", "santa catarina", "rio grande do sul",
]
RESTRICAO_MARCADORES = [
    "exclusiv", "somente", "apenas", "restrit", "limitad", "voltad", "destinad",
    "municipios do", "municipios da", "municipios de", "municipios das",
    "municipios dos", "estado do", "estado da", "estados do", "sediad",
    "com sede", "residentes", "domiciliad",
]


# --- Pré-filtro de sinal (roda ANTES da pontuação) ---------------------------
# Dois níveis: sinais FORTES qualificam sozinhos; sinais FRACOS só qualificam
# em conjunto (2+) ou acompanhados de um valor em R$. Isso corta páginas de
# menu/manual (ex.: "Como Submeter Propostas", "Liberação de Recursos") que só
# têm termos genéricos como "recursos"/"proposta".
SINAIS_FORTES = [
    "edital", "chamada pública", "chamada de projetos", "inscrições abertas",
    "seleção de projetos", "seleção pública", "convocatória", "processo seletivo",
    # variações de "inscrições abertas" (aluno/olimpíada já caíram antes):
    "abre inscrições", "abrem inscrições", "recebe inscrições", "recebem inscrições",
    # prêmio institucional / patrocínio também são captação que o PFC concorre —
    # prêmio PARA ALUNO já cai antes, em e_oportunidade_aluno.
    "prêmio", "premiação", "patrocínio", "patrocinador",
]
SINAIS_FRACOS = [
    "recursos", "proposta", "financiamento", "apoio financeiro", "doação",
    "fomento", "bolsa", "candidatura", "prazo de submissão", "chamada",
]
_RE_VALOR = re.compile(r"r\$\s?[\d.,]+")

# NOTA: a antiga whitelist FONTES_CONTEXTO_EDITAL foi REMOVIDA. Ela dava passe
# livre no filtro de sinal a certas fontes — o que deixava até página de menu
# ("Tire suas Dúvidas", "Materiais de Comunicação") entrar na fila, e blindava
# o catálogo de modalidades da FAPESP. Agora TODA fonte passa pelo mesmo filtro
# de sinal; quem não tem sinal de oportunidade (edital/chamada/valor) cai.

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
    # aula/tutorial sobre captação (não é edital, é conteúdo):
    "aula ensina", "como elaborar proposta", "webinar", "curso de captação",
    # contratação/licitação (prefeitura contrata prestador — não é captação):
    "contratar organização especializada", "contratação de organização",
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


def e_oportunidade_aluno(titulo: str, descricao: str) -> bool:
    """True se o item é OPORTUNIDADE PARA ALUNO (olimpíada, medalha, premiação
    de estudante, bolsa/vaga de participante) — isso é missão, não captação.
    Normaliza acentos (_norm) porque as chaves em NEGATIVAS_ALUNO são sem acento
    ('olimpiada' precisa casar com 'Olimpíada')."""
    texto = _norm(f"{titulo or ''} {descricao or ''}")
    return any(k in texto for k in NEGATIVAS_ALUNO)


def e_premio_pessoa_fisica(titulo: str, descricao: str) -> bool:
    """True se o prêmio é para PESSOA FÍSICA (professor/educador/jornalista
    individual) — laureia o indivíduo, não a organização, então não é captação
    do PFC. Normaliza acentos (chaves em NEGATIVAS_PESSOA_FISICA são sem acento)."""
    texto = _norm(f"{titulo or ''} {descricao or ''}")
    return any(k in texto for k in NEGATIVAS_PESSOA_FISICA)


def e_encerrado(titulo: str, descricao: str) -> bool:
    """True se o item sinaliza edição PASSADA / inscrições ENCERRADAS."""
    texto = _norm(f"{titulo or ''} {descricao or ''}")
    return any(k in texto for k in ENCERRADO)


def e_nao_elegivel(titulo: str, descricao: str) -> bool:
    """True se é captação que o PFC genuinamente NÃO tem como concorrer
    (bem-estar animal, saúde hospitalar/clínica, recorte étnico/aldeia indígena).
    NÃO barra impacto social/comunitário/cultura/ambiente amplos — nesses o PFC
    pode se candidatar. Normaliza acentos (chaves em NAO_ELEGIVEL são sem acento)."""
    texto = _norm(f"{titulo or ''} {descricao or ''}")
    return any(k in texto for k in NAO_ELEGIVEL)


def e_ambiental(titulo: str, descricao: str) -> bool:
    """True se o edital é sobre meio ambiente/ecologia — fora do escopo do PFC.
    Barra tudo que é ambiental (inclusive socioambiental/educação ambiental), por
    decisão do coordenador. Termos precisos (ver AMBIENTAL): nunca 'eco'/'ambiente'
    soltos. Normaliza acentos (chaves em AMBIENTAL são sem acento)."""
    texto = _norm(f"{titulo or ''} {descricao or ''}")
    return any(k in texto for k in AMBIENTAL)


def e_restrito_fora_sudeste(titulo: str, descricao: str) -> bool:
    """True se o edital é RESTRITO a região/estado FORA de SP/Sudeste (o PFC é de
    SP). NÃO barra: nacional/sem recorte, ou que cite SP/Sudeste/Sorocaba/município
    do PFC, ou que liste várias regiões incluindo o Sudeste. RECALL > PRECISÃO: só
    barra quando um MARCADOR de restrição aparece PERTO (mesma frase) de uma âncora
    fora do Sudeste — nunca 'sul' solto ('zona sul', 'sul de Minas' = Sudeste). Na
    dúvida, MANTÉM (melhor mostrar um nacional a mais do que esconder)."""
    texto = _norm(f"{titulo or ''} {descricao or ''}")
    if any(k in texto for k in INCLUI_SUDESTE_NACIONAL):
        return False
    # macro-região OU estado fora do Sudeste citado = restrição, mesmo sem
    # marcador colado (ex.: "organizações sociais do Norte e Nordeste",
    # "organizações do Rio Grande do Sul"):
    if any(a in texto for a in ANCORAS_FORA_SUDESTE_FORTES + ESTADOS_FORA_SUDESTE_FORTES):
        return True
    # sufixo de edição regional: "Edital ... – Norte", "... - Sul":
    if re.search(r"[-–]\s*(norte|sul)\b", texto):
        return True
    for m in RESTRICAO_MARCADORES:
        i = texto.find(m)
        while i != -1:
            janela = texto[max(0, i - 25): i + len(m) + 45]   # restrição colada à região
            if any(a in janela for a in ANCORAS_FORA_SUDESTE):
                return True
            i = texto.find(m, i + 1)
    return False


def avaliar_sinal(op: dict) -> tuple[bool, str]:
    """Decisão do pré-filtro. Retorna (passa, motivo_descarte).

    Ordem: exclusão administrativa -> encerrado (edição passada) ->
    oportunidade-para-aluno -> prêmio para pessoa física -> inelegível (fora do
    que o PFC concorre) -> filtro de sinal. Sem whitelist: toda fonte passa pelo
    mesmo crivo. A régua é ELEGIBILIDADE (dinheiro que o PFC pode captar), não
    tema estreito — impacto social, comunitário e cultura entram.
    """
    titulo = op.get("titulo", "")
    descricao = op.get("descricao", "")
    if titulo_excluido(titulo):
        return False, "título genérico/administrativo excluído"
    if e_encerrado(titulo, descricao):
        return False, "edição passada / inscrições encerradas"
    if e_oportunidade_aluno(titulo, descricao):
        return False, "oportunidade para aluno (olimpíada/medalha/bolsa), não captação"
    if e_premio_pessoa_fisica(titulo, descricao):
        return False, "prêmio para pessoa física (professor/indivíduo), não captação institucional"
    if e_nao_elegivel(titulo, descricao):
        return False, "inaplicável ao PFC (bem-estar animal/saúde hospitalar/aldeia indígena)"
    if e_ambiental(titulo, descricao):
        return False, "ambiental/ecologia (fora do escopo do PFC)"
    if e_restrito_fora_sudeste(titulo, descricao):
        return False, "restrito a região fora de SP/Sudeste (o PFC é de São Paulo)"
    if tem_sinal_de_oportunidade(titulo, descricao):
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
    aluno = sum(1 for k in NEGATIVAS_ALUNO if k in t)
    # Oportunidade PARA ALUNO (olimpíada/medalha/bolsa de participante) não é
    # captação: aderência ao chão (2ª linha de defesa; a 1ª é avaliar_sinal).
    if aluno >= 1:
        return max(0, 10 - aluno * 5), f"oportunidade para aluno, não captação ({aluno} sinal)"
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
    dias = op.get("dias_restantes")
    if isinstance(dias, int):
        # prazo REAL extraído (radar/prazos.py): urgência conta a favor,
        # prazo vencido derruba (oportunidade perdida).
        if dias < 0:
            score -= 30
            notas.append(f"VENCIDA (prazo há {-dias}d)")
        elif dias <= 30:
            score += 40
            notas.append(f"prazo em {dias}d — agir agora")
        else:
            score += 30
            notas.append(f"prazo em {dias}d")
    elif str(op.get("prazo", "")).strip():
        score += 30
        notas.append("tem prazo")
    if str(op.get("url", "")).startswith("http"):
        score += 25
        notas.append("link direto")
    if len(op.get("descricao", "")) > 60:
        score += 5
    return max(0, min(100, score)), "; ".join(notas) or "pouca informação de contato"


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
