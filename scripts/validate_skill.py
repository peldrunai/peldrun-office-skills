#!/usr/bin/env python3
# scripts/validate_skill.py
"""Validate a PELDRUN skill package against the manifest schema and
structural constraints.

This script is used in two places:

1. Locally, before committing a skill change:
       python scripts/validate_skill.py skills/pdf_document
       python scripts/validate_skill.py --all

2. In CI (.github/workflows/validate.yml), on every push and pull request.

Exit codes:
    0 - the package passed validation (warnings are allowed)
    1 - the package failed validation (one or more errors)
    2 - the CLI was invoked with an invalid argument
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Manifest schema file, relative to the repository root.
SCHEMA_FILE_NAME = "manifest.schema.json"

# SKILL.md size thresholds (bytes).
SKILL_MD_SOFT_LIMIT = 10 * 1024          # Warn if a SKILL.md body exceeds this.
SKILL_MD_HARD_LIMIT = 256 * 1024        # Mirror of manifest.limits.max_instructions_bytes.

# Icon size threshold (bytes). Mirrors the backend SVG sanitizer cap.
ICON_SVG_MAX_BYTES = 32 * 1024

# sub_skills array ceiling. Mirrors the manifest schema.
MAX_SUB_SKILLS = 50

# Required manifest fields. Mirrors manifest.schema.json's "required" array.
REQUIRED_MANIFEST_FIELDS = (
    "schema_version",
    "id",
    "version",
    "name",
    "description",
    "execution",
)

# Patterns. These mirror the JSON Schema definitions.
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_]{2,63}$")
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:-[a-z0-9.\-]+)?$")
SCHEMA_VERSION_PATTERN = re.compile(r"^1\.\d+\.\d+(?:-[a-z0-9.\-]+)?$")
SUB_SKILL_PATH_PATTERN = re.compile(
    r"^sub_skills/(?:[A-Za-z0-9_.\-]+/)*[A-Za-z0-9_.\-]+\.md$"
)

# Simple heuristic to detect <script> in SVG. Full sanitization happens
# server-side in the PELDRUN backend; this is a fast pre-flight check.
SVG_SCRIPT_PATTERN = re.compile(r"<\s*script\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Report object
# ---------------------------------------------------------------------------

class ValidationReport:
    """Collects errors and warnings for one skill package."""

    def __init__(self, skill_dir: Path) -> None:
        self.skill_dir = skill_dir
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def ok(self) -> bool:
        return not self.errors

    def print(self, verbose: bool = True) -> None:
        name = self.skill_dir.name
        if not verbose and self.ok:
            print(f"[OK]   {name}")
            return

        print(f"\n=== Validating: {name} ({self.skill_dir}) ===")

        if self.errors:
            print(f"  Errors ({len(self.errors)}):")
            for err in self.errors:
                print(f"    [x] {err}")
        else:
            print("  Errors: none")

        if self.warnings:
            print(f"  Warnings ({len(self.warnings)}):")
            for warn in self.warnings:
                print(f"    [!] {warn}")
        else:
            print("  Warnings: none")

        status = "PASS" if self.ok else "FAIL"
        print(f"  Result: {status}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_schema_file(start: Path) -> Path | None:
    """Walk up from `start` looking for manifest.schema.json."""
    current = start.resolve()
    for _ in range(6):  # Limit traversal depth.
        candidate = current / SCHEMA_FILE_NAME
        if candidate.is_file():
            return candidate
        if current.parent == current:
            break
        current = current.parent
    return None


def check_file_exists(report: ValidationReport, path: Path, label: str) -> bool:
    if not path.is_file():
        report.error(f"missing required file: {label}")
        return False
    if path.stat().st_size == 0:
        report.error(f"file is empty: {label}")
        return False
    return True


def parse_frontmatter(text: str) -> dict | None:
    """Extract YAML frontmatter as a flat dict without requiring PyYAML.

    Only supports the simple `key: value` form used by SKILL.md files.
    Returns None if the frontmatter block is missing or malformed.
    """
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end].strip()
    result: dict[str, str] = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            return None
        key, _, value = line.partition(":")
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


# ---------------------------------------------------------------------------
# Validation steps
# ---------------------------------------------------------------------------

def validate_manifest_structure(report: ValidationReport, manifest: dict) -> None:
    """Structural checks that do not require the JSON Schema library."""
    for field in REQUIRED_MANIFEST_FIELDS:
        if field not in manifest:
            report.error(f"manifest.json: missing required field '{field}'")

    schema_version = manifest.get("schema_version", "")
    if schema_version and not SCHEMA_VERSION_PATTERN.match(schema_version):
        report.error(
            f"manifest.json: schema_version must match '1.x.y' (got '{schema_version}')"
        )

    manifest_id = manifest.get("id", "")
    if manifest_id and not ID_PATTERN.match(manifest_id):
        report.error(
            f"manifest.json: id must match ^[a-z0-9][a-z0-9_]{{2,63}}$ (got '{manifest_id}')"
        )

    version = manifest.get("version", "")
    if version and not SEMVER_PATTERN.match(version):
        report.error(f"manifest.json: version is not semver (got '{version}')")

    execution = manifest.get("execution", {})
    if isinstance(execution, dict):
        exec_type = execution.get("type", "instructions")
        if exec_type != "instructions":
            report.error(
                f"manifest.json: execution.type must be 'instructions' (got '{exec_type}')"
            )


def validate_manifest_against_schema(
    report: ValidationReport,
    manifest: dict,
    schema_path: Path | None,
) -> None:
    """Full JSON Schema validation, if the library and file are available."""
    if schema_path is None:
        report.warn(
            f"{SCHEMA_FILE_NAME} not found at repository root; "
            "skipping full JSON Schema validation"
        )
        return

    try:
        import jsonschema  # type: ignore
    except ImportError:
        report.warn(
            "jsonschema library not installed; "
            "skipping full JSON Schema validation (run: pip install jsonschema)"
        )
        return

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report.error(f"failed to load {schema_path.name}: {exc}")
        return

    validator = jsonschema.Draft7Validator(schema)
    for err in sorted(validator.iter_errors(manifest), key=lambda e: list(e.path)):
        location = "/".join(str(p) for p in err.path) or "<root>"
        report.error(f"manifest.json [{location}]: {err.message}")


def validate_skill_md(report: ValidationReport, skill_dir: Path, manifest: dict) -> None:
    """Check SKILL.md exists, has frontmatter, and respects size limits."""
    execution = manifest.get("execution", {})
    instructions_file = "SKILL.md"
    if isinstance(execution, dict):
        instructions_file = execution.get("instructions_file", "SKILL.md")

    if "/" in instructions_file or "\\" in instructions_file:
        report.error(
            f"execution.instructions_file must not contain a directory separator "
            f"(got '{instructions_file}')"
        )
        return

    instructions_path = skill_dir / instructions_file
    if not check_file_exists(report, instructions_path, instructions_file):
        return

    size = instructions_path.stat().st_size
    if size > SKILL_MD_HARD_LIMIT:
        report.error(
            f"{instructions_file} is {size} bytes; hard limit is {SKILL_MD_HARD_LIMIT}"
        )
    elif size > SKILL_MD_SOFT_LIMIT:
        report.warn(
            f"{instructions_file} is {size} bytes; recommended maximum is "
            f"{SKILL_MD_SOFT_LIMIT} bytes"
        )

    text = instructions_path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(text)
    if frontmatter is None:
        report.error(f"{instructions_file} is missing YAML frontmatter (--- block)")
    else:
        if "name" not in frontmatter:
            report.warn(f"{instructions_file} frontmatter is missing 'name'")
        if "description" not in frontmatter:
            report.warn(f"{instructions_file} frontmatter is missing 'description'")


def validate_icon(report: ValidationReport, skill_dir: Path, manifest: dict) -> None:
    """Check icon.svg if present; it is optional but must be safe."""
    icon_rel = manifest.get("icon")
    has_inline = "icon_svg" in manifest

    if not icon_rel and not has_inline:
        return  # Neither icon is declared — that is allowed.

    if icon_rel:
        icon_path = skill_dir / icon_rel
        if not check_file_exists(report, icon_path, icon_rel):
            return
        size = icon_path.stat().st_size
        if size > ICON_SVG_MAX_BYTES:
            report.error(
                f"{icon_rel} is {size} bytes; maximum is {ICON_SVG_MAX_BYTES}"
            )
        try:
            content = icon_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            report.error(f"{icon_rel} is not valid UTF-8")
            return
        if SVG_SCRIPT_PATTERN.search(content):
            report.error(f"{icon_rel} contains a <script> element")

    if has_inline:
        inline = manifest.get("icon_svg", "")
        if not isinstance(inline, str):
            report.error("manifest.json: icon_svg must be a string")
        elif SVG_SCRIPT_PATTERN.search(inline):
            report.error("manifest.json: icon_svg contains a <script> element")


def validate_references_dir(
    report: ValidationReport, skill_dir: Path, manifest: dict
) -> None:
    """If references_dir is declared, it must exist and be a directory."""
    execution = manifest.get("execution", {})
    if not isinstance(execution, dict):
        return
    references_dir = execution.get("references_dir")
    if not references_dir:
        return
    ref_path = skill_dir / references_dir
    if not ref_path.is_dir():
        report.error(f"references_dir '{references_dir}' is not a directory")
        return
    files = [p for p in ref_path.rglob("*") if p.is_file()]
    if not files:
        report.warn(f"references_dir '{references_dir}' is empty")


def validate_sub_skills(
    report: ValidationReport, skill_dir: Path, manifest: dict
) -> None:
    """Validate the sub_skills array and the referenced files."""
    sub_skills = manifest.get("sub_skills")
    if not sub_skills:
        return

    if not isinstance(sub_skills, list):
        report.error("manifest.json: sub_skills must be an array")
        return

    if len(sub_skills) > MAX_SUB_SKILLS:
        report.error(
            f"manifest.json: {len(sub_skills)} sub_skills declared; maximum is {MAX_SUB_SKILLS}"
        )

    seen_ids: set[str] = set()
    for index, sub in enumerate(sub_skills):
        prefix = f"sub_skills[{index}]"
        if not isinstance(sub, dict):
            report.error(f"{prefix}: must be an object")
            continue

        sub_id = sub.get("id", "")
        if not ID_PATTERN.match(sub_id):
            report.error(f"{prefix}.id is invalid: '{sub_id}'")
        elif sub_id in seen_ids:
            report.error(f"{prefix}.id duplicates a sibling: '{sub_id}'")
        else:
            seen_ids.add(sub_id)

        description = sub.get("description", "")
        if not isinstance(description, str) or not (10 <= len(description) <= 500):
            report.error(f"{prefix}.description must be 10-500 characters")

        instructions_rel = sub.get("instructions_file", "")
        if not SUB_SKILL_PATH_PATTERN.match(instructions_rel):
            report.error(
                f"{prefix}.instructions_file must match 'sub_skills/.../file.md' "
                f"(got '{instructions_rel}')"
            )
            continue

        if ".." in instructions_rel.split("/"):
            report.error(f"{prefix}.instructions_file contains '..'")

        instructions_path = (skill_dir / instructions_rel).resolve()
        try:
            instructions_path.relative_to(skill_dir.resolve())
        except ValueError:
            report.error(
                f"{prefix}.instructions_file escapes the package: '{instructions_rel}'"
            )
            continue

        if not check_file_exists(report, instructions_path, instructions_rel):
            continue

        size = instructions_path.stat().st_size
        if size > SKILL_MD_HARD_LIMIT:
            report.error(
                f"{instructions_rel} is {size} bytes; hard limit is {SKILL_MD_HARD_LIMIT}"
            )
        elif size > SKILL_MD_SOFT_LIMIT:
            report.warn(
                f"{instructions_rel} is {size} bytes; recommended maximum is "
                f"{SKILL_MD_SOFT_LIMIT} bytes"
            )

        sub_text = instructions_path.read_text(encoding="utf-8")
        if parse_frontmatter(sub_text) is None:
            report.warn(
                f"{instructions_rel} has no YAML frontmatter (recommended but not required)"
            )


def validate_id_matches_folder(report: ValidationReport, skill_dir: Path, manifest: dict) -> None:
    folder = skill_dir.name
    manifest_id = manifest.get("id", "")
    if manifest_id and manifest_id != folder:
        report.error(
            f"manifest.id '{manifest_id}' does not match folder name '{folder}'"
        )


# ---------------------------------------------------------------------------
# Public API (also used by build_zip.py and release.yml)
# ---------------------------------------------------------------------------

def validate_skill(skill_dir: Path) -> ValidationReport:
    """Run the full validation suite against one skill directory."""
    report = ValidationReport(skill_dir)

    if not skill_dir.is_dir():
        report.error(f"not a directory: {skill_dir}")
        return report

    manifest_path = skill_dir / "manifest.json"
    if not check_file_exists(report, manifest_path, "manifest.json"):
        return report

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.error(f"manifest.json is not valid JSON: {exc}")
        return report

    if not isinstance(manifest, dict):
        report.error("manifest.json must be a JSON object")
        return report

    schema_path = find_schema_file(skill_dir)

    validate_manifest_structure(report, manifest)
    validate_manifest_against_schema(report, manifest, schema_path)
    validate_id_matches_folder(report, skill_dir, manifest)
    validate_skill_md(report, skill_dir, manifest)
    validate_icon(report, skill_dir, manifest)
    validate_references_dir(report, skill_dir, manifest)
    validate_sub_skills(report, skill_dir, manifest)

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def iter_skill_dirs(skills_root: Path) -> Iterable[Path]:
    """Yield each subdirectory of skills/ in sorted order."""
    for entry in sorted(skills_root.iterdir()):
        if entry.is_dir() and not entry.name.startswith("."):
            yield entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate PELDRUN skill packages.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "skill_dir",
        nargs="?",
        type=Path,
        help="Path to a single skill directory (e.g. skills/pdf_document)",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Validate every skill under skills/",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print a one-line summary per skill",
    )
    args = parser.parse_args(argv)

    targets: list[Path]
    if args.all:
        repo_root = Path(__file__).resolve().parent.parent
        skills_root = repo_root / "skills"
        if not skills_root.is_dir():
            print(f"error: skills directory not found at {skills_root}", file=sys.stderr)
            return 2
        targets = list(iter_skill_dirs(skills_root))
        if not targets:
            print(f"error: no skills found under {skills_root}", file=sys.stderr)
            return 2
    else:
        targets = [args.skill_dir]

    failed = 0
    for skill_dir in targets:
        report = validate_skill(skill_dir)
        report.print(verbose=not args.quiet)
        if not report.ok:
            failed += 1

    print()
    if failed:
        print(f"FAILED: {failed} of {len(targets)} skill(s) failed validation.")
        return 1
    print(f"PASSED: all {len(targets)} skill(s) validated successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())