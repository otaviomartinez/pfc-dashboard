"""Sonda (só diagnóstico, NÃO grava nada): o que acontece com cada edital do
Prosas no crivo do radar. Roda pela "Sonda Fiscal" com alvo=prosas_crivo.

Imprime, para cada item: veredito do pré-filtro (motivo do lixo ou "sem
sinal"), notas de aderência/total e se entraria na fila.
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from radar.fontes_ancora import fonte_prosas  # noqa: E402
from radar.main import LIMIAR_ADERENCIA, LIMIAR_FILA  # noqa: E402
from radar.scorer import avaliar_sinal, pontuacao  # noqa: E402

itens = fonte_prosas()
print(f"Prosas: {len(itens)} itens (abertos, sem órgão público de fora)\n")
vered = Counter()
for op in itens:
    passa, motivo = avaliar_sinal(op)
    if not passa:
        vered[motivo] += 1
        print(f"[LIXO] {motivo[:45]:45} | {op['titulo'][:90]}")
        continue
    p = pontuacao(op)
    entra = p["score_total"] >= LIMIAR_FILA and p["score_aderencia"] >= LIMIAR_ADERENCIA
    vered["FILA" if entra else "nota baixa"] += 1
    print(f"[{'FILA' if entra else 'baixa'}] ader {p['score_aderencia']:>3} tot {p['score_total']:>3}"
          f" | {op['titulo'][:90]}\n        {op['descricao'][:150]}")
print("\nResumo:", dict(vered))
