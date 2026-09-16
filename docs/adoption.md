# Team adoption playbook

Start with a working data product, then introduce governance as the team learns the workflow. Do not require a production workbook before anyone has seen generated dbt run.

## Day 1: prove the starter

```bash
det new customer_360
cd customer_360
det prove data_product.xlsx --project-dir .
```

The scaffold contains a validated sample workbook, two generated models, source definitions, contracts, tests, a DuckDB profile, and project documentation. Inspect `data_product.xlsx`, `models/`, and `contracts/` together so analysts and engineers can connect specification rows to ordinary dbt output.

Success means the proof reports that contract sync, dbt execution, tests, and evaluation passed in isolation.

## Week 1: replace the sample structure

Create a production-safe workbook or import an existing contract, DDL file, or dbt manifest:

```bash
det workbook build contracts/orders.xlsx
det workbook import contracts/imported_orders.xlsx --from-ddl schema.sql --identity-mappings
```

Choose one small real product. Record its owner, output schema, upstream sources, and copy mappings before adding complex transformations.

## Week 2: add contracts and behavior

Add quality rules to `Quality`. Add warning, quarantine, or failure behavior to `Operational Validation`. Keep generated SQL under review and use `det generate --dry-run` before publication.

```bash
det validate contracts/orders.xlsx
det generate contracts/orders.xlsx --project-dir build/orders --dry-run --prune
det generate contracts/orders.xlsx --project-dir build/orders --prune
```

## Week 3: make proof the delivery gate

Run the same isolated proof locally and in CI:

```bash
det prove contracts/orders.xlsx --project-dir build/orders
```

Require validation, generated-file sync, dbt tests, and proof before merging workbook or generated-project changes.

## Month 1: standardize selectively

Review repeated mappings, quality rules, ownership fields, and adapter settings across the first products. Standardize only patterns that have appeared in real delivery. Keep the starter scaffold for training and use governed workbooks for production products.

## Two supported modes

| Mode | Use it for | Entry command |
| --- | --- | --- |
| Starter | Evaluation, training, and the first working result | `det new customer_360` |
| Governed | Real schemas, contracts, mappings, and team delivery | `det workbook build` or `det workbook import` |

The modes use the same workbook, validator, generator, and proof pipeline. Moving to governed delivery does not require adopting a different runtime or rewriting generated dbt.
