#!/usr/bin/env python3
# scripts/update_catalog.py
"""Update catalog.json for one or more PELDRUN skill packages.

catalog.json is the machine-readable index consumed by the PELDRUN Skill
Catalog subsystem. Each entry has its own version, download_url, and
SHA-256 checksum. Per-skill versioning (decision C) means updating one
skill MUST NOT touch the other entries.

Two modes:

    --only <skill_id>   Update one entry, preserve every other entry
                        byte-for-byte. Used by release.yml on a per-skill
                        tag (e.g. pdf_document-v1.1.0).

    --all               Rebuild the whole catalog from skills/ + dist/.
                        Used for the initial publication and for local
                        maintenance.

The script also:

    - Computes SHA-256 of each ZIP directly (does not trust external input).
    - Validates that the ZIP exists and matches the manifest version.
    - Produces a deterministic JSON output (sorted keys, stable indent).
    - Skips writing if the new content (ignoring updated_at) equals the
      existing content, avoiding empty commits in CI.

Usage:
    python scripts/update_catalog.py --only pdf_document
    python scripts/update_catalog.py --all
    python scripts/update_catalog.py --all --prune
    python scripts/update_catalog.py --only pdf_document --dry-run

Exit codes:
    0 - catalog updated (or already up to date)
    1 - one or more requested skills could not be updated
    2 - CLI was invoked with invalid arguments
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = REPO_ROOT / "skills"
DIST_DIR = REPO_ROOT / "dist"
CATALOG_PATH = REPO_ROOT / "catalog.json"

# GitHub location. Overridable so the same script works if the repo is
# forked, moved under an org, or mirrored.
DEFAULT_GITHUB_REPO = "peldrunai/peldrun-office-skills"
DEFAULT_BASE_URL = "https://github.com"

# Catalog schema version. Matches what the PELDRUN backend expects.
CATALOG_SCHEMA_VERSION = 1

# GitHub repo slug format: "owner/name", both non-empty, no spaces.
GITHUB_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sha256_of(path: Path) -> str:
    """Return the lowercase hex SHA-256 checksum of a file."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now_iso() -> str:
    """Return the current UTC time in ISO 8601 with a 'Z' suffix."""
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def load_manifest(skill_id: str) -> dict:
    """Load and parse skills/<skill_id>/manifest.json."""
    manifest_path = SKILLS_ROOT / skill_id / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {manifest_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{manifest_path} must contain a JSON object")
    return data


def find_zip(skill_id: str, version: str) -> Path:
    """Locate the ZIP produced by build_zip.py for a specific version."""
    zip_path = DIST_DIR / f"{skill_id}-{version}.zip"
    if not zip_path.is_file():
        raise FileNotFoundError(
            f"ZIP not found for {skill_id} v{version}: {zip_path}\n"
            f"Run: python scripts/build_zip.py --only {skill_id}"
        )
    return zip_path


def build_download_url(
    github_repo: str, base_url: str, skill_id: str, version: str
) -> str:
    """Construct the GitHub Releases download URL for a per-skill tag.

    Tag format:    <skill_id>-v<version>
    Asset format:  <skill_id>-<version>.zip
    """
    tag = f"{skill_id}-v{version}"
    filename = f"{skill_id}-{version}.zip"
    return f"{base_url}/{github_repo}/releases/download/{tag}/{filename}"


def build_catalog_entry(
    manifest: dict,
    zip_path: Path,
    github_repo: str,
    base_url: str,
) -> dict:
    """Produce one catalog.json entry from a manifest and a ZIP."""
    skill_id = manifest["id"]
    version = manifest["version"]

    sub_skills = manifest.get("sub_skills") or []
    if not isinstance(sub_skills, list):
        raise ValueError(f"{skill_id}: sub_skills must be an array")

    entry: dict = {
        "id": skill_id,
        "name": manifest.get("name", skill_id),
        "version": version,
        "description": manifest.get("description", ""),
        "download_url": build_download_url(
            github_repo, base_url, skill_id, version
        ),
        "checksum_sha256": sha256_of(zip_path),
        "tags": manifest.get("tags", []),
        "has_sub_skills": len(sub_skills) > 0,
        "sub_skills_count": len(sub_skills),
        "trust": manifest.get("trust", "unverified"),
        "license": manifest.get("license", "MIT"),
        "release_date": manifest.get("release_date")
        or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }

    # Include optional fields only when the manifest declares them, so the
    # catalog stays minimal and never fabricates defaults for absent data.
    for optional_field in ("brand_color", "short_description"):
        if manifest.get(optional_field):
            entry[optional_field] = manifest[optional_field]

    return entry


def catalogs_equal_ignoring_timestamp(a: dict, b: dict) -> bool:
    """Return True if two catalogs are identical apart from updated_at."""
    a_copy = {k: v for k, v in a.items() if k != "updated_at"}
    b_copy = {k: v for k, v in b.items() if k != "updated_at"}
    return a_copy == b_copy


def read_existing_catalog() -> dict:
    """Load catalog.json, or return an empty skeleton if it is absent/empty."""
    empty: dict = {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "updated_at": utc_now_iso(),
        "skills": [],
    }
    if not CATALOG_PATH.is_file():
        return empty
    raw = CATALOG_PATH.read_text(encoding="utf-8").strip()
    if not raw:
        return empty
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"existing catalog.json is invalid JSON: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("skills"), list):
        raise RuntimeError("existing catalog.json is malformed")
    return data


def list_skill_dirs() -> list[str]:
    """Return every skill folder name under skills/, sorted alphabetically."""
    if not SKILLS_ROOT.is_dir():
        raise RuntimeError(f"skills directory not found: {SKILLS_ROOT}")
    return sorted(
        d.name
        for d in SKILLS_ROOT.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


# ---------------------------------------------------------------------------
# Core update function
# ---------------------------------------------------------------------------

def update_catalog(
    *,
    mode: str,                       # "all" or "only"
    skill_id: str | None,            # required when mode == "only"
    github_repo: str,
    base_url: str,
    prune: bool,
    dry_run: bool,
) -> dict:
    """Apply the requested update and (unless dry_run) write catalog.json.

    Returns a summary dict with keys: catalog, changes, skipped, written.
    """
    existing = read_existing_catalog()
    existing_by_id = {
        entry["id"]: entry
        for entry in existing["skills"]
        if isinstance(entry, dict) and "id" in entry
    }

    # Resolve which skills are being updated.
    if mode == "all":
        target_ids = list_skill_dirs()
    else:
        assert skill_id is not None
        target_ids = [skill_id]

    updated_by_id: dict[str, dict] = dict(existing_by_id)
    changes: list[str] = []
    skipped: list[str] = []

    for sid in target_ids:
        try:
            manifest = load_manifest(sid)
            if manifest.get("id") != sid:
                raise ValueError(
                    f"manifest.id '{manifest.get('id')}' does not match folder '{sid}'"
                )
            version = manifest.get("version")
            if not isinstance(version, str) or not version:
                raise ValueError(f"{sid}: manifest is missing 'version'")

            zip_path = find_zip(sid, version)
            entry = build_catalog_entry(manifest, zip_path, github_repo, base_url)

            if existing_by_id.get(sid) == entry:
                changes.append(f"unchanged {sid} v{version}")
            else:
                updated_by_id[sid] = entry
                changes.append(f"updated {sid} v{version}")
        except (FileNotFoundError, ValueError) as exc:
            skipped.append(f"skipped {sid}: {exc}")

    # Pruning — only when explicitly requested, and only for entries whose
    # skill folder no longer exists under skills/.
    if prune:
        for sid in list(updated_by_id.keys()):
            if not (SKILLS_ROOT / sid).is_dir():
                del updated_by_id[sid]
                changes.append(f"pruned {sid}")

    # Deterministic ordering by id.
    sorted_entries = [
        updated_by_id[sid] for sid in sorted(updated_by_id.keys())
    ]

    new_catalog: dict = {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "updated_at": utc_now_iso(),
        "skills": sorted_entries,
    }

    written = False
    if not catalogs_equal_ignoring_timestamp(existing, new_catalog):
        if not dry_run:
            tmp_path = CATALOG_PATH.with_suffix(CATALOG_PATH.suffix + ".tmp")
            payload = json.dumps(new_catalog, indent=2, ensure_ascii=False) + "\n"
            tmp_path.write_text(payload, encoding="utf-8")
            tmp_path.replace(CATALOG_PATH)
        written = True

    return {
        "catalog": new_catalog,
        "changes": changes,
        "skipped": skipped,
        "written": written,
        "dry_run": dry_run,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Update catalog.json for PELDRUN skills.",
    )
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        "--all",
        action="store_true",
        help="Rebuild the catalog from every skill under skills/",
    )
    target_group.add_argument(
        "--only",
        metavar="SKILL_ID",
        help="Update a single skill entry (e.g. pdf_document)",
    )
    parser.add_argument(
        "--github-repo",
        default=DEFAULT_GITHUB_REPO,
        metavar="OWNER/REPO",
        help=f"GitHub repository slug (default: {DEFAULT_GITHUB_REPO})",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL for release downloads (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Remove entries whose skill folder no longer exists",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned changes without writing catalog.json",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable summary",
    )
    args = parser.parse_args(argv)

    if not GITHUB_REPO_PATTERN.match(args.github_repo):
        print(
            f"error: --github-repo must be 'owner/repo' (got '{args.github_repo}')",
            file=sys.stderr,
        )
        return 2

    try:
        result = update_catalog(
            mode="all" if args.all else "only",
            skill_id=args.only,
            github_repo=args.github_repo,
            base_url=args.base_url,
            prune=args.prune,
            dry_run=args.dry_run,
        )
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(
            json.dumps(
                {
                    "written": result["written"],
                    "dry_run": result["dry_run"],
                    "changes": result["changes"],
                    "skipped": result["skipped"],
                    "skill_count": len(result["catalog"]["skills"]),
                },
                indent=2,
            )
        )
    else:
        print("Changes:")
        if result["changes"]:
            for line in result["changes"]:
                print(f"  - {line}")
        else:
            print("  (none)")

        if result["skipped"]:
            print("\nSkipped:")
            for line in result["skipped"]:
                print(f"  - {line}")

        print()
        if result["dry_run"]:
            print(f"[dry-run] would write {CATALOG_PATH}")
        elif result["written"]:
            print(f"Wrote {CATALOG_PATH}")
        else:
            print(f"No changes to {CATALOG_PATH}")

        print(
            f"Total skills in catalog: {len(result['catalog']['skills'])}"
        )

    return 0 if not result["skipped"] else 1


if __name__ == "__main__":
    sys.exit(main())