# `det` V5.0.1 CLI reference

Run `det --help` or `det <command> --help`. Absolute paths are safest in automation.

## Command summary

| Command | Main effect | External dependency |
| --- | --- | --- |
| `det workbook build OUTPUT.xlsx` | create a production-safe workbook | none |
| `det workbook import OUTPUT.xlsx ...` | create a workbook from ODCS, DDL, or dbt | Data Contract CLI for `.xlsx` |
| `det workbook sync WORKBOOK.xlsx ...` | merge changed structures | Data Contract CLI for `.xlsx` |
| `det workbook refresh WORKBOOK.xlsx` | rebuild contextual lists and protections | none |
| `det source import --workbook ...` | merge/replace source metadata | Data Contract CLI for `.xlsx` |
| `det validate WORKBOOK.xlsx` | validate workbook and typed IR | none |
| `det compile WORKBOOK.xlsx --output-dir DIR` | emit ODCS and DET YAML | none |
| `det generate WORKBOOK.xlsx --project-dir DIR` | atomically generate and sync a dbt project | Data Contract CLI |
| `det status WORKBOOK.xlsx --project-dir DIR` | report workbook or generated-file drift | Data Contract CLI |
| `det check WORKBOOK.xlsx --project-dir DIR` | lint contract, parse dbt, lint SQL | Data Contract, dbt, SQLFluff |
| `det lint --project-dir DIR` | run SQLFluff with the dbt templater | SQLFluff, dbt |
| `det prove WORKBOOK.xlsx --project-dir DIR` | isolated release-grade proof | Data Contract, dbt, SQLFluff |

## Build

Interactive:

```bash
det workbook build contracts/orders.xlsx
```

The questionnaire asks for product basics, an optional initial model, and whether to include
Customer 360 demo rows. Demo data defaults to **No**.

Repeatable automation:

```bash
det workbook build contracts/orders.xlsx \
  --no-input \
  --product-id orders \
  --name "Orders" \
  --domain sales \
  --owner "Sales Analytics" \
  --adapter duckdb \
  --target-schema analytics \
  --toolkit-revision v5.0.1
```

`--sample-customer-data` is the only sample-data opt-in. `--force` replaces an existing output
after review.

## Import and sync

Choose exactly one source flag:

```bash
det workbook import contracts/orders.xlsx --from-contract orders.odcs.yaml
det workbook import contracts/orders.xlsx --from-contract standard_odcs.xlsx
det workbook import contracts/orders.xlsx --from-ddl orders.sql
det workbook import contracts/orders.xlsx --from-dbt-manifest upstream/target/manifest.json
```

For `.xlsx`, the compiler runs Data Contract CLI's official Excel importer into a temporary
canonical ODCS YAML file. DDL may also use `--product-id` and `--name`.

Imported models are disabled and mappings remain blank unless `--identity-mappings` is supplied.
That flag is appropriate only when each target field is genuinely a direct source copy.

Merge a changed target structure:

```bash
det workbook sync contracts/orders.xlsx --from-contract orders.odcs.yaml
```

The default adds/updates fields and preserves mappings, parameters, operational rules, and
lookups. `--replace-schema` also removes target fields no longer present; dependent mappings are
preserved so validation can identify each broken reference.

## Source metadata

```bash
det source import \
  --workbook contracts/orders.xlsx \
  --from-dbt-manifest /absolute/upstream/target/manifest.json \
  --replace
```

Create that manifest from the upstream project directory:

```bash
dbt deps --profiles-dir /absolute/path/to/profiles
dbt parse --profiles-dir /absolute/path/to/profiles
test -f target/manifest.json
```

`target/manifest.json` is dbt discovery output. It is unrelated to DET's generated
`.det-manifest.json` hash ledger.

## Refresh and validate

After manually adding models, fields, source relations, or lookups, close Excel and run:

```bash
det workbook refresh contracts/orders.xlsx
det validate contracts/orders.xlsx
```

Refresh accepts the v5.0.1 workbook schema only. Validation returns stable codes with sheet,
row, context, and a corrective hint.

## Generate, inspect, and prove

```bash
det status contracts/orders.xlsx --project-dir build/orders --prune
det generate contracts/orders.xlsx --project-dir build/orders --dry-run --prune
det generate contracts/orders.xlsx --project-dir build/orders --prune

export DBT_DATA_ENGINEERING_TOOLKIT_GIT_URL=https://github.com/systemizing-solutions/dbt_data_engineering_toolkit.git
cd build/orders
dbt deps --profiles-dir .
cd ../..

det check contracts/orders.xlsx --project-dir build/orders
det prove contracts/orders.xlsx --project-dir build/orders
```

`--dry-run` performs the real synchronization in disposable staging. `--force` is an explicit
recovery path for reviewed generated-file drift. `--prune` removes only obsolete files whose
recorded hash still matches.

## Exit codes

| Code | Meaning |
| ---: | --- |
| 0 | success |
| 1 | service, check, or proof failure |
| 2 | invalid arguments, workbook, specification, or generated-file drift |
| 3 | missing or failing required dependency |
