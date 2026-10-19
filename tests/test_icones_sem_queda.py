"""Ícone que não existe nunca derruba a tela (KeyError na sidebar, out/2026).

    python tests/test_icones_sem_queda.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui import formato  # noqa: E402
from ui.estilos import ICONES  # noqa: E402


def test_icone_inexistente_vira_reserva():
    css = formato.css_icones_botoes({"emnav_x": "nao-existe"}, {"emnav_x": "X"}, {"emnav_x": "#38BDF8"})
    assert "st-key-emnav_x" in css
    assert "nao-existe" not in css
    assert formato.svg_icone("nao-existe").startswith("<svg")


def test_todo_icone_usado_nas_sidebars_existe():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fonte = open(os.path.join(raiz, "app.py"), encoding="utf-8").read()
    usados = set(re.findall(r'"(?:emnav|nav|emenda|pc|parc)[_a-z0-9-]*":\s*"([a-z0-9-]+)"', fonte))
    faltam = sorted(u for u in usados if u not in ICONES)
    assert not faltam, f"ícones sem desenho em ui/estilos.py: {faltam}"


if __name__ == "__main__":
    test_icone_inexistente_vira_reserva()
    test_todo_icone_usado_nas_sidebars_existe()
    print("ícones: todos os testes passaram")
