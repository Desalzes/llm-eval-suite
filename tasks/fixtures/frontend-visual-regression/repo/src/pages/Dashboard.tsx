import { FilterBar } from "../components/FilterBar";
import "../components/FilterBar.css";

const summaryTiles = [
  { label: "Open tickets", value: "128" },
  { label: "SLA risk", value: "14" },
  { label: "Resolved today", value: "37" }
];

export function Dashboard() {
  return (
    <main className="dashboard-shell">
      <header className="dashboard-header">
        <p className="dashboard-kicker">Support Operations</p>
        <h1 className="dashboard-title">Team Dashboard</h1>
      </header>

      <section
        className="filter-bar-visual-frame"
        data-testid="filter-bar-visual-frame"
        aria-label="Dashboard filter controls"
      >
        <FilterBar />
      </section>

      <section className="dashboard-summary" aria-label="Dashboard summary">
        {summaryTiles.map((tile) => (
          <article className="summary-tile" key={tile.label}>
            <p className="summary-label">{tile.label}</p>
            <p className="summary-value">{tile.value}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
