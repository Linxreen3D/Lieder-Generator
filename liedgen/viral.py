"""Viral-Score: quantifiziert, wie gut ein Song zu bekannten Viral-Mustern passt.

Warum diese Merkmale?
---------------------
* Streaming zählt erst nach 30 Sekunden (Spotify). Wer vorher skippt, ist verloren
  → Hook früh, Intro kurz.
* Short-Form (TikTok/Reels/Shorts) braucht einen 10–30 s langen, in sich
  geschlossenen Ausschnitt → "Clipbarkeit".
* Ohrwürmer entstehen durch Wiederholung + Vorhersagbarkeit mit kleiner
  Überraschung → Kompressionsrate der Lyrics (Informationsgehalt), Hook-Wiederholung.
* Singbarkeit: kurze, gleichmäßige Zeilen im Refrain (Silben/Zeile, geringe Varianz).
* Tempo und Länge: jede Nische hat einen Sweet-Spot (Genre-Profil, kalibrierbar).

Jedes Merkmal wird auf [0, 1] abgebildet; der Gesamtscore ist ein gewichtetes
GEOMETRISCHES Mittel × 100. Das geometrische Mittel bestraft "schwächstes Glied"-
Fehler: ein perfekter Refrain rettet keinen Song, dessen Hook erst nach 60 s kommt.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import mean, pstdev

from . import lyrics as L
from .genres import GenreProfile

INSTRUMENTAL_TAGS = ("intro", "outro", "instrumental", "break", "drop", "build", "solo", "interlude", "theme")

WEIGHTS = {
    "hook_timing": 0.20,
    "hook_repetition": 0.15,
    "intro": 0.08,
    "duration": 0.10,
    "tempo": 0.10,
    "repetition": 0.10,
    "singability": 0.10,
    "rhyme": 0.07,
    "clipability": 0.05,
    "address": 0.05,
}
LYRIC_FEATURES = {"repetition", "singability", "rhyme", "address"}


def gauss(x: float, mu: float, sigma: float) -> float:
    return math.exp(-0.5 * ((x - mu) / sigma) ** 2)


def soft_range(x: float, lo: float, hi: float, softness: float) -> float:
    """1 innerhalb [lo, hi], gaußförmiger Abfall außerhalb."""
    if lo <= x <= hi:
        return 1.0
    edge = lo if x < lo else hi
    return gauss(x, edge, softness)


@dataclass
class TimedSection:
    tag: str
    lines: list[str]
    bars: int
    start: float
    end: float
    is_hook: bool

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class FeatureResult:
    name: str
    score: float
    value: str
    tip: str = ""


@dataclass
class ViralReport:
    total: float
    features: list[FeatureResult]
    timeline: list[TimedSection] = field(default_factory=list)
    duration_s: float = 0.0
    bpm: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total": round(self.total, 1),
            "duration_s": round(self.duration_s, 1),
            "bpm": self.bpm,
            "features": [
                {"name": f.name, "score": round(f.score, 3), "value": f.value, "tip": f.tip}
                for f in self.features
            ],
            "timeline": [
                {"tag": t.tag, "start": round(t.start, 1), "end": round(t.end, 1), "bars": t.bars, "hook": t.is_hook}
                for t in self.timeline
            ],
        }

    def tips(self) -> list[str]:
        return [f.tip for f in sorted(self.features, key=lambda f: f.score) if f.tip]


def estimate_bars(sec: L.LyricSection) -> int:
    t = sec.tag.lower()
    if not sec.lines:
        return 8 if any(k in t for k in ("drop", "theme")) else 4
    # Faustregel: eine Lyrik-Zeile ≈ 2 Takte
    return max(2, len(sec.lines) * 2)


def build_timeline(sections: list[L.LyricSection], bpm: float, bars: list[int] | None = None) -> list[TimedSection]:
    spb = 240.0 / bpm
    out, t = [], 0.0
    for i, s in enumerate(sections):
        b = bars[i] if bars and i < len(bars) and bars[i] else estimate_bars(s)
        out.append(TimedSection(s.tag, s.lines, b, t, t + b * spb, s.is_hook))
        t += b * spb
    return out


def score_song(title: str, lyrics_text: str, genre: GenreProfile, bpm: float | None = None,
               bars: list[int] | None = None) -> ViralReport:
    bpm = float(bpm or genre.bpm_opt)
    sections = L.parse(lyrics_text)
    tl = build_timeline(sections, bpm, bars)
    duration = tl[-1].end if tl else 0.0
    instrumental = genre.language == "instrumental"
    feats: list[FeatureResult] = []

    # 1) Hook-Timing
    hooks = [t for t in tl if t.is_hook]
    t_hook = hooks[0].start if hooks else duration
    s = 1.0 if t_hook <= genre.hook_deadline_s else math.exp(-(t_hook - genre.hook_deadline_s) / 12.0)
    feats.append(FeatureResult(
        "hook_timing", s, f"Hook bei {t_hook:.0f}s (Ziel ≤ {genre.hook_deadline_s:.0f}s)",
        "" if s > 0.8 else "Hook früher bringen: Refrain-Snippet als Intro oder Strophe 1 kürzen.",
    ))

    # 2) Hook-Wiederholung (Anzahl Refrains + Titel im Text)
    n_hooks = len(hooks)
    title_n = L.title_occurrences(title, sections) if not instrumental else 4
    target = max(1, min(3, sum(1 for x in genre.structure if x.is_hook)))
    s_rep = min(1.0, n_hooks / target) * (0.5 + 0.5 * min(1.0, title_n / 4.0))
    feats.append(FeatureResult(
        "hook_repetition", s_rep, f"{n_hooks} Hook-Teile, Titel {title_n}x im Text",
        "" if s_rep > 0.8 else "Mind. 3 Refrains/Drops und den Titel ≥4x singen – der Titel ist das Suchwort.",
    ))

    # 3) Intro-Länge (Zeit bis erste Vocal- oder Hook-Sektion)
    first_content = next((t for t in tl if t.is_hook or (t.lines and not t.tag.lower().startswith("intro"))), None)
    t_intro = first_content.start if first_content else duration
    intro_max = max(5.0, 480.0 / bpm)   # "kurz" = max. 5 s bzw. 2 Takte
    s = 1.0 if t_intro <= intro_max + 0.05 else math.exp(-(t_intro - intro_max) / 6.0)
    feats.append(FeatureResult(
        "intro", s, f"Intro {t_intro:.1f}s (Ziel ≤ {intro_max:.0f}s)",
        "" if s > 0.8 else "Intro auf ≤5 s kürzen (in Suno: [Short Intro] oder direkt mit [Chorus] starten).",
    ))

    # 4) Länge
    s = soft_range(duration, genre.duration_min_s, genre.duration_max_s, 20)
    feats.append(FeatureResult(
        "duration", s, f"{duration:.0f}s (Ziel {genre.duration_min_s}–{genre.duration_max_s}s)",
        "" if s > 0.8 else ("Song kürzen – kurze Songs = mehr Replays pro Hörer."
                            if duration > genre.duration_max_s else "Song etwas länger machen (Bridge/2. Refrain)."),
    ))

    # 5) Tempo (Half-/Double-Time zählt mit)
    sigma = max(4.0, (genre.bpm_max - genre.bpm_min) / 3)
    s = max(gauss(bpm * k, genre.bpm_opt, sigma) for k in (0.5, 1.0, 2.0))
    feats.append(FeatureResult(
        "tempo", s, f"{bpm:.0f} BPM (Sweet-Spot {genre.bpm_opt})",
        "" if s > 0.7 else f"Tempo Richtung {genre.bpm_opt} BPM verschieben (BPM in den Suno-Style schreiben).",
    ))

    # 6) Clipbarkeit: gibt es einen Hook-Teil von 10–30 s?
    # 10–30 s ideal; längere Hook-Teile lassen sich noch schneiden (bis ~48 s ohne Abzug)
    best = max((soft_range(h.duration, 10, 48, 8) for h in hooks), default=0.0)
    feats.append(FeatureResult(
        "clipability", best,
        f"Hook-Länge {', '.join(f'{h.duration:.0f}s' for h in hooks[:3]) or '–'}",
        "" if best > 0.8 else "Ein Hook-Teil sollte 10–30 s lang und für sich verständlich sein (TikTok-Sound).",
    ))

    if not instrumental and not genre.chant:
        all_lines = [l for s_ in sections for l in s_.lines]
        hook_lines = [l for h in hooks for l in h.lines] or all_lines

        # 7) Wiederholung / Informationsdichte
        cr = L.compression_ratio("\n".join(all_lines))
        s = gauss(cr, 0.40, 0.10) if cr > 0.40 else soft_range(cr, 0.25, 0.40, 0.08)
        feats.append(FeatureResult(
            "repetition", s, f"Kompressionsrate {cr:.2f} (Ziel 0.25–0.40)",
            "" if s > 0.7 else ("Mehr Wiederholung: Refrain-Zeilen exakt wiederholen, Strophen-Motive aufgreifen."
                                if cr > 0.4 else "Zu monoton – Strophen brauchen neue Bilder."),
        ))

        # 8) Singbarkeit des Hooks
        syl = [L.line_syllables(l) for l in hook_lines] or [0]
        m, sd = mean(syl), pstdev(syl) if len(syl) > 1 else 0.0
        cv = sd / m if m else 1.0
        s = gauss(m, 8, 3.5) * math.exp(-max(0.0, cv - 0.2) * 2)
        feats.append(FeatureResult(
            "singability", s, f"Hook Ø {m:.1f} Silben/Zeile, Streuung {cv:.0%}",
            "" if s > 0.7 else "Hook-Zeilen auf 6–10 Silben und gleich lang bringen.",
        ))

        # 9) Reimdichte
        dens = mean([L.rhyme_density(s_.lines) for s_ in sections if len(s_.lines) >= 2] or [0.0])
        s = min(1.0, dens / 0.5)
        feats.append(FeatureResult(
            "rhyme", s, f"Reimdichte {dens:.0%}",
            "" if s > 0.7 else "Mehr Endreime (AABB oder ABAB) – Reime machen Zeilen vorhersagbar & merkbar.",
        ))

        # 10) Direkte Ansprache
        if genre.pronouns:
            pr = set(genre.pronouns)
            share = sum(1 for l in all_lines if pr & set(L.words(l))) / max(1, len(all_lines))
            s = min(1.0, share / 0.3)
            feats.append(FeatureResult(
                "address", s, f"{share:.0%} der Zeilen mit {'/'.join(genre.pronouns[:3])}",
                "" if s > 0.7 else "Hörer direkt ansprechen – Ich/Du-Perspektive erhöht Identifikation.",
            ))

    total_w = sum(WEIGHTS[f.name] for f in feats)
    log_sum = sum(WEIGHTS[f.name] * math.log(max(0.05, f.score)) for f in feats)
    total = 100.0 * math.exp(log_sum / total_w)
    return ViralReport(total, feats, tl, duration, bpm)
