#!/usr/bin/env python3
"""lint_wiki.py — docs/wiki/ Phase 2 schema linter.

Enforces docs/wiki/SCHEMA.md and docs/wiki/README.md rules on the tree:

  * Directory → page-type mapping (SCHEMA §1) and kebab-case filenames (§2)
  * Frontmatter presence + required fields for content / brief / snapshot (§3)
  * Required minimal sections per page type (§4.1 / §4.2 / §4.3)
  * 300-line hard cap per page (§4 footer; README "长度硬上限")
  * Wikilink format `[[type/slug]]` + target existence (§5)
  * Orphan detection via index.md inclusion (README "Graph view 孤立节点")
  * Tag whitelist from _meta/taxonomy.md, including banned tags (§8 rule 8)
  * Each `sources:` entry must be registered in _meta/source-manifest.md
    (§8 rule 7)
  * Hermes-specific rules (§8 rules 1–5):
      1. pages containing `~/.hermes` literal must also reference
         `get_hermes_home()` or `profile`
      2. pages that talk about registering / adding tools must wikilink
         `[[entities/tool-registry]]`
      3. pages that mention `memory provider` must wikilink
         `[[entities/memoryprovider]]`
      4. comparison pages must carry a section heading with 不是 / vs / 区别
      5. query pages must wikilink to ≥ 1 entity or concept page

Scope:
  * Stdlib only. No external deps.
  * Reads only inside docs/wiki/. Does not import Hermes runtime (SCHEMA §0).
  * Prints grouped findings (errors first, then warnings) with file:line refs
    and returns exit codes suitable for PR gates.

Usage:
  python docs/wiki/scripts/lint_wiki.py              # warnings non-fatal
  python docs/wiki/scripts/lint_wiki.py --strict     # warnings -> exit 1
  python docs/wiki/scripts/lint_wiki.py --path PATH  # lint only one file

Exit codes:
  0  no errors (and no warnings in --strict mode)
  1  at least one error (or warning in --strict mode)
  2  linter could not run — taxonomy / manifest / index unreadable
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple


# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
WIKI_DIR = SCRIPT_DIR.parent
REPO_ROOT = WIKI_DIR.parent.parent

TAXONOMY_PATH = WIKI_DIR / "_meta" / "taxonomy.md"
MANIFEST_PATH = WIKI_DIR / "_meta" / "source-manifest.md"
INDEX_PATH = WIKI_DIR / "index.md"


# ----------------------------------------------------------------------------
# Exit codes
# ----------------------------------------------------------------------------

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_BROKEN = 2


# ----------------------------------------------------------------------------
# Schema constants (mirrors SCHEMA.md)
# ----------------------------------------------------------------------------

MAX_PAGE_LINES = 300

CONTENT_DIRS = ("entities", "concepts", "comparisons", "queries")
BRIEFS_DIR = "briefs"
RAW_DIR = "raw"

TYPE_BY_DIR = {
    "entities": "entity",
    "concepts": "concept",
    "comparisons": "comparison",
    "queries": "query",
    "briefs": "brief-template",
}
CONTENT_TYPES = frozenset({"entity", "concept", "comparison", "query"})

CONTENT_REQUIRED_KEYS = (
    "title",
    "type",
    "tags",
    "sources",
    "wikilinks_out",
    "last_refreshed",
    "refreshed_by",
)
BRIEF_REQUIRED_KEYS = (
    "title",
    "type",
    "usage",
    "tags",
    "wikilinks_out",
    "last_refreshed",
    "refreshed_by",
)
SNAPSHOT_REQUIRED_KEYS = (
    "kind",
    "source_path",
    "captured_at",
    "sha256",
    "supersedes",
)
SNAPSHOT_FORBIDDEN_KEYS = ("wikilinks_out", "tags")

CONTENT_REQUIRED_SECTIONS = (
    "## TL;DR",
    "## 责任边界",
    "## 调用链 / 关系",
    "## 坑点",
    "## References",
)
BRIEF_REQUIRED_SECTIONS = (
    "## Usage",
    "## Placeholders",
    "## Output destination",
)

COMPARISON_SECTION_KEYWORDS = ("不是", "vs", "区别")

ROOT_FIXED_TARGETS = frozenset({"README", "SCHEMA", "index", "log"})
BRIEF_TEMPLATE_SUFFIX = ".template"


# ----------------------------------------------------------------------------
# Hermes-specific rule markers (SCHEMA §8)
# ----------------------------------------------------------------------------

HARDCODED_PATH_LITERAL = "~/.hermes"
PROFILE_AWARE_MARKERS = ("get_hermes_home", "profile")

REGISTER_TOOL_PATTERNS: Tuple[re.Pattern, ...] = (
    re.compile(r"register[ _]a[ _]tool", re.IGNORECASE),
    re.compile(r"register_tool"),
    re.compile(r"添加工具"),
    re.compile(r"注册工具"),
)
REGISTER_TOOL_TARGET = "entities/tool-registry"

MEMORY_PROVIDER_RE = re.compile(r"memory provider", re.IGNORECASE)
MEMORY_PROVIDER_TARGET = "entities/memoryprovider"


# ----------------------------------------------------------------------------
# Parsing regex
# ----------------------------------------------------------------------------

FRONTMATTER_DELIM = "---"
WIKILINK_RE = re.compile(r"\[\[([^\[\]\n]+?)\]\]")
H2_RE = re.compile(r"^##\s+(.+?)\s*$")
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SNAPSHOT_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]+-\d{8}$")
KEY_RE = re.compile(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$")
BLOCK_ITEM_RE = re.compile(r"^\s+-\s*(.*)$")


# ----------------------------------------------------------------------------
# Dataclasses
# ----------------------------------------------------------------------------


@dataclass
class Finding:
    severity: str  # "error" | "warning"
    rule: str
    path: Path
    line: Optional[int]
    message: str


@dataclass
class WikilinkRef:
    raw: str  # full text inside [[...]], may include alias
    slug: str  # before "|"; for content pages normally "type/slug"
    line: int  # 1-based line in file


@dataclass
class Page:
    path: Path
    directory: str
    frontmatter: Dict[str, object]
    frontmatter_errors: List[str]
    body_text: str
    body_start_line: int  # 1-based line of first body line (after closing ---)
    total_lines: int


@dataclass
class LintContext:
    allowed_tags: Set[str]
    banned_tags: Set[str]
    manifest_sources: Set[str]
    existing_slugs: Set[str]  # e.g. {"entities/aiagent", "concepts/agent-loop"}
    index_slugs: Set[str]  # content slugs reachable from index.md


# ----------------------------------------------------------------------------
# YAML-ish frontmatter parser (only the shapes SCHEMA §3 uses)
# ----------------------------------------------------------------------------


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and (
        (s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")
    ):
        return s[1:-1]
    return s


def _parse_flow_list(value: str) -> List[str]:
    s = value.strip()
    if not (s.startswith("[") and s.endswith("]")):
        raise ValueError(f"expected flow list enclosed in []: {value!r}")
    inner = s[1:-1].strip()
    if not inner:
        return []
    items: List[str] = []
    buf = ""
    depth = 0
    for ch in inner:
        if ch == "," and depth == 0:
            items.append(buf)
            buf = ""
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        buf += ch
    if buf.strip():
        items.append(buf)
    return [_unquote(x.strip()) for x in items]


def parse_frontmatter(text: str) -> Tuple[Dict[str, object], int, List[str]]:
    """Parse top-of-file frontmatter.

    Returns (data, body_start_line_1based, errors).
    body_start_line is 1 when there is no frontmatter.
    """
    lines = text.splitlines()
    errors: List[str] = []
    if not lines or lines[0].strip() != FRONTMATTER_DELIM:
        return {}, 1, ["missing opening '---' frontmatter delimiter"]
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == FRONTMATTER_DELIM:
            end = i
            break
    if end is None:
        return {}, 1, ["frontmatter has no closing '---'"]

    data: Dict[str, object] = {}
    pending_key: Optional[str] = None
    pending_list: List[str] = []

    def flush() -> None:
        nonlocal pending_key, pending_list
        if pending_key is not None:
            data[pending_key] = pending_list
        pending_key = None
        pending_list = []

    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m_item = BLOCK_ITEM_RE.match(raw)
        if m_item:
            if pending_key is None:
                errors.append(f"block list item with no preceding key: {raw!r}")
                continue
            pending_list.append(_unquote(m_item.group(1)))
            continue
        m_kv = KEY_RE.match(raw)
        if not m_kv:
            errors.append(f"unparseable frontmatter line: {raw!r}")
            continue
        flush()
        key = m_kv.group(1)
        val = m_kv.group(2).strip()
        if not val:
            pending_key = key
            pending_list = []
            continue
        if val.startswith("["):
            try:
                data[key] = _parse_flow_list(val)
            except ValueError as exc:
                errors.append(f"[{key}] {exc}")
                data[key] = []
        else:
            data[key] = _unquote(val)
    flush()
    return data, end + 2, errors


# ----------------------------------------------------------------------------
# Loaders: taxonomy, manifest, index
# ----------------------------------------------------------------------------


def load_taxonomy(path: Path) -> Tuple[Set[str], Set[str], List[Finding]]:
    findings: List[Finding] = []
    if not path.exists():
        findings.append(
            Finding("error", "taxonomy-missing", path, None,
                    "taxonomy.md not found — cannot validate tags")
        )
        return set(), set(), findings

    text = path.read_text(encoding="utf-8")
    allowed: Set[str] = set()
    banned: Set[str] = set()

    in_tag_table = False
    in_banned_section = False
    for line in text.splitlines():
        stripped = line.strip()

        # Allowed table: header row contains "| tag |"
        if stripped.startswith("| tag ") or stripped.startswith("|tag "):
            in_tag_table = True
            continue
        if in_tag_table:
            if not stripped.startswith("|") or stripped.startswith("|--"):
                if stripped.startswith("|--"):
                    continue
                in_tag_table = False
            else:
                cells = [c.strip() for c in stripped.strip("|").split("|")]
                if cells:
                    tag = cells[0]
                    if tag.startswith("`") and tag.endswith("`"):
                        tag = tag[1:-1]
                    if tag and tag != "tag":
                        allowed.add(tag)
                continue

        # Banned section
        if "显式禁止的 tag" in line or "banned tag" in line.lower():
            in_banned_section = True
            continue
        if in_banned_section:
            if stripped.startswith("## "):
                in_banned_section = False
                continue
            m = re.match(r"^\s*-\s+`([^`]+)`", line)
            if m:
                banned.add(m.group(1))

    return allowed, banned, findings


def load_manifest_sources(path: Path) -> Tuple[Set[str], List[Finding]]:
    findings: List[Finding] = []
    if not path.exists():
        findings.append(
            Finding("error", "manifest-missing", path, None,
                    "source-manifest.md not found — cannot validate sources")
        )
        return set(), findings

    sources: Set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if stripped.startswith("| source_path") or stripped.startswith("|---"):
            continue
        inner = stripped.strip("|").strip()
        if not inner:
            continue
        first = inner.split("|", 1)[0].strip()
        if first.startswith("`") and first.endswith("`"):
            first = first[1:-1]
        if first:
            sources.add(first)
    return sources, findings


def load_index_slugs(path: Path) -> Tuple[Set[str], List[Finding]]:
    findings: List[Finding] = []
    if not path.exists():
        findings.append(
            Finding("error", "index-missing", path, None,
                    "index.md not found — cannot detect orphans")
        )
        return set(), findings
    slugs: Set[str] = set()
    for m in WIKILINK_RE.finditer(path.read_text(encoding="utf-8")):
        target = m.group(1).split("|", 1)[0].strip()
        if "/" in target:
            slugs.add(target)
    return slugs, findings


# ----------------------------------------------------------------------------
# Page discovery & parsing
# ----------------------------------------------------------------------------


def discover_content_pages(wiki_dir: Path) -> List[Path]:
    pages: List[Path] = []
    for sub in CONTENT_DIRS + (BRIEFS_DIR,):
        d = wiki_dir / sub
        if d.exists():
            pages.extend(sorted(d.glob("*.md")))
    return pages


def discover_snapshot_pages(wiki_dir: Path) -> List[Path]:
    raw = wiki_dir / RAW_DIR
    if not raw.exists():
        return []
    return sorted(raw.rglob("*.md"))


def read_page(path: Path) -> Page:
    text = path.read_text(encoding="utf-8")
    fm, body_start, fm_errors = parse_frontmatter(text)
    total_lines = len(text.splitlines())
    # body slice as text
    lines = text.splitlines(keepends=True)
    body_text = "".join(lines[body_start - 1 :]) if body_start - 1 < len(lines) else ""
    return Page(
        path=path,
        directory=path.parent.name,
        frontmatter=fm,
        frontmatter_errors=fm_errors,
        body_text=body_text,
        body_start_line=body_start,
        total_lines=total_lines,
    )


def expected_type_for(path: Path) -> Optional[str]:
    return TYPE_BY_DIR.get(path.parent.name)


def slug_of(path: Path) -> str:
    stem = path.stem
    if path.parent.name == BRIEFS_DIR and stem.endswith(BRIEF_TEMPLATE_SUFFIX):
        stem = stem[: -len(BRIEF_TEMPLATE_SUFFIX)]
    return f"{path.parent.name}/{stem}"


def extract_wikilinks(body_text: str, body_start_line: int) -> List[WikilinkRef]:
    refs: List[WikilinkRef] = []
    for i, line in enumerate(body_text.splitlines()):
        for m in WIKILINK_RE.finditer(line):
            raw = m.group(1).strip()
            slug = raw.split("|", 1)[0].strip()
            refs.append(
                WikilinkRef(raw=raw, slug=slug, line=body_start_line + i)
            )
    return refs


def extract_h2_headers(body_text: str, body_start_line: int) -> List[Tuple[int, str]]:
    out: List[Tuple[int, str]] = []
    for i, line in enumerate(body_text.splitlines()):
        if line.startswith("##"):
            out.append((body_start_line + i, line.rstrip()))
    return out


# ----------------------------------------------------------------------------
# Filename validation
# ----------------------------------------------------------------------------


def check_filename(path: Path) -> List[Finding]:
    out: List[Finding] = []
    stem = path.stem
    parent = path.parent.name

    if parent == BRIEFS_DIR:
        if not stem.endswith(BRIEF_TEMPLATE_SUFFIX):
            out.append(
                Finding("error", "briefs-filename-suffix", path, None,
                        f"briefs file must end with '.template.md': {path.name}")
            )
            return out
        base = stem[: -len(BRIEF_TEMPLATE_SUFFIX)]
        if not KEBAB_RE.match(base):
            out.append(
                Finding("error", "filename-not-kebab", path, None,
                        f"briefs filename stem must be kebab-case: '{base}'")
            )
        return out

    if parent == RAW_DIR or (path.parent.parent and path.parent.parent.name == RAW_DIR):
        if not SNAPSHOT_NAME_RE.match(stem):
            out.append(
                Finding("error", "snapshot-filename", path, None,
                        f"raw snapshot filename must end with '-YYYYMMDD': {path.name}")
            )
        return out

    if parent in CONTENT_DIRS:
        if not KEBAB_RE.match(stem):
            out.append(
                Finding("error", "filename-not-kebab", path, None,
                        f"filename must be kebab-case (lowercase + hyphens): '{stem}'")
            )
    return out


# ----------------------------------------------------------------------------
# Frontmatter validation
# ----------------------------------------------------------------------------


def _required_keys_for(expected_type: str) -> Sequence[str]:
    if expected_type == "brief-template":
        return BRIEF_REQUIRED_KEYS
    if expected_type in CONTENT_TYPES:
        return CONTENT_REQUIRED_KEYS
    return ()


def check_frontmatter(page: Page, expected_type: str) -> List[Finding]:
    out: List[Finding] = []
    for err in page.frontmatter_errors:
        out.append(
            Finding("error", "frontmatter-parse", page.path, None, err)
        )

    declared_type = page.frontmatter.get("type")
    if declared_type != expected_type:
        out.append(
            Finding(
                "error",
                "type-mismatch",
                page.path,
                None,
                f"frontmatter type {declared_type!r} does not match "
                f"directory '{page.directory}/' (expected {expected_type!r})",
            )
        )

    for key in _required_keys_for(expected_type):
        if key not in page.frontmatter:
            out.append(
                Finding("error", "frontmatter-missing", page.path, None,
                        f"required frontmatter key missing: '{key}'")
            )
    return out


def check_snapshot_frontmatter(page: Page) -> List[Finding]:
    out: List[Finding] = []
    for err in page.frontmatter_errors:
        out.append(
            Finding("error", "frontmatter-parse", page.path, None, err)
        )
    for key in SNAPSHOT_REQUIRED_KEYS:
        if key not in page.frontmatter:
            out.append(
                Finding("error", "snapshot-frontmatter-missing", page.path, None,
                        f"snapshot frontmatter missing required key: '{key}'")
            )
    for key in SNAPSHOT_FORBIDDEN_KEYS:
        if key in page.frontmatter:
            out.append(
                Finding("error", "snapshot-frontmatter-forbidden", page.path, None,
                        f"snapshot frontmatter must not include '{key}' (SCHEMA §3.3)")
            )
    if page.frontmatter.get("kind") not in (None, "snapshot"):
        out.append(
            Finding("error", "snapshot-kind", page.path, None,
                    f"snapshot kind must be 'snapshot', got {page.frontmatter.get('kind')!r}")
        )
    return out


# ----------------------------------------------------------------------------
# Sections, length, tags, sources
# ----------------------------------------------------------------------------


def check_required_sections(page: Page, expected_type: str) -> List[Finding]:
    out: List[Finding] = []
    if expected_type in CONTENT_TYPES:
        required = CONTENT_REQUIRED_SECTIONS
    elif expected_type == "brief-template":
        required = BRIEF_REQUIRED_SECTIONS
    else:
        return out
    body = page.body_text
    for required_heading in required:
        if not any(
            line.strip() == required_heading or line.strip().startswith(required_heading + " ")
            for line in body.splitlines()
        ):
            out.append(
                Finding("error", "section-missing", page.path, None,
                        f"required section heading missing: '{required_heading}'")
            )
    return out


def check_comparison_keywords(page: Page, expected_type: str) -> List[Finding]:
    if expected_type != "comparison":
        return []
    for _, line in extract_h2_headers(page.body_text, page.body_start_line):
        for kw in COMPARISON_SECTION_KEYWORDS:
            if kw.lower() in line.lower():
                return []
    return [
        Finding(
            "error",
            "comparison-no-distinction",
            page.path,
            None,
            "comparison page must carry a section heading containing "
            "'不是', 'vs', or '区别' (SCHEMA §4.2)",
        )
    ]


def check_page_length(page: Page) -> List[Finding]:
    if page.total_lines > MAX_PAGE_LINES:
        return [
            Finding(
                "error",
                "page-too-long",
                page.path,
                None,
                f"page has {page.total_lines} lines, exceeds hard cap {MAX_PAGE_LINES} "
                "— split into smaller pages (SCHEMA §4)",
            )
        ]
    return []


def check_tags(page: Page, expected_type: str, ctx: LintContext) -> List[Finding]:
    out: List[Finding] = []
    if expected_type not in CONTENT_TYPES and expected_type != "brief-template":
        return out
    tags = page.frontmatter.get("tags", [])
    if not isinstance(tags, list):
        out.append(
            Finding("error", "tags-shape", page.path, None,
                    f"'tags' must be a list, got {type(tags).__name__}")
        )
        return out
    if not tags:
        out.append(
            Finding("error", "tags-empty", page.path, None,
                    "'tags' must contain at least one entry")
        )
    for tag in tags:
        if not isinstance(tag, str):
            out.append(
                Finding("error", "tag-shape", page.path, None,
                        f"tag must be a string, got {tag!r}")
            )
            continue
        if tag in ctx.banned_tags:
            out.append(
                Finding("error", "tag-banned", page.path, None,
                        f"tag '{tag}' is explicitly banned by taxonomy.md")
            )
        elif ctx.allowed_tags and tag not in ctx.allowed_tags:
            out.append(
                Finding("error", "tag-unknown", page.path, None,
                        f"tag '{tag}' is not in taxonomy.md whitelist")
            )
    return out


def check_sources(page: Page, expected_type: str, ctx: LintContext) -> List[Finding]:
    out: List[Finding] = []
    if expected_type not in CONTENT_TYPES:
        return out
    sources = page.frontmatter.get("sources", [])
    if not isinstance(sources, list):
        out.append(
            Finding("error", "sources-shape", page.path, None,
                    f"'sources' must be a list, got {type(sources).__name__}")
        )
        return out
    if not sources:
        out.append(
            Finding("error", "sources-empty", page.path, None,
                    "'sources' must contain at least one entry (SCHEMA §3.1)")
        )
    for src in sources:
        if not isinstance(src, str):
            continue
        if src not in ctx.manifest_sources:
            out.append(
                Finding(
                    "error",
                    "source-unregistered",
                    page.path,
                    None,
                    f"source '{src}' is not registered in _meta/source-manifest.md "
                    "(SCHEMA §8 rule 7)",
                )
            )
    return out


# ----------------------------------------------------------------------------
# Wikilinks: format + target existence
# ----------------------------------------------------------------------------


def check_wikilinks(page: Page, ctx: LintContext) -> List[Finding]:
    out: List[Finding] = []
    wls = extract_wikilinks(page.body_text, page.body_start_line)
    for wl in wls:
        slug = wl.slug
        if not slug:
            out.append(
                Finding("error", "wikilink-empty", page.path, wl.line,
                        f"empty wikilink: [[{wl.raw}]]")
            )
            continue
        if ".md" in slug:
            out.append(
                Finding("error", "wikilink-extension", page.path, wl.line,
                        f"wikilink must not include '.md': [[{wl.raw}]]")
            )
            continue
        if slug.startswith("./") or slug.startswith("../") or slug.startswith("/"):
            out.append(
                Finding("error", "wikilink-relative", page.path, wl.line,
                        f"relative-path wikilink forbidden: [[{wl.raw}]]")
            )
            continue
        if slug in ROOT_FIXED_TARGETS:
            continue
        if "/" not in slug:
            out.append(
                Finding(
                    "error",
                    "wikilink-bad-format",
                    page.path,
                    wl.line,
                    f"wikilink must be '[[type/slug]]' or root file "
                    f"(README/SCHEMA/index/log): [[{wl.raw}]]",
                )
            )
            continue
        prefix = slug.split("/", 1)[0]
        if prefix not in TYPE_BY_DIR:
            out.append(
                Finding(
                    "error",
                    "wikilink-bad-prefix",
                    page.path,
                    wl.line,
                    f"wikilink prefix must be one of "
                    f"{sorted(TYPE_BY_DIR.keys())}: [[{wl.raw}]]",
                )
            )
            continue
        if slug not in ctx.existing_slugs:
            out.append(
                Finding(
                    "warning",
                    "wikilink-missing-target",
                    page.path,
                    wl.line,
                    f"wikilink target does not exist: [[{wl.raw}]] "
                    "— if this is a future page, log it in _meta/backlog.md",
                )
            )
    return out


# ----------------------------------------------------------------------------
# Orphan check
# ----------------------------------------------------------------------------


def check_orphan(page: Page, expected_type: str, ctx: LintContext) -> List[Finding]:
    if expected_type not in CONTENT_TYPES:
        return []
    this_slug = slug_of(page.path)
    if this_slug in ctx.index_slugs:
        return []
    return [
        Finding(
            "warning",
            "orphan-page",
            page.path,
            None,
            f"page '{this_slug}' is not linked from index.md "
            "— add it under By type / By subsystem / By tag, "
            "or remove the page",
        )
    ]


# ----------------------------------------------------------------------------
# Hermes-specific rules
# ----------------------------------------------------------------------------


def _wikilink_slug_set(page: Page) -> Set[str]:
    slugs = {w.slug for w in extract_wikilinks(page.body_text, page.body_start_line)}
    fm_out = page.frontmatter.get("wikilinks_out", [])
    if isinstance(fm_out, list):
        for item in fm_out:
            if isinstance(item, str):
                slugs.add(item.strip())
    return slugs


def check_hardcoded_path(page: Page) -> List[Finding]:
    if HARDCODED_PATH_LITERAL not in page.body_text:
        return []
    if any(marker in page.body_text for marker in PROFILE_AWARE_MARKERS):
        return []
    line_no = None
    for i, line in enumerate(page.body_text.splitlines()):
        if HARDCODED_PATH_LITERAL in line:
            line_no = page.body_start_line + i
            break
    return [
        Finding(
            "warning",
            "hardcoded-path-no-profile-mention",
            page.path,
            line_no,
            f"page mentions literal '{HARDCODED_PATH_LITERAL}' without referencing "
            "'get_hermes_home()' or 'profile' — profile-aware paths expected "
            "(SCHEMA §8 rule 1)",
        )
    ]


def check_register_tool_link(page: Page, expected_type: str) -> List[Finding]:
    if expected_type not in CONTENT_TYPES:
        return []
    if slug_of(page.path) == REGISTER_TOOL_TARGET:
        return []  # the target page does not need to wikilink to itself
    if not any(p.search(page.body_text) for p in REGISTER_TOOL_PATTERNS):
        return []
    if any(s.startswith(REGISTER_TOOL_TARGET) for s in _wikilink_slug_set(page)):
        return []
    return [
        Finding(
            "warning",
            "register-tool-no-registry-link",
            page.path,
            None,
            "page discusses tool registration / `register_tool` / 添加工具 but "
            f"does not wikilink to '[[{REGISTER_TOOL_TARGET}]]' (SCHEMA §8 rule 2)",
        )
    ]


def check_memory_provider_link(page: Page, expected_type: str) -> List[Finding]:
    if expected_type not in CONTENT_TYPES:
        return []
    if slug_of(page.path) == MEMORY_PROVIDER_TARGET:
        return []
    if not MEMORY_PROVIDER_RE.search(page.body_text):
        return []
    if any(s.startswith(MEMORY_PROVIDER_TARGET) for s in _wikilink_slug_set(page)):
        return []
    return [
        Finding(
            "warning",
            "memory-provider-no-entity-link",
            page.path,
            None,
            "page mentions 'memory provider' but does not wikilink to "
            f"'[[{MEMORY_PROVIDER_TARGET}]]' (SCHEMA §8 rule 3)",
        )
    ]


def check_query_links_entity_or_concept(page: Page, expected_type: str) -> List[Finding]:
    if expected_type != "query":
        return []
    slugs = _wikilink_slug_set(page)
    for slug in slugs:
        if slug.startswith("entities/") or slug.startswith("concepts/"):
            return []
    return [
        Finding(
            "error",
            "query-no-entity-concept-link",
            page.path,
            None,
            "query page must wikilink to at least one entity/ or concept/ page "
            "(SCHEMA §8 rule 5)",
        )
    ]


# ----------------------------------------------------------------------------
# Per-page orchestration
# ----------------------------------------------------------------------------


def check_content_page(page: Page, ctx: LintContext) -> List[Finding]:
    out: List[Finding] = []
    expected_type = expected_type_for(page.path)
    if expected_type is None:
        out.append(
            Finding("error", "dir-invalid", page.path, None,
                    f"page lives in unknown wiki subdirectory: '{page.directory}'")
        )
        return out

    out.extend(check_filename(page.path))
    out.extend(check_frontmatter(page, expected_type))
    out.extend(check_tags(page, expected_type, ctx))
    out.extend(check_sources(page, expected_type, ctx))
    out.extend(check_required_sections(page, expected_type))
    out.extend(check_comparison_keywords(page, expected_type))
    out.extend(check_page_length(page))
    out.extend(check_wikilinks(page, ctx))
    out.extend(check_orphan(page, expected_type, ctx))
    out.extend(check_hardcoded_path(page))
    out.extend(check_register_tool_link(page, expected_type))
    out.extend(check_memory_provider_link(page, expected_type))
    out.extend(check_query_links_entity_or_concept(page, expected_type))
    return out


def check_snapshot_page(page: Page) -> List[Finding]:
    out: List[Finding] = []
    out.extend(check_filename(page.path))
    out.extend(check_snapshot_frontmatter(page))
    return out


# ----------------------------------------------------------------------------
# Reporter
# ----------------------------------------------------------------------------


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def report(findings: List[Finding], *, show_clean: bool = True) -> None:
    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]

    def _dump(label: str, bucket: List[Finding]) -> None:
        if not bucket:
            return
        print(f"==================== {label} ({len(bucket)}) ====================")
        grouped: Dict[str, List[Finding]] = defaultdict(list)
        for f in bucket:
            grouped[_rel(f.path)].append(f)
        for file_key in sorted(grouped.keys()):
            print(f"\n{file_key}:")
            for f in grouped[file_key]:
                loc = f":L{f.line}" if f.line is not None else ""
                print(f"  [{f.rule}]{loc} {f.message}")
        print()

    _dump("ERRORS", errors)
    _dump("WARNINGS", warnings)

    if not findings:
        if show_clean:
            print("lint_wiki: clean — no findings.")
        return

    print("==================== SUMMARY ====================")
    print(f"errors:   {len(errors)}")
    print(f"warnings: {len(warnings)}")


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------


def build_context(wiki_dir: Path) -> Tuple[LintContext, List[Finding]]:
    bootstrap: List[Finding] = []

    allowed, banned, tax_findings = load_taxonomy(TAXONOMY_PATH)
    bootstrap.extend(tax_findings)

    manifest_sources, manifest_findings = load_manifest_sources(MANIFEST_PATH)
    bootstrap.extend(manifest_findings)

    index_slugs, index_findings = load_index_slugs(INDEX_PATH)
    bootstrap.extend(index_findings)

    existing_slugs: Set[str] = set()
    for p in discover_content_pages(wiki_dir):
        existing_slugs.add(slug_of(p))

    ctx = LintContext(
        allowed_tags=allowed,
        banned_tags=banned,
        manifest_sources=manifest_sources,
        existing_slugs=existing_slugs,
        index_slugs=index_slugs,
    )
    return ctx, bootstrap


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lint_wiki.py",
        description=(
            "Schema-enforce docs/wiki/ per SCHEMA.md §1–§8. Prints grouped "
            "errors + warnings and exits non-zero on problems."
        ),
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="treat warnings as failures (exit 1 if any warning is raised)",
    )
    p.add_argument(
        "--path",
        metavar="PATH",
        help="lint only the given .md file (must live inside docs/wiki/)",
    )
    p.add_argument(
        "--no-snapshots",
        action="store_true",
        help="skip raw/ snapshot frontmatter checks",
    )
    return p


def _resolve_single_path(arg: str) -> Optional[Path]:
    p = Path(arg)
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    else:
        p = p.resolve()
    try:
        p.relative_to(WIKI_DIR)
    except ValueError:
        return None
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    ctx, bootstrap = build_context(WIKI_DIR)
    if any(f.severity == "error" and f.rule in {
        "taxonomy-missing", "manifest-missing", "index-missing"
    } for f in bootstrap):
        report(bootstrap, show_clean=False)
        return EXIT_BROKEN

    findings: List[Finding] = list(bootstrap)

    if args.path:
        target = _resolve_single_path(args.path)
        if target is None:
            print(
                f"error: --path must live inside {_rel(WIKI_DIR)}: {args.path}",
                file=sys.stderr,
            )
            return EXIT_BROKEN
        if not target.exists():
            print(f"error: file not found: {args.path}", file=sys.stderr)
            return EXIT_BROKEN
        content_pages = [target] if target.parent.name in (
            *CONTENT_DIRS, BRIEFS_DIR
        ) else []
        snapshot_pages = (
            [target]
            if (
                target.parent.name == RAW_DIR
                or (target.parent.parent and target.parent.parent.name == RAW_DIR)
            )
            else []
        )
    else:
        content_pages = discover_content_pages(WIKI_DIR)
        snapshot_pages = [] if args.no_snapshots else discover_snapshot_pages(WIKI_DIR)

    for path in content_pages:
        page = read_page(path)
        findings.extend(check_content_page(page, ctx))

    for path in snapshot_pages:
        page = read_page(path)
        findings.extend(check_snapshot_page(page))

    report(findings)

    error_count = sum(1 for f in findings if f.severity == "error")
    warning_count = sum(1 for f in findings if f.severity == "warning")
    if error_count > 0:
        return EXIT_FAIL
    if args.strict and warning_count > 0:
        return EXIT_FAIL
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
