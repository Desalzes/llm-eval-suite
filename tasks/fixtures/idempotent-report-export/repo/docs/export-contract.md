# Daily Export Contract

The command exports a Markdown report and `manifest.json` for one report date.

Rules:

- The CLI is `python -m reports.daily_export --orders orders.csv --out output --date YYYY-MM-DD`.
- The report file is named `daily-report-YYYY-MM-DD.md`.
- Running the same command twice should leave identical output.
- Running the same date with new input should replace that date's report and manifest entry.
- Manifest entries for other dates must be preserved.
