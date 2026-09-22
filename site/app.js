// Fill in your GitHub "owner/repo" so the footer link and the one-click
// "suggest a fix" links point at the right place.
const GITHUB_REPO = "lord-r3-core-cfp";

const state = {
  conferences: [],
  search: "",
  ranks: new Set(["A*", "A", "B"]),
  hideUnknown: false,
  sortBy: "deadline",
};

const els = {};

function rankClass(rank) {
  return rank === "A*" ? "rank-Astar" : `rank-${rank}`;
}

function daysUntil(isoDate) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = new Date(isoDate);
  return Math.round((target - today) / 86400000);
}

function formatDeadline(entry) {
  if (!entry.deadline) {
    return { dateLabel: "unbekannt", countdownLabel: "", countdownClass: "" };
  }
  const days = daysUntil(entry.deadline);
  const dateLabel = new Date(entry.deadline).toLocaleDateString("de-DE", {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
  let countdownLabel;
  let countdownClass = "";
  if (days < 0) {
    countdownLabel = `vor ${Math.abs(days)} Tagen abgelaufen`;
    countdownClass = "passed";
  } else if (days === 0) {
    countdownLabel = "heute!";
    countdownClass = "due-soon";
  } else {
    countdownLabel = `in ${days} Tag${days === 1 ? "" : "en"}`;
    if (days <= 14) countdownClass = "due-soon";
  }
  return { dateLabel, countdownLabel, countdownClass };
}

function statusBadge(entry) {
  if (entry.status === "verified") return `<span class="badge status-verified">verifiziert</span>`;
  if (entry.status === "community") {
    return `<span class="badge status-community" title="Quelle: ${entry.source || "community"}">community (${entry.source || "?"})</span>`;
  }
  return `<span class="badge status-unknown">keine Deadline bekannt</span>`;
}

function suggestFixUrl(entry) {
  const filename = `${entry.acronym.toLowerCase()}.yml`;
  const template = [
    `acronym: ${entry.acronym}`,
    `deadline: "YYYY-MM-DD"`,
    `timezone: "AoE"`,
    `cfp_url: ""`,
    `verified_by: "your-github-username"`,
    "",
  ].join("\n");
  const params = new URLSearchParams({ filename, value: template });
  return `https://github.com/${GITHUB_REPO}/new/main/data/overrides?${params.toString()}`;
}

function renderCard(entry) {
  const { dateLabel, countdownLabel, countdownClass } = formatDeadline(entry);
  const forChips = (entry.field_of_research || [])
    .map((f) => `<span class="for-chip" title="${f.name}">${f.code}</span>`)
    .join(" ");
  const cfpLink = entry.cfp_url
    ? `<a class="cfp-link" href="${entry.cfp_url}" target="_blank" rel="noopener">CFP-Seite →</a>`
    : `<a class="cfp-link" href="${suggestFixUrl(entry)}" target="_blank" rel="noopener">Deadline hinzufügen →</a>`;
  const eventInfo = [entry.event_date, entry.place].filter(Boolean).join(" · ");
  const note = entry.notes ? `<div class="conf-note">${entry.notes}</div>` : "";

  return `
    <li class="conf-card">
      <div class="conf-main">
        <div class="conf-title-row">
          <span class="conf-acronym">${entry.acronym}</span>
          <span class="badge ${rankClass(entry.rank)}">${entry.rank}</span>
          <span class="conf-title">${entry.title}</span>
        </div>
        <div class="conf-meta">
          ${statusBadge(entry)}
          ${forChips}
          ${cfpLink}
          ${eventInfo ? `<span class="conf-event">${eventInfo}</span>` : ""}
        </div>
        ${note}
      </div>
      <div class="conf-deadline">
        <span class="deadline-date">${dateLabel}</span>
        <span class="deadline-countdown ${countdownClass}">${countdownLabel}</span>
      </div>
    </li>`;
}

const RANK_ORDER = { "A*": 0, A: 1, B: 2 };

function applyFilters() {
  const q = state.search.trim().toLowerCase();
  let items = state.conferences.filter((e) => state.ranks.has(e.rank));
  if (q) {
    items = items.filter(
      (e) => e.acronym.toLowerCase().includes(q) || e.title.toLowerCase().includes(q)
    );
  }
  if (state.hideUnknown) {
    items = items.filter((e) => e.deadline);
  }

  items = [...items];
  if (state.sortBy === "deadline") {
    items.sort((a, b) => {
      if (!a.deadline && !b.deadline) return a.acronym.localeCompare(b.acronym);
      if (!a.deadline) return 1;
      if (!b.deadline) return -1;
      return a.deadline.localeCompare(b.deadline);
    });
  } else if (state.sortBy === "rank") {
    items.sort((a, b) => RANK_ORDER[a.rank] - RANK_ORDER[b.rank] || a.acronym.localeCompare(b.acronym));
  } else {
    items.sort((a, b) => a.acronym.localeCompare(b.acronym));
  }
  return items;
}

function render() {
  const items = applyFilters();
  els.list.innerHTML = items.map(renderCard).join("");
  els.emptyState.hidden = items.length > 0;
  els.resultCount.textContent = `${items.length} von ${state.conferences.length} Konferenzen`;
}

async function init() {
  els.list = document.getElementById("conference-list");
  els.emptyState = document.getElementById("empty-state");
  els.resultCount = document.getElementById("result-count");
  els.search = document.getElementById("search");
  els.hideUnknown = document.getElementById("hide-unknown");
  els.sortBy = document.getElementById("sort-by");
  els.generatedAt = document.getElementById("generated-at");
  els.repoLink = document.getElementById("repo-link");
  els.contributeLink = document.getElementById("contribute-link");

  if (GITHUB_REPO !== "OWNER/REPO") {
    els.repoLink.href = `https://github.com/${GITHUB_REPO}`;
    els.contributeLink.href = `https://github.com/${GITHUB_REPO}/blob/main/CONTRIBUTING.md`;
  }

  els.search.addEventListener("input", (e) => {
    state.search = e.target.value;
    render();
  });
  document.querySelectorAll(".rank-toggle").forEach((cb) => {
    cb.addEventListener("change", () => {
      if (cb.checked) state.ranks.add(cb.value);
      else state.ranks.delete(cb.value);
      render();
    });
  });
  els.hideUnknown.addEventListener("change", (e) => {
    state.hideUnknown = e.target.checked;
    render();
  });
  els.sortBy.addEventListener("change", (e) => {
    state.sortBy = e.target.value;
    render();
  });

  try {
    const res = await fetch("data/conferences.json", { cache: "no-cache" });
    const data = await res.json();
    state.conferences = data.conferences;
    els.generatedAt.textContent = new Date(data.generated_at).toLocaleString("de-DE");
  } catch (err) {
    els.emptyState.hidden = false;
    els.emptyState.textContent = "Daten konnten nicht geladen werden.";
    console.error(err);
  }
  render();
}

init();
