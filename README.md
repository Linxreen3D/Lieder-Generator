# Lieder-Generator (`liedgen`)

Tool, um Songs für **Suno AI** zu erzeugen, die sich an den messbaren Mustern viraler Hits
orientieren – und um mehrere **Artist-Profile** (ein Spotify-Artist pro Nische) mit Release-Pipeline,
Streams und geschätztem Umsatz zu verwalten.

```
Trends (Chart-CSV) ──► Genre-Profile ──► Generator (Claude / offline) ──► Viral-Score ──► Suno-Prompt
                          ▲  kalibrieren                          Generate & Select       │
                          └───────────────────────────────────────────────────────────────┤
                                     Portfolio (Artists, Songs, Status, Streams) ◄────────┘
```

## Schnellstart

```bash
pip install -e .               # keine Pflicht-Abhängigkeiten
pip install -e ".[ai]"         # optional: Claude für echte Lyrics
export ANTHROPIC_API_KEY=...   # optional

liedgen genres -v                                   # Nischen ansehen
liedgen generate balkan_ballade -n 5 --out out/     # 5 Kandidaten, bester zuerst, Export als .md/.json
liedgen serve                                       # Web-Dashboard auf http://127.0.0.1:8765
```

Ohne Installation geht auch `python -m liedgen …`.

## Windows: Installation per Doppelklick

1. **Python installieren** (einmalig): <https://www.python.org/downloads/> – beim Setup
   **„Add python.exe to PATH“ anhaken**. Alternativ in PowerShell: `winget install Python.Python.3.12`
2. **Projekt herunterladen**: auf GitHub den Branch wählen → *Code* → *Download ZIP* → entpacken
   (z.B. nach `C:\Musik\Lieder-Generator`). Oder mit Git: `git clone` + `git checkout <branch>`.
3. **`install.bat`** doppelklicken – legt `.venv` an, installiert alles und erzeugt die Datei `.env`.
4. Optional: **`.env`** mit dem Editor öffnen und `ANTHROPIC_API_KEY=` eintragen (für Claude-Lyrics).
   Dort steht auch `LIEDGEN_FOCUS` – welche Nischen im Tool erscheinen.
5. **`start.bat`** doppelklicken – der Browser öffnet das Dashboard (<http://127.0.0.1:8765>).
   Das schwarze Fenster offen lassen, solange du arbeitest.

Deine Daten liegen in `liedgen.db` im Projektordner (regelmäßig sichern).
Meldet Windows beim ersten Start „Der Computer wurde durch Windows geschützt“: *Weitere Informationen → Trotzdem ausführen*.

## Kostenlos: Lyrics über den Claude-Chat (ohne API-Guthaben)

Im Generator als Backend **„Claude-Chat (kostenlos)“** wählen → *Generieren* zeigt einen Prompt.
Den in einem neuen Chat auf <https://claude.ai> einfügen, die komplette Antwort zurückkopieren und
*Auswerten* klicken – Bewertung und Suno-Export wie beim API-Modus. Per CLI:
`liedgen prompt balkan_ballade -n 3 --out prompt.txt` und `liedgen import balkan_ballade antwort.txt --save 1`.
Tipp: max. 3 Kandidaten pro Chat, sonst wird die Antwort zu lang.

## Enthaltene Nischen

| Key | Nische | Sprache | Sweet-Spot | Warum |
|---|---|---|---|---|
| `nordic_folk_pop` | Nordic Folk-Pop | en | 96 BPM | global, TikTok-Natur-Visuals, Gaming/Focus-Playlists |
| `balkan_ballade` | Balkan Ballade | BKS | 76 BPM | treue Diaspora-Hörer, wenig KI-Konkurrenz |
| `deutschrap_street` | Deutschrap Street/Trap | de | 144 BPM | größter DE-Markt, Hook = TikTok-Sound |
| `deutschrap_melodic` | Deutschrap Melodic | de | 100 BPM | breitestes DACH-Publikum |
| `phonk` | Brazilian/Drift Phonk | (pt) | 130 BPM | Gym/Car-Edits, fast instrumental |
| `afro_house` | Afro House / Amapiano | en | 120 BPM | wachsend, Club + Beach |
| `schlager_party` | Party-Schlager | de | 128 BPM | saisonal (Malle, Après-Ski) |
| `lofi_chill` | Lo-Fi Instrumental | – | 82 BPM | passive Hintergrund-Streams |

Neue Nischen: in `liedgen/genres.py` ein `GenreProfile` registrieren (+ optional Textbausteine in `templates.py`).

## Workflow

1. **Artist-Profile anlegen** – ein Artist pro Nische (eigene Identität, eigene Playlists):
   `liedgen artist add --name "Nordvind" --genre nordic_folk_pop --distributor DistroKid`
2. **Generieren & auswählen** – `liedgen generate nordic_folk_pop -n 6 --save 2 --artist Nordvind`
   erzeugt 6 Kandidaten, bewertet sie und speichert die besten 2.
3. **In Suno** (Custom Mode) *Style of Music*, *Exclude Styles*, *Title* und *Lyrics* einfügen,
   2–4 Takes generieren, besten wählen. Status setzen: `liedgen song status 1 --status ausgewählt`.
4. **Mastern / Distribuieren** (DistroKid, Amuse, RouteNote …) → `--status eingereicht` → `--status live`.
5. **Streams erfassen** (aus Spotify for Artists): `liedgen stats add --song-id 1 --day 2026-11-18 --streams 420`
   oder im Web-UI unter *Songs*. Dashboard: `liedgen stats dashboard`.
6. **Trends nachziehen**: `liedgen trends analyze charts.csv`, dann `liedgen trends calibrate charts.csv`
   – passt BPM-/Längen-Sweet-Spots der Profile an echte Daten an (`liedgen_calibration.json`).

### Chart-CSV-Format

```
date,title,artist,genre,streams,bpm,duration_s
2026-11-01,Some Song,Some Artist,nordic_folk_pop,12345,98,162
```
`genre` muss ein Profil-Key sein. `bpm`/`duration_s` optional (die Spotify-Web-API liefert für neue Apps
keine Audio-Features mehr – BPM z.B. aus Tunebat/SongBPM oder manuell). Zum Ausprobieren:
`liedgen trends demo demo.csv` erzeugt **synthetische** Daten.

### Eigene Lyrics bewerten

```bash
liedgen score mein_song.txt --genre deutschrap_melodic --title "3 Uhr Nachts" --bpm 98
```

## Der Viral-Score

Details und Begründungen: [`docs/STRATEGIE.md`](docs/STRATEGIE.md). Kurz: 10 Merkmale (Hook-Timing,
Hook-Wiederholung, Intro-Länge, Songlänge, Tempo, Clipbarkeit, Wiederholungsgrad via Kompressionsrate,
Singbarkeit, Reimdichte, direkte Ansprache) → je 0–1 → gewichtetes **geometrisches** Mittel × 100.

> Der Score misst, ob ein Song die *formalen* Muster erfüllt – er ist eine Checkliste mit Mathematik,
> keine Hit-Garantie. Melodie, Stimme und Produktion (das, was Suno erzeugt) bewertet er nicht.
> Deshalb erreichen auch einfache Offline-Entwürfe hohe Werte; über Qualität entscheiden Ohr und Daten.

## Projektstruktur

```
liedgen/
  genres.py     Genre-Profile (BPM, Struktur in Takten, Suno-Tags, Themen, Regeln)
  viral.py      Viral-Score (Timeline aus Takten × BPM, 10 Merkmale)
  lyrics.py     Parser für Suno-Format, Silben, Reime, Kompressionsrate
  generator.py  Kandidaten erzeugen (Claude oder Templates) + Generate & Select
  suno.py       Suno-Export (Style ≤ 1000 Zeichen, Exclude, Lyrics)
  trends.py     Chart-CSV: Wachstumsraten (log-lineare Regression), Kalibrierung
  portfolio.py  SQLite: Artists, Songs, Status-Pipeline, Streams, Umsatzschätzung
  server.py     Web-Dashboard (nur Standardbibliothek)
  cli.py        Kommandozeile
tests/          pytest
```

Tests: `pip install -e ".[dev]" && pytest`
