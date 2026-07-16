#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

import yaml

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_ERROR = 2

USES_PATTERN = re.compile(r"^\s*uses:\s+([^\s]+)", re.MULTILINE)
SHA_PATTERN = re.compile(r"@[0-9a-f]{40}(\s+#.*)?$")


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate TG3 workflow, config, and documentation contracts."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root to validate.",
    )
    return parser


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return EXIT_FAILURE


def validate_required_files(repo: Path) -> int:
    required_files = [
        repo / ".github/workflows/ci.yml",
        repo / ".github/workflows/detect-and-eval.yml",
        repo / ".github/workflows/sweep-orphans.yml",
        repo / "config/azure.env.example",
        repo / "config/models.yaml",
        repo / "config/evaluation.yaml",
        repo / "config/recommender.yaml",
        repo / "docs/setup-guide.md",
        repo / "docs/oidc-setup.md",
        repo / "docs/troubleshooting.md",
        repo / "docs/tg2-operator-evidence.md",
        repo / "docs/tg3-handoff-contract.md",
        repo / "scripts/validate_tg3_contracts.py",
    ]
    missing = [str(path.relative_to(repo)) for path in required_files if not path.exists()]
    if missing:
        print("Missing required TG3 files:", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        return EXIT_FAILURE
    return EXIT_SUCCESS


def validate_env_contract(repo: Path) -> int:
    env_text = (repo / "config/azure.env.example").read_text(encoding="utf-8")
    required_env = [
        "AZURE_CLIENT_ID=",
        "AZURE_TENANT_ID=",
        "AZURE_SUBSCRIPTION_ID=",
        "RESOURCE_GROUP=",
        "FOUNDRY_ACCOUNT_NAME=",
        "FOUNDRY_PROJECT_NAME=",
        "ACA_ENVIRONMENT_NAME=",
        "ACA_JOB_NAME=",
        "STORAGE_ACCOUNT_NAME=",
        "KEY_VAULT_NAME=",
        "DEPLOYMENT_TYPE=",
        "ALLOWED_REGIONS=",
        "RETIREMENT_HORIZON_DAYS=",
        "CANDIDATES_PER_RETIRING_MODEL=",
        "ENABLE_AUTO_PR=",
        "AUTOMATION_OWNERSHIP_TAG=",
        "AUTOMATION_SCOPE_TAG=",
        "MANAGED_BY_TAG=",
        "AUTOMATION_CLEANUP_TAG=",
    ]
    missing = [entry for entry in required_env if entry not in env_text]
    if missing:
        print("Missing required environment entries in config/azure.env.example:", file=sys.stderr)
        for entry in missing:
            print(f"  - {entry}", file=sys.stderr)
        return EXIT_FAILURE
    return EXIT_SUCCESS


def validate_workflow_pinning_and_structure(repo: Path) -> int:
    marker_checks = {
        "permissions:": "top-level permissions block",
        "concurrency:": "concurrency control",
    }
    for workflow_path in sorted((repo / ".github/workflows").glob("*.yml")):
        text = workflow_path.read_text(encoding="utf-8")
        rel_path = workflow_path.relative_to(repo)
        for marker, description in marker_checks.items():
            if marker not in text:
                return fail(f"{rel_path} is missing {description}.")
        if "actions/checkout@" in text and "persist-credentials: false" not in text:
            return fail(f"{rel_path} must disable persisted checkout credentials.")
        for match in USES_PATTERN.finditer(text):
            action_ref = match.group(1)
            if action_ref.startswith("./"):
                continue
            if not SHA_PATTERN.search(action_ref):
                return fail(f"{rel_path} contains an unpinned action reference: {action_ref}")
    return EXIT_SUCCESS


def validate_detect_and_eval_contract(repo: Path) -> int:
    text = (repo / ".github/workflows/detect-and-eval.yml").read_text(encoding="utf-8")
    required_markers = {
        "python scripts/validate_tg3_contracts.py": "shared TG3 contract validation",
        "run-context.json": "run context artifact generation",
        "cleanup-recovery.json": "cleanup recovery artifact generation",
        "id-token: write": "OIDC-enabled Azure job permissions",
        "ENABLE_AUTO_PR": "auto-remediation gate enforcement",
        "tg2-contract-pending": "TG2 placeholder handling",
        "teardown-plan.json": "rollback and teardown planning artifact",
    }
    for marker, description in required_markers.items():
        if marker not in text:
            return fail(f"detect-and-eval.yml is missing {description}.")
    return EXIT_SUCCESS


def validate_sweeper_contract(repo: Path) -> int:
    text = (repo / ".github/workflows/sweep-orphans.yml").read_text(encoding="utf-8")
    required_markers = {
        "managedBy": "TG2 managed-by safety tag check",
        "cleanup": "TG2 cleanup tag compatibility",
        "created_at_utc": "age-based orphan filtering",
        "stale-resource-ids.txt": "deterministic stale resource manifest",
        "python scripts/validate_tg3_contracts.py": "shared TG3 contract validation",
    }
    for marker, description in required_markers.items():
        if marker not in text:
            return fail(f"sweep-orphans.yml is missing {description}.")
    return EXIT_SUCCESS


def validate_config(repo: Path) -> int:
    parsed_yaml: dict[str, object] = {}
    for yaml_path in sorted((repo / "config").glob("*.yaml")):
        with yaml_path.open("r", encoding="utf-8") as handle:
            parsed_yaml[yaml_path.name] = yaml.safe_load(handle)

    evaluation = parsed_yaml["evaluation.yaml"]
    if not isinstance(evaluation, dict):
        return fail("config/evaluation.yaml must parse to a mapping.")
    evaluation_required = [
        "retirement_horizon_days",
        "candidates_per_retiring_model",
        "deployment_type_preferences",
        "allowed_regions",
        "quality_gates",
        "timeouts",
    ]
    missing_evaluation = [key for key in evaluation_required if key not in evaluation]
    if missing_evaluation:
        print("config/evaluation.yaml is missing required keys:", file=sys.stderr)
        for key in missing_evaluation:
            print(f"  - {key}", file=sys.stderr)
        return EXIT_FAILURE
    if not evaluation["deployment_type_preferences"]:
        return fail("config/evaluation.yaml must define at least one deployment_type_preferences entry.")
    if not evaluation["allowed_regions"]:
        return fail("config/evaluation.yaml must define at least one allowed_regions entry.")

    recommender = parsed_yaml["recommender.yaml"]
    if not isinstance(recommender, dict):
        return fail("config/recommender.yaml must parse to a mapping.")
    if "weights" not in recommender or "hard_filters" not in recommender:
        return fail("config/recommender.yaml must define weights and hard_filters sections.")
    weight_total = sum(float(value) for value in recommender["weights"].values())
    if not math.isclose(weight_total, 1.0, rel_tol=0.0, abs_tol=1e-9):
        return fail(f"config/recommender.yaml weights must sum to 1.0, found {weight_total}.")

    models = parsed_yaml["models.yaml"]
    if not isinstance(models, dict) or not models.get("watch_list"):
        return fail("config/models.yaml must define a non-empty watch_list.")
    return EXIT_SUCCESS


def validate_docs(repo: Path) -> int:
    expectations = {
        "setup-guide.md": [
            "ENABLE_SCHEDULED_EVALS",
            "ENABLE_ORPHAN_SWEEP",
            "ENABLE_AUTO_PR",
            "validate_tg3_contracts.py",
        ],
        "oidc-setup.md": [
            "No client secret is required or recommended.",
            "id-token: write",
            "repo:<org>/<repo>:ref:refs/heads/main",
        ],
        "troubleshooting.md": [
            "tg2-contract-pending",
            "Sweep Orphans",
            "ENABLE_AUTO_PR",
            "validate_tg3_contracts.py",
        ],
        "tg3-handoff-contract.md": [
            "private-only",
            "managedBy=model-upgrade-automation",
            "cleanup=ephemeral",
        ],
    }
    for doc_name, markers in expectations.items():
        doc_text = (repo / "docs" / doc_name).read_text(encoding="utf-8")
        for marker in markers:
            if marker not in doc_text:
                return fail(f"docs/{doc_name} is missing required guidance marker: {marker}")
    return EXIT_SUCCESS


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()
    repo = args.repo_root.resolve()
    if not repo.exists():
        return fail(f"Repository root does not exist: {repo}")

    validators = [
        validate_required_files,
        validate_env_contract,
        validate_workflow_pinning_and_structure,
        validate_detect_and_eval_contract,
        validate_sweeper_contract,
        validate_config,
        validate_docs,
    ]
    for validator in validators:
        result = validator(repo)
        if result != EXIT_SUCCESS:
            return result

    print("TG3 workflow and configuration contracts validated.")
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())