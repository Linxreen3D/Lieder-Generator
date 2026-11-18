"""Suno-Export: Style-Prompt, Exclude-Styles und Lyrics im Suno-Custom-Mode-Format.

Suno hat keine offizielle öffentliche API. Der Export ist daher für Copy & Paste in
den Custom Mode gedacht (Felder: Lyrics, Style of Music, Exclude Styles, Title).
Hinweis: Künstlernamen im Style-Prompt werden von Suno blockiert – die Profile
beschreiben Klang daher nur über Genre-/Instrument-/Stimmungs-Tags.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .genres import GenreProfile

STYLE_LIMIT = 1000   # Zeichenlimit Style-Feld (v4.5+/v5); ältere Modelle: 200
LYRICS_LIMIT = 5000


@dataclass
class SunoPrompt:
    title: str
    style: str
    exclude: str
    lyrics: str
    instrumental: bool

    def to_dict(self) -> dict:
        return {"title": self.title, "style": self.style, "exclude_styles": self.exclude,
                "lyrics": self.lyrics, "instrumental": self.instrumental}

    def to_markdown(self) -> str:
        return (
            f"## {self.title}\n\n"
            f"**Style of Music** ({len(self.style)} Zeichen)\n```\n{self.style}\n```\n\n"
            f"**Exclude Styles**\n```\n{self.exclude}\n```\n\n"
            f"**Instrumental:** {'ja' if self.instrumental else 'nein'}\n\n"
            f"**Lyrics**\n```\n{self.lyrics}```\n"
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def build_style(genre: GenreProfile, bpm: float, key: str | None = None,
                extra: list[str] | None = None, limit: int = STYLE_LIMIT) -> str:
    parts = list(genre.style_tags)
    parts.append(f"{round(bpm)} bpm")
    if key:
        parts.append(key)
    parts += extra or []
    # "radio-ready hook in first seconds" hilft Suno, früh in den Refrain zu gehen
    parts.append("catchy hook" if genre.language != "instrumental" else "memorable motif")
    seen, out = set(), []
    for p in parts:
        p = p.strip()
        if p and p.lower() not in seen:
            seen.add(p.lower())
            out.append(p)
    style = ", ".join(out)
    while len(style) > limit and out:
        out.pop(-2 if len(out) > 1 else -1)
        style = ", ".join(out)
    return style


def build_prompt(genre: GenreProfile, title: str, lyrics: str, bpm: float,
                 key: str | None = None, extra_style: list[str] | None = None,
                 legacy_200: bool = False) -> SunoPrompt:
    instrumental = genre.language == "instrumental"
    if len(lyrics) > LYRICS_LIMIT:
        raise ValueError(f"Lyrics zu lang für Suno ({len(lyrics)} > {LYRICS_LIMIT} Zeichen)")
    return SunoPrompt(
        title=title,
        style=build_style(genre, bpm, key, extra_style, 200 if legacy_200 else STYLE_LIMIT),
        exclude=", ".join(genre.exclude_tags),
        lyrics=lyrics,
        instrumental=instrumental,
    )
