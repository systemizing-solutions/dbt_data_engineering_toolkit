# Build your first data product

Choose the starter path for a working result first. Choose the governed path when you are ready to model a real schema.

## 1. Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e "./python"
```

The default install includes Data Contract CLI with Excel support, dbt Core, dbt-duckdb,
DuckDB, SQLFluff, and the dbt templater.

## 2. Scaffold and prove the starter

```bash
det new customer_360
cd customer_360
det prove data_product.xlsx --project-dir .
```

The first command creates a validated sample workbook and a generated DuckDB project containing contracts, two models, source definitions, tests, profiles, and documentation. The second command resolves packages and proves contract sync, SQL lint, dbt execution, tests, and evaluation in an isolated copy.

No package URL configuration is required for the public repository. Set `DBT_DATA_ENGINEERING_TOOLKIT_GIT_URL` only when you need to use a fork or mirror.

## 3. Start a governed product

```bash
cd ..
det workbook build contracts/orders.xlsx --no-input \
    --product-id orders \
    --name "Orders" \
    --domain sales
```

This production-safe path adds no demonstration rows, sources, mappings, rules, or lookups. It uses the same validation, generation, and proof pipeline as the starter.

## 4. Import an existing schema, if available

```bash
det workbook import contracts/imported_orders.xlsx --from-contract standard_odcs.xlsx
```

You can instead use ODCS YAML, SQL DDL, or a dbt `target/manifest.json`. For a workbook created in
step 3, use `det source import` to register upstream data and complete the output schema in Excel.

## 5. Complete the workbook

1. Set product identity and ownership in `Fundamentals`.
2. Define output fields in `Schema <model>`.
3. Add the model in `DET Models` and ordered inputs in `DET Model Inputs`.
4. Register physical inputs in `DET Sources` and `DET Source Schema`.
5. Add source-to-target operations in `DET Mapping` and `DET Parameters`.
6. Add key/value rows in `DET Lookups` where mappings need them.
7. Put contract rules in `Quality`.
8. Put warnings, quarantine, or runtime failure behavior in `Operational Validation` and
   `Operational Parameters`.

After structural edits:

```bash
det workbook refresh contracts/orders.xlsx
det validate contracts/orders.xlsx
```

## 6. Understand the generated SQL

Mappings compile to inline expressions, not a model-level dictionary:

{% raw %}
```sql
select
    {{ dbt_data_engineering_toolkit.clean_string('customer_name') }} as customer_name,
    {{ de_toolkit.mapping(
        expression='event_code',
        mapping={
            'launch': '2026-09-04',
            'renewal': '2027-01-15'
        },
        default='2026-01-01',
        data_type='date',
        format={'pattern': '%d/%m/%Y'}
    ) }} as event_date_display,
    {{ de_toolkit.is_email('email') }} as _email_valid
from {{ source('raw', 'customers') }}
```
{% endraw %}

Both namespaces are real dbt packages; no per-model Jinja alias is required.

## 7. Generate

```bash
det generate contracts/orders.xlsx --project-dir build/orders --dry-run --prune
det generate contracts/orders.xlsx --project-dir build/orders --prune
```

Generation creates ODCS and DET YAML, models, schema YAML, quarantine views, package/profile
configuration, `.sqlfluff`, a project README, and `.det-manifest.json`.

## 8. Check and prove

```bash
det check contracts/orders.xlsx --project-dir build/orders
det prove contracts/orders.xlsx --project-dir build/orders
```

`det prove` resolves packages in an isolated copy. The dbt manifest appears in that temporary proof project during execution. DET's `build/orders/.det-manifest.json` remains the persistent drift ledger.

Continue with the [team adoption playbook](adoption.md) for a staged route from the sample product to production governance.
