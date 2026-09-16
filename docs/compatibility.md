# V6.0.0 compatibility matrix

The package supports dbt Core on all eight requested data platforms. It is also compatible with
dbt Fusion wherever Fusion currently provides an adapter. Athena and ClickHouse remain Core-only
because dbt Fusion does not currently ship those adapters; this is an engine limitation, not a
hidden fallback in the toolkit.

| Data platform | Compiler install | Core verification | Fusion verification |
| --- | --- | --- | --- |
| DuckDB | default install or `[duckdb]` | full build on every CI run | full build on every CI run |
| BigQuery | `[bigquery]` | isolated parse/dispatch gate and credentialed build | parse gate and credentialed build |
| Snowflake | `[snowflake]` | isolated parse/dispatch gate and credentialed build | parse gate and credentialed build |
| Databricks | `[databricks]` | isolated parse/dispatch gate and credentialed build | parse gate and credentialed build |
| Redshift | `[redshift]` | isolated parse/dispatch gate and credentialed build | parse gate and credentialed build |
| Spark | `[spark]` | isolated parse/dispatch gate and credentialed build | parse gate and credentialed build |
| Athena | `[athena]` | isolated parse/dispatch gate and credentialed build | not supplied by Fusion |
| ClickHouse | `[clickhouse]` | isolated parse/dispatch gate and credentialed build | not supplied by Fusion |

The root project declares:

```yaml
require-dbt-version: [">=1.10.6", "<3.0.0"]
```

It follows dbt's [Fusion package compatibility guide](https://docs.getdbt.com/guides/dbt-package-compat):
current schema syntax, a clean deprecation scan, an integration project, Core testing, and Fusion
builds. Because the required `dbt_project_evaluator` dependency currently documents Fusion with
`--static-analysis=off`, `--no-manage-state`, and `deactivate_for_fusion: true`, the toolkit uses
those flags explicitly instead of claiming a stronger mode than its dependency supports. The
Fusion-supported adapter list is maintained by dbt in
the [v2 upgrade guide](https://docs.getdbt.com/docs/dbt-versions/dbt-upgrade/upgrading-to-v2).

## Warehouse feature floor

The dbt adapter version and the warehouse engine version are separate compatibility surfaces.
Use currently supported managed releases for BigQuery, Snowflake, Redshift, and Databricks SQL.
For versioned engines, the public macros require:

| Platform | Minimum feature floor | Reason |
| --- | --- | --- |
| DuckDB | 1.4.x | pinned compiler runtime and integration execution |
| Databricks Runtime | 10.4 LTS | `try_cast`; Databricks SQL is supported as a managed service |
| Apache Spark | 3.5+ | safe-cast and modern SQL-function behavior used by the facade |
| Amazon Athena | engine version 3 | Trino-compatible array, regex, and lambda behavior |
| ClickHouse | 23.7+ | `initcapUTF8` and the current UTF-8/string function surface |

## Install one deployment adapter

The compiler includes dbt Core and DuckDB by default. Add the warehouse used by that deployment:

```bash
python -m pip install "dbt-data-engineering-toolkit-compiler[bigquery]==6.0.0"
python -m pip install "dbt-data-engineering-toolkit-compiler[snowflake]==6.0.0"
python -m pip install "dbt-data-engineering-toolkit-compiler[databricks]==6.0.0"
```

Use a separate virtual environment per warehouse. In particular, Spark's upstream PyHive stack
and the Databricks SQL connector currently require incompatible Thrift versions. V6.0.0 therefore
does not advertise a misleading `all-adapters` extra.

## What the gates prove

- Every Core adapter parses the complete integration project in an isolated dependency job.
- A manifest contract verifies safety-critical adapter dispatch for casts, regular expressions,
  temporal formatting, grouped numbers, percentiles, and string operations.
- DuckDB executes all models and tests without credentials.
- `.github/workflows/cloud-integration.yml` executes live Core builds on all credentialed remote
  warehouses and live Fusion builds on every Fusion-supported remote warehouse.
- Unsupported native features fail explicitly or are conditionally excluded from the portable
  fixture; no normal `cast` silently replaces a requested safe cast.

Run the credentialed workflow before creating a release tag. Configuration is documented in
[deployment](deployment.md).
