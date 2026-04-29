#!/usr/bin/env python3
"""drift_check.py — docs/wiki/ Phase 2 source-drift reporter.

Walks docs/wiki/_meta/source-manifest.md, reads each referenced wiki page's
frontmatter ``last_refreshed``, and compares it against the on-disk mtime of
the source file. A (page, source) pair is "drifted" when the source file's
mtime is strictly newer than the page's ``last_refreshed`` (day granularity).

Scope:
  * Stdlib only. No external dependencies.
  * Reads docs/wiki/ + the source files referenced from the manifest.
  * Never writes — pure reporter.

Usage:
  python docs/wiki/scripts/drift_check.py              # any drift at all
  python docs/wiki/scripts/drift_check.py --days 14    # only drift >= 14 days

Exit codes:
  0  no drifted pages at or above the --days threshold
  1  at least one drifted page at or above the threshold
  2  manifest could not be parsed, or --days is negative
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
WIKI_DIR = SCRIPT_DIR.parent
REPO_ROOT = WIKI_DIR.parent.parent
MANIFEST_PATH = WIKI_DIR / "_meta" / "source-manifest.md"

EXIT_OK = 0
EXIT_DRIFT = 1
EXIT_BROKEN = 2

EM_DASH = "—"
HEADER_PREFIX = "| source_path |"
EXPECTED_COLUMNS = 7
FRONTMATTER_DELIM = "---"


@dataclass
class ManifestRow:
    source_path: str
    kind: str
    wiki_refs: List[str]
    line_index: int


@dataclass
class DriftEntry:
    page: str
    source: str
    source_mtime: _dt.date
    page_last_refreshed: _dt.date
    days_stale: int


def _strip_cell(cell: str) -> str:
    s = cell.strip()
    if len(s) >= 2 and s.startswith("`") and s.endswith("`"):
        return s[1:-1]
    return s


def _parse_wiki_refs(cell: str) -> List[str]:
    s = cell.strip()
    if not s or s == EM_DASH:
        return []
    return [_strip_cell(p) for p in cell.split(",") if p.strip()]


def parse_manifest(path: Path) -> List[ManifestRow]:
    if not path.exists():
        raise ValueError(f"manifest not found at {path}")
    lines = path.read_text(encoding="utf-8").splitlines()

    header_idx: Optional[int] = None
    for i, line in enumerate(lines):
        if line.startswith(HEADER_PREFIX):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError(
            "could not find table header beginning with '| source_path |'"
        )
    if header_idx + 1 >= len(lines):
        raise ValueError("manifest ends before the separator row")
    sep = lines[header_idx + 1].strip()
    if not sep.startswith("|---"):
        raise ValueError(f"missing '|---' separator after header (got: {sep!r})")

    rows: List[ManifestRow] = []
    i = header_idx + 2
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped or not stripped.startswith("|"):
            break
        inner = stripped
        if inner.startswith("|"):
            inner = inner[1:]
        if inner.endswith("|"):
            inner = inner[:-1]
        cells = [c.strip() for c in inner.split("|")]
        if len(cells) != EXPECTED_COLUMNS:
            raise ValueError(
                f"malformed table row at line {i + 1}: {lines[i]!r}"
            )
        rows.append(
            ManifestRow(
                source_path=_strip_cell(cells[0]),
                kind=_strip_cell(cells[1]),
                wiki_refs=_parse_wiki_refs(cells[6]),
                line_index=i,
            )
        )
        i += 1
    return rows


def _read_last_refreshed(
    page_path: Path,
) -> Tuple[Optional[_dt.date], Optional[str]]:
    """Return (parsed_date, error_reason). Date is None on any failure."""
    if not page_path.exists():
        return None, "page file not found"
    try:
        text = page_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"page unreadable: {exc}"
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIM:
        return None, "frontmatter missing"
    end: Optional[int] = None
    for j in range(1, len(lines)):
        if lines[j].strip() == FRONTMATTER_DELIM:
            end = j
            break
    if end is None:
        return None, "frontmatter not closed"
    for raw in lines[1:end]:
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        if key.strip() != "last_refreshed":
            continue
        v = value.strip()
        if not v:
            return None, "last_refreshed empty"
        try:
            return _dt.date.fromisoformat(v), None
        except ValueError:
            return None, f"last_refreshed not ISO date: {v!r}"
    return None, "last_refreshed absent"


def compute_drift(
    rows: List[ManifestRow],
) -> Tuple[List[DriftEntry], List[str]]:
    drift: List[DriftEntry] = []
    notes: List[str] = []

    for row in rows:
        if not row.wiki_refs:
            continue
        src = REPO_ROOT / row.source_path
        if not src.exists():
            notes.append(
                f"source missing on disk — skipping: {row.source_path}"
            )
            continue
        src_mtime = _dt.date.fromtimestamp(src.stat().st_mtime)
        for ref in row.wiki_refs:
            page_path = WIKI_DIR / ref
            refreshed, err = _read_last_refreshed(page_path)
            if refreshed is None:
                notes.append(
                    f"page '{ref}' skipped for source '{row.source_path}': {err}"
                )
                continue
            if src_mtime > refreshed:
                drift.append(
                    DriftEntry(
                        page=ref,
                        source=row.source_path,
                        source_mtime=src_mtime,
                        page_last_refreshed=refreshed,
                        days_stale=(src_mtime - refreshed).days,
                    )
                )
    return drift, notes


def print_drift_table(entries: List[DriftEntry]) -> None:
    if not entries:
        print("drift_check: no drifted pages at or above threshold.")
        return
    print("| page | source | source_mtime | page_last_refreshed | days_stale |")
    print("|------|--------|--------------|---------------------|------------|")
    for e in sorted(entries, key=lambda x: (-x.days_stale, x.page, x.source)):
        print(
            f"| `{e.page}` | `{e.source}` | {e.source_mtime.isoformat()} |"
            f" {e.page_last_refreshed.isoformat()} | {e.days_stale} |"
        )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="drift_check.py",
        description=(
            "Report docs/wiki/ pages whose source file mtime is newer than "
            "the page's frontmatter last_refreshed. Reads "
            "_meta/source-manifest.md as the authoritative page<->source "
            "binding."
        ),
    )
    p.add_argument(
        "--days",
        type=int,
        default=0,
        metavar="N",
        help="only report drift >= N days (default: 0 — any drift at all)",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.days < 0:
        print("error: --days must be >= 0", file=sys.stderr)
        return EXIT_BROKEN

    try:
        rows = parse_manifest(MANIFEST_PATH)
    except ValueError as exc:
        print(f"error: manifest parse failure: {exc}", file=sys.stderr)
        return EXIT_BROKEN

    drift, notes = compute_drift(rows)
    filtered = [d for d in drift if d.days_stale >= args.days]

    for n in notes:
        print(f"note: {n}", file=sys.stderr)

    print_drift_table(filtered)
    return EXIT_DRIFT if filtered else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
