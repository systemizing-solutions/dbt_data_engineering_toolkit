"""Tests for format dispatch at the external structure boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from dbt_data_engineering_toolkit_compiler.operational import CommandResult
from dbt_data_engineering_toolkit_compiler.services.imports.structures import (
    StructureFormat,
    StructureImportService,
)

ODCS = """apiVersion: v3.1.0
kind: DataContract
id: urn:datacontract:sales:orders
name: Orders
version: 1.0.0
status: draft
schema:
  - name: orders
    physicalType: table
    properties:
      - name: order_id
        logicalType: integer
        required: true
"""


class ExcelImportStub:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, Path]] = []

    def import_excel(self, workbook: Path, output: Path) -> CommandResult:
        self.calls.append((workbook, output))
        output.write_text(ODCS, encoding="utf-8")
        return CommandResult(("datacontract", "import", "excel"), 0)

    def export_excel(self, contract: Path, output: Path) -> CommandResult:
        raise AssertionError("not used")

    def lint(self, contract: Path) -> CommandResult:
        raise AssertionError("not used")

    def dbt_sync(self, contract: Path, project: Path, *, dry_run: bool) -> CommandResult:
        raise AssertionError("not used")


@pytest.mark.parametrize("extension", [".xlsx", ".xlsm"])
def test_standard_odcs_excel_delegates_to_data_contract_cli(tmp_path: Path, extension: str) -> None:
    source = tmp_path / f"standard_odcs{extension}"
    source.touch()
    datacontract = ExcelImportStub()

    imported = StructureImportService(datacontract=datacontract).load(
        source,
        StructureFormat.ODCS,
    )

    assert len(datacontract.calls) == 1
    assert datacontract.calls[0][0] == source
    assert imported.product.product_id == "orders"
    assert [model.name for model in imported.models] == ["orders"]
    assert [column.name for column in imported.models[0].columns] == ["order_id"]


def test_contract_import_rejects_unknown_extension(tmp_path: Path) -> None:
    source = tmp_path / "contract.json"
    source.write_text("{}", encoding="utf-8")

    try:
        StructureImportService(datacontract=ExcelImportStub()).load(
            source,
            StructureFormat.ODCS,
        )
    except ValueError as exc:
        assert ".yaml, .yml, .xlsx, or .xlsm" in str(exc)
    else:
        raise AssertionError("unknown contract extensions must be rejected")
