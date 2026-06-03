import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "innovation_plan.json"


def _load_plan() -> dict:
    assert PLAN_PATH.exists(), "Create innovation_plan.json at the repository root"
    try:
        plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"innovation_plan.json must be valid JSON: {exc}") from exc
    assert isinstance(plan, dict), "innovation_plan.json must contain a JSON object"
    return plan


def _flatten(value: object) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten(item) for item in value)
    return str(value)


def _text(plan: dict) -> str:
    return _flatten(plan).lower()


def test_plan_has_counterexample_sections() -> None:
    plan = _load_plan()
    required = {
        "claim_status",
        "default_claim",
        "why_coloring_intuition_can_fail",
        "branches",
        "representation_shift",
        "counterexample_families",
        "generator_plan",
        "certificate_plan",
        "negative_controls",
        "ranked_next_experiments",
    }
    assert required.issubset(plan), f"Missing sections: {sorted(required - set(plan))}"
    assert plan["claim_status"] in {"hypothesis", "search-plan", "unverified", "candidate"}


def test_default_claim_names_greedy_spread_and_d_plus_one_gap() -> None:
    plan = _load_plan()
    text = _text(plan)
    assert "greedy-spread" in text or "greedy spread" in text
    assert "d + 1" in text or "d+1" in text or "maximum degree" in text
    assert "lowest" in text and "volume" in text
    assert any(term in text for term in ["not graph coloring", "vertex order", "algorithm", "heuristic"])


def test_branches_prioritize_adversarial_constructions() -> None:
    plan = _load_plan()
    branches = plan["branches"]
    assert isinstance(branches, list)
    assert len(branches) >= 4

    branch_text = _flatten(branches).lower()
    assert any(term in branch_text for term in ["counterexample", "adversarial", "gadget", "bad order"])
    assert any(term in branch_text for term in ["brute force", "enumerate", "sat", "ilp", "solver"])

    for branch in branches:
        assert isinstance(branch, dict)
        for key in ["name", "construction_hypothesis", "search_method", "verification", "risk"]:
            assert branch.get(key), f"branch missing {key}: {branch}"


def test_representation_shift_uses_conflict_graph_or_constraints() -> None:
    plan = _load_plan()
    shift = plan["representation_shift"]
    assert isinstance(shift, dict)
    for key in ["from", "to", "visible_invariant", "testable_prediction"]:
        assert shift.get(key), f"representation_shift missing {key}"

    text = _text(plan)
    assert "conflict graph" in text
    assert any(term in text for term in ["graph coloring", "greedy coloring", "vertex order", "chromatic"])
    assert any(term in text for term in ["constraint", "sat", "ilp", "brute force", "enumerate"])


def test_counterexample_family_and_generator_are_specific() -> None:
    plan = _load_plan()
    families = plan["counterexample_families"]
    generator = plan["generator_plan"]
    assert isinstance(families, list)
    assert len(families) >= 3
    assert isinstance(generator, dict)

    family_text = _flatten(families).lower()
    assert any(term in family_text for term in ["gadget", "crown", "cycle", "path", "clique", "decoy"])
    assert any(term in family_text for term in ["compose", "scale", "parameter", "family"])

    for family in families:
        assert isinstance(family, dict)
        for key in ["name", "parameters", "expected_failure", "shrink_strategy"]:
            assert family.get(key), f"counterexample family missing {key}: {family}"

    for key in ["instance_schema", "search_procedure", "shrinker", "outputs"]:
        assert generator.get(key), f"generator_plan missing {key}"


def test_certificate_plan_can_accept_or_falsify() -> None:
    plan = _load_plan()
    certificate = plan["certificate_plan"]
    controls = plan["negative_controls"]
    assert isinstance(certificate, dict)
    assert isinstance(controls, list)
    assert len(controls) >= 3

    for key in ["checker", "counterexample_criteria", "support_criteria", "falsification_tests"]:
        assert certificate.get(key), f"certificate_plan missing {key}"

    text = _text(plan)
    assert any(term in text for term in ["pytest", "property test", "checker", "certificate"])
    assert any(term in text for term in ["minimal", "shrink", "smallest", "delta-debug"])
    assert any(term in text for term in ["raw volume", "conflict concentration", "slot"])


def test_next_experiments_are_ranked_and_plan_avoids_false_certainty() -> None:
    plan = _load_plan()
    experiments = plan["ranked_next_experiments"]
    assert isinstance(experiments, list)
    assert len(experiments) >= 3
    for experiment in experiments:
        assert isinstance(experiment, dict)
        for key in ["rank", "experiment", "expected_signal", "stop_condition"]:
            assert experiment.get(key) is not None, f"experiment missing {key}: {experiment}"

    text = _text(plan)
    forbidden = [
        "proved the claim false",
        "disproved greedy-spread",
        "proved greedy-spread",
        "guaranteed counterexample",
    ]
    for phrase in forbidden:
        assert phrase not in text
    assert any(term in text for term in ["hypothesis", "candidate", "unverified", "falsify", "search"])
