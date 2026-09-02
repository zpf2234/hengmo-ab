#!/usr/bin/env python3
"""Validate the CUMCM A/B archetype-routed model and algorithm catalog."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


REQUIRED_ROOT_FIELDS = {
    "schema_version",
    "catalog_id",
    "scope",
    "selection_policy",
    "candidate_roles",
    "claim_levels",
    "algorithm_contracts",
    "archetypes",
    "historical_problem_index",
}

REQUIRED_ARCHETYPE_FIELDS = {
    "id",
    "name",
    "problem_signature",
    "baseline_families",
    "main_candidate_families",
    "heterogeneous_challenges",
    "required_validation",
    "hard_rejections",
    "claim_ceiling",
    "historical_calibration",
}

NONEMPTY_ARCHETYPE_ARRAYS = {
    "problem_signature",
    "baseline_families",
    "main_candidate_families",
    "heterogeneous_challenges",
    "required_validation",
    "hard_rejections",
}

REQUIRED_ROLES = {
    "baseline",
    "main_candidate",
    "heterogeneous_challenge",
    "fallback",
}

MONTE_CARLO_EVIDENCE = {
    "uncertainty_source",
    "sampling_plan",
    "sample_size_rationale",
    "seed_policy",
    "interval_method",
    "variance_or_effective_sample_size",
    "stopping_rule",
    "multiplicity_control_for_multi_candidate_selection",
    "independent_confirmation_for_adaptive_selection",
}

FORBIDDEN_ROUTING_PHRASES = {
    "a题使用",
    "b题使用",
    "a题优先",
    "b题优先",
    "a题默认",
    "b题默认",
    "monte carlo is mandatory",
    "灰色预测适合小样本",
    "元启发式证明全局最优",
}


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    repeated: set[str] = set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return sorted(repeated)


def _expect_string_list(
    container: dict[str, Any],
    field: str,
    location: str,
    errors: list[str],
    *,
    nonempty: bool = True,
) -> list[str]:
    value = container.get(field)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        errors.append(f"{location}.{field} must be a list of strings")
        return []
    if nonempty and not value:
        errors.append(f"{location}.{field} must not be empty")
    duplicates = _duplicates(value)
    if duplicates:
        errors.append(f"{location}.{field} contains duplicates: {duplicates}")
    return value


def validate_document(document: Any) -> list[str]:
    """Return validation errors; an empty list means the catalog is valid."""
    errors: list[str] = []
    if not isinstance(document, dict):
        return ["catalog root must be a JSON object"]

    missing_root = sorted(REQUIRED_ROOT_FIELDS - set(document))
    if missing_root:
        errors.append(f"catalog missing root fields: {missing_root}")

    scope = document.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be an object")
    else:
        if scope.get("contest") != "CUMCM":
            errors.append("scope.contest must equal CUMCM")
        if scope.get("problem_letters") != ["A", "B"]:
            errors.append("scope.problem_letters must be exactly ['A', 'B']")
        routing_keys = _expect_string_list(scope, "routing_keys", "scope", errors)
        excluded = _expect_string_list(
            scope, "routing_key_excludes", "scope", errors
        )
        if "problem_letter" not in excluded:
            errors.append("scope.routing_key_excludes must contain problem_letter")
        if "problem_letter" in routing_keys:
            errors.append("problem_letter must never be a routing key")
        if scope.get("same_problem_answer_leakage_forbidden") is not True:
            errors.append(
                "scope.same_problem_answer_leakage_forbidden must be true"
            )

    roles = document.get("candidate_roles")
    if not isinstance(roles, list) or any(not isinstance(role, str) for role in roles):
        errors.append("candidate_roles must be a list of strings")
    elif set(roles) != REQUIRED_ROLES:
        errors.append(
            "candidate_roles must contain exactly baseline, main_candidate, "
            "heterogeneous_challenge, fallback"
        )

    selection_policy = document.get("selection_policy")
    if not isinstance(selection_policy, dict):
        errors.append("selection_policy must be an object")
    else:
        if selection_policy.get("principle") != "minimum_sufficient_method":
            errors.append(
                "selection_policy.principle must equal minimum_sufficient_method"
            )
        _expect_string_list(
            selection_policy,
            "priority_order",
            "selection_policy",
            errors,
        )
        _expect_string_list(
            selection_policy,
            "simple_method_wins_when",
            "selection_policy",
            errors,
        )
        _expect_string_list(
            selection_policy,
            "complexity_upgrade_requires",
            "selection_policy",
            errors,
        )
        if selection_policy.get("algorithm_label_has_no_score") is not True:
            errors.append(
                "selection_policy.algorithm_label_has_no_score must be true"
            )

    claim_levels = document.get("claim_levels")
    claim_level_ids: set[str] = set()
    if not isinstance(claim_levels, dict) or not claim_levels:
        errors.append("claim_levels must be a non-empty object")
    else:
        claim_level_ids = set(claim_levels)
        for level_id, contract in claim_levels.items():
            location = f"claim_levels.{level_id}"
            if not isinstance(contract, dict):
                errors.append(f"{location} must be an object")
                continue
            _expect_string_list(contract, "allowed_claims", location, errors)
            _expect_string_list(contract, "minimum_evidence", location, errors)

    contracts = document.get("algorithm_contracts")
    if not isinstance(contracts, dict) or not contracts:
        errors.append("algorithm_contracts must be a non-empty object")
        contracts = {}
    else:
        for contract_id, contract in contracts.items():
            location = f"algorithm_contracts.{contract_id}"
            if not isinstance(contract, dict):
                errors.append(f"{location} must be an object")
                continue
            _expect_string_list(contract, "use_when", location, errors)
            _expect_string_list(contract, "required_evidence", location, errors)
            if not isinstance(contract.get("claim_limit"), str):
                errors.append(f"{location}.claim_limit must be a string")

    monte_carlo = contracts.get("monte_carlo")
    if not isinstance(monte_carlo, dict):
        errors.append("algorithm_contracts.monte_carlo is required")
    else:
        mc_evidence = set(monte_carlo.get("required_evidence", []))
        missing = sorted(MONTE_CARLO_EVIDENCE - mc_evidence)
        if missing:
            errors.append(
                "algorithm_contracts.monte_carlo missing evidence controls: "
                f"{missing}"
            )

    metaheuristic = contracts.get("metaheuristic_search")
    if not isinstance(metaheuristic, dict):
        errors.append("algorithm_contracts.metaheuristic_search is required")
    else:
        limit = metaheuristic.get("claim_limit")
        if limit != "L2_best_known":
            errors.append(
                "metaheuristic_search claim_limit must be L2_best_known"
            )

    archetypes = document.get("archetypes")
    archetype_ids: list[str] = []
    if not isinstance(archetypes, list) or not archetypes:
        errors.append("archetypes must be a non-empty list")
        archetypes = []
    for index, archetype in enumerate(archetypes):
        location = f"archetypes[{index}]"
        if not isinstance(archetype, dict):
            errors.append(f"{location} must be an object")
            continue
        missing = sorted(REQUIRED_ARCHETYPE_FIELDS - set(archetype))
        if missing:
            errors.append(f"{location} missing fields: {missing}")
        archetype_id = archetype.get("id")
        if not isinstance(archetype_id, str) or not re.fullmatch(
            r"[A-Z][A-Z0-9_]*", archetype_id
        ):
            errors.append(f"{location}.id must use UPPER_SNAKE_CASE")
        else:
            archetype_ids.append(archetype_id)
        if not isinstance(archetype.get("name"), str) or not archetype.get("name"):
            errors.append(f"{location}.name must be a non-empty string")
        for field in NONEMPTY_ARCHETYPE_ARRAYS:
            _expect_string_list(archetype, field, location, errors)
        _expect_string_list(
            archetype,
            "historical_calibration",
            location,
            errors,
            nonempty=False,
        )
        ceiling = archetype.get("claim_ceiling")
        if ceiling not in claim_level_ids:
            errors.append(
                f"{location}.claim_ceiling references unknown level: {ceiling}"
            )

    duplicate_ids = _duplicates(archetype_ids)
    if duplicate_ids:
        errors.append(f"duplicate archetype ids: {duplicate_ids}")
    archetype_id_set = set(archetype_ids)

    history = document.get("historical_problem_index")
    historical_ids: list[str] = []
    if not isinstance(history, list) or not history:
        errors.append("historical_problem_index must be a non-empty list")
        history = []
    for index, record in enumerate(history):
        location = f"historical_problem_index[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{location} must be an object")
            continue
        problem = record.get("problem")
        if not isinstance(problem, str) or not re.fullmatch(
            r"20\d{2}[AB]", problem
        ):
            errors.append(f"{location}.problem must look like 2025A or 2025B")
        else:
            historical_ids.append(problem)
        routes = _expect_string_list(record, "routes", location, errors)
        unknown = sorted(set(routes) - archetype_id_set)
        if unknown:
            errors.append(f"{location}.routes references unknown ids: {unknown}")

    duplicate_history = _duplicates(historical_ids)
    if duplicate_history:
        errors.append(f"duplicate historical problem ids: {duplicate_history}")

    serialized = json.dumps(document, ensure_ascii=False).lower()
    for phrase in sorted(FORBIDDEN_ROUTING_PHRASES):
        if phrase in serialized:
            errors.append(f"forbidden letter/stereotype routing phrase: {phrase}")

    return errors


def default_catalog_path() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "ab-model-routing.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalog",
        type=Path,
        default=default_catalog_path(),
        help="Path to ab-model-routing.json",
    )
    args = parser.parse_args()

    try:
        document = json.loads(args.catalog.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {"status": "FAIL", "catalog": str(args.catalog), "errors": [str(exc)]},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    errors = validate_document(document)
    report = {
        "status": "PASS" if not errors else "FAIL",
        "catalog": str(args.catalog),
        "archetype_count": len(document.get("archetypes", [])),
        "algorithm_contract_count": len(document.get("algorithm_contracts", {})),
        "historical_problem_count": len(document.get("historical_problem_index", [])),
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
