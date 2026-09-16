"""Contract tests for the thin CLI exposer and every public command route."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from dbt_data_engineering_toolkit_compiler.errors import (
    ToolkitDependencyError,
    ToolkitServiceError,
    ToolkitValidationError,
)
from dbt_data_engineering_toolkit_compiler.exposers import cli
from dbt_data_engineering_toolkit_compiler.operational import ApplicationResult


class RecordingApplication:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []
        self.error = error

    def __getattr__(self, name: str):
        def invoke(*args: object, **kwargs: object) -> ApplicationResult:
            self.calls.append((name, args, kwargs))
            if self.error is not None:
                raise self.error
            return ApplicationResult.success(f"{name}: ok")

        return invoke


@pytest.mark.parametrize(
    ("argv", "method"),
    [
        (["init", "product.xlsx", "--no-input", "--no-sample-data"], "build_workbook"),
        (["workbook", "build", "product.xlsx", "--no-input", "--no-sample-data"], "build_workbook"),
        (
            [
                "workbook",
                "import",
                "product.xlsx",
                "--from-contract",
                "contract.xlsx",
                "--identity-mappings",
                "--force",
            ],
            "import_workbook",
        ),
        (
            [
                "workbook",
                "sync",
                "product.xlsx",
                "--from-ddl",
                "schema.sql",
                "--replace-schema",
                "--identity-mappings",
            ],
            "sync_workbook",
        ),
        (["workbook", "refresh", "product.xlsx"], "refresh_workbook"),
        (
            [
                "source",
                "import",
                "--workbook",
                "product.xlsx",
                "--from-dbt-manifest",
                "manifest.json",
                "--relation",
                "raw.orders",
                "--source-name",
                "raw",
                "--replace",
            ],
            "import_source",
        ),
        (["validate", "product.xlsx"], "validate"),
        (
            [
                "compile",
                "product.xlsx",
                "--output-dir",
                "contracts",
                "--dry-run",
                "--force",
                "--prune",
            ],
            "compile",
        ),
        (
            [
                "generate",
                "product.xlsx",
                "--project-dir",
                "generated",
                "--dry-run",
                "--force",
                "--prune",
            ],
            "generate",
        ),
        (
            [
                "check",
                "product.xlsx",
                "--project-dir",
                "generated",
                "--skip-dbt",
                "--skip-sqlfluff",
            ],
            "check",
        ),
        (["lint", "--project-dir", "generated"], "lint"),
        (["status", "product.xlsx", "--project-dir", "generated", "--prune"], "status"),
        (
            [
                "prove",
                "product.xlsx",
                "--project-dir",
                "generated",
                "--skip-evaluator",
                "--local-package-root",
                ".",
            ],
            "prove",
        ),
    ],
)
def test_every_cli_route_delegates_to_the_application(
    argv: list[str], method: str, capsys: pytest.CaptureFixture[str]
) -> None:
    application = RecordingApplication()

    assert cli.main(argv, application=application) == 0

    assert application.calls[0][0] == method
    assert f"{method}: ok" in capsys.readouterr().out


def test_present_separates_normal_and_error_messages(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = ApplicationResult(exit_code=7, messages=("done", ""), error_messages=("bad", ""))

    assert cli._present(result) == 7

    captured = capsys.readouterr()
    assert captured.out == "done\n"
    assert captured.err == "bad\n"


def test_prompt_helpers_accept_defaults_and_truthy_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter(["", "YES", "no"])
    monkeypatch.setattr("builtins.input", lambda _label: next(answers))

    assert cli._prompt("Name", "Default") == "Default"
    assert cli._prompt_yes_no("Sample") is True
    assert cli._prompt_yes_no("Sample", default=True) is False


def test_interactive_workbook_answers_are_filename_specific(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class InteractiveInput:
        @staticmethod
        def isatty() -> bool:
            return True

    answers = iter(
        [
            "no",
            "sales product",
            "Sales Product",
            "commercial",
            "Curated sales",
            "data-team",
            "yes",
            "stg sales",
        ]
    )
    monkeypatch.setattr(cli.sys, "stdin", InteractiveInput())
    monkeypatch.setattr("builtins.input", lambda _label: next(answers))
    args = cli.build_parser().parse_args(["workbook", "build", "ignored.xlsx"])

    scaffold, include_sample = cli._workbook_answers(args, Path("orders.xlsx"))

    assert include_sample is False
    assert scaffold.product_id == "sales_product"
    assert scaffold.name == "Sales Product"
    assert scaffold.domain == "commercial"
    assert scaffold.initial_model == "stg_sales"


def test_interactive_sample_requires_positive_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    class InteractiveInput:
        @staticmethod
        def isatty() -> bool:
            return True

    monkeypatch.setattr(cli.sys, "stdin", InteractiveInput())
    monkeypatch.setattr("builtins.input", lambda _label: "yes")
    args = cli.build_parser().parse_args(["workbook", "build", "anything.xlsx"])

    scaffold, include_sample = cli._workbook_answers(args, Path("anything.xlsx"))

    assert include_sample is True
    assert scaffold.product_id == "customer_accounts"


@pytest.mark.parametrize(
    ("error", "exit_code"),
    [
        (ToolkitValidationError("invalid workbook"), 2),
        (ToolkitDependencyError("missing dependency"), 3),
        (ToolkitServiceError("service failed"), 1),
        (ValueError("bad value"), 2),
        (OSError("bad file"), 2),
        (KeyError("missing key"), 2),
    ],
)
def test_main_maps_owned_failures_to_stable_exit_codes(
    error: Exception,
    exit_code: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    application = RecordingApplication(error)

    assert cli.main(["validate", "product.xlsx"], application=application) == exit_code

    assert str(error) in capsys.readouterr().err


def test_init_defaults_to_demo_workbook_for_first_run() -> None:
    args = cli.build_parser().parse_args(["init", "customer_accounts.xlsx"])

    assert args.command == "init"
    assert args.output == "customer_accounts.xlsx"
    assert args.sample_customer_data is True


def test_new_scaffolds_a_complete_starter_project(
    capsys: pytest.CaptureFixture[str],
) -> None:
    application = RecordingApplication()

    exit_code = cli.main(["new", "customer_360"], application=application)

    assert exit_code == 0
    method, args, kwargs = application.calls[0]
    assert method == "scaffold_project"
    assert args[0] == Path("customer_360").resolve()
    assert kwargs == {"force": False}
    assert "scaffold_project: ok" in capsys.readouterr().out


def test_new_creates_a_valid_generated_project(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "customer_360"

    assert cli.main(["new", str(project)]) == 0

    assert (project / "data_product.xlsx").is_file()
    assert (project / "dbt_project.yml").is_file()
    assert (project / "contracts" / "customer_accounts.odcs.yaml").is_file()
    assert (project / "models" / "staging" / "stg_customers.sql").is_file()
    assert (project / "seeds" / "raw_customers.csv").is_file()
    assert (project / "seeds" / "raw_accounts.csv").is_file()
    output = capsys.readouterr().out
    assert "Valid: Customer Accounts" in output
    assert f"cd {project.resolve()}" in output
    assert "det prove data_product.xlsx --project-dir ." in output


def test_new_refuses_to_overwrite_an_existing_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "customer_360"
    project.mkdir()

    assert cli.main(["new", str(project)]) == 2

    assert "Refusing to overwrite" in capsys.readouterr().err
    assert not (project / "data_product.xlsx").exists()


def test_quickstart_lists_first_success_steps(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(["quickstart"], application=RecordingApplication())

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "DBT_DATA_ENGINEERING_TOOLKIT_GIT_URL" not in output
    assert "det new customer_360" in output
    assert "cd customer_360" in output
    assert "det prove data_product.xlsx --project-dir ." in output


def test_source_resolves_contract_ddl_and_manifest_paths() -> None:
    for values, expected in (
        (
            {"from_contract": "contract.yml", "from_ddl": None, "from_dbt_manifest": None},
            cli.ImportFormat.ODCS,
        ),
        (
            {"from_contract": None, "from_ddl": "schema.sql", "from_dbt_manifest": None},
            cli.ImportFormat.DDL,
        ),
        (
            {"from_contract": None, "from_ddl": None, "from_dbt_manifest": "manifest.json"},
            cli.ImportFormat.DBT_MANIFEST,
        ),
    ):
        path, source_format = cli._source(argparse.Namespace(**values))
        assert path.is_absolute()
        assert source_format == expected
