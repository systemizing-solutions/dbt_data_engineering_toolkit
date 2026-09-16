"""Actionable diagnostics for acceptance failure scenarios."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pytest

from dbt_data_engineering_toolkit_compiler.errors import SpecificationValidationError
from dbt_data_engineering_toolkit_compiler.models import (
    Cardinality,
    Materialization,
    SchemaImplementation,
    SchemaProperty,
    TransformationStep,
)
from dbt_data_engineering_toolkit_compiler.services.validation.service import (
    SpecificationValidationService,
)
from dbt_data_engineering_toolkit_compiler.services.workbooks.service import (
    WorkbookInterpretationService,
)


def _spec():
    workbook = Path(
        str(
            files("dbt_data_engineering_toolkit_compiler")
            / "resources"
            / "data_product_multi_source_sample.xlsx"
        )
    )
    return WorkbookInterpretationService().load(workbook).model_copy(deep=True)


def _diagnostic(spec, code: str) -> str:
    with pytest.raises(SpecificationValidationError) as caught:
        SpecificationValidationService().validate(spec)
    rendered = str(caught.value)
    assert code in rendered
    return rendered


def test_mapping_relation_must_be_a_declared_model_input() -> None:
    spec = _spec()
    mapping = next(item for item in spec.mappings if item.model == "stg_customers")
    mapping.source_relation = "raw_accounts"
    mapping.source_field = "account_id"
    assert "not an input" in _diagnostic(spec, "DET-MAP-005")


def test_unknown_source_field_lists_relation_context() -> None:
    spec = _spec()
    mapping = next(item for item in spec.mappings if item.target_field == "email")
    mapping.source_field = "emali"
    rendered = _diagnostic(spec, "DET-MAP-011")
    assert "relation=raw_customers" in rendered
    assert "Choose one of:" in rendered


def test_unknown_join_key_lists_available_relation_fields() -> None:
    spec = _spec()
    spec.relationships[0].right_key = "missing_account_key"
    rendered = _diagnostic(spec, "DET-REL-004")
    assert "relation=raw_accounts" in rendered
    assert "account_id" in rendered


def test_type_incompatible_operation_reports_pipeline_context() -> None:
    spec = _spec()
    source = next(item for item in spec.source_columns if item.name == "email")
    source.logical_type = "number"
    mapping = next(item for item in spec.mappings if item.target_field == "email")
    mapping.source_type = "number"
    assert "requires string" in _diagnostic(spec, "DET-MAP-016")


def test_final_type_mismatch_is_rejected() -> None:
    spec = _spec()
    prop = next(item for item in spec.schema_properties if item.name == "lifetime_value")
    prop.logical_type = "date"
    assert "pipeline produces number" in _diagnostic(spec, "DET-MAP-021")


def test_enforced_numeric_shape_must_match_cleaning_parameters() -> None:
    spec = _spec()
    mapping = next(item for item in spec.mappings if item.target_field == "lifetime_value")
    mapping.steps[0].parameters["precision"] = 38
    mapping.steps[0].parameters["scale"] = 6
    rendered = _diagnostic(spec, "DET-MAP-022")
    assert "numeric(38,6)" in rendered
    assert "Precision to 18 and Scale to 2" in rendered


def test_unmapped_contract_field_is_rejected() -> None:
    spec = _spec()
    spec.schema_properties.append(
        SchemaProperty(
            object_name="customer_account_mart",
            name="unmapped_business_field",
            logical_type="string",
            implementation=SchemaImplementation.MAPPED,
            workbook_sheet="Schema customer_account_mart",
            workbook_row=99,
        )
    )
    assert "has no DET Mapping" in _diagnostic(spec, "DET-MOD-007")


def test_many_to_many_requires_explicit_opt_in() -> None:
    spec = _spec()
    spec.relationships[0].cardinality = Cardinality.MANY_TO_MANY
    assert "can multiply rows" in _diagnostic(spec, "DET-REL-006")


def test_incremental_is_explicitly_unsupported() -> None:
    spec = _spec()
    spec.models[0].materialization = Materialization.INCREMENTAL
    assert "intentionally unavailable" in _diagnostic(spec, "DET-MOD-003")


def test_missing_lookup_is_rejected() -> None:
    spec = _spec()
    mapping = next(item for item in spec.mappings if item.target_field == "status_label")
    mapping.steps[0].parameters["lookup"] = "missing_status_lookup"
    assert "does not exist" in _diagnostic(spec, "DET-MAP-020")


def test_unusual_macro_order_warns_without_rejecting_the_specification() -> None:
    spec = _spec()
    mapping = next(item for item in spec.mappings if item.target_field == "status_label")
    mapping.steps.append(
        TransformationStep(
            step=2,
            operation="clean_code",
            workbook_row=99,
        )
    )

    warnings = SpecificationValidationService().validate(spec)

    assert [item.code for item in warnings] == ["DET-MAP-023"]
    assert "intentional alternative" in (warnings[0].hint or "")


def test_mapping_format_before_a_later_step_warns_without_rejection() -> None:
    spec = _spec()
    mapping = next(item for item in spec.mappings if item.target_field == "status_label")
    mapping.steps[0].parameters["format_case"] = "upper"
    mapping.steps.append(
        TransformationStep(
            step=2,
            operation="fill_missing",
            parameters={"value": "UNKNOWN"},
            workbook_row=99,
        )
    )

    warnings = SpecificationValidationService().validate(spec)

    assert [item.code for item in warnings] == ["DET-MAP-024"]
    assert "format only" in (warnings[0].hint or "")


def test_statement_shaped_contract_transform_is_rejected() -> None:
    spec = _spec()
    prop = next(
        item
        for item in spec.schema_properties
        if item.object_name == "stg_customers" and item.name == "customer_name"
    )
    prop.odcs_fields["transformLogic"] = (
        "SELECT UPPER(customer_name) AS customer_name "
        "WHERE UPPER(customer_name) IN ('ALICE', 'BOB')"
    )

    rendered = _diagnostic(spec, "DET-MAP-025")

    assert "one scalar SQL expression" in rendered
    assert "UPPER(transaction_post_type_description)" in rendered


def test_contract_transform_unknown_input_column_is_rejected() -> None:
    spec = _spec()
    prop = next(
        item
        for item in spec.schema_properties
        if item.object_name == "stg_customers" and item.name == "customer_name"
    )
    prop.odcs_fields["transformLogic"] = "upper(missing_customer_name)"

    rendered = _diagnostic(spec, "DET-MAP-026")

    assert "unknown input column 'missing_customer_name'" in rendered
