# SQL-first V5.0.0 dbt walkthrough

Every public cleaning, transformation, formatting, and validation macro returns
one SQL expression, keeping the model readable as ordinary SQL and Jinja.

## 1. Install the package graph

Before Package Hub publication:

{% raw %}
```yaml
packages:
  - git: "{{ env_var('DBT_DATA_ENGINEERING_TOOLKIT_GIT_URL') }}"
    revision: 5.0.0
  - git: "{{ env_var('DBT_DATA_ENGINEERING_TOOLKIT_GIT_URL') }}"
    revision: 5.0.0
    subdirectory: aliases/de_toolkit
```
{% endraw %}

After publication, replace the first entry with the canonical Hub package at `5.0.0`. Keep the
second Git entry when the short namespace is wanted.

## 2. Clean columns inline

{% raw %}
```sql
with distinct_source as (
    {{ dbt_data_engineering_toolkit.distinct_rows(ref('raw_customer_events')) }}
),

cleaned as (
    select
        {{ dbt_data_engineering_toolkit.clean_string('customer_id') }} as customer_id,
        {{ de_toolkit.clean_string('customer_name') }} as customer_name,
        {{ dbt_data_engineering_toolkit.clean_email('email') }} as email,
        {{ dbt_data_engineering_toolkit.clean_phone('phone') }} as phone,
        {{ dbt_data_engineering_toolkit.clean_boolean('active') }} as active,
        {{ dbt_data_engineering_toolkit.clean_numeric(
            'revenue', precision=18, scale=2
        ) }} as revenue,
        {{ dbt_data_engineering_toolkit.clean_date('signup_date') }} as signup_date
    from distinct_source
)
```
{% endraw %}

Alias each call like any selected SQL expression.

## 3. Map, default, convert, and format

JSON text and Jinja mappings are both supported:

{% raw %}
```sql
{{ dbt_data_engineering_toolkit.mapping(
    expression='status_code',
    mapping='{"A":"active","I":"inactive"}',
    default='unknown',
    data_type='string',
    format={'case': 'upper'},
    case_sensitive=false
) }} as status_label
```
{% endraw %}

Typed numeric output stays numeric:

{% raw %}
```sql
{{ de_toolkit.mapping(
    expression='price_band',
    mapping={
        'standard': '1234.5',
        'premium': '98765.432'
    },
    default=0,
    data_type={'name': 'numeric', 'precision': 18, 'scale': 2}
) }} as price_amount
```
{% endraw %}

Formatting a date produces presentation text:

{% raw %}
```sql
{{ de_toolkit.mapping(
    expression='event_code',
    mapping={
        'launch': '2026-09-04',
        'renewal': '2027-01-15'
    },
    default='2026-01-01',
    data_type='date',
    format={'pattern': '%d/%m/%Y'}
) }} as event_date_display
```
{% endraw %}

## 4. Validate visibly

{% raw %}
```sql
validated as (
    select
        *,
        {{ dbt_data_engineering_toolkit.is_email('email') }} as _email_valid,
        {{ de_toolkit.is_positive('revenue', allow_null=true) }} as _revenue_valid,
        {{ dbt_data_engineering_toolkit.rule_compare(
            'signup_date', '<=', 'current_date', allow_null=false
        ) }} as _signup_date_valid
    from mapped
)
```
{% endraw %}

Append messages and audit fields in the final projection:

{% raw %}
```sql
select
    *,
    {{ dbt_data_engineering_toolkit.assertions() }},
    {{ dbt_data_engineering_toolkit.audit_columns('demo_seed') }}
from validated
```
{% endraw %}

Quarantine models use `accepted_rows(ref(...))` and `rejected_rows(ref(...))`.

## 5. Run the full tooling

```bash
export DBT_DATA_ENGINEERING_TOOLKIT_GIT_URL=https://github.com/systemizing-solutions/dbt_data_engineering_toolkit.git

dbt deps --profiles-dir .
sqlfluff lint . --config .sqlfluff
dbt build --profiles-dir . --exclude package:dbt_project_evaluator

dbt run-operation generate_model_yaml \
  --profiles-dir . \
  --args '{model_names: [stg_customer_events]}'

dbt seed --profiles-dir . --select package:dbt_project_evaluator
dbt run --profiles-dir . --select package:dbt_project_evaluator
```

or replace the `env_var(...)` with `"https://github.com/systemizing-solutions/dbt_data_engineering_toolkit.git"` in the `packages.yml`.

`dbt_utils`, `dbt_assertions`, `codegen`, and `dbt_project_evaluator` are implementation
dependencies. Consumer models call the toolkit facade, so the underlying package can be replaced
without rewriting those models.
