#!/usr/bin/env python3
"""Regression tests for the CUMCM A/B model catalog validator."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from validate_ab_model_catalog import default_catalog_path, validate_document


def expect_failure(name: str, document: dict, expected_fragment: str) -> str:
    errors = validate_document(document)
    if not errors:
        raise AssertionError(f"{name}: invalid fixture unexpectedly passed")
    if not any(expected_fragment in error for error in errors):
        raise AssertionError(
            f"{name}: expected error containing {expected_fragment!r}, got {errors}"
        )
    return name


def main() -> int:
    source = json.loads(default_catalog_path().read_text(encoding="utf-8"))
    valid_errors = validate_document(source)
    if valid_errors:
        raise AssertionError(f"valid catalog failed: {valid_errors}")

    passed = ["valid_catalog"]

    missing_field = copy.deepcopy(source)
    missing_field["archetypes"][0].pop("required_validation")
    passed.append(
        expect_failure(
            "missing_required_validation",
            missing_field,
            "missing fields",
        )
    )

    letter_routing = copy.deepcopy(source)
    letter_routing["scope"]["routing_keys"].append("problem_letter")
    passed.append(
        expect_failure(
            "problem_letter_as_routing_key",
            letter_routing,
            "must never be a routing key",
        )
    )

    algorithm_label_bonus = copy.deepcopy(source)
    algorithm_label_bonus["selection_policy"]["algorithm_label_has_no_score"] = False
    passed.append(
        expect_failure(
            "algorithm_label_bonus",
            algorithm_label_bonus,
            "algorithm_label_has_no_score must be true",
        )
    )

    weak_monte_carlo = copy.deepcopy(source)
    weak_monte_carlo["algorithm_contracts"]["monte_carlo"][
        "required_evidence"
    ].remove("multiplicity_control_for_multi_candidate_selection")
    passed.append(
        expect_failure(
            "monte_carlo_without_multiplicity_control",
            weak_monte_carlo,
            "missing evidence controls",
        )
    )

    global_metaheuristic = copy.deepcopy(source)
    global_metaheuristic["algorithm_contracts"]["metaheuristic_search"][
        "claim_limit"
    ] = "L4_exact_global"
    passed.append(
        expect_failure(
            "metaheuristic_global_overclaim",
            global_metaheuristic,
            "must be L2_best_known",
        )
    )

    unknown_route = copy.deepcopy(source)
    unknown_route["historical_problem_index"][0]["routes"].append("UNKNOWN")
    passed.append(
        expect_failure(
            "unknown_historical_route",
            unknown_route,
            "references unknown ids",
        )
    )

    print(
        json.dumps(
            {"status": "PASS", "cases": passed, "case_count": len(passed)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
