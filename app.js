/* ============================================================================
   app.js — LLM Eval Suite · Coding-Agent Scorecard
   ----------------------------------------------------------------------------
   Plain, dependency-free front-end. Simple hash routing wires four sections:
       #home              the front door + quickstart
       #setups            gallery of "setups" (the skills/instructions you give your AI)
       #setups/<id>       one setup, with a read-only file browser
       #challenges        searchable grid of challenges
       #challenges/<id>   one challenge's plain-English contract
       #leaderboard       ranked results, linked back to the setup that produced them

   ALL displayed content comes from three globals (generated from disk by Python):
       window.ATLAS_DATA        challenge corpus + summary + category palette
       window.LEADERBOARD_DATA  ranked results
       window.SETUPS_DATA       setups (instructions + skills + files)
   In production these are regenerated from disk by Python; we only READ them.
   If a global is missing we render a graceful empty state instead of crashing.

   The app is READ-ONLY. Anywhere a user would "create" something, we instead
   show the exact terminal command to run, with a copy button.
   ========================================================================== */

(function () {
  "use strict";

  /* -------------------------------------------------------- tiny utilities */

  // Escape text so user/data content can't inject HTML.
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  // Read a global safely; return fallback if absent.
  function data(name, fallback) {
    return (typeof window[name] !== "undefined" && window[name]) ? window[name] : fallback;
  }

  const $  = (sel, root) => (root || document).querySelector(sel);
  const app = () => document.getElementById("app");

  // Format a token count like 255,850.
  function fmtInt(n) {
    if (n == null) return "—";
    return Number(n).toLocaleString("en-US");
  }

  /* ----------------------------------------------------------------- icons
     Inline SVGs so the app needs no icon font or network. */
  const I = {
    copy: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
    check: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
    shield: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>',
    file: '<svg class="ficon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>',
    folder: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2z"/></svg>',
    chevron: '<svg class="sr-chev" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>',
    arrow: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>',
    search: '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>',
    info: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
    alert: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    close: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    play: '<svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="6 4 20 12 6 20 6 4"/></svg>'
  };

  /* ---------------------------------------------------- shared components */

  // A dark terminal command block with a copy button.
  // `cmd` is the text copied; `display` (optional) is the rendered HTML.
  function cmdBlock(cmd, opts) {
    opts = opts || {};
    const light = opts.light ? " light" : "";
    const shown = opts.display || (opts.prompt === false ? esc(cmd) : '<span class="prompt">$ </span>' + esc(cmd));
    return `<div class="cmd${light}">
      <code>${shown}</code>
      <button class="copy" data-copy="${esc(cmd)}">${I.copy}<span class="copy-text">Copy</span></button>
    </div>`;
  }

  // Render a category pill (filled with its palette color).
  function catPill(cat) {
    const pal = (data("ATLAS_DATA", {}).palette) || {};
    const color = pal[cat] || "var(--ink-3)";
    return `<span class="cat-pill" style="background:${color}">${esc(cat)}</span>`;
  }

  // A setup badge ("example" / "yours" / "baseline").
  function setupBadge(b) {
    const label = { example: "example", yours: "yours", baseline: "baseline" }[b] || b;
    return `<span class="badge ${esc(b)}"><span class="dot"></span>${esc(label)}</span>`;
  }

  // Very light markdown renderer for the file viewer (headings, lists, code,
  // and YAML frontmatter). Intentionally minimal — content is trusted-ish but
  // we still escape everything first.
  function renderMarkdown(src) {
    if (!src) return '<p style="color:var(--ink-3)">This file is empty.</p>';
    let text = src;
    let fm = "";
    // Pull off YAML frontmatter (--- ... ---) and show it as a styled block.
    const m = text.match(/^---\n([\s\S]*?)\n---\n?/);
    if (m) { fm = m[1]; text = text.slice(m[0].length); }

    const lines = text.split("\n");
    let html = "", listType = null;
    function closeList() { if (listType) { html += `</${listType}>`; listType = null; } }
    const inline = (s) => esc(s).replace(/`([^`]+)`/g, "<code>$1</code>");

    for (const raw of lines) {
      const line = raw.replace(/\s+$/, "");
      if (/^#\s+/.test(line))      { closeList(); html += `<h1>${inline(line.replace(/^#\s+/, ""))}</h1>`; }
      else if (/^##\s+/.test(line)){ closeList(); html += `<h2>${inline(line.replace(/^##\s+/, ""))}</h2>`; }
      else if (/^\s*[-*]\s+/.test(line)) { if (listType !== "ul") { closeList(); html += "<ul>"; listType = "ul"; } html += `<li>${inline(line.replace(/^\s*[-*]\s+/, ""))}</li>`; }
      else if (/^\s*\d+\.\s+/.test(line)){ if (listType !== "ol") { closeList(); html += "<ol>"; listType = "ol"; } html += `<li>${inline(line.replace(/^\s*\d+\.\s+/, ""))}</li>`; }
      else if (line.trim() === "")  { closeList(); }
      else                          { closeList(); html += `<p>${inline(line)}</p>`; }
    }
    closeList();
    const fmHtml = fm ? `<div class="frontmatter">${esc(fm)}</div>` : "";
    return `<div class="md">${fmHtml}${html}</div>`;
  }

  function emptyState(title, sub) {
    return `<div class="empty"><div class="e-title">${esc(title)}</div><div class="e-sub">${esc(sub || "")}</div></div>`;
  }

  /* ============================================================  HOME  ==== */

  function viewHome() {
    const atlas = data("ATLAS_DATA", null);
    const sum = (atlas && atlas.summary) || { fixtureCount: 0, evalSetCount: 0, weightedPoints: 0 };

    const prepareCmd = "python run.py prepare tasks/examples/python-cli-bugfix/task.json";
    const scoreCmd   = "python run.py score  tasks/examples/python-cli-bugfix/task.json --workspace <workspace-from-prepare>";
    const codexCmd   = "python codex_runner.py --model <model> --eval-set tasks/eval-sets/core.json";

    return `<div class="view">

      <section class="hero">
        <h1>Is your AI coding assistant any good?</h1>
        <p class="lede">A friendly community benchmark that measures how well your AI assistant fixes
          real code — and shows you how to make it better. No coding required to read the results.</p>
        <div class="hero-actions">
          <a class="btn primary" href="#challenges">${I.play} Browse the challenges</a>
          <a class="btn" href="#leaderboard">See the leaderboard</a>
        </div>
      </section>

      <!-- The 3-step loop -->
      <section class="loop">
        <div class="grid cols-3">
          <div class="panel step">
            <span class="num">1</span>
            <h3>Pick or build a <span class="kw">setup</span></h3>
            <p>A setup is the skills and instructions you hand your AI before it starts — its playbook.
               Start from an example or make your own.</p>
            <a class="btn ghost small" href="#setups">Explore setups →</a>
          </div>
          <div class="panel step">
            <span class="num">2</span>
            <h3>Point it at a <span class="kw">challenge</span></h3>
            <p>A challenge is a small, real coding task with hidden tests. Let your AI read it and do the work
               inside the files it's allowed to touch.</p>
            <a class="btn ghost small" href="#challenges">Browse challenges →</a>
          </div>
          <div class="panel step">
            <span class="num">3</span>
            <h3><span class="kw">Score</span> the result</h3>
            <p>One command grades the work: did the tests pass, and did it stay inside the lines?
               You get a clear pass / fail / unsafe verdict.</p>
            <a class="btn ghost small" href="#leaderboard">See results →</a>
          </div>
        </div>
      </section>

      <!-- 2-minute quickstart -->
      <section class="quickstart">
        <div class="panel qs-card">
          <h2>The 2-minute quickstart <span class="min">· copy, paste, run</span></h2>
          <div class="qs-steps">
            <div class="qs-step">
              <div class="qs-label"><b>1. Prepare a workspace</b> — sets up a copy of the broken code for your AI to work in.</div>
              ${cmdBlock(prepareCmd)}
            </div>
            <div class="qs-step">
              <div class="qs-label"><b>2. Score what your AI did</b> — runs the hidden tests and checks it stayed in the allowed files.</div>
              ${cmdBlock(scoreCmd)}
            </div>
          </div>
          <div class="qs-alt">
            <span class="qs-alt-label">Running an OpenAI model on a ChatGPT / Codex subscription? Skip steps 1–2 — this driver
              prepares, runs, and scores every challenge for you, then writes a summary you can submit:</span>
            ${cmdBlock(codexCmd)}
          </div>
        </div>
      </section>

      <!-- What the score means -->
      <section class="meaning">
        <div class="section-head" style="margin-bottom:14px">
          <h2 style="font-size:22px">What the score means</h2>
          <p class="lede" style="font-size:15px">Every run lands in one of three buckets. Two are about correctness; one is about trust.</p>
        </div>
        <div class="m-grid">
          <div class="panel m-card passed">
            <div class="m-title"><span class="sw"></span>Passed</div>
            <p>The hidden tests pass <b>and</b> the AI only changed the files it was allowed to. This is the goal.</p>
          </div>
          <div class="panel m-card failed">
            <div class="m-title"><span class="sw"></span>Failed</div>
            <p>The tests still fail. The work isn't done — but nothing out of bounds was touched.</p>
          </div>
          <div class="panel m-card unsafe">
            <div class="m-title"><span class="sw"></span>Unsafe</div>
            <p>It changed files it wasn't allowed to. <span class="worst">The worst outcome</span> — even if tests pass.</p>
          </div>
        </div>
        <div class="metric-rule">
          <span class="ic">${I.info}</span>
          <span>The headline metric is the <b>weighted pass-rate</b> — harder challenges count for more.
            Hard rule: <b>any unsafe change disqualifies a clean ranking</b>, so a fast-but-reckless agent can never top a careful one.</span>
        </div>
      </section>

      <section style="margin-top:34px">
        <div class="grid cols-3">
          <div class="panel" style="padding:18px 20px"><div class="fact-k" style="font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink-3);font-weight:650">Challenges</div><div style="font-size:26px;font-weight:700;margin-top:4px">${esc(sum.fixtureCount)}</div></div>
          <div class="panel" style="padding:18px 20px"><div class="fact-k" style="font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink-3);font-weight:650">Eval sets</div><div style="font-size:26px;font-weight:700;margin-top:4px">${esc(sum.evalSetCount)}</div></div>
          <div class="panel" style="padding:18px 20px"><div class="fact-k" style="font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink-3);font-weight:650">Weighted points</div><div style="font-size:26px;font-weight:700;margin-top:4px">${esc(sum.weightedPoints)}</div></div>
        </div>
      </section>

    </div>`;
  }

  /* ==========================================================  SETUPS  ==== */

  function viewSetups() {
    const sd = data("SETUPS_DATA", null);
    if (!sd || !Array.isArray(sd.setups) || !sd.setups.length) {
      return `<div class="view">${setupsHead()}${emptyState("No setups found", "Once setups are generated from disk, they'll appear here. Try: python run.py setup new <name>")}</div>`;
    }

    const cards = sd.setups.map(function (s) {
      const skillCount = (s.skills || []).length;
      const agentLine = s.model
        ? `${esc(s.agent)} · <span class="mono">${esc(s.model)}</span>`
        : esc(s.agent || "—");
      return `<a class="panel setup-card" href="#setups/${esc(s.id)}">
        <div class="sc-top">
          <h3>${esc(s.name)}</h3>
          <div class="badges-row">${(s.badges || []).map(setupBadge).join("")}</div>
        </div>
        <p class="sc-desc">${esc(s.description)}</p>
        <div class="sc-meta">
          <span class="agent-line">${agentLine}</span>
          <span style="flex:1"></span>
          <span class="chip">${skillCount} skill${skillCount === 1 ? "" : "s"}</span>
        </div>
      </a>`;
    }).join("");

    return `<div class="view">
      ${setupsHead()}
      <div class="grid cols-3">
        ${cards}
        <button class="panel setup-card new" data-new-setup>
          <span class="plus">+</span>
          <strong>New setup</strong>
          <span>Build your own playbook</span>
        </button>
      </div>
    </div>`;
  }

  function setupsHead() {
    return `<div class="section-head">
      <div class="eyebrow">The centerpiece</div>
      <h1>Setups</h1>
      <p class="lede">A setup is everything you give your AI before it starts: its instructions and a set of
        reusable skills. Swapping setups is how you turn a so-so agent into a great one — and the leaderboard
        shows exactly which setup produced each score.</p>
    </div>`;
  }

  /* ----------------------------------------------- setup detail + browser */

  function findSetup(id) {
    const sd = data("SETUPS_DATA", null);
    if (!sd || !Array.isArray(sd.setups)) return null;
    return sd.setups.find((s) => s.id === id) || null;
  }

  function viewSetupDetail(id) {
    const s = findSetup(id);
    if (!s) return `<div class="view"><a class="backlink" href="#setups">${I.arrow} All setups</a>${emptyState("Setup not found", "We couldn't find a setup with that id.")}</div>`;

    const agentLine = s.model
      ? `${esc(s.agent)} <span class="mono">· ${esc(s.model)}</span>`
      : esc(s.agent || "—");

    // Skills list (each row expands to its SKILL.md content).
    const skillsHtml = (s.skills && s.skills.length)
      ? s.skills.map(function (sk, i) {
          return `<div class="skill-row" data-skill="${i}">
            <button class="sr-head" data-skill-toggle="${i}">
              ${I.chevron}
              <span class="sr-name">${esc(sk.name)}</span>
              <span class="sr-purpose">${esc(sk.purpose)}</span>
            </button>
            <div class="sr-body"><pre>${esc(sk.content || "")}</pre></div>
          </div>`;
        }).join("")
      : `<p style="color:var(--ink-3);font-size:13.5px">This setup ships no skills — it measures the raw agent.</p>`;

    // Build the file tree from s.files (read-only browser).
    const files = s.files || [];
    const treeHtml = buildTree(files);

    return `<div class="view" id="setup-detail" data-setup="${esc(s.id)}">
      <a class="backlink" href="#setups">${I.arrow} All setups</a>

      <div class="panel detail-header">
        <div class="dh-top">
          <div>
            <h1>${esc(s.name)}</h1>
            <p class="dh-desc">${esc(s.description)}</p>
          </div>
          <div class="badges-row">${(s.badges || []).map(setupBadge).join("")}</div>
        </div>
        <div class="dh-facts">
          <div class="fact"><div class="fact-k">Built for</div><div class="fact-v">${agentLine}</div></div>
          <div class="fact"><div class="fact-k">Skills</div><div class="fact-v">${(s.skills || []).length}</div></div>
          <div class="fact"><div class="fact-k">Context pack</div><div class="fact-v">${s.contextPack ? '<span class="mono">' + esc(s.contextPack) + '</span>' : '<span style="color:var(--ink-3)">none</span>'}</div></div>
          <div class="fact"><div class="fact-k">Leaderboard</div><div class="fact-v"><a class="usedin-link" href="#leaderboard?setup=${esc(s.id)}">Used in ${esc(s.usedInRuns || 0)} run${s.usedInRuns === 1 ? "" : "s"} →</a></div></div>
        </div>
      </div>

      <div class="grid cols-2" style="align-items:start;grid-template-columns:1fr;gap:18px">

        <!-- File browser: tree + reading pane -->
        <div class="panel browser">
          <div class="tree" id="file-tree">
            <div class="tree-title">Setup files</div>
            ${treeHtml || '<div style="color:var(--ink-3);font-size:13px;padding:8px">No files.</div>'}
          </div>
          <div class="viewer" id="file-viewer"><!-- filled on select --></div>
        </div>

        <!-- Skills -->
        <div class="panel" style="padding:20px">
          <div class="skills-block" style="margin-top:0">
            <div class="sb-title">Skills <span style="color:var(--ink-3);font-weight:500">— reusable instructions the agent can lean on</span></div>
            ${skillsHtml}
          </div>
        </div>
      </div>
    </div>`;
  }

  // Build a small file tree. Files with paths like skills/<name>/SKILL.md are
  // grouped under folder headers; top-level files render flat.
  function buildTree(files) {
    const top = [];
    const folders = {}; // folderName -> [files]
    files.forEach(function (f, idx) {
      const parts = f.path.split("/");
      if (parts.length === 1) {
        top.push({ f, idx });
      } else {
        const folder = parts.slice(0, -1).join("/");
        (folders[folder] = folders[folder] || []).push({ f, idx, leaf: parts[parts.length - 1] });
      }
    });

    let html = top.map(({ f, idx }) =>
      `<button class="tree-item" data-file="${idx}">${I.file}<span>${esc(f.path)}</span></button>`
    ).join("");

    Object.keys(folders).forEach(function (folder) {
      html += `<div class="tree-folder">${I.folder}<span>${esc(folder)}/</span></div>`;
      html += folders[folder].map(({ idx, leaf }) =>
        `<button class="tree-item indent" data-file="${idx}">${I.file}<span>${esc(leaf)}</span></button>`
      ).join("");
    });
    return html;
  }

  // Render the reading pane for a given file index of the active setup.
  function showFile(setupId, idx) {
    const s = findSetup(setupId);
    if (!s) return;
    const f = (s.files || [])[idx];
    const viewer = document.getElementById("file-viewer");
    if (!f || !viewer) return;

    // Highlight the active tree row.
    document.querySelectorAll("#file-tree .tree-item").forEach((el) =>
      el.classList.toggle("active", el.getAttribute("data-file") === String(idx)));

    const body = (f.kind === "markdown")
      ? renderMarkdown(f.content)
      : `<pre>${esc(f.content || "")}</pre>`;

    viewer.innerHTML = `
      <div class="v-head">
        <span class="v-path">${esc(f.path)}</span>
        <span class="v-kind">${esc(f.kind || "text")}</span>
      </div>
      <div class="v-body">${body}</div>`;
  }

  /* ======================================================  CHALLENGES  ==== */

  // Module-level filter state for the challenges grid.
  let challengeFilter = { cat: "All", q: "" };

  function viewChallenges() {
    const atlas = data("ATLAS_DATA", null);
    if (!atlas || !Array.isArray(atlas.fixtures) || !atlas.fixtures.length) {
      return `<div class="view">${challengesHead()}${emptyState("No challenges found", "Challenges are generated from the task corpus on disk.")}</div>`;
    }
    const cats = atlas.categories || ["All"];
    const pal = atlas.palette || {};

    const filterBtns = cats.map(function (c) {
      const active = c === challengeFilter.cat;
      const dot = c === "All" ? "" : `<span class="cat-dot" style="background:${pal[c] || "var(--ink-3)"}"></span>`;
      const style = active && c !== "All" ? `style="background:${pal[c]}"` : "";
      return `<button class="${active ? "active" : ""}" data-cat="${esc(c)}" ${style}>${dot}${esc(c)}</button>`;
    }).join("");

    return `<div class="view">
      ${challengesHead()}
      <div class="filters">
        <div class="search-box">${I.search}<input id="challenge-search" type="text" placeholder="Search challenges…" value="${esc(challengeFilter.q)}" /></div>
      </div>
      <div class="cat-filters" id="cat-filters">${filterBtns}</div>
      <div class="challenge-list" id="challenge-grid">${challengeCards()}</div>
    </div>`;
  }

  function challengesHead() {
    const atlas = data("ATLAS_DATA", {});
    const n = (atlas.fixtures || []).length;
    return `<div class="section-head">
      <div class="eyebrow">The corpus</div>
      <h1>Challenges</h1>
      <p class="lede">${n} small, real coding tasks. Each one has hidden <b>success checks</b> (what must be true)
        and <b>unsafe-change guards</b> (what must never be touched). Pick one and point your AI at it.</p>
    </div>`;
  }

  // Render just the cards (re-run on search/filter without a full re-route).
  function challengeCards() {
    const atlas = data("ATLAS_DATA", {});
    const q = challengeFilter.q.trim().toLowerCase();
    const list = (atlas.fixtures || []).filter(function (fx) {
      if (challengeFilter.cat !== "All" && fx.category !== challengeFilter.cat) return false;
      if (!q) return true;
      return (fx.title + " " + fx.summary + " " + fx.category).toLowerCase().includes(q);
    });

    if (!list.length) return emptyState("No matching challenges", "Try a different search or category.");

    return list.map(function (fx) {
      return `<a class="panel challenge-row" href="#challenges/${esc(fx.id)}">
        <span class="cr-cat">${catPill(fx.category)}</span>
        <div class="cr-main">
          <h3>${esc(fx.title)}</h3>
          <p class="cr-sum">${esc(fx.summary)}</p>
        </div>
        <div class="cr-chips">
          <span class="chip">${esc(fx.criteria)} success check${fx.criteria === 1 ? "" : "s"}</span>
          <span class="chip">${esc(fx.unsafe)} unsafe guard${fx.unsafe === 1 ? "" : "s"}</span>
        </div>
        <span class="cr-arrow"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg></span>
      </a>`;
    }).join("");
  }

  function viewChallengeDetail(id) {
    const atlas = data("ATLAS_DATA", {});
    const fx = (atlas.fixtures || []).find((f) => f.id === id);
    if (!fx) return `<div class="view"><a class="backlink" href="#challenges">${I.arrow} All challenges</a>${emptyState("Challenge not found", "")}</div>`;

    const allowed = Array.isArray(fx.allowed) ? fx.allowed : [fx.allowed].filter(Boolean);
    const checks = fx.checks || [];
    const guards = fx.guards || [];

    return `<div class="view">
      <a class="backlink" href="#challenges">${I.arrow} All challenges</a>

      <div class="panel detail-header">
        <div class="dh-top">
          <div>
            <div style="margin-bottom:10px">${catPill(fx.category)}</div>
            <h1>${esc(fx.title)}</h1>
            <p class="dh-desc">${esc(fx.description || fx.summary)}</p>
          </div>
        </div>
        <div class="dh-facts">
          <div class="fact"><div class="fact-k">Success checks</div><div class="fact-v">${esc(fx.criteria)}</div></div>
          <div class="fact"><div class="fact-k">Unsafe guards</div><div class="fact-v">${esc(fx.unsafe)}</div></div>
        </div>
      </div>

      <div class="cd-grid">
        <div class="panel cd-section">
          <h3>Run the tests</h3>
          ${cmdBlock(fx.command)}
        </div>

        <div class="grid cols-2" style="grid-template-columns:1fr 1fr;gap:16px;align-items:start">
          <div class="panel cd-section">
            <h3>Files the AI may edit</h3>
            <div class="allowed-paths">
              ${allowed.map((p) => `<div class="path"><span class="ic">${I.file}</span>${esc(p)}</div>`).join("")}
            </div>
            <p style="font-size:12.5px;color:var(--ink-3);margin-top:12px">Editing anything else counts as an <b style="color:var(--unsafe)">unsafe change</b>.</p>
          </div>

          <div class="panel cd-section">
            <h3>What "done" looks like</h3>
            <ul class="list-checks checks">
              ${checks.map((c) => `<li><span class="ic">${I.check}</span>${esc(c)}</li>`).join("")}
            </ul>
          </div>
        </div>

        <div class="panel cd-section">
          <h3>Guards — must never happen</h3>
          <ul class="list-checks guards">
            ${guards.map((g) => `<li><span class="ic">${I.shield}</span>${esc(g)}</li>`).join("")}
          </ul>
        </div>

        <div class="panel cd-section">
          <h3>How it's scored</h3>
          <div class="contract">
            <div class="co passed"><div class="co-k">Passed</div><div class="co-v">All checks pass and only allowed files changed.</div></div>
            <div class="co failed"><div class="co-k">Failed</div><div class="co-v">Tests still fail. Allowed files only — just not done yet.</div></div>
            <div class="co unsafe"><div class="co-k">Unsafe</div><div class="co-v">A guarded file was changed. Disqualifying, even if tests pass.</div></div>
          </div>
        </div>
      </div>
    </div>`;
  }

  /* =====================================================  LEADERBOARD  ==== */

  function gradeClassFor(label) {
    switch (label) {
      case "Clean pass": return "g-clean";
      case "Useful pass": return "g-useful";
      case "Needs work": return "g-needs";
      case "Unsafe": return "g-unsafe";
      case "Incomplete": return "g-incomplete";
      default: return "g-none";
    }
  }

  function renderOpenAISamples() {
    const samples = data("OPENAI_SAMPLE_RUNS", null);
    if (!samples || !Array.isArray(samples.slices) || !samples.slices.length) return "";

    const cards = samples.slices.map(function (slice) {
      const taskList = (slice.tasks || []).map(function (task) {
        return `<span class="diag-task">${esc(task)}</span>`;
      }).join("");
      const rows = (slice.rows || []).map(function (row) {
        const pct = Math.round((row.pass_rate || 0) * 100);
        return `<tr>
          <td>
            <div class="agent-cell">
              <div class="a-label">${esc(row.model)}</div>
              <div class="a-model">OpenAI via Codex CLI</div>
            </div>
          </td>
          <td class="num"><div class="passrate"><span class="bar"><i style="width:${pct}%"></i></span><span class="pct">${pct}%</span></div></td>
          <td class="num diag-weight">${esc(row.weighted || "")}</td>
          <td class="num tokens-cell">${fmtInt(row.tokens_total)}</td>
          <td class="num tokens-cell">${Math.round(Number(row.seconds || 0)).toLocaleString("en-US")}s</td>
        </tr>`;
      }).join("");
      return `<article class="diag-card">
        <div class="diag-card-head">
          <div>
            <div class="diag-kicker">OpenAI sample</div>
            <h2>${esc(slice.label)}</h2>
          </div>
          <span class="grade-badge g-clean">All passed</span>
        </div>
        <div class="diag-source">${esc(slice.source)}</div>
        <div class="diag-table-wrap">
          <table class="diag-table">
            <thead>
              <tr>
                <th>Model</th>
                <th class="num">Pass-rate</th>
                <th class="num">Weighted</th>
                <th class="num">Tokens</th>
                <th class="num">Time</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
        <div class="diag-tasks">${taskList}</div>
      </article>`;
    }).join("");

    return `<section class="diag-samples" aria-label="OpenAI diagnostic samples">
      <div class="diag-head">
        <div>
          <div class="eyebrow">Diagnostics</div>
          <h2>OpenAI model sample runs</h2>
        </div>
        <span class="diag-runner">${esc(samples.runner || "codex_runner.py")}</span>
      </div>
      <div class="lb-caveat">
        <span class="ic">${I.info}</span>
        <span>${esc(samples.note || "Sample rows are not official leaderboard entries.")}</span>
      </div>
      <div class="diag-grid">${cards}</div>
    </section>`;
  }

  function viewLeaderboard(setupFilter) {
    const lb = data("LEADERBOARD_DATA", null);
    if (!lb || !Array.isArray(lb.entries) || !lb.entries.length) {
      return `<div class="view">${leaderboardHead()}${emptyState("No results yet", "Score a run to put the first entry on the board.")}</div>`;
    }

    let entries = lb.entries.slice();

    // Optional filter by setup (used by the "Used in N runs" link).
    const activeSetup = setupFilter ? findSetup(setupFilter) : null;
    if (setupFilter) entries = entries.filter((e) => e.setup_id === setupFilter);

    // Sort: clean rows (unsafe === 0) first, then by pass-rate desc.
    // Any row with unsafe > 0 sinks below all clean rows regardless of rate.
    entries.sort(function (a, b) {
      const aFlag = (a.unsafe || 0) > 0 ? 1 : 0;
      const bFlag = (b.unsafe || 0) > 0 ? 1 : 0;
      if (aFlag !== bFlag) return aFlag - bFlag;
      return (b.weighted_pass_rate || 0) - (a.weighted_pass_rate || 0);
    });

    const rows = entries.map(function (e, i) {
      const displayRank = i + 1;
      const flagged = (e.unsafe || 0) > 0;
      const pct = Math.round((e.weighted_pass_rate || 0) * 100);
      const setup = findSetup(e.setup_id);
      // Link only when the setup actually exists; show a known-but-missing id as
      // muted text, and an absent id as a plain dash (never a link to nowhere).
      const setupCell = setup
        ? `<a class="setup-link" href="#setups/${esc(setup.id)}">${esc(setup.name)}</a>`
        : (e.setup_id ? `<span class="setup-link" style="color:var(--ink-2);font-weight:550">${esc(e.setup_id)}</span>` : `<span class="dash">—</span>`);
      const sr = e.metrics_self_reported ? '<span class="sr-flag" title="Self-reported, not scorer-computed">self-reported</span>' : "";

      const unsafeCell = flagged
        ? `<span class="flag-pill">${I.alert} ${esc(e.unsafe)} unsafe</span>`
        : `<span class="unsafe-cell zero">0</span>`;

      const gradeLabel = e.grade_label || "—";
      const gradeScore = (e.grade_score != null) ? `<span class="grade-score">${e.grade_score}</span>` : "";
      const gTags = Array.isArray(e.top_failure_tags) ? e.top_failure_tags : [];
      const gradeTags = (gradeLabel !== "Clean pass" && gTags.length)
        ? `<div class="grade-tags">${gTags.map((t) => `<span class="ftag">${esc(t.tag)}${t.count > 1 ? " &times;" + t.count : ""}</span>`).join("")}</div>`
        : "";
      const gradeCell = `<div class="grade-cell"><span class="grade-badge ${gradeClassFor(gradeLabel)}">${esc(gradeLabel)}</span>${gradeScore}</div>${gradeTags}`;

      return `<tr class="${flagged ? "flagged" : ""}">
        <td>
          <div class="rank-cell"><span class="rank-num ${displayRank === 1 && !flagged ? "top" : ""}">${displayRank}</span></div>
        </td>
        <td>
          <div class="agent-cell">
            <div class="a-label">${esc(e.agent_label)}</div>
            <div class="a-model">${e.model ? esc(e.model) : "no model"}</div>
          </div>
        </td>
        <td class="num">
          <div class="passrate"><span class="bar"><i style="width:${pct}%"></i></span><span class="pct">${pct}%</span></div>
        </td>
        <td>${gradeCell}</td>
        <td>${unsafeCell}</td>
        <td class="num tokens-cell">${fmtInt(e.tokens_total)}${sr}</td>
        <td>${setupCell}</td>
      </tr>`;
    }).join("");

    const filterNote = activeSetup
      ? `<div class="lb-caveat" style="background:var(--accent-soft);border-color:var(--accent-line);color:var(--accent-ink)">
           <span class="ic" style="color:var(--accent)">${I.info}</span>
           <span>Showing runs that used the <b>${esc(activeSetup.name)}</b> setup. <a href="#leaderboard">Show all results</a>.</span>
         </div>`
      : "";

    return `<div class="view">
      ${leaderboardHead()}
      ${filterNote}
      <div class="lb-caveat">
        <span class="ic">${I.info}</span>
        <span><b>Correctness is scorer-computed</b> (we ran the tests). Tokens, time, and cost may be
          <b>self-reported</b> by whoever submitted the run — look for the badge.</span>
      </div>
      <div class="panel" style="padding:6px 4px">
        <div class="lb-table-wrap">
          <table class="lb">
            <thead>
              <tr>
                <th style="width:64px">Rank</th>
                <th>Agent</th>
                <th class="num">Weighted pass-rate</th>
                <th>Grade</th>
                <th>Unsafe</th>
                <th class="num">Tokens</th>
                <th>Setup</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      </div>
      ${setupFilter ? "" : renderOpenAISamples()}
    </div>`;
  }

  function leaderboardHead() {
    return `<div class="section-head">
      <div class="eyebrow">Results</div>
      <h1>Leaderboard</h1>
      <p class="lede">Ranked by weighted pass-rate. Any run that made an <b>unsafe change</b> is flagged and
        sorted below every clean run — no matter how many tests it passed. When a run declares a
        <a href="#setups">setup</a>, its score links straight back to it.</p>
    </div>`;
  }

  /* ============================================================  MODAL  === */

  function openNewSetupModal() {
    const modal = document.getElementById("modal");
    const overlay = document.getElementById("modal-overlay");
    const cmd = "python run.py setup new <name>";
    modal.innerHTML = `
      <div class="m-head">
        <h2>Create a new setup</h2>
        <button class="m-close" data-close-modal aria-label="Close">${I.close}</button>
      </div>
      <div class="m-body">
        <p>This viewer is read-only — it never writes files. To make a new setup, run this in your project
           folder and it will scaffold one for you:</p>
        ${cmdBlock(cmd, { light: true })}
        <div class="m-label">It creates this folder layout:</div>
        <div class="tree-preview">
setups/&lt;name&gt;/<br>
├─ <span class="fname">setup.json</span>      <span class="note"># which agent, model, skills</span><br>
├─ <span class="fname">CLAUDE.md</span>       <span class="note"># your instructions to the AI</span><br>
└─ <span class="fname">skills/</span>         <span class="note"># reusable skill files (optional)</span>
        </div>
        <div class="m-foot">Then edit those files in your editor and <b>refresh this page</b> — your new setup will appear in the gallery.</div>
      </div>`;
    overlay.classList.add("open");
  }

  function closeModal() {
    document.getElementById("modal-overlay").classList.remove("open");
  }

  /* ============================================================  ROUTER  == */

  // Parse the hash into { route, id, query }.
  function parseHash() {
    let h = (location.hash || "#home").replace(/^#/, "");
    let query = {};
    const qi = h.indexOf("?");
    if (qi >= 0) {
      h.slice(qi + 1).split("&").forEach(function (kv) {
        const [k, v] = kv.split("=");
        if (k) query[decodeURIComponent(k)] = decodeURIComponent(v || "");
      });
      h = h.slice(0, qi);
    }
    const parts = h.split("/").filter(Boolean);
    return { route: parts[0] || "home", id: parts[1] || null, query };
  }

  function setActiveNav(route) {
    document.querySelectorAll("#nav-links a").forEach(function (a) {
      a.classList.toggle("active", a.getAttribute("data-route") === route);
    });
  }

  function render() {
    const { route, id, query } = parseHash();
    const root = app();
    let html;

    switch (route) {
      case "home":        html = viewHome(); break;
      case "setups":      html = id ? viewSetupDetail(id) : viewSetups(); break;
      case "challenges":  html = id ? viewChallengeDetail(id) : viewChallenges(); break;
      case "leaderboard": html = viewLeaderboard(query.setup || null); break;
      default:            html = viewHome();
    }

    root.innerHTML = html;
    setActiveNav(route === "setups" || route === "challenges" || route === "leaderboard" || route === "home" ? route : "home");
    window.scrollTo({ top: 0, behavior: "auto" });

    // After rendering a setup detail, auto-open the first file in the browser.
    if (route === "setups" && id) {
      const s = findSetup(id);
      if (s && (s.files || []).length) showFile(id, 0);
    }
  }

  /* ===================================================  EVENT WIRING  ===== */

  // One delegated click handler for the whole app keeps things simple.
  document.addEventListener("click", function (ev) {
    const t = ev.target;

    // Copy buttons (on any command block).
    const copyBtn = t.closest("[data-copy]");
    if (copyBtn) {
      const text = copyBtn.getAttribute("data-copy");
      const label = copyBtn.querySelector(".copy-text");
      const done = function () {
        copyBtn.classList.add("copied");
        if (label) label.textContent = "Copied!";
        setTimeout(function () { copyBtn.classList.remove("copied"); if (label) label.textContent = "Copy"; }, 1400);
      };
      // navigator.clipboard works on https/localhost; fall back for file://.
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text); done(); });
      } else { fallbackCopy(text); done(); }
      return;
    }

    // Open "new setup" modal.
    if (t.closest("[data-new-setup]")) { openNewSetupModal(); return; }

    // Close modal (button or clicking the dim overlay).
    if (t.closest("[data-close-modal]") || t.id === "modal-overlay") { closeModal(); return; }

    // Expand/collapse a skill row.
    const skillToggle = t.closest("[data-skill-toggle]");
    if (skillToggle) {
      const row = skillToggle.closest(".skill-row");
      if (row) row.classList.toggle("open");
      return;
    }

    // Select a file in the setup file browser.
    const fileBtn = t.closest("[data-file]");
    if (fileBtn) {
      const detail = document.getElementById("setup-detail");
      if (detail) showFile(detail.getAttribute("data-setup"), Number(fileBtn.getAttribute("data-file")));
      return;
    }

    // Challenge category filter.
    const catBtn = t.closest("#cat-filters [data-cat]");
    if (catBtn) {
      challengeFilter.cat = catBtn.getAttribute("data-cat");
      refreshChallenges();
      return;
    }
  });

  // Live search for challenges (input event, no re-route).
  document.addEventListener("input", function (ev) {
    if (ev.target && ev.target.id === "challenge-search") {
      challengeFilter.q = ev.target.value;
      const grid = document.getElementById("challenge-grid");
      if (grid) grid.innerHTML = challengeCards();
    }
  });

  // Re-render the challenges view (filters + grid) while keeping focus sane.
  function refreshChallenges() {
    app().innerHTML = viewChallenges();
    const input = document.getElementById("challenge-search");
    if (input && challengeFilter.q) {
      input.focus();
      input.setSelectionRange(input.value.length, input.value.length);
    }
  }

  // Close modal on Escape.
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") closeModal();
  });

  // Fallback clipboard copy for file:// where navigator.clipboard is blocked.
  function fallbackCopy(text) {
    try {
      const ta = document.createElement("textarea");
      ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    } catch (e) { /* no-op: copy simply won't work in this context */ }
  }

  /* ============================================================  BOOT  ==== */

  window.addEventListener("hashchange", render);
  window.addEventListener("DOMContentLoaded", render);
  // If DOMContentLoaded already fired (script at end of body), render now.
  if (document.readyState !== "loading") render();

})();
