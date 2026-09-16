"""dbt project, dependency, profile, and SQLFluff configuration emission."""

from __future__ import annotations

from pathlib import Path

from ...adapters import AdapterRegistry
from ...models import DataProductSpecification, FailureMode
from ...operational import Artifact
from .common import GENERATED_HEADER_YAML, yaml_text


class ProjectConfigurationEmitter:
    def __init__(self, adapters: AdapterRegistry | None = None) -> None:
        self.adapters = adapters or AdapterRegistry.default()

    def emit(self, spec: DataProductSpecification) -> list[Artifact]:
        provider = self.adapters.get(spec.build.adapter)
        if provider is None:
            raise ValueError(f"Unknown adapter {spec.build.adapter!r}")
        project_name = spec.metadata.product_id
        layer_defaults = {
            "staging": "view",
            "intermediate": "ephemeral",
            "marts": "table",
        }
        used_layers = {
            "marts" if model.layer.value == "mart" else model.layer.value
            for model in spec.models
            if model.enabled
        }
        model_configuration = {
            layer: {"+materialized": layer_defaults[layer]} for layer in sorted(used_layers)
        }
        if any(item.failure == FailureMode.REJECT for item in spec.rules):
            model_configuration["quarantine"] = {"+materialized": "view"}
        dbt_project = {
            "name": project_name,
            "version": spec.metadata.version,
            "config-version": 2,
            "profile": spec.build.profile,
            "require-dbt-version": [">=1.10.6", "<3.0.0"],
            "dispatch": [
                {
                    "macro_namespace": "dbt",
                    "search_order": ["dbt_project_evaluator", "dbt"],
                }
            ],
            "model-paths": ["models"],
            "seed-paths": ["seeds"],
            "test-paths": ["tests"],
            "clean-targets": ["target", "dbt_packages", "logs"],
            "vars": {"exclude_packages": ["all"]},
            "models": {project_name: model_configuration},
        }
        default_git_url = (
            "https://github.com/systemizing-solutions/dbt_data_engineering_toolkit.git"
        )
        git_expression = (
            "{{ env_var('" + spec.build.toolkit_git_env + "', '" + default_git_url + "') }}"
        )
        packages = {
            "packages": [
                {
                    "git": git_expression,
                    "revision": spec.build.toolkit_revision,
                },
                {
                    "git": git_expression,
                    "revision": spec.build.toolkit_revision,
                    "subdirectory": "aliases/de_toolkit",
                },
            ]
        }
        artifacts = [
            Artifact(
                Path("dbt_project.yml"),
                GENERATED_HEADER_YAML + yaml_text(dbt_project),
            ),
            Artifact(
                Path("packages.yml"),
                GENERATED_HEADER_YAML + yaml_text(packages),
            ),
        ]
        output = {
            key: spec.build.target_schema if value == "__TARGET_SCHEMA__" else value
            for key, value in provider.profile_output.items()
        }
        profiles = {
            spec.build.profile: {
                "target": "dev",
                "outputs": {"dev": output},
            }
        }
        artifacts.append(
            Artifact(
                Path("profiles.yml"),
                GENERATED_HEADER_YAML + yaml_text(profiles),
            )
        )
        artifacts.extend(self._sqlfluff(spec))
        return artifacts

    def _sqlfluff(self, spec: DataProductSpecification) -> list[Artifact]:
        provider = self.adapters.get(spec.build.adapter)
        if provider is None:
            raise ValueError(f"Unknown adapter {spec.build.adapter!r}")
        configuration = f"""[sqlfluff]
templater = dbt
dialect = {provider.sqlfluff_dialect}
max_line_length = 100
exclude_rules = layout.long_lines

[sqlfluff:templater:dbt]
project_dir = .
profiles_dir = .
profile = {spec.build.profile}
"""
        return [
            Artifact(Path(".sqlfluff"), configuration),
            Artifact(
                Path(".sqlfluffignore"),
                "target/\ndbt_packages/\nlogs/\ntests/datacontract_cli/\n",
            ),
        ]
