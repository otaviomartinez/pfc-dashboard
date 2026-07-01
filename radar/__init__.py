"""Radar de Descoberta — varredura diária de editais e oportunidades (PFC).

Arquitetura em 3 camadas:
  1) fontes_ancora.py    — extração dedicada por fonte verificada
  2) fontes_genericas.py — extrator genérico (URLs em config_fontes.json)
  3) descoberta.py       — sugestão de novas fontes (revisão humana)
Orquestração: main.py · Pontuação: scorer.py · Deduplicação: dedup.py
"""
