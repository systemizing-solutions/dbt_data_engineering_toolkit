"""Thin command-line exposer for :class:`ToolkitApplication`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..brokers.template_workbooks import WorkbookScaffold
from ..errors import (
    ToolkitDependencyError,
    ToolkitServiceError,
    ToolkitValidationError,
)
from ..operational import ApplicationResult
from ..services.application import ImportFormat, ToolkitApplication, safe_identifier
from ..version import COMPILER_VERSION, DEFAULT_DATA_PRODUCT_VERSION, DEFAULT_TOOLKIT_REVISION


def _present(result: ApplicationResult) -> int:
    for message in result.messages:
        if message:
            print(message)
    for message in result.error_messages:
        if message:
            print(message, file=sys.stderr)
    return result.exit_code


def _prompt(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or (default or "")


def _prompt_yes_no(label: str, *, default: bool = False) -> bool:
    suffix = "Y/n" if default else "y/N"
    value = input(f"{label} [{suffix}]: ").strip().casefold()
    if not value:
        return default
    return value in {"y", "yes", "true", "1"}


def _workbook_answers(args: argparse.Namespace, destination: Path) -> tuple[WorkbookScaffold, bool]:
    interactive = sys.stdin.isatty() and not args.no_input
    include_sample = bool(args.sample_customer_data)
    if args.sample_customer_data is None and interactive:
        include_sample = _prompt_yes_no(
            "Include the multi-source customer demonstration data?", default=False
        )
    if include_sample:
        return WorkbookScaffold(product_id="customer_accounts", name="Customer Accounts"), True
    default_id = safe_identifier(destination.stem)
    product_id = args.product_id or (
        safe_identifier(_prompt("Product ID", default_id)) if interactive else default_id
    )
    default_name = product_id.replace("_", " ").title()
    name = args.name or (_prompt("Product name", default_name) if interactive else default_name)
    domain = args.domain
    purpose = args.purpose
    owner = args.owner
    model = args.model
    if interactive:
        domain = domain if domain is not None else (_prompt("Domain (optional)") or None)
        purpose = purpose if purpose is not None else (_prompt("Purpose (optional)") or None)
        owner = owner if owner is not None else (_prompt("Owner (optional)") or None)
        if model is None and _prompt_yes_no(
            "Create the first output-model row now?", default=False
        ):
            model = safe_identifier(_prompt("Model ID", f"stg_{product_id}"))
    return (
        WorkbookScaffold(
            product_id=product_id,
            name=name,
            version=args.product_version,
            status=args.status,
            domain=domain,
            purpose=purpose,
            owner=owner,
            initial_model=safe_identifier(model) if model else None,
            adapter=args.adapter,
            target_schema=args.target_schema,
            toolkit_revision=args.toolkit_revision,
        ),
        include_sample,
    )


def _source(arguments: argparse.Namespace) -> tuple[Path, ImportFormat]:
    if getattr(arguments, "from_contract", None):
        return Path(arguments.from_contract).resolve(), ImportFormat.ODCS
    if getattr(arguments, "from_ddl", None):
        return Path(arguments.from_ddl).resolve(), ImportFormat.DDL
    return Path(arguments.from_dbt_manifest).resolve(), ImportFormat.DBT_MANIFEST


def _init(args: argparse.Namespace, app: ToolkitApplication) -> ApplicationResult:
    destination = Path(args.output).resolve()
    scaffold, include_sample = _workbook_answers(args, destination)
    return app.build_workbook(
        destination,
        scaffold,
        include_customer_sample=include_sample,
        force=args.force,
    )


def _new(args: argparse.Namespace, app: ToolkitApplication) -> ApplicationResult:
    return app.scaffold_project(Path(args.project_dir).resolve(), force=args.force)


def _workbook_import(args: argparse.Namespace, app: ToolkitApplication) -> ApplicationResult:
    source, source_format = _source(args)
    return app.import_workbook(
        Path(args.output).resolve(),
        source,
        source_format,
        product_id=args.product_id,
        product_name=args.name,
        toolkit_revision=args.toolkit_revision,
        identity_mappings=args.identity_mappings,
        force=args.force,
    )


def _workbook_sync(args: argparse.Namespace, app: ToolkitApplication) -> ApplicationResult:
    source, source_format = _source(args)
    return app.sync_workbook(
        Path(args.workbook).resolve(),
        source,
        source_format,
        product_id=args.product_id,
        product_name=args.name,
        replace_schema=args.replace_schema,
        identity_mappings=args.identity_mappings,
    )


def _workbook_refresh(args: argparse.Namespace, app: ToolkitApplication) -> ApplicationResult:
    return app.refresh_workbook(Path(args.workbook).resolve())


def _source_import(args: argparse.Namespace, app: ToolkitApplication) -> ApplicationResult:
    source, source_format = _source(args)
    return app.import_source(
        Path(args.workbook).resolve(),
        source,
        source_format,
        relation=args.relation,
        source_name=args.source_name,
        replace_existing=args.replace,
    )


def _validate(args: argparse.Namespace, app: ToolkitApplication) -> ApplicationResult:
    return app.validate(Path(args.workbook).resolve())


def _compile(args: argparse.Namespace, app: ToolkitApplication) -> ApplicationResult:
    return app.compile(
        Path(args.workbook).resolve(),
        Path(args.output_dir).resolve(),
        dry_run=args.dry_run,
        force=args.force,
        prune=args.prune,
    )


def _generate(args: argparse.Namespace, app: ToolkitApplication) -> ApplicationResult:
    return app.generate(
        Path(args.workbook).resolve(),
        Path(args.project_dir).resolve(),
        dry_run=args.dry_run,
        force=args.force,
        prune=args.prune,
    )


def _check(args: argparse.Namespace, app: ToolkitApplication) -> ApplicationResult:
    return app.check(
        Path(args.workbook).resolve(),
        Path(args.project_dir).resolve(),
        skip_dbt=args.skip_dbt,
        skip_sqlfluff=args.skip_sqlfluff,
    )


def _lint(args: argparse.Namespace, app: ToolkitApplication) -> ApplicationResult:
    return app.lint(Path(args.project_dir).resolve())


def _status(args: argparse.Namespace, app: ToolkitApplication) -> ApplicationResult:
    return app.status(
        Path(args.workbook).resolve(),
        Path(args.project_dir).resolve(),
        prune=args.prune,
    )


def _prove(args: argparse.Namespace, app: ToolkitApplication) -> ApplicationResult:
    return app.prove(
        Path(args.workbook).resolve(),
        Path(args.project_dir).resolve(),
        run_evaluator=not args.skip_evaluator,
        local_package_root=(
            Path(args.local_package_root).resolve() if args.local_package_root else None
        ),
    )


def _quickstart(args: argparse.Namespace, app: ToolkitApplication) -> ApplicationResult:
    steps = (
        "Quickstart path to your first working product:\n"
        "  det new customer_360\n"
        "  cd customer_360\n"
        "  det prove data_product.xlsx --project-dir .\n\n"
        "The scaffold contains a validated workbook and a complete reviewable dbt project."
    )
    return ApplicationResult.success(steps)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="det",
        description="Compile controlled Excel data products to ODCS and dbt.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser(
        "init",
        help="Create a starter workbook and get to a working first result quickly",
    )
    _add_workbook_build_arguments(init)
    init.set_defaults(handler=_init, sample_customer_data=True)

    new = commands.add_parser(
        "new",
        help="Create a complete starter workbook and generated dbt project",
    )
    new.add_argument("project_dir")
    new.add_argument("--force", action="store_true")
    new.set_defaults(handler=_new)

    quickstart = commands.add_parser(
        "quickstart",
        help="Print the fastest path from blank workbook to generated dbt project",
    )
    quickstart.set_defaults(handler=_quickstart)

    workbook = commands.add_parser("workbook", help="Controlled workbook commands")
    workbook_commands = workbook.add_subparsers(dest="workbook_command", required=True)
    workbook_build = workbook_commands.add_parser(
        "build",
        help=f"Answer a short questionnaire and build a safe v{COMPILER_VERSION} workbook",
    )
    _add_workbook_build_arguments(workbook_build)
    workbook_build.set_defaults(handler=_init)

    workbook_import = workbook_commands.add_parser(
        "import", help="Create a DET workbook from ODCS, SQL DDL, or a dbt manifest"
    )
    _add_structural_import_arguments(workbook_import, output=True)
    workbook_import.add_argument("--force", action="store_true")
    workbook_import.set_defaults(handler=_workbook_import)

    workbook_sync = workbook_commands.add_parser(
        "sync", help="Merge changed external structures while preserving DET mappings"
    )
    _add_structural_import_arguments(workbook_sync, output=False)
    workbook_sync.add_argument(
        "--replace-schema",
        action="store_true",
        help="Remove target fields absent from the imported structure after review",
    )
    workbook_sync.set_defaults(handler=_workbook_sync)

    workbook_refresh = workbook_commands.add_parser(
        "refresh", help="Refresh contextual dropdowns and compiler metadata"
    )
    workbook_refresh.add_argument("workbook")
    workbook_refresh.set_defaults(handler=_workbook_refresh)

    source = commands.add_parser("source", help="Source-schema import commands")
    source_commands = source.add_subparsers(dest="source_command", required=True)
    source_import = source_commands.add_parser(
        "import", help="Import source columns into DET Source Schema"
    )
    source_import.add_argument("--workbook", required=True)
    import_group = source_import.add_mutually_exclusive_group(required=True)
    import_group.add_argument("--from-dbt-manifest")
    import_group.add_argument("--from-contract")
    import_group.add_argument("--from-ddl")
    source_import.add_argument("--relation")
    source_import.add_argument("--source-name", default="imported")
    source_import.add_argument("--replace", action="store_true")
    source_import.set_defaults(handler=_source_import)

    validate = commands.add_parser("validate", help="Validate workbook structure and semantics")
    validate.add_argument("workbook")
    validate.set_defaults(handler=_validate)

    compile_parser = commands.add_parser("compile", help="Compile canonical ODCS and DET YAML")
    compile_parser.add_argument("workbook")
    compile_parser.add_argument("--output-dir", required=True)
    _add_generation_flags(compile_parser)
    compile_parser.set_defaults(handler=_compile)

    generate = commands.add_parser("generate", help="Generate contracts and complete dbt project")
    generate.add_argument("workbook")
    generate.add_argument("--project-dir", required=True)
    _add_generation_flags(generate)
    generate.set_defaults(handler=_generate)

    check = commands.add_parser(
        "check", help="Run workbook, ODCS, sync, dbt parse, and SQLFluff checks"
    )
    check.add_argument("workbook")
    check.add_argument("--project-dir", required=True)
    check.add_argument("--skip-dbt", action="store_true")
    check.add_argument("--skip-sqlfluff", action="store_true")
    check.set_defaults(handler=_check)

    lint = commands.add_parser("lint", help="Lint generated SQL with SQLFluff's dbt templater")
    lint.add_argument("--project-dir", required=True)
    lint.set_defaults(handler=_lint)

    status = commands.add_parser("status", help="Report workbook changes or generated-file drift")
    status.add_argument("workbook")
    status.add_argument("--project-dir", required=True)
    status.add_argument("--prune", action="store_true")
    status.set_defaults(handler=_status)

    prove = commands.add_parser(
        "prove", help="Run isolated contract sync, dbt build, tests, and evaluation"
    )
    prove.add_argument("workbook")
    prove.add_argument("--project-dir", required=True)
    prove.add_argument("--skip-evaluator", action="store_true")
    prove.add_argument("--local-package-root", help=argparse.SUPPRESS)
    prove.set_defaults(handler=_prove)
    return parser


def _add_generation_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--prune", action="store_true")


def _add_workbook_build_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("output")
    parser.add_argument("--product-id")
    parser.add_argument("--name")
    parser.add_argument("--product-version", default=DEFAULT_DATA_PRODUCT_VERSION)
    parser.add_argument("--status", default="draft")
    parser.add_argument("--domain")
    parser.add_argument("--purpose")
    parser.add_argument("--owner")
    parser.add_argument("--model", help="Optionally create the first output-model row")
    parser.add_argument("--adapter", default="duckdb")
    parser.add_argument("--target-schema", default="main")
    parser.add_argument("--toolkit-revision", default=DEFAULT_TOOLKIT_REVISION)
    sample = parser.add_mutually_exclusive_group()
    sample.add_argument(
        "--sample-customer-data",
        action="store_true",
        default=None,
        help="Explicitly opt in to the Customer 360 demonstration",
    )
    sample.add_argument(
        "--no-sample-data",
        dest="sample_customer_data",
        action="store_false",
        help="Create only the questionnaire answers (the default)",
    )
    parser.add_argument("--no-input", action="store_true", help="Use flags and safe defaults")
    parser.add_argument("--force", action="store_true")
    parser.set_defaults(handler=_init)


def _add_structural_import_arguments(parser: argparse.ArgumentParser, *, output: bool) -> None:
    parser.add_argument("output" if output else "workbook")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--from-contract", help="Existing ODCS YAML or standard ODCS Excel")
    source.add_argument("--from-ddl", help="SQL file containing CREATE TABLE statements")
    source.add_argument("--from-dbt-manifest", help="dbt target/manifest.json")
    parser.add_argument("--product-id", help="Product ID for DDL imports")
    parser.add_argument("--name", help="Product name for DDL imports")
    parser.add_argument("--toolkit-revision", default=DEFAULT_TOOLKIT_REVISION)
    parser.add_argument(
        "--identity-mappings",
        action="store_true",
        help="Opt in to source rows and Copy value mappings for every field",
    )


def main(argv: list[str] | None = None, application: ToolkitApplication | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    app = application or ToolkitApplication()
    try:
        return _present(args.handler(args, app))
    except ToolkitValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ToolkitDependencyError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except ToolkitServiceError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (ValueError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
