"""Reusable application orchestration behind thin exposers."""

from __future__ import annotations

import re
import shlex
from dataclasses import replace
from pathlib import Path

from ..adapters import AdapterRegistry
from ..brokers.datacontracts import CliDataContractBroker, DataContractBroker
from ..brokers.dependencies import (
    CliDbtBroker,
    CliSqlFluffBroker,
    DbtBroker,
    SqlFluffBroker,
)
from ..brokers.files import FileBroker, LocalFileBroker
from ..brokers.projects import LocalProjectWorkspaceBroker, ProjectWorkspaceBroker
from ..brokers.target_workbooks import (
    OpenpyxlTargetWorkbookBroker,
    TargetWorkbookBroker,
)
from ..brokers.template_workbooks import (
    OpenpyxlTemplateWorkbookBroker,
    TemplateWorkbookBroker,
    WorkbookScaffold,
)
from ..brokers.workbook_edits import (
    OpenpyxlWorkbookEditBroker,
    SourceWorkbookEditBroker,
)
from ..errors import MissingDependencyError
from ..generation import apply_changes, plan_changes, sha256_bytes
from ..models import DataProductSpecification
from ..operational import ApplicationResult, Artifact, CommandResult
from ..prove import ProjectProofService
from ..registry import OperatorRegistry
from ..version import COMPILER_VERSION, DEFAULT_TOOLKIT_REVISION
from .emissions.service import EmissionService
from .generation import ProjectGenerationService
from .imports.structures import StructureFormat, StructureImportService
from .validation.service import SpecificationValidationService
from .workbooks.service import WorkbookInterpretationService

ImportFormat = StructureFormat


def safe_identifier(value: str) -> str:
    result = re.sub(r"[^a-z0-9_]+", "_", value.strip().casefold()).strip("_")
    if not result:
        return "data_product"
    return f"product_{result}" if result[0].isdigit() else result


class ToolkitApplication:
    """Application entry point shared by CLI and future exposers."""

    def __init__(
        self,
        *,
        files: FileBroker | None = None,
        registry: OperatorRegistry | None = None,
        adapters: AdapterRegistry | None = None,
        emissions: EmissionService | None = None,
        validator: SpecificationValidationService | None = None,
        dbt: DbtBroker | None = None,
        sqlfluff: SqlFluffBroker | None = None,
        datacontract: DataContractBroker | None = None,
        imports: StructureImportService | None = None,
        templates: TemplateWorkbookBroker | None = None,
        source_workbooks: SourceWorkbookEditBroker | None = None,
        target_workbooks: TargetWorkbookBroker | None = None,
        projects: ProjectWorkspaceBroker | None = None,
        workbooks: WorkbookInterpretationService | None = None,
    ) -> None:
        self.files = files or LocalFileBroker()
        self.registry = registry or OperatorRegistry.load()
        self.adapters = adapters or AdapterRegistry.default()
        self.emissions = emissions or EmissionService(
            registry=self.registry,
            adapters=self.adapters,
        )
        self.validator = validator or SpecificationValidationService(
            self.registry,
            self.adapters,
        )
        self.dbt = dbt or CliDbtBroker()
        self.sqlfluff = sqlfluff or CliSqlFluffBroker()
        self.datacontract = datacontract or CliDataContractBroker()
        self.imports = imports or StructureImportService(self.files, self.datacontract)
        self.templates = templates or OpenpyxlTemplateWorkbookBroker()
        self.source_workbooks = source_workbooks or OpenpyxlWorkbookEditBroker()
        self.target_workbooks = target_workbooks or OpenpyxlTargetWorkbookBroker()
        self.projects = projects or LocalProjectWorkspaceBroker()
        self.workbooks = workbooks or WorkbookInterpretationService()
        self.generation = ProjectGenerationService(
            files=self.files,
            projects=self.projects,
            datacontract=self.datacontract,
            registry=self.registry,
            adapters=self.adapters,
        )

    def build_workbook(
        self,
        destination: Path,
        scaffold: WorkbookScaffold,
        *,
        include_customer_sample: bool = False,
        force: bool = False,
    ) -> ApplicationResult:
        self.templates.build(
            destination,
            scaffold=scaffold,
            include_customer_sample=include_customer_sample,
            force=force,
        )
        kind = "Customer 360 demonstration" if include_customer_sample else "production-safe blank"
        return ApplicationResult.success(f"Created {kind} workbook: {destination}")

    def scaffold_project(self, destination: Path, *, force: bool = False) -> ApplicationResult:
        if self.files.exists(destination) and not force:
            return ApplicationResult.failure(
                f"Refusing to overwrite {destination}; pass --force after review.",
                exit_code=2,
            )
        workbook = destination / "data_product.xlsx"
        scaffold = WorkbookScaffold(product_id="customer_accounts", name="Customer Accounts")
        self.templates.build(
            workbook,
            scaffold=scaffold,
            include_customer_sample=True,
            force=force,
        )
        validation = self.validate(workbook)
        generation = self.generate(workbook, destination, force=force)
        self.files.write_text_atomic(
            destination / "seeds" / "raw_customers.csv",
            "customer_id,account_id,customer_name,email,status_code\n"
            "C001,A001, alice smith ,alice@example.com,A\n"
            "C002,A002,bob jones,not-an-email,I\n"
            "C003,A003,carol diaz,carol@example.com,A\n",
        )
        self.files.write_text_atomic(
            destination / "seeds" / "raw_accounts.csv",
            "account_id,account_tier,lifetime_value\n"
            "A001,gold,1250.50\n"
            "A002,silver,-25.00\n"
            "A003,bronze,300.00\n",
        )
        return ApplicationResult.success(
            f"Created starter data product: {destination}",
            *validation.messages,
            *generation.messages,
            f"Next: cd {shlex.quote(str(destination))} "
            "&& det prove data_product.xlsx --project-dir .",
        )

    def refresh_workbook(self, workbook: Path) -> ApplicationResult:
        self.templates.refresh(workbook)
        return ApplicationResult.success(
            f"Refreshed contextual dropdowns and v{COMPILER_VERSION} metadata in {workbook}"
        )

    def import_workbook(
        self,
        destination: Path,
        source: Path,
        source_format: ImportFormat,
        *,
        product_id: str | None = None,
        product_name: str | None = None,
        toolkit_revision: str = DEFAULT_TOOLKIT_REVISION,
        identity_mappings: bool = False,
        force: bool = False,
    ) -> ApplicationResult:
        if self.files.exists(destination) and not force:
            return ApplicationResult.failure(
                f"Refusing to overwrite {destination}; pass --force after review.",
                exit_code=2,
            )
        structure = self.imports.load(
            source,
            source_format,
            product_id=product_id or safe_identifier(destination.stem),
            product_name=product_name,
        )
        product, models = structure.as_target()
        scaffold = WorkbookScaffold(
            product_id=product.product_id,
            name=product.name,
            version=product.version,
            status=product.status,
            domain=product.domain,
            purpose=product.description,
            owner=product.owner,
            toolkit_revision=toolkit_revision,
        )
        self.templates.build(destination, scaffold, force=force)
        self.target_workbooks.apply(
            destination,
            product,
            models,
            replace_schema=True,
            identity_mappings=identity_mappings,
        )
        if source_format == ImportFormat.DBT_MANIFEST:
            sources, columns = structure.as_source()
            self.source_workbooks.apply_sources(destination, sources, columns)
        state = (
            "identity mappings were added."
            if identity_mappings
            else "mapping sheets remain reviewable and empty."
        )
        return ApplicationResult.success(
            f"Imported {len(models)} target structure(s) into {destination}; {state}"
        )

    def sync_workbook(
        self,
        workbook: Path,
        source: Path,
        source_format: ImportFormat,
        *,
        product_id: str | None = None,
        product_name: str | None = None,
        replace_schema: bool = False,
        identity_mappings: bool = False,
    ) -> ApplicationResult:
        current_metadata = None
        if source_format == ImportFormat.DDL and not product_id:
            current_metadata = self.workbooks.load(workbook).metadata
            product_id = current_metadata.product_id
            product_name = product_name or current_metadata.name
        structure = self.imports.load(
            source,
            source_format,
            product_id=product_id or safe_identifier(workbook.stem),
            product_name=product_name,
        )
        product, models = structure.as_target()
        if current_metadata is not None:
            product = replace(
                product,
                version=current_metadata.version,
                status=current_metadata.status,
                domain=current_metadata.domain,
                description=current_metadata.description,
                owner=current_metadata.owner,
                contract_id=current_metadata.contract_id,
            )
        self.target_workbooks.apply(
            workbook,
            product,
            models,
            replace_schema=replace_schema,
            identity_mappings=identity_mappings,
        )
        if source_format == ImportFormat.DBT_MANIFEST:
            sources, columns = structure.as_source()
            self.source_workbooks.apply_sources(
                workbook,
                sources,
                columns,
                replace=replace_schema,
            )
        mode = "Replaced" if replace_schema else "Merged"
        return ApplicationResult.success(
            f"{mode} {len(models)} target structure(s) into {workbook}; existing "
            "DET Mapping, Parameters, Operational Validation, and Lookups were preserved."
        )

    def import_source(
        self,
        workbook: Path,
        source: Path,
        source_format: ImportFormat,
        *,
        relation: str | None = None,
        source_name: str = "imported",
        replace_existing: bool = False,
    ) -> ApplicationResult:
        structure = self.imports.load(source, source_format)
        sources, columns = structure.as_source(
            relation=relation,
            source_name=source_name if source_format == ImportFormat.DDL else None,
        )
        self.source_workbooks.apply_sources(
            workbook,
            sources,
            columns,
            replace=replace_existing,
        )
        return ApplicationResult.success(
            f"Imported {len(columns)} source field(s) across {len(sources)} relation(s) into {workbook}"
        )

    def validate(self, workbook: Path) -> ApplicationResult:
        spec = self.workbooks.load(workbook)
        warnings = self.validator.validate(spec)
        return ApplicationResult.success(
            *(item.render() for item in warnings),
            f"Valid: {spec.metadata.name} ({len(spec.models)} models, "
            f"{len(spec.mappings)} mapped columns, {len(spec.rules)} rules)",
        )

    def compile(
        self,
        workbook: Path,
        output: Path,
        *,
        dry_run: bool = False,
        force: bool = False,
        prune: bool = False,
    ) -> ApplicationResult:
        spec = self._validated(workbook)
        return self._write(
            workbook,
            output,
            self.emissions.emit_contracts(spec),
            dry_run=dry_run,
            force=force,
            prune=prune,
        )

    def generate(
        self,
        workbook: Path,
        project: Path,
        *,
        dry_run: bool = False,
        force: bool = False,
        prune: bool = False,
    ) -> ApplicationResult:
        spec = self._validated(workbook)
        plan = self.generation.plan_or_publish(
            workbook=workbook,
            project=project,
            spec=spec,
            compiler_artifacts=self.emissions.emit_all(spec),
            publish=not dry_run,
            force=force,
            prune=prune,
        )
        messages = [f"{change.action:9} {change.path.as_posix()}" for change in plan.changes]
        if not dry_run:
            count = sum(item.action != "unchanged" for item in plan.changes)
            messages.append(
                f"Generated and contract-synchronized {count} change(s) atomically in {project}"
            )
        return ApplicationResult.success(*messages)

    def check(
        self,
        workbook: Path,
        project: Path,
        *,
        skip_dbt: bool = False,
        skip_sqlfluff: bool = False,
    ) -> ApplicationResult:
        spec = self._validated(workbook)
        contract = project / "contracts" / f"{spec.metadata.product_id}.odcs.yaml"
        if not self.files.exists(contract):
            return ApplicationResult.failure(
                f"Missing {contract}; run `det generate` first.",
                exit_code=2,
            )
        messages: list[str] = []
        for label, result in (
            ("Data Contract lint", self.datacontract.lint(contract)),
            (
                "Data Contract dbt sync dry-run",
                self.datacontract.dbt_sync(contract, project, dry_run=True),
            ),
        ):
            messages.append(f"{label}:\n{result.output}".rstrip())
            if not result.succeeded:
                return ApplicationResult.failure(*messages)
        if not skip_dbt:
            result = self.dbt.parse(project)
            messages.append(f"dbt parse:\n{result.output}".rstrip())
            if not result.succeeded:
                return ApplicationResult.failure(*messages)
        if not skip_sqlfluff:
            result = self._lint_result(project)
            messages.append(f"SQLFluff:\n{result.output}".rstrip())
            if not result.succeeded:
                return ApplicationResult.failure(*messages)
        return ApplicationResult.success(*messages)

    def lint(self, project: Path) -> ApplicationResult:
        result = self._lint_result(project)
        return (
            ApplicationResult.success(result.output)
            if result.succeeded
            else ApplicationResult.failure(result.output)
        )

    def status(self, workbook: Path, project: Path, *, prune: bool = False) -> ApplicationResult:
        spec = self._validated(workbook)
        plan = self.generation.plan_or_publish(
            workbook=workbook,
            project=project,
            spec=spec,
            compiler_artifacts=self.emissions.emit_all(spec),
            publish=False,
            prune=prune,
        )
        changes = plan.changes
        changed = [item for item in changes if item.action != "unchanged"]
        if not changed:
            return ApplicationResult.success(
                "In sync: workbook, generated files, and DET manifest agree."
            )
        messages = [f"{item.action:9} {item.path.as_posix()}" for item in changed]
        messages.append(f"Out of sync: {len(changed)} generated change(s) are required.")
        return ApplicationResult(exit_code=1, messages=tuple(messages))

    def prove(
        self,
        workbook: Path,
        project: Path,
        *,
        run_evaluator: bool = True,
        local_package_root: Path | None = None,
    ) -> ApplicationResult:
        spec = self._validated(workbook)
        plan = self.generation.plan_or_publish(
            workbook=workbook,
            project=project,
            spec=spec,
            compiler_artifacts=self.emissions.emit_all(spec),
            publish=False,
        )
        changes = plan.changes
        stale = [item for item in changes if item.action != "unchanged"]
        if stale:
            return ApplicationResult.failure(
                "Generated project is stale; run `det generate` before `det prove`.",
                *(f"{item.action:9} {item.path.as_posix()}" for item in stale),
                exit_code=2,
            )
        contract = Path("contracts") / f"{spec.metadata.product_id}.odcs.yaml"
        passed, messages = ProjectProofService(
            files=self.files,
            dbt=self.dbt,
            sqlfluff=self.sqlfluff,
            datacontract=self.datacontract,
        ).prove(
            project,
            contract,
            run_evaluator=run_evaluator,
            local_package_root=local_package_root,
        )
        if passed:
            messages.append(
                "Proof passed: contract sync, dbt execution, tests, and evaluator completed in isolation."
            )
            return ApplicationResult.success(*messages)
        return ApplicationResult.failure(*messages)

    def _validated(self, workbook: Path) -> DataProductSpecification:
        spec = self.workbooks.load(workbook)
        self.validator.validate(spec)
        return spec

    def _write(
        self,
        workbook: Path,
        output: Path,
        artifacts: list[Artifact],
        *,
        dry_run: bool,
        force: bool,
        prune: bool,
    ) -> ApplicationResult:
        changes, manifest = plan_changes(
            output,
            artifacts,
            force=force,
            prune=prune,
            file_broker=self.files,
        )
        messages = [f"{change.action:9} {change.path.as_posix()}" for change in changes]
        if not dry_run:
            self.files.ensure_directory(output)
            apply_changes(
                output,
                artifacts,
                changes,
                manifest,
                sha256_bytes(self.files.read_bytes(workbook)),
                file_broker=self.files,
            )
            count = sum(item.action != "unchanged" for item in changes)
            messages.append(f"Generated {count} change(s) in {output}")
        return ApplicationResult.success(*messages)

    def _lint_result(self, project: Path) -> CommandResult:
        config = project / ".sqlfluff"
        if not self.files.exists(config):
            raise MissingDependencyError(
                "sqlfluff-configuration",
                f"Missing {config}; regenerate this V{COMPILER_VERSION} project.",
            )
        return self.sqlfluff.lint(project)
