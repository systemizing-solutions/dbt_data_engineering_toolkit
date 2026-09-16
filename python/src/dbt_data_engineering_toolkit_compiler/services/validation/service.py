"""Processing service that aggregates autonomous specification validators."""

from __future__ import annotations

from typing import Protocol

from ...adapters import AdapterRegistry
from ...errors import Diagnostic, DiagnosticSeverity, SpecificationValidationError
from ...models import DataProductSpecification
from ...registry import OperatorRegistry
from .context import ValidationContext
from .mappings import MappingValidator
from .metadata_sources import MetadataAndSourceValidator
from .model_outputs import ModelOutputValidator
from .models_schema import ModelAndSchemaValidator
from .quality_build import QualityAndBuildValidator
from .relationships import RelationshipValidator
from .rules import RuleValidator


class SpecificationValidator(Protocol):
    def validate(self, context: ValidationContext) -> None: ...


class SpecificationValidationService:
    """Run independent validation components and aggregate their diagnostics."""

    def __init__(
        self,
        registry: OperatorRegistry | None = None,
        adapters: AdapterRegistry | None = None,
        validators: tuple[SpecificationValidator, ...] | None = None,
    ) -> None:
        self.registry = registry or OperatorRegistry.load()
        self.adapters = adapters or AdapterRegistry.default()
        self.validators = validators or (
            MetadataAndSourceValidator(),
            ModelAndSchemaValidator(),
            MappingValidator(),
            ModelOutputValidator(self.adapters),
            RuleValidator(),
            RelationshipValidator(),
            QualityAndBuildValidator(self.adapters),
        )

    def validate(self, specification: DataProductSpecification) -> tuple[Diagnostic, ...]:
        context = ValidationContext.create(specification, self.registry)
        for validator in self.validators:
            validator.validate(context)
        errors = [
            item for item in context.diagnostics if item.severity == DiagnosticSeverity.ERROR
        ]
        if errors:
            raise SpecificationValidationError(errors)
        return tuple(
            item for item in context.diagnostics if item.severity == DiagnosticSeverity.WARNING
        )
