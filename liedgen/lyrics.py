"""Lyrics-Werkzeuge: Parsen im Suno-Format, Silben, Reime, Wiederholung.

Suno-Format:
    [Verse 1]
    Zeile...
    [Chorus]
    Zeile...
"""

from __future__ import annotations

import re
import unicodedata
import zlib
from dataclasses import dataclass, field

TAG_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$")
ADLIB_RE = re.compile(r"\([^)]*\)")
VOWELS = "aeiouyäöüåæøéèêáàíìóòúùąęěůóa"
HOOK_WORDS = ("chorus", "hook", "refrain", "drop", "theme a")


@dataclass
class LyricSection:
    tag: str
    lines: list[str] = field(default_factory=list)

    @property
    def is_hook(self) -> bool:
        t = self.tag.lower()
        return any(w in t for w in HOOK_WORDS) and "pre" not in t


def parse(text: str) -> list[LyricSection]:
    sections: list[LyricSection] = []
    current: LyricSection | None = None
    for raw in text.splitlines():
        m = TAG_RE.match(raw)
        if m:
            current = LyricSection(m.group(1).strip())
            sections.append(current)
            continue
        line = raw.strip()
        if not line:
            continue
        if current is None:
            current = LyricSection("Verse")
            sections.append(current)
        current.lines.append(line)
    return sections


def render(sections: list[LyricSection]) -> str:
    out = []
    for s in sections:
        out.append(f"[{s.tag}]")
        out.extend(s.lines)
        out.append("")
    return "\n".join(out).strip() + "\n"


def _fold(s: str) -> str:
    """Kleinschreibung, Ad-libs raus, Satzzeichen raus."""
    s = ADLIB_RE.sub(" ", s.lower())
    return re.sub(r"[^\w\s'-]", " ", s)


def words(line: str) -> list[str]:
    return [w for w in _fold(line).split() if w]


def syllables(word: str) -> int:
    """Heuristische Silbenzählung über Vokalgruppen (de/en/BKS/skandinavisch tauglich)."""
    w = word.lower()
    groups = re.findall(rf"[{VOWELS}]+", w)
    n = len(groups)
    if w.endswith("e") and n > 1 and not w.endswith(("le", "ee")) and re.search(r"[a-z]", w) and w.isascii():
        # englisches stummes e ("love", "time") – im Deutschen nicht, daher nur bei kurzen ascii-Wörtern
        if len(w) <= 5:
            n -= 1
    # Diphthonge zählen als eine Gruppe – bereits durch Regex erfasst.
    # Silbisches r im BKS ("srce", "prst")
    if n == 0 and "r" in w:
        n = 1
    return max(1, n)


def line_syllables(line: str) -> int:
    return sum(syllables(w) for w in words(line))


def rhyme_key(line: str, n_vowel_groups: int = 1) -> str:
    """Endreim-Schlüssel: alles ab der n-letzten Vokalgruppe des letzten Wortes."""
    ws = words(line)
    if not ws:
        return ""
    w = unicodedata.normalize("NFC", ws[-1])
    spans = [m.start() for m in re.finditer(rf"[{VOWELS}]+", w)]
    if not spans:
        return w
    idx = spans[-n_vowel_groups] if len(spans) >= n_vowel_groups else spans[0]
    return w[idx:]


def rhymes(a: str, b: str) -> bool:
    ka, kb = rhyme_key(a), rhyme_key(b)
    if not ka or not kb:
        return False
    if ka == kb:
        return True
    # unreiner Reim: gleicher Vokalkern
    va = re.match(rf"[{VOWELS}]+", ka)
    vb = re.match(rf"[{VOWELS}]+", kb)
    return bool(va and vb and va.group() == vb.group() and ka[-1:] == kb[-1:])


def rhyme_density(lines: list[str]) -> float:
    """Anteil der Zeilen, die mit einer der 2 folgenden Zeilen reimen (AABB, ABAB)."""
    if len(lines) < 2:
        return 0.0
    hits = 0
    for i, line in enumerate(lines[:-1]):
        if any(rhymes(line, lines[j]) for j in range(i + 1, min(i + 3, len(lines)))):
            hits += 1
    return hits / (len(lines) - 1)


def compression_ratio(text: str) -> float:
    """Komprimiert/roh. Niedrig = viel Wiederholung. Typische Hits: ~0.30–0.50."""
    raw = _fold(text).encode("utf-8")
    if len(raw) < 20:
        return 1.0
    return len(zlib.compress(raw, 9)) / len(raw)


def title_occurrences(title: str, sections: list[LyricSection]) -> int:
    t = " ".join(words(title))
    if not t:
        return 0
    return sum(" ".join(words(l)).count(t) for s in sections for l in s.lines)
