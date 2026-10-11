#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only static checks, with new local audit records. No version changes."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, unquote
import base64
import argparse
import hashlib
import json
import re
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
parser = argparse.ArgumentParser()
parser.add_argument("--report", default="audit/public-inventory.json")
args = parser.parse_args()
BASE = "/greenwakame-playground/"
VERSION = SITE / "works/midnight-inspection/v0.1.0-phase1"
INFO_HASH = "fca101370091e62d3e7139cbd65a4f72bbd4f33af23d95e60f58fc0d2e9826b8"
class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []
        self.ids = set()
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        for key in ("href", "src"):
            if key in attrs:
                self.refs.append(attrs[key])

files = sorted(path for path in SITE.rglob("*") if path.is_file())
assert all(not path.is_symlink() for path in SITE.rglob("*")), "Public tree contains symlinks"
assert hashlib.sha256((VERSION / "build-info.json").read_bytes()).hexdigest() == INFO_HASH
info = json.loads((VERSION / "build-info.json").read_text(encoding="utf-8"))
assert info["sourceCommit"] == "6f1c1788e01162cd38264fe373f97520c4ab9884"
assert info["base"] == BASE + "works/midnight-inspection/v0.1.0-phase1/"
assert info["sourcemap"] is False
assert {path.relative_to(VERSION).as_posix() for path in VERSION.rglob("*") if path.is_file()} == set(info["files"]) | {"build-info.json"}
for name, entry in info["files"].items():
    assert hashlib.sha256((VERSION / name).read_bytes()).hexdigest() == entry["sha256"], name
forbidden_names = {".git", "node_modules", "tests", "src", "work", ".env", "package.json", "pnpm-lock.yaml"}
assert not any(path.suffix.lower() in (".map", ".ts", ".tsx", ".py", ".tar") or any(part in forbidden_names for part in path.relative_to(SITE).parts) for path in files)
documents = {}
for path in files:
    if path.suffix == ".html":
        doc = Document()
        doc.feed(path.read_text(encoding="utf-8"))
        documents[path] = doc
internal = []
external = set()
for path, doc in documents.items():
    current = "http://review.invalid" + BASE + path.relative_to(SITE).as_posix()
    for ref in doc.refs:
        parsed = urlsplit(ref)
        if parsed.scheme == "data":
            continue
        if parsed.scheme or parsed.netloc:
            assert parsed.scheme == "https" and parsed.netloc, "Unexpected external scheme"
            external.add(ref)
            continue
        resolved = urlsplit(urljoin(current, ref))
        assert resolved.path.startswith(BASE), "Wrong Pages subpath: " + ref
        target = SITE / unquote(resolved.path[len(BASE):])
        assert target.resolve().is_relative_to(SITE.resolve())
        if target.is_dir():
            target = target / "index.html"
        assert target.is_file(), "Broken internal link: " + ref
        if resolved.fragment:
            assert target in documents and unquote(resolved.fragment) in documents[target].ids, "Missing fragment: " + ref
        internal.append({"from": path.relative_to(SITE).as_posix(), "to": target.relative_to(SITE).as_posix()})
corpus = []
wasm = []
binary_assets = []
for path in files:
    raw = path.read_bytes()
    if path.suffix == ".png":
        # Validate PNG structure/CRCs; only metadata-declared, approved bytes are accepted.
        metadata = json.loads((ROOT / "metadata/works.json").read_text(encoding="utf-8"))
        covers = {item["cover"]["path"]: item["cover"] for item in metadata["works"]}
        name = path.relative_to(SITE).as_posix()
        assert name in covers and hashlib.sha256(raw).hexdigest() == covers[name]["sha256"]
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"
        offset, chunks = 8, []
        while offset < len(raw):
            length = struct.unpack(">I", raw[offset:offset+4])[0]
            kind = raw[offset+4:offset+8]
            payload = raw[offset+8:offset+8+length]
            crc = struct.unpack(">I", raw[offset+8+length:offset+12+length])[0]
            assert zlib.crc32(kind + payload) & 0xffffffff == crc
            chunks.append(kind)
            offset += length + 12
        assert offset == len(raw) and chunks[0] == b"IHDR" and chunks[-1] == b"IEND" and b"IDAT" in chunks
        assert struct.unpack(">II", raw[16:24]) == (covers[name]["width"], covers[name]["height"])
        binary_assets.append({"path": name, "type": "image/png", "bytes": len(raw), "approvedHashMatches": True, "crcVerified": True})
        corpus.append((name + ":raw-byte-pattern-scan", raw.decode("latin1")))
        continue
    text = raw.decode("utf-8", errors="strict")
    if path.suffix == ".js":
        matches = [match for match in re.finditer(r"AGFzbQ[A-Za-z0-9+/=]*", text) if len(match.group()) > 10000]
        for match in matches:
            decoded = base64.b64decode(match.group())
            assert decoded[:8] == b"\0asm\x01\0\0\0"
            wasm.append({"bytes": len(decoded), "sha256": hashlib.sha256(decoded).hexdigest()})
            corpus.append((path.name + ":decoded-wasm", decoded.decode("utf-8", errors="replace")))
        for match in reversed(matches):
            text = text[:match.start()] + "<embedded-wasm>" + text[match.end():]
    corpus.append((path.relative_to(SITE).as_posix(), text))
patterns = {
    "sourceMapDirective": r"sourceMappingURL",
    "personalAbsolutePath": r"/Users/|/home/(?!runner(?:/|$))|[A-Za-z]:\\\\Users\\\\",
    "githubToken": r"gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}",
    "awsAccessKey": r"AKIA[A-Z0-9]{16}",
    "privateKey": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "developmentClient": r"@vite/client|/@fs/|debug=audio|debug=anomaly"
}
findings = []
for name, pattern in patterns.items():
    for path, text in corpus:
        if re.search(pattern, text):
            findings.append({"check": name, "file": path})
assert not findings, "Public audit findings (values omitted): " + repr(findings)
manifest = {path.relative_to(SITE).as_posix(): {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in files}
license_data = json.loads((SITE / "licenses/supplement/components.json").read_text(encoding="utf-8"))
assert isinstance(license_data, dict) and isinstance(license_data.get("p1iTarget18Counts"), dict)
counts = license_data["p1iTarget18Counts"]
license_status = ("RELEASE READY" if license_data.get("status") == "COVERED"
                  and counts.get("ACTION REQUIRED") == 0 and counts.get("EVIDENCE GAP") == 0
                  and license_data.get("remainingHolds") == [] else "HOLD")
report = {"status": "PASS", "files": len(files), "bytes": sum(entry["bytes"] for entry in manifest.values()),
          "versionFiles": len(info["files"]) + 1, "versionBytes": sum(path.stat().st_size for path in VERSION.rglob("*") if path.is_file()),
          "fixedVersionUnchanged": True, "fixedBuildInfoSha256": INFO_HASH,
          "htmlPages": len(documents), "internalReferencesChecked": len(internal), "externalLinks": sorted(external),
          "embeddedWasm": wasm, "binaryAssets": binary_assets, "patternFindings": findings, "scans": list(patterns),
          "sourceMaps": 0, "developmentFiles": 0, "upstreamBuildPaths": "Rust/WASM upstream /home/runner and /rustc paths remain; no personal absolute paths detected",
          "securityLimit": "Pattern and file-scope inspection is not a proof of absence of every possible secret",
          "licenseAssessment": {"status": license_status, "scope": license_data["scope"],
                                "target18Counts": counts, "coverageLimit": license_data["coverageLimit"],
                                "remainingNonBlocking": license_data["remainingNonBlocking"]},
          "designReview": "User approved", "priorUserGameplayQa": "8/8 PASS; Chrome version unrecorded",
          "publicationStatus": "NOT_PUBLISHED", "publicReleaseApproved": False,
          "releaseHolds": license_data["remainingHolds"],
          "manifest": manifest}
out = ROOT / args.report
out.parent.mkdir(parents=True, exist_ok=True)
with out.open("x", encoding="utf-8") as stream:
    json.dump(report, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print("PUBLIC AUDIT PASS:", report["files"], "files;", report["bytes"], "bytes;", len(internal), "internal references;", len(external), "external URL(s)")
print("FIXED VERSION UNCHANGED; no map, personal path, known credential pattern, or development-file findings")
print("LICENSE ASSESSMENT:", license_status, "for reviewed conditions; design user approved; publication requires separate approval")
