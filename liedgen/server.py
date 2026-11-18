"""Lokale Web-Oberfläche (nur Standardbibliothek): Dashboard, Generator, Analyse."""

from __future__ import annotations

import json
import re
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources

from . import generator, trends
from .genres import GENRES, get as get_genre
from .portfolio import STATUSES, Portfolio
from .viral import score_song


def make_handler(pf: Portfolio, trends_csv: str | None, payout: float):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # ruhiger Log
            pass

        def _send(self, code: int, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", f"{ctype}; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _json(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}")

        def do_GET(self):
            try:
                if self.path in ("/", "/index.html"):
                    html = resources.files("liedgen.web").joinpath("index.html").read_bytes()
                    return self._send(200, html, "text/html")
                if self.path == "/api/genres":
                    return self._send(200, {"genres": [g.to_dict() for g in GENRES.values()],
                                            "statuses": STATUSES,
                                            "claude": generator.claude_available()})
                if self.path == "/api/dashboard":
                    return self._send(200, pf.dashboard(payout))
                if self.path == "/api/songs":
                    return self._send(200, pf.songs())
                if self.path == "/api/trends":
                    if not trends_csv:
                        return self._send(200, {"available": False})
                    rows = trends.load_csv(trends_csv)
                    tt = trends.track_trends(rows)
                    return self._send(200, {"available": True, "genres": trends.genre_summary(rows),
                                            "rising": [t.__dict__ for t in tt if t.rising][:15]})
                return self._send(404, {"error": "not found"})
            except Exception as e:  # noqa: BLE001
                traceback.print_exc()
                return self._send(500, {"error": str(e)})

        def do_POST(self):
            try:
                body = self._json()
                if self.path == "/api/generate":
                    cands = generator.generate(body["genre"], int(body.get("n", 4)), body.get("theme") or None,
                                               body.get("backend", "auto"))
                    return self._send(200, [c.to_dict() for c in cands])
                if self.path == "/api/score":
                    g = get_genre(body["genre"])
                    rep = score_song(body.get("title", ""), body["lyrics"], g, body.get("bpm") or None)
                    return self._send(200, {**rep.to_dict(), "tips": rep.tips()})
                if self.path == "/api/artists":
                    aid = pf.add_artist(body["name"], body["genre"], body.get("spotify_url", ""),
                                        body.get("distributor", ""), body.get("persona", ""))
                    return self._send(200, {"id": aid})
                if self.path == "/api/songs":
                    sid = pf.add_song(body["title"], body["genre"], body.get("artist"), body.get("status", "generiert"),
                                      body.get("viral_score"), body.get("bpm"), body.get("suno"),
                                      body.get("lyrics", ""), body.get("notes", ""))
                    return self._send(200, {"id": sid})
                m = re.fullmatch(r"/api/songs/(\d+)/status", self.path)
                if m:
                    pf.set_status(int(m.group(1)), body["status"], body.get("release_date"))
                    return self._send(200, {"ok": True})
                m = re.fullmatch(r"/api/songs/(\d+)/assign", self.path)
                if m:
                    pf.assign(int(m.group(1)), body["artist"])
                    return self._send(200, {"ok": True})
                if self.path == "/api/stats":
                    pf.add_stats(int(body["song_id"]), body["day"], int(body["streams"]),
                                 int(body.get("listeners") or 0), int(body.get("saves") or 0))
                    return self._send(200, {"ok": True})
                return self._send(404, {"error": "not found"})
            except Exception as e:  # noqa: BLE001
                traceback.print_exc()
                return self._send(400, {"error": str(e)})

    return Handler


def serve(db: str, host: str, port: int, trends_csv: str | None, payout: float) -> None:
    pf = Portfolio(db)
    srv = ThreadingHTTPServer((host, port), make_handler(pf, trends_csv, payout))
    print(f"liedgen läuft auf http://{host}:{port}  (Strg+C zum Beenden)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
