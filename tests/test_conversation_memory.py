import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ConversationMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="conversation-memory-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_append_memory_writes_jsonl_and_recall_prefers_query_match(self) -> None:
        from suite.conversation_memory import append_memory, recall_memory

        append_memory(
            self.temp_dir,
            summary="Discussed Polymarket accounting reconciliation and dashboard PnL attribution.",
            topics=["accounting", "polymarket"],
            source="assistant",
        )
        append_memory(
            self.temp_dir,
            summary="Discussed sprite animation workflow for the game project.",
            topics=["game", "sprites"],
            source="assistant",
        )

        memory_path = self.temp_dir / "local" / "conversation-memory" / "turns.jsonl"
        self.assertTrue(memory_path.exists())
        rows = [json.loads(line) for line in memory_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["schema_version"], "conversation_memory_v1")

        recalled = recall_memory(self.temp_dir, query="accounting", limit=5)

        self.assertEqual(recalled["status"], "present")
        self.assertEqual(recalled["entries"][0]["topics"], ["accounting", "polymarket"])
        self.assertIn("dashboard PnL", recalled["entries"][0]["summary"])

    def test_recall_missing_memory_returns_empty_result(self) -> None:
        from suite.conversation_memory import recall_memory

        recalled = recall_memory(self.temp_dir, query="accounting")

        self.assertEqual(recalled["status"], "missing")
        self.assertEqual(recalled["entries"], [])

    def test_memory_cli_append_and_recall_markdown(self) -> None:
        append_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "memory",
                "append",
                "--repo-root",
                str(self.temp_dir),
                "--summary",
                "Captured the Amadeus memory design approval.",
                "--topic",
                "amadeus",
                "--topic",
                "memory",
                "--source",
                "assistant",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )
        self.assertEqual(append_result.returncode, 0, append_result.stderr + append_result.stdout)
        self.assertEqual(json.loads(append_result.stdout)["entry"]["topics"], ["amadeus", "memory"])

        recall_result = subprocess.run(
            [
                sys.executable,
                "-m",
                "suite.cli",
                "memory",
                "recall",
                "--repo-root",
                str(self.temp_dir),
                "--query",
                "memory",
                "--format",
                "markdown",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )
        self.assertEqual(recall_result.returncode, 0, recall_result.stderr + recall_result.stdout)
        self.assertIn("Captured the Amadeus memory design approval.", recall_result.stdout)
        self.assertIn("topics: amadeus, memory", recall_result.stdout)


if __name__ == "__main__":
    unittest.main()
