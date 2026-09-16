# Compiler examples

`customer_360/` is generated from the workbook shipped at
`python/src/dbt_data_engineering_toolkit_compiler/resources/data_product_sample.xlsx`.
The only hand-maintained file inside the generated project is the example
`seeds/raw_customers.csv` fixture.

`customer_accounts/` is the V5.0.0 acceptance product generated from
`data_product_multi_source_sample.xlsx`. Its two seed files exercise two source
relations, two models, a many-to-one join, contextual mappings, a lookup,
multi-step cleaning, synchronized contract tests, warning behavior, and
quarantine views.

Regenerate it from the package root:

```bash
PYTHONPATH=python/src python3 -m dbt_data_engineering_toolkit_compiler generate \
  python/src/dbt_data_engineering_toolkit_compiler/resources/data_product_sample.xlsx \
  --project-dir examples/compiler/customer_360 --prune

PYTHONPATH=python/src python3 -m dbt_data_engineering_toolkit_compiler generate \
  python/src/dbt_data_engineering_toolkit_compiler/resources/data_product_multi_source_sample.xlsx \
  --project-dir examples/compiler/customer_accounts --prune
```

Then prove the complete flow:

```bash
export DBT_DATA_ENGINEERING_TOOLKIT_GIT_URL=https://github.com/systemizing-solutions/dbt_data_engineering_toolkit.git
det prove \
  python/src/dbt_data_engineering_toolkit_compiler/resources/data_product_multi_source_sample.xlsx \
  --project-dir examples/compiler/customer_accounts
```
