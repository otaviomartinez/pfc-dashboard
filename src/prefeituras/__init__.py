"""Painel PREFEITURAS — a terceira perna do funil do PFC.

Emendas responde "qual parlamentar abordar"; Captação, "qual edital existe".
Aqui: **a prefeitura é quem recebe a emenda e quem assina o convênio**.

REGRA DE OURO (equivalente ao autorizado-vs-pago das Emendas): não existe número
público de "verba disponível da prefeitura". Os indicadores mostram CAPACIDADE
(CAPAG, caixa) e PRIORIDADE (MDE, os 25% do art. 212 da CF) — nunca
DISPONIBILIDADE. A UI é obrigada a dizer isso.

Arquitetura igual à de src/emendas.py: nada de API em runtime do Streamlit.
Script offline (`python -m src.prefeituras`) -> CSV em data/prefeituras/ -> o app
só lê. Camada pura (sem I/O) mora em ui/formato.py.
"""
