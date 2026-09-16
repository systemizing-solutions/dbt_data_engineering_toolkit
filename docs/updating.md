# Updating a V6.0.0 product safely

There are two authoritative edit paths: workbook changes and toolkit-source changes. Generated
files are outputs in both cases.

## Workbook changed

Use this sequence:

```bash
det workbook refresh contracts/orders.xlsx
det validate contracts/orders.xlsx
det status contracts/orders.xlsx --project-dir build/orders --prune
det generate contracts/orders.xlsx --project-dir build/orders --dry-run --prune
det generate contracts/orders.xlsx --project-dir build/orders --prune
det check contracts/orders.xlsx --project-dir build/orders
det prove contracts/orders.xlsx --project-dir build/orders
```

Refresh is needed after manually adding/renaming models, fields, source relations, inputs, or
lookups so contextual dropdowns are rebuilt. It accepts the v6.0.0 workbook schema only.

## External schema changed

Merge first:

```bash
det workbook sync contracts/orders.xlsx --from-contract updated_orders.xlsx
```

ODCS YAML, SQL DDL, and dbt manifests are also supported. The default adds/updates rows and keeps
removed fields visible. Use `--replace-schema` only after reviewing deletions. Existing mappings,
parameters, operational rules, and lookups are preserved either way.

If a removed field is still mapped, validation reports the missing relation/field and the mapping
location. It does not erase the mapping.

## Generated code changed

`.det-manifest.json` contains the hash of every generated file after Data Contract sync. The next
generation refuses to overwrite a hand edit.

Choose one response:

- Move contract, mapping, lookup, or validation intent into the workbook.
- Put project-specific custom SQL in a separate downstream model not owned by DET.
- Restore an accidental edit.
- Change the owning emitter when behavior should change for every generated project.
- Use `--force` only after a deliberate review of the replacement.

Do not add custom files to `.det-manifest.json`.

## Toolkit source changed

1. Change the canonical macro or owning compiler component.
2. Add a focused unit or acceptance test.
3. Regenerate `de_toolkit` wrappers when public signatures change.
4. Regenerate workbook resources and example projects.
5. Run all Python, static, dbt, codegen, evaluator, and proof gates.
6. Update the version and changelog.
7. Publish an immutable Git tag and GitHub release.
8. Update `Toolkit Revision` in consumer workbooks.
9. Regenerate consumer projects and review their complete diffs.

Version updates are managed by bumpver from the repository-root `bumpver.toml`.

```bash
python -m pip install -e "./python[release]"
bumpver update --patch
```

Use `--minor` or `--major` when needed. The configured bump updates the Python
distribution version, compiler version constants, and both dbt package versions,
then creates and pushes a matching Git tag (`vX.Y.Z`).
Never point a production workbook at an unpinned branch.

## Which manifest is which?

| File | Producer | Purpose |
| --- | --- | --- |
| `target/manifest.json` | dbt parse/build | dbt graph and metadata; valid import input |
| `.det-manifest.json` | DET generation | hashes, ownership, workbook provenance, and drift protection |
