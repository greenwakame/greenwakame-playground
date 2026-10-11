#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Loopback-only static review server at the exact Pages project subpath."""
from pathlib import Path, PurePosixPath
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit
import argparse
import mimetypes

ROOT = Path(__file__).resolve().parents[1] / "site"
BASE = "/greenwakame-playground/"
class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.respond(False)
    def do_GET(self):
        self.respond(True)
    def respond(self, body):
        requested = urlsplit(self.path).path
        if requested in ("/", BASE.rstrip("/")):
            self.send_response(302)
            self.send_header("Location", BASE)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        relative = unquote(requested[len(BASE):]) if requested.startswith(BASE) else None
        permitted = relative is not None and "\\" not in relative
        if permitted:
            permitted = all(part not in (".", "..") for part in relative.split("/"))
        candidate = ROOT.joinpath(*PurePosixPath(relative or "").parts) if permitted else ROOT / "__absent__"
        if permitted:
            permitted = candidate.resolve().is_relative_to(ROOT.resolve())
        if permitted and candidate.is_dir():
            candidate = candidate / "index.html"
        status = 200 if permitted and candidate.is_file() else 404
        if status == 404:
            candidate = ROOT / "404.html"
        payload = candidate.read_bytes()
        suffix = candidate.suffix.lower()
        if candidate.name.startswith("LICENSE") or suffix in (".md", ".txt"):
            mime = "text/plain; charset=utf-8"
        else:
            mime = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
                    ".js": "text/javascript; charset=utf-8", ".json": "application/json; charset=utf-8",
                    ".wasm": "application/wasm"}.get(suffix, mimetypes.guess_type(str(candidate))[0] or "application/octet-stream")
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if body:
            self.wfile.write(payload)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args()
    assert (ROOT / "index.html").is_file(), "Build the portal first"
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print("LOCAL REVIEW: http://127.0.0.1:" + str(args.port) + BASE, flush=True)
    print("Serving site/ only. Ctrl+C to stop. No port fallback.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
