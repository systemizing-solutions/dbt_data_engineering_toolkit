"""Shared state prepared once for autonomous specification validators."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from ...errors import Diagnostic, DiagnosticCategory, DiagnosticSeverity
from ...models import (
    ColumnMapping,
    DataProductSpecification,
    SchemaProperty,
    ValidationRule,
)
from ...registry import OperatorRegistry
from .common import canonical_type


@dataclass(slots=True)
class ValidationContext:
    spec: DataProductSpecification
    registry: OperatorRegistry
    diagnostics: list[Diagnostic] = field(default_factory=list)
    model_names: set[str] = field(default_factory=set)
    source_names: set[str] = field(default_factory=set)
    lookup_names: set[str] = field(default_factory=set)
    enabled_models: set[str] = field(default_factory=set)
    all_relations: set[str] = field(default_factory=set)
    schema_keys: list[tuple[str, str]] = field(default_factory=list)
    schema: dict[tuple[str, str], SchemaProperty] = field(default_factory=dict)
    relation_fields: dict[str, dict[str, str]] = field(default_factory=dict)
    mappings_by_model: dict[str, list[ColumnMapping]] = field(default_factory=dict)
    inferred_types: dict[tuple[str, str], str] = field(default_factory=dict)
    rules_by_model: dict[str, list[ValidationRule]] = field(default_factory=dict)

    @classmethod
    def create(
        cls, spec: DataProductSpecification, registry: OperatorRegistry
    ) -> "ValidationContext":
        model_names = {item.name for item in spec.models}
        source_names = {item.relation for item in spec.sources}
        schema_keys = [(item.object_name, item.name) for item in spec.schema_properties]
        relation_fields: dict[str, dict[str, str]] = defaultdict(dict)
        for column in spec.source_columns:
            relation_fields[column.relation][column.name] = canonical_type(column.logical_type)
        for prop in spec.schema_properties:
            relation_fields[prop.object_name][prop.name] = canonical_type(prop.logical_type)
        return cls(
            spec=spec,
            registry=registry,
            model_names=model_names,
            source_names=source_names,
            lookup_names={item.lookup for item in spec.lookups},
            enabled_models={item.name for item in spec.models if item.enabled},
            all_relations=model_names | source_names,
            schema_keys=schema_keys,
            schema={(item.object_name, item.name): item for item in spec.schema_properties},
            relation_fields=dict(relation_fields),
            mappings_by_model=defaultdict(list),
            rules_by_model=defaultdict(list),
        )

    def add(
        self,
        code: str,
        category: DiagnosticCategory,
        source: str,
        row: int | None,
        message: str,
        hint: str | None = None,
        severity: DiagnosticSeverity = DiagnosticSeverity.ERROR,
        **context: str,
    ) -> None:
        self.diagnostics.append(
            Diagnostic(
                source,
                row,
                message,
                hint,
                code=code,
                category=category,
                severity=severity,
                context=context,
            )
        )
