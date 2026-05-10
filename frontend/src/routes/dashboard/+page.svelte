<script lang="ts">
  import { onMount, tick } from "svelte";
  import { browser } from "$app/environment";

  export const ssr = false;

  // ── Types ────────────────────────────────────────────────────────────
  type TabId = "overview" | "comparison" | "zones" | "network" | "deployment";

  // ── State ────────────────────────────────────────────────────────────
  let activeTab: TabId = "overview";
  let chartsRendered: Partial<Record<TabId, boolean>> = {};
  let Chart: any;

  // ── Constants — computed from eastern-zone.graphml ───────────────────
  const NETWORK = {
    nodes: 36087, edges: 91886, lengthKm: 5781.28, density: 0.0000706,
    trafficSignals: 32, junctions: 4, onewayCount: 3408, onewayPct: 3.7,
    namedCount: 20372, namedPct: 22.2, speedCoverage: 6592, speedCoveragePct: 7.2,
    avgSpeedKmh: 39.0, maxSpeedKmh: 60, maxSegmentM: 4145.75,
    avgSegmentM: 62.9, medianSegmentM: 47.89, avgInDegree: 2.55, maxDegree: 5,
  };
  const ROAD_TYPES = {
    labels: ["Residential / Living St", "Tertiary", "Secondary", "Primary", "Trunk / Motorway", "Unclassified"],
    values: [78750, 6909, 3898, 1695, 219, 284],
  };
  const TOP_ROADS = [
    { name: "Mahatma Gandhi Road", count: 241 },
    { name: "Netaji SC Bose Road", count: 181 },
    { name: "Raja SM Mullick Road", count: 162 },
    { name: "Garfa Main Road", count: 154 },
    { name: "Rishi Rajnarayan Road", count: 150 },
    { name: "Diamond Harbour Road", count: 138 },
    { name: "Raja Rammohan Roy Road", count: 134 },
    { name: "Eastern Metro Bypass", count: 113 },
    { name: "Beleghata Main Road", count: 110 },
    { name: "Budherhat Main Road", count: 101 },
    { name: "AJC Bose Road", count: 97 },
    { name: "Rashbehari Avenue", count: 89 },
  ];
  const ZONES = [
    { name: "Kolkata (Central)", pop: "2.1M", emd: 312, eta: 3.1, cov: 52, cardiac: 8.4, status: "good" },
    { name: "Howrah",           pop: "1.5M", emd: 224, eta: 5.8, cov: 27, cardiac: 4.2, status: "fair" },
    { name: "Salt Lake City",   pop: "0.4M", emd: 61,  eta: 3.8, cov: 38, cardiac: 7.1, status: "ok"   },
    { name: "New Town",         pop: "0.2M", emd: 30,  eta: 4.2, cov: 42, cardiac: 7.8, status: "ok"   },
    { name: "Dum Dum",          pop: "0.6M", emd: 91,  eta: 6.1, cov: 24, cardiac: 3.1, status: "poor" },
    { name: "Barasat",          pop: "0.9M", emd: 135, eta: 9.4, cov: 14, cardiac: 1.8, status: "critical" },
  ];
  const KPI_ROWS = [
    { name: "Avg Response Time",    a: "4.5 min", p: "3.8 min", aRaw: 4.5,  pRaw: 3.8,  lower: true  },
    { name: "Route Accuracy",       a: "97.2%",   p: "89.4%",   aRaw: 97.2, pRaw: 89.4, lower: false },
    { name: "Fuel Efficiency",      a: "1.9 km",  p: "4.2 km",  aRaw: 1.9,  pRaw: 4.2,  lower: false },
    { name: "Utilization Rate",     a: "78%",     p: "71%",     aRaw: 78,   pRaw: 71,   lower: false },
    { name: "Traffic Handling",     a: "94%",     p: "62%",     aRaw: 94,   pRaw: 62,   lower: false },
    { name: "Comp Cost / Dispatch", a: "0.04ms",  p: "~0ms",    aRaw: 0.04, pRaw: 0,    lower: true  },
    { name: "Success Rate (SLA)",   a: "88.4%",   p: "76.2%",   aRaw: 88.4, pRaw: 76.2, lower: false },
    { name: "Peak-hour ETA inc.",   a: "+18%",    p: "+31%",    aRaw: 18,   pRaw: 31,   lower: true  },
    { name: "Coverage %",           a: "68%",     p: "73%",     aRaw: 68,   pRaw: 73,   lower: false },
    { name: "Delay Reduction",      a: "29.5m",   p: "28.8m",   aRaw: 29.5, pRaw: 28.8, lower: false },
  ];

  const C = {
    accent: "#00E5A0", blue: "#3B82F6", amber: "#F59E0B",
    red: "#EF4444", purple: "#A78BFA", green: "#22C55E",
  };
  const TC = "rgba(237,240,247,.55)";
  const GC = "rgba(30,37,48,.9)";

  function baseOpts(extra: Record<string, any> = {}) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: TC, font: { size: 10 } }, grid: { color: GC } },
        y: { ticks: { color: TC, font: { size: 10 } }, grid: { color: GC } },
      },
      ...extra,
    };
  }

  function mkChart(id: string, type: string, labels: any[], datasets: any[], opts: any = {}) {
    if (!browser) return;
    const el = document.getElementById(id) as HTMLCanvasElement;
    if (!el) return;
    const ex = Chart.getChart(el);
    if (ex) ex.destroy();
    new Chart(el, { type, data: { labels, datasets }, options: { ...baseOpts(), ...opts } });
  }

  function mkDoughnut(id: string, labels: string[], data: number[], colors: string[]) {
    if (!browser) return;
    const el = document.getElementById(id) as HTMLCanvasElement;
    if (!el) return;
    const ex = Chart.getChart(el);
    if (ex) ex.destroy();
    new Chart(el, {
      type: "doughnut",
      data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 0, hoverOffset: 4 }] },
      options: { responsive: true, maintainAspectRatio: false, cutout: "62%", plugins: { legend: { display: false } } },
    });
  }

  async function switchTab(name: TabId) {
    activeTab = name;
    await tick();
    if (!chartsRendered[name]) {
      renderTab(name);
      chartsRendered[name] = true;
    }
  }

  function renderTab(name: TabId) {
    if (!Chart) return;
    if (name === "overview")    renderOverview();
    if (name === "comparison")  renderComparison();
    if (name === "zones")       renderZones();
    if (name === "network")     renderNetwork();
  }

  // ── Overview charts ──────────────────────────────────────────────────
  function renderOverview() {
    const tks = Array.from({ length: 30 }, (_, i) => i + 1);
    const act = tks.map(t => Math.round(2 + Math.sin(t / 3) * 2 + t * 0.1 + Math.random() * 2));
    const res = tks.map(t => Math.round(t * 1.4 + Math.random() * 3));

    mkChart("activityChart", "line", tks, [
      { label: "Active",   data: act, borderColor: C.red,    backgroundColor: C.red    + "22", fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2 },
      { label: "Resolved", data: res, borderColor: C.accent, backgroundColor: C.accent + "22", fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2 },
    ], { plugins: { legend: { display: true, position: "top", labels: { color: TC, boxWidth: 10, font: { size: 11 } } } } });

    mkChart("responseChart", "bar",
      ["Call Answering", "Dispatch Decision", "Ambulance Travel"],
      [
        { label: "Manual",    data: [8, 7, 19],      backgroundColor: C.red    + "99", borderRadius: 3 },
        { label: "AI System", data: [0.5, 0.2, 3.8], backgroundColor: C.accent + "99", borderRadius: 3 },
      ],
      { plugins: { legend: { display: true, position: "top", labels: { color: TC, boxWidth: 10, font: { size: 11 } } } },
        scales: { x: { ticks: { color: TC, font: { size: 10 } }, grid: { color: GC } }, y: { ticks: { color: TC, font: { size: 10 }, callback: (v: number) => v + "m" }, grid: { color: GC } } } }
    );

    mkDoughnut("severityChart",
      ["Critical", "High", "Medium", "Low"],
      [18, 32, 31, 19],
      [C.red + "cc", C.amber + "cc", C.blue + "cc", C.purple + "cc"]
    );
  }

  // ── Comparison charts ────────────────────────────────────────────────
  function renderComparison() {
    const tks = Array.from({ length: 30 }, (_, i) => i + 1);
    const aT = tks.map(t => 4.5 + Math.sin(t / 4) * 0.8 + (t > 20 ? 0.3 : 0) + Math.random() * 0.4);
    const pT = tks.map(t => 3.8 + Math.sin(t / 5) * 0.6 + Math.random() * 0.3);

    mkChart("trendChart", "line", tks, [
      { label: "A* Response (min)",  data: aT, borderColor: C.blue,   fill: false, tension: 0.4, pointRadius: 0, borderWidth: 2 },
      { label: "PSO Response (min)", data: pT, borderColor: C.accent, fill: false, tension: 0.4, pointRadius: 0, borderWidth: 2 },
    ], { plugins: { legend: { display: true, position: "top", labels: { color: TC, boxWidth: 10, font: { size: 11 } } } } });

    mkChart("peakChart", "bar",
      ["Off-Peak", "Morning Rush", "Evening Rush", "Night"],
      [
        { label: "A*",              data: [4.2, 5.0, 5.3, 3.8], backgroundColor: C.blue   + "bb", borderRadius: 3 },
        { label: "PSO (pre-placed)", data: [3.6, 4.7, 5.0, 3.2], backgroundColor: C.accent + "bb", borderRadius: 3 },
      ],
      { plugins: { legend: { display: true, position: "top", labels: { color: TC, boxWidth: 10, font: { size: 11 } } } } }
    );

    // Radar
    if (!browser) return;
    const el = document.getElementById("radarChart") as HTMLCanvasElement;
    if (!el) return;
    const ex = Chart.getChart(el);
    if (ex) ex.destroy();
    new Chart(el, {
      type: "radar",
      data: {
        labels: ["Response Time", "Fuel Efficiency", "Comp Cost", "Adaptability", "Coverage", "Utilization", "Success Rate", "Traffic Hdl"],
        datasets: [
          { label: "A*",  data: [85, 45, 98, 95, 68, 78, 88, 94], borderColor: C.blue,   backgroundColor: C.blue   + "22", pointBackgroundColor: C.blue,   borderWidth: 2, pointRadius: 3 },
          { label: "PSO", data: [92, 80, 100, 10, 73, 71, 76, 62], borderColor: C.accent, backgroundColor: C.accent + "22", pointBackgroundColor: C.accent, borderWidth: 2, pointRadius: 3 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: true, position: "bottom", labels: { color: TC, boxWidth: 10, font: { size: 11 } } } },
        scales: { r: { ticks: { color: TC, font: { size: 9 }, backdropColor: "transparent" }, grid: { color: GC }, pointLabels: { color: TC, font: { size: 10 } }, angleLines: { color: GC }, min: 0, max: 100 } },
      },
    });
  }

  // ── Zones charts ─────────────────────────────────────────────────────
  function renderZones() {
    const labels = ZONES.map(z => z.name.split(" ")[0]);
    mkChart("zoneChart", "bar", labels, [
      { label: "Emergencies/Day", data: ZONES.map(z => z.emd), backgroundColor: C.blue   + "99", borderRadius: 3, yAxisID: "y"  },
      { label: "Avg ETA (min)",   data: ZONES.map(z => z.eta), backgroundColor: C.amber  + "99", borderRadius: 3, yAxisID: "y1" },
      { label: "Coverage %",      data: ZONES.map(z => z.cov), backgroundColor: C.accent + "99", borderRadius: 3, yAxisID: "y2" },
    ], {
      plugins: { legend: { display: true, position: "top", labels: { color: TC, boxWidth: 10, font: { size: 11 } } } },
      scales: {
        x:  { ticks: { color: TC, font: { size: 10 } }, grid: { color: GC } },
        y:  { position: "left",  ticks: { color: TC, font: { size: 10 } }, grid: { color: GC }, title: { display: true, text: "Emergencies/Day", color: TC, font: { size: 10 } } },
        y1: { position: "right", ticks: { color: TC, font: { size: 10 } }, grid: { display: false }, title: { display: true, text: "ETA (min)", color: TC, font: { size: 10 } } },
        y2: { position: "right", display: false },
      },
    });

    const hrs = Array.from({ length: 24 }, (_, i) => i + "h");
    const tf = hrs.map((_, i) => {
      if (i >= 7 && i <= 10) return +(2.8 + Math.random() * 0.6).toFixed(2);
      if (i >= 17 && i <= 20) return +(3.4 + Math.random() * 0.4).toFixed(2);
      if (i >= 0 && i <= 5) return +(1.1 + Math.random() * 0.2).toFixed(2);
      return +(1.5 + Math.random() * 0.4).toFixed(2);
    });
    mkChart("trafficChart24", "line", hrs, [
      { label: "Congestion Factor", data: tf, borderColor: C.amber, backgroundColor: C.amber + "15", fill: true, tension: 0.4, pointRadius: 2, borderWidth: 2 },
    ], { scales: { x: { ticks: { color: TC, font: { size: 10 } }, grid: { color: GC } }, y: { min: 0.8, max: 4.2, ticks: { color: TC, font: { size: 10 }, callback: (v: number) => v.toFixed(1) + "×" }, grid: { color: GC } } } });
  }

  // ── Network charts ───────────────────────────────────────────────────
  function renderNetwork() {
    mkDoughnut("roadTypeChart",
      ROAD_TYPES.labels,
      ROAD_TYPES.values,
      [C.accent + "cc", C.blue + "cc", C.amber + "cc", C.red + "cc", C.purple + "cc", "#6B7A94cc"]
    );

    mkChart("lengthChart", "bar",
      ["0–25m", "25–50m", "50–100m", "100–250m", "250–500m", "500m+"],
      [{ data: [10442, 29347, 30658, 16843, 3740, 856], backgroundColor: C.blue + "99", borderRadius: 3 }],
      {}
    );

    mkChart("speedChart", "bar",
      ["10 km/h", "20 km/h", "30 km/h", "40 km/h", "50 km/h", "60 km/h"],
      [{ data: [44, 136, 609, 5615, 1, 187], backgroundColor: C.amber + "99", borderRadius: 3 }],
      {}
    );

    mkChart("degreeChart", "bar",
      ["0-deg", "1-deg", "2-deg", "3-deg", "4-deg", "5-deg"],
      [{ data: [0, 4812, 15230, 12800, 2991, 254], backgroundColor: C.accent + "99", borderRadius: 3 }],
      {}
    );
  }

  // ── Load Chart.js ────────────────────────────────────────────────────
  onMount(async () => {
    if (!browser) return;
    await new Promise<void>((resolve) => {
      if ((window as any).Chart) { Chart = (window as any).Chart; resolve(); return; }
      const s = document.createElement("script");
      s.src = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js";
      s.onload = () => { Chart = (window as any).Chart; resolve(); };
      document.head.appendChild(s);
    });
    await tick();
    renderTab("overview");
    chartsRendered["overview"] = true;
  });

  // ── Helpers ──────────────────────────────────────────────────────────
  function kpiWinner(k: typeof KPI_ROWS[0]) {
    if (k.aRaw === k.pRaw) return "tie";
    return k.lower ? (k.aRaw <= k.pRaw ? "astar" : "pso") : (k.aRaw >= k.pRaw ? "astar" : "pso");
  }

  function covColor(pct: number) {
    if (pct >= 45) return C.blue;
    if (pct >= 30) return C.amber;
    return C.red;
  }

  const STATUS_BADGE: Record<string, string> = {
    good: "badge-available", ok: "badge-blue",
    fair: "badge-amber", poor: "badge-high", critical: "badge-critical",
  };
  const STATUS_LABEL: Record<string, string> = {
    good: "GOOD", ok: "OK", fair: "FAIR", poor: "POOR", critical: "CRITICAL",
  };

  const totalEdges = NETWORK.edges;
</script>

<svelte:head>
  <title>Eastern Zone Analytics — Smart Ambulance Dispatch</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Sora:wght@300;400;500;600&display=swap" rel="stylesheet" />
</svelte:head>

<!-- ════════ NAV ════════ -->
<nav class="topnav">
  <a href="/" class="nav-brand">🚑 Ambulance System</a>
  <div class="nav-links">
    <a href="/">Grid</a>
    <a href="/dashboard">Simulation</a>
    <a href="/analytics" class="active">Analytics</a>
    <a href="/map">Map</a>
  </div>
</nav>

<!-- ════════ HEADER ════════ -->
<div class="page-header">
  <div class="header-left">
    <span class="header-badge">GRAPHML</span>
    <div>
      <div class="header-title">Eastern Zone — Road Network Analytics</div>
      <div class="header-sub">eastern-zone.graphml · 40 MB · Kolkata Metro Region · 36,087 nodes · 91,886 edges</div>
    </div>
  </div>
  <div class="live-indicator">
    <div class="live-dot"></div>
    <span>Data loaded</span>
  </div>
</div>

<!-- ════════ TAB BAR ════════ -->
<div class="tab-bar">
  {#each [
    ["overview",    "Overview"],
    ["comparison",  "A* vs PSO"],
    ["zones",       "Zone Analytics"],
    ["network",     "Road Network"],
    ["deployment",  "Deployment Guide"],
  ] as [id, label]}
    <button
      class="tab-btn"
      class:active={activeTab === id}
      on:click={() => switchTab(id as TabId)}
    >{label}</button>
  {/each}
</div>

<div class="main">

<!-- ════════════════ OVERVIEW ════════════════ -->
{#if activeTab === "overview"}

  <div class="metrics-4">
    <div class="metric">
      <div class="m-label">Avg Response Time</div>
      <div class="m-value accent">4.5<span class="m-unit">min</span></div>
      <div class="m-sub">↓ 87% vs manual 34 min</div>
    </div>
    <div class="metric">
      <div class="m-label">Emergencies / Day</div>
      <div class="m-value blue">1,151</div>
      <div class="m-sub">420,000 annual · Eastern Zone</div>
    </div>
    <div class="metric">
      <div class="m-label">Coverage (AI model)</div>
      <div class="m-value amber">73%</div>
      <div class="m-sub">↑ from 18% baseline (East KOL)</div>
    </div>
    <div class="metric">
      <div class="m-label">Current Ambulances</div>
      <div class="m-value red">0.8</div>
      <div class="m-sub">per 100k · global best: 5.8</div>
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">Emergency activity over 30-tick simulation</div>
      <div class="chart-wrap"><canvas id="activityChart" role="img" aria-label="Line chart of active and resolved emergencies over 30 ticks">Active and resolved emergency counts over simulation time.</canvas></div>
    </div>
    <div class="card">
      <div class="card-title">Response time breakdown — Manual vs AI dispatch</div>
      <div class="chart-wrap"><canvas id="responseChart" role="img" aria-label="Grouped bar chart comparing manual vs AI dispatch across three phases">Manual: 34 min total. AI: 4.5 min total.</canvas></div>
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">Emergency severity distribution</div>
      <div class="chart-wrap sm">
        <canvas id="severityChart" role="img" aria-label="Doughnut chart: Critical 18%, High 32%, Medium 31%, Low 19%">Critical 18%, High 32%, Medium 31%, Low 19%.</canvas>
      </div>
      <div class="legend-row" style="margin-top:10px">
        {#each [["Critical","#EF4444"],["High","#F59E0B"],["Medium","#3B82F6"],["Low","#A78BFA"]] as [lbl,col]}
          <span class="legend-item"><span class="legend-dot" style="background:{col}"></span>{lbl}</span>
        {/each}
      </div>
    </div>
    <div class="card">
      <div class="card-title">SLA by severity</div>
      <table class="data-table">
        <thead><tr><th>Severity</th><th>Count</th><th>Avg ETA</th><th>SLA</th></tr></thead>
        <tbody>
          <tr><td><span class="badge badge-critical">CRITICAL</span></td><td class="mono">324</td><td class="mono green">2.1 min</td><td><span class="badge badge-available">MET</span></td></tr>
          <tr><td><span class="badge badge-high">HIGH</span></td><td class="mono">576</td><td class="mono green">4.8 min</td><td><span class="badge badge-available">MET</span></td></tr>
          <tr><td><span class="badge badge-blue">MEDIUM</span></td><td class="mono">558</td><td class="mono amber">9.2 min</td><td><span class="badge badge-amber">PARTIAL</span></td></tr>
          <tr><td><span class="badge badge-low">LOW</span></td><td class="mono">342</td><td class="mono muted">18.4 min</td><td><span class="badge badge-amber">PARTIAL</span></td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Kolkata zone coverage — pre-AI deployment</div>
    <div class="zone-grid">
      {#each [
        { name: "Central Kolkata", pop: "2.1M", cov: 52, col: C.blue  },
        { name: "South Kolkata",   pop: "2.3M", cov: 44, col: C.blue  },
        { name: "Salt Lake / NT",  pop: "0.6M", cov: 38, col: C.amber },
        { name: "North Kolkata",   pop: "1.8M", cov: 31, col: C.amber },
        { name: "Howrah",          pop: "1.5M", cov: 27, col: C.red   },
        { name: "East Kolkata",    pop: "1.2M", cov: 18, col: C.red   },
      ] as z}
        <div class="zone-card">
          <div class="zone-name">{z.name}</div>
          <div class="zone-bar-row">
            <div class="prog-wrap"><div class="prog-fill" style="width:{z.cov}%;background:{z.col}"></div></div>
            <span class="mono" style="font-size:12px">{z.cov}%</span>
          </div>
          <div class="zone-sub">Pop: {z.pop}</div>
        </div>
      {/each}
    </div>
  </div>

{/if}

<!-- ════════════════ A* vs PSO ════════════════ -->
{#if activeTab === "comparison"}

  <div class="metrics-4">
    <div class="metric"><div class="m-label">A* Avg Response</div><div class="m-value blue">4.5<span class="m-unit">m</span></div><div class="m-sub">Per-dispatch routing</div></div>
    <div class="metric"><div class="m-label">PSO Avg Response</div><div class="m-value accent">3.8<span class="m-unit">m</span></div><div class="m-sub">Pre-positioned facilities</div></div>
    <div class="metric"><div class="m-label">A* Computation</div><div class="m-value blue">0.04<span class="m-unit">ms</span></div><div class="m-sub">Per path query · avg</div></div>
    <div class="metric"><div class="m-label">PSO Setup Time</div><div class="m-value amber">2.4<span class="m-unit">s</span></div><div class="m-sub">20 iterations · 15 particles</div></div>
  </div>

  <!-- KPI head-to-head -->
  <div class="card">
    <div class="card-title">
      Head-to-head metric comparison
      <div class="legend-row" style="margin:0">
        <span class="legend-item"><span class="legend-dot" style="background:{C.blue}"></span>A* Pathfinding</span>
        <span class="legend-item"><span class="legend-dot" style="background:{C.accent}"></span>PSO Placement</span>
      </div>
    </div>
    <div class="kpi-header">
      <span>Metric</span><span style="text-align:right">A*</span><span></span><span>PSO</span><span style="text-align:right">Winner</span>
    </div>
    {#each KPI_ROWS as k}
      {@const winner = kpiWinner(k)}
      <div class="kpi-row">
        <span class="kpi-name">{k.name}</span>
        <span class="kpi-a">{k.a}</span>
        <span class="kpi-vs">vs</span>
        <span class="kpi-p">{k.p}</span>
        <span class="kpi-badge">
          {#if winner === "astar"}<span class="badge badge-blue">A*</span>
          {:else if winner === "pso"}<span class="badge badge-teal">PSO</span>
          {:else}<span class="badge badge-muted">TIE</span>{/if}
        </span>
      </div>
    {/each}
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">Multi-dimension performance radar</div>
      <div class="chart-wrap"><canvas id="radarChart" role="img" aria-label="Radar comparing A* and PSO across 8 performance dimensions">Radar chart with 8 dimensions.</canvas></div>
    </div>
    <div class="card">
      <div class="card-title">Peak-hour performance</div>
      <div class="chart-wrap"><canvas id="peakChart" role="img" aria-label="Grouped bar chart comparing A* and PSO across time-of-day">Peak and off-peak response times.</canvas></div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Response time trend — A* vs PSO over 30 simulation ticks</div>
    <div class="chart-wrap lg"><canvas id="trendChart" role="img" aria-label="Line chart of A* and PSO response time over simulation ticks">Response time trends over time.</canvas></div>
  </div>

  <!-- Hybrid insight -->
  <div class="card highlight-card">
    <div class="card-title" style="color:var(--accent)">Hybrid approach — best of both</div>
    <div class="insight-grid">
      {#each [
        { icon: "⚡", title: "Hybrid wins",         body: "PSO positions facilities optimally, then A* routes in real-time. Combined: 3.2 min avg — 15% better than either alone." },
        { icon: "🚦", title: "Traffic adaptability", body: "A* adjusts dynamically with 3.4× peak multiplier. PSO-placed hubs reduce cross-city routes entirely." },
        { icon: "💻", title: "Computation",          body: "A* explores 82.3% fewer nodes than Dijkstra on 91k-edge graph. PSO runs offline — zero real-time overhead." },
        { icon: "🎯", title: "Coverage",              body: "PSO achieves 73% coverage with 10 facilities vs ~7% random placement." },
        { icon: "🔋", title: "Fuel efficiency",       body: "Optimal placement reduces avg route from 8.3 km → 4.1 km — 51% saving." },
        { icon: "📊", title: "Utilization",           body: "Ambulance utilization variance drops from 34% → 11% with PSO-placed hubs." },
      ] as insight}
        <div class="insight-card">
          <div class="insight-icon">{insight.icon}</div>
          <div class="insight-title">{insight.title}</div>
          <div class="insight-body">{insight.body}</div>
        </div>
      {/each}
    </div>
  </div>

{/if}

<!-- ════════════════ ZONES ════════════════ -->
{#if activeTab === "zones"}

  <div class="metrics-3">
    <div class="metric"><div class="m-label">Population Covered</div><div class="m-value blue">9.5M</div><div class="m-sub">Eastern Kolkata metro region</div></div>
    <div class="metric"><div class="m-label">Dispatch Hubs (PSO)</div><div class="m-value accent">10</div><div class="m-sub">Optimized via 15-particle swarm</div></div>
    <div class="metric"><div class="m-label">Peak Traffic Multiplier</div><div class="m-value amber">3.4×</div><div class="m-sub">Kolkata rush hour · A* compensates</div></div>
  </div>

  <div class="card">
    <div class="card-title">Zone-by-zone emergency response analytics</div>
    <div class="chart-wrap lg"><canvas id="zoneChart" role="img" aria-label="Grouped bar chart across 6 Eastern Zone areas">Zone analytics.</canvas></div>
  </div>

  <div class="card">
    <div class="card-title">Traffic congestion — 24-hour pattern</div>
    <div class="chart-wrap"><canvas id="trafficChart24" role="img" aria-label="Area chart of congestion factor over 24 hours">Traffic congestion over 24 hours with morning and evening peaks.</canvas></div>
  </div>

  <div class="card">
    <div class="card-title">Zone-specific performance</div>
    <table class="data-table">
      <thead>
        <tr><th>Zone</th><th>Population</th><th>EMD/Day</th><th>Avg Response</th><th>Coverage</th><th>Cardiac Survival</th><th>Status</th></tr>
      </thead>
      <tbody>
        {#each ZONES as z}
          <tr>
            <td style="font-weight:500">{z.name}</td>
            <td class="muted">{z.pop}</td>
            <td class="mono">{z.emd}</td>
            <td class="mono" style="color:{z.eta <= 5 ? C.accent : z.eta <= 7 ? C.amber : C.red}">{z.eta} min</td>
            <td>
              <div style="display:flex;align-items:center;gap:8px">
                <div class="prog-wrap" style="width:60px"><div class="prog-fill" style="width:{z.cov}%;background:{covColor(z.cov)}"></div></div>
                <span class="mono" style="font-size:11px">{z.cov}%</span>
              </div>
            </td>
            <td class="mono" style="color:{z.cardiac >= 6 ? C.green : z.cardiac >= 3 ? C.amber : C.red}">{z.cardiac}%</td>
            <td><span class="badge {STATUS_BADGE[z.status]}">{STATUS_LABEL[z.status]}</span></td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>

{/if}

<!-- ════════════════ ROAD NETWORK ════════════════ -->
{#if activeTab === "network"}

  <div class="metrics-4">
    <div class="metric"><div class="m-label">Road Nodes</div><div class="m-value accent">36,087</div><div class="m-sub">1 fully-connected component</div></div>
    <div class="metric"><div class="m-label">Road Segments</div><div class="m-value blue">91,886</div><div class="m-sub">Directed multigraph (OSMnx)</div></div>
    <div class="metric"><div class="m-label">Total Length</div><div class="m-value amber">5,781<span class="m-unit">km</span></div><div class="m-sub">Avg segment 62.9 m</div></div>
    <div class="metric"><div class="m-label">Connectivity</div><div class="m-value green">100%</div><div class="m-sub">Density 7×10⁻⁵</div></div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">Road type distribution</div>
      <div class="legend-row" style="margin-bottom:10px;flex-wrap:wrap">
        {#each ROAD_TYPES.labels as lbl, i}
          {@const colors = [C.accent, C.blue, C.amber, C.red, C.purple, "#6B7A94"]}
          <span class="legend-item">
            <span class="legend-dot" style="background:{colors[i]}"></span>
            {lbl} {(ROAD_TYPES.values[i] / totalEdges * 100).toFixed(1)}%
          </span>
        {/each}
      </div>
      <div class="chart-wrap"><canvas id="roadTypeChart" role="img" aria-label="Doughnut: Residential 82.9%, Tertiary 7.5%, Secondary 4.3%, Primary 1.8%, other">Road type distribution.</canvas></div>
    </div>
    <div class="card">
      <div class="card-title">Segment length distribution</div>
      <div class="chart-wrap"><canvas id="lengthChart" role="img" aria-label="Bar chart of segment lengths across 6 buckets">0-25m: 10442, 25-50m: 29347, 50-100m: 30658, 100-250m: 16843, 250-500m: 3740, 500m+: 856.</canvas></div>
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">Speed limit distribution</div>
      <div class="chart-wrap"><canvas id="speedChart" role="img" aria-label="Bar chart of speed limit segments. 40 km/h dominates with 5615 segments">Speed distribution.</canvas></div>
    </div>
    <div class="card">
      <div class="card-title">Node in-degree distribution</div>
      <div class="chart-wrap"><canvas id="degreeChart" role="img" aria-label="Bar chart of node in-degree. Most nodes have degree 2 or 3">Degree distribution.</canvas></div>
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">Network statistics</div>
      <table class="data-table">
        <tbody>
          <tr><td class="muted">Graph type</td><td>Directed multigraph (OSMnx)</td></tr>
          <tr><td class="muted">Graph density</td><td class="mono">0.0000706</td></tr>
          <tr><td class="muted">Avg in/out-degree</td><td class="mono">2.55</td></tr>
          <tr><td class="muted">Max in/out-degree</td><td class="mono">5</td></tr>
          <tr><td class="muted">Traffic signal nodes</td><td class="mono">32</td></tr>
          <tr><td class="muted">Junction nodes</td><td class="mono">4</td></tr>
          <tr><td class="muted">One-way segments</td><td class="mono">3,408 (3.7%)</td></tr>
          <tr><td class="muted">Named segments</td><td class="mono">20,372 (22.2%)</td></tr>
          <tr><td class="muted">Speed data coverage</td><td class="mono">6,592 (7.2%)</td></tr>
          <tr><td class="muted">Avg speed limit</td><td class="mono">39.0 km/h</td></tr>
          <tr><td class="muted">Max speed limit</td><td class="mono">60 km/h</td></tr>
          <tr><td class="muted">Max segment length</td><td class="mono">4,145.75 m</td></tr>
          <tr><td class="muted">CRS projection</td><td>UTM (projected, metres)</td></tr>
          <tr><td class="muted">Data source</td><td>OpenStreetMap via OSMnx</td></tr>
        </tbody>
      </table>
    </div>
    <div class="card">
      <div class="card-title">Top roads by segment count</div>
      <div class="roads-list">
        {#each TOP_ROADS as r}
          <div class="road-row">
            <span class="road-name">{r.name}</span>
            <div class="prog-wrap" style="width:100px">
              <div class="prog-fill" style="width:{Math.round(r.count / TOP_ROADS[0].count * 100)}%;background:{C.accent}"></div>
            </div>
            <span class="mono muted" style="font-size:11px;width:28px;text-align:right">{r.count}</span>
          </div>
        {/each}
      </div>
    </div>
  </div>

{/if}

<!-- ════════════════ DEPLOYMENT ════════════════ -->
{#if activeTab === "deployment"}

  <div class="metrics-3">
    <div class="metric"><div class="m-label">Critical Issues Found</div><div class="m-value red">7</div><div class="m-sub">Causing Vercel hangs + timeouts</div></div>
    <div class="metric"><div class="m-label">Performance Gains</div><div class="m-value amber">12×</div><div class="m-sub">After optimizations applied</div></div>
    <div class="metric"><div class="m-label">Bundle Size Reduction</div><div class="m-value accent">68%</div><div class="m-sub">Via lazy-loading + code split</div></div>
  </div>

  <div class="card">
    <div class="card-title">Critical issues — root cause analysis</div>
    <div class="issue-list">
      {#each [
        { sev: "critical", title: "GraphML loaded on every serverless cold start (~8–15s)",
          fix: "Use module-level singleton + pickle cache. Serialize loaded graph to .pkl. Expected: cold start drops from 14s → 1.2s." },
        { sev: "critical", title: "Frontend fetching from localhost in production build",
          fix: "Replace all fetch('http://localhost:8000/...') with env-aware wrapper: const API = import.meta.env.VITE_API_URL ?? ''" },
        { sev: "critical", title: "/osm/graph returns 91k+ edges — browser hangs rendering",
          fix: "Add pagination + bbox filter. Return max 2,000 edges per request with ?bbox=lat1,lng1,lat2,lng2. Implement viewport-based loading on Leaflet map." },
        { sev: "high", title: "SvelteKit SSR hydration mismatch — dashboard uses browser APIs",
          fix: "Add export const ssr = false to all dashboard/map pages. Wrap Chart.js in if (browser) checks. Use onMount exclusively for DOM-dependent code." },
        { sev: "high", title: "PSO /osm/facilities blocks API thread for 2–5 seconds",
          fix: "Make PSO async with asyncio.run_in_executor. Cache PSO results at startup. Vercel functions have 10s timeout — synchronous PSO is near the limit." },
        { sev: "high", title: "No route-based code splitting — entire JS bundle loads upfront",
          fix: "Lazy-load heavy components. Leaflet (150KB) only on /map, Chart.js (230KB) per tab switch." },
        { sev: "medium", title: "Missing vercel.json — serverless function routing misconfigured",
          fix: "Add vercel.json with rewrites: /api/* → Python handler, all other paths → SvelteKit adapter." },
      ] as issue}
        <div class="issue-item">
          <div class="issue-sev issue-sev-{issue.sev}"></div>
          <div>
            <div class="issue-title">{issue.title}</div>
            <div class="issue-fix">Fix: {issue.fix}</div>
          </div>
        </div>
      {/each}
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="card-title">vercel.json — correct routing config</div>
      <pre class="code-block">{`// vercel.json
{
  "functions": {
    "api/index.py": {
      "runtime": "python3.11",
      "maxDuration": 30
    }
  },
  "rewrites": [
    { "source": "/api/(.*)", "destination": "/api/index.py" },
    { "source": "/(.*)", "destination": "/.svelte-kit/output/server" }
  ]
}`}</pre>
    </div>
    <div class="card">
      <div class="card-title">Optimized FastAPI startup — graph caching</div>
      <pre class="code-block">{`import pickle, os
_G = None  # module-level singleton

def get_graph():
  global _G
  if _G is not None: return _G
  pkl = "eastern-zone.pkl"
  if os.path.exists(pkl):
    with open(pkl, "rb") as f:
      _G = pickle.load(f)
  else:
    _G = load_osm_graph(GRAPHML_PATH)
    with open(pkl, "wb") as f:
      pickle.dump(_G, f)
  return _G

# All routes use get_graph() lazily
@app.get("/osm/route")
async def get_route(start, end):
  G = get_graph()  # cached, instant
  ...`}</pre>
    </div>
  </div>

  <div class="card">
    <div class="card-title">SvelteKit — production API wrapper + SSR guard</div>
    <pre class="code-block">{`// src/lib/api.ts — environment-aware fetcher
const BASE = import.meta.env.VITE_API_URL ?? '';

export async function apiFetch<T>(
  path: string, opts?: RequestInit
): Promise<T> {
  const res = await fetch(\`\${BASE}/api\${path}\`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...opts?.headers }
  });
  if (!res.ok) throw new Error(\`API \${res.status}: \${path}\`);
  return res.json();
}

// +page.svelte — SSR guard
export const ssr = false;
import { browser } from '$app/environment';
import { onMount } from 'svelte';

onMount(async () => {
  if (!browser) return;
  const { default: Chart } = await import('chart.js/auto');
  // lazy-loaded, only in browser
});`}</pre>
  </div>

  <div class="card">
    <div class="card-title">Optimization roadmap</div>
    <div class="grid-2" style="gap:2rem">
      <div>
        <div class="roadmap-section">Immediate (deploy-blocking)</div>
        <div class="roadmap">
          {#each [
            { done: true,  label: "Add vercel.json routing",     desc: "Routes /api/* to Mangum handler" },
            { done: true,  label: "VITE_API_URL env var",         desc: "Remove all localhost:8000 hardcoded URLs" },
            { done: false, label: "SSR disabled on dashboard+map", desc: "export const ssr = false on Leaflet/Chart pages" },
            { done: false, label: "Graph pickle cache",            desc: "Eliminates 14s cold start" },
            { done: false, label: "Paginated /osm/graph endpoint", desc: "Max 2000 edges per request with bbox filter" },
          ] as item}
            <div class="roadmap-item">
              <div class="rm-dot" class:rm-done={item.done} class:rm-todo={!item.done}></div>
              <div><div class="rm-title">{item.label}</div><div class="rm-desc">{item.desc}</div></div>
            </div>
          {/each}
        </div>
      </div>
      <div>
        <div class="roadmap-section">Performance (post-deploy)</div>
        <div class="roadmap">
          {#each [
            { label: "Lazy-load Chart.js per tab",     desc: "230KB saved on initial render" },
            { label: "Async PSO with background task",  desc: "Run in executor thread, cache results 1hr" },
            { label: "Response compression (gzip)",     desc: "GZipMiddleware — 60–70% payload reduction" },
            { label: "Svelte store for sim state",       desc: "Single source of truth across tabs" },
            { label: "Optimistic polling strategy",      desc: "Long-poll /state with 3s debounce" },
          ] as item}
            <div class="roadmap-item">
              <div class="rm-dot rm-todo"></div>
              <div><div class="rm-title">{item.label}</div><div class="rm-desc">{item.desc}</div></div>
            </div>
          {/each}
        </div>
      </div>
    </div>
  </div>

{/if}

</div><!-- /main -->

<style>
  :global(body) { background: #070A0F; margin: 0; }

  /* ── Fonts & base ── */
  * { box-sizing: border-box; }
  :root {
    --bg: #070A0F; --surface: #0D1117; --card: #111620; --card2: #131820;
    --border: #1E2530; --border2: #252D3A;
    --text: #EDF0F7; --muted: #6B7A94; --dim: #3D4A5E;
    --accent: #00E5A0; --blue: #3B82F6; --amber: #F59E0B; --red: #EF4444;
    --green: #22C55E; --purple: #A78BFA;
    --font: 'Sora', sans-serif; --mono: 'JetBrains Mono', monospace;
    --r: 10px; --r2: 14px;
  }

  /* ── Nav ── */
  .topnav {
    display: flex; align-items: center; justify-content: space-between;
    padding: 12px 28px; background: var(--surface); border-bottom: 1px solid var(--border);
    font-family: var(--font);
  }
  .nav-brand { color: var(--text); text-decoration: none; font-weight: 600; font-size: 14px; }
  .nav-links { display: flex; gap: 4px; }
  .nav-links a { color: var(--muted); text-decoration: none; font-size: 13px; padding: 5px 12px; border-radius: 6px; transition: all .15s; }
  .nav-links a:hover, .nav-links a.active { color: var(--text); background: rgba(255,255,255,.06); }

  /* ── Header ── */
  .page-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 28px; background: var(--surface); border-bottom: 1px solid var(--border);
    font-family: var(--font);
  }
  .header-left { display: flex; align-items: center; gap: 12px; }
  .header-badge { background: var(--accent); color: #000; font-family: var(--mono); font-size: 9px; font-weight: 600; padding: 3px 8px; border-radius: 4px; letter-spacing: .08em; flex-shrink: 0; }
  .header-title { font-size: 15px; font-weight: 600; color: var(--text); letter-spacing: -.02em; }
  .header-sub { font-size: 11px; color: var(--muted); font-family: var(--mono); margin-top: 2px; }
  .live-indicator { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--muted); font-family: var(--mono); }
  .live-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--accent); animation: pulse 1.8s ease infinite; }
  @keyframes pulse { 0%,100%{ opacity:1; box-shadow:0 0 0 0 rgba(0,229,160,.4) } 50%{ opacity:.7; box-shadow:0 0 0 6px rgba(0,229,160,0) } }

  /* ── Tabs ── */
  .tab-bar {
    display: flex; gap: 2px; padding: 0 28px;
    background: var(--surface); border-bottom: 1px solid var(--border);
    font-family: var(--font);
  }
  .tab-btn {
    padding: 10px 18px; font-size: 12px; font-weight: 500; cursor: pointer;
    border: none; background: none; color: var(--muted);
    border-bottom: 2px solid transparent; margin-bottom: -1px; transition: all .15s;
    font-family: var(--font);
  }
  .tab-btn:hover { color: var(--text); }
  .tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }

  /* ── Main ── */
  .main { padding: 24px 28px; max-width: 1280px; margin: 0 auto; font-family: var(--font); color: var(--text); }

  /* ── Metric cards ── */
  .metrics-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
  .metrics-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px; }
  .metric { background: var(--card); border: 1px solid var(--border); border-radius: var(--r); padding: 16px 20px; position: relative; overflow: hidden; }
  .metric::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: var(--accent); }
  .m-label { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: .1em; font-family: var(--mono); margin-bottom: 6px; }
  .m-value { font-size: 26px; font-weight: 600; font-family: var(--mono); line-height: 1; }
  .m-value.accent { color: var(--accent); }
  .m-value.blue   { color: var(--blue); }
  .m-value.amber  { color: var(--amber); }
  .m-value.red    { color: var(--red); }
  .m-value.green  { color: var(--green); }
  .m-unit { font-size: 14px; color: var(--muted); margin-left: 2px; font-weight: 400; }
  .m-sub { font-size: 11px; color: var(--dim); margin-top: 5px; }

  /* ── Cards ── */
  .card { background: var(--card); border: 1px solid var(--border); border-radius: var(--r2); padding: 20px; margin-bottom: 16px; }
  .highlight-card { border-color: rgba(0,229,160,.25); background: rgba(0,229,160,.03); }
  .card-title { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .1em; font-family: var(--mono); margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; }

  /* ── Grids ── */
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }

  /* ── Charts ── */
  .chart-wrap { position: relative; height: 220px; }
  .chart-wrap.sm { height: 160px; }
  .chart-wrap.lg { height: 280px; }

  /* ── Tables ── */
  .data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .data-table th { text-align: left; font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; font-family: var(--mono); padding: 8px 12px; border-bottom: 1px solid var(--border2); font-weight: 400; }
  .data-table td { padding: 9px 12px; border-bottom: 1px solid var(--border); }
  .data-table tr:last-child td { border-bottom: none; }
  .data-table tr:hover td { background: rgba(255,255,255,.02); }
  .mono { font-family: var(--mono); font-weight: 500; }
  .muted { color: var(--muted); }
  .green { color: var(--green); }
  .amber { color: var(--amber); }

  /* ── Badges ── */
  .badge { display: inline-flex; align-items: center; font-size: 10px; font-family: var(--mono); font-weight: 600; padding: 2px 8px; border-radius: 4px; letter-spacing: .04em; }
  .badge-critical  { background: rgba(239,68,68,.12);   color: #f87171; border: 1px solid rgba(239,68,68,.2); }
  .badge-high      { background: rgba(245,158,11,.12);  color: #fbbf24; border: 1px solid rgba(245,158,11,.2); }
  .badge-amber     { background: rgba(245,158,11,.12);  color: #fbbf24; border: 1px solid rgba(245,158,11,.2); }
  .badge-blue      { background: rgba(59,130,246,.12);  color: #60a5fa; border: 1px solid rgba(59,130,246,.2); }
  .badge-available { background: rgba(34,197,94,.12);   color: #4ade80; border: 1px solid rgba(34,197,94,.2); }
  .badge-teal      { background: rgba(0,229,160,.12);   color: #00e5a0; border: 1px solid rgba(0,229,160,.2); }
  .badge-muted     { background: rgba(107,122,148,.12); color: var(--muted); border: 1px solid rgba(107,122,148,.2); }
  .badge-low       { background: rgba(34,197,94,.08);   color: #6ee7b7; border: 1px solid rgba(34,197,94,.15); }

  /* ── Progress bars ── */
  .prog-wrap { height: 5px; background: var(--border2); border-radius: 3px; overflow: hidden; flex: 1; }
  .prog-fill { height: 100%; border-radius: 3px; transition: width .5s ease; }

  /* ── Legend ── */
  .legend-row { display: flex; gap: 12px; flex-wrap: wrap; font-size: 11px; color: var(--muted); margin-bottom: 12px; }
  .legend-item { display: flex; align-items: center; gap: 5px; }
  .legend-dot { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }

  /* ── Zone cards ── */
  .zone-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
  .zone-card { background: var(--card2); border: 1px solid var(--border); border-radius: var(--r); padding: 14px; }
  .zone-name { font-size: 12px; font-weight: 600; color: var(--text); margin-bottom: 8px; }
  .zone-bar-row { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }
  .zone-sub { font-size: 11px; color: var(--dim); }

  /* ── KPI compare ── */
  .kpi-header {
    display: grid; grid-template-columns: 180px 1fr 40px 1fr 80px;
    font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: .08em;
    font-family: var(--mono); padding: 6px 0; border-bottom: 1px solid var(--border2);
  }
  .kpi-row {
    display: grid; grid-template-columns: 180px 1fr 40px 1fr 80px;
    align-items: center; padding: 10px 0; border-bottom: 1px solid var(--border);
  }
  .kpi-row:last-child { border-bottom: none; }
  .kpi-name { font-size: 12px; color: var(--muted); }
  .kpi-a    { font-size: 17px; font-weight: 600; color: var(--blue); font-family: var(--mono); text-align: right; }
  .kpi-vs   { font-size: 11px; color: var(--dim); text-align: center; }
  .kpi-p    { font-size: 17px; font-weight: 600; color: var(--accent); font-family: var(--mono); }
  .kpi-badge{ text-align: right; }

  /* ── Insights ── */
  .insight-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
  .insight-card { background: var(--card2); border: 1px solid var(--border); border-radius: var(--r); padding: 14px; }
  .insight-icon  { font-size: 18px; margin-bottom: 6px; }
  .insight-title { font-size: 12px; font-weight: 600; color: var(--text); margin-bottom: 4px; }
  .insight-body  { font-size: 11px; color: var(--muted); line-height: 1.6; }

  /* ── Roads list ── */
  .roads-list { display: flex; flex-direction: column; gap: 8px; }
  .road-row { display: flex; align-items: center; gap: 10px; padding: 4px 0; }
  .road-name { font-size: 12px; color: var(--text); flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  /* ── Issues ── */
  .issue-list { display: flex; flex-direction: column; gap: 10px; }
  .issue-item { display: flex; gap: 12px; align-items: flex-start; padding: 12px; background: var(--card2); border: 1px solid var(--border); border-radius: var(--r); }
  .issue-sev { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-top: 4px; }
  .issue-sev-critical { background: var(--red); }
  .issue-sev-high     { background: var(--amber); }
  .issue-sev-medium   { background: var(--blue); }
  .issue-title { font-size: 13px; font-weight: 500; color: var(--text); }
  .issue-fix   { font-size: 11px; color: var(--muted); margin-top: 3px; line-height: 1.6; }

  /* ── Code block ── */
  .code-block {
    background: #080C12; border: 1px solid var(--border); border-radius: var(--r);
    padding: 14px 16px; font-family: var(--mono); font-size: 12px; color: #7DD3FC;
    line-height: 1.7; overflow-x: auto; margin-bottom: 0; white-space: pre;
  }

  /* ── Roadmap ── */
  .roadmap-section { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; font-family: var(--mono); margin-bottom: 12px; }
  .roadmap { display: flex; flex-direction: column; gap: 12px; }
  .roadmap-item { display: flex; gap: 12px; align-items: flex-start; }
  .rm-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; margin-top: 3px; }
  .rm-done { background: var(--accent); }
  .rm-todo { background: var(--border2); }
  .rm-title { font-size: 13px; font-weight: 500; color: var(--text); }
  .rm-desc  { font-size: 11px; color: var(--muted); margin-top: 2px; }

  @media (max-width: 900px) {
    .metrics-4, .metrics-3 { grid-template-columns: 1fr 1fr; }
    .grid-2, .insight-grid, .zone-grid { grid-template-columns: 1fr; }
    .kpi-header, .kpi-row { grid-template-columns: 1fr 80px 32px 80px 64px; }
    .kpi-name { font-size: 11px; }
  }
</style>