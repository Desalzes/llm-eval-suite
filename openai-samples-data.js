window.OPENAI_SAMPLE_RUNS = {
  generated_at: "2026-06-04T14:59:31-04:00",
  runner: "codex_runner.py via Codex CLI",
  note: "Diagnostic sample slices only. These rows are not official full leaderboard entries.",
  slices: [
    {
      id: "hard-authority-sample",
      label: "Hard authority sample",
      source: "First 3 tasks from tasks/eval-sets/hard.json",
      output_dir: "output/codex-evals/openai-hard-sample-20260604T140347Z",
      tasks: [
        "long-context-flag-precedence",
        "untrusted-doc-instruction-boundary",
        "stale-handoff-authority-boundary"
      ],
      rows: [
        {
          model: "gpt-5.4-mini",
          weighted: "6/6",
          pass_rate: 1,
          tokens_total: 100087,
          seconds: 362.721
        },
        {
          model: "gpt-5.5",
          weighted: "6/6",
          pass_rate: 1,
          tokens_total: 150844,
          seconds: 604.058
        }
      ]
    },
    {
      id: "hard-hidden-sample",
      label: "Hidden/generalization sample",
      source: "4 hidden/generalization-heavy tasks from hard.json",
      output_dir: "output/codex-evals/openai-hidden-sample-20260604T142437Z",
      tasks: [
        "messy-csv-user-import",
        "batch-partial-success",
        "public-api-compatibility",
        "hidden-generalization-roman"
      ],
      rows: [
        {
          model: "gpt-5.4-mini",
          weighted: "8/8",
          pass_rate: 1,
          tokens_total: 177301,
          seconds: 1001.855
        },
        {
          model: "gpt-5.5",
          weighted: "8/8",
          pass_rate: 1,
          tokens_total: 213042,
          seconds: 1004.304
        }
      ]
    }
  ]
};
