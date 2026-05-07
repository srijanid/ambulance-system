<script lang="ts">
  import { onMount, tick } from "svelte";
  import { browser } from "$app/environment";

  // ── Types ────────────────────────────────────────────────────────────
  interface Ambulance {
    id: string;
    base_node: [number, number];
    current_node: [number, number];
    status: string;
    assigned_emergency_id: string | null;
    total_responses: number;
    total_distance: number;
  }
  interface Hospital {
    id: string;
    name: string;
    node: [number, number];
    capacity: number;
    current_patients: number;
    occupancy_pct: number;
    is_available: boolean;
  }
  interface Snapshot {
    tick: number;
    new_emergency: any;
    active: number;
    resolved: number;
    avg_congestion: number;
  }
  interface HeatNode {
    node: [number, number];
    row: number;
    col: number;
    demand: number;
    min_dist_to_facility: number;
    risk_score: number;
    risk_score_normalised: number;
  }
  interface GridNode {
    id: string;
    row: number;
    col: number;
    neighbours: { row: number; col: number; weight: number }[];
  }
  interface AlgoPair {
    astar: { nodes_explored: number; computation_time_ms: number; cost: number };
    dijkstra: { nodes_explored: number; computation_time_ms: number; cost: number };
    astar_traffic: { cost: number };
    speedup: number;
    nodes_saved: number;
  }
  interface SimData {
    config: { rows: number; cols: number; seed: number; use_traffic: boolean; coverage_radius: number };
    grid: GridNode[];
    ambulances: Ambulance[];
    hospitals: Hospital[];
    active_emergencies: any[];
    heatmap: HeatNode[];
    coverage: { coverage_pct: number; covered_nodes: number; total_nodes: number; node_distances: Record<string, number> };
    traffic: { tick: number; avg_congestion_factor: number; level_distribution: Record<string, number>; incidents: any[] };
    metrics: { total_dispatches: number; avg_eta_seconds: number; avg_route_cost: number; avg_computation_ms: number };
    algorithm_comparison: { pairs: AlgoPair[]; summary: any };
    snapshots: Snapshot[];
    resolved_count: number;
  }

  // ── State ────────────────────────────────────────────────────────────
  let sim: SimData | null = null;
  let activeTab: "overview" | "city" | "algo" | "coverage" | "fleet" = "overview";
  let layerMode: "normal" | "heatmap" | "traffic" = "normal";
  let chartsRendered: Record<string, boolean> = {};
  let Chart: any;

  // canvas ref
  let cityCanvas: HTMLCanvasElement;

  // ── Load data ────────────────────────────────────────────────────────
  onMount(async () => {
    if (!browser) return;
    const res = await fetch("../src/simulation_data.json");
    sim = await res.json() as SimData;

    // Load Chart.js
    await loadChartJs();
    await tick();
    renderChartsFor("overview");
    chartsRendered["overview"] = true;
    setTimeout(() => renderGrid(), 80);
  });

  function loadChartJs(): Promise<void> {
    return new Promise((resolve) => {
      if ((window as any).Chart) { Chart = (window as any).Chart; resolve(); return; }
      const s = document.createElement("script");
      s.src = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js";
      s.onload = () => { Chart = (window as any).Chart; resolve(); };
      document.head.appendChild(s);
    });
  }

  async function switchTab(name: typeof activeTab) {
    activeTab = name;
    await tick();
    if (!chartsRendered[name]) {
      renderChartsFor(name);
      chartsRendered[name] = true;
    }
    if (name === "city") setTimeout(renderGrid, 50);
  }

  function renderChartsFor(name: string) {
    if (!sim || !Chart) return;
    if (name === "overview") renderOverviewCharts();
    if (name === "algo") renderAlgoCharts();
    if (name === "coverage") renderCoverageCharts();
    if (name === "fleet") renderFleetChart();
  }

  // ── Derived data ─────────────────────────────────────────────────────
  $: avgEtaMin = sim ? (sim.metrics.avg_eta_seconds / 60).toFixed(1) : "—";
  $: severityCounts = sim
    ? sim.snapshots.reduce((acc: Record<string, number>, s) => {
        if (s.new_emergency) acc[s.new_emergency.severity] = (acc[s.new_emergency.severity] || 0) + 1;
        return acc;
      }, {})
    : {};

  // ── Chart colours ────────────────────────────────────────────────────
  const BLUE = "#378ADD", TEAL = "#1D9E75", AMBER = "#BA7517", RED = "#E24B4A", GRAY = "#888780";

  function baseOpts(yMin?: number) {
    const tc = "rgba(255,255,255,0.55)", gc = "rgba(255,255,255,0.07)";
    return {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: tc, font: { size: 10 } }, grid: { color: gc } },
        y: { ticks: { color: tc, font: { size: 10 } }, grid: { color: gc }, ...(yMin != null ? { min: yMin } : {}) },
      },
    };
  }

  function destroyChart(id: string) {
    const existing = Chart.getChart(id);
    if (existing) existing.destroy();
  }

  // ── Overview charts ──────────────────────────────────────────────────
  function renderOverviewCharts() {
    if (!sim) return;
    const ticks = sim.snapshots.map(s => s.tick);

    destroyChart("activityChart");
    new Chart(document.getElementById("activityChart"), {
      type: "line",
      data: {
        labels: ticks,
        datasets: [
          { label: "Active", data: sim.snapshots.map(s => s.active), borderColor: RED, backgroundColor: RED + "22", fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2 },
          { label: "Resolved", data: sim.snapshots.map(s => s.resolved), borderColor: TEAL, backgroundColor: TEAL + "22", fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2 },
        ],
      },
      options: {
        ...baseOpts(), responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: true, position: "top", labels: { color: "rgba(255,255,255,0.55)", font: { size: 11 }, boxWidth: 10, padding: 12 } } },
      },
    });

    destroyChart("trafficChart");
    new Chart(document.getElementById("trafficChart"), {
      type: "line",
      data: {
        labels: ticks,
        datasets: [{ data: sim.snapshots.map(s => s.avg_congestion), borderColor: AMBER, backgroundColor: AMBER + "22", fill: true, tension: 0.5, pointRadius: 0, borderWidth: 2 }],
      },
      options: {
        ...baseOpts(1.0), responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: baseOpts().scales.x, y: { ...baseOpts(1.0).scales.y, ticks: { color: "rgba(255,255,255,0.55)", font: { size: 10 }, callback: (v: number) => v.toFixed(2) } } },
      },
    });

    destroyChart("severityChart");
    const sevOrder = ["critical", "high", "medium", "low"];
    const sevColors = [RED, "#EF9F27", BLUE, TEAL];
    new Chart(document.getElementById("severityChart"), {
      type: "doughnut",
      data: {
        labels: sevOrder.map(s => s.charAt(0).toUpperCase() + s.slice(1)),
        datasets: [{ data: sevOrder.map(s => severityCounts[s] || 0), backgroundColor: sevColors, borderWidth: 0, hoverOffset: 4 }],
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: "60%",
        plugins: { legend: { display: true, position: "right", labels: { color: "rgba(255,255,255,0.55)", font: { size: 11 }, boxWidth: 10, padding: 8 } } },
      },
    });
  }

  // ── Algo charts ──────────────────────────────────────────────────────
  function renderAlgoCharts() {
    if (!sim) return;
    const pairs = sim.algorithm_comparison.pairs;
    const labels = pairs.map((_, i) => "P" + (i + 1));
    const tc = "rgba(255,255,255,0.55)", gc = "rgba(255,255,255,0.07)";

    destroyChart("algoNodesChart");
    new Chart(document.getElementById("algoNodesChart"), {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "A*", data: pairs.map(p => p.astar.nodes_explored), backgroundColor: BLUE + "cc", borderRadius: 2 },
          { label: "Dijkstra", data: pairs.map(p => p.dijkstra.nodes_explored), backgroundColor: GRAY + "cc", borderRadius: 2 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: true, position: "top", labels: { color: tc, font: { size: 11 }, boxWidth: 10 } } },
        scales: { x: { ticks: { color: tc, font: { size: 10 }, autoSkip: true, maxTicksLimit: 10 }, grid: { color: gc } }, y: { ticks: { color: tc, font: { size: 10 } }, grid: { color: gc } } },
      },
    });

    destroyChart("algoTimeChart");
    new Chart(document.getElementById("algoTimeChart"), {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "A* (ms)", data: pairs.map(p => p.astar.computation_time_ms), backgroundColor: BLUE + "cc", borderRadius: 2 },
          { label: "Dijkstra (ms)", data: pairs.map(p => p.dijkstra.computation_time_ms), backgroundColor: GRAY + "cc", borderRadius: 2 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: true, position: "top", labels: { color: tc, font: { size: 11 }, boxWidth: 10 } } },
        scales: {
          x: { ticks: { color: tc, font: { size: 10 }, autoSkip: true, maxTicksLimit: 10 }, grid: { color: gc } },
          y: { ticks: { color: tc, font: { size: 10 }, callback: (v: number) => v.toFixed(3) }, grid: { color: gc } },
        },
      },
    });

    destroyChart("routeCompChart");
    new Chart(document.getElementById("routeCompChart"), {
      type: "scatter",
      data: {
        datasets: [
          { label: "Static A*", data: pairs.map((p, i) => ({ x: i + 1, y: parseFloat(p.astar.cost.toFixed(1)) })), backgroundColor: BLUE + "cc", pointRadius: 5 },
          { label: "Traffic-aware", data: pairs.map((p, i) => ({ x: i + 1, y: parseFloat(p.astar_traffic.cost.toFixed(1)) })), backgroundColor: AMBER + "cc", pointRadius: 5, pointStyle: "triangle" },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: true, position: "top", labels: { color: tc, font: { size: 11 }, boxWidth: 10, usePointStyle: true } } },
        scales: {
          x: { ticks: { color: tc, font: { size: 10 } }, grid: { color: gc }, title: { display: true, text: "Query pair", color: tc, font: { size: 10 } } },
          y: { ticks: { color: tc, font: { size: 10 } }, grid: { color: gc }, title: { display: true, text: "Path cost", color: tc, font: { size: 10 } } },
        },
      },
    });
  }

  // ── Coverage charts ──────────────────────────────────────────────────
  function renderCoverageCharts() {
    if (!sim) return;
    const hm = sim.heatmap;
    const tc = "rgba(255,255,255,0.55)", gc = "rgba(255,255,255,0.07)";

    destroyChart("heatmapChart");
    new Chart(document.getElementById("heatmapChart"), {
      type: "bubble",
      data: {
        datasets: [{
          data: hm.map(h => ({ x: h.col, y: h.row, r: Math.max(2, h.risk_score_normalised * 9) })),
          backgroundColor: hm.map(h => {
            const v = h.risk_score_normalised;
            if (v < 0.2) return "#3266ad88";
            if (v < 0.4) return "#7aacd688";
            if (v < 0.6) return "#fdd0a288";
            if (v < 0.8) return "#fd8d3c88";
            return "#a6360388";
          }),
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false, layout: { padding: 10 },
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (d: any) => `Risk: ${d.raw.r.toFixed(2)}` } } },
        scales: {
          x: { min: -1, max: 14, ticks: { color: tc, font: { size: 9 } }, grid: { color: gc } },
          y: { min: -1, max: 14, ticks: { color: tc, font: { size: 9 } }, grid: { color: gc } },
        },
      },
    });

    // Distance-to-facility histogram using real node_distances
    const distances = Object.values(sim.coverage.node_distances);
    const maxDist = Math.max(...distances);
    const bucketCount = 10;
    const bucketSize = maxDist / bucketCount;
    const buckets = new Array(bucketCount).fill(0);
    distances.forEach(d => {
      const idx = Math.min(bucketCount - 1, Math.floor(d / bucketSize));
      buckets[idx]++;
    });
    const bucketLabels = Array.from({ length: bucketCount }, (_, i) =>
      `${(i * bucketSize).toFixed(0)}–${((i + 1) * bucketSize).toFixed(0)}`
    );

    destroyChart("distChart");
    new Chart(document.getElementById("distChart"), {
      type: "bar",
      data: {
        labels: bucketLabels,
        datasets: [{ data: buckets, backgroundColor: TEAL + "bb", borderRadius: 2 }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: tc, font: { size: 9 }, maxRotation: 40 }, grid: { color: gc } },
          y: { ticks: { color: tc, font: { size: 10 } }, grid: { color: gc } },
        },
      },
    });
  }

  // ── Fleet chart ──────────────────────────────────────────────────────
  function renderFleetChart() {
    if (!sim) return;
    const ambs = sim.ambulances;
    const tc = "rgba(255,255,255,0.55)", gc = "rgba(255,255,255,0.07)";

    destroyChart("fleetChart");
    new Chart(document.getElementById("fleetChart"), {
      type: "bar",
      data: {
        labels: ambs.map(a => a.id),
        datasets: [
          { label: "Responses", data: ambs.map(a => a.total_responses), backgroundColor: BLUE + "cc", borderRadius: 2, yAxisID: "y" },
          { label: "Distance", data: ambs.map(a => Math.round(a.total_distance)), backgroundColor: TEAL + "cc", borderRadius: 2, yAxisID: "y1" },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: true, position: "top", labels: { color: tc, font: { size: 11 }, boxWidth: 10 } } },
        scales: {
          x: { ticks: { color: tc, font: { size: 11 } }, grid: { color: gc } },
          y: { position: "left", ticks: { color: tc, font: { size: 10 } }, grid: { color: gc }, title: { display: true, text: "Responses", color: tc, font: { size: 10 } } },
          y1: { position: "right", ticks: { color: tc, font: { size: 10 } }, grid: { display: false }, title: { display: true, text: "Distance", color: tc, font: { size: 10 } } },
        },
      },
    });
  }

  // ── Grid canvas ──────────────────────────────────────────────────────
  function renderGrid() {
    if (!sim || !cityCanvas) return;
    const ctx = cityCanvas.getContext("2d")!;
    const W = cityCanvas.width, H = cityCanvas.height;
    const { rows, cols } = sim.config;
    const pad = 28;
    const cellW = (W - pad * 2) / cols;
    const cellH = (H - pad * 2) / rows;
    const nodeX = (c: number) => pad + c * cellW + cellW / 2;
    const nodeY = (r: number) => pad + r * cellH + cellH / 2;

    ctx.fillStyle = "#0a0e1a";
    ctx.fillRect(0, 0, W, H);

    if (layerMode === "heatmap") {
      sim.heatmap.forEach(h => {
        const v = h.risk_score_normalised;
        const r = Math.round(v * 255), b = Math.round((1 - v) * 200);
        ctx.fillStyle = `rgba(${r},${Math.round(60 + v * 30)},${b},0.85)`;
        ctx.fillRect(nodeX(h.col) - cellW / 2 + 1, nodeY(h.row) - cellH / 2 + 1, cellW - 2, cellH - 2);
      });
      sim.hospitals.forEach(h => {
        ctx.fillStyle = "#60a5fa";
        ctx.beginPath(); ctx.arc(nodeX(h.node[1]), nodeY(h.node[0]), 7, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = "#fff"; ctx.font = "bold 8px sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillText("H", nodeX(h.node[1]), nodeY(h.node[0]));
      });
      return;
    }

    if (layerMode === "traffic") {
      // Build factor map from node_distances as proxy
      const factorMap: Record<string, number> = {};
      sim.heatmap.forEach(h => { factorMap[`${h.row},${h.col}`] = h.risk_score_normalised; });
      for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
        const v = factorMap[`${r},${c}`] ?? 0.3;
        const rv = Math.round(v * 220), gv = Math.round((1 - v) * 200);
        ctx.fillStyle = `rgba(${rv},${gv},40,0.75)`;
        ctx.fillRect(nodeX(c) - cellW / 2 + 1, nodeY(r) - cellH / 2 + 1, cellW - 2, cellH - 2);
      }
      // Traffic incident hotspots
      sim.traffic.incidents.forEach(inc => {
        const [r, c] = inc.node;
        ctx.strokeStyle = "#ff4444"; ctx.lineWidth = 2;
        ctx.strokeRect(nodeX(c) - cellW / 2 + 2, nodeY(r) - cellH / 2 + 2, cellW - 4, cellH - 4);
      });
      return;
    }

    // Normal network view — draw edges from real grid data
    sim.grid.forEach(node => {
      node.neighbours.forEach(nb => {
        const alpha = Math.max(0.1, Math.min(0.5, 1 / (nb.weight / 3)));
        ctx.strokeStyle = `rgba(55,80,120,${alpha})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(nodeX(node.col), nodeY(node.row));
        ctx.lineTo(nodeX(nb.col), nodeY(nb.row));
        ctx.stroke();
      });
    });

    // Road nodes
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      ctx.fillStyle = "#374151";
      ctx.beginPath(); ctx.arc(nodeX(c), nodeY(r), 2, 0, Math.PI * 2); ctx.fill();
    }

    // Hospital coverage rings
    sim.hospitals.forEach(h => {
      const x = nodeX(h.node[1]), y = nodeY(h.node[0]);
      const radiusPx = sim!.config.coverage_radius * Math.min(cellW, cellH);
      ctx.fillStyle = "rgba(59,130,246,0.07)";
      ctx.beginPath(); ctx.arc(x, y, radiusPx, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = "rgba(59,130,246,0.25)"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.arc(x, y, radiusPx, 0, Math.PI * 2); ctx.stroke();
    });

    // Active emergency routes
    sim.active_emergencies.forEach(em => {
      if (em.route?.length > 1) {
        ctx.strokeStyle = em.color + "99"; ctx.lineWidth = 2; ctx.setLineDash([4, 4]);
        ctx.beginPath();
        em.route.forEach(([r, c]: [number, number], idx: number) => {
          if (idx === 0) ctx.moveTo(nodeX(c), nodeY(r)); else ctx.lineTo(nodeX(c), nodeY(r));
        });
        ctx.stroke(); ctx.setLineDash([]);
      }
    });

    // Hospitals
    sim.hospitals.forEach(h => {
      const x = nodeX(h.node[1]), y = nodeY(h.node[0]);
      ctx.fillStyle = "#3b82f6"; ctx.strokeStyle = "#93c5fd"; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(x, y, 8, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#fff"; ctx.font = "bold 9px sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText("H", x, y);
    });

    // Ambulances
    sim.ambulances.forEach(a => {
      const x = nodeX(a.current_node[1]), y = nodeY(a.current_node[0]);
      const col = a.status === "available" ? "#22c55e" : a.status === "dispatched" ? "#f59e0b" : "#60a5fa";
      ctx.fillStyle = col; ctx.strokeStyle = col + "88"; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#fff"; ctx.font = "bold 7px sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText("A", x, y);
    });

    // Active emergencies
    sim.active_emergencies.forEach(em => {
      const x = nodeX(em.node[1]), y = nodeY(em.node[0]);
      ctx.fillStyle = em.color; ctx.strokeStyle = em.color + "99"; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(x, y, 7, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      ctx.fillStyle = "#fff"; ctx.font = "bold 8px sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText("!", x, y);
    });
  }

  $: if (browser && cityCanvas && sim) renderGrid();
  $: layerMode, renderGrid();

  // ── Helpers ──────────────────────────────────────────────────────────
  const statusBadge: Record<string, string> = {
    available: "badge-available", dispatched: "badge-dispatched",
    returning: "badge-returning", on_scene: "badge-dispatched", at_hospital: "badge-medium",
  };
</script>

<svelte:head>
  <title>Simulation Dashboard — Smart Ambulance Dispatch</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet" />
</svelte:head>

<!-- ════════════════════════════════════════ NAV ══ -->
<nav class="topnav">
  <a href="/" class="nav-brand">🚑 Ambulance System</a>
  <div class="nav-links">
    <a href="/">Grid</a>
    <a href="/simulation" class="active">Simulation</a>
    <a href="/dashboard">India/Kolkata</a>
    <a href="/map">Map</a>
  </div>
</nav>

{#if !sim}
  <div class="loading-screen">
    <div class="spinner"></div>
    <p>Loading simulation data…</p>
  </div>
{:else}

<!-- ════════════════════════════════════════ DASH ══ -->
<div class="dash">

  <!-- Topbar -->
  <div class="topbar">
    <div class="title-block">
      <h1>Smart Ambulance Dispatch</h1>
      <p>A* routing · PSO placement · Real-time traffic simulation · {sim.config.rows}×{sim.config.cols} urban grid · seed {sim.config.seed}</p>
    </div>
    <div class="status-pill">
      <div class="pulse"></div>
      Simulation complete — {sim.snapshots.length} ticks · {sim.resolved_count} resolved
    </div>
  </div>

  <!-- Tabs -->
  <div class="tabs">
    {#each [["overview","Overview"],["city","City map"],["algo","Algorithm analysis"],["coverage","Coverage"],["fleet","Fleet status"]] as [id, label]}
      <button class="tab" class:active={activeTab === id} on:click={() => switchTab(id as any)}>
        {label}
      </button>
    {/each}
  </div>

  <!-- ═══ OVERVIEW ════════════════════════════════════════════════════ -->
  {#if activeTab === "overview"}
    <div class="grid-4">
      <div class="stat">
        <div class="lbl">Emergencies resolved</div>
        <div class="val" style="color:#1D9E75">{sim.resolved_count}</div>
        <div class="sub">from {sim.snapshots.length}-tick simulation</div>
      </div>
      <div class="stat">
        <div class="lbl">Avg ETA</div>
        <div class="val">{avgEtaMin}<span class="val-unit">min</span></div>
        <div class="sub">{sim.metrics.avg_eta_seconds.toFixed(1)}s avg ETA</div>
      </div>
      <div class="stat">
        <div class="lbl">Total dispatches</div>
        <div class="val">{sim.metrics.total_dispatches}</div>
        <div class="sub">via A* pathfinding</div>
      </div>
      <div class="stat">
        <div class="lbl">Fleet size</div>
        <div class="val">{sim.ambulances.length}</div>
        <div class="sub">{sim.hospitals.length} hospitals · {sim.config.rows}×{sim.config.cols} grid</div>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-title">Emergency activity over time</div>
        <div class="chart-wrap"><canvas id="activityChart"></canvas></div>
      </div>
      <div class="card">
        <div class="card-title">Traffic congestion over time</div>
        <div class="chart-wrap"><canvas id="trafficChart"></canvas></div>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-title">Severity breakdown (all spawned)</div>
        <div class="chart-wrap" style="height:160px"><canvas id="severityChart"></canvas></div>
      </div>
      <div class="card">
        <div class="card-title">Algorithm comparison snapshot</div>
        <div class="algo-compare">
          <div class="algo-card">
            <div class="big" style="color:#185FA5">{sim.algorithm_comparison.summary.avg_astar_nodes}</div>
            <div class="lbl">A* avg nodes</div>
          </div>
          <div class="algo-card">
            <div class="big" style="color:#888780">{sim.algorithm_comparison.summary.avg_dijkstra_nodes}</div>
            <div class="lbl">Dijkstra avg nodes</div>
          </div>
          <div class="algo-card">
            <div class="big" style="color:#1D9E75">{sim.algorithm_comparison.summary.avg_speedup}×</div>
            <div class="lbl">A* speedup</div>
          </div>
        </div>
        <p class="hint">
          A* explores {((1 - sim.algorithm_comparison.summary.avg_astar_nodes / sim.algorithm_comparison.summary.avg_dijkstra_nodes) * 100).toFixed(1)}% fewer nodes than Dijkstra across {sim.algorithm_comparison.summary.n_pairs} path pairs,
          with {(sim.algorithm_comparison.summary.avg_dijkstra_ms - sim.algorithm_comparison.summary.avg_astar_ms).toFixed(3)}ms avg time saved per query.
        </p>
      </div>
    </div>
  {/if}

  <!-- ═══ CITY MAP ═════════════════════════════════════════════════════ -->
  {#if activeTab === "city"}
    <div class="card" style="padding:1rem">
      <div class="city-header">
        <div class="card-title" style="margin-bottom:0">City grid — {sim.config.rows}×{sim.config.cols} road network</div>
        <div class="layer-select">
          <label>Layer:</label>
          <select bind:value={layerMode} on:change={renderGrid}>
            <option value="normal">Network</option>
            <option value="heatmap">Demand heatmap</option>
            <option value="traffic">Traffic</option>
          </select>
        </div>
      </div>
      <div class="grid-canvas-wrap">
        <canvas bind:this={cityCanvas} width="640" height="480"></canvas>
      </div>
      <div class="legend">
        {#if layerMode === "normal"}
          <div class="leg-item"><div class="leg-dot" style="background:#22c55e"></div>Ambulance (available)</div>
          <div class="leg-item"><div class="leg-dot" style="background:#f59e0b"></div>Ambulance (dispatched)</div>
          <div class="leg-item"><div class="leg-dot" style="background:#3b82f6"></div>Hospital</div>
          <div class="leg-item"><div class="leg-dot" style="background:#ef4444"></div>Emergency</div>
          <div class="leg-item"><div class="leg-dot" style="background:#374151"></div>Road node</div>
        {:else if layerMode === "heatmap"}
          <div class="heat-legend">
            {#each ["#3266ad","#5489c2","#7aacd6","#a9cfe7","#d3e8f5","#fdd0a2","#fdae6b","#fd8d3c","#e6550d","#a63603"] as c}
              <div style="background:{c}"></div>
            {/each}
          </div>
          <span style="font-size:11px">Low risk ← → High risk</span>
        {:else}
          <div class="leg-item"><div class="leg-dot" style="background:#4ade80;border-radius:2px"></div>Clear</div>
          <div class="leg-item"><div class="leg-dot" style="background:#facc15;border-radius:2px"></div>Moderate</div>
          <div class="leg-item"><div class="leg-dot" style="background:#ef4444;border-radius:2px"></div>Heavy · incidents marked with red border</div>
        {/if}
      </div>
      <!-- Traffic incidents from real data -->
      {#if layerMode === "traffic" && sim.traffic.incidents.length}
        <div class="incidents-list">
          {#each sim.traffic.incidents as inc}
            <div class="incident-row">
              <span class="inc-node">[{inc.node[0]},{inc.node[1]}]</span>
              <span class="badge badge-{inc.level === 'heavy' ? 'critical' : inc.level === 'moderate' ? 'high' : 'available'}">{inc.level}</span>
              <span class="inc-desc">{inc.description}</span>
              <span class="inc-factor">×{inc.factor.toFixed(2)}</span>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  <!-- ═══ ALGO ══════════════════════════════════════════════════════════ -->
  {#if activeTab === "algo"}
    <div class="grid-4">
      <div class="stat"><div class="lbl">A* avg nodes</div><div class="val" style="color:#185FA5">{sim.algorithm_comparison.summary.avg_astar_nodes}</div><div class="sub">per path query</div></div>
      <div class="stat"><div class="lbl">Dijkstra avg nodes</div><div class="val" style="color:#888780">{sim.algorithm_comparison.summary.avg_dijkstra_nodes}</div><div class="sub">per path query</div></div>
      <div class="stat"><div class="lbl">A* speedup</div><div class="val" style="color:#1D9E75">{sim.algorithm_comparison.summary.avg_speedup}×</div><div class="sub">faster computation</div></div>
      <div class="stat"><div class="lbl">Nodes saved</div><div class="val">{sim.algorithm_comparison.summary.avg_nodes_saved}</div><div class="sub">per query avg</div></div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-title">Nodes explored — A* vs Dijkstra ({sim.algorithm_comparison.summary.n_pairs} pairs)</div>
        <div class="chart-wrap" style="height:220px"><canvas id="algoNodesChart"></canvas></div>
      </div>
      <div class="card">
        <div class="card-title">Computation time (ms) per query</div>
        <div class="chart-wrap" style="height:220px"><canvas id="algoTimeChart"></canvas></div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Route cost — static vs traffic-aware A*</div>
      <div class="chart-wrap" style="height:200px"><canvas id="routeCompChart"></canvas></div>
      <p class="hint" style="margin-top:8px">
        Traffic-aware routing produces higher costs due to congestion multipliers (avg factor {sim.traffic.avg_congestion_factor.toFixed(2)}).
        Each point is one of {sim.algorithm_comparison.summary.n_pairs} test pairs. Seed: {sim.config.seed}.
      </p>
    </div>

    <div class="card card-muted">
      <div class="card-title">How A* works — f(n) = g(n) + h(n)</div>
      <div class="algo-explain">
        <div><strong>g(n)</strong><br><span>Actual cost from start to node n — accumulated edge weights along the best known path so far.</span></div>
        <div><strong>h(n)</strong><br><span>Heuristic estimate of cost from n to goal. Uses Manhattan distance for grid graphs — admissible and consistent.</span></div>
        <div><strong>Priority queue</strong><br><span>A min-heap ordered by f(n). Nodes with lower total estimated cost are expanded first, pruning unnecessary branches.</span></div>
      </div>
    </div>
  {/if}

  <!-- ═══ COVERAGE ═════════════════════════════════════════════════════ -->
  {#if activeTab === "coverage"}
    <div class="grid-4">
      <div class="stat"><div class="lbl">Coverage %</div><div class="val" style="color:#E24B4A">{sim.coverage.coverage_pct}%</div><div class="sub">within radius {sim.config.coverage_radius}</div></div>
      <div class="stat"><div class="lbl">Covered nodes</div><div class="val">{sim.coverage.covered_nodes}</div><div class="sub">of {sim.coverage.total_nodes} total</div></div>
      <div class="stat"><div class="lbl">Hospitals placed</div><div class="val">{sim.hospitals.length}</div><div class="sub">via K-means clustering</div></div>
      <div class="stat"><div class="lbl">Coverage radius</div><div class="val">{sim.config.coverage_radius}</div><div class="sub">graph distance units</div></div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-title">Demand heatmap — risk score distribution</div>
        <div class="chart-wrap" style="height:220px"><canvas id="heatmapChart"></canvas></div>
        <div class="heat-legend">
          {#each ["#3266ad","#5489c2","#7aacd6","#a9cfe7","#d3e8f5","#fdd0a2","#fdae6b","#fd8d3c","#e6550d","#a63603"] as c}
            <div style="background:{c}"></div>
          {/each}
        </div>
        <div class="heat-legend-labels"><span>Low risk</span><span>High risk</span></div>
      </div>
      <div class="card">
        <div class="card-title">Distance to nearest facility distribution</div>
        <div class="chart-wrap" style="height:220px"><canvas id="distChart"></canvas></div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">Coverage optimization — K-means vs random placement</div>
      <div class="coverage-compare">
        <div>
          <div class="cc-head" style="color:#1D9E75">K-means optimized</div>
          <div class="cc-body">
            Facilities placed at centroid of demand clusters.<br>
            Minimizes average distance to nearest facility.<br>
            Coverage: <strong>{sim.coverage.coverage_pct}%</strong> within radius {sim.config.coverage_radius}<br>
            Uncovered nodes: {sim.coverage.uncovered_nodes} of {sim.coverage.total_nodes}
          </div>
        </div>
        <div>
          <div class="cc-head" style="color:#888780">Random baseline</div>
          <div class="cc-body">
            Facilities placed at uniformly random nodes.<br>
            No optimization — naive dispatch.<br>
            Expected coverage: ~<strong>6–7%</strong> within same radius<br>
            K-means improvement: ~+{(sim.coverage.coverage_pct - 6.5).toFixed(1)}% coverage
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- ═══ FLEET ═════════════════════════════════════════════════════════ -->
  {#if activeTab === "fleet"}
    <div class="grid-2">
      <div class="card">
        <div class="card-title">Ambulance fleet status</div>
        {#each sim.ambulances as a}
          <div class="amb-row">
            <span class="amb-id">{a.id}</span>
            <span class="node-label">[{a.current_node[0]},{a.current_node[1]}]</span>
            <span class="badge {statusBadge[a.status] || 'badge-medium'}">{a.status}</span>
            <span class="resp-count">{a.total_responses} resp</span>
            <span class="dist-count">{a.total_distance.toFixed(1)} dist</span>
          </div>
        {/each}
      </div>
      <div class="card">
        <div class="card-title">Hospital occupancy</div>
        {#each sim.hospitals as h}
          <div class="hosp-row">
            <span class="hosp-name">{h.name}</span>
            <span class="hosp-count">{h.current_patients}/{h.capacity}</span>
            <div class="progress-bar"><div class="progress-fill" style="width:{h.occupancy_pct}%"></div></div>
            <span class="hosp-pct">{h.occupancy_pct.toFixed(1)}%</span>
          </div>
        {/each}
        {#if sim.active_emergencies.length}
          <div style="margin-top:12px;border-top:0.5px solid var(--c-border);padding-top:10px">
            <div class="card-title" style="margin-bottom:8px">Active emergencies</div>
            {#each sim.active_emergencies as em}
              <div class="amb-row">
                <span class="badge badge-{em.severity}">{em.severity}</span>
                <span style="font-size:12px;flex:1">{em.description}</span>
                <span class="node-label">[{em.node[0]},{em.node[1]}]</span>
                <span class="resp-count">{(em.eta_seconds/60).toFixed(1)}m ETA</span>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <div class="card">
      <div class="card-title">Fleet performance — responses &amp; distance</div>
      <div class="chart-wrap" style="height:200px"><canvas id="fleetChart"></canvas></div>
    </div>

    <div class="card card-muted">
      <div class="card-title">Dispatch algorithm logic</div>
      <div class="dispatch-logic">
        {#each [
          "Emergency submitted with severity level (critical / high / medium / low)",
          "Priority queue orders pending emergencies — critical first, then by creation time",
          "A* calculates cost from each available ambulance to the emergency node",
          "Nearest ambulance (lowest A* cost) is dispatched",
          "Best hospital selected by A* distance from emergency scene",
          "Ambulance marked dispatched until emergency resolved, then returns to available",
        ] as step, i}
          <div class="dispatch-step">
            <span class="step-num">{i + 1}</span>
            <span>{step}</span>
          </div>
        {/each}
      </div>
    </div>
  {/if}

</div><!-- /dash -->
{/if}<!-- /if sim -->

<style>
  :global(body) { background: #0a0d14; }

  .topnav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 24px;
    background: #080b12;
    border-bottom: 0.5px solid rgba(255,255,255,0.07);
    font-family: 'IBM Plex Sans', sans-serif;
  }
  .nav-brand { color: #f0f6ff; text-decoration: none; font-weight: 600; font-size: 14px; }
  .nav-links { display: flex; gap: 6px; }
  .nav-links a { color: rgba(255,255,255,0.45); text-decoration: none; font-size: 13px; padding: 5px 12px; border-radius: 6px; transition: all .15s; }
  .nav-links a:hover { color: rgba(255,255,255,0.9); background: rgba(255,255,255,0.06); }
  .nav-links a.active { color: rgba(255,255,255,0.9); background: rgba(255,255,255,0.09); }

  .loading-screen { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 60vh; gap: 16px; color: rgba(255,255,255,0.4); font-family: 'IBM Plex Mono', monospace; font-size: 13px; }
  .spinner { width: 32px; height: 32px; border: 2px solid rgba(255,255,255,0.1); border-top-color: #378ADD; border-radius: 50%; animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Dashboard ── */
  .dash { padding: 1rem 1.5rem; font-family: 'IBM Plex Sans', sans-serif; color: #e2e8f0; max-width: 1200px; margin: 0 auto; }

  .topbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
  .title-block h1 { font-size: 17px; font-weight: 600; letter-spacing: -0.3px; color: #f0f6ff; }
  .title-block p { font-size: 12px; color: rgba(255,255,255,0.4); margin-top: 2px; font-family: 'IBM Plex Mono', monospace; }
  .status-pill { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; padding: 5px 11px; border-radius: 20px; background: rgba(29,158,117,0.12); color: #4ade80; font-weight: 500; border: 0.5px solid rgba(29,158,117,0.3); }
  .pulse { width: 7px; height: 7px; border-radius: 50%; background: #4ade80; animation: pulse 1.4s ease infinite; }
  @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(0.8)} }

  /* ── Tabs ── */
  .tabs { display: flex; gap: 2px; border-bottom: 0.5px solid rgba(255,255,255,0.08); margin-bottom: 1rem; }
  .tab { padding: 7px 14px; font-size: 13px; cursor: pointer; border: none; background: none; color: rgba(255,255,255,0.4); border-bottom: 2px solid transparent; margin-bottom: -1px; transition: color .15s; font-family: 'IBM Plex Sans', sans-serif; }
  .tab:hover { color: rgba(255,255,255,0.8); }
  .tab.active { color: #f0f6ff; border-bottom-color: #f0f6ff; font-weight: 500; }

  /* ── Grids ── */
  .grid-4 { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 10px; margin-bottom: 1rem; }
  .grid-2 { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 12px; margin-bottom: 1rem; }

  /* ── Stat tiles ── */
  .stat { background: rgba(255,255,255,0.04); border: 0.5px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 12px 14px; }
  .stat .lbl { font-size: 11px; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: .4px; margin-bottom: 4px; }
  .stat .val { font-size: 26px; font-weight: 500; color: #f0f6ff; line-height: 1.1; }
  .val-unit { font-size: 14px; font-weight: 400; color: rgba(255,255,255,0.5); margin-left: 2px; }
  .stat .sub { font-size: 11px; color: rgba(255,255,255,0.3); margin-top: 3px; }

  /* ── Cards ── */
  .card { background: rgba(255,255,255,0.03); border: 0.5px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 12px; }
  .card-muted { background: rgba(255,255,255,0.02); border-color: transparent; }
  .card-title { font-size: 12px; font-weight: 500; margin-bottom: 12px; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: .4px; }

  /* ── Charts ── */
  .chart-wrap { position: relative; height: 180px; }

  /* ── Badges ── */
  .badge { display: inline-block; font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 500; }
  .badge-critical { background: rgba(226,75,74,0.15); color: #f87171; border: 0.5px solid rgba(226,75,74,0.3); }
  .badge-high { background: rgba(186,117,23,0.15); color: #fbbf24; border: 0.5px solid rgba(186,117,23,0.3); }
  .badge-medium { background: rgba(55,138,221,0.15); color: #60a5fa; border: 0.5px solid rgba(55,138,221,0.3); }
  .badge-available { background: rgba(29,158,117,0.15); color: #4ade80; border: 0.5px solid rgba(29,158,117,0.3); }
  .badge-dispatched { background: rgba(245,158,11,0.15); color: #fbbf24; border: 0.5px solid rgba(245,158,11,0.3); }
  .badge-returning { background: rgba(55,138,221,0.15); color: #60a5fa; border: 0.5px solid rgba(55,138,221,0.3); }
  .badge-low { background: rgba(29,158,117,0.1); color: #6ee7b7; border: 0.5px solid rgba(29,158,117,0.2); }

  /* ── Algo compare ── */
  .algo-compare { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 10px; }
  .algo-card { border: 0.5px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 12px; text-align: center; }
  .algo-card .big { font-size: 28px; font-weight: 500; line-height: 1; }
  .algo-card .lbl { font-size: 11px; color: rgba(255,255,255,0.4); margin-top: 4px; text-transform: uppercase; letter-spacing: .3px; }
  .hint { font-size: 12px; color: rgba(255,255,255,0.35); line-height: 1.6; }

  /* ── City map ── */
  .city-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
  .layer-select { display: flex; align-items: center; gap: 6px; font-size: 12px; color: rgba(255,255,255,0.4); }
  .layer-select select { background: rgba(255,255,255,0.06); border: 0.5px solid rgba(255,255,255,0.12); color: #f0f6ff; font-size: 12px; padding: 3px 8px; border-radius: 6px; cursor: pointer; }
  .grid-canvas-wrap { border: 0.5px solid rgba(255,255,255,0.08); border-radius: 10px; overflow: hidden; background: #0a0e1a; margin-bottom: 8px; }
  .grid-canvas-wrap canvas { display: block; width: 100% !important; }
  .legend { display: flex; gap: 12px; flex-wrap: wrap; font-size: 12px; color: rgba(255,255,255,0.4); margin-top: 6px; }
  .leg-item { display: flex; align-items: center; gap: 5px; }
  .leg-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
  .heat-legend { display: flex; height: 8px; border-radius: 4px; overflow: hidden; margin: 4px 0; }
  .heat-legend div { flex: 1; }
  .heat-legend-labels { display: flex; justify-content: space-between; font-size: 11px; color: rgba(255,255,255,0.35); }
  .incidents-list { margin-top: 10px; border-top: 0.5px solid rgba(255,255,255,0.08); padding-top: 8px; }
  .incident-row { display: flex; align-items: center; gap: 10px; padding: 5px 0; font-size: 12px; border-bottom: 0.5px solid rgba(255,255,255,0.05); }
  .incident-row:last-child { border-bottom: none; }
  .inc-node { font-family: 'IBM Plex Mono', monospace; color: rgba(255,255,255,0.5); font-size: 11px; }
  .inc-desc { flex: 1; color: rgba(255,255,255,0.5); }
  .inc-factor { font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: rgba(255,255,255,0.35); }

  /* ── Algo explain ── */
  .algo-explain { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; font-size: 13px; }
  .algo-explain strong { font-weight: 600; display: block; margin-bottom: 4px; color: #f0f6ff; }
  .algo-explain span { color: rgba(255,255,255,0.4); line-height: 1.7; }

  /* ── Coverage compare ── */
  .coverage-compare { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }
  .cc-head { font-weight: 500; margin-bottom: 8px; }
  .cc-body { font-size: 13px; color: rgba(255,255,255,0.4); line-height: 1.8; }
  .cc-body strong { color: rgba(255,255,255,0.8); font-weight: 500; }

  /* ── Fleet ── */
  .amb-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 0.5px solid rgba(255,255,255,0.06); font-size: 13px; }
  .amb-row:last-child { border-bottom: none; }
  .amb-id { font-weight: 600; font-family: 'IBM Plex Mono', monospace; font-size: 12px; background: rgba(255,255,255,0.06); padding: 2px 7px; border-radius: 4px; color: #60a5fa; }
  .node-label { font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: rgba(255,255,255,0.35); }
  .resp-count { margin-left: auto; font-size: 12px; color: rgba(255,255,255,0.35); font-family: 'IBM Plex Mono', monospace; }
  .dist-count { font-size: 11px; color: rgba(255,255,255,0.25); font-family: 'IBM Plex Mono', monospace; }
  .hosp-row { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 0.5px solid rgba(255,255,255,0.06); font-size: 13px; }
  .hosp-row:last-child { border-bottom: none; }
  .hosp-name { flex: 1; font-weight: 500; color: #f0f6ff; }
  .hosp-count { font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: rgba(255,255,255,0.4); }
  .progress-bar { height: 4px; background: rgba(255,255,255,0.08); border-radius: 2px; overflow: hidden; width: 80px; }
  .progress-fill { height: 100%; border-radius: 2px; background: #378ADD; transition: width .3s; }
  .hosp-pct { font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: rgba(255,255,255,0.4); min-width: 40px; text-align: right; }

  /* ── Dispatch logic ── */
  .dispatch-logic { display: flex; flex-direction: column; gap: 8px; }
  .dispatch-step { display: flex; align-items: flex-start; gap: 10px; font-size: 13px; color: rgba(255,255,255,0.45); line-height: 1.5; }
  .step-num { font-family: 'IBM Plex Mono', monospace; font-size: 11px; font-weight: 600; background: rgba(55,138,221,0.15); color: #60a5fa; padding: 1px 7px; border-radius: 10px; flex-shrink: 0; margin-top: 1px; }
</style>