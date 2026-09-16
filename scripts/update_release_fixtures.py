#!/usr/bin/env python3
"""Refresh release fixtures that must stay in lockstep with version bumps."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from openpyxl import load_workbook

from dbt_data_engineering_toolkit_compiler.version import COMPILER_VERSION


ROOT = Path(__file__).resolve().parents[1]
PYTHON_SOURCE = ROOT / "python" / "src"
WORKBOOKS = (
    ROOT / "python/src/dbt_data_engineering_toolkit_compiler/resources/data_product.xlsx",
    ROOT / "python/src/dbt_data_engineering_toolkit_compiler/resources/data_product_sample.xlsx",
    ROOT
    / "python/src/dbt_data_engineering_toolkit_compiler/resources/data_product_multi_source_sample.xlsx",
)
RELEASE_OUTPUTS = [
    *WORKBOOKS,
    ROOT / "CHANGELOG.md",
    ROOT / "examples/compiler/customer_360",
    ROOT / "examples/compiler/customer_accounts",
]


def release_versions() -> list[str]:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    versions = re.findall(r"^## (\d+\.\d+\.\d+)\b", changelog, flags=re.MULTILINE)
    return [version for version in versions if version != COMPILER_VERSION]


def update_release_docs(new_version: str) -> list[Path]:
    versions = release_versions()
    if not versions:
        return []
    changed: list[Path] = []
    doc_patterns = [
        "docs/**/*.md",
        "docs/**/*.html",
        "README.md",
        "python/README.md",
        "examples/compiler/**/README.md",
        "examples/end_to_end/README.md",
        "index.html",
    ]
    for pattern in doc_patterns:
        for path in ROOT.glob(pattern):
            text = path.read_text(encoding="utf-8")
            if not any(version in text for version in versions):
                continue
            for version in versions:
                text = text.replace(version, new_version)
            path.write_text(text, encoding="utf-8")
            changed.append(path)
    return changed


def update_workbook_template_version(path: Path) -> None:
    workbook = load_workbook(path)
    try:
        if "_DET Metadata" not in workbook.sheetnames:
            raise ValueError(f"Workbook is missing _DET Metadata: {path}")
        workbook["_DET Metadata"]["B4"] = COMPILER_VERSION
        if "DET Build" in workbook.sheetnames:
            workbook["DET Build"]["B8"] = COMPILER_VERSION
        workbook.save(path)
    finally:
        workbook.close()


def update_changelog() -> None:
    changelog = ROOT / "CHANGELOG.md"
    text = changelog.read_text(encoding="utf-8")
    heading = f"## {COMPILER_VERSION} - 2026-09-07"
    if heading in text:
        return
    entry = (
        f"{heading}\n\n"
        f"- Refreshed the release fixtures and example package metadata for the {COMPILER_VERSION} release.\n\n"
    )
    if text.startswith("# Changelog\n\n"):
        text = "# Changelog\n\n" + entry + text[len("# Changelog\n\n"):]
    else:
        text = f"# Changelog\n\n{entry}{text.lstrip()}"
    changelog.write_text(text, encoding="utf-8")


def run_command(args: list[str]) -> None:
    env = dict(os.environ)
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{PYTHON_SOURCE}{os.pathsep}{pythonpath}"
        if pythonpath
        else str(PYTHON_SOURCE)
    )
    result = subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)


def stage_release_outputs() -> None:
    # Fixture directories are intentionally broad and can match global ignore rules,
    # so force-add only this explicit allowlist of release outputs.
    run_command(
        ["git", "add", "-f", "--", *[str(path.relative_to(ROOT)) for path in RELEASE_OUTPUTS]]
    )


def main() -> int:
    new_version = os.environ.get("BUMPVER_NEW_VERSION", COMPILER_VERSION)
    updated_docs = update_release_docs(new_version)
    update_changelog()
    for workbook_path in WORKBOOKS:
        update_workbook_template_version(workbook_path)
    run_command(
        [
            sys.executable,
            "-m",
            "dbt_data_engineering_toolkit_compiler",
            "workbook",
            "refresh",
            "python/src/dbt_data_engineering_toolkit_compiler/resources/data_product_sample.xlsx",
        ]
    )
    run_command(
        [
            sys.executable,
            "-m",
            "dbt_data_engineering_toolkit_compiler",
            "workbook",
            "refresh",
            "python/src/dbt_data_engineering_toolkit_compiler/resources/data_product_multi_source_sample.xlsx",
        ]
    )
    run_command(
        [
            sys.executable,
            "-m",
            "dbt_data_engineering_toolkit_compiler",
            "generate",
            "python/src/dbt_data_engineering_toolkit_compiler/resources/data_product_sample.xlsx",
            "--project-dir",
            "examples/compiler/customer_360",
            "--prune",
            "--force",
        ]
    )
    run_command(
        [
            sys.executable,
            "-m",
            "dbt_data_engineering_toolkit_compiler",
            "generate",
            "python/src/dbt_data_engineering_toolkit_compiler/resources/data_product_multi_source_sample.xlsx",
            "--project-dir",
            "examples/compiler/customer_accounts",
            "--prune",
            "--force",
        ]
    )
    stage_release_outputs()
    if updated_docs:
        run_command(["git", "add", "--", *[str(path.relative_to(ROOT)) for path in updated_docs]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())