#!/usr/bin/env python3
"""ingest_seed.py — docs/wiki/ Phase 2 ingest helper.

Reads docs/wiki/_meta/source-manifest.md, compares the recorded sha256 prefix
for each registered source against the current file on disk, and reports the
drift. With --apply it generates verbatim snapshots for kind=doc sources under
docs/wiki/raw/repo-docs/ and appends a matching manifest row (append-only; old
rows stay in place, new row carries today's date and `supersedes` pointing at
the prior snapshot_path).

Scope:
  * Stdlib only. No external dependencies.
  * Touches only docs/wiki/raw/repo-docs/ and docs/wiki/_meta/source-manifest.md.
  * kind=code sources are listed as candidates but never snapshotted
    automatically — structured code summaries require human + Claude review
    (SCHEMA §6).

Usage:
  python docs/wiki/scripts/ingest_seed.py --dry-run
  python docs/wiki/scripts/ingest_seed.py --apply
  python docs/wiki/scripts/ingest_seed.py --source README.md --apply

Exit codes:
  0  no changes, or --apply completed cleanly
  1  --apply refused because a target snapshot already exists for today
  2  manifest could not be parsed, or --source names a row that is not in the
     manifest
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
WIKI_DIR = SCRIPT_DIR.parent
REPO_ROOT = WIKI_DIR.parent.parent
MANIFEST_PATH = WIKI_DIR / "_meta" / "source-manifest.md"
RAW_DOC_DIR = WIKI_DIR / "raw" / "repo-docs"

EXIT_OK = 0
EXIT_CONFLICT = 1
EXIT_MANIFEST_BROKEN = 2

EM_DASH = "—"
HEADER_PREFIX = "| source_path |"
SHA_PREFIX_LEN = 8
EXPECTED_COLUMNS = 7


@dataclass
class ManifestRow:
    source_path: str
    kind: str
    captured_at: str
    snapshot_path: str
    sha256: str
    supersedes: str
    wiki_refs_cell: str
    line_index: int


@dataclass
class Candidate:
    row: ManifestRow
    status: str  # one of: changed | needs-snapshot | source-missing | up-to-date
    current_sha: Optional[str]
    current_mtime_date: Optional[str]


def _strip_cell(cell: str) -> str:
    s = cell.strip()
    if len(s) >= 2 and s.startswith("`") and s.endswith("`"):
        return s[1:-1]
    return s


def _parse_row(line: str, line_index: int) -> Optional[ManifestRow]:
    raw = line.rstrip("\n")
    if not raw.lstrip().startswith("|"):
        return None
    inner = raw.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    cells = [c.strip() for c in inner.split("|")]
    if len(cells) != EXPECTED_COLUMNS:
        return None
    return ManifestRow(
        source_path=_strip_cell(cells[0]),
        kind=_strip_cell(cells[1]),
        captured_at=_strip_cell(cells[2]),
        snapshot_path=_strip_cell(cells[3]),
        sha256=_strip_cell(cells[4]),
        supersedes=_strip_cell(cells[5]),
        wiki_refs_cell=cells[6],
        line_index=line_index,
    )


def parse_manifest(path: Path) -> Tuple[List[str], List[ManifestRow], int, int]:
    """Return (lines, rows, header_idx, table_end_idx_exclusive)."""
    if not path.exists():
        raise ValueError(f"manifest not found at {path}")
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

    header_idx = None
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
        row = _parse_row(lines[i], i)
        if row is None:
            raise ValueError(
                f"malformed table row at line {i + 1}: {lines[i]!r}"
            )
        rows.append(row)
        i += 1

    return lines, rows, header_idx, i


def parse_wiki_refs(cell: str) -> List[str]:
    cell = cell.strip()
    if not cell or cell == EM_DASH:
        return []
    return [_strip_cell(p) for p in cell.split(",") if p.strip()]


def _sha_hex(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(rows: List[ManifestRow]) -> List[Candidate]:
    out: List[Candidate] = []
    for row in rows:
        src = REPO_ROOT / row.source_path
        if not src.exists():
            out.append(Candidate(row, "source-missing", None, None))
            continue
        full = _sha_hex(src)
        prefix = full[:SHA_PREFIX_LEN]
        mtime_iso = _dt.date.fromtimestamp(src.stat().st_mtime).isoformat()
        if not row.sha256 or row.sha256 == EM_DASH:
            out.append(Candidate(row, "needs-snapshot", prefix, mtime_iso))
        elif prefix != row.sha256:
            out.append(Candidate(row, "changed", prefix, mtime_iso))
        else:
            out.append(Candidate(row, "up-to-date", prefix, mtime_iso))
    return out


def _affects(row: ManifestRow) -> str:
    refs = parse_wiki_refs(row.wiki_refs_cell)
    return ", ".join(refs) if refs else EM_DASH


def print_report(candidates: List[Candidate], mode: str) -> None:
    changed = [c for c in candidates if c.status == "changed"]
    needs = [c for c in candidates if c.status == "needs-snapshot"]
    missing = [c for c in candidates if c.status == "source-missing"]
    up = [c for c in candidates if c.status == "up-to-date"]

    print(f"Mode: {mode}")
    print(f"Candidate refreshes ({len(changed)}):")
    for c in changed:
        print(
            f"  - {c.row.source_path} [{c.row.kind}]"
            f" (sha256 changed: {c.row.sha256} → {c.current_sha},"
            f" mtime {c.row.captured_at} → {c.current_mtime_date})"
        )
        print(f"    affects: {_affects(c.row)}")
    print(f"Needs initial snapshot ({len(needs)}):")
    for c in needs:
        print(
            f"  - {c.row.source_path} [{c.row.kind}]"
            f" (no sha on record, current sha {c.current_sha},"
            f" mtime {c.current_mtime_date})"
        )
        print(f"    affects: {_affects(c.row)}")
    if missing:
        print(f"Source file missing ({len(missing)}):")
        for c in missing:
            missing_path = REPO_ROOT / c.row.source_path
            print(
                f"  - {c.row.source_path} [{c.row.kind}]"
                f" — file not found at {missing_path}"
            )
            print(f"    affects: {_affects(c.row)}")
    print(f"Up-to-date: {len(up)}")


def _format_cell(value: str) -> str:
    if not value or value == EM_DASH:
        return EM_DASH
    return f"`{value}`"


def _format_row(row: ManifestRow) -> str:
    cells = [
        _format_cell(row.source_path),
        row.kind,
        row.captured_at,
        _format_cell(row.snapshot_path),
        _format_cell(row.sha256),
        _format_cell(row.supersedes),
        row.wiki_refs_cell if row.wiki_refs_cell else EM_DASH,
    ]
    return "| " + " | ".join(cells) + " |\n"


def _render_doc_snapshot(
    source_path: str,
    captured_at: str,
    sha_hex: str,
    supersedes: str,
    body: str,
) -> str:
    frontmatter = (
        "---\n"
        "kind: snapshot\n"
        f"source_path: {source_path}\n"
        f"captured_at: {captured_at}\n"
        f"sha256: {sha_hex}\n"
        f"supersedes: {supersedes if supersedes else EM_DASH}\n"
        "---\n"
        "\n"
    )
    body = body.lstrip("\n")
    if not body.endswith("\n"):
        body += "\n"
    return frontmatter + body


def _doc_snapshot_target(source_path: str, date_compact: str) -> Path:
    stem = Path(source_path).stem
    return RAW_DOC_DIR / f"{stem}-{date_compact}.md"


def apply_doc_candidates(
    lines: List[str],
    candidates: List[Candidate],
    table_end_idx: int,
) -> Tuple[List[str], List[Path], List[str]]:
    today = _dt.date.today()
    date_compact = today.strftime("%Y%m%d")
    date_iso = today.isoformat()

    created: List[Path] = []
    log_entries: List[str] = []
    appended_rows: List[str] = []

    for c in candidates:
        if c.row.kind != "doc":
            continue
        if c.status not in ("changed", "needs-snapshot"):
            continue

        src = REPO_ROOT / c.row.source_path
        target = _doc_snapshot_target(c.row.source_path, date_compact)
        if target.exists():
            raise FileExistsError(str(target.relative_to(REPO_ROOT)))

        body = src.read_text(encoding="utf-8")
        full_sha = _sha_hex(src)
        prior = (
            c.row.snapshot_path
            if c.row.snapshot_path and c.row.snapshot_path != EM_DASH
            else EM_DASH
        )

        rendered = _render_doc_snapshot(
            source_path=c.row.source_path,
            captured_at=date_iso,
            sha_hex=full_sha,
            supersedes=prior,
            body=body,
        )
        RAW_DOC_DIR.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
        created.append(target)

        new_row = ManifestRow(
            source_path=c.row.source_path,
            kind=c.row.kind,
            captured_at=date_iso,
            snapshot_path=str(target.relative_to(WIKI_DIR)),
            sha256=full_sha[:SHA_PREFIX_LEN],
            supersedes=prior,
            wiki_refs_cell=c.row.wiki_refs_cell,
            line_index=-1,
        )
        appended_rows.append(_format_row(new_row))
        log_entries.append(
            f"{c.row.source_path}: snapshot"
            f" {target.relative_to(WIKI_DIR)}"
            f" sha={full_sha[:SHA_PREFIX_LEN]}"
            f" supersedes={prior}"
        )

    if not appended_rows:
        return lines, created, log_entries

    new_lines = lines[:table_end_idx] + appended_rows + lines[table_end_idx:]
    return new_lines, created, log_entries


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ingest_seed.py",
        description=(
            "Reconcile docs/wiki/_meta/source-manifest.md against current source "
            "files; on --apply, write verbatim snapshots for doc sources only."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="report candidates without writing any files (default)",
    )
    mode_group.add_argument(
        "--apply",
        dest="apply",
        action="store_true",
        help="write new snapshots for doc candidates and append manifest rows",
    )
    parser.add_argument(
        "--source",
        metavar="PATH",
        help="restrict processing to a single source_path from the manifest",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.dry_run and not args.apply:
        args.dry_run = True

    try:
        lines, rows, _header_idx, table_end = parse_manifest(MANIFEST_PATH)
    except ValueError as exc:
        print(f"error: manifest parse failure: {exc}", file=sys.stderr)
        return EXIT_MANIFEST_BROKEN

    if args.source:
        filtered = [r for r in rows if r.source_path == args.source]
        if not filtered:
            print(
                f"error: no row in manifest with source_path '{args.source}'",
                file=sys.stderr,
            )
            return EXIT_MANIFEST_BROKEN
        rows_to_process = filtered
    else:
        rows_to_process = rows

    candidates = classify(rows_to_process)
    print_report(candidates, mode="apply" if args.apply else "dry-run")

    if args.dry_run:
        return EXIT_OK

    try:
        new_lines, created, log_entries = apply_doc_candidates(
            lines, candidates, table_end
        )
    except FileExistsError as exc:
        print(
            f"error: apply conflict — target snapshot already exists: {exc}",
            file=sys.stderr,
        )
        return EXIT_CONFLICT

    if created:
        MANIFEST_PATH.write_text("".join(new_lines), encoding="utf-8")
        print()
        print(f"Applied: {len(created)} doc snapshot(s)")
        for entry in log_entries:
            print(f"  - {entry}")
        print(f"Manifest updated: {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    else:
        print()
        print("Applied: 0 doc snapshot(s) — no doc candidates pending.")

    code_pending = [
        c
        for c in candidates
        if c.row.kind == "code" and c.status in ("changed", "needs-snapshot")
    ]
    if code_pending:
        print()
        print(
            f"Reminder: {len(code_pending)} code source(s) need a structured summary"
        )
        print(
            "  (this script only snapshots kind=doc sources; code snapshots are"
            " hand-authored per SCHEMA §6 — hand to Claude Code with a CONNECT"
            " prompt)."
        )

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
