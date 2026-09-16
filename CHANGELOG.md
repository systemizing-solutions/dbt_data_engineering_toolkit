# Changelog

## 5.0.1 - 2026-09-07

- Refreshed the release fixtures and example package metadata for the 5.0.1 release.

## 5.0.0 - 2026-09-07

- Refreshed the release fixtures and example package metadata for the 5.0.0 release.

## 4.1.1 - 2026-09-07

- Refreshed the release fixtures and example package metadata for the 4.1.1 release.

## 4.1.0 - 2026-09-07

- Refreshed the release fixtures and example package metadata for the 4.1.0 release.

## 4.0.3 - 2026-09-07

- Refreshed the release fixtures and example package metadata for the 4.0.3 release.

## 4.0.2 - 2026-09-07

- Refreshed the release fixtures and example package metadata for the 4.0.2 release.

## 4.0.1 - 2026-09-07

- Refreshed the release fixtures and example package metadata for the 4.0.1 release.

## 4.0.0 - 2026-09-07

- Refreshed the release fixtures and example package metadata for the 4.0.0 release.

## 3.2.0 - 2026-09-07

- Refreshed the release fixtures and example package metadata for the 3.2.0 release.

## 3.1.0 - 2026-09-07

- Refreshed the release fixtures and example package metadata for the 3.1.0 release.

## 3.0.7 - 2026-09-07

- Refreshed the release fixtures and example package metadata for the 3.0.7 release.

## 3.0.6 - 2026-09-07

- Refreshed the release fixtures and example package metadata for the 3.0.6 release.

## 3.0.5 - 2026-09-07

- Refreshed the release fixtures and example package metadata for the 3.0.5 release.

## 3.0.2 - 2026-09-07

- Refreshed the release fixtures and example package metadata for the 3.0.2 release.
- added github pages for docs
- got the python and dbt code release ready
- update release fixtures

## 2.3.0 - 2026-09-06

- Added an enforced 80% Python coverage gate; the release suite covers 85.01% of compiler
  statements across brokers, services, CLI exposers, and acceptance flows.
- Added a source-derived dbt coverage gate that measures 98.53% (134/136) of the DuckDB-scoped
  generic, private, and adapter implementation graph, directly executes all 104 documented public
  facades, and fails below 80%.
- Added Core adapter providers, profile templates, SQLFluff dialects, safe casts, regular
  expressions, temporal/number formatting, statistics, and string dispatches for BigQuery,
  Snowflake, DuckDB, Databricks, Redshift, Athena, ClickHouse, and Spark.
- Added isolated no-credential parse/dispatch CI for every remote adapter, full DuckDB builds,
  and credentialed live build workflows for all supported Core warehouses.
- Implemented dbt Fusion package metadata, current-schema/deprecation checks, a full Fusion
  DuckDB build, evaluator-safe Fusion parsing, and dbt Labs package-testing workflows for
  supported remote Fusion adapters.
- Added per-adapter PyPI extras while intentionally omitting an unsafe all-adapters extra because
  Spark PyHive and Databricks currently have incompatible upstream Thrift constraints.
- Added secure PyPI trusted publishing for wheel/source distributions and attached those artifacts
  to the immutable GitHub release used by dbt Package Hub.
- Added explicit compatibility, testing, credential setup, PyPI, GitHub release, and Package Hub
  deployment documentation.
- Added deterministic compaction for Data Contract-generated test paths and a 180-character
  source-archive path budget so the release extracts through ordinary Windows Explorer.
- Removed development-origin language and fixture names from the public documentation and
  integration suite.

## 2.2.0 - 2026-09-06

- Prepared the first public release under the canonical
  `dbt_data_engineering_toolkit` repository and dbt project name.
- Removed development-only workbook migrations, old sheet aliases, duplicate
  quality inputs, and Python compatibility facades.
- Made the official `Quality` sheet the single contract-quality input, alongside
  `Operational Validation` and `Operational Parameters` for runtime behavior.
- Added direct official ODCS Excel import by delegating workbook interpretation
  to Data Contract CLI before using the canonical ODCS YAML importer.
- Made Data Contract CLI with Excel support, dbt Core, dbt-duckdb, DuckDB,
  SQLFluff, and the dbt templater default compiler dependencies.
- Normalized the bundled workbooks, generated projects, documentation, CI, and
  release automation to v2.2.0 and the canonical Python distribution name.
- Added live official-Excel round-trip acceptance coverage, source-removal
  diagnostics, and static PostgreSQL/Snowflake project checks.
- Documented the complete workbook-to-dbt update flow and the GitHub/dbt Package
  Hub publication process.

## 2.1.1 - 2026-09-06

- Made the official visible ODCS `Quality` sheet the authoritative BA
  contract-quality surface and compiled library, SQL, custom, and text rows
  into the canonical `QualityRule` representation.
- Preserved unsupported or advanced per-rule ODCS fields through an explicit
  JSON passthrough column instead of silently discarding deliberate edits.
- Retained the hidden `Contract Quality` sheet as a V2.0/V2.1 compatibility
  input, coalescing equivalent official and legacy rows without duplication.
- Added end-to-end acceptance coverage proving official Quality rows survive
  Excel → canonical IR → ODCS, including custom implementations and passthrough
  values.
- Added regression coverage proving source-schema replacement preserves an
  existing mapping when its source field disappears and emits an actionable
  validation diagnostic.
- Added static full-project emission checks for PostgreSQL and Snowflake and
  corrected generated operational array types to come from the selected
  adapter provider.
- Migrated bundled workbooks to the visible official Quality authoring surface,
  hid the compatibility sheet, and clarified authoring, updating, migration,
  and Package Hub deployment guidance.

## 2.1.0 - 2026-09-06

- Made Data Contract synchronization a mandatory generation phase before final
  hashes are calculated, and publish only a validated post-sync project through
  a rollback-safe sibling staging directory.
- Added manifest provenance for compiler, workbook schema, operator registry,
  ODCS version, adapter, contract authority, workbook content, compiler-owned
  files, and Data Contract-owned files.
- Added context-aware workbook dropdowns for each model's target fields, model
  inputs, relation fields, join keys, operators, parameters, controlled values,
  and lookup names; `det workbook refresh` rebuilds them deterministically.
- Renamed the BA-facing quality sheets to `Contract Quality`, `Operational
  Validation`, and `Operational Parameters`, while accepting V2.0 names and
  providing `det workbook migrate` for a safe-copy upgrade.
- Simplified schema sheets around the common BA columns, grouped advanced ODCS
  fields, protected/very-hid all system sheets, and preserved unmodelled ODCS
  fields through import, workbook parsing, and re-emission.
- Added DuckDB, PostgreSQL, and Snowflake adapter providers covering dependency,
  dialect, types, materializations, contract capability, and environment-only
  profile templates; incomplete incremental materialization remains blocked.
- Strengthened contextual diagnostics, relationship/cardinality validation,
  contract/operational rule ownership, full mapping coverage, lookup checks, and
  end-to-end operation type inference.
- Added a two-source/two-model Customer Accounts fixture with a real join,
  cardinality test, multi-step cleaning, lookup mapping, enforced contracts,
  warning and quarantine behavior, plus explicit failure acceptance scenarios.
- Corrected generated join formatting, no-op self aliases, transformation column
  ordering, adapter-dispatched title casing, and numeric precision/scale in the
  executable example; SQLFluff, 14 product build nodes, and all 48 evaluator
  models pass on DuckDB.
- Added V2.0 workbook compatibility metadata and refresh/migration commands,
  excluded reproducible dbt caches from atomic project publication, and
  documented the full authoring, update, proof, and Package Hub release paths.

## 2.0.0 - 2026-09-06

- Reorganized the compiler around replaceable file, workbook, command, dbt,
  SQLFluff, and Data Contract brokers; technology dependencies no longer leak
  into application, validation, import, or emission services.
- Split workbook interpretation, specification validation, and artifact
  emission into independently owned components coordinated by small services.
- Moved every CLI workflow into `ToolkitApplication`; the CLI now maps
  arguments, prompts, results, and exception families only.
- Unified ODCS, DDL, and dbt-manifest parsing behind one typed
  `ImportedDataStructure` that can populate either source or target workbook
  rows, and isolated the controlled DDL parser behind that replaceable boundary.
- Added typed operational models, a localized exception taxonomy, and stable
  support diagnostic codes across workbook and specification validation.
- Generated the complete `de_toolkit` facade from canonical public macro/test
  signatures and added a deterministic staleness check.
- Centralized compiler, workbook-schema, default product, and toolkit revision
  versions; added Ruff, format, Pyright, component tests, and decomposed static
  checks to the release gate.
- Added GitHub tag/release automation and exact instructions for Git release,
  dbt Package Hub/Hubcap submission, canonical Hub consumption, and the
  separate short-namespace distribution path.
- Formatted long generated macro calls and mapping dictionaries vertically
  while retaining inline SQL expressions, and excluded only Data Contract
  CLI-owned tests from the generated SQLFluff layout gate.
- Made sibling dbt/Data Contract/SQLFluff executables discoverable when `det`
  is invoked without activating its virtual environment, and constrained the
  default DuckDB runtime to the tested 1.4 line.
- Replaced the monolithic reference README with a guided end-to-end V2 flow
  plus focused architecture, CLI, imports, updating, deployment, SQL, and
  migration documents.

## 1.1.0 - 2026-09-05

- Made Data Contract CLI, dbt Core, DuckDB, SQLFluff, and the dbt SQLFluff
  templater default compiler dependencies.
- Replaced the always-Customer workbook copy with a guided scaffold. Blank,
  filename-specific output is the default; Customer 360 data requires the
  explicit `--sample-customer-data` opt-in.
- Added `det workbook import` for ODCS YAML, SQL DDL, and dbt manifests, plus
  optional, explicit identity mappings. Imported models stay disabled until
  mappings are supplied; identity imports are enabled immediately.
- Added `det workbook sync` to merge later structural changes while preserving
  mappings, parameters, lookups, and rules; destructive field removal requires
  `--replace-schema`.
- Documented exactly how `dbt deps` and `dbt parse` create an upstream
  `target/manifest.json`, where the artifact lives, and what each import flag
  updates.
- Generated `.sqlfluff`, `.sqlfluffignore`, and `Makefile` files and made
  SQLFluff's dbt-templated lint part of `det check` and `det prove`.
- Replaced emitted local dbt package paths with a published Git repository
  environment variable and pinned toolkit revision, including the
  `aliases/de_toolkit` subdirectory package.
- Added `det status`, generated-project update instructions, and separate,
  explicit workflows for workbook edits, upstream schema changes, custom SQL,
  compiler changes, and accidental generated-file drift.

## 1.0.0 - 2026-09-05

- Rebuilt the controlled workbook as an official ODCS Excel-template superset,
  retaining the standard Fundamentals, Schema, Relationships, Quality, Support,
  Team, Roles, SLA, Servers, Pricing, and Custom Properties sheets.
- Added first-class source schemas and `det source import` for dbt manifests,
  upstream ODCS contracts, and SQL DDL.
- Replaced the wide mapping form with compact `DET Mapping` rows plus normalized
  transformation/rule parameter sheets; dropdowns are generated from the same
  operator registry used by compiler validation.
- Added protected business-input ranges and very-hidden compiler metadata/list
  sheets to prevent accidental workbook damage.
- Enforced declared model inputs, source fields and keys, complete published
  field implementation, and end-to-end inferred transformation types against
  the ODCS target schema.
- Made the Data Contract the schema-test authority, added optional native dbt
  contract enforcement, and derived uniqueness tests from join cardinality.
- Blocked unsafe many-to-many joins and incomplete incremental semantics, and
  removed aggregate Unique rules from row-routing SQL.
- Added `det prove`, which performs real Data Contract synchronization and a
  disposable DuckDB build/test/evaluator acceptance run without modifying the
  generated project.
- Expanded compiler coverage to 20 unit tests and added V1 release checks for
  workbook controls, deterministic generation, source imports and contracts.

## 0.9.0 - 2026-09-05

- Added the optional `det` controlled data-product compiler and a professionally
  formatted, dropdown-driven Excel workbook for business analysts.
- Added a strict Pydantic IR plus cross-sheet validation for identifiers,
  references, operator type flow, parameters, lookups, grains, cycles, joins,
  quality vocabulary, and failure behavior.
- Added a single BA-safe operator registry that drives workbook dropdowns,
  validation, and generated inline `de_toolkit` macro calls.
- Added deterministic ODCS 3.1 and DET YAML generation with source-to-target
  lineage, transformation logic, schema constraints, portable quality rules,
  SLA, ownership, and server metadata.
- Added readable dbt project generation: source/ref CTEs, ordered inline macro
  CTEs, row assertions, valid/rejected views, native tests, singular fail-build
  tests, package configuration, profile, and documentation.
- Added `det product init`, `validate`, `compile`, `generate`, `generate
  --dry-run`, and `check`, including manifest-based drift protection, atomic
  writes, and safe pruning.
- Added optional Data Contract CLI/Python integration for ODCS lint and dbt
  synchronization checks.
- Added a generated Customer 360 example, workbook/compiler unit tests, and an
  executable DuckDB acceptance flow proving seed, model, tests, and quarantine.

## 0.8.0 - 2026-09-05

- Added an optional companion dbt package named `de_toolkit`, providing a real
  globally qualified short namespace for the complete public macro and generic
  test API.
- Kept `data_engineering_toolkit` as the canonical implementation and
  dependency boundary; the short package contains thin wrappers only.
- Added executable integration coverage proving equivalent cleaning, mapping,
  surrogate-key, assertion, quarantine-filter, and generic-test behavior across
  both namespaces.
- Added dependency-boundary checks that reject direct `dbt_utils` and
  `dbt_assertions` calls from consumer-style model and test SQL.
- Documented the two-entry Git/subdirectory installation and clarified that a
  Jinja `{% set %}` alias is local to one model, not global dbt configuration.

## 0.7.0 - 2026-09-05

- Added `mapping(expression=..., mapping=..., default=..., data_type=...,
  format=...)` as the single primary inline mapping API.
- Removed `select_cleaned`, `clean_expression`, and `apply_operations`; the
  configuration DSL no longer exists in the package.
- Converted the runnable example and all integration models to direct inline
  SQL-expression macros and ordinary CTEs.
- Removed configuration-dictionary examples from the README and parity guide.
- Added a V0.7 migration guide with direct expression-to-expression replacements.

## 0.6.0 - 2026-09-05

- Made direct, inline SQL-expression macros the primary documented API.
- Rewrote the runnable walkthrough so cleaning, mapping, formatting, business
  rules, and validation are visible beside each selected column.
- Added typed inline mapping helpers: `map_string`, `map_integer`,
  `map_numeric`, `map_date`, `map_timestamp`, and `map_boolean`.
- Added `format_string`, `format_date`, and `format_timestamp` helpers, and
  added an optional `null_value` directly to `format_number`.
- Added `clean_code` for the common trim, prefix/suffix removal, case, and
  correction flow without an operation-list configuration.
- Kept `select_cleaned`, `clean_expression`, and `apply_operations` for
  backward compatibility, but moved them to an optional bulk-configuration
  section instead of presenting them as the normal usage style.

## 0.5.0 - 2026-09-04

- Added a verified, standalone `examples/end_to_end` project and a step-by-step
  README that goes from installation and raw seed data through mapping,
  validation, quarantine, tests, code generation, docs, evaluator checks, and
  CI, including commands and expected results.
- Added `key_value_map` / `map_value` for native Jinja dictionaries or JSON
  object strings, with case-sensitive or case-insensitive key matching.
- Added an optional default for unmapped keys, explicit null defaults, and a
  `preserve_unmapped` mode when passthrough is required.
- Added safe post-mapping conversion to string, integer, numeric, date,
  timestamp, or boolean values, including numeric precision/scale controls.
- Added type-aware display formatting: string case and whitespace rules,
  canonical strftime-style date/timestamp patterns, and numeric decimal,
  grouping, prefix, suffix, and invalid/null display controls.
- Added `mapping`, `map_values`, and `convert_type` support to the composable
  configuration pipeline, plus executable DuckDB integration fixtures for
  JSON parsing, defaults, failed casts, typed outputs, and formatted outputs.

## 0.4.0 - 2026-09-04

- Added composable `operations` pipelines to `clean_expression` and
  `select_cleaned` for fluent transformation chaining.
- Added missing-value, full-row deduplication, correction-map, category encoding,
  string manipulation, row slicing, scaling, binning, outlier, anomaly, and
  deterministic class-undersampling macros.
- Added variance and correlation diagnostics as generic tests, keeping feature
  removal explicit and reviewable.
- Added adapter-dispatched percentile, regex extraction, and Unicode
  normalization capabilities with explicit compile-time failures where a safe
  portable implementation is unavailable.
- Added executable DuckDB coverage and a method-by-method support matrix for the
  expanded cleaning API.

## 0.3.0 - 2026-09-04

- Added `dbt-labs/codegen` 0.14.1 for source, base-model, model-YAML, import-CTE,
  and unit-test-template generation.
- Added `dbt-labs/dbt_project_evaluator` 1.3.5 for modeling, testing,
  documentation, structure, performance, and governance checks.
- Raised the minimum dbt Core version to 1.10.6 to satisfy the evaluator's
  compatibility contract.
- Added the required evaluator dispatch configuration to the DuckDB integration
  project and a ready-to-copy consumer configuration example.
- Separated normal toolkit builds from opt-in evaluator execution.
- Added CI smoke tests for code generation and evaluator model execution.

## 0.2.0 - 2026-09-04

- Renamed the package and public namespace to `data_engineering_toolkit`.
- Added config-driven `select_cleaned` and `clean_expression` macros.
- Added formatting, safe casting, booleans, phone/email, country/currency codes.
- Added validation predicates and generic data tests.
- Added cross-column business rules with compile-time argument validation.
- Added stable facades for `dbt_assertions` and `dbt_utils`.
- Added accepted/quarantined row filters, audit columns, and PII masking.
- Added a DuckDB integration project, static checks, and CI.
