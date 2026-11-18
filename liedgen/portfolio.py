"""Portfolio: mehrere Artist-Profile (je Nische ein Spotify-Artist) mit Songs,
Release-Pipeline und Stream-Statistiken in einer lokalen SQLite-Datenbank.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

STATUSES = ["idee", "generiert", "ausgewählt", "gemastert", "eingereicht", "live", "verworfen"]
DEFAULT_PAYOUT_EUR = 0.003      # grober Schnitt pro Stream, stark länder-/abo-abhängig
MIN_STREAMS_FOR_PAYOUT = 1000   # Spotify: Track braucht ≥1000 Streams in 12 Monaten

SCHEMA = """
CREATE TABLE IF NOT EXISTS artists (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    genre TEXT NOT NULL,
    spotify_url TEXT DEFAULT '',
    distributor TEXT DEFAULT '',
    persona TEXT DEFAULT '',
    created_at TEXT DEFAULT (date('now'))
);
CREATE TABLE IF NOT EXISTS songs (
    id INTEGER PRIMARY KEY,
    artist_id INTEGER REFERENCES artists(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    genre TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'generiert',
    viral_score REAL,
    bpm REAL,
    suno_json TEXT,
    lyrics TEXT,
    release_date TEXT,
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (date('now'))
);
CREATE TABLE IF NOT EXISTS stats (
    song_id INTEGER REFERENCES songs(id) ON DELETE CASCADE,
    day TEXT NOT NULL,
    streams INTEGER NOT NULL DEFAULT 0,
    listeners INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    PRIMARY KEY (song_id, day)
);
"""


class Portfolio:
    def __init__(self, path: str | Path = "liedgen.db"):
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)

    # ------------------------------------------------------------ Artists
    def add_artist(self, name: str, genre: str, spotify_url: str = "", distributor: str = "",
                   persona: str = "") -> int:
        cur = self.db.execute(
            "INSERT INTO artists(name, genre, spotify_url, distributor, persona) VALUES (?,?,?,?,?)",
            (name, genre, spotify_url, distributor, persona))
        self.db.commit()
        return cur.lastrowid

    def artists(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM artists ORDER BY genre, name")]

    def artist_id(self, name_or_id: str | int) -> int:
        row = self.db.execute("SELECT id FROM artists WHERE id = ? OR name = ?",
                              (name_or_id, str(name_or_id))).fetchone()
        if not row:
            raise KeyError(f"Artist '{name_or_id}' nicht gefunden")
        return row["id"]

    # ------------------------------------------------------------ Songs
    def add_song(self, title: str, genre: str, artist: str | int | None = None, status: str = "generiert",
                 viral_score: float | None = None, bpm: float | None = None, suno: dict | None = None,
                 lyrics: str = "", notes: str = "") -> int:
        aid = self.artist_id(artist) if artist not in (None, "") else None
        cur = self.db.execute(
            "INSERT INTO songs(artist_id, title, genre, status, viral_score, bpm, suno_json, lyrics, notes)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (aid, title, genre, status, viral_score, bpm, json.dumps(suno, ensure_ascii=False) if suno else None,
             lyrics, notes))
        self.db.commit()
        return cur.lastrowid

    def set_status(self, song_id: int, status: str, release_date: str | None = None) -> None:
        if status not in STATUSES:
            raise ValueError(f"Status muss einer von {STATUSES} sein")
        if status == "live" and not release_date:
            release_date = date.today().isoformat()
        self.db.execute("UPDATE songs SET status = ?, release_date = COALESCE(?, release_date) WHERE id = ?",
                        (status, release_date, song_id))
        self.db.commit()

    def assign(self, song_id: int, artist: str | int) -> None:
        self.db.execute("UPDATE songs SET artist_id = ? WHERE id = ?", (self.artist_id(artist), song_id))
        self.db.commit()

    def songs(self, artist: str | int | None = None) -> list[dict]:
        q = ("SELECT s.*, a.name AS artist, COALESCE(SUM(st.streams),0) AS streams FROM songs s "
             "LEFT JOIN artists a ON a.id = s.artist_id LEFT JOIN stats st ON st.song_id = s.id")
        args: tuple = ()
        if artist not in (None, ""):
            q += " WHERE s.artist_id = ?"
            args = (self.artist_id(artist),)
        q += " GROUP BY s.id ORDER BY s.created_at DESC, s.id DESC"
        return [dict(r) for r in self.db.execute(q, args)]

    def song(self, song_id: int) -> dict:
        r = self.db.execute("SELECT * FROM songs WHERE id = ?", (song_id,)).fetchone()
        if not r:
            raise KeyError(f"Song {song_id} nicht gefunden")
        return dict(r)

    # ------------------------------------------------------------ Stats
    def add_stats(self, song_id: int, day: str, streams: int, listeners: int = 0, saves: int = 0) -> None:
        self.db.execute(
            "INSERT INTO stats(song_id, day, streams, listeners, saves) VALUES (?,?,?,?,?) "
            "ON CONFLICT(song_id, day) DO UPDATE SET streams=excluded.streams, "
            "listeners=excluded.listeners, saves=excluded.saves",
            (song_id, day, streams, listeners, saves))
        self.db.commit()

    # ------------------------------------------------------------ Dashboard
    def dashboard(self, payout: float = DEFAULT_PAYOUT_EUR, today: date | None = None) -> dict:
        today = today or date.today()
        d7 = (today - timedelta(days=7)).isoformat()
        d14 = (today - timedelta(days=14)).isoformat()
        d365 = (today - timedelta(days=365)).isoformat()

        song_rows = self.db.execute(
            "SELECT s.id, s.artist_id, s.title, s.status, s.viral_score,"
            " COALESCE(SUM(st.streams),0) AS total,"
            " COALESCE(SUM(CASE WHEN st.day > ? THEN st.streams END),0) AS last7,"
            " COALESCE(SUM(CASE WHEN st.day > ? AND st.day <= ? THEN st.streams END),0) AS prev7,"
            " COALESCE(SUM(CASE WHEN st.day > ? THEN st.streams END),0) AS last365,"
            " COALESCE(SUM(st.saves),0) AS saves, COALESCE(SUM(st.listeners),0) AS listeners"
            " FROM songs s LEFT JOIN stats st ON st.song_id = s.id GROUP BY s.id",
            (d7, d14, d7, d365)).fetchall()

        artists = {a["id"]: {**a, "songs": 0, "live": 0, "streams": 0, "last7": 0, "prev7": 0,
                             "revenue_eur": 0.0, "top_song": None, "pipeline": {s: 0 for s in STATUSES}}
                   for a in self.artists()}
        unassigned = {"pipeline": {s: 0 for s in STATUSES}, "songs": 0}
        for r in song_rows:
            a = artists.get(r["artist_id"], unassigned)
            a["songs"] += 1
            a["pipeline"][r["status"]] += 1
            if r["artist_id"] not in artists:
                continue
            a["live"] += r["status"] == "live"
            a["streams"] += r["total"]
            a["last7"] += r["last7"]
            a["prev7"] += r["prev7"]
            # Spotify zahlt nur für Tracks mit ≥1000 Streams in den letzten 12 Monaten
            if r["last365"] >= MIN_STREAMS_FOR_PAYOUT:
                a["revenue_eur"] += r["total"] * payout
            if r["total"] and (a["top_song"] is None or r["total"] > a["top_song"]["streams"]):
                a["top_song"] = {"title": r["title"], "streams": r["total"]}
        for a in artists.values():
            a["growth_7d"] = (a["last7"] / a["prev7"] - 1) if a["prev7"] else None
            a["revenue_eur"] = round(a["revenue_eur"], 2)

        totals = {
            "artists": len(artists),
            "songs": len(song_rows),
            "live": sum(a["live"] for a in artists.values()),
            "streams": sum(a["streams"] for a in artists.values()),
            "last7": sum(a["last7"] for a in artists.values()),
            "revenue_eur": round(sum(a["revenue_eur"] for a in artists.values()), 2),
            "payout_per_stream": payout,
        }
        return {"totals": totals, "artists": list(artists.values()), "unassigned": unassigned}
