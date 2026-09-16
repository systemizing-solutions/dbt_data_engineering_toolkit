"""Readable dbt model, quarantine, and singular-test SQL emission."""

from __future__ import annotations

from textwrap import indent

from ...models import (
    DataProductSpecification,
    FailureMode,
    ModelSpecification,
    SourceSpecification,
    ValidationRule,
)
from ...operational import JsonValue
from ...registry import OperatorRegistry
from .common import GENERATED_HEADER_SQL, jinja


def _jinja_pretty(value: JsonValue, *, indentation: int = 0) -> str:
    """Render nested Jinja values vertically without hiding them in configuration."""

    if isinstance(value, dict):
        if not value:
            return "{}"
        entries = [
            " " * (indentation + 4)
            + f"{jinja(key)}: {_jinja_pretty(item, indentation=indentation + 4)}"
            for key, item in value.items()
        ]
        return "{\n" + ",\n".join(entries) + "\n" + " " * indentation + "}"
    if isinstance(value, list):
        if not value:
            return "[]"
        entries = [
            " " * (indentation + 4) + _jinja_pretty(item, indentation=indentation + 4)
            for item in value
        ]
        return "[\n" + ",\n".join(entries) + "\n" + " " * indentation + "]"
    return jinja(value)


def _render_macro(
    name: str,
    arguments: list[tuple[str | None, JsonValue]],
) -> str:
    """Render a compact call when readable and a SQL-style vertical call otherwise."""

    compact_arguments = [
        f"{argument_name}={jinja(value)}" if argument_name else jinja(value)
        for argument_name, value in arguments
    ]
    compact = "{{ de_toolkit." + name + "(" + ", ".join(compact_arguments) + ") }}"
    contains_collection = any(isinstance(value, (dict, list)) for _, value in arguments)
    if not contains_collection and len(compact) <= 100:
        return compact

    vertical_arguments = []
    for argument_name, value in arguments:
        prefix = f"{argument_name}=" if argument_name else ""
        vertical_arguments.append(prefix + _jinja_pretty(value, indentation=4))
    return (
        "{{ de_toolkit."
        + name
        + "(\n"
        + ",\n".join("    " + argument for argument in vertical_arguments)
        + "\n) }}"
    )


def macro_call(
    expression: str,
    operation: str,
    parameters: dict[str, JsonValue],
    lookups: dict[str, dict[str, JsonValue]],
    registry: OperatorRegistry,
) -> str:
    operator = registry.resolve(operation)
    if operator is None or operator.key == "copy":
        return expression
    if operator.key == "lower":
        return f"lower({expression})"
    if operator.key == "upper":
        return f"upper({expression})"
    if operator.key == "title":
        return _render_macro("string_title", [(None, expression)])
    params = dict(parameters)
    if operator.key == "map_values":
        lookup = str(params.pop("lookup"))
        params["mapping"] = lookups[lookup]
        data_type = params.get("data_type")
        if data_type == "numeric" and ("precision" in params or "scale" in params):
            params["data_type"] = {
                "name": "numeric",
                "precision": params.pop("precision", 38),
                "scale": params.pop("scale", 6),
            }
        else:
            params.pop("precision", None)
            params.pop("scale", None)
        formatting: dict[str, JsonValue] = {}
        if "format_pattern" in params:
            formatting["pattern"] = params.pop("format_pattern")
        if "format_case" in params:
            formatting["case"] = params.pop("format_case")
        if formatting:
            params["format"] = formatting
    elif operator.key == "convert_value":
        if params.get("data_type") == "numeric" and (
            "precision" in params or "scale" in params
        ):
            params["data_type"] = {
                "name": "numeric",
                "precision": params.pop("precision", 38),
                "scale": params.pop("scale", 6),
            }
        else:
            params.pop("precision", None)
            params.pop("scale", None)
    elif operator.key == "correct_errors":
        lookup = str(params.pop("lookup"))
        params.pop("case_sensitive", None)
        params["correction_map"] = lookups[lookup]
    arguments: list[tuple[str | None, JsonValue]] = [
        ("expression", expression) if operator.key == "map_values" else (None, expression)
    ]
    if operator.key == "map_values":
        preferred_order = (
            "mapping",
            "default",
            "preserve_unmapped",
            "case_sensitive",
            "data_type",
            "format",
        )
        ordered_names = [name for name in preferred_order if name in params]
        ordered_names.extend(name for name in params if name not in preferred_order)
    else:
        ordered_names = list(params)
    arguments.extend((name, params[name]) for name in ordered_names)
    return _render_macro(operator.macro, arguments)


def rule_expression(rule: ValidationRule, registry: OperatorRegistry) -> str:
    operator = registry.resolve(rule.operation)
    expression = rule.target_field
    if operator is None:
        return "false"
    if operator.key == "required":
        return f"{expression} is not null"
    if operator.key == "unique":
        raise ValueError("Unique is aggregate and must be emitted as a native dbt test")
    params = dict(rule.parameters)
    if operator.key == "no_future_date":
        return _render_macro(
            "rule_compare",
            [
                (None, expression),
                (None, "<="),
                (None, "current_date"),
                ("allow_null", False),
            ],
        )
    if operator.key == "rule_compare":
        compare_to = str(params.pop("compare_to"))
        comparison = params.pop("operator")
        arguments: list[tuple[str | None, JsonValue]] = [
            (None, expression),
            (None, comparison),
            (None, compare_to),
        ]
        arguments.extend((key, value) for key, value in params.items())
        return _render_macro("rule_compare", arguments)
    arguments = [(None, expression)]
    arguments.extend((key, value) for key, value in params.items())
    return _render_macro(operator.macro, arguments)


def source_expression(source: SourceSpecification) -> str:
    return f"{{{{ source('{source.source_name}', '{source.table_name}') }}}}"


class ModelSqlEmitter:
    def emit(
        self,
        spec: DataProductSpecification,
        model: ModelSpecification,
        registry: OperatorRegistry,
    ) -> str:
        sources = {item.relation: item for item in spec.sources}
        mappings = [item for item in spec.mappings if item.model == model.name]
        relationships = [item for item in spec.relationships if item.model == model.name]
        ctes: list[str] = []
        for relation in model.inputs:
            expression = (
                source_expression(sources[relation])
                if relation in sources
                else f"{{{{ ref('{relation}') }}}}"
            )
            ctes.append(f"source__{relation} as (\n    select * from {expression}\n)")

        if relationships:
            first = relationships[0]
            join_lines = [f"    from source__{first.left_relation} as {first.left_relation}"]
            for relationship in relationships:
                join_lines.extend(
                    [
                        f"    {relationship.join_type.value} join source__{relationship.right_relation} as {relationship.right_relation}",
                        f"        on {relationship.left_relation}.{relationship.left_key} = {relationship.right_relation}.{relationship.right_key}",
                    ]
                )
            mapped_from = "\n".join(join_lines)
            base_relation = first.left_relation
        else:
            base_relation = model.inputs[0]
            mapped_from = f"    from source__{base_relation} as {base_relation}"

        selected: list[str] = []
        properties = {
            item.name: item for item in spec.schema_properties if item.object_name == model.name
        }
        for mapping in mappings:
            prop = properties.get(mapping.target_field)
            transform_logic = prop.odcs_fields.get("transformLogic") if prop else None
            expression = (
                transform_logic.strip()
                if isinstance(transform_logic, str) and transform_logic.strip()
                else f"{mapping.source_relation}.{mapping.source_field}"
            )
            if transform_logic or mapping.source_field != mapping.target_field:
                expression += f" as {mapping.target_field}"
            selected.append(f"        {expression}")
        ctes.append("mapped as (\n    select\n" + ",\n".join(selected) + f"\n{mapped_from}\n)")

        max_step = max((step.step for mapping in mappings for step in mapping.steps), default=0)
        prior = "mapped"
        lookup_maps = {
            name: spec.lookup(name) for name in sorted({item.lookup for item in spec.lookups})
        }
        for step_number in range(1, max_step + 1):
            plain_expressions: list[str] = []
            calculated_expressions: list[str] = []
            changed = False
            for mapping in mappings:
                step = next((item for item in mapping.steps if item.step == step_number), None)
                if step:
                    transformed = macro_call(
                        mapping.target_field,
                        step.operation,
                        step.parameters,
                        lookup_maps,
                        registry,
                    )
                    changed = changed or transformed != mapping.target_field
                    if transformed == mapping.target_field:
                        plain_expressions.append(f"        {mapping.target_field}")
                    else:
                        calculated_expressions.append(
                            f"{indent(transformed, '        ')} as {mapping.target_field}"
                        )
                else:
                    plain_expressions.append(f"        {mapping.target_field}")
            if changed:
                name = f"transformed_{step_number:02d}"
                expressions = plain_expressions + calculated_expressions
                ctes.append(
                    f"{name} as (\n    select\n"
                    + ",\n".join(expressions)
                    + f"\n    from {prior}\n)"
                )
                prior = name

        rules = [item for item in spec.rules if item.model == model.name]
        row_rules = []
        for rule in rules:
            operator = registry.resolve(rule.operation)
            if rule.failure in {FailureMode.WARN, FailureMode.REJECT} and (
                operator is None or operator.key != "unique"
            ):
                row_rules.append(rule)
        if row_rules:
            ctes.append(
                "validated as (\n    select\n        *,\n"
                + ",\n".join(
                    f"{indent(rule_expression(rule, registry), '        ')} as _{rule.name}_valid"
                    for rule in row_rules
                )
                + f"\n    from {prior}\n)"
            )
            prior = "validated"

        rejection_rules = [item for item in row_rules if item.failure == FailureMode.REJECT]
        warning_rules = [item for item in row_rules if item.failure == FailureMode.WARN]
        final_columns = [f"    {mapping.target_field}" for mapping in mappings]
        if rejection_rules:
            final_columns.append("    {{ de_toolkit.assertions(column='_det_rejections') }}")
        if warning_rules:
            final_columns.append("    {{ de_toolkit.assertions(column='_det_warnings') }}")
        final_columns.append(
            "    {{ de_toolkit.audit_columns("
            + jinja(model.audit_source or spec.metadata.product_id)
            + ") }}"
        )
        return (
            GENERATED_HEADER_SQL
            + f"{{{{ config(materialized='{model.materialization.value}') }}}}\n\n"
            + "with "
            + ",\n\n".join(ctes)
            + "\n\nselect\n"
            + ",\n".join(final_columns)
            + f"\nfrom {prior}\n"
        )


class SingularTestEmitter:
    def emit(self, rule: ValidationRule, registry: OperatorRegistry) -> str:
        expression = rule_expression(rule, registry)
        severity = "warn" if rule.failure == FailureMode.WARN else "error"
        return (
            GENERATED_HEADER_SQL
            + f"{{{{ config(severity='{severity}') }}}}\n\n"
            + "select *\n"
            + f"from {{{{ ref('{rule.model}') }}}}\n"
            + f"where not ({expression})\n"
        )
