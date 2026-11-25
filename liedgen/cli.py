"""Kommandozeile: `liedgen <befehl>` bzw. `python -m liedgen <befehl>`."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import generator, trends
from .genres import GENRES, focus_keys, get as get_genre
from .portfolio import DEFAULT_PAYOUT_EUR, STATUSES, Portfolio
from .viral import score_song

CAL_FILE = os.environ.get("LIEDGEN_CALIBRATION", "liedgen_calibration.json")


def _bar(x: float, width: int = 20) -> str:
    n = round(max(0.0, min(1.0, x)) * width)
    return "█" * n + "·" * (width - n)


def print_report(rep) -> None:
    print(f"  Viral-Score: {rep.total:5.1f}/100   Länge {rep.duration_s:.0f}s @ {rep.bpm:.0f} BPM")
    for f in rep.features:
        print(f"    {f.name:<16} {_bar(f.score)} {f.score:4.2f}  {f.value}")
    tips = rep.tips()
    if tips:
        print("  Verbesserungen:")
        for t in tips[:4]:
            print(f"    → {t}")


def cmd_genres(a):
    for g in (GENRES[k] for k in focus_keys()):
        if a.verbose:
            print(f"\n=== {g.key}: {g.name} ===\n{g.description}")
            print(f"BPM {g.bpm_min}-{g.bpm_max} (opt {g.bpm_opt}) | Länge {g.duration_min_s}-{g.duration_max_s}s"
                  f" | Hook ≤{g.hook_deadline_s:.0f}s | Sprache {g.language}")
            print("Struktur:", " → ".join(f"{s.tag}({s.bars})" for s in g.structure))
            print("Markt:", g.market_notes)
        else:
            print(f"{g.key:<20} {g.name:<32} {g.bpm_opt:>4} BPM  {g.language}")


def cmd_generate(a):
    _show_candidates(a, generator.generate(a.genre, a.n, a.theme, a.backend, a.seed))


def _show_candidates(a, cands):
    out_dir = Path(a.out) if a.out else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
    pf = Portfolio(a.db) if a.save else None
    for i, c in enumerate(cands[: a.show], 1):
        print(f"\n#{i}  {c.title}  [{c.backend}]  {c.key}, {c.bpm:.0f} BPM  – {c.concept}")
        print_report(c.report)
        if a.full or i == 1:
            print("\n" + c.suno.to_markdown())
        if out_dir:
            stem = f"{c.genre}_{i:02d}_{''.join(ch if ch.isalnum() else '_' for ch in c.title)[:40]}"
            (out_dir / f"{stem}.md").write_text(c.suno.to_markdown(), encoding="utf-8")
            (out_dir / f"{stem}.json").write_text(json.dumps(c.to_dict(), ensure_ascii=False, indent=2),
                                                  encoding="utf-8")
        if pf and i <= a.save:
            sid = pf.add_song(c.title, c.genre, a.artist, "generiert", round(c.report.total, 1), c.bpm,
                              c.suno.to_dict(), c.lyrics, c.concept)
            print(f"  → im Portfolio gespeichert (Song-ID {sid})")
    if out_dir:
        print(f"\nExport: {out_dir}/")


def cmd_prompt(a):
    text = generator.manual_prompt(a.genre, a.n, a.theme)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"Prompt gespeichert: {a.out} – Inhalt in claude.ai einfügen.")
    else:
        print(text)


def cmd_import(a):
    text = Path(a.file).read_text(encoding="utf-8") if a.file != "-" else sys.stdin.read()
    a.backend, a.seed = None, None
    _show_candidates(a, generator.import_answer(a.genre, text))


def cmd_score(a):
    text = Path(a.file).read_text(encoding="utf-8") if a.file != "-" else sys.stdin.read()
    rep = score_song(a.title, text, get_genre(a.genre), a.bpm)
    print(f"„{a.title}“ als {get_genre(a.genre).name}")
    print_report(rep)
    if a.json:
        print(json.dumps(rep.to_dict(), ensure_ascii=False, indent=2))


def cmd_trends(a):
    if a.action == "demo":
        trends.write_demo_csv(a.csv)
        print(f"SYNTHETISCHE Demo-Daten geschrieben: {a.csv} (nicht echt – nur zum Testen!)")
        return
    rows = trends.load_csv(a.csv)
    if a.action == "calibrate":
        cal = trends.calibrate(rows, CAL_FILE)
        print(f"Kalibrierung für {len(cal)} Genres → {CAL_FILE}")
        print(json.dumps(cal, indent=2))
        return
    summ = trends.genre_summary(rows)
    print(f"{'Genre':<22}{'Tracks':>7}{'Momentum/Tag':>14}{'steigend':>10}{'BPM (p10–med–p90)':>22}")
    for g, s in summ.items():
        bpm = (f"{s['bpm_p10']:.0f}–{s['bpm_median']:.0f}–{s['bpm_p90']:.0f}" if s["bpm_median"] else "–")
        print(f"{g:<22}{s['tracks']:>7}{s['momentum_per_day']:>+13.1%}{s['rising_tracks']:>10}{bpm:>22}")
    print("\nAm schnellsten wachsende Tracks:")
    for t in trends.track_trends(rows)[: a.top]:
        print(f"  {t.growth_per_day:+6.1%}/Tag  R²={t.r2:.2f}  {t.title} – {t.artist} ({t.genre})")


def cmd_artist(a):
    pf = Portfolio(a.db)
    if a.action == "add":
        get_genre(a.genre)
        aid = pf.add_artist(a.name, a.genre, a.spotify or "", a.distributor or "", a.persona or "")
        print(f"Artist #{aid} '{a.name}' ({a.genre}) angelegt")
    else:
        for r in pf.artists():
            print(f"#{r['id']:<3} {r['name']:<24} {r['genre']:<20} {r['distributor']:<12} {r['spotify_url']}")


def cmd_song(a):
    pf = Portfolio(a.db)
    if a.action == "list":
        for s in pf.songs(a.artist):
            sc = f"{s['viral_score']:.0f}" if s["viral_score"] is not None else "–"
            print(f"#{s['id']:<4} {s['title'][:30]:<30} {(s['artist'] or '–')[:18]:<18} {s['status']:<12}"
                  f" Score {sc:>3}  Streams {s['streams']:>9,}")
    elif a.action == "status":
        pf.set_status(a.id, a.status, a.date)
        print(f"Song #{a.id} → {a.status}")
    elif a.action == "assign":
        pf.assign(a.id, a.artist_name)
        print(f"Song #{a.id} → {a.artist_name}")
    elif a.action == "show":
        s = pf.song(a.id)
        suno = json.loads(s["suno_json"]) if s["suno_json"] else {}
        print(f"#{s['id']} {s['title']} ({s['genre']}, {s['status']})\n")
        print("Style:", suno.get("style", ""))
        print("Exclude:", suno.get("exclude_styles", ""))
        print("\n" + (s["lyrics"] or ""))


def cmd_stats(a):
    pf = Portfolio(a.db)
    if a.action == "add":
        pf.add_stats(a.song_id, a.day, a.streams, a.listeners, a.saves)
        print("gespeichert")
    else:
        d = pf.dashboard(a.payout)
        t = d["totals"]
        print(f"Artists {t['artists']} | Songs {t['songs']} (live {t['live']}) | Streams {t['streams']:,}"
              f" | 7 Tage {t['last7']:,} | geschätzt {t['revenue_eur']:.2f} € (@{t['payout_per_stream']} €/Stream)\n")
        for r in d["artists"]:
            g = f"{r['growth_7d']:+.0%}" if r["growth_7d"] is not None else "–"
            top = r["top_song"]["title"] if r["top_song"] else "–"
            print(f"  {r['name']:<22} {r['genre']:<20} Songs {r['songs']:>3} live {r['live']:>3}"
                  f"  Streams {r['streams']:>9,}  7d {r['last7']:>7,} ({g})  ≈{r['revenue_eur']:>8.2f} €  Top: {top}")


def cmd_serve(a):
    from .server import serve
    serve(a.db, a.host, a.port, a.trends, a.payout, a.open)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="liedgen", description="Viral-orientierter Song-Generator für Suno AI")
    p.add_argument("--db", default=os.environ.get("LIEDGEN_DB", "liedgen.db"), help="SQLite-Datei")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("genres", help="Genre-Profile anzeigen")
    s.add_argument("-v", "--verbose", action="store_true")
    s.set_defaults(func=cmd_genres)

    s = sub.add_parser("generate", help="Song-Kandidaten erzeugen und bewerten")
    s.add_argument("genre", choices=list(GENRES))
    s.add_argument("-n", type=int, default=5, help="Anzahl Kandidaten")
    s.add_argument("--theme")
    s.add_argument("--backend", choices=["auto", "claude", "template"], default="auto")
    s.add_argument("--seed", type=int)
    s.add_argument("--show", type=int, default=3, help="wie viele anzeigen")
    s.add_argument("--full", action="store_true", help="Suno-Prompt für alle angezeigten ausgeben")
    s.add_argument("--out", help="Export-Ordner für .md/.json")
    s.add_argument("--save", type=int, default=0, help="die besten N ins Portfolio speichern")
    s.add_argument("--artist", help="Artist für --save")
    s.set_defaults(func=cmd_generate)

    s = sub.add_parser("prompt", help="Prompt für claude.ai erzeugen (kostenlos, ohne API-Key)")
    s.add_argument("genre", choices=list(GENRES))
    s.add_argument("-n", type=int, default=3)
    s.add_argument("--theme")
    s.add_argument("--out", help="in Datei schreiben statt anzeigen")
    s.set_defaults(func=cmd_prompt)

    s = sub.add_parser("import", help="Antwort aus claude.ai einlesen und bewerten")
    s.add_argument("genre", choices=list(GENRES))
    s.add_argument("file", help="Textdatei mit der Antwort oder '-'")
    s.add_argument("--show", type=int, default=3)
    s.add_argument("--full", action="store_true")
    s.add_argument("--out")
    s.add_argument("--save", type=int, default=0)
    s.add_argument("--artist")
    s.set_defaults(func=cmd_import)

    s = sub.add_parser("score", help="Eigene Lyrics bewerten (Datei im Suno-Format oder '-')")
    s.add_argument("file")
    s.add_argument("--genre", required=True, choices=list(GENRES))
    s.add_argument("--title", required=True)
    s.add_argument("--bpm", type=float)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_score)

    s = sub.add_parser("trends", help="Chart-CSV analysieren / kalibrieren")
    s.add_argument("action", choices=["analyze", "calibrate", "demo"])
    s.add_argument("csv")
    s.add_argument("--top", type=int, default=10)
    s.set_defaults(func=cmd_trends)

    s = sub.add_parser("artist", help="Artist-Profile verwalten")
    s.add_argument("action", choices=["add", "list"])
    s.add_argument("--name")
    s.add_argument("--genre", choices=list(GENRES))
    s.add_argument("--spotify")
    s.add_argument("--distributor")
    s.add_argument("--persona")
    s.set_defaults(func=cmd_artist)

    s = sub.add_parser("song", help="Songs verwalten")
    s.add_argument("action", choices=["list", "status", "assign", "show"])
    s.add_argument("id", type=int, nargs="?")
    s.add_argument("--status", choices=STATUSES)
    s.add_argument("--date")
    s.add_argument("--artist", help="Filter für list")
    s.add_argument("--to", dest="artist_name", help="Artist für assign")
    s.set_defaults(func=cmd_song)

    s = sub.add_parser("stats", help="Streams erfassen / Dashboard")
    s.add_argument("action", choices=["add", "dashboard"])
    s.add_argument("--song-id", type=int)
    s.add_argument("--day")
    s.add_argument("--streams", type=int, default=0)
    s.add_argument("--listeners", type=int, default=0)
    s.add_argument("--saves", type=int, default=0)
    s.add_argument("--payout", type=float, default=DEFAULT_PAYOUT_EUR)
    s.set_defaults(func=cmd_stats)

    s = sub.add_parser("serve", help="Web-Dashboard starten")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--trends", help="Chart-CSV für den Trends-Tab")
    s.add_argument("--payout", type=float, default=DEFAULT_PAYOUT_EUR)
    s.add_argument("--open", action="store_true", help="Browser automatisch öffnen")
    s.set_defaults(func=cmd_serve)
    return p


def load_env(path: str = ".env") -> None:
    """Einfache .env-Unterstützung (KEY=wert); leere Werte und bereits gesetzte Variablen werden ignoriert."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if v and not os.environ.get(k):
            os.environ[k] = v


def main(argv: list[str] | None = None) -> None:
    for stream in (sys.stdout, sys.stderr):   # Windows-Konsole: Umlaute/Balken sicher ausgeben
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    load_env()
    trends.apply_calibration(CAL_FILE)
    a = build_parser().parse_args(argv)
    try:
        a.func(a)
    except (KeyError, ValueError, RuntimeError) as e:
        sys.exit(f"Fehler: {e}")


if __name__ == "__main__":
    main()
