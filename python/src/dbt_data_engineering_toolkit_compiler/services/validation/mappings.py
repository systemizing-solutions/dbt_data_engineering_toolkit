"""Transformation mapping, parameter, and type-flow validation."""

from __future__ import annotations

from sqlfluff.core import Linter

from ...adapters import AdapterRegistry
from ...errors import DiagnosticCategory, DiagnosticSeverity
from ...models import SchemaImplementation
from ...registry import OperatorKind
from .common import (
    canonical_type,
    mapping_row,
    numeric_shape,
    step_output_type,
    validate_identifier,
    validate_parameter,
)
from .context import ValidationContext


class MappingValidator:
    _RECOMMENDED_STAGES = {
        "convert_value": (1, "convert/interpret"),
        "clean_text": (1, "convert/interpret"),
        "clean_email": (1, "convert/interpret"),
        "clean_phone": (1, "convert/interpret"),
        "clean_numeric": (1, "convert/interpret"),
        "clean_integer": (1, "convert/interpret"),
        "clean_date": (1, "convert/interpret"),
        "clean_timestamp": (1, "convert/interpret"),
        "clean_boolean": (1, "convert/interpret"),
        "clean_code": (1, "convert/interpret"),
        "standardize_country": (2, "standardize"),
        "standardize_currency": (2, "standardize"),
        "correct_errors": (2, "standardize"),
        "map_values": (3, "map"),
        "fill_missing": (4, "default"),
        "lower": (9, "present"),
        "upper": (9, "present"),
        "title": (9, "present"),
    }

    def validate(self, context: ValidationContext) -> None:
        spec = context.spec
        for mapping in spec.mappings:
            target_key = (mapping.model, mapping.target_field)
            row = mapping_row(mapping)
            context.mappings_by_model[mapping.model].append(mapping)
            if target_key in context.inferred_types:
                context.add(
                    "DET-MAP-003",
                    DiagnosticCategory.MAPPING,
                    "DET Mapping",
                    row,
                    f"{mapping.model}.{mapping.target_field} has more than one source-field definition",
                    "Keep one source field and express additional work as ordered steps.",
                )
            if mapping.model not in context.model_names:
                context.add(
                    "DET-MAP-004",
                    DiagnosticCategory.MAPPING,
                    "DET Mapping",
                    row,
                    f"mapping references unknown model {mapping.model!r}",
                )
            else:
                model = spec.model(mapping.model)
                if mapping.source_relation not in model.inputs:
                    context.add(
                        "DET-MAP-005",
                        DiagnosticCategory.MAPPING,
                        "DET Mapping",
                        row,
                        f"{mapping.model}.{mapping.target_field}: source relation {mapping.source_relation!r} is not an input to the model",
                        "Add the relation in DET Model Inputs or select an available input.",
                    )
            if mapping.source_relation not in context.all_relations:
                context.add(
                    "DET-MAP-006",
                    DiagnosticCategory.MAPPING,
                    "DET Mapping",
                    row,
                    f"{mapping.model}.{mapping.target_field} references unknown relation {mapping.source_relation!r}",
                )
            validate_identifier(
                context,
                mapping.target_field,
                "target field",
                "DET Mapping",
                row,
                code="DET-MAP-007",
                category=DiagnosticCategory.MAPPING,
            )
            validate_identifier(
                context,
                mapping.source_field,
                "source field",
                "DET Mapping",
                row,
                code="DET-MAP-008",
                category=DiagnosticCategory.MAPPING,
            )
            prop = context.schema.get(target_key)
            if prop is None:
                context.add(
                    "DET-MAP-009",
                    DiagnosticCategory.MAPPING,
                    "DET Mapping",
                    row,
                    f"{mapping.model}.{mapping.target_field} is missing from its Schema sheet",
                )
            elif prop.implementation != SchemaImplementation.MAPPED:
                context.add(
                    "DET-MAP-010",
                    DiagnosticCategory.MAPPING,
                    "DET Mapping",
                    row,
                    f"{mapping.model}.{mapping.target_field} is mapped but Schema marks it {prop.implementation.value}",
                )
            if prop is not None:
                self._validate_transform_logic(context, mapping, prop)

            available_type = context.relation_fields.get(mapping.source_relation, {}).get(
                mapping.source_field
            )
            if available_type is None:
                available_fields = sorted(context.relation_fields.get(mapping.source_relation, {}))
                context.add(
                    "DET-MAP-011",
                    DiagnosticCategory.MAPPING,
                    "DET Mapping",
                    row,
                    f"{mapping.source_relation}.{mapping.source_field} is not declared in its source or model schema",
                    (
                        "Choose one of: " + ", ".join(available_fields) + "."
                        if available_fields
                        else "Import or declare this relation's source schema, then refresh the workbook."
                    ),
                    model=mapping.model,
                    target=mapping.target_field,
                    relation=mapping.source_relation,
                )
                current_type = canonical_type(mapping.source_type)
            else:
                current_type = available_type
                declared_source_type = canonical_type(mapping.source_type)
                if (
                    declared_source_type not in {"", "unknown"}
                    and declared_source_type != available_type
                ):
                    context.add(
                        "DET-MAP-012",
                        DiagnosticCategory.MAPPING,
                        "DET Mapping",
                        row,
                        f"{mapping.source_relation}.{mapping.source_field} is declared {available_type}, not {mapping.source_type}",
                    )

            step_numbers = [step.step for step in mapping.steps]
            if len(step_numbers) != len(set(step_numbers)):
                context.add(
                    "DET-MAP-013",
                    DiagnosticCategory.MAPPING,
                    "DET Mapping",
                    row,
                    f"{mapping.model}.{mapping.target_field} uses the same Step more than once",
                    "Use consecutive step numbers 1, 2, 3... for this target field.",
                )
            if step_numbers and sorted(step_numbers) != list(range(1, max(step_numbers) + 1)):
                context.add(
                    "DET-MAP-014",
                    DiagnosticCategory.MAPPING,
                    "DET Mapping",
                    row,
                    f"{mapping.model}.{mapping.target_field} has a gap in its step sequence",
                )
            previous_stage: tuple[int, str] | None = None
            for step_index, step in enumerate(mapping.steps):
                operator = context.registry.resolve(step.operation)
                if operator is None or operator.kind != OperatorKind.TRANSFORMATION:
                    context.add(
                        "DET-MAP-015",
                        DiagnosticCategory.MAPPING,
                        "DET Mapping",
                        step.workbook_row,
                        f"unknown transformation {step.operation!r}",
                        "Choose an option from the Operation dropdown.",
                    )
                    continue
                stage = self._RECOMMENDED_STAGES.get(operator.key)
                if stage is not None and previous_stage is not None and stage[0] < previous_stage[0]:
                    context.add(
                        "DET-MAP-023",
                        DiagnosticCategory.MAPPING,
                        "DET Mapping",
                        step.workbook_row,
                        f"{mapping.model}.{mapping.target_field}: {stage[1]} step "
                        f'"{operator.label}" follows a {previous_stage[1]} step',
                        "Recommended flow: convert_value/type-aware clean_* -> "
                        "standardize_*/correct_errors -> mapping -> fill_missing -> "
                        "derive/conform -> validate/route -> present. "
                        "Keep this order when it fits the field; the workbook still permits an "
                        "intentional alternative.",
                        severity=DiagnosticSeverity.WARNING,
                        model=mapping.model,
                        target=mapping.target_field,
                    )
                if stage is not None:
                    previous_stage = stage
                if (
                    operator.key == "map_values"
                    and ({"format_pattern", "format_case"} & step.parameters.keys())
                    and step_index < len(mapping.steps) - 1
                ):
                    context.add(
                        "DET-MAP-024",
                        DiagnosticCategory.MAPPING,
                        "DET Mapping",
                        step.workbook_row,
                        f"{mapping.model}.{mapping.target_field}: mapping formats the value before "
                        "the transformation pipeline is complete",
                        "Remove Format Pattern/Format Case from this mapping step, perform later "
                        "semantic and business logic on the typed value, and format only when the "
                        "published target requires text. The workbook permits this order when it "
                        "is intentional.",
                        severity=DiagnosticSeverity.WARNING,
                        model=mapping.model,
                        target=mapping.target_field,
                    )
                allowed_inputs = {canonical_type(item) for item in operator.input_types}
                if "any" not in allowed_inputs and current_type not in allowed_inputs:
                    context.add(
                        "DET-MAP-016",
                        DiagnosticCategory.MAPPING,
                        "DET Mapping",
                        step.workbook_row,
                        f'{mapping.model}.{mapping.target_field}: "{operator.label}" requires '
                        f"{', '.join(operator.input_types)}, but {mapping.source_relation}.{mapping.source_field} is {current_type}",
                    )
                for name, definition in operator.parameters.items():
                    if definition.required and name not in step.parameters:
                        context.add(
                            "DET-MAP-017",
                            DiagnosticCategory.MAPPING,
                            "DET Parameters",
                            step.workbook_row,
                            f'"{operator.label}" requires {name.replace("_", " ")}',
                        )
                for name, value in step.parameters.items():
                    definition = operator.parameters.get(name)
                    if definition is None:
                        context.add(
                            "DET-MAP-018",
                            DiagnosticCategory.MAPPING,
                            "DET Parameters",
                            step.workbook_row,
                            f'"{operator.label}" does not accept parameter {name!r}',
                        )
                    else:
                        validate_parameter(
                            context,
                            name,
                            value,
                            definition,
                            "DET Parameters",
                            step.workbook_row,
                            code="DET-MAP-019",
                            category=DiagnosticCategory.MAPPING,
                        )
                lookup = step.parameters.get("lookup")
                if lookup and lookup not in context.lookup_names:
                    context.add(
                        "DET-MAP-020",
                        DiagnosticCategory.MAPPING,
                        "DET Parameters",
                        step.workbook_row,
                        f"lookup {lookup!r} does not exist",
                    )
                current_type = step_output_type(current_type, operator, step.parameters)
            context.inferred_types[target_key] = current_type
            if prop is not None and canonical_type(prop.logical_type) != current_type:
                context.add(
                    "DET-MAP-021",
                    DiagnosticCategory.MAPPING,
                    prop.workbook_sheet or f"Schema {mapping.model}",
                    prop.workbook_row,
                    f"{mapping.model}.{mapping.target_field}: transformation pipeline produces {current_type} but Schema declares {canonical_type(prop.logical_type)}",
                    "Change the mapping operation/formatting or the contract Logical Type.",
                )
            self._validate_numeric_shape(context, mapping, prop, current_type)

    @staticmethod
    def _validate_transform_logic(context, mapping, prop) -> None:
        transform_logic = prop.odcs_fields.get("transformLogic")
        if not isinstance(transform_logic, str) or not transform_logic.strip():
            return
        provider = AdapterRegistry.default().get(context.spec.build.adapter)
        dialect = provider.sqlfluff_dialect if provider else context.spec.build.adapter
        parsed = Linter(dialect=dialect).parse_string(
            f"select ({transform_logic.strip()}) as __det_value"
        )
        tree = parsed.tree
        unparsable = list(tree.recursive_crawl("unparsable")) if tree else []
        select_count = len(list(tree.recursive_crawl("select_statement"))) if tree else 0
        if parsed.violations or unparsable or select_count != 1:
            context.add(
                "DET-MAP-025",
                DiagnosticCategory.MAPPING,
                prop.workbook_sheet or f"Schema {mapping.model}",
                prop.workbook_row,
                f"{mapping.model}.{mapping.target_field}: Transform Logic must be one scalar "
                "SQL expression for the configured adapter",
                "Use only the value expression here, for example "
                "UPPER(transaction_post_type_description). Put WHERE filtering in a dedicated "
                "model or express an allowed-value requirement as Operational Validation.",
                model=mapping.model,
                target=mapping.target_field,
            )
            return
        for reference in tree.recursive_crawl("column_reference"):
            parts = [
                part.strip('"`[]').casefold()
                for part in reference.raw.split(".")
                if part.strip()
            ]
            if not parts:
                continue
            field = parts[-1]
            if len(parts) > 1:
                relation = parts[-2]
                if relation not in context.spec.model(mapping.model).inputs or field not in (
                    context.relation_fields.get(relation, {})
                ):
                    context.add(
                        "DET-MAP-026",
                        DiagnosticCategory.MAPPING,
                        prop.workbook_sheet or f"Schema {mapping.model}",
                        prop.workbook_row,
                        f"{mapping.model}.{mapping.target_field}: Transform Logic references "
                        f"unknown input column {reference.raw!r}",
                        "Reference a field declared on one of the model's input relations.",
                    )
                continue
            matches = [
                relation
                for relation in context.spec.model(mapping.model).inputs
                if field in context.relation_fields.get(relation, {})
            ]
            if len(matches) == 1:
                continue
            problem = "ambiguous" if matches else "unknown"
            context.add(
                "DET-MAP-026",
                DiagnosticCategory.MAPPING,
                prop.workbook_sheet or f"Schema {mapping.model}",
                prop.workbook_row,
                f"{mapping.model}.{mapping.target_field}: Transform Logic references {problem} "
                f"input column {reference.raw!r}",
                (
                    "Qualify the column with its declared input relation."
                    if matches
                    else "Reference a field declared on one of the model's input relations."
                ),
            )

    @staticmethod
    def _validate_numeric_shape(context, mapping, prop, current_type: str) -> None:
        if prop is None or current_type != "number":
            return
        model = next((item for item in context.spec.models if item.name == mapping.model), None)
        expected = numeric_shape(prop.physical_type)
        if model is None or not model.enforce_contract or expected is None:
            return
        actual: tuple[int, int] | None = None
        for step in reversed(mapping.steps):
            operator = context.registry.resolve(step.operation)
            if operator is None:
                continue
            defines_numeric = operator.key in {"clean_numeric", "convert_value"} or (
                operator.key == "map_values"
                and canonical_type(str(step.parameters.get("data_type", ""))) == "number"
            )
            if not defines_numeric:
                continue
            precision = step.parameters.get("precision", operator.parameters["precision"].default)
            scale = step.parameters.get("scale", operator.parameters["scale"].default)
            if isinstance(precision, int) and isinstance(scale, int):
                actual = (precision, scale)
            break
        if actual is None or actual == expected:
            return
        context.add(
            "DET-MAP-022",
            DiagnosticCategory.MAPPING,
            "DET Parameters",
            mapping.steps[-1].workbook_row if mapping.steps else prop.workbook_row,
            f"{mapping.model}.{mapping.target_field}: cleaning produces "
            f"numeric({actual[0]},{actual[1]}) but the enforced contract declares "
            f"{prop.physical_type}",
            f"Set Precision to {expected[0]} and Scale to {expected[1]} for the "
            "numeric-producing operation, or change the contract Physical Type.",
            model=mapping.model,
            target=mapping.target_field,
        )
