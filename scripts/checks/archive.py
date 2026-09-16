"""Windows-safe source-release path checks."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from .paths import COMPILER_VERSION, ROOT

ARCHIVE_ROOT = f"{ROOT.name}-{COMPILER_VERSION}"
MAX_ARCHIVE_MEMBER_LENGTH = 180
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
EXCLUDED_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "__pycache__",
    "build",
    "dbt_packages",
    "dist",
    "logs",
    "release",
    "target",
}
EXCLUDED_FILES = {
    ".DS_Store",
    ".coverage",
    "SHA256SUMS",
    "Thumbs.db",
    "coverage.xml",
    f"{ARCHIVE_ROOT}.zip",
    f"{ARCHIVE_ROOT}-workbook.xlsx",
}
EXCLUDED_SUFFIXES = {".duckdb", ".pyc", ".pyo"}


def release_files() -> list[Path]:
    """Return source-release files while excluding reproducible local state."""

    files: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if any(
            part in EXCLUDED_DIRECTORIES
            or part.endswith(".egg-info")
            or ".det-stage-" in part
            or "-det-prove-" in part
            for part in relative.parts
        ):
            continue
        if not path.is_file():
            continue
        if path.name in EXCLUDED_FILES or path.suffix.casefold() in EXCLUDED_SUFFIXES:
            continue
        files.append(path)
    return files


def archive_member(path: Path) -> str:
    """Map one repository file to its portable ZIP member name."""

    return (PurePosixPath(ARCHIVE_ROOT) / path.relative_to(ROOT)).as_posix()


def validate_archive_members(members: list[str]) -> list[str]:
    """Reject paths that are unsafe under ordinary Windows Explorer extraction."""

    errors: list[str] = []
    seen: dict[str, str] = {}
    for member in members:
        if len(member) > MAX_ARCHIVE_MEMBER_LENGTH:
            errors.append(
                f"release path is {len(member)} characters; maximum is "
                f"{MAX_ARCHIVE_MEMBER_LENGTH}: {member}"
            )
        folded = member.casefold()
        if folded in seen and seen[folded] != member:
            errors.append(
                f"case-insensitive release path collision: {seen[folded]} / {member}"
            )
        seen[folded] = member
        for component in PurePosixPath(member).parts:
            stem = component.split(".", 1)[0].upper()
            if stem in WINDOWS_RESERVED_NAMES:
                errors.append(f"Windows-reserved release path component: {member}")
            if component.endswith((" ", ".")):
                errors.append(
                    f"Windows-unsafe trailing character in release path: {member}"
                )
            if any(character in component for character in '<>:"\\|?*'):
                errors.append(f"Windows-invalid character in release path: {member}")
    return errors


def validate_release_paths() -> list[str]:
    """Validate every path that will be written to the source archive."""

    return validate_archive_members([archive_member(path) for path in release_files()])
