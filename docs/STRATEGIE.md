# Strategie: Was Songs viral macht – und wie man damit (realistisch) Geld verdient

## 1. Die Mathematik hinter dem Viral-Score

Jedes Merkmal wird auf einen Wert zwischen 0 und 1 abgebildet. Der Gesamtscore ist das gewichtete
geometrische Mittel:

```
Score = 100 · exp( Σ wᵢ · ln(max(0.05, sᵢ)) / Σ wᵢ )
```

Warum geometrisch? Beim arithmetischen Mittel könnte ein perfekter Refrain einen Song retten, dessen Hook
erst nach einer Minute kommt. Das geometrische Mittel bestraft das schwächste Glied – genau wie echte
Hörer, die nach 8 Sekunden skippen.

| Merkmal | Gewicht | Formel | Begründung |
|---|---|---|---|
| Hook-Timing | 0.20 | 1 bis zur Deadline, danach `e^(−(t−d)/12)` | Spotify zählt einen Stream erst ab 30 s; frühe Skips zerstören zudem das Algorithmus-Signal |
| Hook-Wiederholung | 0.15 | Anzahl Hook-Teile / Ziel × Titel-Häufigkeit (Ziel ≥ 4) | Wiederholung erzeugt Ohrwürmer; der Titel ist das, wonach Leute suchen (Shazam, Spotify-Suche) |
| Länge | 0.10 | 1 im Genre-Bereich, sonst Gauß-Abfall (σ = 20 s) | Kürzere Songs → mehr Wiederholungen pro Hörer → mehr Streams |
| Tempo | 0.10 | Gauß um Sweet-Spot (Half-/Double-Time zählt mit) | Jede Nische hat ein Tempo, auf das Hörer und Playlists konditioniert sind |
| Wiederholungsgrad | 0.10 | zlib-Kompressionsrate der Lyrics, Ziel 0,25–0,40 | Informationstheorie: Hits sind vorhersagbarer (stärker komprimierbar) als Durchschnittssongs, aber nicht monoton |
| Singbarkeit | 0.10 | Gauß um 8 Silben/Zeile × Strafe für Variationskoeffizient > 20 % | Gleich lange, kurze Hook-Zeilen kann man nach einmal Hören mitsingen |
| Intro | 0.08 | ≤ 5 s bzw. 2 Takte, danach exponentieller Abfall | „Skip-Fenster“ in den ersten Sekunden |
| Reimdichte | 0.07 | Anteil reimender Zeilen (AABB/ABAB), Ziel ≥ 50 % | Reime erhöhen Vorhersagbarkeit und Merkbarkeit |
| Clipbarkeit | 0.05 | Hook-Teil 10–30 s (bis ~48 s ohne Abzug) | TikTok/Reels/Shorts brauchen einen in sich geschlossenen Ausschnitt |
| Direkte Ansprache | 0.05 | Anteil Zeilen mit du/you/ti …, Ziel 30 % | Identifikation; Lyrics funktionieren als Caption für Videos |

Die Timeline entsteht aus der Struktur: `Sekunden = Takte × 4 × 60 / BPM` (4/4-Takt).

### Trend-Mathematik
* **Momentum eines Tracks**: lineare Regression von `ln(Streams)` über die Tage → Steigung `b`,
  tägliches Wachstum `g = e^b − 1`. R² sagt, wie stabil der Trend ist (≥ 0,5 und g > 2 %/Tag ⇒ „steigend“).
* **Genre-Momentum**: Median der Track-Wachstumsraten (robust gegen einzelne Ausreißer).
* **Kalibrierung**: Sweet-Spot = Median-BPM, Bereich = 10.–90. Perzentil der aktuellen Chart-Tracks.

### Generate & Select
Statt eines Songs werden *n* Kandidaten erzeugt und nach Score sortiert. Danach entscheidet die
Realität: in Suno 2–4 Takes je Kandidat, Hook-Snippet als Short-Form-Video testen, nur die Gewinner
voll releasen. Die Stream-Daten im Portfolio zeigen, welche Nischen und Muster wirklich funktionieren –
damit lassen sich Profile und Gewichte iterativ anpassen.

## 2. Geld verdienen – Realitätscheck

**Einnahmen pro Stream** liegen grob bei 0,002–0,005 € (abhängig von Land, Abo-Anteil, Distributor).
Das Tool rechnet standardmäßig mit 0,003 € (`--payout` zum Anpassen). 100.000 Streams ≈ 300 €.

**Wichtige Regeln (Stand meines Wissens – vor dem Start aktuell prüfen):**

1. **Suno-Rechte**: Kommerzielle Nutzung nur mit Songs, die mit einem bezahlten Plan (Pro/Premier)
   erstellt wurden. Suno hat seine Bedingungen nach den Label-Einigungen 2025 geändert – aktuelle
   Nutzungsbedingungen lesen, bevor etwas veröffentlicht wird.
2. **Spotify-Mindestgrenze**: Tracks verdienen erst ab 1.000 Streams in 12 Monaten Geld
   (im Dashboard berücksichtigt). Viele kleine Tracks mit je 200 Streams = 0 €.
3. **Spotify-KI-Richtlinien**: Spotify geht gegen Massen-Uploads/Spam, Imitation realer Künstler und
   künstliche Streams vor und unterstützt KI-Kennzeichnung in den Credits (DDEX). Also:
   * keine Stimmen oder Namen realer Künstler imitieren,
   * keine Fast-Duplikate oder 30-Sekunden-Füller hochladen,
   * **niemals** Streams kaufen oder Bots nutzen – führt zu Sperrung und Einbehalt der Einnahmen.
4. **Distributoren** haben eigene KI-Regeln und teils Upload-Limits; KI-Anteil wahrheitsgemäß angeben.
5. **Content ID / YouTube**: Bei Suno-Songs vorsichtig mit Content-ID-Registrierung – ähnliche
   KI-Outputs anderer Nutzer können zu Konflikten führen.

**Was tatsächlich zu Einnahmen führt:**
* **Qualität vor Masse**: 1 starker Song/Woche pro Artist schlägt 30 mittelmäßige.
* **Short-Form zuerst**: Hook-Snippets als TikTok/Reels testen *bevor* der Song erscheint;
  nur releasen, was Reaktionen bekommt.
* **Konsistente Artist-Identität** je Nische (Name, Cover-Stil, Bio, Release-Rhythmus alle 2–4 Wochen).
* **Playlists**: Spotify-Editorial-Pitch (spätestens 7 Tage vor Release über Spotify for Artists),
  User-Curator-Playlists der Nische.
* **Nachbearbeitung**: Suno-Output mastern/editieren (Intro kürzen, Lautheit ~ −14 LUFS),
  Lyrics bei Fremdsprachen (BKS!) von Muttersprachlern prüfen lassen.
* **Mehrfachverwertung**: Instrumental, Sped-up, Extended Mix als eigene Releases (sparsam,
  nicht als Spam).

## 3. Roadmap (Ideen für die nächsten Ausbaustufen)

1. **Spotify-for-Artists-CSV-Import** für automatische Stream-Erfassung je Artist.
2. **Audio-Analyse** der Suno-Takes (librosa: BPM, Energie-Kurve, Zeit bis zum ersten Lautheits-Peak)
   → Score auch auf das echte Audio anwenden und den besten Take automatisch wählen.
3. **A/B-Lernen**: Regression von echten Stream-Ergebnissen auf die Score-Merkmale → Gewichte je
   Nische aus eigenen Daten lernen.
4. **Release-Kalender** (Saisonalität: Schlager Feb–Apr / Okt–Dez, Freitags-Releases).
5. **Cover-Art-Prompts** pro Artist-Identität.
