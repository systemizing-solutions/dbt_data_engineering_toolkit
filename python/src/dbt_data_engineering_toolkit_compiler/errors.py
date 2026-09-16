"""Localized compiler diagnostics and exception taxonomy."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class DiagnosticCategory(StrEnum):
    METADATA = "metadata"
    SOURCE = "source"
    MODEL = "model"
    MAPPING = "mapping"
    RULE = "rule"
    RELATIONSHIP = "relationship"
    QUALITY = "quality"
    BUILD = "build"
    WORKBOOK = "workbook"
    DEPENDENCY = "dependency"


class DiagnosticSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class DiagnosticLocation:
    source: str
    row: int | None = None

    def render(self) -> str:
        return self.source if self.row is None else f"{self.source}, row {self.row}"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    sheet: str
    row: int | None
    message: str
    hint: str | None = None
    code: str = "DET-GEN-001"
    category: DiagnosticCategory = DiagnosticCategory.WORKBOOK
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
    context: dict[str, str] = field(default_factory=dict)

    @property
    def location(self) -> DiagnosticLocation:
        return DiagnosticLocation(self.sheet, self.row)

    def render(self) -> str:
        prefix = "Warning: " if self.severity == DiagnosticSeverity.WARNING else ""
        result = f"{prefix}{self.code} · {self.location.render()}: {self.message}"
        if self.context:
            details = ", ".join(f"{key}={value}" for key, value in sorted(self.context.items()))
            result = f"{result}\n  Context: {details}"
        return f"{result}\n  Fix: {self.hint}" if self.hint else result


class ToolkitError(Exception):
    """Base class for failures intentionally exposed by the toolkit."""


class ToolkitValidationError(ToolkitError):
    """Base class for invalid user-controlled input."""


class ToolkitDependencyError(ToolkitError):
    """Base class for external dependency failures."""


class ToolkitServiceError(ToolkitError):
    """Base class for localized service failures."""


class SpecificationValidationError(ToolkitValidationError):
    """Raised after collecting actionable specification diagnostics."""

    def __init__(self, diagnostics: list[Diagnostic]):
        self.diagnostics = diagnostics
        super().__init__("\n".join(item.render() for item in diagnostics))


class InvalidWorkbookError(ToolkitValidationError):
    """Raised when a workbook cannot be opened or interpreted."""


class MissingWorkbookSheetError(InvalidWorkbookError):
    """Raised when a required DET workbook sheet is absent."""


class GeneratedFileDriftError(ToolkitValidationError):
    """Raised when a generated file was hand-edited since the prior run."""


class DependencyExecutionError(ToolkitDependencyError):
    """Base class for a failed external command."""

    def __init__(
        self,
        dependency: str,
        message: str,
        *,
        command: tuple[str, ...] = (),
        return_code: int | None = None,
    ) -> None:
        self.dependency = dependency
        self.command = command
        self.return_code = return_code
        super().__init__(message)


class MissingDependencyError(DependencyExecutionError):
    """Raised when a required executable or Python dependency is unavailable."""


class DbtExecutionError(DependencyExecutionError):
    """Raised when dbt cannot complete a requested operation."""


class SqlFluffExecutionError(DependencyExecutionError):
    """Raised when SQLFluff cannot complete a requested operation."""


class DataContractExecutionError(DependencyExecutionError):
    """Raised when Data Contract CLI cannot complete a requested operation."""


class FileOperationError(ToolkitDependencyError):
    """Raised when an external filesystem operation fails."""

    def __init__(self, path: Path, message: str) -> None:
        self.path = path
        super().__init__(message)
