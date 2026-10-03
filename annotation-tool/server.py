#!/usr/bin/env python3
"""
Minimal local server for manual human annotation of the 50-record sample.

Design goals, in priority order:
  1. Never modify the input datasets. Both input CSVs are opened read-only and
     there is no code path that opens them for writing.
  2. Never lose an annotation. Saves are read-modify-write upserts against the
     existing file, written atomically via a temp file + os.replace, with a
     one-time backup taken before the first write of a session.
  3. Be structurally incapable of leaking a label to the browser. The API
     serves a hard-coded whitelist of fields; `source_label` is not in it and
     is never serialised to the client.
  4. Zero dependencies. Standard library only.

Run:  python annotation-tool/server.py
Then: open http://127.0.0.1:8765
"""

import argparse
import csv
import json
import os
import shutil
import socket
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECORDS_CSV = ROOT / "dataset" / "combined" / "human_evaluation_50.csv"
ANNOTATIONS_CSV = ROOT / "dataset" / "combined" / "human_annotations_50.csv"
BACKUP_CSV = ROOT / "dataset" / "combined" / "human_annotations_50.backup.csv"

HERE = Path(__file__).resolve().parent

# The ONLY fields ever sent to the browser. source_label is deliberately absent,
# as is every other inherited label/annotation column.
CLIENT_FIELDS = ("record_id", "record_index", "prompt", "response")

# Columns in the saved annotation CSV. Identifiers for traceability; no labels.
OUTPUT_COLUMNS = [
    "record_id",
    "record_index",
    "original_id",
    "source_dataset",
    "source_id",
    "group_id",
    "model",
    "framing",
    "category",
    "prompt",
    "response",
    "f1",
    "f2",
    "f3",
    "f4",
    "f5",
    "annotator",
    "annotated_at_utc",
]

VALID_SCORES = {"0", "1", "2"}

_lock = threading.Lock()
_backup_taken = False


class Annotator:
    """Owns the annotation file. All mutation goes through save()."""

    def __init__(self, records_path: Path, annotations_path: Path):
        self.records_path = records_path
        self.annotations_path = annotations_path
        self.records = self._load_records(records_path)
        self.by_id = {r["record_id"]: r for r in self.records}
        self.ids = [r["record_id"] for r in self.records]

    @staticmethod
    def _load_records(path: Path):
        if not path.exists():
            raise SystemExit(f"ERROR: records file not found: {path}")
        with path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            raise SystemExit(f"ERROR: records file is empty: {path}")
        out = []
        for i, r in enumerate(rows, 1):
            rid = r.get("id", "").strip()
            if not rid:
                raise SystemExit(f"ERROR: row {i} of {path} has no id")
            out.append(
                {
                    "record_id": rid,
                    "record_index": i,
                    "prompt": r.get("prompt", ""),
                    "response": r.get("response", ""),
                    # identifiers only, for the saved CSV
                    "original_id": r.get("original_id", ""),
                    "source_dataset": r.get("source_dataset", ""),
                    "source_id": r.get("source_id", ""),
                    "group_id": r.get("group_id", ""),
                    "model": r.get("model", ""),
                    "framing": r.get("framing", ""),
                    "category": r.get("category", ""),
                }
            )
        return out

    # ---- reading existing annotations -------------------------------------

    def existing(self):
        """record_id -> {f1..f5} for every saved row."""
        result = {}
        if not self.annotations_path.exists():
            return result
        with self.annotations_path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                rid = (row.get("record_id") or "").strip()
                if not rid:
                    continue
                result[rid] = {k: (row.get(k) or "").strip() for k in ("f1", "f2", "f3", "f4", "f5")}
        return result

    def _existing_rows(self):
        if not self.annotations_path.exists():
            return []
        with self.annotations_path.open(encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    # ---- writing ----------------------------------------------------------

    def _take_backup(self):
        """One-time backup before the session's first write."""
        global _backup_taken
        if _backup_taken or not self.annotations_path.exists():
            return
        if BACKUP_CSV.exists():
            shutil.copy2(self.annotations_path, BACKUP_CSV)
        else:
            shutil.copy2(self.annotations_path, BACKUP_CSV)
        _backup_taken = True

    def save(self, record_id, scores, annotator=""):
        """Upsert one record. Never removes other rows."""
        if record_id not in self.by_id:
            raise ValueError(f"unknown record_id: {record_id!r}")
        for k, v in scores.items():
            if str(v) not in VALID_SCORES:
                raise ValueError(f"{k} must be one of 0,1,2 - got {v!r}")
        if set(scores) != {"f1", "f2", "f3", "f4", "f5"}:
            raise ValueError("all five facets are required")

        with _lock:
            self._take_backup()

            rows = {r.get("record_id", ""): r for r in self._existing_rows()}
            order = [rid for rid in self.ids if rid in rows]
            order += [rid for rid in rows if rid not in set(self.ids)]

            rec = self.by_id[record_id]
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")

            if record_id in rows:
                row = rows[record_id]
            else:
                row = {c: rec.get(c, "") for c in OUTPUT_COLUMNS}
                rows[record_id] = row
                order.append(record_id)

            for k in ("f1", "f2", "f3", "f4", "f5"):
                row[k] = str(scores[k])
            row["annotator"] = annotator
            row["annotated_at_utc"] = now
            # Refresh identifier columns in case the sample file was reissued.
            for c in ("record_index", "original_id", "source_dataset", "source_id",
                      "group_id", "model", "framing", "category", "prompt", "response"):
                if c in rec:
                    row[c] = rec[c]

            tmp = self.annotations_path.with_suffix(".csv.tmp")
            with tmp.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
                w.writeheader()
                for rid in order:
                    w.writerow({c: rows[rid].get(c, "") for c in OUTPUT_COLUMNS})
            os.replace(tmp, self.annotations_path)  # atomic
            return record_id, now

    def reset(self, require_confirm=False):
        """Destructive. Requires explicit confirmation; backs up first."""
        if not require_confirm:
            raise PermissionError("reset requires confirmation")
        with _lock:
            if self.annotations_path.exists():
                shutil.copy2(self.annotations_path, BACKUP_CSV)
            if self.annotations_path.exists():
                self.annotations_path.unlink()
        return True


class Handler(BaseHTTPRequestHandler):
    annotator: Annotator = None
    server_version = "SycAuditAnnotator/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))

    # ---- helpers ----------------------------------------------------------

    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj).encode("utf-8"))

    def _read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        return json.loads(self.rfile.read(n).decode("utf-8"))

    # ---- routes -----------------------------------------------------------

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            return self._static("index.html")
        if path == "/app.js":
            return self._static("app.js")
        if path == "/style.css":
            return self._static("style.css")
        if path == "/api/records":
            a = self.annotator
            return self._json(200, {
                "total": len(a.records),
                "records": [
                    {k: r[k] for k in CLIENT_FIELDS} for r in a.records
                ],
                "annotations": a.existing(),
                "annotations_path": str(a.annotations_path),
            })
        if path == "/api/annotations":
            return self._json(200, {"annotations": self.annotator.existing()})
        if path == "/api/download":
            return self._download()
        return self._json(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            body = self._read_json()
        except Exception as e:
            return self._json(400, {"error": f"bad JSON: {e}"})

        if path == "/api/save":
            rid = body.get("record_id")
            scores = body.get("scores") or {}
            try:
                _, now = self.annotator.save(
                    rid,
                    {k: scores.get(k) for k in ("f1", "f2", "f3", "f4", "f5")},
                    annotator=(body.get("annotator") or "")[:64],
                )
            except ValueError as e:
                return self._json(400, {"error": str(e)})
            return self._json(200, {"ok": True, "record_id": rid, "saved_at": now})

        if path == "/api/reset":
            try:
                self.annotator.reset(require_confirm=bool(body.get("confirm")))
            except PermissionError as e:
                return self._json(403, {"error": str(e)})
            return self._json(200, {"ok": True})

        return self._json(404, {"error": "not found"})

    def _static(self, name):
        p = HERE / name
        if not p.exists():
            return self._json(404, {"error": f"missing {name}"})
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
        }[p.suffix]
        if p.suffix == ".html":
            # Rewrite asset URLs with an mtime token so an edited stylesheet or
            # script can never be served from a stale browser cache. A browser
            # holding the pre-fix /style.css requests a different URL as soon as
            # the file changes, which forces a fresh fetch.
            body = p.read_bytes()
            for asset in ("style.css", "app.js"):
                ap_ = HERE / asset
                token = int(ap_.stat().st_mtime) if ap_.exists() else 0
                body = body.replace(
                    f'"/{asset}"'.encode("utf-8"),
                    f'"/{asset}?v={token}"'.encode("utf-8"),
                )
            return self._send(200, body, ctype)
        return self._send(200, p.read_bytes(), ctype)

    def _download(self):
        p = self.annotator.annotations_path
        if not p.exists():
            return self._json(404, {"error": "no annotations saved yet"})
        return self._send(200, p.read_bytes(), "text/csv; charset=utf-8")


def main():
    ap = argparse.ArgumentParser(description="Human annotation tool for the 50-record sample")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    ann = Annotator(RECORDS_CSV, ANNOTATIONS_CSV)
    Handler.annotator = ann

    try:
        srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as e:
        if getattr(e, "errno", None) in (48, 98, 10048):
            print(f"Port {args.port} in use. Try: python annotation-tool/server.py --port {args.port + 1}")
            return 1
        raise

    n_done = len(ann.existing())
    print("=" * 66)
    print("  SycAudit human annotation tool")
    print("=" * 66)
    print(f"  records      : {len(ann.records)}  ({RECORDS_CSV})")
    print(f"  annotations  : {ANNOTATIONS_CSV}")
    print(f"  already done : {n_done}/{len(ann.records)}")
    print(f"  listening on : http://127.0.0.1:{args.port}")
    print("  Ctrl+C to stop")
    print("=" * 66)

    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}")).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
