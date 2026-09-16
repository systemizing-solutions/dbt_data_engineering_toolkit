"""Interpret product metadata and official schema sheets."""

from __future__ import annotations

import json
from collections.abc import Mapping

from ...brokers.workbooks import CellValue
from ...models import ProductMetadata, SchemaImplementation, SchemaProperty
from ...operational import JsonValue
from ...registry import OperatorRegistry
from ...version import (
    DEFAULT_DATA_PRODUCT_VERSION,
    OPERATOR_REGISTRY_VERSION,
    WORKBOOK_SCHEMA_VERSION,
)
from .common import (
    WorkbookParseContext,
    boolean,
    contract_product_id,
    key_values,
    optional,
    optional_text,
    rows,
    schema_sheet_names,
    slug,
)

LOGICAL_OPTION_FIELDS = {
    "Maximum Items": "maximumItems",
    "Minimum Items": "minimumItems",
    "Unique Items": "uniqueItems",
    "Format": "format",
    "Minimum Length": "minLength",
    "Maximum Length": "maxLength",
    "Exclusive Minimum": "exclusiveMinimum",
    "Minimum": "minimum",
    "Exclusive Maximum": "exclusiveMaximum",
    "Maximum": "maximum",
    "Multiple Of": "multipleOf",
    "Minimum Properties": "minProperties",
    "Maximum Properties": "maxProperties",
    "Required Properties": "requiredProperties",
    "Pattern": "pattern",
}
PROPERTY_FIELDS = {
    "Business Name": "businessName",
    "Example(s)": "examples",
    "Tags": "tags",
    "Physical Name": "physicalName",
    "Primary Key Position": "primaryKeyPosition",
    "Partitioned": "partitioned",
    "Partition Key Position": "partitionKeyPosition",
    "Encrypted Name": "encryptedName",
    "Transform Sources": "transformSourceObjects",
    "Transform Logic": "transformLogic",
    "Transform Description": "transformDescription",
    "Critical Data Element Status": "criticalDataElement",
}


def _json_compatible(value: CellValue) -> JsonValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _advanced_property_fields(row: Mapping[str, CellValue]) -> dict[str, JsonValue]:
    result: dict[str, JsonValue] = {}
    for header, key in PROPERTY_FIELDS.items():
        value = optional(row.get(header))
        if value is None:
            continue
        if key in {"examples", "tags", "transformSourceObjects", "requiredProperties"}:
            result[key] = [item.strip() for item in str(value).split(",") if item.strip()]
        else:
            result[key] = _json_compatible(value)
    url = optional(row.get("Authoritative Definition URL"))
    if url is not None:
        definition: dict[str, JsonValue] = {"url": str(url)}
        definition_type = optional(row.get("Authoritative Definition Type"))
        if definition_type is not None:
            definition["type"] = str(definition_type)
        result["authoritativeDefinitions"] = [definition]
    logical_options: dict[str, JsonValue] = {}
    for header, key in LOGICAL_OPTION_FIELDS.items():
        value = optional(row.get(header))
        if value is not None:
            logical_options[key] = _json_compatible(value)
    if logical_options:
        result["logicalTypeOptions"] = logical_options
    return result


class ProductSchemaInterpreter:
    def interpret(
        self, context: WorkbookParseContext
    ) -> tuple[ProductMetadata, list[SchemaProperty]]:
        workbook = context.workbook
        metadata = key_values(workbook.sheet("_DET Metadata"))
        template_version = slug(metadata.get("template_version"))
        if template_version != WORKBOOK_SCHEMA_VERSION:
            context.add(
                "_DET Metadata",
                None,
                f"template version is {template_version or 'blank'}, expected {WORKBOOK_SCHEMA_VERSION}",
                code="DET-WBK-003",
                hint=(
                    "Create a current workbook with `det workbook build`, then import the "
                    "authoritative ODCS, DDL, or dbt manifest."
                ),
            )
        registry_fingerprint = slug(metadata.get("operator_registry_sha256"))
        expected_fingerprint = OperatorRegistry.load().fingerprint()
        if registry_fingerprint and registry_fingerprint != expected_fingerprint:
            context.add(
                "_DET Metadata",
                None,
                "the workbook operator registry does not match this compiler",
                code="DET-WBK-005",
                hint=(
                    "Run `det workbook refresh WORKBOOK.xlsx`, then review operation and "
                    "parameter dropdowns before generating."
                ),
            )
        registry_version = slug(metadata.get("operator_registry_version"))
        if registry_version and registry_version != OPERATOR_REGISTRY_VERSION:
            context.add(
                "_DET Metadata",
                None,
                f"operator registry version is {registry_version}, expected "
                f"{OPERATOR_REGISTRY_VERSION}",
                code="DET-WBK-006",
                hint="Refresh the workbook and review operation selections.",
            )
        product = self._product(context)
        return product, self._schema(context)

    @staticmethod
    def _product(context: WorkbookParseContext) -> ProductMetadata:
        fundamentals = context.workbook.sheet("Fundamentals")
        contract_id = slug(fundamentals.cell(7, 3))
        try:
            return ProductMetadata(
                contract_id=contract_id or None,
                product_id=contract_product_id(contract_id, fundamentals.cell(15, 3)),
                name=slug(fundamentals.cell(8, 3)),
                version=slug(fundamentals.cell(9, 3)) or DEFAULT_DATA_PRODUCT_VERSION,
                status=slug(fundamentals.cell(10, 3)) or "draft",
                domain=optional_text(fundamentals.cell(14, 3)),
                description=optional_text(fundamentals.cell(19, 3)),
                owner=optional_text(fundamentals.cell(12, 3)),
            )
        except Exception as exc:  # aggregate cell-level model errors
            context.add("Fundamentals", None, str(exc), code="DET-WBK-011")
            return ProductMetadata(product_id="invalid", name="invalid")

    @staticmethod
    def _schema(context: WorkbookParseContext) -> list[SchemaProperty]:
        schema: list[SchemaProperty] = []
        for sheet_name in schema_sheet_names(context.workbook):
            sheet = context.workbook.sheet(sheet_name)
            object_name = slug(sheet.cell(5, 2)) or sheet_name.removeprefix("Schema ")
            for row_number, row in rows(sheet, header_row=13, data_row=14):
                if not optional(row.get("Property")):
                    continue
                try:
                    schema.append(
                        SchemaProperty(
                            object_name=object_name,
                            name=slug(row.get("Property")),
                            logical_type=slug(row.get("Logical Type")),
                            physical_type=optional_text(row.get("Physical Type")),
                            description=optional_text(row.get("Description")),
                            required=boolean(row.get("Required")),
                            primary_key=boolean(row.get("Primary Key")),
                            unique=boolean(row.get("Unique")),
                            classification=optional_text(row.get("Classification")),
                            implementation=SchemaImplementation(
                                (slug(row.get("DET Implementation")) or "mapped").casefold()
                            ),
                            workbook_sheet=sheet_name,
                            workbook_row=row_number,
                            odcs_fields=_advanced_property_fields(row),
                        )
                    )
                except Exception as exc:  # aggregate all row diagnostics
                    context.add(sheet_name, row_number, str(exc), code="DET-WBK-012")
        return schema

    @staticmethod
    def odcs_passthrough(context: WorkbookParseContext) -> dict[str, JsonValue]:
        if "_DET Raw ODCS" not in context.workbook.sheetnames:
            return {}
        sheet = context.workbook.sheet("_DET Raw ODCS")
        raw = "".join(
            str(row[0])
            for row in sheet.iter_rows(min_row=2)
            if row and isinstance(row[0], str) and row[0]
        )
        if not isinstance(raw, str) or not raw.strip():
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            context.add(
                "_DET Raw ODCS",
                2,
                f"stored ODCS passthrough JSON is invalid: {exc}",
                code="DET-WBK-007",
            )
            return {}
        return payload if isinstance(payload, dict) else {}
