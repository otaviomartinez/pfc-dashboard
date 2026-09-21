"""Painel de Prefeituras do Dashboard PFC — a terceira perna do funil.

Emendas responde "qual parlamentar abordar"; Captação, "qual edital existe".
Aqui: **a prefeitura é quem recebe a emenda e quem assina o convênio**.

REGRA DE OURO (equivalente ao autorizado-vs-pago das Emendas): não existe número
público de "verba disponível da prefeitura". Os indicadores mostram CAPACIDADE
(CAPAG, caixa) e PRIORIDADE (MDE, os 25% do art. 212 da CF) — nunca
DISPONIBILIDADE. A UI é obrigada a dizer isso.

Segue o molde de `src/emendas.py`: construção OFFLINE (script -> CSV/config), o
app só LÊ o resultado. Nada de chamar API em runtime do Streamlit. A camada pura
(sem I/O) mora em `ui/formato.py`.

Módulos:
  resolver_ibge — resolve/valida o código IBGE dos 11 a partir da tabela oficial
                  já versionada no repo (data/ibge_regioes_imediatas_sp.csv).
  config        — carrega config/pfc_prefeituras.toml (usa o resolver para
                  reconferir cada código; código errado derruba com erro).
  siconfi       — cliente do Tesouro + parsers puros de MDE/caixa.
  capag         — nota de capacidade de pagamento (ausência != nota ruim).
  eleitos       — prefeitos/vices/vereadores do TSE (campo factual, sem juízo).
  mde           — leitura do CSV construído por `python -m src.prefeituras`.
"""
