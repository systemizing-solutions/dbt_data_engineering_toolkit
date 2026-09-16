# Deploy V5.0.1 to PyPI and dbt Package Hub

V5.0.1 publishes three related artifacts:

| Artifact | Distribution | Consumer API |
| --- | --- | --- |
| canonical dbt package | immutable GitHub release, then dbt Package Hub | `dbt_data_engineering_toolkit.*` |
| short-name companion project | pinned Git subdirectory or separate Hub repository | `de_toolkit.*` |
| Python compiler | checked wheel and source distribution on PyPI with OIDC provenance | `det` |

Package Hub consumes `dbt/`. PyPI consumes only `python/`. The release workflow publishes both
from the same `v5.0.1` tag after the local quality gates pass.

## 1. Create the permanent public repository

Use the final public URL before releasing, for example:

```text
https://github.com/systemizing-solutions/dbt_data_engineering_toolkit
```

The `dbt/` subfolder must retain `dbt_project.yml`, `packages.yml`, `macros/`, `.sqlfluff`, and
`.sqlfluffignore`. The dbt project name must remain `dbt_data_engineering_toolkit`; dbt derives the
macro namespace from that name.

Confirm the release range and dependencies:

```yaml
require-dbt-version: [">=1.10.6", "<3.0.0"]
```

```yaml
packages:
  - package: dbt-labs/dbt_utils
    version: 1.4.1
  - package: AxelThevenot/dbt_assertions
    version: 1.8.3
  - package: dbt-labs/codegen
    version: 0.14.1
  - package: dbt-labs/dbt_project_evaluator
    version: 1.3.5
```

Review dbt's [package-author guide](https://docs.getdbt.com/guides/building-packages) and
[Fusion package compatibility guide](https://docs.getdbt.com/guides/dbt-package-compat).

## 2. Configure warehouse integration credentials

Create repository Actions variables and secrets matching this table. Use dedicated CI users,
least-privilege credentials, disposable schemas, and warehouse cost controls.

| Platform | Actions variables | Actions secrets |
| --- | --- | --- |
| BigQuery | `BIGQUERY_PROJECT` | `BIGQUERY_KEYFILE_JSON` |
| Snowflake | `SNOWFLAKE_USER`, `SNOWFLAKE_ROLE`, `SNOWFLAKE_DATABASE`, `SNOWFLAKE_WAREHOUSE` | `SNOWFLAKE_ACCOUNT`, `DBT_ENV_SECRET_SNOWFLAKE_PASS` |
| Databricks | `DATABRICKS_HOST`, `DATABRICKS_HTTP_PATH` | `DBT_ENV_SECRET_DATABRICKS_TOKEN` |
| Redshift | `REDSHIFT_HOST`, `REDSHIFT_PORT`, `REDSHIFT_USER`, `REDSHIFT_DATABASE` | `DBT_ENV_SECRET_REDSHIFT_PASS` |
| Athena | `ATHENA_DATABASE`, `ATHENA_REGION_NAME`, `ATHENA_S3_DATA_DIR`, `ATHENA_S3_DATA_NAMING`, `ATHENA_S3_STAGING_DIR` | `DBT_ENV_SECRET_ATHENA_AWS_ACCESS_KEY_ID`, `DBT_ENV_SECRET_ATHENA_AWS_SECRET_ACCESS_KEY` |
| Spark | `SPARK_HOST`, `SPARK_PORT`, `SPARK_USER`, `SPARK_METHOD` | adapter/authentication-specific secrets, if required by the selected method |
| ClickHouse | `DET_CLICKHOUSE_HOST`, `DET_CLICKHOUSE_PORT`, `DET_CLICKHOUSE_USER` | `DBT_ENV_SECRET_DET_CLICKHOUSE_PASSWORD` |

`.github/workflows/cloud-integration.yml` creates a unique schema for each run. It uses dbt Labs'
official `dbt-package-testing` Core and Fusion workflows for supported adapters and a dedicated
ClickHouse Core job. It is available as a manual release-candidate preflight and is also called by
the tag release workflow, so publication cannot proceed without its credentialed builds. Protect
the credentials from untrusted code and require review on the `pypi` environment.

## 3. Configure PyPI trusted publishing

In GitHub, create an environment named `pypi` and add a required reviewer. In PyPI, create either
the project or a pending trusted publisher with:

| Setting | Value |
| --- | --- |
| PyPI project | `dbt-data-engineering-toolkit-compiler` |
| GitHub owner | `systemizing-solutions` |
| Repository | `dbt_data_engineering_toolkit` |
| Workflow | `release.yml` |
| Environment | `pypi` |

This setup is required before the first automated publish. Trusted publishing will fail until PyPI
has a matching trusted publisher entry for this repository/workflow/environment tuple.

If `https://pypi.org/project/dbt-data-engineering-toolkit-compiler/` is 404, that is expected
before first publish.

Before first publish, complete this checklist in PyPI:

1. Sign in to PyPI and open `Publishing` for `dbt-data-engineering-toolkit-compiler`.
2. If the project does not exist yet, create a pending trusted publisher (project can be created
  on first successful OIDC publish).
3. Add trusted publisher values that exactly match this repository:
  `systemizing-solutions` / `dbt_data_engineering_toolkit` / `release.yml` / `pypi`.
4. Save the publisher and then run the tagged release workflow.

For automated release, the first successful trusted-publisher run can create the project.

If you skip this, the `pypa/gh-action-pypi-publish` step is expected to fail with an identity or
publisher mismatch error even when the build artifacts are valid.

The workflow requests a short-lived OpenID Connect token through `id-token: write`; do not store a
long-lived PyPI API token. PyPI documents the setup in its
[trusted publisher guide](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).

## Automated PyPI publishing

This repository uses GitHub Actions to automatically publish to PyPI when a release tag is pushed.

### Setup (one-time configuration)

1. Register a Trusted Publisher in PyPI for this exact tuple:
  `systemizing-solutions` / `dbt_data_engineering_toolkit` / `release.yml` / `pypi`.
2. Ensure the GitHub environment `pypi` exists and has required reviewers.
3. Ensure `.github/workflows/release.yml` has `id-token: write` on the publish job.
4. Confirm the version in `python/pyproject.toml`, `dbt/dbt_project.yml`, and
  `aliases/de_toolkit/dbt_project.yml` matches the tag you will push.

### How it works

When you run bumpver and push the resulting tag:

```bash
./venv/bin/bumpver update --patch   # or --minor / --major
```

the release flow will:

1. Validate the release tag and version alignment.
2. Run quality and integration gates.
3. Build wheel and source distributions.
4. Publish to PyPI using OIDC trusted publishing (`pypa/gh-action-pypi-publish`).
5. Attach release artifacts to the GitHub release for Package Hub consumption.

### Security

This approach avoids long-lived PyPI API tokens:

1. No PyPI password/token is stored in repository secrets.
2. PyPI verifies repo, workflow, ref, and environment identity via OIDC.
3. Publishing can be constrained with GitHub environment approvals.

## 4. Run every release gate

From a clean checkout:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e "./python[test,release]"

python scripts/release.py verify-tag v5.0.1
python scripts/generate_alias_facade.py --check
python scripts/static_check.py
make quality
make python-coverage
make dbt-coverage
make codegen evaluator

det prove \
  python/src/dbt_data_engineering_toolkit_compiler/resources/data_product_multi_source_sample.xlsx \
  --project-dir examples/compiler/customer_accounts \
  --local-package-root .
```

Expected coverage is at least 80% for both codebases. V5.0.1 records 85.01% Python statement
coverage, 98.53% (134/136) DuckDB-scoped dbt macro implementation coverage, and 100% (104/104)
public-API direct execution coverage. Read the exact metric definitions in [testing](testing.md).

Next run the credentialed matrix as a release-candidate preflight and wait for every job to pass:

```bash
gh workflow run cloud-integration.yml --repo systemizing-solutions/dbt_data_engineering_toolkit
gh run list --workflow cloud-integration.yml --limit 1 \
  --repo systemizing-solutions/dbt_data_engineering_toolkit
gh run watch RUN_ID --exit-status --repo systemizing-solutions/dbt_data_engineering_toolkit
```

Do not tag the release if a supported warehouse was skipped. The release workflow runs this
matrix again for the tagged commit and separately builds DuckDB with Fusion before it can build
or publish the distributions. Fusion cannot test Athena or ClickHouse until Fusion supplies those
adapters; their Core builds remain required. See the [compatibility matrix](compatibility.md).

## 5. Build and inspect the PyPI artifacts locally

### Build

```bash
cd python
poetry install --with test,release
poetry build
python -m zipfile --list dist/dbt_data_engineering_toolkit_compiler-5.0.1-py3-none-any.whl
```

The wheel must contain `py.typed`, `resources/operators.yml`, and all three controlled workbook
resources. Test the exact wheel in a clean environment:

```bash
python -m venv /tmp/det-wheel-smoke
/tmp/det-wheel-smoke/bin/python -m pip install \
  python/dist/dbt_data_engineering_toolkit_compiler-5.0.1-py3-none-any.whl
/tmp/det-wheel-smoke/bin/det --help
/tmp/det-wheel-smoke/bin/det workbook build /tmp/release-smoke.xlsx --no-input
/tmp/det-wheel-smoke/bin/det validate /tmp/release-smoke.xlsx
```

### Publish (manual fallback)

If automated publishing is unavailable, publish manually with Poetry from the `python/` directory.

1. Build artifacts locally using the Build steps above.
2. Create a PyPI API token (account settings -> API tokens).
  If the project does not exist yet, use an account-scoped token for the first manual publish,
  then switch to project-scoped tokens afterward.
3. Configure Poetry to use the token:

```bash
cd python
poetry config pypi-token.pypi "pypi-..."
```

4. Optionally verify auth against TestPyPI first:

```bash
cd python
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry config pypi-token.testpypi "pypi-..."
poetry publish -r testpypi
```

5. Publish from `python/`:

```bash
cd python
poetry publish
```

6. Verify the new version appears in the project release list.

Manual `poetry publish` does not use GitHub OIDC trusted publishing. Trusted publishing is only
used by `pypa/gh-action-pypi-publish` in GitHub Actions.

Use this only as an operational fallback. The preferred path is automated OIDC publishing from
`release.yml`.

## 6. Push source and create the immutable release

For a new repository:

```bash
git init
git add .
git commit -m "Release dbt_data_engineering_toolkit v5.0.1"
git branch -M main
git remote add origin git@github.com:systemizing-solutions/dbt_data_engineering_toolkit.git
git push -u origin main

git tag -a v5.0.1 -m "dbt_data_engineering_toolkit v5.0.1"
git push origin v5.0.1
```

`.github/workflows/release.yml` repeats the release proof, requires the credentialed Core/Fusion
matrix and Fusion DuckDB build, builds and clean-installs both Python distribution formats, and
builds and extract-tests a Windows-safe source ZIP. It publishes the Python distributions to PyPI
with trusted publishing and attaches all release files to the GitHub release consumed by Package
Hub.

Verify both channels:

```bash
gh release view v5.0.1 --repo systemizing-solutions/dbt_data_engineering_toolkit
python -m pip index versions dbt-data-engineering-toolkit-compiler
```

Never move or overwrite a published tag. Correct a release with a new semantic version.

## 7. Smoke-test the Git dbt package

In a clean consumer project, create:
### Using environment variables
```yaml
packages:
  - git: "{{ env_var('DBT_DATA_ENGINEERING_TOOLKIT_GIT_URL') }}"
    revision: 5.0.1
    subdirectory: dbt
  - git: "{{ env_var('DBT_DATA_ENGINEERING_TOOLKIT_GIT_URL') }}"
    revision: 5.0.1
    subdirectory: aliases/de_toolkit
```

### Using the git repo directly 
```yaml
packages:
  - git: "https://github.com/systemizing-solutions/dbt_data_engineering_toolkit.git"
    revision: 5.0.1
    subdirectory: dbt
  - git: "https://github.com/systemizing-solutions/dbt_data_engineering_toolkit.git"
    revision: 5.0.1
    subdirectory: aliases/de_toolkit
```

Then run:

```bash
export DBT_DATA_ENGINEERING_TOOLKIT_GIT_URL=https://github.com/systemizing-solutions/dbt_data_engineering_toolkit.git

dbt clean
dbt deps
dbt parse
dbt build
```

Compile at least one call through each namespace before submitting the package to Hub.

## 8. Submit the canonical package to dbt Package Hub

Follow the current [Hubcap README](https://github.com/dbt-labs/hubcap): fork Hubcap, add
`systemizing-solutions/dbt_data_engineering_toolkit` to `hub.json` in sorted order, and open a pull request.
Hubcap discovers semantic GitHub releases and opens the registry-data change used by Package Hub.

```bash
gh repo fork dbt-labs/hubcap --clone
cd hubcap
git checkout -b add-dbt-data-engineering-toolkit
# Add systemizing-solutions/dbt_data_engineering_toolkit to hub.json in sorted order.
git add hub.json
git commit -m "Add systemizing-solutions/dbt_data_engineering_toolkit"
git push -u origin add-dbt-data-engineering-toolkit
gh pr create --repo dbt-labs/hubcap \
  --title "Add systemizing-solutions/dbt_data_engineering_toolkit" \
  --body "Adds dbt_data_engineering_toolkit v5.0.1 to dbt Package Hub."
```

After Hub ingestion, verify the registry dependency:

```yaml
packages:
  - package: systemizing-solutions/dbt_data_engineering_toolkit
    version: 5.0.1
```

```bash
dbt clean
dbt deps
dbt build
```

The nested `de_toolkit` project is not automatically a second Hub package. Continue using the
pinned Git subdirectory entry, or publish that project from its own top-level repository. dbt has
no package-level Python-style alias.
