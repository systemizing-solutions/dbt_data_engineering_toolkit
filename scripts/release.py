#!/usr/bin/env python3
"""Small release checks shared by local maintainers and CI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import tomllib
import yaml

ROOT = Path(__file__).resolve().parents[1]
DBT_ROOT = ROOT / "dbt"
PYTHON_SOURCE = ROOT / "python" / "src"
sys.path.insert(0, str(PYTHON_SOURCE))

from dbt_data_engineering_toolkit_compiler.version import COMPILER_VERSION


def verify_tag(tag: str) -> None:
    expected = COMPILER_VERSION
    allowed = {expected, f"v{COMPILER_VERSION}"}
    if tag not in allowed:
        allowed_list = ", ".join(repr(value) for value in sorted(allowed))
        raise ValueError(f"release tag is {tag!r}; expected one of: {allowed_list}")
    root = yaml.safe_load((DBT_ROOT / "dbt_project.yml").read_text(encoding="utf-8"))
    alias = yaml.safe_load(
        (ROOT / "aliases/de_toolkit/dbt_project.yml").read_text(encoding="utf-8")
    )
    pyproject = tomllib.loads(
        (ROOT / "python/pyproject.toml").read_text(encoding="utf-8")
    )
    versions = {
        "canonical dbt package": str(root["version"]),
        "alias dbt package": str(alias["version"]),
        "Python compiler": str(pyproject["project"]["version"]),
    }
    mismatches = {
        name: version
        for name, version in versions.items()
        if version != COMPILER_VERSION
    }
    if mismatches:
        values = ", ".join(f"{name}={value}" for name, value in mismatches.items())
        raise ValueError(f"release versions do not match {COMPILER_VERSION}: {values}")


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify-tag")
    verify.add_argument("tag")
    args = parser.parse_args()
    if args.command == "verify-tag":
        verify_tag(args.tag)
        print(f"Release tag {args.tag} matches every package version.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
