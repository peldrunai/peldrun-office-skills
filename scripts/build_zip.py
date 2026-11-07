#!/usr/bin/env python3
# scripts/build_zip.py
"""Build deterministic ZIP archives for one or more PELDRUN skill packages.

Deterministic means: for the same input files, this script produces
byte-identical ZIPs with the same SHA-256 checksum. This is achieved by:

    - Sorting files by their POSIX relative path.
    - Fixing the modification time to 1980-01-01T00:00:00 (the MS-DOS epoch).
    - Fixing the file mode to 0o644 (-rw-r--r--).
    - Using the same compression level (9) and algorithm (DEFLATED).

Determinism matters because catalog.json records the SHA-256 of each ZIP.
If the ZIP were non-deterministic, every rebuild would change the checksum
even when no source file changed, invalidating the catalog entry.

Usage:
    python scripts/build_zip.py --all
    python scripts/build_zip.py --only pdf_document
    python scripts/build_zip.py --all --output-dir /tmp/zips
    python scripts/build_zip.py --all --json > build-report.json

Exit codes:
    0 - all requested skills were built
    1 - at least one skill failed (validation or build)
    2 - CLI was invoked with invalid arguments
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

# The sibling validator lives in the same directory. The explicit
# sys.path insert lets this script run from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_skill import validate_skill  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = REPO_ROOT / "skills"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "dist"

# Fixed timestamp for every ZIP entry. Must be >= 1980 (the MS-DOS epoch),
# which is the minimum value the ZIP format can represent.
FIXED_DATE_TIME = (1980, 1, 1, 0, 0, 0)

# Fixed file mode. 0o644 = rw-r--r--, world-readable, not executable.
FIXED_FILE_MODE = 0o644

# Compression level. 9 = maximum. Deterministic for a given zlib version.
COMPRESS_LEVEL = 9

# Package hard limits (mirror the backend validator).
MAX_FILES = 500
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024              # 5 MiB per file
MAX_TOTAL_UNCOMPRESSED_BYTES = 100 * 1024 * 1024   # 100 MiB total

# Soft warning threshold. The plan targets ~12 KB per ZIP; we warn well
# above that to leave headroom for references, but low enough to catch
# accidental bloat (e.g. committed screenshots).
SOFT_SIZE_WARNING_BYTES = 50 * 1024                # 50 KB

# Names that must never appear in a skill ZIP.
SKIP_DIR_NAMES = frozenset({
    "__pycache__", ".git", ".svn", ".hg",
    ".venv", "venv", "env", "ENV",
    "node_modules", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "dist", "build",
})

# File suffixes that must never appear in a skill ZIP.
SKIP_FILE_SUFFIXES = (".pyc", ".pyo", ".pyd")

# Exact file names that must never appear in a skill ZIP.
SKIP_FILE_NAMES = frozenset({".DS_Store", "Thumbs.db"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def should_skip(rel_path: Path) -> bool:
    """Return True if a file at rel_path (relative to the skill root)
    should be excluded from the ZIP."""
    for part in rel_path.parts:
        if part in SKIP_DIR_NAMES:
            return True
        # Skip any hidden file or any file inside a hidden directory.
        # '.' and '..' never appear as parts of a normalized relative path.
        if part.startswith("."):
            return True
    if rel_path.suffix in SKIP_FILE_SUFFIXES:
        return True
    if rel_path.name in SKIP_FILE_NAMES:
        return True
    return False


def sha256_of(path: Path) -> str:
    """Return the lowercase hex SHA-256 checksum of a file."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_files(skill_dir: Path) -> list[tuple[Path, Path]]:
    """Return a sorted list of (absolute_path, relative_path) tuples for
    every file that should be included in the ZIP.

    Raises RuntimeError if a symlink is found (symlinks are forbidden by
    the backend validator and must not reach a release ZIP).
    """
    entries: list[tuple[Path, Path]] = []
    symlinks: list[str] = []

    for path in skill_dir.rglob("*"):
        rel = path.relative_to(skill_dir)
        if path.is_symlink():
            symlinks.append(rel.as_posix())
            continue
        if not path.is_file():
            continue
        if should_skip(rel):
            continue
        entries.append((path, rel))

    if symlinks:
        raise RuntimeError(
            f"symlinks are not allowed in a skill package: {symlinks}"
        )

    entries.sort(key=lambda item: item[1].as_posix())
    return entries


def check_limits(
    skill_id: str, entries: list[tuple[Path, Path]]
) -> list[str]:
    """Return a list of error strings if the package exceeds any hard limit."""
    errors: list[str] = []

    if len(entries) > MAX_FILES:
        errors.append(
            f"{skill_id}: package contains {len(entries)} files (max {MAX_FILES})"
        )

    total_bytes = 0
    for abs_path, rel in entries:
        size = abs_path.stat().st_size
        total_bytes += size
        if size > MAX_FILE_SIZE_BYTES:
            errors.append(
                f"{skill_id}: file '{rel.as_posix()}' is {size} bytes "
                f"(max {MAX_FILE_SIZE_BYTES})"
            )

    if total_bytes > MAX_TOTAL_UNCOMPRESSED_BYTES:
        errors.append(
            f"{skill_id}: uncompressed total is {total_bytes} bytes "
            f"(max {MAX_TOTAL_UNCOMPRESSED_BYTES})"
        )

    return errors


# ---------------------------------------------------------------------------
# Public API (also used by release.yml)
# ---------------------------------------------------------------------------

def build_skill_zip(
    skill_dir: Path,
    output_dir: Path,
    *,
    skip_validation: bool = False,
) -> dict:
    """Build one skill ZIP and return a summary dictionary.

    The returned dictionary has the shape:

        {
            "id": "pdf_document",
            "version": "1.0.0",
            "path": "dist/pdf_document-1.0.0.zip",
            "sha256": "<64 hex chars>",
            "size_bytes": 12456,
            "file_count": 5,
            "warnings": ["..."] ,
        }

    Raises RuntimeError if validation fails, a hard limit is exceeded, or
    any I/O error occurs.
    """
    skill_id = skill_dir.name
    warnings: list[str] = []

    # Step 1 - validate before touching the filesystem.
    if not skip_validation:
        report = validate_skill(skill_dir)
        if not report.ok:
            joined = "; ".join(report.errors)
            raise RuntimeError(f"validation failed: {joined}")
        warnings.extend(report.warnings)

    # Step 2 - read the manifest to learn the version.
    manifest_path = skill_dir / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read manifest.json: {exc}") from exc

    version = manifest.get("version")
    if not isinstance(version, str) or not version:
        raise RuntimeError("manifest.json is missing a valid 'version' field")

    # Step 3 - collect and sort the files that will go into the ZIP.
    entries = collect_files(skill_dir)
    if not entries:
        raise RuntimeError("no files to include in the ZIP")

    # Step 4 - enforce hard limits before writing anything.
    limit_errors = check_limits(skill_id, entries)
    if limit_errors:
        raise RuntimeError("; ".join(limit_errors))

    # Step 5 - write the ZIP atomically.
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{skill_id}-{version}.zip"
    tmp_path = zip_path.with_suffix(zip_path.suffix + ".tmp")

    try:
        with zipfile.ZipFile(
            tmp_path, "w", zipfile.ZIP_DEFLATED, compresslevel=COMPRESS_LEVEL
        ) as archive:
            for abs_path, rel in entries:
                data = abs_path.read_bytes()
                zinfo = zipfile.ZipInfo(
                    filename=rel.as_posix(),
                    date_time=FIXED_DATE_TIME,
                )
                zinfo.compress_type = zipfile.ZIP_DEFLATED
                zinfo.external_attr = FIXED_FILE_MODE << 16
                zinfo.create_system = 0  # 0 = FAT; most portable.
                archive.writestr(zinfo, data)
        tmp_path.replace(zip_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise

    # Step 6 - report.
    compressed_size = zip_path.stat().st_size
    if compressed_size > SOFT_SIZE_WARNING_BYTES:
        warnings.append(
            f"ZIP is {compressed_size} bytes "
            f"(recommended under {SOFT_SIZE_WARNING_BYTES})"
        )

    try:
        rel_output = zip_path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        rel_output = str(zip_path)

    return {
        "id": skill_id,
        "version": version,
        "path": rel_output,
        "sha256": sha256_of(zip_path),
        "size_bytes": compressed_size,
        "file_count": len(entries),
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def iter_skill_dirs() -> list[Path]:
    """Return every skill directory under skills/, in sorted order."""
    return sorted(
        path
        for path in SKILLS_ROOT.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build deterministic ZIP archives for PELDRUN skills.",
    )
    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        "--all",
        action="store_true",
        help="Build every skill under skills/",
    )
    target_group.add_argument(
        "--only",
        metavar="SKILL_ID",
        help="Build a single skill by its folder name (e.g. pdf_document)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to write ZIPs into (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip validation (use only for debugging)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a JSON summary instead of human-readable output",
    )
    args = parser.parse_args(argv)

    output_dir: Path = args.output_dir
    if not output_dir.is_absolute():
        output_dir = (Path.cwd() / output_dir).resolve()

    # Resolve the target set.
    if args.all:
        if not SKILLS_ROOT.is_dir():
            print(
                f"error: skills directory not found: {SKILLS_ROOT}",
                file=sys.stderr,
            )
            return 2
        targets = iter_skill_dirs()
        if not targets:
            print(
                f"error: no skill directories under {SKILLS_ROOT}",
                file=sys.stderr,
            )
            return 2
    else:
        target = SKILLS_ROOT / args.only
        if not target.is_dir():
            print(f"error: skill directory not found: {target}", file=sys.stderr)
            return 2
        targets = [target]

    results: list[dict] = []
    failures: list[str] = []

    for skill_dir in targets:
        if not args.json:
            print(f"\n=== Building: {skill_dir.name} ===")
        try:
            summary = build_skill_zip(
                skill_dir,
                output_dir,
                skip_validation=args.skip_validate,
            )
        except RuntimeError as exc:
            failures.append(f"{skill_dir.name}: {exc}")
            if not args.json:
                print(f"  [FAIL] {exc}")
            continue

        results.append(summary)
        if not args.json:
            print(f"  Built:    {summary['path']}")
            print(f"  Size:     {summary['size_bytes']} bytes")
            print(f"  Files:    {summary['file_count']}")
            print(f"  SHA-256:  {summary['sha256']}")
            for warning in summary["warnings"]:
                print(f"  [warning] {warning}")

    # Final summary.
    if args.json:
        print(json.dumps({"results": results, "failures": failures}, indent=2))
    else:
        print()
        if failures:
            print(f"FAILED: {len(failures)} of {len(targets)} skill(s) failed.")
            for failure in failures:
                print(f"  - {failure}")
        else:
            print(f"SUCCESS: {len(results)} skill(s) built in {output_dir}")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())