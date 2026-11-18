"""Trend-Analyse aus Chart-Exporten (CSV).

Erwartete Spalten (Header, Reihenfolge egal; fehlende optionale Spalten ok):
    date (YYYY-MM-DD), title, artist, genre, streams      – Pflicht
    rank, bpm, duration_s                                  – optional

Quellen: eigene Exporte z.B. aus Spotify-Charts-Seiten, Chartmetric/Soundcharts,
TikTok Creative Center (manuell), oder dein Spotify-for-Artists-Export.
Hinweis: Spotifys Web-API liefert für neue Apps seit Ende 2024 keine
Audio-Features (BPM/Energy) mehr – BPM muss aus anderer Quelle oder manuell kommen.

Mathematik
----------
* Momentum eines Tracks = Steigung der Regressionsgeraden von ln(streams) über die
  Tage  →  tägliche Wachstumsrate  g = e^slope − 1.
* Genre-Momentum = Median der Track-Wachstumsraten (robust gegen Ausreißer).
* Kalibrierung: Sweet-Spot-BPM = Median, Bereich = 10.–90. Perzentil.
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from statistics import median

from .genres import GENRES


@dataclass
class TrackTrend:
    title: str
    artist: str
    genre: str
    days: int
    last_streams: float
    growth_per_day: float   # 0.05 = +5 %/Tag
    r2: float

    @property
    def rising(self) -> bool:
        return self.growth_per_day > 0.02 and self.r2 > 0.5


def _ols(xs: list[float], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return 0.0, 0.0
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (my + slope * (x - mx))) ** 2 for x, y in zip(xs, ys))
    r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
    return slope, r2


def percentile(vals: list[float], p: float) -> float:
    s = sorted(vals)
    if not s:
        return float("nan")
    k = (len(s) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def load_csv(path: str | Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["streams"] = float(r["streams"])
        for k in ("bpm", "duration_s", "rank"):
            r[k] = float(r[k]) if r.get(k) not in (None, "") else None
    return rows


def track_trends(rows: list[dict]) -> list[TrackTrend]:
    series: dict[tuple, list[tuple[date, float]]] = defaultdict(list)
    meta = {}
    for r in rows:
        k = (r["title"], r["artist"])
        series[k].append((date.fromisoformat(r["date"]), r["streams"]))
        meta[k] = r["genre"]
    out = []
    for (title, artist), pts in series.items():
        pts.sort()
        if len(pts) < 3:
            continue
        d0 = pts[0][0]
        xs = [(d - d0).days for d, _ in pts]
        ys = [math.log(max(1.0, s)) for _, s in pts]
        slope, r2 = _ols(xs, ys)
        out.append(TrackTrend(title, artist, meta[(title, artist)], len(pts), pts[-1][1], math.exp(slope) - 1, r2))
    return sorted(out, key=lambda t: t.growth_per_day, reverse=True)


def genre_summary(rows: list[dict]) -> dict[str, dict]:
    trends = track_trends(rows)
    by_genre: dict[str, dict] = defaultdict(lambda: {"bpm": [], "dur": [], "growth": [], "streams": 0.0, "tracks": set()})
    for r in rows:
        g = by_genre[r["genre"]]
        g["tracks"].add((r["title"], r["artist"]))
        g["streams"] += r["streams"]
        if r["bpm"]:
            g["bpm"].append(r["bpm"])
        if r["duration_s"]:
            g["dur"].append(r["duration_s"])
    for t in trends:
        by_genre[t.genre]["growth"].append(t.growth_per_day)
    out = {}
    for name, g in by_genre.items():
        uniq_bpm = g["bpm"]
        out[name] = {
            "tracks": len(g["tracks"]),
            "total_streams": g["streams"],
            "momentum_per_day": median(g["growth"]) if g["growth"] else 0.0,
            "rising_tracks": sum(1 for t in trends if t.genre == name and t.rising),
            "bpm_median": median(uniq_bpm) if uniq_bpm else None,
            "bpm_p10": percentile(uniq_bpm, 0.1) if uniq_bpm else None,
            "bpm_p90": percentile(uniq_bpm, 0.9) if uniq_bpm else None,
            "duration_p10": percentile(g["dur"], 0.1) if g["dur"] else None,
            "duration_p90": percentile(g["dur"], 0.9) if g["dur"] else None,
        }
    return dict(sorted(out.items(), key=lambda kv: kv[1]["momentum_per_day"], reverse=True))


def calibrate(rows: list[dict], out_path: str | Path) -> dict:
    """Schreibt Profil-Overrides (nur für Genres, die es in GENRES gibt)."""
    summ = genre_summary(rows)
    cal = {}
    for key, s in summ.items():
        if key not in GENRES or s["bpm_median"] is None:
            continue
        c = {"bpm_opt": round(s["bpm_median"]), "bpm_min": round(s["bpm_p10"]), "bpm_max": round(s["bpm_p90"])}
        if s["duration_p10"] is not None:
            c["duration_min_s"] = round(s["duration_p10"])
            c["duration_max_s"] = round(s["duration_p90"])
        cal[key] = c
    Path(out_path).write_text(json.dumps(cal, indent=2), encoding="utf-8")
    return cal


def apply_calibration(path: str | Path) -> list[str]:
    p = Path(path)
    if not p.exists():
        return []
    cal = json.loads(p.read_text(encoding="utf-8"))
    changed = []
    for key, vals in cal.items():
        if key in GENRES:
            for k, v in vals.items():
                setattr(GENRES[key], k, v)
            changed.append(key)
    return changed


def write_demo_csv(path: str | Path, days: int = 21, seed: int = 7) -> None:
    """Erzeugt SYNTHETISCHE Beispieldaten zum Ausprobieren (keine echten Charts!)."""
    rng = random.Random(seed)
    start = date.today() - timedelta(days=days)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "title", "artist", "genre", "streams", "bpm", "duration_s"])
        for gkey, g in GENRES.items():
            for i in range(6):
                base = rng.uniform(2e3, 8e4)
                growth = rng.gauss(0.01 if gkey not in ("nordic_folk_pop", "phonk") else 0.05, 0.03)
                bpm = round(rng.gauss(g.bpm_opt, (g.bpm_max - g.bpm_min) / 5))
                dur = round(rng.uniform(g.duration_min_s, g.duration_max_s))
                for d in range(days):
                    s = base * math.exp(growth * d) * rng.uniform(0.9, 1.1)
                    w.writerow([(start + timedelta(days=d)).isoformat(), f"Demo {gkey} {i+1}",
                                f"Synthetic Artist {i+1}", gkey, round(s), bpm, dur])
