"""Radar de Parcerias — base curada + camada pura (sem I/O de rede, sem Streamlit).

Lista CANDIDATOS a abordar (empresas que doam material/cesta → módulo 1;
fundações do direito da criança → módulos 2/3/4). Regra de ouro: nada aqui é
parceria confirmada — o status nasce "a abordar" e a curadoria é manual. Nunca
inventar contato/valor/vínculo (ver PLANO_PARCERIAS.md).

A base-semente é um CSV versionado (data/parcerias_seed.csv). Quando o Fábio for
editar ao vivo, migra para uma aba do Sheets — mas isso é escrita de produção e
depende de OK explícito (não é feito aqui).
"""
from __future__ import annotations

import csv
import os
import unicodedata

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_CSV = os.path.join(BASE, "data", "parcerias_seed.csv")

CAMPOS = ["nome", "tipo", "foco", "modulos", "abrangencia", "site",
          "como_abordar", "status", "obs", "fonte"]

# Módulos do PFC (rótulos para exibição; ver project-radar-parcerias na memória).
MODULOS_PFC = {
    1: "Módulo 1 · escolas",
    2: "Módulo 2 · desenvolvimento social",
    3: "Módulo 3 · Fundação Casa",
    4: "Módulo 4 · situação de rua",
}


def _norm(s: str) -> str:
    """minúsculas, sem acento, espaços colapsados — para busca/casamento robusto."""
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())


def parse_modulos(campo) -> list[int]:
    """'2;3;4' → [2,3,4]. Tolera vazio, espaços e separadores ; ou ,. Ignora
    pedaços não-numéricos em vez de quebrar. Ordena e remove repetido."""
    bruto = str(campo or "").replace(",", ";")
    nums = set()
    for pedaco in bruto.split(";"):
        p = pedaco.strip()
        if p.isdigit():
            nums.add(int(p))
    return sorted(nums)


def preparar(rows: list[dict]) -> list[dict]:
    """Normaliza linhas de parceria (venham do CSV-semente OU da aba do Sheets):
    acrescenta `modulos_lista` (ints) derivado de `modulos`. Idempotente. PURA."""
    for r in rows:
        r["modulos_lista"] = parse_modulos(r.get("modulos"))
    return rows


def carregar_parcerias(caminho: str = SEED_CSV) -> list[dict]:
    """Lê a base-semente (CSV utf-8). Arquivo ausente → [] (nunca quebra a tela).
    Acrescenta `modulos_lista` (ints) a cada linha, derivado de `modulos`."""
    try:
        with open(caminho, encoding="utf-8-sig", newline="") as f:
            linhas = list(csv.DictReader(f))
    except FileNotFoundError:
        return []
    return preparar(linhas)


def filtrar_parcerias(rows: list[dict], modulo=None, tipo: str = "",
                      status: str = "", busca: str = "") -> list[dict]:
    """Filtra a base. Todos os critérios são opcionais (vazio/None = ignora).
    `modulo` casa contra a lista de módulos do parceiro; `tipo`/`status` casam
    exato (normalizado); `busca` casa por substring em nome/foco/obs. PURA."""
    def ok(r):
        if modulo not in (None, "", "Todos") and int(modulo) not in r.get("modulos_lista", []):
            return False
        if tipo and tipo != "Todos" and _norm(r.get("tipo")) != _norm(tipo):
            return False
        if status and status != "Todos" and _norm(r.get("status")) != _norm(status):
            return False
        if busca:
            alvo = _norm(f"{r.get('nome')} {r.get('foco')} {r.get('obs')}")
            if _norm(busca) not in alvo:
                return False
        return True
    return [r for r in rows if ok(r)]


def parceiros_por_modulo(rows: list[dict]) -> dict:
    """{modulo(int): [parceiros]} — um parceiro aparece em cada módulo que serve.
    Útil para a visão agrupada por módulo do PFC. PURA."""
    fora = {m: [] for m in MODULOS_PFC}
    for r in rows:
        for m in r.get("modulos_lista", []):
            fora.setdefault(m, []).append(r)
    return fora


def tipos_disponiveis(rows: list[dict]) -> list[str]:
    """Tipos distintos presentes na base (para preencher o filtro). Ordenado."""
    return sorted({str(r.get("tipo", "")).strip() for r in rows if r.get("tipo")})


def status_disponiveis(rows: list[dict]) -> list[str]:
    """Status distintos presentes na base (para o filtro). Ordenado."""
    return sorted({str(r.get("status", "")).strip() for r in rows if r.get("status")})


def gancho_parceria(row: dict) -> str:
    """Linha de abordagem HONESTA. Prioriza o `como_abordar` curado; se vazio,
    compõe do foco/tipo — nunca inventa contato ou vínculo. Sempre deixa claro
    que é um candidato a abordar."""
    curado = str(row.get("como_abordar", "")).strip()
    if curado:
        return curado
    foco = str(row.get("foco", "")).strip()
    tipo = str(row.get("tipo", "")).strip()
    if foco and tipo:
        return f"Candidato a abordar — {tipo} com foco em {foco} (a confirmar canal)."
    return "Candidato a abordar (a confirmar foco e canal)."
