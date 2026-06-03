const statusOptions = ["Open", "In Review", "Resolved"];

export function FilterBar() {
  const activeStatus = "In Review";

  return (
    <form className="filter-bar" aria-label="Ticket filters">
      <div className="filter-group filter-group--search">
        <label className="filter-label" htmlFor="filter-search">
          Search
        </label>
        <input
          id="filter-search"
          className="filter-field"
          type="search"
          defaultValue="enterprise"
          aria-label="Search tickets"
        />
      </div>

      <div className="filter-group filter-group--status">
        <span className="filter-label" id="status-filter-label">
          Status
        </span>
        <div
          className="segmented-control"
          role="radiogroup"
          aria-labelledby="status-filter-label"
        >
          {statusOptions.map((status) => {
            const isActive = status === activeStatus;

            return (
              <button
                aria-checked={isActive}
                className={`filter-segment${isActive ? " is-active" : ""}`}
                key={status}
                role="radio"
                type="button"
              >
                {status}
              </button>
            );
          })}
        </div>
      </div>

      <div className="filter-group filter-group--range">
        <label className="filter-label" htmlFor="filter-range">
          Date range
        </label>
        <select
          id="filter-range"
          className="filter-field"
          defaultValue="last-30"
          aria-label="Date range"
        >
          <option value="last-7">Last 7 days</option>
          <option value="last-30">Last 30 days</option>
          <option value="quarter">This quarter</option>
        </select>
      </div>

      <button className="filter-apply" type="button">
        Apply
      </button>
    </form>
  );
}
