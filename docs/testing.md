# V6.0.0 testing and coverage

Both codebases have a mandatory 80% release gate. The current release results are:

| Codebase | Metric | Result | Enforced minimum |
| --- | --- | ---: | ---: |
| Python compiler | statement coverage reported by coverage.py | 85.01% | 80% |
| dbt package | DuckDB-scoped macro implementation execution coverage | 98.53% (134/136) | 80% |
| dbt public API | directly exercised documented facades | 100% (104/104) | 80% |

## Python coverage

Run:

```bash
make python-coverage
```

Pytest executes broker, service, exposer, and acceptance tests. `pytest-cov` measures the installed
compiler source and fails below 80%. CI also writes `coverage.xml`. Exclusions are limited to type
checking guards, module entry-point guards, and deliberately abstract `NotImplementedError` paths.

## dbt coverage

Run:

```bash
make dbt-coverage
```

dbt does not emit Python-style line coverage for Jinja macros. The repository therefore uses two
auditable metrics implemented by `scripts/dbt_coverage.py`:

1. Discover every macro definition directly from `dbt/macros/`.
2. Select generic/private macros plus the adapter branch reachable for the manifest target;
   implementations for unrelated adapters are not placed in that target's denominator.
3. Read successful nodes in `run_results.json` and traverse their manifest macro-dependency graph.
4. Measure the covered adapter-scoped implementation graph and fail below 80%.
5. Independently discover every non-private, non-dispatch public facade, require
   `dbt/macros/schema.yml` to document exactly that surface, and count only direct dependencies from
   successful executed nodes. That second metric also fails below 80%.
6. Write both results to `integration_tests/target/dbt_coverage.json`.

This prevents either documentation-only facades or unreachable helper definitions from inflating
coverage. The DuckDB suite reaches 134 of 136 generic/private/DuckDB implementation macros and
directly executes all 104 public facades, plus relation helpers, generated namespace behavior,
mappings, validations, quarantine routing, generic tests, codegen, and project evaluator
integration. Credentialed Core and Fusion builds run the same adapter-scoped 80% gate for their
own target.

## Adapter and Fusion tests

The ordinary CI workflow runs:

- static YAML/Jinja/release checks;
- the Python coverage, Ruff, format, and Pyright gates;
- a dbt Core version matrix and full DuckDB builds;
- isolated Core parse/dispatch jobs for BigQuery, Snowflake, Databricks, Redshift, Spark, Athena,
  and ClickHouse;
- a full credential-free Fusion DuckDB build;
- Fusion parses/builds with the flags required by `dbt_project_evaluator` (`static-analysis=off`,
  unmanaged state, and its incompatible fixtures deactivated);
- a `dbt-autofix deprecations` dry run.

The credentialed workflow uses dbt Labs' official
[`dbt-package-testing`](https://github.com/dbt-labs/dbt-package-testing) reusable workflows for
remote Core and Fusion builds, plus a dedicated ClickHouse Core job. Those live checks require
repository secrets and are intentionally separate from untrusted pull-request execution.

## Complete local gate

```bash
python -m pip install -e "./python[test]"
make check
```

Release publication repeats the fast gates and is blocked on the credentialed Core/Fusion matrix
for the tagged commit, as described in [deployment](deployment.md).
