// Fill in your GitHub "owner/repo" so the footer link and the one-click
// "suggest a fix" links point at the right place.
const GITHUB_REPO = "lord-r3/core-cfp";

const state = {
  conferences: [],
  search: "",
  ranks: new Set(["A*", "A", "B"]),
  forCode: "",
  region: "",
  format: "",
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
    return { dateLabel: "unknown", countdownLabel: "", countdownClass: "" };
  }
  const days = daysUntil(entry.deadline);
  const dateLabel = new Date(entry.deadline).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
  let countdownLabel;
  let countdownClass = "";
  if (days < 0) {
    countdownLabel = `${Math.abs(days)} day${days === -1 ? "" : "s"} overdue`;
    countdownClass = "passed";
  } else if (days === 0) {
    countdownLabel = "due today!";
    countdownClass = "due-soon";
  } else {
    countdownLabel = `in ${days} day${days === 1 ? "" : "s"}`;
    if (days <= 14) countdownClass = "due-soon";
  }
  return { dateLabel, countdownLabel, countdownClass };
}

function statusBadge(entry) {
  if (entry.status === "verified") return `<span class="badge status-verified">verified</span>`;
  if (entry.status === "community") {
    return `<span class="badge status-community" title="Source: ${entry.source || "community"}">community (${entry.source || "?"})</span>`;
  }
  return `<span class="badge status-unknown">no known deadline</span>`;
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

function acceptanceRateLine(entry) {
  const rates = entry.acceptance_rates || [];
  if (rates.length === 0) return "";
  const latest = rates[0];
  const history = rates.map((r) => `${r.year}: ${r.rate}%`).join(", ");
  return `<span class="accept-rate" title="Acceptance rate history (source: emeryberger/csconferences) - ${history}">Acceptance ${latest.rate}% (${latest.year})</span>`;
}

// --- iCal (.ics) export ---

function escapeIcsText(text) {
  return String(text)
    .replace(/\\/g, "\\\\")
    .replace(/;/g, "\\;")
    .replace(/,/g, "\\,")
    .replace(/\r?\n/g, "\\n");
}

function icsDate(isoDate, offsetDays = 0) {
  const d = new Date(`${isoDate}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + offsetDays);
  return d.toISOString().slice(0, 10).replace(/-/g, "");
}

// ponytail: no RFC5545 75-char line folding - real ceiling: a very long DESCRIPTION
// could upset a strict parser; every mainstream calendar app tolerates it in practice.
function buildIcsEvent(entry) {
  const description = [entry.title, entry.notes, entry.cfp_url].filter(Boolean).join(" - ");
  return [
    "BEGIN:VEVENT",
    `UID:${entry.id}-${entry.deadline}@core-cfp`,
    `DTSTAMP:${new Date().toISOString().replace(/[-:]/g, "").split(".")[0]}Z`,
    `DTSTART;VALUE=DATE:${icsDate(entry.deadline)}`,
    `DTEND;VALUE=DATE:${icsDate(entry.deadline, 1)}`,
    `SUMMARY:${escapeIcsText(`${entry.acronym} CFP deadline`)}`,
    `DESCRIPTION:${escapeIcsText(description)}`,
    entry.cfp_url ? `URL:${entry.cfp_url}` : null,
    "END:VEVENT",
  ]
    .filter(Boolean)
    .join("\r\n");
}

function buildIcs(entries) {
  const events = entries.filter((e) => e.deadline).map(buildIcsEvent);
  return ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//core-cfp//deadlines//EN", "CALSCALE:GREGORIAN", ...events, "END:VCALENDAR"].join(
    "\r\n"
  );
}

function downloadIcs(filename, text) {
  const blob = new Blob([text], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function renderCard(entry) {
  const { dateLabel, countdownLabel, countdownClass } = formatDeadline(entry);
  const forChips = (entry.field_of_research || [])
    .map((f) => `<span class="for-chip" title="${f.name}">${f.code}</span>`)
    .join(" ");
  const cfpLink = entry.cfp_url
    ? `<a class="cfp-link" href="${entry.cfp_url}" target="_blank" rel="noopener">CFP page →</a>`
    : `<a class="cfp-link" href="${suggestFixUrl(entry)}" target="_blank" rel="noopener">Add a deadline →</a>`;
  const dblpLink = entry.dblp_url
    ? `<a class="cfp-link" href="${entry.dblp_url}" target="_blank" rel="noopener">DBLP ↗</a>`
    : "";
  const icsButton = entry.deadline
    ? `<button type="button" class="ics-link" data-ics-id="${entry.id}">Add to calendar</button>`
    : "";
  const formatLabel = entry.format ? entry.format[0].toUpperCase() + entry.format.slice(1) : null;
  const eventInfo = [entry.event_date, entry.place, formatLabel].filter(Boolean).join(" · ");
  const note = entry.notes ? `<div class="conf-note">${entry.notes}</div>` : "";
  const acceptRate = acceptanceRateLine(entry);

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
          ${dblpLink}
          ${icsButton}
          ${eventInfo ? `<span class="conf-event">${eventInfo}</span>` : ""}
          ${acceptRate}
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
  if (state.forCode) {
    items = items.filter((e) => (e.field_of_research || []).some((f) => f.code === state.forCode));
  }
  if (state.region) {
    items = items.filter((e) => e.region === state.region);
  }
  if (state.format) {
    items = items.filter((e) => e.format === state.format);
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

function populateOptions(selectEl, values) {
  for (const [value, label] of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    selectEl.appendChild(option);
  }
}

function populateFilterOptions(conferences) {
  const forCodes = new Map();
  const regions = new Set();
  for (const entry of conferences) {
    for (const f of entry.field_of_research || []) forCodes.set(f.code, f.name);
    if (entry.region) regions.add(entry.region);
  }
  const forOptions = [...forCodes.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([code, name]) => [code, `${code} – ${name}`]);
  populateOptions(els.forFilter, forOptions);

  const regionOptions = [...regions].sort().map((r) => [r, r]);
  populateOptions(els.regionFilter, regionOptions);
}

function render() {
  const items = applyFilters();
  els.list.innerHTML = items.map(renderCard).join("");
  els.emptyState.hidden = items.length > 0;
  els.resultCount.textContent = `${items.length} of ${state.conferences.length} conferences`;
}

// --- share links: reflect filter state in the URL, and restore it on load ---

function syncUrlToState() {
  const params = new URLSearchParams();
  if (state.search) params.set("q", state.search);
  if (state.ranks.size !== 3) params.set("ranks", [...state.ranks].join(","));
  if (state.forCode) params.set("for", state.forCode);
  if (state.region) params.set("region", state.region);
  if (state.format) params.set("format", state.format);
  if (state.hideUnknown) params.set("known", "1");
  if (state.sortBy !== "deadline") params.set("sort", state.sortBy);
  const qs = params.toString();
  history.replaceState(null, "", qs ? `?${qs}` : location.pathname);
}

function restoreStateFromUrl() {
  const params = new URLSearchParams(location.search);
  if (params.has("q")) state.search = params.get("q");
  if (params.has("ranks")) state.ranks = new Set(params.get("ranks").split(",").filter(Boolean));
  if (params.has("for")) state.forCode = params.get("for");
  if (params.has("region")) state.region = params.get("region");
  if (params.has("format")) state.format = params.get("format");
  if (params.has("known")) state.hideUnknown = true;
  if (params.has("sort")) state.sortBy = params.get("sort");
}

function onFilterChange() {
  syncUrlToState();
  render();
}

async function init() {
  els.list = document.getElementById("conference-list");
  els.emptyState = document.getElementById("empty-state");
  els.resultCount = document.getElementById("result-count");
  els.search = document.getElementById("search");
  els.forFilter = document.getElementById("for-filter");
  els.regionFilter = document.getElementById("region-filter");
  els.formatFilter = document.getElementById("format-filter");
  els.hideUnknown = document.getElementById("hide-unknown");
  els.sortBy = document.getElementById("sort-by");
  els.generatedAt = document.getElementById("generated-at");
  els.repoLink = document.getElementById("repo-link");
  els.contributeLink = document.getElementById("contribute-link");
  els.copyLink = document.getElementById("copy-link");
  els.exportIcs = document.getElementById("export-ics");

  if (GITHUB_REPO !== "OWNER/REPO") {
    els.repoLink.href = `https://github.com/${GITHUB_REPO}`;
    els.contributeLink.href = `https://github.com/${GITHUB_REPO}/blob/main/CONTRIBUTING.md`;
  }

  restoreStateFromUrl();
  els.search.value = state.search;
  document.querySelectorAll(".rank-toggle").forEach((cb) => {
    cb.checked = state.ranks.has(cb.value);
  });
  els.formatFilter.value = state.format;
  els.hideUnknown.checked = state.hideUnknown;
  els.sortBy.value = state.sortBy;

  els.search.addEventListener("input", (e) => {
    state.search = e.target.value;
    onFilterChange();
  });
  document.querySelectorAll(".rank-toggle").forEach((cb) => {
    cb.addEventListener("change", () => {
      if (cb.checked) state.ranks.add(cb.value);
      else state.ranks.delete(cb.value);
      onFilterChange();
    });
  });
  els.forFilter.addEventListener("change", (e) => {
    state.forCode = e.target.value;
    onFilterChange();
  });
  els.regionFilter.addEventListener("change", (e) => {
    state.region = e.target.value;
    onFilterChange();
  });
  els.formatFilter.addEventListener("change", (e) => {
    state.format = e.target.value;
    onFilterChange();
  });
  els.hideUnknown.addEventListener("change", (e) => {
    state.hideUnknown = e.target.checked;
    onFilterChange();
  });
  els.sortBy.addEventListener("change", (e) => {
    state.sortBy = e.target.value;
    onFilterChange();
  });

  els.copyLink.addEventListener("click", async () => {
    const original = els.copyLink.textContent;
    try {
      await navigator.clipboard.writeText(location.href);
      els.copyLink.textContent = "Copied!";
    } catch (err) {
      console.error(err);
      els.copyLink.textContent = "Copy failed - copy manually";
    }
    setTimeout(() => (els.copyLink.textContent = original), 1500);
  });
  els.exportIcs.addEventListener("click", () => {
    downloadIcs("core-cfp-selection.ics", buildIcs(applyFilters()));
  });
  els.list.addEventListener("click", (e) => {
    const button = e.target.closest("[data-ics-id]");
    if (!button) return;
    const entry = state.conferences.find((c) => String(c.id) === button.dataset.icsId);
    if (entry) downloadIcs(`${entry.acronym}.ics`, buildIcs([entry]));
  });

  try {
    const res = await fetch("data/conferences.json", { cache: "no-cache" });
    const data = await res.json();
    state.conferences = data.conferences;
    els.generatedAt.textContent = new Date(data.generated_at).toLocaleString("en-US");
    populateFilterOptions(state.conferences);
    els.forFilter.value = state.forCode;
    els.regionFilter.value = state.region;
  } catch (err) {
    els.emptyState.hidden = false;
    els.emptyState.textContent = "Could not load conference data.";
    console.error(err);
  }
  render();
}

init();
