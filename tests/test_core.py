from datetime import date, timedelta

import pytest

from liedgen import lyrics as L
from liedgen import generator, trends
from liedgen.genres import GENRES, get
from liedgen.portfolio import Portfolio
from liedgen.suno import STYLE_LIMIT, build_style
from liedgen.viral import score_song


@pytest.mark.parametrize("key", list(GENRES))
def test_default_structure_meets_own_targets(key):
    g = GENRES[key]
    tl = g.section_seconds()
    first_hook = next(a for s, a, _ in tl if s.is_hook)
    assert first_hook <= g.hook_deadline_s
    assert g.duration_min_s <= tl[-1][2] <= g.duration_max_s


@pytest.mark.parametrize("key", list(GENRES))
def test_template_generation_scores_and_exports(key):
    cands = generator.generate(key, n=3, backend="template", seed=1)
    assert len(cands) == 3
    assert cands[0].report.total >= cands[-1].report.total
    for c in cands:
        assert 0 <= c.report.total <= 100
        assert len(c.suno.style) <= STYLE_LIMIT
        assert c.suno.lyrics.strip().startswith("[")


def test_parse_and_render_roundtrip():
    text = "[Verse 1]\nA line\nB line\n\n[Chorus]\nHook (yeah)\n"
    secs = L.parse(text)
    assert [s.tag for s in secs] == ["Verse 1", "Chorus"]
    assert secs[1].is_hook and not secs[0].is_hook
    assert L.parse(L.render(secs))[1].lines == ["Hook (yeah)"]


def test_rhymes_and_syllables():
    assert L.rhymes("Ich bleib wach bis ich es hab", "Nachtschicht, Blick auf die Stadt") is False
    assert L.rhymes("Your voice is calling through the night", "The northern lights are pulling in") is False
    assert L.rhymes("Cold light falling on the bay", "Our fathers boats have sailed away")
    assert L.rhymes("Kafana prazna, čaša puna", "Moje srce je tuge puna")
    assert L.syllables("Sommer") == 2
    assert L.line_syllables("3 Uhr nachts und du bist nicht da") >= 6


def test_late_hook_is_penalised():
    g = get("deutschrap_melodic")
    early = "[Hook]\n" + "\n".join(["Du und ich im Licht der Nacht"] * 4) + "\n[Verse 1]\n" + "\n".join(["Strophe Zeile hier"] * 8)
    late = "[Intro]\n[Verse 1]\n" + "\n".join(["Strophe Zeile hier"] * 16) + "\n[Hook]\n" + "\n".join(["Du und ich im Licht der Nacht"] * 4)
    a = score_song("Licht der Nacht", early, g, 100)
    b = score_song("Licht der Nacht", late, g, 100)
    assert a.total > b.total
    assert any("Hook früher" in t for t in b.tips())


def test_style_limit_respected():
    g = get("nordic_folk_pop")
    s = build_style(g, 96, "D minor", ["x" * 50] * 30, limit=200)
    assert len(s) <= 200


def test_trend_growth_detection(tmp_path):
    p = tmp_path / "c.csv"
    trends.write_demo_csv(p, days=14)
    rows = trends.load_csv(p)
    summ = trends.genre_summary(rows)
    assert set(summ) == set(GENRES)
    # Demo-Daten: Nordic/Phonk wachsen schneller
    order = list(summ)
    assert order.index("phonk") < order.index("schlager_party") or order.index("nordic_folk_pop") < 4
    cal = trends.calibrate(rows, tmp_path / "cal.json")
    assert "bpm_opt" in cal["phonk"]


def test_portfolio_dashboard(tmp_path):
    pf = Portfolio(tmp_path / "t.db")
    pf.add_artist("Nordvind", "nordic_folk_pop")
    sid = pf.add_song("Carry Me Home", "nordic_folk_pop", "Nordvind", viral_score=90)
    pf.set_status(sid, "live")
    today = date(2026, 6, 30)
    for i in range(14):
        pf.add_stats(sid, (today - timedelta(days=i)).isoformat(), 100 + i * 10)
    d = pf.dashboard(0.004, today)
    a = d["artists"][0]
    assert a["live"] == 1 and a["streams"] == sum(100 + i * 10 for i in range(14))
    assert a["revenue_eur"] == round(a["streams"] * 0.004, 2)   # > 1000 Streams → zahlungsrelevant
    assert a["growth_7d"] < 0  # ältere Tage hatten mehr Streams
    with pytest.raises(ValueError):
        pf.set_status(sid, "quatsch")


def test_manual_prompt_and_import():
    from pathlib import Path
    p = generator.manual_prompt("balkan_ballade", 2, "Heimweh")
    assert "Heimweh" in p and '"songs"' in p and "[Chorus]" in p
    answer = (Path(__file__).parent / "beispiel_antwort.txt").read_text(encoding="utf-8")
    cands = generator.import_answer("balkan_ballade", answer)
    assert cands[0].title == "Ne Zovi Me" and cands[0].backend == "claude.ai"
    assert cands[0].report.total > 80 and "[Chorus]" in cands[0].suno.lyrics
    with pytest.raises(ValueError):
        generator.import_answer("balkan_ballade", "Sorry, kein JSON hier")
