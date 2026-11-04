"""Leitura de fonte por FEED RSS e pela API do WordPress (mais estável que HTML).

    python tests/test_radar_feeds.py
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from radar.fontes_genericas import MAX_IDADE_DIAS, itens_de_feed, itens_de_wp_api  # noqa: E402

HOJE = datetime.date(2026, 11, 4)
RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>X</title>
<item><title><![CDATA[Instituto X abre edital para projetos de educação]]></title>
<link>https://x.org/edital-2026</link><pubDate>Mon, 02 Nov 2026 10:00:00 +0000</pubDate>
<description><![CDATA[<p>Inscrições até 30/11. Apoio de <b>R$ 200 mil</b>.</p>]]></description></item>
<item><title>Edital antigo de 2024 para OSCs</title><link>https://x.org/velho</link>
<pubDate>Mon, 01 Apr 2024 10:00:00 +0000</pubDate></item>
<item><title>Sem data mas com título longo o bastante</title><link>https://x.org/sem-data</link></item>
<item><title>Curto</title><link>https://x.org/curto</link></item>
</channel></rss>"""


def test_feed_rss_tira_html_e_guarda_data():
    itens = itens_de_feed(RSS, "X", hoje_=HOJE)
    assert itens[0]["titulo"] == "Instituto X abre edital para projetos de educação"
    assert itens[0]["url"] == "https://x.org/edital-2026"
    assert itens[0]["descricao"] == "Inscrições até 30/11. Apoio de R$ 200 mil."
    assert itens[0]["publicado_em"] == "2026-11-02"


def test_feed_corta_post_velho_e_mantem_sem_data():
    urls = [i["url"] for i in itens_de_feed(RSS, "X", hoje_=HOJE)]
    assert "https://x.org/velho" not in urls, f"post com mais de {MAX_IDADE_DIAS} dias"
    assert "https://x.org/sem-data" in urls, "sem data não dá para julgar: mantém"
    assert "https://x.org/curto" not in urls


def test_feed_atom():
    atom = """<feed><entry><title>Chamada pública para OSCs de educação</title>
    <link href="https://y.org/chamada"/><published>2026-10-30T09:00:00Z</published>
    <summary>Projetos com jovens</summary></entry></feed>"""
    itens = itens_de_feed(atom, "Y", hoje_=HOJE)
    assert itens[0]["url"] == "https://y.org/chamada" and itens[0]["publicado_em"] == "2026-10-30"


def test_api_do_wordpress():
    posts = [{"title": {"rendered": "Edital &#8211; apoio a projetos sociais 2026"},
              "link": "https://z.org/e", "date": "2026-10-20T10:00:00",
              "excerpt": {"rendered": "<p>OSCs de SP</p>"}},
             {"title": {"rendered": "Notícia velha sobre edital"}, "link": "https://z.org/v",
              "date": "2025-01-01T10:00:00", "excerpt": {"rendered": ""}}]
    itens = itens_de_wp_api(posts, "Z", hoje_=HOJE)
    assert [i["url"] for i in itens] == ["https://z.org/e"]
    assert itens[0]["titulo"] == "Edital – apoio a projetos sociais 2026"


def test_feed_quebrado_nao_derruba():
    assert itens_de_feed("isto não é xml", "X", hoje_=HOJE) == []
    assert itens_de_wp_api(None, "X", hoje_=HOJE) == []


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
            print(f"ok  {nome}")
    print("feeds do radar: todos os testes passaram")
