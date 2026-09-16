"""Focused coverage for pluggable adapter capabilities and emitted profiles."""

import pytest

from dbt_data_engineering_toolkit_compiler.adapters import AdapterRegistry
from dbt_data_engineering_toolkit_compiler.models import (
    BuildConfiguration,
    DataProductSpecification,
    ProductMetadata,
)
from dbt_data_engineering_toolkit_compiler.services.emissions.project_config import (
    ProjectConfigurationEmitter,
)


def _artifacts(adapter: str) -> dict[str, str]:
    spec = DataProductSpecification(
        metadata=ProductMetadata(product_id="orders", name="Orders"),
        build=BuildConfiguration(adapter=adapter, target_schema="analytics"),
    )
    return {item.path.as_posix(): item.content for item in ProjectConfigurationEmitter().emit(spec)}


def test_default_registry_exposes_supported_adapter_capabilities() -> None:
    registry = AdapterRegistry.default()
    assert registry.names() == (
        "athena",
        "bigquery",
        "clickhouse",
        "databricks",
        "duckdb",
        "postgres",
        "redshift",
        "snowflake",
        "spark",
    )
    duckdb = registry.get("duckdb")
    postgres = registry.get("postgres")
    snowflake = registry.get("snowflake")
    assert duckdb is not None and duckdb.dbt_dependency == "dbt-duckdb>=1.10,<2"
    assert postgres is not None and postgres.sqlfluff_dialect == "postgres"
    assert snowflake is not None and snowflake.data_type("integer", None) == "number(38,0)"


@pytest.mark.parametrize(
    ("adapter", "dependency", "dialect", "profile_marker"),
    [
        ("athena", "dbt-athena-community", "athena", "DET_ATHENA_S3_STAGING_DIR"),
        ("bigquery", "dbt-bigquery", "bigquery", "DET_BIGQUERY_PROJECT"),
        ("clickhouse", "dbt-clickhouse", "clickhouse", "DET_CLICKHOUSE_HOST"),
        ("databricks", "dbt-databricks", "databricks", "DET_DATABRICKS_HTTP_PATH"),
        ("duckdb", "dbt-duckdb", "duckdb", "target/data_product.duckdb"),
        ("postgres", "dbt-postgres", "postgres", "DET_POSTGRES_HOST"),
        ("redshift", "dbt-redshift", "redshift", "DET_REDSHIFT_HOST"),
        ("snowflake", "dbt-snowflake", "snowflake", "DET_SNOWFLAKE_ACCOUNT"),
        ("spark", "dbt-spark[PyHive]", "sparksql", "DET_SPARK_HOST"),
    ],
)
def test_every_adapter_emits_an_installable_profile_and_sqlfluff_configuration(
    adapter: str,
    dependency: str,
    dialect: str,
    profile_marker: str,
) -> None:
    provider = AdapterRegistry.default().get(adapter)
    assert provider is not None
    assert provider.dbt_dependency.startswith(f"{dependency}>=1.10,")

    artifacts = _artifacts(adapter)
    assert f"type: {adapter}" in artifacts["profiles.yml"]
    assert profile_marker in artifacts["profiles.yml"]
    assert (
        "schema: analytics" in artifacts["profiles.yml"]
        or "dataset: analytics" in artifacts["profiles.yml"]
    )
    assert f"dialect = {dialect}" in artifacts[".sqlfluff"]
    assert "templater = dbt" in artifacts[".sqlfluff"]


def test_postgres_profile_uses_only_environment_references_for_credentials() -> None:
    artifacts = _artifacts("postgres")
    profile = artifacts["profiles.yml"]
    assert "DET_POSTGRES_HOST" in profile
    assert "DET_POSTGRES_PASSWORD" in profile
    assert "schema: analytics" in profile
    assert "password: '{{ env_var" in profile
    assert "dialect = postgres" in artifacts[".sqlfluff"]


def test_snowflake_profile_and_types_come_from_the_provider() -> None:
    artifacts = _artifacts("snowflake")
    profile = artifacts["profiles.yml"]
    for name in (
        "DET_SNOWFLAKE_ACCOUNT",
        "DET_SNOWFLAKE_DATABASE",
        "DET_SNOWFLAKE_PASSWORD",
        "DET_SNOWFLAKE_WAREHOUSE",
    ):
        assert name in profile
    assert "dialect = snowflake" in artifacts[".sqlfluff"]


def test_generated_project_declares_runtime_floor_and_evaluator_dispatch() -> None:
    artifacts = _artifacts("duckdb")
    project = artifacts["dbt_project.yml"]
    packages = artifacts["packages.yml"]
    assert "require-dbt-version:" in project
    assert "- '>=1.10.6'" in project
    assert "macro_namespace: dbt" in project
    assert "- dbt_project_evaluator" in project
    assert "exclude_packages:" in project
    assert "subdirectory: dbt" in packages
    assert "subdirectory: aliases/de_toolkit" in packages


def test_spark_provider_installs_the_required_pyhive_transport() -> None:
    provider = AdapterRegistry.default().get("spark")
    assert provider is not None
    assert provider.dbt_dependency == "dbt-spark[PyHive]>=1.10,<2"
