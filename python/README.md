# Data Engineering Toolkit compiler

The `det` CLI turns the controlled V5.0.1 official-ODCS Excel superset into
canonical ODCS, DET execution metadata, and a readable dbt project. It includes
safe questionnaire-based workbook creation, ODCS/DDL/dbt-to-Excel import and
merge-safe synchronization, source-schema import, cross-sheet semantic/type
validation, atomic post-sync generation, Data Contract synchronization, SQLFluff,
and the isolated `det prove` acceptance flow. Data Contract CLI, dbt Core,
DuckDB, and SQLFluff are default dependencies.

V5.0.1 makes the visible official `Quality` sheet authoritative, preserves
advanced per-rule ODCS values, supports eight production warehouse providers, and adds mandatory
85.01% Python statement coverage. The generated dbt package has 98.53% DuckDB-scoped macro
implementation coverage plus 100% public-API direct execution coverage and supports dbt Core plus
Fusion-compatible projects. External resources
are isolated behind brokers; reusable services interpret workbooks and input
formats; independent components validate with stable diagnostic codes; and one
emitter owns each artifact family. The CLI remains a thin exposer over
`ToolkitApplication`.

## Install

```bash
python -m pip install dbt-data-engineering-toolkit-compiler==5.0.1
```

The default installation includes Data Contract CLI, dbt Core, dbt-duckdb,
DuckDB, and SQLFluff. Install one additional warehouse adapter per deployment
environment, for example:

```bash
python -m pip install "dbt-data-engineering-toolkit-compiler[snowflake]"
```

Supported extras are `athena`, `bigquery`, `clickhouse`, `databricks`,
`duckdb`, `postgres`, `redshift`, `snowflake`, and `spark`.

## Workflow

Use this sequence to move from workbook design to validated, testable dbt
delivery.

| Step | Business action | Outcome | Command |
| --- | --- | --- | --- |
| 1 | Run the guided, safe workbook builder | Product basics; no demo rows by default | `det workbook build PRODUCT.xlsx` |
| 2 | Import or define target structures | ODCS model and property rows | `det workbook import ...` |
| 3 | Register/import upstream sources | Checked source fields and types | `det source import ...` |
| 4 | Define model inputs, mappings, and joins | Context-aware fields and executable cardinality checks | `det workbook refresh PRODUCT.xlsx` |
| 5 | Add contract rules on Quality; runtime handling on Operational Validation | ODCS tests, warnings, and quarantine with one clear authority | Use workbook sheets (no CLI command) |
| 6 | Validate the workbook | Actionable cross-sheet diagnostics | `det validate PRODUCT.xlsx` |
| 7 | Preview generated changes | No files changed | `det generate PRODUCT.xlsx --project-dir dbt_product --dry-run --prune` |
| Optional before step 8 | Override the default package source for a fork or mirror | dbt packages resolve from your published Git URL and pinned revision | `export DBT_DATA_ENGINEERING_TOOLKIT_GIT_URL=https://github.com/systemizing-solutions/dbt_data_engineering_toolkit.git` |
| 8 | Generate, sync, and lint | dbt packages resolve from the public Git URL and pinned revision | `det generate ...; det check ...` |
| 9 | Run isolated acceptance | Contract, dbt tests, evaluator | `det prove PRODUCT.xlsx --project-dir dbt_product` |
| 10 | Merge later schema changes | Mappings and rules preserved | `det workbook sync ...` |
| Demo | Opt in only when explicitly wanted | Multi-source customer training rows | `det workbook build demo.xlsx --sample-customer-data` |

Generated `packages.yml` uses the public repository by default. To use a fork or mirror, override its package source URL before running `dbt deps`:

```bash
export DBT_DATA_ENGINEERING_TOOLKIT_GIT_URL=https://github.com/systemizing-solutions/dbt_data_engineering_toolkit.git
```

If you need a custom variable name, set `Toolkit Git Env` on the `DET Build` sheet
before `det generate`, then export that variable name in your shell.

## Quick start

```bash
det new customer_360
cd customer_360
det prove data_product.xlsx --project-dir .
```

This starter mode creates and validates a populated workbook, generates a complete DuckDB dbt project, and proves it through the normal contract and dbt pipeline. The public package URL is the default; `DBT_DATA_ENGINEERING_TOOLKIT_GIT_URL` remains available for forks and mirrors.

For production-safe blank workbooks, use `det workbook build data_product.xlsx --no-input`. The starter and governed paths use the same compiler and proof services.

Continue with `det --help` and `det workbook --help`. The source repository
root README contains the complete workbook-to-ODCS-to-dbt walkthrough,
architecture, compatibility matrix, testing definitions, and deployment guide.
