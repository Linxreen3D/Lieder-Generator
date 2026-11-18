"""Genre-Profile: was in einer Nische gerade funktioniert.

Jedes Profil beschreibt Zielwerte (BPM, Länge, Hook-Zeitpunkt), die Song-Struktur
in Takten, Klangbild, Vokal-Stil, Themen und fertige Suno-Style-Tags.

Die Werte sind Startwerte aus Beobachtungen typischer Chart-Songs der Nische.
Mit `liedgen trends calibrate` lassen sich BPM/Länge aus echten Chartdaten
nachkalibrieren (siehe trends.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class Section:
    tag: str          # Suno-Metatag, z.B. "Chorus", "Verse 1", "Drop"
    bars: int         # Länge in Takten (4/4)
    is_hook: bool = False


@dataclass
class GenreProfile:
    key: str
    name: str
    description: str
    language: str                    # Hauptsprache der Lyrics (ISO)
    bpm_min: int
    bpm_opt: int
    bpm_max: int
    duration_min_s: int
    duration_max_s: int
    hook_deadline_s: float           # spätester Hook-Einstieg
    structure: list[Section]
    style_tags: list[str]            # Suno "Style of Music"
    exclude_tags: list[str]          # Suno "Exclude styles"
    vocal: str
    moods: list[str]
    themes: list[str]
    lyric_rules: list[str]
    market_notes: str
    pronouns: list[str] = field(default_factory=list)  # direkte Ansprache ("du", "you", "ti")
    keys: list[str] = field(default_factory=list)       # typische Tonarten
    chant: bool = False   # Text nur aus kurzen Shouts/Chants → Lyrik-Metriken entfallen

    def to_dict(self) -> dict:
        return asdict(self)

    def section_seconds(self, bpm: float | None = None) -> list[tuple[Section, float, float]]:
        """Start/Ende jeder Sektion in Sekunden (4/4-Takt)."""
        bpm = bpm or self.bpm_opt
        sec_per_bar = 4 * 60.0 / bpm
        out, t = [], 0.0
        for s in self.structure:
            d = s.bars * sec_per_bar
            out.append((s, t, t + d))
            t += d
        return out


S = Section

GENRES: dict[str, GenreProfile] = {}


def _reg(p: GenreProfile) -> None:
    GENRES[p.key] = p


_reg(GenreProfile(
    key="nordic_folk_pop",
    name="Nordic Folk-Pop",
    description="Ätherischer, skandinavisch geprägter Folk-Pop: weite Hallräume, Kehlgesang-Chöre, "
                "Trommeln, melancholische Moll-Melodik. Läuft stark auf TikTok/Reels mit Natur-Visuals.",
    language="en",
    bpm_min=80, bpm_opt=96, bpm_max=118,
    duration_min_s=140, duration_max_s=200,
    hook_deadline_s=20,
    structure=[S("Intro", 2), S("Verse 1", 4), S("Chorus", 8, True),
               S("Verse 2", 8), S("Pre-Chorus", 4), S("Chorus", 8, True), S("Post-Chorus", 4, True),
               S("Bridge", 8), S("Final Chorus", 8, True), S("Outro", 4)],
    style_tags=["nordic folk pop", "ethereal female vocals", "tribal drums", "deep male choir chants",
                "nyckelharpa", "atmospheric reverb", "minor key", "cinematic build", "viking ambience"],
    exclude_tags=["trap hi-hats", "autotune", "edm drop", "country"],
    vocal="Klare, hauchige Frauenstimme, Chor-Shouts im Refrain (\"Hey!\", \"Oh-oh\")",
    moods=["sehnsüchtig", "mystisch", "kraftvoll", "naturverbunden"],
    themes=["Heimkehr übers Meer", "Nordlicht", "alte Götter / Ahnen", "Winter & Feuer", "Wolf / Rabe als Symbol"],
    lyric_rules=["Bildsprache aus Natur (Meer, Eis, Feuer, Wald)", "Refrain mit Vokal-Hook (\"oh-oh-oh\")",
                 "Kurze, mantraartige Zeilen", "Optional ein Wort Altnordisch/Schwedisch als Hook"],
    market_notes="Globale Nische, starke Playlist-Nachfrage (Focus/Fantasy/Gaming). Instrumental-Versionen "
                 "zusätzlich hochladen – Gaming/Study-Playlists.",
    pronouns=["you", "we"],
    keys=["D minor", "E minor", "A minor"],
))

_reg(GenreProfile(
    key="balkan_ballade",
    name="Balkan Ballade",
    description="Emotionale Balkan-Ballade (Pop-Folk/Sevdah-Einflüsse): Klavier, Streicher, Akkordeon, "
                "Melismen, Liebeskummer. Sehr hohe Streaming-Treue in der Diaspora (DACH!).",
    language="bs",
    bpm_min=64, bpm_opt=76, bpm_max=92,
    duration_min_s=170, duration_max_s=230,
    hook_deadline_s=35,
    structure=[S("Intro", 2), S("Verse 1", 8), S("Chorus", 8, True),
               S("Verse 2", 8), S("Pre-Chorus", 4), S("Chorus", 8, True),
               S("Instrumental Break", 4), S("Final Chorus", 8, True), S("Outro", 6)],
    style_tags=["balkan ballad", "emotional male vocals", "melismatic", "piano", "string section",
                "accordion", "darbuka", "minor key", "sevdah influence", "dramatic"],
    exclude_tags=["rap", "edm", "happy", "country"],
    vocal="Kraftvolle, emotionale Männer- oder Frauenstimme mit Melismen, Höhepunkt im letzten Refrain",
    moods=["herzzerreißend", "stolz", "nostalgisch", "dramatisch"],
    themes=["verlorene Liebe", "Heimweh / Gastarbeiter", "Mutter", "Verrat", "eine Nacht in der Kafana"],
    lyric_rules=["Sprache: Bosnisch/Kroatisch/Serbisch (BKS), einfache Alltagssprache",
                 "Direkte Ansprache mit \"ti\" / \"ljubavi\"", "Refrain-Titel 2x wiederholen",
                 "Starker Kontrast: ruhige Strophe → laute Refrain-Melodie"],
    market_notes="Treue Hörer, gute Streams pro Hörer, wenig englische Konkurrenz durch KI-Massenware. "
                 "Wichtig: muttersprachlich korrekte Texte (von Native Speaker gegenlesen lassen).",
    pronouns=["ti", "tebe", "tebi", "moja", "moj"],
    keys=["A minor", "D minor", "E minor"],
))

_reg(GenreProfile(
    key="deutschrap_street",
    name="Deutschrap (Street/Trap)",
    description="Harter Deutschrap auf Trap-Beat: 808, dunkle Melodien, Ad-libs. Hook muss in den ersten "
                "Sekunden zitierbar sein – die Hook-Zeile ist der TikTok-Sound.",
    language="de",
    bpm_min=130, bpm_opt=144, bpm_max=160,
    duration_min_s=120, duration_max_s=170,
    hook_deadline_s=12,
    # Takte im notierten Tempo (144 BPM) – entspricht 12/8 Rap-Bars im Half-Time-Feel
    structure=[S("Intro", 2), S("Hook", 16, True), S("Verse 1", 24), S("Hook", 16, True),
               S("Verse 2", 16), S("Hook", 16, True), S("Outro", 2)],
    style_tags=["german rap", "trap", "hard 808", "dark piano melody", "aggressive male rap vocals",
                "ad-libs", "half-time drums", "street"],
    exclude_tags=["singing chorus", "acoustic guitar", "pop punk", "rock"],
    vocal="Selbstbewusster, rhythmischer Rap, Hook halb-gesungen mit Autotune",
    moods=["kalt", "hungrig", "stolz", "nachts"],
    themes=["vom Block nach oben", "Loyalität / Brüder", "Geld & Hunger", "Verrat", "Nachtfahrt durch die Stadt"],
    lyric_rules=["Mehrsilbige Reime (Doppelreime)", "Hook = 1 zitierbare Zeile, 4x", "Ad-libs in Klammern",
                 "Keine realen Personen/Marken diffamieren"],
    market_notes="Größter deutscher Streaming-Markt, aber hohe Konkurrenz. Erfolg kommt fast nur über "
                 "Short-Form-Content (Hook-Snippet vorab testen).",
    pronouns=["du", "dich", "dir", "ich", "wir"],
    keys=["C# minor", "F minor", "G minor"],
))

_reg(GenreProfile(
    key="deutschrap_melodic",
    name="Deutschrap Melodic / Pop-Rap",
    description="Melodischer Deutschrap mit gesungener Hook, Gitarren-Loop oder Afro-Elementen. "
                "Radio- und Playlist-tauglich, Sommer-/Nachtgefühl.",
    language="de",
    bpm_min=90, bpm_opt=100, bpm_max=128,
    duration_min_s=130, duration_max_s=175,
    hook_deadline_s=15,
    structure=[S("Intro", 2), S("Hook", 8, True), S("Verse 1", 12), S("Pre-Hook", 4),
               S("Hook", 8, True), S("Verse 2", 8), S("Pre-Hook", 4), S("Hook", 8, True), S("Outro", 2)],
    style_tags=["german melodic rap", "pop rap", "guitar loop", "afro swing groove", "autotune vocals",
                "catchy sung hook", "warm bass", "summer night"],
    exclude_tags=["metal", "screamo", "orchestral"],
    vocal="Gesungene Autotune-Hook, Strophen halb gerappt/halb gesungen",
    moods=["melancholisch", "verliebt", "sommerlich", "nostalgisch"],
    themes=["Sommernacht mit ihr/ihm", "Kindheitsfreunde", "Ex vermissen", "raus aus der Stadt", "3 Uhr nachts"],
    lyric_rules=["Hook singbar, max. 8 Silben pro Zeile", "Titel = erste Hook-Zeile",
                 "Konkrete Alltagsbilder (Späti, Balkon, S-Bahn)", "Direkte Ansprache \"du\""],
    market_notes="Breitestes Publikum im DACH-Raum, gute Chancen auf User-Playlists. Speed-up-Version "
                 "als separate Single ist Standard.",
    pronouns=["du", "dich", "dir", "wir"],
    keys=["A minor", "C major", "F# minor"],
))

_reg(GenreProfile(
    key="phonk",
    name="Phonk / Brazilian Phonk",
    description="Drift-/Brazilian-Phonk: Cowbell-Melodien, verzerrte 808, Funk-Vocal-Chops. Riesig in "
                "Gym/Car-Edits. Fast instrumental – Sprache egal, globale Reichweite.",
    language="pt",
    bpm_min=120, bpm_opt=130, bpm_max=160,
    duration_min_s=100, duration_max_s=150,
    hook_deadline_s=8,
    structure=[S("Intro", 2), S("Drop", 16, True), S("Break", 12), S("Build", 4),
               S("Drop", 16, True), S("Outro", 8)],
    style_tags=["brazilian phonk", "drift phonk", "cowbell melody", "distorted 808", "funk carioca vocal chops",
                "aggressive", "gym", "high energy", "sidechain"],
    exclude_tags=["acoustic", "ballad", "soft vocals", "orchestral"],
    vocal="Kurze, gechoppte Vocal-Samples / Shouts, kaum Text",
    moods=["aggressiv", "düster", "energetisch"],
    themes=["Nachtfahrt / Drift", "Gym-Motivation", "Dunkle Straßen"],
    lyric_rules=["Max. 2–4 kurze Vocal-Phrasen, oft wiederholt", "Drop spätestens nach 8 Sekunden",
                 "Lautmalerei / Shouts statt Strophen"],
    market_notes="Hohe Stückzahl möglich (kurze Tracks), Content-Creator nutzen Phonk massenhaft. "
                 "Achtung: Spotify filtert Spam – lieber weniger, aber unterscheidbare Tracks.",
    pronouns=[],
    keys=["F minor", "G# minor"],
    chant=True,
))

_reg(GenreProfile(
    key="afro_house",
    name="Afro House / Amapiano Pop",
    description="Afro House mit Log-Drum/Amapiano-Elementen und Vocal-Hook. Clubs + Beach-Playlists, "
                "funktioniert international und im DACH-Club-Bereich.",
    language="en",
    bpm_min=112, bpm_opt=120, bpm_max=126,
    duration_min_s=150, duration_max_s=210,
    hook_deadline_s=20,
    structure=[S("Intro", 2), S("Chorus", 8, True), S("Verse 1", 8), S("Chorus", 8, True), S("Drop", 16, True),
               S("Verse 2", 8), S("Chorus", 8, True), S("Drop", 16, True), S("Outro", 4)],
    style_tags=["afro house", "amapiano log drums", "deep house groove", "soulful vocals",
                "shakers", "warm pads", "hypnotic", "sunset"],
    exclude_tags=["trap", "rock", "metal", "dubstep"],
    vocal="Soulige Vocals, Call & Response, Chant-Hook",
    moods=["euphorisch", "warm", "hypnotisch", "tanzbar"],
    themes=["Sonnenuntergang am Meer", "Freiheit", "Tanzen bis zum Morgen", "Gemeinschaft"],
    lyric_rules=["Wenig Text, starke Wiederholung", "Chant-Hook (Call & Response)", "Einfache englische Wörter"],
    market_notes="Wachsendes Genre, DJs suchen Material. Extended Mix als Zusatz-Release.",
    pronouns=["you", "we"],
    keys=["A minor", "F minor", "C minor"],
))

_reg(GenreProfile(
    key="schlager_party",
    name="Schlager-Party / Ballermann",
    description="Party-Schlager mit Four-to-the-floor, Mitgröl-Refrain und Fox-/Techno-Elementen. "
                "Saisonales Geschäft (Mallorca, Après-Ski, Karneval).",
    language="de",
    bpm_min=120, bpm_opt=128, bpm_max=140,
    duration_min_s=130, duration_max_s=180,
    hook_deadline_s=15,
    structure=[S("Intro", 2), S("Chorus", 8, True), S("Verse 1", 8), S("Pre-Chorus", 4),
               S("Chorus", 8, True), S("Verse 2", 8), S("Pre-Chorus", 4), S("Chorus", 8, True),
               S("Drop", 8, True), S("Chorus", 8, True), S("Outro", 4)],
    style_tags=["german schlager", "party anthem", "four on the floor", "festival techno synths",
                "crowd shouts", "sing-along chorus", "brass stabs", "euphoric"],
    exclude_tags=["sad", "ballad", "trap", "metal"],
    vocal="Kräftige Party-Stimme, Gruppen-Shouts, Mitsing-Refrain",
    moods=["ausgelassen", "albern", "euphorisch"],
    themes=["Malle / Urlaub", "Après-Ski", "Feiern bis zum Morgen", "Absurde Alltags-Story"],
    lyric_rules=["Refrain in 3 Sekunden verstehbar", "Mitgröl-Zeile + Klatsch-Stelle",
                 "Wortwitz / Doppeldeutigkeit (jugendfrei halten)", "Titel 4x im Refrain"],
    market_notes="Sehr saisonal: Releases Feb–Apr (Malle) und Okt–Dez (Après-Ski) planen.",
    pronouns=["du", "wir", "ihr"],
    keys=["G major", "A major", "D major"],
))

_reg(GenreProfile(
    key="lofi_chill",
    name="Lo-Fi / Chill Instrumental",
    description="Lo-Fi-Hip-Hop/Chillhop-Instrumentals für Study/Sleep/Focus-Playlists. Kein Viral-Genre, "
                "aber stabile, passive Streams (Hintergrundhören).",
    language="instrumental",
    bpm_min=70, bpm_opt=82, bpm_max=92,
    duration_min_s=120, duration_max_s=180,
    hook_deadline_s=10,
    structure=[S("Intro", 2), S("Theme A", 16, True), S("Theme B", 16), S("Theme A", 16, True), S("Outro", 4)],
    style_tags=["lofi hip hop", "chillhop", "dusty vinyl crackle", "mellow rhodes", "jazzy chords",
                "soft boom bap drums", "warm tape saturation", "instrumental"],
    exclude_tags=["vocals", "singing", "rap", "edm", "distortion"],
    vocal="Instrumental (in Suno 'Instrumental' aktivieren)",
    moods=["entspannt", "verträumt", "gemütlich"],
    themes=["Regen am Fenster", "Spätschicht", "Tokio bei Nacht", "Sonntagmorgen"],
    lyric_rules=["Instrumental – nur Metatags für Struktur verwenden"],
    market_notes="Einnahmen über Masse an Streams pro Track; benötigt Playlist-Pitching. Spotify "
                 "reduziert Auszahlung für sehr kurze 'Noise'-Tracks – Tracks > 2 Minuten halten.",
    pronouns=[],
    keys=["F major", "D minor", "Bb major"],
))


def get(key: str) -> GenreProfile:
    try:
        return GENRES[key]
    except KeyError:
        raise KeyError(f"Unbekanntes Genre '{key}'. Verfügbar: {', '.join(GENRES)}") from None
