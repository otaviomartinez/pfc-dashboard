"""Painel de Prefeituras do Dashboard PFC.

Segue o molde de `src/emendas.py`: construção OFFLINE (script -> CSV/config), o
app só LÊ o resultado. Nada de chamar API em runtime do Streamlit.

PASSO 1: `resolver_ibge` resolve o código IBGE dos 11 municípios a partir da
tabela oficial já versionada no repo (data/ibge_regioes_imediatas_sp.csv).
"""
