# dbt_data_engineering_toolkit

**A shared path from business requirements and source-to-target mappings to validated, readable and testable dbt data products.**

The goal is simple:

> **Align BAs, analysts and data engineers around the same data-product specification, validate the engineering intent early, and turn it into consistent, readable and testable dbt.**

Today, the path from a business requirement to a production dbt data product is often fragmented across:

* requirements and tickets
* source-to-target mapping spreadsheets
* data contracts
* transformation specifications
* quality rules
* documentation
* dbt models and tests
* engineer- or team-specific implementation patterns

`dbt_data_engineering_toolkit` closes that gap by providing a structured path from:

```text
Business Requirements
        ↓
Shared Data Product Definition
        ↓
Source-to-Target Mapping
        ↓
Transformations + Business Rules
        ↓
Data Quality + Operational Behaviour
        ↓
Validate Early
        ↓
Generate dbt
        ↓
dbt build / test / prove
```

The important part is that **the data-product specification becomes the collaboration point**.

BAs and analysts can help define **what the data product should do**, while data engineers retain control over **how it is implemented**.

Because the specification drives generation, the contract, documentation and implementation can remain aligned instead of slowly drifting apart.

And the result is still **ordinary dbt**.

No proprietary runtime.

No hidden transformation engine.

No model-level configuration dictionary that has to be decoded before someone can understand the SQL.

Generated models remain readable, reviewable and testable dbt projects.

## Quickstart: your first working data product

If you want the shortest path to a working result, use the starter flow:

```bash
det new customer_360
cd customer_360
det prove data_product.xlsx --project-dir .
```

`det new` creates and validates a populated starter workbook, then generates a reviewable DuckDB dbt project with contracts, models, tests, profiles, and project documentation. `det prove` installs the pinned packages and runs contract sync, lint, dbt execution, tests, and evaluation in isolation. No package URL configuration is required for the public repository; set `DBT_DATA_ENGINEERING_TOOLKIT_GIT_URL` only to override it.

Use [the team adoption playbook](docs/adoption.md) to progress from this starter to a governed product. For the full workbook workflow, continue with the walkthrough below.

## Table of contents

- [What is in this repository?](#what-is-in-this-repository)
- [Reusable dbt package](#-reusable-dbt-package)
- [Data-product compiler and CLI](#-data-product-compiler-and-cli)
- [The collaboration model](#the-collaboration-model)
- [Contract what vs implementation how](#contract-what-vs-implementation-how)
- [Release quality and compatibility](#release-quality-and-compatibility)
- [Maintainability architecture](#maintainability-architecture)
- [Safe, transactional generation](#safe-transactional-generation)
- [Complete workbook-to-dbt walkthrough](#complete-workbook-to-dbt-walkthrough)
  - [Step 1 - Install the compiler](#step-1--install-the-compiler)
  - [Step 2 - Create the controlled workbook](#step-2--create-the-controlled-workbook)
  - [Step 2A - Start from an existing structure](#step-2a--start-from-an-existing-structure)
  - [Step 3 - Define the product and output schema](#step-3--define-the-product-and-output-schema)
  - [Step 4 - Register or import source schemas](#step-4--register-or-import-source-schemas)
  - [Step 4A - Refresh workbook contextual choices](#step-4a--refresh-workbook-contextual-choices)
  - [Step 5 - Define models and ordered inputs](#step-5--define-models-and-ordered-inputs)
  - [Step 6 - Build source-to-target mappings](#step-6--build-source-to-target-mappings)
  - [Step 7 - Define quality and operational behaviour](#step-7--define-quality-and-operational-behaviour)
  - [Step 8 - Validate before generating](#step-8--validate-before-generating)
  - [Step 9 - Preview generation before publishing](#step-9--preview-generation-before-publishing)
  - [Step 10 - Inspect the generated data product](#step-10--inspect-the-generated-data-product)
  - [Step 11 - Install dependencies and run fast checks](#step-11--install-dependencies-and-run-fast-checks)
  - [Step 12 - Prove the generated dbt flow](#step-12--prove-the-generated-dbt-flow)
  - [Step 13 - Adopt generated code safely](#step-13--adopt-generated-code-safely)
- [Two supported dbt macro namespaces](#two-supported-dbt-macro-namespaces)
- [Documentation](#documentation)
- [Publishing and consuming V4.1.1](#publishing-and-consuming-v401)
- [Development gates](#development-gates)
- [Design principles](#design-principles)
- [The broader goal](#the-broader-goal)

---

# What is in this repository?

The toolkit contains two complementary components:

1. 🧱 **A reusable dbt package** providing a standard engineering vocabulary for common data-engineering work.
2. 🐍 **A Python compiler and CLI** for defining, validating, generating and proving complete dbt data products from controlled Excel or ODCS specifications.

They can be used together, but the dbt package can also be used independently.

---

# 🧱 Reusable dbt package

The dbt package provides an inline-first API for routine data-engineering work:

```text
define intent
  → contract transform
  → convert / interpret
  → standardize
  → map / default
  → derive
  → conform
  → validate
  → assert / route
  → present
```

The aim is to provide a **consistent engineering vocabulary** for work that otherwise tends to be implemented slightly differently across projects and engineers.

The sequence is a recommended conceptual flow, not a rigid macro order. Map it to the public API as follows:

| Stage | DET implementation |
| --- | --- |
| Define intent | Target schema and the operation chosen for the source value |
| Contract transform | A validated scalar SQL expression from ODCS `transformLogic`; no `SELECT`, `FROM`, `WHERE`, joins, or multiple statements |
| Convert / interpret | `convert_value()` or type-aware `clean_string()`, `clean_email()`, `clean_phone()`, `clean_numeric()`, `clean_integer()`, `clean_date()`, `clean_timestamp()`, `clean_boolean()`, or `clean_code()` |
| Standardize | `standardize_country()`, `standardize_currency()`, and optional `correct_errors()` |
| Map / default | `mapping()`, then `fill_missing()` or `mapping(default=...)` |
| Derive | Ordinary SQL expressions or a dedicated transformation macro; validation predicates do not derive values |
| Conform | Target data type, precision, scale, and canonical value, including `mapping(data_type=...)` or a type-aware `clean_*()` where appropriate |
| Validate | `is_email()`, `is_positive()`, `is_between()`, `is_in_list()`, `rule_compare()`, and other predicates |
| Assert / route | `assertions()`, `keep_valid_rows()`, and `keep_quarantined_rows()` |
| Present | Final string/display formatting, only when representation is part of the target |

Conversion is one of the first executable tasks after defining target intent. Use `convert_value()` when the target type is selected dynamically or a direct generic conversion best expresses the mapping. The type-specific `clean_*()` macros combine conversion with source interpretation and normalization; they are not a preliminary string-cleaning pass. A monetary string should normally go directly through `clean_numeric()`, and a date string through `clean_date()`.

Although `convert_value()` and the `format_*()` macros share `conversion_and_formatting.sql`, they occupy opposite ends of the conceptual flow: conversion establishes a typed value early, while `format_value()`, `format_number()`, and `format_temporal()` publish a display string only after semantic and business logic is complete.

ODCS `transformLogic` is executable when the target field also has a `DET Mapping`. It runs first, before the field's ordered conversion, cleaning, standardization, mapping, and default steps. To keep generated models composable and reviewable, DET accepts exactly one scalar SQL expression over fields from the model's declared inputs. For example:

```sql
upper(transaction_post_type_description)
```

Do not put `SELECT`, `FROM`, `WHERE`, joins, aliases, or multiple statements in property-level `transformLogic`. Row filtering is model-level behavior; an allowed-value requirement belongs in Operational Validation when it should flag, warn, or quarantine rows.

`det validate` parses each executable transform using the configured adapter's SQL dialect and rejects unknown or ambiguous input columns. `det check` then runs dbt parse and SQLFluff against the generated project; `det prove` performs isolated execution. Function availability and warehouse runtime behavior ultimately require `det prove` against the selected adapter.

`mapping()` spans several conceptual stages because it can map, default, convert, conform, and format in one expression. Treat `format` as a final presentation operation: do not use it inside `mapping()` while the value still needs date, numeric, semantic, or business logic. Prefer `mapping(data_type='date')`, perform date logic and validation on the resulting date, then format only if the published target genuinely requires text.

The workbook supports multiple ordered `DET Mapping` rows for the same target field. Express the pipeline explicitly as Step 1, Step 2, Step 3, and so on. `det validate` warns when recognized macro families appear outside the recommended sequence, but it does not reject an intentional alternative order; type compatibility and contract conformance remain enforced.

For example:

```text
convert_value()

clean_string()
clean_email()
clean_phone()
clean_numeric()
clean_date()
clean_timestamp()
clean_boolean()

standardize_country()
standardize_currency()

mapping()
fill_missing()

is_email()
is_positive()

assertions()
keep_valid_rows()
keep_quarantined_rows()

format_value()
format_number()
format_temporal()
...
```

Each macro behaves as a SQL-expression function, keeping transformation logic beside the column it affects.

```sql
select
    {{ dbt_data_engineering_toolkit.clean_string('customer_name') }} as customer_name,
    {{ de_toolkit.clean_email('email') }} as email,
    {{ dbt_data_engineering_toolkit.clean_numeric(
        'revenue',
        precision=18,
        scale=2
    ) }} as revenue,
    {{ dbt_data_engineering_toolkit.is_email('email') }} as _email_valid
from {{ source('raw', 'customers') }}
```

The API is deliberately **SQL-first**.

A developer should be able to read a model from top to bottom without first finding and decoding a separate transformation configuration.

The package delegates established primitives to existing dbt ecosystem packages where appropriate:

* `dbt_utils` for established utility primitives
* `dbt_assertions` for row-level assertions
* `codegen` for scaffolding
* `dbt_project_evaluator` for project-quality analysis

Those implementation namespaces do not need to appear in normal transformation models.

---

# 🐍 Data-product compiler and CLI

The Python package provides the `det` CLI and a controlled data-product compiler.

It allows a team to define a data product through a protected Excel workbook or existing ODCS structure using **business-friendly names for common dbt and data-engineering tasks**.

The workbook captures information such as:

* product identity and ownership
* target schemas and fields
* upstream sources and their schemas
* source-to-target mappings
* ordered transformations and cleaning rules
* model inputs
* joins
* expected join cardinality
* lookups
* model grain
* materialization
* contract enforcement
* data-quality requirements
* operational validation
* warn / reject / quarantine / fail behaviour
* SLA information
* support information
* server information
* pricing and other ODCS metadata

The compiler validates that specification and emits:

* canonical ODCS 3.1 YAML
* typed DET execution metadata
* dbt sources
* dbt models
* model YAML
* dbt contracts
* synchronized tests
* quarantine models
* project configuration
* SQLFluff configuration
* proof infrastructure
* generation manifests

The generated SQL is deliberately understandable **without the workbook or compiler**.

---

# The collaboration model

The workbook is not intended to replace engineering with Excel.

It exists to create a clearer collaboration boundary.

## BAs and analysts can help define

* what the product represents
* target fields
* business definitions
* source-to-target relationships
* transformation intent
* mapping decisions
* lookup values
* quality expectations
* ownership
* support expectations
* SLA and contract metadata

## Data engineers retain control over

* source structures
* model architecture
* model inputs
* grains
* joins
* cardinality
* physical types
* transformation implementation
* operational validation
* materialization
* dbt contracts
* generated SQL
* deployment
* execution
* proof

The specification therefore becomes a shared representation of the product without pretending that every participant needs to understand Jinja, warehouse SQL or dbt internals.

---

# Contract **what** vs implementation **how**

A key design principle is the separation between:

> **What does this data product promise?**

and:

> **How will dbt implement that promise?**

ODCS remains authoritative for the data contract.

DET adds the execution metadata needed to turn those promises into a deterministic implementation.

The workbook therefore separates official ODCS surfaces from DET implementation surfaces.

| Workbook tabs                                                                                                                              | Responsibility                                                                               |
| ------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| `Fundamentals`, `Schema <model>`, `Relationships`, `Quality`, `SLA`, `Servers`, `Team`, `Roles`, `Support`, `Pricing`, `Custom Properties` | Official ODCS identity, ownership, schema and service promises                               |
| `DET Models`, `DET Model Inputs`                                                                                                           | dbt layers, materializations, grains, contract enforcement and ordered input relations       |
| `DET Sources`, `DET Source Schema`                                                                                                         | First-class dbt sources and their importable columns, keys and types                         |
| `DET Mapping`, `DET Parameters`, `DET Lookups`                                                                                             | Compact source-to-target rows, normalized operation parameters and key/value maps            |
| `Quality`                                                                                                                                  | Authoritative visible ODCS 3.1 contract-quality rules                                        |
| `DET Relationships`                                                                                                                        | Explicit joins and cardinality review                                                        |
| `Operational Validation`, `Operational Parameters`                                                                                         | Runtime warning, quarantine and implementation-validation behaviour                          |
| `DET Build`                                                                                                                                | Adapter, profile, schema, published Git URL environment variable and pinned toolkit revision |
| `_DET Context`, `_DET Lists`, `_DET Metadata`, `_DET Raw ODCS`                                                                             | Protected compiler context and round-trip state                                              |

---

# Release quality and compatibility

V4.1.1 has explicit release gates for both the Python compiler and dbt package.

| Gate                                      |    V4.1.1 result |
| ----------------------------------------- | ---------------: |
| Python statement coverage                 |           85.01% |
| dbt DuckDB-scoped implementation coverage | 98.53% — 134/136 |
| dbt public-API direct execution coverage  |   100% — 104/104 |

Both coverage gates fail below 80%.

dbt Core is tested for:

* BigQuery
* Snowflake
* DuckDB
* Databricks
* Redshift
* Athena
* ClickHouse
* Spark

PostgreSQL is also supported by the compiler adapter configuration.

The package follows dbt's Fusion compatibility guidance and tests Fusion for every requested platform for which Fusion currently provides an adapter.

Athena and ClickHouse are explicitly Core-only.

See:

* [Compatibility](docs/compatibility.md)
* [Testing](docs/testing.md)

for the exact proof level and credentialed warehouse matrix.

---

# Maintainability architecture

The dbt SQL API and compiler are deliberately separated.

```text
CLI / future API
       ↓
ToolkitApplication
       ↓
workbook · import · validation · emission · proof services
       ↓
file · workbook · dbt · SQLFluff · Data Contract brokers
```

External libraries and commands are confined to brokers.

Format-specific parsers produce one typed:

```text
ImportedDataStructure
```

Independent validators return stable error codes such as:

```text
DET-MAP-004
```

Independent emitters return artifacts without directly writing files.

The `de_toolkit` facade is generated from canonical macro signatures so that the canonical and short namespaces cannot drift independently.

See [Architecture](docs/architecture.md).

---

# Safe, transactional generation

Generation is performed as a single post-synchronization transaction:

```text
workbook
    ↓
typed specification
    ↓
staged ODCS / DET / dbt
    ↓
Data Contract synchronization
    ↓
synchronized validation
    ↓
final hashes
    ↓
atomic publish
```

If synchronization, linting or synchronized-output validation fails, the existing project and its `.det-manifest.json` remain byte-for-byte untouched.

A failed generation therefore does not leave a partially updated dbt project behind.

---

# Complete workbook-to-dbt walkthrough

The following is the complete compiler workflow.

Commands assume you are running from the extracted `dbt_data_engineering_toolkit` repository unless stated otherwise.

---

## Step 1 — Install the compiler

Create a virtual environment and install the Python compiler:

```bash
python -m venv .venv-compiler
source .venv-compiler/bin/activate

python -m pip install -e "./python"
```

That installation includes:

* the DET compiler
* Data Contract CLI
* dbt Core
* the DuckDB adapter
* the tested DuckDB 1.4 runtime
* SQLFluff
* SQLFluff's dbt templater

Data Contract and dbt are normal runtime dependencies.

There is no separate optional compiler extra required for the default workflow.

The compiler requires **Python 3.11 or later**.

Excel itself is not required to execute the compiler.

---

# Step 2 — Create the controlled workbook

Create a new product definition:

```bash
det workbook build orders_data_product.xlsx
```

The generated workbook is an **official ODCS Excel-template superset**.

Its standard sheets can be interpreted by Data Contract CLI, while DET-specific sheets describe executable dbt behaviour.

When running interactively, the command asks for:

* Product ID
* name
* domain
* purpose
* owner
* whether an initial model row should be created
* whether Customer 360 demonstration data should be included

Demo data defaults to **No**.

For automation or CI:

```bash
det workbook build orders_data_product.xlsx \
  --no-input \
  --product-id orders_data_product \
  --name "Orders Data Product" \
  --domain sales \
  --owner "Sales Analytics"
```

This creates a production-safe workbook with no:

* sources
* mappings
* rules
* lookups
* sample-data rows

The filename is used only as the default Product ID.

No fixed Customer identity is injected into normal workbooks.

Training data is an explicit opt-in:

```bash
det workbook build customer_360_demo.xlsx \
  --no-input \
  --sample-customer-data
```

---

## Workbook safety and metadata

Do not rename workbook tabs or columns.

Yellow/dropdown cells are the supported business-facing authoring interface.

Protected sheets use the password:

```text
det
```

This protection exists only to prevent accidental edits.

It is **not a security boundary**.

`_DET Lists` and `_DET Metadata` are very hidden.

The same operator registry drives:

* workbook dropdowns
* compiler validation
* accepted parameters
* type flow
* generated macro names
* registry versioning
* registry fingerprinting stored in `_DET Metadata`

This keeps the authoring experience and compiler behaviour aligned.

---

# Step 2A — Start from an existing structure

You do not need to manually recreate an existing schema.

DET can build its workbook from:

* ODCS YAML
* standard ODCS Excel
* SQL DDL
* dbt manifests

### Existing ODCS YAML

```bash
det workbook import orders.xlsx \
  --from-contract orders.odcs.yaml
```

### Existing standard ODCS workbook

```bash
det workbook import orders.xlsx \
  --from-contract standard_odcs.xlsx
```

### SQL DDL

```bash
det workbook import orders.xlsx \
  --from-ddl orders.sql
```

### dbt manifest

```bash
det workbook import orders.xlsx \
  --from-dbt-manifest upstream/target/manifest.json
```

For `.xlsx` input, DET delegates official workbook interpretation to Data Contract CLI.

The workflow is:

```text
Official ODCS Excel
        ↓
Data Contract CLI
        ↓
Canonical temporary ODCS YAML
        ↓
DET ODCS importer
        ↓
DET workbook
```

DET does **not** maintain a second independent parser for the official ODCS Excel format.

Each import creates:

* `Fundamentals`
* one `Schema <model>` tab per imported object
* matching `DET Models` rows

Mapping, parameter, rule and lookup decisions remain empty for review.

Imported models are disabled by default so incomplete transformation logic cannot accidentally be generated.

Enable the model only after defining its inputs and mappings.

---

## Explicit identity mappings

DET deliberately does **not** assume:

```text
target field = same-named source field
```

If the imported structure genuinely represents a one-to-one source, opt into identity mappings explicitly:

```bash
det workbook import orders.xlsx \
  --from-ddl orders.sql \
  --identity-mappings
```

This also enables the imported models.

Identity mappings are never inferred by default because treating a published target automatically as its own source can hide the real transformation logic.

The broader Data Contract CLI import/export formats remain documented in:

* [Official import guide](https://docs.datacontract.com/imports)
* [Excel export guide](https://docs.datacontract.com/exports/excel)

---

# Step 3 — Define the product and output schema

Open `Fundamentals` and define the product-level information.

Typical fields include:

* stable Product ID
* name
* version
* status
* domain
* purpose
* owner

Product ID must use lowercase snake case because it becomes the dbt project name.

For example:

```text
orders_data_product
```

---

## Define published fields

In each:

```text
Schema <model>
```

tab, define one row for each published field.

Example:

| Property         | Logical Type | Physical Type              | Required | Primary Key | DET Implementation |
| ---------------- | ------------ | -------------------------- | -------- | ----------- | ------------------ |
| `customer_id`    | `string`     | `varchar`                  | Yes      | Yes         | `mapped`           |
| `email`          | `string`     | `varchar`                  | No       | No          | `mapped`           |
| `_det_loaded_at` | `timestamp`  | `timestamp with time zone` | No       | No          | `audit`            |

Every published field must either:

* be implemented through mapping
* be declared `audit`
* be declared `system-generated`

These rows become:

* ODCS properties
* dbt model column contracts

Required, primary-key and unique constraints are synchronized into dbt tests through Data Contract CLI.

DET does not create a second competing representation of the same constraints.

---

## Advanced ODCS properties

Common business-facing columns such as:

* Primary Key
* DET Implementation

remain visible by default.

Advanced ODCS fields are grouped and hidden, rather than removed.

Expand the group when you need fields such as:

* constraints
* encryption
* transform metadata
* complex-type definitions

Imported ODCS extensions are retained inside:

```text
_DET Raw ODCS
```

and merged back during emission rather than being silently discarded.

---

# Step 4 — Register or import source schemas

This step defines the upstream tables that generated models are allowed to read.

`DET Sources` gives each source table a short workbook relation name.

Example:

| Relation        | Source Name | Table Name      |
| --------------- | ----------- | --------------- |
| `crm_customers` | `raw`       | `raw_customers` |

You may enter `DET Source Schema` manually, but importing the structure is safer.

---

# Importing source metadata from dbt

First generate an upstream manifest from the **upstream dbt project's directory** — the directory containing its `dbt_project.yml`.

```bash
cd /absolute/path/to/upstream_dbt_project

dbt deps --profiles-dir /absolute/path/to/profiles

dbt parse --profiles-dir /absolute/path/to/profiles

test -f target/manifest.json
```

`dbt deps` installs packages required by that upstream project.

`dbt parse`:

* validates Jinja
* validates YAML
* produces `manifest.json`
* does **not** query the warehouse

By default, the manifest is created at:

```text
<upstream project>/target/manifest.json
```

relative to the active `dbt_project.yml`.

If the upstream project overrides `--target-path`, use that directory instead.

Relevant dbt documentation:

* [Manifest contents and location](https://docs.getdbt.com/reference/artifacts/manifest-json)
* [`dbt parse`](https://docs.getdbt.com/reference/commands/parse)

---

## Import the upstream sources

Return to the toolkit directory and provide the absolute manifest path:

```bash
cd /absolute/path/to/dbt_data_engineering_toolkit

det source import \
  --workbook orders_data_product.xlsx \
  --from-dbt-manifest /absolute/path/to/upstream_dbt_project/target/manifest.json \
  --replace
```

You can also import from a contract:

```bash
det source import \
  --workbook orders_data_product.xlsx \
  --from-contract upstream.odcs.yaml \
  --relation crm_customers \
  --replace
```

Or DDL:

```bash
det source import \
  --workbook orders_data_product.xlsx \
  --from-ddl raw_customers.sql \
  --relation crm_customers \
  --source-name raw \
  --replace
```

The inputs behave as follows:

| Input                 | What DET reads                                                         | What you may need to change                                                              |
| --------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `--from-dbt-manifest` | Every declared dbt `source` and documented columns                     | Run `dbt parse` again when upstream YAML changes and provide the new manifest            |
| `--from-contract`     | ODCS schema objects and properties                                     | Use `--relation` only for a single-schema contract when you want another workbook alias  |
| `--from-ddl`          | `CREATE TABLE` names, columns, types, nullability and inline key hints | Set the intended dbt `--source-name`; use one DDL table when also supplying `--relation` |

---

## `--replace` behaviour

`--replace` only removes and recreates the imported:

* source relations
* source-column rows

It does **not** overwrite:

* target schemas
* mappings
* parameters
* lookups
* quality rules

Without `--replace`, the importer:

* updates matching fields
* adds new fields

---

## Do not confuse the two manifests

Two unrelated files called manifests appear in the full workflow.

| File                                        | Created by     | Purpose                                                              |
| ------------------------------------------- | -------------- | -------------------------------------------------------------------- |
| `upstream_dbt_project/target/manifest.json` | `dbt parse`    | Discovery input describing models, sources, columns and dependencies |
| `generated_project/.det-manifest.json`      | `det generate` | Hash ledger used to detect generated-file drift                      |

The first is an input from dbt.

The second is DET's generation ledger.

The source schema loaded into the workbook allows the compiler to reject issues such as:

* misspelled source fields
* incompatible operation input types
* invalid join keys

before generation.

---

# Step 4A — Refresh workbook contextual choices

Import and synchronization commands refresh workbook controls automatically.

If you manually add or rename:

* models
* schema properties
* source relations
* operations
* lookups

close Excel and run:

```bash
det workbook refresh orders_data_product.xlsx
```

Then reopen the workbook.

Contextual validation lists are rebuilt so that:

* Target Field is restricted by Model
* Source Field is restricted by Source Relation
* join keys are restricted by relation
* Input Relation is restricted by model
* Parameter is restricted by operation
* Value is restricted by operation
* Lookup is restricted to declared lookup names

These workbook controls help authors avoid invalid choices.

They are not the authoritative validation layer.

`det validate` remains authoritative.

---

# Step 5 — Define models and ordered inputs

Each row in `DET Models` defines a generated model.

Example:

| Model           | Layer     | Materialization | Grain         | Enforce Contract |
| --------------- | --------- | --------------- | ------------- | ---------------- |
| `stg_customers` | `staging` | `table`         | `customer_id` | Yes              |

Then define model inputs in:

```text
DET Model Inputs
```

Example:

| Model           | Order | Input Relation  |
| --------------- | ----: | --------------- |
| `stg_customers` |     1 | `crm_customers` |

The compiler validates issues such as:

* missing model inputs
* missing grain fields
* model dependency cycles
* source relations referenced outside declared model inputs
* unsafe many-to-many relationships

before dbt is invoked.

`incremental` materialization is deliberately not advertised in V4.1.1 until watermark and merge semantics are fully declarative.

---

# Step 6 — Build source-to-target mappings

`DET Mapping` is deliberately compact.

Each row identifies:

* Model
* Target Field
* Source Relation
* Source Field
* Step
* Operation

Example:

| Model           | Target Field | Source Relation | Source Field    | Step | Operation     |
| --------------- | ------------ | --------------- | --------------- | ---: | ------------- |
| `stg_customers` | `email`      | `crm_customers` | `email_address` |    1 | `Clean email` |

Multiple rows against the same target field represent ordered transformation steps:

```text
Step 1
   ↓
Step 2
   ↓
Step 3
```

Operation-specific options are stored separately in `DET Parameters`.

This avoids turning the source-to-target mapping into a 20+ column configuration form.

---

# Example — mapping and formatting a value

Suppose the target field is:

```text
event_date_display
```

and the source contains:

```text
event_code
```

The mapping could be:

| Model           | Target Field         | Source Relation | Source Field | Step | Operation    |
| --------------- | -------------------- | --------------- | ------------ | ---: | ------------ |
| `stg_customers` | `event_date_display` | `crm_customers` | `event_code` |    1 | `Map values` |

Its parameters are declared separately:

| Model           | Target Field         | Step | Parameter        | Value         |
| --------------- | -------------------- | ---: | ---------------- | ------------- |
| `stg_customers` | `event_date_display` |    1 | `Lookup`         | `event_dates` |
| `stg_customers` | `event_date_display` |    1 | `Default`        | `2026-01-01`  |
| `stg_customers` | `event_date_display` |    1 | `Data Type`      | `date`        |
| `stg_customers` | `event_date_display` |    1 | `Format Pattern` | `%d/%m/%Y`    |

And the lookup itself is defined in:

```text
DET Lookups
```

| Lookup        | Source Value | Target Value |
| ------------- | ------------ | ------------ |
| `event_dates` | `launch`     | `2026-09-04` |
| `event_dates` | `renewal`    | `2027-01-15` |

The generated model remains understandable SQL/Jinja:

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

There is no:

```text
select_cleaned
```

macro and no model-level cleaning dictionary.

The compiler emits source/ref CTEs and inline `de_toolkit` expressions.

---

# End-to-end type flow

The compiler tracks the inferred type after every transformation step.

It then compares the final type against the declared target type in:

```text
Schema <model>
```

For example, formatting a date using:

```text
%d/%m/%Y
```

produces a published string representation.

It does **not** remain a date simply because the input began as a date.

This type flow is validated before generation.

---

# Step 7 — Define quality and operational behaviour

The toolkit deliberately separates:

1. **contract-level data quality**
2. **runtime operational handling**

---

## Contract quality

Contract-level rules belong in the visible official ODCS:

```text
Quality
```

sheet.

Supported ODCS quality rule forms include:

* `library`
* `sql`
* `custom`
* `text`

The `Quality` sheet is authoritative and is consumed directly by the compiler.

Library rules map workbook:

* rule
* operator
* value

fields into canonical `QualityRule` objects.

Advanced columns preserve:

* stable rule IDs
* dimensions
* JSON ODCS passthrough fields

There is one contract-quality authoring surface:

```text
Quality
```

---

## Schema-level constraints

Properties such as:

* Required
* Primary Key
* Unique

belong to the ODCS schema.

For `fail build` behaviour, those constraints remain owned by ODCS schema flags.

DET does not create a second representation.

---

## Operational validation

Runtime row-routing and cross-field predicates belong in:

```text
Operational Validation
```

Each rule explicitly defines its failure behaviour.

| Failure      | Generated behaviour                                                              |
| ------------ | -------------------------------------------------------------------------------- |
| `Allow`      | Rule is documented; row continues                                                |
| `Warn`       | Named item is added to `_det_warnings`; row continues                            |
| `Reject row` | Named item is added to `_det_rejections`; valid and rejected views are generated |
| `Fail build` | Singular dbt test is generated with error severity                               |

`Unique` is rejected for `Warn` and `Reject row` because uniqueness is aggregate logic and cannot safely be represented as a row-level `where` predicate.

---

## Example generated validation

Email and revenue rules might compile to:

```sql
validated as (
    select
        *,
        {{ de_toolkit.is_email(
            'email',
            allow_null=false
        ) }} as _email_invalid_valid,

        {{ de_toolkit.is_positive(
            'revenue',
            allow_null=true
        ) }} as _revenue_not_positive_valid

    from transformed_01
)
```

The implementation remains inspectable.

---

# Join cardinality as executable intent

Relationships do more than describe joins.

Declared cardinality is also used as a validation and testing signal.

For:

* one-to-one
* one-to-many
* many-to-one

relationships, the compiler can generate uniqueness tests on the side expected to be unique.

Unsafe many-to-many relationships are surfaced before dbt execution.

This turns cardinality from documentation into an explicit engineering constraint.

---

# Step 8 — Validate before generating

Run:

```bash
det validate orders_data_product.xlsx
```

A safe blank workbook may produce:

```text
Valid: Orders Data Product (0 models, 0 mapped columns, 0 rules)
```

The explicit multi-source demonstration workbook may produce:

```text
Valid: Customer Accounts (2 models, 12 mapped columns, 2 rules)
```

Validation covers areas including:

* identifiers
* model inputs
* source fields
* target fields
* source-to-target mappings
* end-to-end type flow
* required parameters
* irrelevant parameters
* published-field implementation
* lookup names
* duplicate mappings
* duplicate rules
* model dependency cycles
* grain fields
* ODCS quality vocabulary
* join relationships
* join keys
* join cardinality

Errors identify:

* the relevant workbook sheet
* the row
* the business problem
* a suggested correction

The aim is to move problems left:

> **Catch engineering inconsistencies in the product specification before they become dbt implementation defects.**

---

# Step 9 — Preview generation before publishing

Inspect the current generated state:

```bash
det status orders_data_product.xlsx \
  --project-dir build/orders
```

Preview all final post-sync file operations:

```bash
det generate orders_data_product.xlsx \
  --project-dir build/orders \
  --dry-run \
  --prune
```

Then generate:

```bash
det generate orders_data_product.xlsx \
  --project-dir build/orders \
  --prune
```

To produce only canonical contract artifacts:

```bash
det compile orders_data_product.xlsx \
  --output-dir build/contracts
```

---

# Dry-run means real validation, not fake generation

Both:

```text
det status
```

and:

```text
det generate --dry-run
```

create a disposable staged project.

They perform the real Data Contract synchronization against that staging area.

They do not publish the result.

Normal generation publishes only after:

* synchronized YAML validates
* synchronized tests validate
* final output validation succeeds

---

# Reproducible cache handling

Generated project caches such as:

```text
target/
logs/
dbt_packages/
```

are intentionally invalidated after successful publication.

They are not copied into the generation transaction.

These are reproducible runtime artifacts rather than authoritative generated source.

---

# Deterministic generation

Generation intentionally writes no timestamps into generated files.

Given the same:

* workbook
* compiler
* registry
* ODCS behaviour
* adapter configuration

the generated content should remain deterministic.

This makes diffs meaningful and supports drift detection.

---

# `.det-manifest.json`

Generation creates:

```text
.det-manifest.json
```

The manifest tracks the final post-sync state, including information such as:

* generated file hashes
* workbook hash
* compiler version
* workbook version
* operator registry version
* operator registry fingerprint
* ODCS version
* selected adapter
* artifact authority
* compiler ownership
* Data Contract ownership

If a generated file is manually changed, a later generation refuses to silently overwrite it.

The expected resolution is to:

1. move the intended change back into the workbook or compiler, or
2. explicitly review and use `--force` only as a recovery mechanism

`--prune` only deletes unchanged files that the previous manifest proves were generated.

---

# Step 10 — Inspect the generated data product

A generated project contains ordinary dbt and contract artifacts.

Example:

```text
contracts/
    orders_data_product.odcs.yaml
    orders_data_product.det.yaml

models/
    sources.yml

    staging/
        stg_orders.sql
        stg_orders.yml

    quarantine/
        stg_orders_valid.sql
        stg_orders_rejected.sql

tests/
    datacontract_cli/
    ...

dbt_project.yml
packages.yml
profiles.yml

.sqlfluff
.sqlfluffignore

Makefile
README.md

.det-manifest.json
```

ODCS describes **what the product promises**.

DET metadata describes **how those promises become dbt**.

The generated dbt project remains understandable and reviewable even when neither the workbook nor compiler is open.

---

# Generated dbt remains normal dbt

This is an intentional design requirement.

For example:

```sql
select
    {{ de_toolkit.clean_string('customer_name') }} as customer_name,
    {{ de_toolkit.clean_email('email') }} as email,
    {{ de_toolkit.standardize_country('country') }} as country_code
from {{ source('crm', 'customers') }}
```

The workbook helps define the implementation.

The compiler helps validate and generate the implementation.

But the generated SQL remains:

* readable
* reviewable
* testable
* executable
* extendable

dbt.

The toolkit does not introduce a proprietary execution layer between the engineer and the warehouse.

---

# Step 11 — Install dependencies and run fast checks

Generated `packages.yml` contains no local filesystem package path.

It installs the canonical `dbt/` package and, when required, the `aliases/de_toolkit` project from the same published repository revision configured in `DET Build`.

Set the repository URL:

```bash
export DBT_DATA_ENGINEERING_TOOLKIT_GIT_URL=https://github.com/systemizing-solutions/dbt_data_engineering_toolkit.git
```

Install dbt dependencies:

```bash
cd build/orders

dbt deps --profiles-dir .

cd ../..
```

Then run:

```bash
det check orders_data_product.xlsx \
  --project-dir build/orders
```

---

# What `det check` does

`det check` performs fast generated-project verification.

It:

1. delegates ODCS schema validation to the Data Contract Python API
2. executes:

```text
datacontract dbt sync --dry-run
```

as a consistency check

3. parses the generated dbt project
4. executes SQLFluff using the dbt templater and generated `.sqlfluff`

Data Contract, dbt and SQLFluff are all part of the default compiler dependency set.

The emitted contract targets current:

```text
ODCS v4.1.1
```

Relevant documentation:

* [ODCS guide](https://docs.datacontract.com/open-data-contract-standard)
* [Quality-rule guide](https://docs.datacontract.com/quality-rules)
* [Data Contract dbt synchronization](https://docs.datacontract.com/commands/dbt/sync)
* [SQLFluff dbt templater configuration](https://docs.sqlfluff.com/en/stable/configuration/templating/dbt.html)
* [dbt package dependency format](https://docs.getdbt.com/docs/build/packages)

To run only SQL linting:

```bash
det lint --project-dir build/orders
```

---

# Adapter configuration and credentials

`DET Build` selects an adapter provider.

DuckDB works immediately for local execution.

Profiles for:

* BigQuery
* Snowflake
* Databricks
* Redshift
* Athena
* ClickHouse
* Spark
* PostgreSQL

contain only:

```text
env_var(...)
```

references.

The required warehouse adapter/extra must be installed in the execution environment.

Credentials are never stored in:

* the workbook
* generated profiles

The generated README lists the exact environment variables required by the selected adapter.

---

# Step 12 — Prove the generated dbt flow

Run the full release-grade proof:

```bash
det prove orders_data_product.xlsx \
  --project-dir build/orders
```

`det prove` copies the generated project into a disposable sibling directory.

It then performs the actual workflow against that copy.

Conceptually:

```text
generated project
        ↓
disposable proof copy
        ↓
install dependencies
        ↓
real Data Contract synchronization
        ↓
seed available source fixtures
        ↓
dbt parse
        ↓
dbt build
        ↓
execute synchronized tests
        ↓
SQLFluff
        ↓
dbt_project_evaluator
```

The original generated project remains unchanged.

---

# Realistic multi-source proof fixture

The repository includes an optional realistic fixture at:

```text
python/src/dbt_data_engineering_toolkit_compiler/resources/
data_product_multi_source_sample.xlsx
```

Its generated project is checked in at:

```text
examples/compiler/customer_accounts
```

The example demonstrates:

* two sources
* two models
* a many-to-one join
* a lookup
* multi-step cleaning
* contract tests
* a warning
* rejected rows
* valid-row views
* quarantine behaviour

Its source seeds make the proof self-contained.

Run:

```bash
cd examples/compiler/customer_accounts

export DBT_DATA_ENGINEERING_TOOLKIT_GIT_URL=https://github.com/systemizing-solutions/dbt_data_engineering_toolkit.git

dbt deps

dbt seed \
  --profiles-dir . \
  --exclude package:dbt_project_evaluator

dbt build \
  --profiles-dir . \
  --exclude package:dbt_project_evaluator

dbt seed \
  --profiles-dir . \
  --select package:dbt_project_evaluator

dbt run \
  --profiles-dir . \
  --select package:dbt_project_evaluator
```

or replace the `env_var(...)` with `"https://github.com/systemizing-solutions/dbt_data_engineering_toolkit.git"` in the `packages.yml`.

Expected proof includes:

* two seeds
* both contract-enforced models
* 14 product build nodes
* synchronized ODCS tests
* both quarantine views
* 48 evaluator models

passing successfully.

The checked-in example project is already contract-synchronized through `det generate`.

Running Data Contract synchronization manually against it would bypass DET's:

* atomic write behaviour
* path normalization
* manifest tracking

Sample data is never added by the normal `det workbook build` command unless explicitly requested.

---

# Step 13 — Adopt generated code safely

There are two distinct update paths:

1. changes to the **authoritative product specification**
2. changes to **custom downstream implementation**

Do not mix them.

| What changed                                       | Authoritative edit                                             | Safe commands                                                     |
| -------------------------------------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------- |
| Business contract, source, mapping, lookup or rule | Edit the workbook                                              | `det status`, dry-run generation, generation, check, prove        |
| Upstream ODCS / DDL / dbt structure                | Re-import using `det workbook sync`                            | Review changes, repair mappings, validate and regenerate          |
| Custom project-only SQL                            | Create a separate non-generated model downstream               | Normal lint/build workflow; do not add it to `.det-manifest.json` |
| Compiler/emitter behaviour                         | Change toolkit source and publish a new revision               | Regenerate and review the complete diff                           |
| Accidental edit to generated content               | Restore the file or move the intended change into the workbook | `det status` detects drift; `--force` is recovery-only            |

---

# Normal workbook-authoritative workflow

The normal product-change sequence is:

```bash
det validate contracts/orders_data_product.xlsx

det status \
  contracts/orders_data_product.xlsx \
  --project-dir dbt_orders

det generate \
  contracts/orders_data_product.xlsx \
  --project-dir dbt_orders \
  --dry-run \
  --prune

det generate \
  contracts/orders_data_product.xlsx \
  --project-dir dbt_orders \
  --prune

det check \
  contracts/orders_data_product.xlsx \
  --project-dir dbt_orders

det prove \
  contracts/orders_data_product.xlsx \
  --project-dir dbt_orders
```

In short:

```text
edit
  ↓
validate
  ↓
inspect drift
  ↓
preview
  ↓
generate
  ↓
check
  ↓
prove
```

---

# Synchronizing upstream structural changes

When an external schema changes:

```bash
det workbook sync \
  contracts/orders_data_product.xlsx \
  --from-contract upstream_orders.odcs.yaml
```

The default behaviour is an additive/update merge.

Existing rows in:

* `DET Mapping`
* `DET Parameters`
* `Operational Validation`
* `DET Lookups`

are retained.

Use:

```text
--replace-schema
```

only when fields removed upstream should also be removed from target schema tabs.

If an existing mapping now references a removed or incompatible field, DET deliberately does **not** delete the mapping silently.

Instead:

```bash
det validate
```

surfaces the inconsistency for review.

---

# Two supported dbt macro namespaces

dbt does not provide a global Python-style package alias in `packages.yml`.

A Jinja assignment such as:

```jinja
{% set de_toolkit = dbt_data_engineering_toolkit %}
```

is scoped only to the model where it is declared.

V4.1.1 therefore provides a real companion dbt package called:

```text
de_toolkit
```

Once both package roots are installed, either form works globally.

Canonical namespace:

```sql
{{ dbt_data_engineering_toolkit.clean_string('customer_name') }}
```

Short namespace:

```sql
{{ de_toolkit.clean_string('customer_name') }}
```

Example:

```sql
select
    {{ dbt_data_engineering_toolkit.clean_string(
        'customer_name'
    ) }} as canonical_name,

    {{ de_toolkit.clean_string(
        'customer_name'
    ) }} as short_name

from {{ ref('raw_customers') }}
```

The short package contains only generated thin wrappers.

`dbt_data_engineering_toolkit` remains the actual implementation and dependency boundary.

Both namespaces therefore execute the same behaviour.

---

# Documentation

The README provides the complete conceptual and operational flow.

More focused guides are available for deeper reference.

| Need                                                | Guide                                           |
| --------------------------------------------------- | ----------------------------------------------- |
| Shortest runnable path                              | [Quickstart](docs/quickstart.md)                |
| Every `det` command and its side effects            | [CLI reference](docs/cli.md)                    |
| ODCS, DDL and manifest conversion                   | [Import and synchronization](docs/imports.md)   |
| Workbook edits, code edits and generated-file drift | [Updating safely](docs/updating.md)             |
| Broker → Service → Exposer architecture             | [Architecture](docs/architecture.md)            |
| Adapter and Fusion support matrix                   | [Compatibility](docs/compatibility.md)          |
| Coverage definitions and commands                   | [Testing](docs/testing.md)                      |
| GitHub release and dbt Package Hub submission       | [Deployment](docs/deployment.md)                |
| Full dbt-only walkthrough and recipes               | [SQL walkthrough](docs/sql_walkthrough.md)      |
| First public release details                        | [V4.1.1 release notes](V4.1.1_RELEASE_NOTES.md) |

---

# Publishing and consuming V4.1.1

Before the canonical package is accepted into dbt Package Hub, pin the Git release.

For only the canonical namespace:

```yaml
packages:
  - git: "https://github.com/systemizing-solutions/dbt_data_engineering_toolkit.git"
    revision: v4.1.1
    subdirectory: dbt
```

To also install the short `de_toolkit` namespace:

```yaml
packages:
  - git: "https://github.com/systemizing-solutions/dbt_data_engineering_toolkit.git"
    revision: v4.1.1

  - git: "https://github.com/systemizing-solutions/dbt_data_engineering_toolkit.git"
    revision: v4.1.1
    subdirectory: aliases/de_toolkit
```

After the canonical project is listed on Package Hub, consumers may install it using:

```yaml
package: systemizing-solutions/dbt_data_engineering_toolkit
```

The short:

```text
de_toolkit
```

namespace remains a second dbt project.

Either:

* retain the Git subdirectory dependency, or
* publish the alias project as its own top-level repository/package

dbt does not provide package-level Python-style aliases.

The complete release, Package Hub submission, verification and rollback commands are documented in:

[Deployment](docs/deployment.md)

---

# Development gates

Install test dependencies:

```bash
python -m pip install -e "./python[test]"
```

Validate that the alias package still matches the canonical API:

```bash
python scripts/generate_alias_facade.py --check
```

Run static checks:

```bash
python scripts/static_check.py
```

Run the broader project quality gates:

```bash
make quality
make python-coverage
make dbt-coverage
make codegen evaluator
```

V4.1.1 supports:

```text
dbt Core 1.10.6+
```

and declares the Fusion-compatible range:

```text
>=1.10.6,<3.0.0
```

---

# Design principles

The toolkit is deliberately opinionated about a few things.

## 1. Define the product once

The product definition should not have to be recreated separately in:

* requirements
* spreadsheets
* documentation
* dbt YAML
* tests
* SQL implementation

The specification should be structured enough to generate and verify those downstream artifacts.

---

## 2. Make engineering intent explicit

Mappings should show mappings.

Joins should show joins.

Cardinality should be declared.

Quality should state both the expectation and operational consequence.

Transformation steps should be ordered and named.

The compiler should not have to guess what the author meant.

---

## 3. Validate before generating

The best place to catch:

* a missing field
* the wrong type
* an unsafe join
* an incomplete mapping
* a missing lookup
* an invalid transformation sequence

is before the generated project exists.

---

## 4. Prefer established standards

ODCS remains the contract standard rather than inventing a toolkit-specific data-contract format.

Existing dbt ecosystem capabilities are reused where appropriate rather than recreated unnecessarily.

---

## 5. Keep generated dbt readable

Generated code should look like code a data engineer could reasonably have written themselves.

The compiler must not become a prerequisite for understanding the implementation.

---

## 6. Preserve engineering control

The workbook is a collaboration surface.

It is not a replacement for data engineering expertise.

Engineers retain control over implementation, architecture, execution and deployment.

---

## 7. Keep specification and implementation aligned

If the workbook changes, the generated implementation can be regenerated and reviewed.

If generated files are changed manually, drift detection makes that visible.

This makes documentation and code much harder to accidentally evolve independently.

---

# The broader goal

Ultimately, `dbt_data_engineering_toolkit` is trying to make this:

```text
Business need
    ↓
BA mapping spreadsheet
    ↓
analyst notes
    ↓
ticket comments
    ↓
engineering interpretation
    ↓
custom SQL
    ↓
custom tests
    ↓
documentation written later
    ↓
eventual drift
```

look more like this:

```text
Business Requirements
        ↓
Shared Data Product Specification
        ↓
Source-to-Target Mapping
        ↓
Explicit Engineering Intent
        ↓
Early Validation
        ↓
Deterministic dbt Generation
        ↓
dbt build / test / prove
        ↓
Reviewable Data Product
```

Or, more simply:

> **Define a data product once, make the engineering intent explicit, validate it early, and turn it into consistent, readable and testable dbt rather than rebuilding the same plumbing for every data product.**

The outcome is a cleaner collaboration point between **BAs, analysts and data engineers**, while keeping the final implementation where it belongs:

**in readable, standard dbt.**
