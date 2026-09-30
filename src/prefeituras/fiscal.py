"""Método fiscal REVISADO do painel de Prefeituras — "a cidade banca?".

Pedido do Fábio (set/2026): além de MDE (os 25%) + CAPAG, olhar mais fatores que
indiquem melhor a capacidade real de a prefeitura assumir o programa. Fatores
somados (todos de fonte pública oficial):
  - caixa / disponibilidade (RGF Anexo 5): tem folga de caixa?
  - despesa com pessoal vs. teto da LRF (executivo municipal = 54% da RCL);
  - dependência de FPM (município pequeno que vive de repasse = frágil);
  - CAUC / regularidade: se está irregular, NEM PODE assinar convênio — decisivo.

REGRA DE OURO (a mesma do painel): estes fatores mostram CAPACIDADE e PRIORIDADE,
nunca "verba disponível". E — regra de honestidade — fator ausente é "sem dado",
NUNCA tratado como ruim.

Este módulo é ADITIVO e PURO: não substitui `ui.formato.temperatura_prefeitura`
(que segue calculando a base MDE+CAPAG). `capacidade_fiscal` recebe essa base
pronta e a enriquece. A UI e a alimentação com dados reais (RGF/CAUC/FPM) são
passo seguinte, coordenado — hoje o que faltar entra como "sem dado".
"""
from __future__ import annotations

# Teto da Lei de Responsabilidade Fiscal para pessoal do EXECUTIVO municipal
# (% da Receita Corrente Líquida). Alerta = 90% do teto; prudencial = 95%.
LRF_PESSOAL_LIMITE = 54.0
LRF_PESSOAL_ALERTA = 48.6       # 90% de 54
LRF_PESSOAL_PRUDENCIAL = 51.3   # 95% de 54
# Acima disto, a prefeitura depende demais do FPM (frágil a repasse) — heurística.
FPM_DEPENDENCIA_ALTA = 60.0

_DOWNGRADE = {"quente": "morno", "morno": "morno", "frio": "frio", "sem_dado": "sem_dado"}


def _cauc_irregular(cauc) -> bool | None:
    """True se irregular, False se regular, None se sem dado. Tolera bool ou texto
    ('regular'/'irregular'/'adimplente'/'inadimplente')."""
    if cauc is None or str(cauc).strip() == "":
        return None
    if isinstance(cauc, bool):
        return not cauc
    t = str(cauc).strip().lower()
    if t in ("regular", "adimplente", "ok", "sim", "true", "1"):
        return False
    if t in ("irregular", "inadimplente", "nao", "não", "false", "0", "bloqueado"):
        return True
    return None


def _num(x):
    try:
        return float(str(x).replace("%", "").replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


def sinal_pessoal(pessoal_pct) -> dict:
    """Sinal do gasto com pessoal vs. teto da LRF (54%)."""
    v = _num(pessoal_pct)
    if v is None:
        return {"fator": "pessoal", "nivel": "sem_dado", "texto": "despesa com pessoal: sem dado"}
    if v >= LRF_PESSOAL_PRUDENCIAL:
        return {"fator": "pessoal", "nivel": "ruim",
                "texto": f"pessoal em {v:.1f}% da RCL — acima do limite prudencial da LRF"}
    if v >= LRF_PESSOAL_ALERTA:
        return {"fator": "pessoal", "nivel": "alerta",
                "texto": f"pessoal em {v:.1f}% da RCL — no limite de alerta da LRF"}
    return {"fator": "pessoal", "nivel": "bom", "texto": f"pessoal em {v:.1f}% da RCL — dentro do teto"}


def sinal_caixa(caixa) -> dict:
    """Sinal da disponibilidade de caixa (RGF Anexo 5). >0 folga; <=0 aperto."""
    v = _num(caixa)
    if v is None:
        return {"fator": "caixa", "nivel": "sem_dado", "texto": "disponibilidade de caixa: sem dado"}
    if v > 0:
        return {"fator": "caixa", "nivel": "bom", "texto": "caixa com folga (disponibilidade positiva)"}
    return {"fator": "caixa", "nivel": "ruim", "texto": "caixa apertado (disponibilidade <= 0)"}


def sinal_fpm(dependencia_fpm) -> dict:
    """Sinal da dependência de FPM (% da receita). Alta = frágil a repasse."""
    v = _num(dependencia_fpm)
    if v is None:
        return {"fator": "fpm", "nivel": "sem_dado", "texto": "dependência de FPM: sem dado"}
    if v >= FPM_DEPENDENCIA_ALTA:
        return {"fator": "fpm", "nivel": "alerta",
                "texto": f"depende {v:.0f}% do FPM — frágil a variação de repasse"}
    return {"fator": "fpm", "nivel": "bom", "texto": f"dependência de FPM em {v:.0f}% — diversificada"}


def sinal_cauc(cauc) -> dict:
    """Sinal da regularidade (CAUC). Irregular = não pode assinar convênio."""
    irreg = _cauc_irregular(cauc)
    if irreg is None:
        return {"fator": "cauc", "nivel": "sem_dado", "texto": "regularidade (CAUC): sem dado"}
    if irreg:
        return {"fator": "cauc", "nivel": "ruim",
                "texto": "irregular no CAUC — não pode receber transferência voluntária/convênio"}
    return {"fator": "cauc", "nivel": "bom", "texto": "regular no CAUC — apta a convênio"}


def capacidade_fiscal(base_temperatura: str, caixa=None, pessoal_pct=None,
                      dependencia_fpm=None, cauc=None) -> dict:
    """Enriquece a temperatura-base (MDE+CAPAG) com os fatores novos.

    `base_temperatura` vem de ui.formato.temperatura_prefeitura (não recalculado
    aqui). Devolve {temperatura, base, bloqueio, sinais, resumo}:
      - CAUC irregular → temperatura 'bloqueado' (override): nem assina convênio;
      - caixa apertado OU pessoal no prudencial → rebaixa 'quente'→'morno';
      - FPM alto é informativo (não muda a temperatura sozinho);
      - fator ausente = 'sem dado', nunca penaliza.
    """
    base = str(base_temperatura or "sem_dado")
    sinais = [sinal_caixa(caixa), sinal_pessoal(pessoal_pct),
              sinal_fpm(dependencia_fpm), sinal_cauc(cauc)]

    # CAUC irregular é bloqueio duro — decisivo, independe de MDE/CAPAG.
    if _cauc_irregular(cauc) is True:
        return {"temperatura": "bloqueado", "base": base, "bloqueio": True,
                "sinais": sinais,
                "resumo": "Bloqueado: irregular no CAUC — não pode assinar convênio agora."}

    temperatura = base
    rebaixa = any(s["fator"] in ("caixa", "pessoal") and s["nivel"] == "ruim" for s in sinais)
    if rebaixa:
        temperatura = _DOWNGRADE.get(base, base)

    fpm_alerta = any(s["fator"] == "fpm" and s["nivel"] == "alerta" for s in sinais)
    partes = []
    if temperatura != base:
        partes.append("capacidade rebaixada por caixa/pessoal")
    if fpm_alerta:
        partes.append("atenção à dependência de FPM")
    resumo = "; ".join(partes) if partes else "sem ressalvas fiscais além da base MDE+CAPAG"
    return {"temperatura": temperatura, "base": base, "bloqueio": False,
            "sinais": sinais, "resumo": resumo}
