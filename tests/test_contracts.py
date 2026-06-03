import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from suite.contracts import validate_contract, validate_findings_file, validate_workspace_contracts


ROOT = Path(__file__).resolve().parents[1]


class ContractsTests(unittest.TestCase):
    def test_workspace_contract_validation_accepts_current_inputs(self) -> None:
        errors = validate_workspace_contracts(ROOT)

        self.assertEqual(errors, [])

    def test_task_contract_reports_missing_required_field(self) -> None:
        errors = validate_contract(
            "task",
            {
                "id": "broken-task",
                "title": "Broken Task",
                "description": "Missing allowed paths.",
                "repo": "repo",
                "test_command": ["python", "-m", "unittest"],
                "success_criteria": ["It validates."],
            },
        )

        self.assertIn("$.allowed_paths is required", errors)

    def test_finding_contract_requires_provenance_and_approval_tier(self) -> None:
        errors = validate_contract(
            "finding",
            {
                "schema_version": "finding_v1",
                "finding_id": "unit-1",
                "detector_id": "unit.detector",
                "artifact_id": "artifact-1",
                "finding_type": "tests_failed",
                "severity": "medium",
                "confidence": "high",
                "summary": "Tests failed.",
                "affected_artifacts": [],
                "suggested_fix": "Inspect the failed test output.",
            },
        )

        self.assertIn("$.provenance is required", errors)
        self.assertIn("$.required_approval_tier is required", errors)

    def test_findings_file_validation_reports_line_numbered_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="findings-contract-test-") as temp_dir:
            findings_path = Path(temp_dir) / "findings.jsonl"
            findings_path.write_text(
                json.dumps(
                    {
                        "schema_version": "finding_v1",
                        "finding_id": "bad-1",
                        "detector_id": "unit.detector",
                        "artifact_id": "artifact-1",
                        "finding_type": "tests_failed",
                        "severity": "medium",
                        "confidence": "high",
                        "summary": "Tests failed.",
                        "affected_artifacts": [],
                        "provenance": {},
                        "suggested_fix": "Inspect output.",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            errors = validate_findings_file(findings_path)

        self.assertEqual(errors, ["line 1: $.required_approval_tier is required"])

    def test_validate_contracts_cli_prints_json_summary(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "validate-contracts",
                "--root",
                str(ROOT),
                "--json",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        summary = json.loads(completed.stdout)
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["errors"], [])
        self.assertGreater(summary["validated_files"], 0)


from unittest.mock import patch

from suite import contracts as contracts_module


class ValidatorUnsupportedKeywordRegressionTests(unittest.TestCase):
    """Once we adopt jsonschema, schemas using `pattern` must actually validate.

    The hand-rolled validator silently passes `pattern`; this test fails against
    it and passes against jsonschema. Lock the regression in place so we never
    silently revert.
    """

    def tearDown(self):
        # After Task 4 the validator is lru_cache-decorated; clearing the cache
        # here ensures the patched synthetic schema does not leak across tests.
        # Pre-swap _get_validator does not exist; getattr keeps this runnable today.
        cache_clear = getattr(getattr(contracts_module, "_get_validator", None), "cache_clear", None)
        if cache_clear is not None:
            cache_clear()

    def test_pattern_keyword_rejects_nonmatching_value(self):
        synthetic_schema = {
            "type": "object",
            "required": ["code"],
            "properties": {"code": {"type": "string", "pattern": "^[A-Z]{3}-[0-9]+$"}},
        }
        with patch.object(contracts_module, "_load_schema", return_value=synthetic_schema):
            errors = contracts_module.validate_contract("__test_pattern__", {"code": "lowercase-bad"})
        self.assertNotEqual(errors, [], "pattern keyword must reject non-matching values")


class ValidatorErrorFormatStabilityTests(unittest.TestCase):
    """Lock today's error message shape so the jsonschema swap can preserve it."""

    def test_type_mismatch_at_root(self):
        # finding schema requires object at root
        errors = validate_contract("finding", "not-an-object")
        self.assertEqual(errors, ["$ must be object, got string"])

    def test_type_mismatch_at_nested_path(self):
        # run-result.tests_passed must be boolean
        bad = {
            "run_id": "x",
            "status": "passed",
            "tests_passed": "not-a-bool",
        }
        errors = validate_contract("run-result", bad)
        self.assertIn("$.tests_passed must be boolean, got string", errors)

    def test_required_missing_at_root(self):
        errors = validate_contract("run-result", {})
        # run-result requires exactly ["run_id", "status"]
        self.assertIn("$.run_id is required", errors)
        self.assertIn("$.status is required", errors)

    def test_enum_violation(self):
        bad = {
            "run_id": "x",
            "status": "not-a-valid-status",
        }
        errors = validate_contract("run-result", bad)
        # status enum: passed, failed, unsafe, timeout, idle_timeout, capped, missing_result
        match = [e for e in errors if e.startswith("$.status must be one of")]
        self.assertEqual(len(match), 1, f"expected one enum error for $.status, got: {errors}")

    def test_additional_property_not_allowed(self):
        # finding schema has additionalProperties: false
        good = {
            "schema_version": "finding_v1",
            "finding_id": "abc1234567890123",
            "detector_id": "d",
            "artifact_id": "a",
            "finding_type": "issue",
            "severity": "low",
            "confidence": "high",
            "summary": "s",
            "affected_artifacts": [],
            "provenance": {},
            "suggested_fix": "x",
            "required_approval_tier": "none",
            "details": {},
            "unexpected_extra_field": "boom",
        }
        errors = validate_contract("finding", good)
        self.assertIn("$.unexpected_extra_field is not allowed", errors)


POSITIVE_EXAMPLES = {
    "task": {
        "id": "t",
        "title": "T",
        "description": "d",
        "repo": "tasks/fixtures/example/repo",
        "test_command": ["pytest"],
        "allowed_paths": [],
        "success_criteria": [],
    },
    "profile": {
        "id": "p",
        "name": "P",
        "description": "d",
        "command": ["echo"],
    },
    "eval-set": {
        "id": "s",
        "name": "S",
        "description": "d",
        "tasks": [],
    },
    "run-result": {
        "run_id": "r",
        "status": "passed",
    },
    "eval-summary": {
        "run_id": "r",
        "run_dir": "/tmp/r",
        "set_id": "s",
        "profile_id": "p",
        "status": "passed",
        "status_counts": {},
        "weighted_status_counts": {},
        "runs": [],
    },
    "finding": {
        "schema_version": "finding_v1",
        "finding_id": "abc1234567890123",
        "detector_id": "d",
        "artifact_id": "a",
        "finding_type": "issue",
        "severity": "low",
        "confidence": "high",
        "summary": "s",
        "affected_artifacts": [],
        "provenance": {},
        "suggested_fix": "x",
        "required_approval_tier": "none",
    },
    "project-pack": {
        "id": "pp",
        "name": "PP",
        "source_path": "/tmp/pp",
        "isolation_mode": "worktree",
        "branch_prefix": "feature/",
        "allow_immediate_work": True,
        "allow_external_loop": False,
    },
    "orientation": {
        "schema_version": "orientation_v1",
        "session_id": "sess",
        "scope": "scope",
        "started_at": "2026-05-27T00:00:00Z",
        "git_snapshot": {
            "branch": None,
            "head": None,
            "status_lines": [],
            "recent_commits": [],
        },
        "reads": [],
        "status_snapshot_path": "/tmp/snap.json",
    },
    "handoff": {
        "schema_version": "handoff_v1",
        "session_id": "sess",
        "scope": "scope",
        "ended_at": "2026-05-27T00:00:00Z",
        "mode": "handoff",
        "authority_level": "docs-only",
        "git_state": {
            "branch": None,
            "head": None,
            "diff_since_orient": [],
        },
        "what_checked": [],
        "what_changed": [],
        "next_action": "review",
        "unresolved_risks": [],
    },
    "compliance": {
        "schema_version": "compliance_v1",
        "session_id": "sess",
        "verified_at": "2026-05-27T00:00:00Z",
        "rules": [],
        "overall": "pass",
    },
    "amadeus-session": {
        "schema_version": "amadeus_session_v1",
        "session_id": "sess",
        "created_at": "2026-05-27T00:00:00Z",
        "updated_at": "2026-05-27T00:00:00Z",
        "repo_root": "/tmp/repo",
        "status": "fast_ready",
        "git_snapshot": {
            "branch": None,
            "head": None,
            "status_lines": [],
            "recent_commits": [],
        },
        "fast_brief": {
            "status": "complete",
            "path": "/tmp/brief.json",
            "generated_at": None,
        },
        "deep_refresh": {
            "status": "not_started",
            "path": "/tmp/refresh.json",
            "command": "noop",
            "started_at": None,
            "completed_at": None,
            "process_id": None,
            "stdout_path": None,
            "stderr_path": None,
            "error": None,
        },
        "live_checks": {
            "network": False,
            "ssh": False,
            "browser": False,
            "api": False,
            "service_status": False,
        },
        "artifacts": [],
    },
    "amadeus-delegation-job": {
        "schema_version": "amadeus_delegation_job_v1",
        "job_id": "amadeus-job-20260531-120000",
        "created_at": "2026-05-31T12:00:00Z",
        "updated_at": "2026-05-31T12:00:00Z",
        "repo_root": "/tmp/repo",
        "session_id": "amadeus-20260531-120000",
        "user_request": "What is the state of the rebuild?",
        "project_hint": "ChatGPT",
        "authority": "read_only",
        "requested_output": "status_report",
        "status": "created",
        "scoper": {
            "required": True,
            "prompt_path": "runs/amadeus-delegations/amadeus-job-20260531-120000/scoper-prompt.md",
            "agent_session_dir": None,
        },
        "worker": {
            "backend": None,
            "profile_path": None,
            "prompt_path": "runs/amadeus-delegations/amadeus-job-20260531-120000/worker-prompt.md",
            "report_path": "runs/amadeus-delegations/amadeus-job-20260531-120000/worker-report.json",
            "agent_session_dir": None,
            "allowed_paths": [],
            "run_evidence": None,
        },
        "worker_report_sha256": None,
        "artifacts": [
            "job.json",
            "scoper-prompt.md",
            "worker-prompt.md",
        ],
    },
    "amadeus-worker-report": {
        "schema_version": "amadeus_worker_report_v1",
        "job_id": "amadeus-job-20260531-120000",
        "created_at": "2026-05-31T12:01:00Z",
        "role": "scoper",
        "request": "What is the state of the rebuild?",
        "scope_decision": {
            "work_type": "status",
            "needs_live_access": False,
            "needs_code_changes": False,
            "needs_followup_workers": False,
        },
        "authority_used": ["docs/session-handoff.md"],
        "summary": "The rebuild needs a read-only status report.",
        "findings": [
            {
                "claim": "A status report is enough for this request.",
                "basis": "The user asked where things stand, not for a fix.",
                "confidence": "high",
            }
        ],
        "evidence": ["request text"],
        "unknowns": ["No worker has inspected source yet."],
        "recommended_next_action": "Run an investigator worker.",
        "changed_files": [],
        "verification": [],
        "confidence": "high",
    },
    "relay-handoff": {
        "schema_version": "relay_handoff_v1",
        "session_id": "sess",
        "scope": "scope",
        "scope_marker": "marker",
        "project": "project",
        "hard_rules": [],
        "source_boundaries": [],
        "changed_files": [],
        "generated_artifacts": [],
        "unresolved_risks": [],
        "next_action": "review",
        "verification_evidence": [],
        "project_pack_authority_reads": [],
    },
    "polymarket-market-snapshot": {
        "schema_version": "polymarket_market_snapshot_v1",
        "snapshot_id": "snap1",
        "captured_at": "2026-05-27T00:00:00Z",
        "source": "gamma",
        "source_url": "https://example.com",
        "market_id": "m1",
        "event_slug": "evt",
        "question": "?",
        "outcomes": [],
        "prices": {},
        "orderbook": {},
        "volume": None,
        "liquidity": None,
        "end_date": None,
        "closed": False,
        "resolution_status": "open",
        "raw_artifact": {},
    },
    "polymarket-hypothesis": {
        "schema_version": "polymarket_hypothesis_v1",
        "hypothesis_id": "h1",
        "created_at": "2026-05-27T00:00:00Z",
        "agent_profile_id": "p",
        "model": "m",
        "market_scope": "single",
        "market_id": "m1",
        "source_snapshot_id": "snap1",
        "question": "?",
        "outcomes": [],
        "prices": {},
        "thesis": "t",
        "entry_rule": "e",
        "exit_rule": "x",
        "position_sizing_rule": "ps",
        "data_requirements": [],
        "expected_edge": "edge",
        "known_risks": [],
        "falsification_rule": "f",
        "paper_only": True,
        "claim_ids": [],
    },
    "polymarket-paper-trade": {
        "schema_version": "polymarket_paper_trade_v1",
        "paper_trade_id": "pt1",
        "opened_at": "2026-05-27T00:00:00Z",
        "closed_at": None,
        "status": "open",
        "hypothesis_id": "h1",
        "market_id": "m1",
        "source_snapshot_id": "snap1",
        "question": "?",
        "side": "buy",
        "outcome": "yes",
        "reference_price": 0.5,
        "paper_size": 10.0,
        "limit_price": 0.5,
        "simulated_fill_price": 0.5,
        "fill_assumption": "midpoint",
        "slippage_assumption": 0.01,
        "fees_assumption": 0.0,
        "exit_reason": "none",
        "paper_pnl": 0.0,
        "paper_only": True,
        "live_trading": False,
        "claim_ids": [],
        "safety_notes": [],
        "risk_notes": [],
    },
}


class PerSchemaPositiveSmokeTests(unittest.TestCase):
    """Each registered schema accepts at least one minimal valid example."""

    def test_each_registered_contract_has_a_positive_example(self):
        from suite.contracts import SCHEMA_FILES
        missing = set(SCHEMA_FILES) - set(POSITIVE_EXAMPLES)
        self.assertFalse(missing, f"missing positive examples for: {sorted(missing)}")

    def test_examples_validate_clean(self):
        for contract, example in POSITIVE_EXAMPLES.items():
            with self.subTest(contract=contract):
                errors = validate_contract(contract, example)
                self.assertEqual(errors, [], f"{contract}: {errors}")


class AmadeusContractRegressionTests(unittest.TestCase):
    def test_worker_report_rejects_malformed_job_id(self):
        bad = {
            **POSITIVE_EXAMPLES["amadeus-worker-report"],
            "job_id": "not-a-job",
        }

        errors = validate_contract("amadeus-worker-report", bad)

        self.assertTrue(
            any(error.startswith("$.job_id:") and "does not match" in error for error in errors),
            f"expected $.job_id pattern error, got: {errors}",
        )


class PerSchemaNegativeTests(unittest.TestCase):
    """One required-missing test per schema, plus additionalProperties where applicable."""

    def test_required_field_missing_each_schema(self):
        from suite.contracts import SCHEMA_FILES, _load_schema
        for contract in SCHEMA_FILES:
            schema = _load_schema(contract)
            required = schema.get("required", [])
            if not required:
                continue
            with self.subTest(contract=contract):
                errors = validate_contract(contract, {})
                self.assertTrue(
                    any(f"$.{key} is required" in errors for key in required),
                    f"{contract}: expected required-missing error for one of {required}, got: {errors}",
                )

    def test_additional_property_blocked_each_schema(self):
        from suite.contracts import SCHEMA_FILES, _load_schema
        for contract in SCHEMA_FILES:
            schema = _load_schema(contract)
            if schema.get("additionalProperties") is not False:
                continue
            example = POSITIVE_EXAMPLES.get(contract)
            if example is None or not isinstance(example, dict):
                continue
            poisoned = {**example, "__unexpected_stray_field__": "boom"}
            with self.subTest(contract=contract):
                errors = validate_contract(contract, poisoned)
                self.assertIn(
                    "$.__unexpected_stray_field__ is not allowed",
                    errors,
                    f"{contract}: expected additionalProperties error, got: {errors}",
                )


class WorkspaceContractsIntegrationTests(unittest.TestCase):
    """Synthesize a tmp workspace with one valid + one invalid file per
    file-on-disk contract type. validate_workspace_contracts must report
    exactly the invalid files."""

    def test_workspace_validation_collects_errors_per_contract(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "profiles").mkdir()
            (root / "tasks" / "eval-sets").mkdir(parents=True)
            (root / "tasks" / "examples" / "good").mkdir(parents=True)
            (root / "tasks" / "fixtures" / "bad").mkdir(parents=True)
            # Valid profile (uses 'description' which is required per the schema)
            (root / "profiles" / "valid.json").write_text(json.dumps({
                "id": "p", "name": "P", "description": "d", "command": ["echo"],
            }), encoding="utf-8")
            # Invalid profile (missing required 'command')
            (root / "profiles" / "invalid.json").write_text(json.dumps({
                "id": "p", "name": "P", "description": "d",
            }), encoding="utf-8")
            # Valid eval-set
            (root / "tasks" / "eval-sets" / "good.json").write_text(json.dumps({
                "id": "s", "name": "S", "description": "d", "tasks": [],
            }), encoding="utf-8")
            # Invalid task (missing several required fields)
            (root / "tasks" / "fixtures" / "bad" / "task.json").write_text(json.dumps({
                "id": "t",
            }), encoding="utf-8")
            # Valid task
            (root / "tasks" / "examples" / "good" / "task.json").write_text(json.dumps({
                "id": "t", "title": "T", "description": "d",
                "repo": "tasks/examples/good/repo",
                "test_command": ["pytest"],
                "allowed_paths": [], "success_criteria": [],
            }), encoding="utf-8")
            errors = validate_workspace_contracts(root)
            self.assertTrue(any("profiles/invalid.json" in e for e in errors),
                            f"expected error for invalid profile, got: {errors}")
            self.assertTrue(any("tasks/fixtures/bad/task.json" in e for e in errors),
                            f"expected error for invalid task, got: {errors}")
            self.assertFalse(any("profiles/valid.json" in e for e in errors),
                             f"valid profile must not report errors, got: {errors}")
            self.assertFalse(any("tasks/examples/good/task.json" in e for e in errors),
                             f"valid task must not report errors, got: {errors}")


if __name__ == "__main__":
    unittest.main()
