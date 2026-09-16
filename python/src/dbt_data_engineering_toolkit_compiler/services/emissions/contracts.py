"""Canonical ODCS and DET execution metadata emission."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from ...models import (
    ColumnMapping,
    ContractQualityRule,
    DataProductSpecification,
    SchemaProperty,
    ValidationRule,
)
from ...operational import Artifact
from ...version import DET_SPEC_VERSION
from .common import GENERATED_HEADER_YAML, remove_empty, yaml_text


class ContractEmitter:
    def emit(self, spec: DataProductSpecification) -> list[Artifact]:
        properties_by_object: dict[str, list[dict[str, object]]] = defaultdict(list)
        mappings = {(item.model, item.target_field): item for item in spec.mappings}
        rules_by_field: dict[tuple[str, str], list[ValidationRule]] = defaultdict(list)
        for rule in spec.rules:
            rules_by_field[(rule.model, rule.target_field)].append(rule)
        object_quality: dict[str, list[dict[str, object]]] = defaultdict(list)
        property_quality: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
        for rule in spec.quality:
            quality_rule = self._quality_rule(rule)
            if rule.property_name:
                property_quality[(rule.object_name, rule.property_name)].append(quality_rule)
            else:
                object_quality[rule.object_name].append(quality_rule)
        for prop in spec.schema_properties:
            properties_by_object[prop.object_name].append(
                self._property(
                    prop,
                    mappings.get((prop.object_name, prop.name)),
                    rules_by_field[(prop.object_name, prop.name)],
                    property_quality[(prop.object_name, prop.name)],
                )
            )

        raw_description = spec.odcs_passthrough.get("description")
        description = dict(raw_description) if isinstance(raw_description, dict) else {}
        description["purpose"] = spec.metadata.description or spec.metadata.name
        raw_schema = spec.odcs_passthrough.get("schema")
        raw_schema_objects = (
            [item for item in raw_schema if isinstance(item, dict)]
            if isinstance(raw_schema, list)
            else []
        )
        raw_schema_by_name = {
            str(item.get("name", "")).casefold(): item for item in raw_schema_objects
        }
        emitted_schema: list[dict[str, object]] = []
        for model in spec.models:
            if not model.enabled:
                continue
            schema_item: dict[str, object] = dict(raw_schema_by_name.get(model.name.casefold(), {}))
            schema_item.update(
                {
                    "name": model.name,
                    "description": model.description,
                    "physicalType": "table",
                    "quality": object_quality.get(model.name, []),
                    "properties": properties_by_object.get(model.name, []),
                }
            )
            emitted_schema.append(schema_item)

        contract_payload: dict[str, object] = dict(spec.odcs_passthrough)
        contract_payload.update(
            {
                "apiVersion": "v3.1.0",
                "kind": "DataContract",
                "id": spec.metadata.contract_id
                or f"urn:datacontract:{spec.metadata.domain or 'data'}:{spec.metadata.product_id}",
                "name": spec.metadata.name,
                "version": spec.metadata.version,
                "status": spec.metadata.status,
                "domain": spec.metadata.domain,
                "dataProduct": spec.metadata.product_id,
                "description": description,
                "schema": emitted_schema,
                "slaProperties": [
                    {
                        "property": item.name,
                        "value": item.value,
                        "unit": item.unit,
                        "description": item.description,
                    }
                    for item in spec.sla
                ],
                "roles": [item.model_dump(mode="json") for item in spec.roles],
                "support": [item.model_dump(mode="json") for item in spec.support],
            }
        )
        if spec.team or "team" not in contract_payload:
            contract_payload["team"] = {
                "name": spec.metadata.owner or spec.metadata.domain or "Data Product Team",
                "members": [
                    {
                        "username": member.username,
                        "name": member.name,
                        "role": member.role,
                        "customProperties": (
                            [{"property": "email", "value": member.email}]
                            if member.email and member.email != member.username
                            else []
                        ),
                    }
                    for member in spec.team
                ],
            }
        if spec.servers or "servers" not in contract_payload:
            contract_payload["servers"] = [
                {
                    "server": server.name,
                    "type": server.server_type,
                    "environment": server.environment,
                    "account": server.account,
                    "database": server.database,
                    "schema": server.schema_name,
                    "host": server.host,
                    "port": server.port,
                }
                for server in spec.servers
            ]
        contract = remove_empty(contract_payload)
        det = {
            "apiVersion": DET_SPEC_VERSION,
            "kind": "DataProductExecution",
            "product": spec.metadata.product_id,
            "spec": spec.model_dump(mode="json"),
        }
        return [
            Artifact(
                Path(f"contracts/{spec.metadata.product_id}.odcs.yaml"),
                GENERATED_HEADER_YAML + yaml_text(contract),
            ),
            Artifact(
                Path(f"contracts/{spec.metadata.product_id}.det.yaml"),
                GENERATED_HEADER_YAML + yaml_text(det),
            ),
        ]

    @staticmethod
    def _quality_rule(rule: ContractQualityRule) -> dict[str, object]:
        quality_rule: dict[str, object] = dict(rule.odcs_fields)
        quality_rule.update(
            {
                "id": rule.rule_id,
                "type": rule.rule_type,
                "metric": rule.metric,
                "query": rule.query,
                "engine": rule.engine,
                "implementation": rule.implementation,
                "dimension": rule.dimension,
                "description": rule.description,
                "severity": rule.severity,
                "scheduler": rule.scheduler,
                "schedule": rule.schedule,
            }
        )
        if rule.threshold:
            quality_rule[rule.threshold] = rule.value
        cleaned = remove_empty(quality_rule)
        assert isinstance(cleaned, dict)
        return cleaned

    @staticmethod
    def _property(
        prop: SchemaProperty,
        mapping: ColumnMapping | None,
        rules: list[ValidationRule],
        quality: list[dict[str, object]],
    ) -> dict[str, object]:
        logical_options: dict[str, object] = {}
        for rule in rules:
            operation = rule.operation.casefold()
            if operation in {"is_between", "number in range"}:
                if "min_value" in rule.parameters:
                    logical_options["minimum"] = rule.parameters["min_value"]
                if "max_value" in rule.parameters:
                    logical_options["maximum"] = rule.parameters["max_value"]
            elif operation in {"is_in_list", "value in list"}:
                logical_options["enum"] = rule.parameters.get("values", [])
            elif operation in {"regex_match", "matches pattern"}:
                logical_options["pattern"] = rule.parameters.get("pattern")
        item: dict[str, object] = dict(prop.odcs_fields)
        item.update(
            {
                "name": prop.name,
                "logicalType": prop.logical_type,
                "description": prop.description,
                "required": prop.required,
                "primaryKey": prop.primary_key,
                "unique": prop.unique,
            }
        )
        if prop.physical_type:
            item["physicalType"] = prop.physical_type
        if prop.classification:
            item["classification"] = prop.classification
        if logical_options:
            item["logicalTypeOptions"] = logical_options
        if quality:
            item["quality"] = quality
        if mapping is not None:
            item["transformSourceObjects"] = [f"{mapping.source_relation}.{mapping.source_field}"]
            if not item.get("transformLogic"):
                item["transformLogic"] = " -> ".join(step.operation for step in mapping.steps)
            if not item.get("transformDescription"):
                item["transformDescription"] = (
                    f"Generated as explicit de_toolkit macro calls for {mapping.target_field}."
                )
        return {key: value for key, value in item.items() if value is not None}
