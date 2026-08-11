"""Scraper dos deputados FEDERAIS de SP via API de dados abertos da Câmara.

Fonte: https://dadosabertos.camara.leg.br/api/v2/deputados (JSON oficial — não é
raspagem de HTML). Traz o ROSTER cru (id, nome, partido, UF, e-mail, foto) da
legislatura atual, filtrado por UF=SP.

IMPORTANTE — o que este módulo NÃO faz:
  * NÃO escreve no Google Sheets de produção. Aterrissa num CSV versionado
    (data/deputados_federais_camara.csv), append-only + dedup por ID da Câmara,
    no mesmo espírito do radar.
  * NÃO inventa score/aderência/chance/estratégia. A base federal é CURADA à mão;
    o que vem daqui é dado CRU — "candidato a curar", nunca auto-pontuado.

Rodar manualmente (na máquina do usuário, que tem rede):
    python -m src.camara_federais
As funções de PARSE e DEDUP são puras (testáveis sem rede).
"""
from __future__ import annotations

import csv
from pathlib import Path

API_URL = "https://dadosabertos.camara.leg.br/api/v2/deputados"
CACHE_CSV = Path(__file__).resolve().parent.parent / "data" / "deputados_federais_camara.csv"

# Colunas do cache (cruas + rastro de origem). NÃO inclui score/aderência/chance:
# esses são curados à mão na aba do Sheets, não vêm da Câmara.
CAMPOS = ["id", "nome", "partido", "uf", "email", "foto", "uri", "fonte"]


def parse_deputado(item: dict) -> dict:
    """Um item cru da API v2/deputados → nosso dicionário. PURA/testável.

    Esquema real da API (estável): {id, uri, nome, siglaPartido, uriPartido,
    siglaUf, idLegislatura, urlFoto, email}. Campo ausente vira "" (nunca quebra)."""
    def g(k):
        v = (item or {}).get(k)
        return "" if v is None else str(v).strip()
    return {
        "id": g("id"),
        "nome": g("nome"),
        "partido": g("siglaPartido"),
        "uf": g("siglaUf"),
        "email": g("email"),
        "foto": g("urlFoto"),
        "uri": g("uri"),
        "fonte": "camara-api",
    }


def dedup_novos(scraped: list[dict], existentes_ids) -> list[dict]:
    """Filtra os scrapeados, tirando quem já existe na base (por ID da Câmara).
    PURA. `existentes_ids` = iterável de IDs já cadastrados (Sheets/CSV). Também
    remove duplicatas DENTRO do scrape (mesmo id repetido na paginação)."""
    ja = {str(x).strip() for x in (existentes_ids or []) if str(x).strip()}
    novos, vistos = [], set()
    for d in scraped:
        i = str(d.get("id", "")).strip()
        if not i or i in ja or i in vistos:
            continue
        vistos.add(i)
        novos.append(d)
    return novos


# --------------------------------------------------------------------------- #
# Rede (NÃO exercitado nos testes; roda na máquina com internet)
# --------------------------------------------------------------------------- #
def buscar_deputados_sp(uf: str = "SP", itens: int = 100, timeout: int = 20) -> list[dict]:
    """Busca (com paginação) os deputados da UF na legislatura atual e devolve a
    lista já parseada. Requer rede. Levanta em erro de rede (o caller trata)."""
    import requests  # import tardio: o parse/dedup não dependem de rede
    out, pagina = [], 1
    while True:
        r = requests.get(API_URL, params={"siglaUf": uf, "itens": itens,
                                           "pagina": pagina, "ordem": "ASC",
                                           "ordenarPor": "nome"},
                         headers={"Accept": "application/json"}, timeout=timeout)
        r.raise_for_status()
        dados = r.json().get("dados", []) or []
        out += [parse_deputado(x) for x in dados]
        if len(dados) < itens:
            break
        pagina += 1
    return out


def _ler_ids_cache(caminho: Path = CACHE_CSV) -> set:
    if not caminho.exists():
        return set()
    with caminho.open(encoding="utf-8-sig", newline="") as f:
        return {str(r.get("id", "")).strip() for r in csv.DictReader(f)}


def atualizar_cache_camara(uf: str = "SP", existentes_ids=None) -> dict:
    """Fetch + dedup + APPEND no CSV cache (nunca no Sheets). `existentes_ids` =
    IDs já na base curada (passe carregar_deputados_federais()['ID'] para não
    recadastrar). Sem isso, deduplica só contra o próprio cache. {sucesso, ...}."""
    try:
        scraped = buscar_deputados_sp(uf=uf)
    except Exception as e:  # noqa: BLE001
        return {"sucesso": False, "mensagem": f"Erro ao consultar a Câmara: {e}"}
    ja = set(_ler_ids_cache()) | {str(x).strip() for x in (existentes_ids or [])}
    novos = dedup_novos(scraped, ja)
    CACHE_CSV.parent.mkdir(parents=True, exist_ok=True)
    escrever_cabecalho = not CACHE_CSV.exists()
    with CACHE_CSV.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if escrever_cabecalho:
            w.writeheader()
        for d in novos:
            w.writerow({k: d.get(k, "") for k in CAMPOS})
    return {"sucesso": True, "encontrados": len(scraped), "novos": len(novos),
            "cache": str(CACHE_CSV)}


if __name__ == "__main__":
    res = atualizar_cache_camara()
    if res["sucesso"]:
        print(f"OK — {res['encontrados']} deputados SP na Câmara · {res['novos']} "
              f"novos gravados em {res['cache']} (crus, a curar).")
    else:
        print(res["mensagem"])
