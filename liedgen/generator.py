"""Song-Generator: erzeugt mehrere Kandidaten, bewertet sie mit dem Viral-Score
und gibt sie sortiert zurück ("Generate & Select").

Backends
--------
* ``template`` – offline, aus Textbausteinen (templates.py). Immer verfügbar.
* ``claude``   – Claude schreibt Lyrics nach Genre-Profil + Viral-Regeln.
                 Benötigt ``pip install anthropic`` und einen API-Key (ANTHROPIC_API_KEY).
* ``auto``     – Claude, falls verfügbar, sonst Template.
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field

from . import lyrics as L
from .genres import GenreProfile, get as get_genre
from .suno import SunoPrompt, build_prompt
from .templates import BANK
from .viral import ViralReport, score_song

CLAUDE_MODEL = os.environ.get("LIEDGEN_MODEL", "claude-opus-5-5")


@dataclass
class Candidate:
    genre: str
    title: str
    lyrics: str
    bpm: float
    key: str
    concept: str = ""
    style_extra: list[str] = field(default_factory=list)
    bars: list[int] = field(default_factory=list)
    backend: str = "template"
    report: ViralReport | None = None
    suno: SunoPrompt | None = None

    def to_dict(self) -> dict:
        return {
            "genre": self.genre, "title": self.title, "bpm": self.bpm, "key": self.key,
            "concept": self.concept, "backend": self.backend, "lyrics": self.lyrics,
            "score": self.report.to_dict() if self.report else None,
            "tips": self.report.tips() if self.report else [],
            "suno": self.suno.to_dict() if self.suno else None,
        }


def _finalize(c: Candidate, g: GenreProfile) -> Candidate:
    c.report = score_song(c.title, c.lyrics, g, c.bpm, c.bars or None)
    c.suno = build_prompt(g, c.title, c.lyrics, c.bpm, c.key, c.style_extra)
    return c


# ---------------------------------------------------------------- Template-Backend

def _template_candidate(g: GenreProfile, rng: random.Random, theme: str | None) -> Candidate:
    bank = BANK.get(g.key, {"hooks": [("Untitled", [])], "verse": [], "pre": [], "bridge": []})
    title, hook = rng.choice(bank["hooks"])
    # Bausteine sind Reimpaare → paarweise mischen
    pairs = [bank["verse"][i:i + 2] for i in range(0, len(bank["verse"]), 2)]
    rng.shuffle(pairs)
    verse_pool = [line for p in pairs for line in p]
    bpm = round(rng.triangular(g.bpm_min, g.bpm_max, g.bpm_opt))
    sections: list[L.LyricSection] = []
    bars: list[int] = []
    # Variation: manchmal Hook ganz an den Anfang ziehen (Viral-Trick "Hook-first")
    structure = list(g.structure)
    if rng.random() < 0.4 and not structure[1].is_hook and g.language != "instrumental":
        first_hook = next(s for s in structure if s.is_hook)
        structure.insert(1, type(first_hook)(first_hook.tag, 4, True))
    vi = 0
    for s in structure:
        t = s.tag.lower()
        if g.language == "instrumental":
            lines: list[str] = []
        elif s.is_hook and hook:
            lines = hook * max(1, s.bars // 8) if s.bars >= 8 else hook[:2]
        elif "verse" in t:
            n = max(2, min(len(verse_pool), s.bars // 2))
            n -= n % 2   # Reimpaare nicht zerreißen
            if verse_pool:
                lines = [verse_pool[(vi + k) % len(verse_pool)] for k in range(n)]
                vi += n
            else:
                lines = []
        elif "pre" in t and bank["pre"]:
            lines = rng.sample(bank["pre"], min(2, len(bank["pre"])))
        elif "bridge" in t and bank["bridge"]:
            lines = bank["bridge"][:4]
        else:
            lines = []
        sections.append(L.LyricSection(s.tag, lines))
        bars.append(s.bars)
    concept = f"Thema: {theme}" if theme else f"Thema: {rng.choice(g.themes)}"
    return Candidate(g.key, title, L.render(sections), bpm, rng.choice(g.keys or ["A minor"]),
                     concept=concept, bars=bars, backend="template")


def generate_template(g: GenreProfile, n: int, theme: str | None, seed: int | None) -> list[Candidate]:
    rng = random.Random(seed)
    return [_finalize(_template_candidate(g, rng, theme), g) for _ in range(n)]


# ---------------------------------------------------------------- Claude-Backend

SONG_SCHEMA = {
    "type": "object",
    "properties": {
        "songs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "concept": {"type": "string"},
                    "bpm": {"type": "integer"},
                    "key": {"type": "string"},
                    "style_extra": {"type": "array", "items": {"type": "string"}},
                    "sections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "tag": {"type": "string"},
                                "lines": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["tag", "lines"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["title", "concept", "bpm", "key", "style_extra", "sections"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["songs"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """Du bist Songwriter und A&R für Streaming-Hits. Du schreibst Original-Lyrics für \
Suno AI. Ziel: Songs, die die messbaren Muster viraler Tracks erfüllen, ohne fremde Songs zu \
kopieren.

Harte Regeln:
- Keine Zeilen, Hooks oder Melodiezitate aus existierenden Songs, keine Namen realer Künstler.
- Keine realen Personen beleidigen, keine Marken diffamieren.
- Folge exakt der vorgegebenen Sektionsreihenfolge (Tags), damit Timing und Taktlängen stimmen.
- Lyrics in der angegebenen Sprache, natürlich und muttersprachlich klingend.
- Ad-libs in runden Klammern, keine Regieanweisungen in den Lyric-Zeilen.
- style_extra: 2–5 kurze englische Suno-Style-Tags (Instrumente/Stimmung), keine Künstlernamen.

Viral-Kriterien, die bewertet werden:
- Hook/Refrain vor der Hook-Deadline; Titel steckt in der ersten Hook-Zeile und kommt ≥4x vor.
- Hook-Zeilen: 6–10 Silben, gleich lang, exakt wiederholbar, eine Zeile als 10–30 s TikTok-Sound.
- Endreime (AABB/ABAB), direkte Ansprache des Hörers, konkrete Bilder statt Floskeln.
- Kontrast: ruhigere Strophe → Pre-Chorus baut Spannung → Refrain löst auf.
- Jeder Kandidat mit einem anderen Konzept und Titel."""


def _claude_prompt(g: GenreProfile, n: int, theme: str | None) -> str:
    timeline = g.section_seconds()
    struct = "\n".join(
        f"  [{s.tag}] {s.bars} Takte ({a:.0f}–{b:.0f}s){' ← HOOK' if s.is_hook else ''}"
        for s, a, b in timeline
    )
    return f"""Schreibe {n} unterschiedliche Song-Kandidaten.

Genre: {g.name} – {g.description}
Sprache: {g.language}
Tempo: {g.bpm_min}–{g.bpm_max} BPM (Sweet-Spot {g.bpm_opt}); typische Tonarten: {', '.join(g.keys)}
Länge: {g.duration_min_s}–{g.duration_max_s}s; Hook-Deadline: {g.hook_deadline_s:.0f}s
Gesang: {g.vocal}
Stimmungen: {', '.join(g.moods)}
Themenpool: {', '.join(g.themes)}
{'Vorgegebenes Thema: ' + theme if theme else ''}
Textregeln: {'; '.join(g.lyric_rules)}

Struktur (genau diese Tags in dieser Reihenfolge; ca. 1 Lyric-Zeile pro 2 Takte, Instrumental-Teile ohne Zeilen):
{struct}
"""


def generate_claude(g: GenreProfile, n: int, theme: str | None) -> list[Candidate]:
    import anthropic  # optional dependency

    client = anthropic.Anthropic()
    with client.beta.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=64000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _claude_prompt(g, n, theme)}],
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": SONG_SCHEMA}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    ) as stream:
        msg = stream.get_final_message()

    if msg.stop_reason == "refusal":
        raise RuntimeError("Claude hat die Anfrage abgelehnt – Thema anpassen.")
    if msg.stop_reason == "max_tokens":
        raise RuntimeError("Antwort abgeschnitten (max_tokens) – weniger Kandidaten anfordern.")
    text = next(b.text for b in msg.content if b.type == "text")
    return _from_json(g, json.loads(text), "claude")


def _from_json(g: GenreProfile, data: dict, backend: str) -> list[Candidate]:
    struct_tags = [s.tag.lower() for s in g.structure]
    out = []
    for s in data["songs"]:
        secs = [L.LyricSection(x["tag"], [l for l in x["lines"] if l.strip()]) for x in s["sections"]]
        bars = [sec.bars for sec in g.structure] if [x.tag.lower() for x in secs] == struct_tags else []
        c = Candidate(g.key, s["title"], L.render(secs), float(s.get("bpm") or g.bpm_opt),
                      s.get("key") or (g.keys[0] if g.keys else ""), concept=s.get("concept", ""),
                      style_extra=s.get("style_extra", []), bars=bars, backend=backend)
        out.append(_finalize(c, g))
    return sorted(out, key=lambda c: c.report.total, reverse=True)


# ---------------------------------------------------------------- Manuell über claude.ai (kostenlos)

MANUAL_FORMAT = """
Antworte AUSSCHLIESSLICH mit einem JSON-Codeblock in genau diesem Format (keine Erklärungen davor/danach):
```json
{"songs": [
  {"title": "...", "concept": "1 Satz Idee", "bpm": 96, "key": "D minor",
   "style_extra": ["tag1", "tag2"],
   "sections": [{"tag": "Intro", "lines": []}, {"tag": "Verse 1", "lines": ["Zeile", "Zeile"]}]}
]}
```"""


def manual_prompt(genre_key: str, n: int = 3, theme: str | None = None) -> str:
    """Kompletter Prompt zum Einfügen in den claude.ai-Chat (ohne API-Kosten)."""
    g = get_genre(genre_key)
    return f"{SYSTEM_PROMPT}\n\n{_claude_prompt(g, n, theme)}\n{MANUAL_FORMAT}\n"


def import_answer(genre_key: str, text: str) -> list[Candidate]:
    """Antwort aus dem Chat einlesen (JSON, auch mit Codeblock/Text drumherum)."""
    g = get_genre(genre_key)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Kein JSON in der Antwort gefunden – bitte die komplette Antwort von Claude kopieren.")
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON unvollständig oder fehlerhaft ({e.msg}). Claude bitten: 'Bitte nur das JSON nochmal komplett'.") from None
    if isinstance(data, dict) and "songs" not in data and "sections" in data:
        data = {"songs": [data]}
    return _from_json(g, data, "claude.ai")


def claude_available() -> bool:
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def generate(genre_key: str, n: int = 5, theme: str | None = None, backend: str = "auto",
             seed: int | None = None) -> list[Candidate]:
    g = get_genre(genre_key)
    if backend == "auto":
        backend = "claude" if claude_available() else "template"
    if backend == "claude":
        cands = generate_claude(g, n, theme)
    elif backend == "template":
        cands = generate_template(g, n, theme, seed)
    else:
        raise ValueError(f"Unbekanntes Backend '{backend}'")
    return sorted(cands, key=lambda c: c.report.total if c.report else 0, reverse=True)
