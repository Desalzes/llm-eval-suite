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


def _lower_text(plan: dict) -> str:
    return _flatten(plan).lower()


def test_plan_has_required_top_level_sections() -> None:
    plan = _load_plan()
    required = {
        "claim_status",
        "default_framing",
        "default_failure_mode",
        "branches",
        "remote_analogies",
        "representation_shifts",
        "construction_search",
        "certificate_plan",
        "ranked_next_experiments",
        "discarded_branches",
    }
    assert required.issubset(plan), f"Missing sections: {sorted(required - set(plan))}"
    assert plan["claim_status"] in {"hypothesis", "candidate", "search-plan", "unverified"}


def test_branches_are_independent_and_testable() -> None:
    plan = _load_plan()
    branches = plan["branches"]
    assert isinstance(branches, list)
    assert len(branches) >= 5

    names = []
    for branch in branches:
        assert isinstance(branch, dict)
        for key in ["name", "hypothesis", "mechanism", "verification", "risk"]:
            assert branch.get(key), f"branch missing {key}: {branch}"
        names.append(str(branch["name"]).strip().lower())

    assert len(set(names)) == len(names), "Branch names must be distinct"
    mechanisms = [str(branch["mechanism"]).lower() for branch in branches]
    assert len(set(mechanisms)) >= 4, "Branches should not be paraphrases of one mechanism"


def test_remote_analogies_explain_transfer_and_failure_modes() -> None:
    plan = _load_plan()
    analogies = plan["remote_analogies"]
    assert isinstance(analogies, list)
    assert len(analogies) >= 2

    analogy_text = " ".join(_flatten(analogy).lower() for analogy in analogies)
    assert any(term in analogy_text for term in ["coding theory", "error-correcting", "hamming"])
    assert any(term in analogy_text for term in ["lattice", "number theory", "hashing", "sat", "ilp"])

    for analogy in analogies:
        assert isinstance(analogy, dict)
        for key in ["source_domain", "borrowed_move", "why_it_might_transfer", "failure_mode"]:
            assert analogy.get(key), f"analogy missing {key}: {analogy}"


def test_representation_shift_hits_overlap_as_vector_or_matrix_problem() -> None:
    plan = _load_plan()
    shifts = plan["representation_shifts"]
    assert isinstance(shifts, list)
    assert len(shifts) >= 1

    text = _lower_text(plan)
    representation_terms = [
        "incidence vector",
        "bit vector",
        "boolean cube",
        "matrix",
        "dot product",
        "overlap matrix",
        "cohort cell",
    ]
    assert sum(term in text for term in representation_terms) >= 3
    assert any(term in text for term in ["parity", "hamming", "residue", "orthogonal", "low-correlation"])

    for shift in shifts:
        assert isinstance(shift, dict)
        for key in ["from", "to", "new_invariant", "testable_prediction"]:
            assert shift.get(key), f"representation shift missing {key}: {shift}"


def test_construction_search_and_certificate_are_executable_enough() -> None:
    plan = _load_plan()
    search = plan["construction_search"]
    certificate = plan["certificate_plan"]
    assert isinstance(search, dict)
    assert isinstance(certificate, dict)

    for key in ["candidate_family", "search_procedure", "parameters", "negative_controls"]:
        assert search.get(key), f"construction_search missing {key}"
    for key in ["checker", "acceptance_criteria", "falsification_tests"]:
        assert certificate.get(key), f"certificate_plan missing {key}"

    text = _lower_text(plan)
    assert any(term in text for term in ["enumerate", "brute force", "exhaustive", "generator", "sat", "ilp"])
    assert any(term in text for term in ["pytest", "property test", "checker", "falsify", "counterexample"])


def test_next_experiments_and_discarded_branches_are_specific() -> None:
    plan = _load_plan()
    experiments = plan["ranked_next_experiments"]
    discarded = plan["discarded_branches"]
    assert isinstance(experiments, list)
    assert len(experiments) >= 3
    assert isinstance(discarded, list)
    assert len(discarded) >= 2

    for experiment in experiments:
        assert isinstance(experiment, dict)
        for key in ["rank", "experiment", "expected_signal", "stop_condition"]:
            assert experiment.get(key) is not None, f"experiment missing {key}: {experiment}"

    for branch in discarded:
        assert isinstance(branch, dict)
        assert branch.get("name")
        assert branch.get("discard_reason")


def test_plan_avoids_false_certainty() -> None:
    plan = _load_plan()
    text = _lower_text(plan)
    forbidden = [
        "proved the conjecture",
        "solved the problem",
        "guaranteed optimum",
        "mathematical proof is complete",
    ]
    for phrase in forbidden:
        assert phrase not in text
    assert any(term in text for term in ["hypothesis", "candidate", "unverified", "falsify", "test"])
