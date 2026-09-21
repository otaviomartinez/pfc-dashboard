#!/usr/bin/env python3
"""Captura uma resposta REAL do SICONFI e salva como fixture de teste.

RODE ISTO NA SUA MÁQUINA (aqui no ambiente de dev o domínio do Tesouro está
bloqueado por política da organização — gateway 403).

    python scripts/capturar_fixture_siconfi.py

Salva tests/fixtures/siconfi_rreo_anexo08.json com a resposta crua. Depois,
tests/test_prefeituras_siconfi.py passa a validar o parser contra ELA (hoje ele
roda só com estruturas sintéticas, claramente rotuladas como tal).

Serve também de teste de fumaça da string do anexo: se vier items=[], a string
de `no_anexo` mudou — é o vazio silencioso que o plano manda vigiar.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.prefeituras import siconfi                      # noqa: E402
from src.prefeituras.config import carregar_municipios   # noqa: E402

EXERCICIO = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
DESTINO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "tests", "fixtures", "siconfi_rreo_anexo08.json")


def main() -> int:
    mun = carregar_municipios()[0]
    print(f"Consultando {mun['nome']} ({mun['cod_ibge']}) · exercício {EXERCICIO}…")
    itens = siconfi.buscar_rreo(mun["cod_ibge"], EXERCICIO, 6, siconfi.ANEXO_MDE)
    if not itens:
        print("VAZIO. Ou o exercício não foi publicado, ou a string de no_anexo "
              f"mudou (hoje: {siconfi.ANEXO_MDE!r}). Confira a doc antes de seguir.")
        return 1
    os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
    with open(DESTINO, "w", encoding="utf-8") as f:
        json.dump({"items": itens}, f, ensure_ascii=False, indent=2)
    print(f"{len(itens)} linhas salvas em {DESTINO}")
    print("MDE extraído:", siconfi.extrair_mde(itens, EXERCICIO, 6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
