"""Structured release, architecture, dependency, and consumer checks."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import tomllib
import yaml

try:
    from .archive import validate_release_paths
    from .paths import ALIAS_ROOT, COMPILER_VERSION, DBT_ROOT, ROOT
except ImportError:
    scripts_root = Path(__file__).resolve().parents[1]
    if str(scripts_root) not in sys.path:
        sys.path.insert(0, str(scripts_root))
    from checks.archive import validate_release_paths
    from checks.paths import ALIAS_ROOT, COMPILER_VERSION, DBT_ROOT, ROOT

REQUIRED_DEPENDENCIES = {
    "dbt-labs/dbt_utils",
    "AxelThevenot/dbt_assertions",
    "dbt-labs/codegen",
    "dbt-labs/dbt_project_evaluator",
}
REQUIRED_DEFAULT_PYTHON_DEPENDENCIES = {
    "datacontract-cli",
    "dbt-core",
    "dbt-duckdb",
    "duckdb",
    "sqlfluff",
    "sqlfluff-templater-dbt",
}
REQUIRED_ADAPTER_EXTRAS = {
    "athena",
    "bigquery",
    "clickhouse",
    "databricks",
    "duckdb",
    "redshift",
    "snowflake",
    "spark",
}
REQUIRED_DOCUMENTS = {
    "docs/architecture.md",
    "docs/cli.md",
    "docs/compatibility.md",
    "docs/deployment.md",
    "docs/imports.md",
    "docs/quickstart.md",
    "docs/sql_walkthrough.md",
    "docs/testing.md",
    "docs/updating.md",
    "V2.3.0_RELEASE_NOTES.md",
}
REMOVED_FILES = {
    "SOLUTION_DESIGN.md",
    "requirements-dev.txt",
    "metadata/operators.yml",
}
REMOVED_COMPATIBILITY_MODULES = {
    "cli.py",
    "datacontract.py",
    "emit.py",
    "source_import.py",
    "validation.py",
    "workbook.py",
    "workbook_import.py",
    "workbook_template.py",
}
IGNORED_SCAN_DIRECTORIES = {".git", "dbt_packages", "target", ".venv", "venv"}
MAX_README_LINES = 2500


def _yaml(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _normalized_license_terms(path: Path) -> str:
    """Return normalized MIT terms while ignoring copyright holder lines."""
    lines = path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    kept = [line.rstrip() for line in lines if not line.startswith("Copyright (c) ")]
    return "\n".join(kept).strip()


def check_project() -> list[str]:
    errors: list[str] = []
    root_project = _yaml(DBT_ROOT / "dbt_project.yml")
    alias_project = _yaml(ALIAS_ROOT / "dbt_project.yml")
    if root_project.get("name") != "dbt_data_engineering_toolkit":
        errors.append("dbt/dbt_project.yml: canonical package name changed")
    if str(root_project.get("version")) != COMPILER_VERSION:
        errors.append("dbt/dbt_project.yml: version must match version.py")
    required_dbt = root_project.get("require-dbt-version") or []
    required_dbt_text = ",".join(str(item) for item in required_dbt)
    if ">=1.10.6" not in required_dbt_text or "<3.0.0" not in required_dbt_text:
        errors.append(
            "dbt/dbt_project.yml: require-dbt-version must include Core and Fusion"
        )
    if alias_project.get("name") != "de_toolkit":
        errors.append("aliases/de_toolkit/dbt_project.yml: alias name changed")
    if str(alias_project.get("version")) != COMPILER_VERSION:
        errors.append(
            "aliases/de_toolkit/dbt_project.yml: version must match version.py"
        )
    alias_required_dbt = alias_project.get("require-dbt-version") or []
    alias_required_dbt_text = ",".join(str(item) for item in alias_required_dbt)
    if (
        ">=1.10.6" not in alias_required_dbt_text
        or "<3.0.0" not in alias_required_dbt_text
    ):
        errors.append(
            "aliases/de_toolkit/dbt_project.yml: require-dbt-version must match the canonical package"
        )
    if f"## {COMPILER_VERSION}" not in (ROOT / "CHANGELOG.md").read_text(
        encoding="utf-8"
    ):
        errors.append(f"CHANGELOG.md: missing {COMPILER_VERSION} release")

    packages = _yaml(DBT_ROOT / "packages.yml").get("packages") or []
    found = {
        str(item.get("package"))
        for item in packages
        if isinstance(item, dict) and item.get("package")
    }
    for missing in sorted(REQUIRED_DEPENDENCIES - found):
        errors.append(f"dbt/packages.yml: missing {missing}")

    pyproject = tomllib.loads(
        (ROOT / "python" / "pyproject.toml").read_text(encoding="utf-8")
    )
    project = pyproject.get("project") or {}
    if project.get("name") != "dbt-data-engineering-toolkit-compiler":
        errors.append("python/pyproject.toml: canonical distribution name changed")
    if str(project.get("version")) != COMPILER_VERSION:
        errors.append("python/pyproject.toml: version must match version.py")
    if project.get("license") != "MIT":
        errors.append(
            "python/pyproject.toml: license must match the repository MIT license"
        )
    if project.get("license-files") != ["LICENSE"]:
        errors.append("python/pyproject.toml: Python distribution must include LICENSE")
    root_license_terms = _normalized_license_terms(ROOT / "LICENSE")
    python_license_terms = _normalized_license_terms(ROOT / "python/LICENSE")
    if root_license_terms != python_license_terms:
        errors.append(
            "python/LICENSE: MIT terms must match the repository LICENSE (copyright holder text may differ)"
        )
    dependency_names = {
        str(item).split("<", 1)[0].split(">", 1)[0].split("=", 1)[0].split("[", 1)[0]
        for item in project.get("dependencies") or []
    }
    for missing in sorted(REQUIRED_DEFAULT_PYTHON_DEPENDENCIES - dependency_names):
        errors.append(f"python/pyproject.toml: {missing} must be a default dependency")
    optional_dependencies = project.get("optional-dependencies") or {}
    for missing in sorted(REQUIRED_ADAPTER_EXTRAS - set(optional_dependencies)):
        errors.append(f"python/pyproject.toml: missing {missing} adapter extra")
    if "all-adapters" in optional_dependencies:
        errors.append(
            "python/pyproject.toml: unsafe all-adapters extra must not be published"
        )
    scripts = project.get("scripts") or {}
    if scripts.get("det") != "dbt_data_engineering_toolkit_compiler.exposers.cli:main":
        errors.append(
            "python/pyproject.toml: det must point directly to the CLI exposer"
        )

    required_architecture = {
        "python/src/dbt_data_engineering_toolkit_compiler/brokers/workbooks.py",
        "python/src/dbt_data_engineering_toolkit_compiler/brokers/dependencies.py",
        "python/src/dbt_data_engineering_toolkit_compiler/brokers/target_workbooks.py",
        "python/src/dbt_data_engineering_toolkit_compiler/brokers/template_workbooks.py",
        "python/src/dbt_data_engineering_toolkit_compiler/brokers/projects.py",
        "python/src/dbt_data_engineering_toolkit_compiler/adapters.py",
        "python/src/dbt_data_engineering_toolkit_compiler/exposers/cli.py",
        "python/src/dbt_data_engineering_toolkit_compiler/services/application.py",
        "python/src/dbt_data_engineering_toolkit_compiler/services/validation/service.py",
        "python/src/dbt_data_engineering_toolkit_compiler/services/emissions/service.py",
        "python/src/dbt_data_engineering_toolkit_compiler/services/imports/structures.py",
        "python/src/dbt_data_engineering_toolkit_compiler/services/generation.py",
        "scripts/build_source_archive.py",
        "scripts/checks/archive.py",
        "scripts/generate_alias_facade.py",
    }
    for relative in sorted(required_architecture | REQUIRED_DOCUMENTS):
        if not (ROOT / relative).exists():
            errors.append(f"missing release component: {relative}")

    source_root = ROOT / "python/src/dbt_data_engineering_toolkit_compiler"
    for path in sorted(source_root.rglob("*.py")):
        relative = path.relative_to(source_root)
        source = path.read_text(encoding="utf-8")
        if relative.parts[0] != "brokers":
            for dependency in ("openpyxl", "subprocess"):
                if f"import {dependency}" in source or f"from {dependency}" in source:
                    errors.append(
                        f"{path.relative_to(ROOT)}: {dependency} must stay behind a broker"
                    )
        if "typing import Any" in source:
            errors.append(
                f"{path.relative_to(ROOT)}: replace Any with an owned model or boundary type"
            )
    for module in sorted(REMOVED_COMPATIBILITY_MODULES):
        if (source_root / module).exists():
            errors.append(f"obsolete compatibility module still exists: {module}")
    for relative in sorted(REMOVED_FILES):
        if (ROOT / relative).exists():
            errors.append(f"removed repository file still exists: {relative}")
    if list(ROOT.glob("MIGRATING_TO_*")):
        errors.append("pre-release migration guides must not be published")
    release_notes = sorted(ROOT.glob("V*_RELEASE_NOTES.md"))
    if [path.name for path in release_notes] != ["V2.3.0_RELEASE_NOTES.md"]:
        errors.append("only V2.3.0_RELEASE_NOTES.md may be published")
    for path in ROOT.rglob("*"):
        if any(part in IGNORED_SCAN_DIRECTORIES for part in path.parts):
            continue
        if path.is_dir() and re.match(
            r"\.customer_accounts(?:\.det-stage|-det-prove)-", path.name
        ):
            errors.append(
                f"temporary proof directory is checked in: {path.relative_to(ROOT)}"
            )
    for test_area in ("brokers", "services", "acceptance"):
        if not (ROOT / "python/tests" / test_area).exists():
            errors.append(f"python/tests: missing component area {test_area}")
    if len((ROOT / "README.md").read_text(encoding="utf-8").splitlines()) > MAX_README_LINES:
        errors.append(
            f"README.md: keep the guided entry point below {MAX_README_LINES} lines; use docs/"
        )

    stale_version = re.compile(r"\b[Vv]2\.(?:0|1|2)(?:\.\d+)?\b")
    text_suffixes = {".json", ".md", ".py", ".toml", ".yml", ".yaml", ".sql", ".txt"}
    for path in sorted(ROOT.rglob("*")):
        if any(part in IGNORED_SCAN_DIRECTORIES for part in path.parts):
            continue
        if not path.is_file() or path == ROOT / "CHANGELOG.md":
            continue
        if path.suffix.casefold() not in text_suffixes and path.name not in {
            "Makefile"
        }:
            continue
        if stale_version.search(path.read_text(encoding="utf-8", errors="ignore")):
            errors.append(
                f"{path.relative_to(ROOT)}: references a pre-release toolkit version"
            )

    for example in ("customer_360", "customer_accounts"):
        example_packages = (
            ROOT / f"examples/compiler/{example}/packages.yml"
        ).read_text(encoding="utf-8")
        if "local:" in example_packages:
            errors.append(
                f"{example}: generated packages.yml contains local package paths"
            )
        for required in (
            "DBT_DATA_ENGINEERING_TOOLKIT_GIT_URL",
            f"revision: {COMPILER_VERSION}",
            "aliases/de_toolkit",
        ):
            if required not in example_packages:
                errors.append(f"{example}: generated packages.yml missing {required}")
    if "templater = dbt" not in (
        ROOT / "examples/compiler/customer_360/.sqlfluff"
    ).read_text(encoding="utf-8"):
        errors.append("generated project: missing dbt-templated .sqlfluff")
    errors.extend(_check_generated_manifests())
    errors.extend(_check_consumer_sql())
    errors.extend(validate_release_paths())
    return errors


def _check_generated_manifests() -> list[str]:
    errors: list[str] = []
    for example in ("customer_360", "customer_accounts"):
        root = ROOT / "examples" / "compiler" / example
        manifest_path = root / ".det-manifest.json"
        if not manifest_path.exists():
            errors.append(f"{example}: generated manifest is missing")
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("compiler_version") != COMPILER_VERSION:
            errors.append(f"{example}: generated manifest compiler version is stale")
        if manifest.get("workbook_schema_version") != COMPILER_VERSION:
            errors.append(f"{example}: generated manifest workbook version is stale")
        files = manifest.get("files") or {}
        for relative, expected in files.items():
            destination = root / relative
            if not destination.exists():
                errors.append(f"{example}: manifest file is missing: {relative}")
                continue
            actual = hashlib.sha256(destination.read_bytes()).hexdigest()
            if actual != expected:
                errors.append(f"{example}: manifest hash is stale: {relative}")
    return errors


def _check_consumer_sql() -> list[str]:
    errors: list[str] = []
    paths: list[Path] = []
    for root in (
        ROOT / "examples/end_to_end/models",
        ROOT / "examples/end_to_end/tests",
        ROOT / "integration_tests/models",
        ROOT / "integration_tests/tests",
    ):
        paths.extend(root.rglob("*.sql"))
    for path in sorted(paths):
        source = path.read_text(encoding="utf-8")
        for namespace in ("dbt_utils.", "dbt_assertions."):
            if namespace in source:
                errors.append(
                    f"{path.relative_to(ROOT)}: {namespace} must stay behind the toolkit facade"
                )
        for removed in ("select_cleaned(", "clean_expression(", "apply_operations("):
            if removed in source:
                errors.append(f"{path.relative_to(ROOT)}: removed call {removed}")
    return errors
