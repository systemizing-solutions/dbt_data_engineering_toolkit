"""Unified imported structure and source-format parsers."""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass, field, replace
from enum import StrEnum
from pathlib import Path

import yaml

from ...brokers.datacontracts import CliDataContractBroker, DataContractBroker
from ...brokers.files import FileBroker, LocalFileBroker
from ...errors import DataContractExecutionError
from ..validation.common import canonical_type


class StructureFormat(StrEnum):
    ODCS = "odcs"
    DDL = "ddl"
    DBT_MANIFEST = "dbt_manifest"


@dataclass(frozen=True, slots=True)
class ImportedColumn:
    relation: str
    name: str
    logical_type: str
    physical_type: str | None = None
    nullable: bool = True
    unique: bool = False
    primary_key: bool = False
    description: str | None = None
    classification: str | None = None
    raw_property: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class ImportedSource:
    relation: str
    source_name: str
    table_name: str
    database: str | None = None
    schema_name: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class ImportedModel:
    name: str
    columns: list[ImportedColumn]
    physical_name: str | None = None
    description: str | None = None
    materialization: str = "view"
    layer: str = "staging"
    grain: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    raw_schema: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class ImportedProduct:
    product_id: str
    name: str
    version: str = "1.0.0"
    status: str = "draft"
    domain: str | None = None
    description: str | None = None
    owner: str | None = None
    contract_id: str | None = None
    raw_contract: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class ImportedDataStructure:
    """Format-neutral result parsed once and applied as source or target data."""

    product: ImportedProduct
    models: list[ImportedModel] = field(default_factory=list)
    sources: list[ImportedSource] = field(default_factory=list)
    columns: list[ImportedColumn] = field(default_factory=list)

    def as_source(
        self,
        *,
        relation: str | None = None,
        source_name: str | None = None,
    ) -> tuple[list[ImportedSource], list[ImportedColumn]]:
        if relation and len(self.sources) != 1:
            raise ValueError("--relation can only be used when the input contains one object")
        relation_map = {
            item.relation: safe_identifier(relation) if relation else item.relation
            for item in self.sources
        }
        sources = [
            replace(
                item,
                relation=relation_map[item.relation],
                source_name=safe_identifier(source_name) if source_name else item.source_name,
            )
            for item in self.sources
        ]
        columns = [
            replace(item, relation=relation_map.get(item.relation, item.relation))
            for item in self.columns
        ]
        return sources, columns

    def as_target(self) -> tuple[ImportedProduct, list[ImportedModel]]:
        if not self.models:
            raise ValueError("input contains no target model structures")
        return self.product, self.models


def safe_identifier(value: str) -> str:
    result = re.sub(r"[^a-z0-9_]+", "_", value.strip().casefold()).strip("_")
    if result and result[0].isdigit():
        result = f"source_{result}"
    return result


def safe_field_identifier(value: str) -> str:
    result = re.sub(r"[^a-z0-9_]+", "_", value.strip().casefold()).rstrip("_")
    if result and result[0].isdigit():
        result = f"field_{result}"
    return result


def physical_to_logical(value: str | None) -> str:
    return canonical_type(value) if value else "string"


def _mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _mappings(value: object) -> list[dict[str, object]]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _text(value: object) -> str | None:
    return str(value) if value not in (None, "") else None


def _first_present(*values: object) -> object | None:
    return next((value for value in values if value not in (None, "")), None)


class StructureImportService:
    """Dispatch to one parser for each external structure format."""

    def __init__(
        self,
        files: FileBroker | None = None,
        datacontract: DataContractBroker | None = None,
    ) -> None:
        self.files = files or LocalFileBroker()
        self.datacontract = datacontract or CliDataContractBroker()

    def load(
        self,
        path: Path,
        source_format: StructureFormat,
        *,
        product_id: str | None = None,
        product_name: str | None = None,
    ) -> ImportedDataStructure:
        if source_format == StructureFormat.ODCS:
            return self._odcs(path)
        if source_format == StructureFormat.DDL:
            return self._ddl(path, product_id=product_id, product_name=product_name)
        return self._manifest(path)

    def _odcs(self, path: Path) -> ImportedDataStructure:
        payload = yaml.safe_load(self._odcs_text(path)) or {}
        if not isinstance(payload, dict):
            raise ValueError("ODCS input must be a YAML object")
        contract_id = str(payload.get("id") or "")
        raw_product = _first_present(
            payload.get("dataProduct"),
            contract_id.rsplit(":", 1)[-1],
            payload.get("name"),
        )
        product_id = safe_identifier(str(raw_product or path.stem))
        team = payload.get("team") or []
        owner: object | None = None
        if isinstance(team, dict):
            owner = _first_present(team.get("name"), team.get("username"))
        elif isinstance(team, list) and team and isinstance(team[0], dict):
            owner = _first_present(team[0].get("name"), team[0].get("username"))
        description = _first_present(payload.get("description"), payload.get("purpose"))
        if isinstance(description, dict):
            description = _first_present(
                description.get("purpose"),
                description.get("usage"),
                description.get("limitations"),
            )
        product = ImportedProduct(
            product_id=product_id,
            name=str(payload.get("name") or product_id.replace("_", " ").title()),
            version=str(payload.get("version") or "1.0.0"),
            status=str(payload.get("status") or "draft"),
            domain=_text(payload.get("domain")),
            description=_text(description),
            owner=_text(owner),
            contract_id=contract_id or None,
            raw_contract=payload,
        )
        raw_schemas = payload.get("schema") or []
        schemas = _mappings(raw_schemas)
        models: list[ImportedModel] = []
        sources: list[ImportedSource] = []
        all_columns: list[ImportedColumn] = []
        for schema in schemas:
            if not schema.get("name"):
                continue
            name = safe_identifier(str(schema["name"]))
            columns: list[ImportedColumn] = []
            grain: list[str] = []
            for item in _mappings(schema.get("properties")):
                if not item.get("name"):
                    continue
                column_name = safe_field_identifier(str(item["name"]))
                is_key = bool(item.get("primaryKey", False))
                if is_key:
                    grain.append(column_name)
                column = ImportedColumn(
                    relation=name,
                    name=column_name,
                    logical_type=str(item.get("logicalType") or "string"),
                    physical_type=_text(item.get("physicalType")),
                    nullable=not bool(item.get("required", False)),
                    unique=bool(item.get("unique", False) or is_key),
                    primary_key=is_key,
                    description=_text(item.get("description")),
                    classification=_text(item.get("classification")),
                    raw_property=item,
                )
                columns.append(column)
                all_columns.append(column)
            physical_type = _first_present(schema.get("physicalType"), schema.get("type"))
            models.append(
                ImportedModel(
                    name=name,
                    physical_name=safe_identifier(
                        str(schema.get("physicalName") or schema["name"])
                    ),
                    description=_text(schema.get("description")),
                    materialization="table" if physical_type == "table" else "view",
                    grain=grain,
                    columns=columns,
                    raw_schema=schema,
                )
            )
            sources.append(
                ImportedSource(
                    relation=name,
                    source_name="contract",
                    table_name=safe_identifier(str(schema.get("physicalName") or schema["name"])),
                    description=_text(schema.get("description")),
                )
            )
        if not models:
            raise ValueError("ODCS input contains no schema objects")
        return ImportedDataStructure(product, models, sources, all_columns)

    def _odcs_text(self, path: Path) -> str:
        suffix = path.suffix.casefold()
        if suffix in {".yaml", ".yml"}:
            return self.files.read_text(path)
        if suffix not in {".xlsx", ".xlsm"}:
            raise ValueError("--from-contract accepts ODCS .yaml, .yml, .xlsx, or .xlsm files")
        with tempfile.TemporaryDirectory(prefix="det-odcs-import-") as temporary:
            canonical = Path(temporary) / "canonical.odcs.yaml"
            result = self.datacontract.import_excel(path, canonical)
            if not result.succeeded:
                raise DataContractExecutionError(
                    "datacontract",
                    "Data Contract CLI could not import the official ODCS Excel workbook:\n"
                    + result.output,
                    command=result.command,
                    return_code=result.return_code,
                )
            return self.files.read_text(canonical)

    def _ddl(
        self,
        path: Path,
        *,
        product_id: str | None,
        product_name: str | None,
    ) -> ImportedDataStructure:
        text = re.sub(
            r"--.*?$|/\*.*?\*/",
            "",
            self.files.read_text(path),
            flags=re.MULTILINE | re.DOTALL,
        )
        statements = _create_table_statements(text)
        if not statements:
            raise ValueError("no CREATE TABLE statement was found")
        sources: list[ImportedSource] = []
        columns: list[ImportedColumn] = []
        models: list[ImportedModel] = []
        for table_name, body in statements:
            raw_table = table_name.split(".")[-1].strip('"`[]')
            relation = safe_identifier(raw_table)
            source = ImportedSource(
                relation=relation,
                source_name="imported",
                table_name=safe_identifier(raw_table),
            )
            table_columns = _ddl_columns(relation, body)
            sources.append(source)
            columns.extend(table_columns)
            models.append(
                ImportedModel(
                    name=relation,
                    physical_name=source.table_name,
                    columns=table_columns,
                    grain=[item.name for item in table_columns if item.primary_key],
                    materialization="table",
                )
            )
        identifier = safe_identifier(product_id or path.stem)
        product = ImportedProduct(
            product_id=identifier,
            name=product_name or identifier.replace("_", " ").title(),
        )
        return ImportedDataStructure(product, models, sources, columns)

    def _manifest(self, path: Path) -> ImportedDataStructure:
        payload = json.loads(self.files.read_text(path))
        if not isinstance(payload, dict):
            raise ValueError("dbt manifest must be a JSON object")
        metadata = _mapping(payload.get("metadata"))
        project_name = str(metadata.get("project_name") or path.parent.parent.name)
        product = ImportedProduct(
            product_id=safe_identifier(project_name),
            name=project_name,
        )
        sources: list[ImportedSource] = []
        source_columns: list[ImportedColumn] = []
        for node in _mapping(payload.get("sources")).values():
            definition = _mapping(node)
            source_name = str(definition.get("source_name") or "source")
            table_name = str(definition.get("name") or definition.get("identifier") or "table")
            relation = safe_identifier(f"{source_name}_{table_name}")
            sources.append(
                ImportedSource(
                    relation=relation,
                    source_name=safe_identifier(source_name),
                    table_name=safe_identifier(table_name),
                    database=_text(definition.get("database")),
                    schema_name=_text(definition.get("schema")),
                    description=_text(definition.get("description")),
                )
            )
            for name, raw_column in _mapping(definition.get("columns")).items():
                column = _mapping(raw_column)
                physical_type = _text(column.get("data_type") or column.get("type"))
                source_columns.append(
                    ImportedColumn(
                        relation=relation,
                        name=safe_field_identifier(name),
                        logical_type=physical_to_logical(physical_type),
                        physical_type=physical_type,
                        description=_text(column.get("description")),
                    )
                )
        models: list[ImportedModel] = []
        for raw_node in _mapping(payload.get("nodes")).values():
            node = _mapping(raw_node)
            if node.get("resource_type") != "model":
                continue
            if node.get("package_name") and node.get("package_name") != project_name:
                continue
            models.append(_manifest_model(node))
        if not models:
            raise ValueError("dbt manifest contains no models from its root project")
        return ImportedDataStructure(product, models, sources, source_columns)


CREATE_TABLE_START = re.compile(
    r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?P<name>[\w.\"`\[\]]+)\s*\(",
    re.IGNORECASE,
)


def _create_table_statements(text: str) -> list[tuple[str, str]]:
    statements: list[tuple[str, str]] = []
    search_from = 0
    while match := CREATE_TABLE_START.search(text, search_from):
        depth = 1
        index = match.end()
        quote: str | None = None
        while index < len(text) and depth:
            character = text[index]
            if quote:
                if character == quote and (index == 0 or text[index - 1] != "\\"):
                    quote = None
            elif character in {"'", '"'}:
                quote = character
            elif character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
            index += 1
        if depth:
            raise ValueError(f"unterminated CREATE TABLE statement for {match.group('name')}")
        statements.append((match.group("name"), text[match.end() : index - 1]))
        search_from = index
    return statements


def _split_columns(body: str) -> list[str]:
    rows: list[str] = []
    current: list[str] = []
    depth = 0
    quote: str | None = None
    previous = ""
    for character in body:
        if quote:
            if character == quote and previous != "\\":
                quote = None
        elif character in {"'", '"'}:
            quote = character
        elif character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
        if character == "," and depth == 0 and quote is None:
            rows.append("".join(current).strip())
            current = []
        else:
            current.append(character)
        previous = character
    if current:
        rows.append("".join(current).strip())
    return rows


def _ddl_columns(relation: str, body: str) -> list[ImportedColumn]:
    definitions = _split_columns(body)
    unique: set[str] = set()
    primary_keys: set[str] = set()
    for definition in definitions:
        key_match = re.search(
            r"\b(?P<kind>primary\s+key|unique)\s*\((?P<columns>[^)]+)\)",
            definition,
            re.IGNORECASE,
        )
        if key_match:
            names = {
                safe_field_identifier(item.strip(' "`[]'))
                for item in key_match.group("columns").split(",")
            }
            if key_match.group("kind").casefold().startswith("primary"):
                primary_keys.update(names)
            if len(names) == 1:
                unique.update(names)
    columns: list[ImportedColumn] = []
    for definition in definitions:
        if re.match(
            r"^(constraint|primary\s+key|foreign\s+key|unique|check)\b",
            definition,
            re.IGNORECASE,
        ):
            continue
        match = re.match(
            r'^["`\[]?(?P<name>[\w]+)["`\]]?\s+(?P<type>[\w]+(?:\s*\([^)]*\))?)',
            definition,
        )
        if not match:
            continue
        physical_type = match.group("type").strip()
        name = safe_field_identifier(match.group("name"))
        primary_key = name in primary_keys or bool(
            re.search(r"\bprimary\s+key\b", definition, re.IGNORECASE)
        )
        is_unique = (
            name in unique
            or bool(re.search(r"\bunique\b", definition, re.IGNORECASE))
            or (primary_key and len(primary_keys) <= 1)
        )
        columns.append(
            ImportedColumn(
                relation=relation,
                name=name,
                logical_type=physical_to_logical(physical_type),
                physical_type=physical_type,
                nullable=not (
                    primary_key or bool(re.search(r"\bnot\s+null\b", definition, re.IGNORECASE))
                ),
                unique=is_unique,
                primary_key=primary_key,
            )
        )
    return columns


def _manifest_model(node: dict[str, object]) -> ImportedModel:
    name = safe_identifier(str(node.get("name") or "model"))
    columns: list[ImportedColumn] = []
    grain: list[str] = []
    for column_name, raw_definition in _mapping(node.get("columns")).items():
        definition = _mapping(raw_definition)
        data_type = _text(definition.get("data_type") or definition.get("type"))
        constraints = _mappings(definition.get("constraints"))
        is_key = any(item.get("type") == "primary_key" for item in constraints)
        safe_name = safe_field_identifier(column_name)
        if is_key:
            grain.append(safe_name)
        columns.append(
            ImportedColumn(
                relation=name,
                name=safe_name,
                logical_type=physical_to_logical(data_type),
                physical_type=data_type,
                nullable=not any(item.get("type") == "not_null" for item in constraints),
                unique=is_key,
                primary_key=is_key,
                description=_text(definition.get("description")),
            )
        )
    dependencies: list[str] = []
    depends_on = _mapping(node.get("depends_on"))
    raw_dependencies = depends_on.get("nodes") or []
    if isinstance(raw_dependencies, list):
        for unique_id in raw_dependencies:
            parts = str(unique_id).split(".")
            if parts[0] == "model" and len(parts) >= 3:
                dependencies.append(safe_identifier(parts[-1]))
            elif parts[0] == "source" and len(parts) >= 4:
                dependencies.append(safe_identifier(f"{parts[-2]}_{parts[-1]}"))
    config = _mapping(node.get("config"))
    materialization = str(config.get("materialized") or "view")
    if materialization not in {"view", "table", "ephemeral"}:
        materialization = "view"
    return ImportedModel(
        name=name,
        physical_name=safe_identifier(str(node.get("alias") or name)),
        description=_text(node.get("description")),
        materialization=materialization,
        grain=grain,
        inputs=list(dict.fromkeys(dependencies)),
        columns=columns,
    )
