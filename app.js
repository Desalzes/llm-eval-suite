// Data is generated from the real corpus by generate_atlas_data.py and loaded
// via atlas-data.js (window.ATLAS_DATA) before this script runs. Regenerate with:
//   python generate_atlas_data.py
const ATLAS = window.ATLAS_DATA || {};
const summary = ATLAS.summary || {
  fixtureCount: 0, testFileCount: 0, evalSetCount: 0, schemaCount: 0,
  profileCount: 0, standardsCount: 0, contextPackCount: 0
};
const categories = ATLAS.categories || ["All"];
const palette = ATLAS.palette || {};
const evalSets = ATLAS.evalSets || [];
const fixtures = ATLAS.fixtures || [];

let activeCategory = "All";
let activeFixtureId = fixtures.length ? fixtures[0].id : null;
let activeEvalSet = evalSets.length ? evalSets[0].id : null;

const byId = (id) => document.getElementById(id);

function renderMetrics() {
  const metrics = [
    ["Fixtures", summary.fixtureCount],
    ["Python Tests", summary.testFileCount],
    ["Eval Sets", summary.evalSetCount],
    ["Schemas", summary.schemaCount]
  ];
  byId("metric-strip").innerHTML = metrics.map(([label, value]) => `
    <article class="metric">
      <span class="section-label">${label}</span>
      <strong>${value}</strong>
    </article>
  `).join("");
}

function renderReference() {
  const ref = byId("reference-list");
  if (!ref) return;
  const items = [
    ["Profiles", summary.profileCount],
    ["Schemas", summary.schemaCount],
    ["Standards", summary.standardsCount],
    ["Context Packs", summary.contextPackCount]
  ];
  ref.innerHTML = items
    .filter(([, value]) => value !== undefined)
    .map(([label, value]) => `<span>${label} <strong>${value}</strong></span>`)
    .join("");
}

function renderEvalSets() {
  byId("eval-list").innerHTML = evalSets.map((set) => `
    <button class="eval-item ${set.id === activeEvalSet ? "is-active" : ""}" data-eval="${set.id}">
      <span>${set.name}</span>
      <strong>${set.tasks}</strong>
    </button>
  `).join("");
  document.querySelectorAll("[data-eval]").forEach((button) => {
    button.addEventListener("click", () => {
      activeEvalSet = button.dataset.eval;
      renderEvalSets();
    });
  });
}

function filteredFixtures() {
  const term = byId("search").value.trim().toLowerCase();
  return fixtures.filter((fixture) => {
    const matchesCategory = activeCategory === "All" || fixture.category === activeCategory;
    const haystack = `${fixture.id} ${fixture.title} ${fixture.summary} ${fixture.category} ${fixture.command}`.toLowerCase();
    return matchesCategory && (!term || haystack.includes(term));
  });
}

function renderCategoryTabs() {
  byId("category-tabs").innerHTML = categories.map((category) => `
    <button class="category-tab ${category === activeCategory ? "is-active" : ""}" data-category="${category}">
      ${category}
    </button>
  `).join("");
  document.querySelectorAll("[data-category]").forEach((button) => {
    button.addEventListener("click", () => {
      activeCategory = button.dataset.category;
      renderAll();
    });
  });
}

function renderCategoryBars(items) {
  const counts = categories.slice(1).map((category) => ({
    category,
    count: items.filter((fixture) => fixture.category === category).length
  })).filter((item) => item.count > 0);
  const max = Math.max(1, ...counts.map((item) => item.count));
  byId("category-bars").innerHTML = counts.map((item) => `
    <div class="bar-row">
      <span>${item.category}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${(item.count / max) * 100}%; background:${palette[item.category]}"></div></div>
      <strong>${item.count}</strong>
    </div>
  `).join("");
  byId("visible-count").textContent = `${items.length} visible`;
}

function renderRiskMap(items) {
  byId("risk-map").innerHTML = items.map((fixture) => {
    const intensity = Math.min(0.92, 0.28 + fixture.unsafe / 8);
    const color = `rgba(217, 91, 69, ${intensity})`;
    return `<div class="risk-cell" title="${fixture.title}" style="background:${color}"></div>`;
  }).join("");
}

function cardText(value, length = 96) {
  return value.length > length ? `${value.slice(0, length - 1)}...` : value;
}

function renderFixtureGrid(items) {
  byId("fixture-grid").innerHTML = items.map((fixture) => `
    <button class="fixture-card ${fixture.id === activeFixtureId ? "is-active" : ""}" data-fixture="${fixture.id}">
      <div class="card-top">
        <span class="fixture-meta">${fixture.category}</span>
        <span class="category-dot" style="background:${palette[fixture.category]}"></span>
      </div>
      <h3>${fixture.title}</h3>
      <p>${cardText(fixture.summary)}</p>
      <div class="mini-stats">
        <span>${fixture.criteria} criteria</span>
        <span>${fixture.unsafe} boundaries</span>
      </div>
    </button>
  `).join("");
  document.querySelectorAll("[data-fixture]").forEach((button) => {
    button.addEventListener("click", () => {
      activeFixtureId = button.dataset.fixture;
      renderAll();
    });
  });
}

function renderDetail() {
  const fixture = fixtures.find((item) => item.id === activeFixtureId) || filteredFixtures()[0] || fixtures[0];
  if (!fixture) {
    byId("detail-panel").innerHTML = '<p class="detail-empty">No fixtures match.</p>';
    return;
  }
  activeFixtureId = fixture.id;
  byId("detail-panel").innerHTML = `
    <span class="detail-chip" style="background:${palette[fixture.category]}">${fixture.category}</span>
    <h2>${fixture.title}</h2>
    <p>${fixture.summary}</p>
    <div class="detail-block">
      <div class="detail-label">Fixture ID</div>
      <code>${fixture.id}</code>
    </div>
    <div class="detail-block">
      <div class="detail-label">Test Command</div>
      <code>${fixture.command}</code>
    </div>
    <div class="detail-block">
      <div class="detail-label">Allowed Paths</div>
      <code>${fixture.allowed}</code>
    </div>
    <div class="detail-block">
      <div class="detail-label">Contract Shape</div>
      <code>${fixture.criteria} success criteria / ${fixture.unsafe} unsafe-change boundaries</code>
    </div>
  `;
}

function renderAll() {
  const items = filteredFixtures();
  if (!items.some((fixture) => fixture.id === activeFixtureId) && items[0]) {
    activeFixtureId = items[0].id;
  }
  renderCategoryTabs();
  renderCategoryBars(items);
  renderRiskMap(items);
  renderFixtureGrid(items);
  renderDetail();
}

renderMetrics();
renderReference();
renderEvalSets();
renderAll();
byId("search").addEventListener("input", renderAll);
