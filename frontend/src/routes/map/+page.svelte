<script lang="ts">
    import { onMount } from "svelte";
    import { browser } from "$app/environment";

    let mapContainer: HTMLDivElement;
    let map: any;

    let L: any;

    let routeLayer: any = null;
    let facilityMarkers: any[] = [];

    let clickMode = false;
    let clickedPoints: any[] = [];

    onMount(async () => {
        if (!browser) return;

        L = (await import("leaflet")).default;

        map = L.map(mapContainer).setView([22.5726, 88.3639], 12);

        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "© OpenStreetMap contributors",
        }).addTo(map);

        // LOAD ROAD GRAPH

        const res = await fetch("http://127.0.0.1:8000/osm/graph");

        const graphData = await res.json();

        graphData.edges.forEach((edge: any) => {
            L.polyline(edge.coordinates, {
                color: "#666",
                weight: 1,
                opacity: 0.4,
            }).addTo(map);
        });

        // CLICK EVENTS

        map.on("click", async (e: any) => {
            if (!clickMode) return;

            clickedPoints.push(e.latlng);

            L.marker(e.latlng).addTo(map);

            if (clickedPoints.length === 2) {
                const start = clickedPoints[0];
                const end = clickedPoints[1];

                const response = await fetch(
                    `http://127.0.0.1:8000/osm/nearest-route?start_lat=${start.lat}&start_lng=${start.lng}&end_lat=${end.lat}&end_lng=${end.lng}`,
                );

                const data = await response.json();

                if (routeLayer) {
                    map.removeLayer(routeLayer);
                }

                routeLayer = L.polyline(data.coordinates, {
                    color: "red",
                    weight: 5,
                }).addTo(map);

                map.fitBounds(routeLayer.getBounds());

                clickedPoints = [];
                clickMode = false;
            }
        });
    });

    // -----------------------------------------------------
    // A*
    // -----------------------------------------------------

    function enableAstarMode() {
        clickedPoints = [];

        clickMode = true;

        alert("Click 2 points on map for A* routing");
    }

    // -----------------------------------------------------
    // PSO
    // -----------------------------------------------------

    let psoLayers: any[] = [];

    async function showPSO() {
        const response = await fetch("http://127.0.0.1:8000/osm/facilities");

        const data = await response.json();

        const L = (await import("leaflet")).default;

        // CLEAR OLD LAYERS
        psoLayers.forEach((layer) => {
            map.removeLayer(layer);
        });

        psoLayers = [];

        // ---------------------------------------------------
        // DRAW FACILITIES
        // ---------------------------------------------------

        data.facilities.forEach((facility: any, index: number) => {
            // FACILITY MARKER
            const marker = L.marker([facility.lat, facility.lng], {
                icon: L.divIcon({
                    html: "🚑",
                    className: "ambulance-icon",
                    iconSize: [30, 30],
                }),
            }).addTo(map).bindPopup(`
            <b>PSO Ambulance Hub ${index + 1}</b><br>
            Coverage Radius: 800m
        `);

            psoLayers.push(marker);

            // ---------------------------------------------------
            // COVERAGE CIRCLE
            // ---------------------------------------------------

            const circle = L.circle([facility.lat, facility.lng], {
                radius: 800,
                color: "lime",
                fillColor: "#00ff00",
                fillOpacity: 0.15,
                weight: 2,
            }).addTo(map);

            psoLayers.push(circle);

            // ---------------------------------------------------
            // RANDOM DEMAND POINTS
            // ---------------------------------------------------

            for (let i = 0; i < 5; i++) {
                const offsetLat = facility.lat + (Math.random() - 0.5) * 0.01;

                const offsetLng = facility.lng + (Math.random() - 0.5) * 0.01;

                // DEMAND POINT
                const demand = L.circleMarker([offsetLat, offsetLng], {
                    radius: 5,
                    color: "red",
                    fillColor: "red",
                    fillOpacity: 1,
                })
                    .addTo(map)
                    .bindPopup("Emergency Demand Point");

                psoLayers.push(demand);

                // CONNECTION LINE
                const line = L.polyline(
                    [
                        [facility.lat, facility.lng],
                        [offsetLat, offsetLng],
                    ],
                    {
                        color: "yellow",
                        dashArray: "5,5",
                        weight: 1,
                    },
                ).addTo(map);

                psoLayers.push(line);
            }
        });

        alert("PSO Optimization Visualized");
    }
</script>

<svelte:head>
    <link
        rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    />
</svelte:head>

<div class="container">
    <div class="topbar">
        <button on:click={enableAstarMode}> A* Route </button>

        <button on:click={showPSO}> PSO Facilities </button>
    </div>

    <div bind:this={mapContainer} class="map"></div>
</div>

<!-- <script lang="ts">
    import { onMount } from "svelte";
    import { browser } from "$app/environment";

    let mapContainer: HTMLDivElement;
    let map: any;

    let userLocation: { lat: number; lng: number } | null = null;

    let routeLayer: any = null;
    let facilityMarkers: any[] = [];

    let astarMode = false;
    let selectedPoints: any[] = [];

    // ------------------------------------------------------------------
    // USER LOCATION
    // ------------------------------------------------------------------

    async function getUserLocation(): Promise<{
        lat: number;
        lng: number;
    } | null> {
        return new Promise((resolve) => {
            if (!navigator.geolocation) {
                resolve(null);
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    resolve({
                        lat: position.coords.latitude,
                        lng: position.coords.longitude,
                    });
                },
                () => resolve(null),
            );
        });
    }

    // ------------------------------------------------------------------
    // LOAD MAP
    // ------------------------------------------------------------------

    onMount(async () => {
        if (!browser) return;

        const L = (await import("leaflet")).default;

        // Kolkata
        map = L.map(mapContainer).setView([22.5726, 88.3639], 12);

        // OSM Tiles
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "© OpenStreetMap contributors",
        }).addTo(map);

        // User location
        userLocation = await getUserLocation();

        if (userLocation) {
            L.marker([userLocation.lat, userLocation.lng])
                .addTo(map)
                .bindPopup("Your Location");
        }

        // --------------------------------------------------------------
        // LOAD GRAPHML ROADS
        // --------------------------------------------------------------

        const res = await fetch("http://127.0.0.1:8000/osm/graph");

        const graphData = await res.json();

        graphData.edges.forEach((edge: any) => {
            L.polyline(edge.coordinates, {
                color: "#666",
                weight: 1,
                opacity: 0.5,
            }).addTo(map);
        });

        // --------------------------------------------------------------
        // CLICK EVENT FOR A*
        // --------------------------------------------------------------

        map.on("click", async (e: any) => {
            if (!astarMode) return;

            selectedPoints.push({
                lat: e.latlng.lat,
                lng: e.latlng.lng,
            });

            // marker
            L.marker([e.latlng.lat, e.latlng.lng]).addTo(map);

            // wait for 2 clicks
            if (selectedPoints.length === 2) {
                const start = selectedPoints[0];
                const end = selectedPoints[1];

                const response = await fetch(
                    `http://127.0.0.1:8000/osm/nearest-route?start_lat=${start.lat}&start_lng=${start.lng}&end_lat=${end.lat}&end_lng=${end.lng}`,
                );

                const data = await response.json();

                if (routeLayer) {
                    map.removeLayer(routeLayer);
                }

                routeLayer = L.polyline(data.coordinates, {
                    color: "red",
                    weight: 5,
                }).addTo(map);

                map.fitBounds(routeLayer.getBounds());

                astarMode = false;
                selectedPoints = [];
            }
        });
    });

    // ------------------------------------------------------------------
    // CENTER USER
    // ------------------------------------------------------------------

    function centerOnUser() {
        if (map && userLocation) {
            map.setView([userLocation.lat, userLocation.lng], 15);
        }
    }

    // ------------------------------------------------------------------
    // ENABLE A*
    // ------------------------------------------------------------------

    async function showAstar() {
        astarMode = true;
        selectedPoints = [];

        alert("Click 2 points on map for A* routing");
    }

    // ------------------------------------------------------------------
    // SHOW PSO FACILITIES
    // ------------------------------------------------------------------

    async function showPSO() {
        const response = await fetch(
            "http://127.0.0.1:8000/osm/facilities",
        );

        const data = await response.json();

        const L = (await import("leaflet")).default;

        facilityMarkers.forEach((m) => map.removeLayer(m));

        facilityMarkers = [];

        data.facilities.forEach((f: any) => {
            const marker = L.circleMarker([f.lat, f.lng], {
                radius: 8,
                color: "lime",
                fillColor: "lime",
                fillOpacity: 1,
            })
                .addTo(map)
                .bindPopup("PSO Optimized Facility");

            facilityMarkers.push(marker);
        });
    }
</script>

<svelte:head>
    <link
        rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    />

    <title>Smart Ambulance Map</title>
</svelte:head>

<div class="map-container">
    <div class="map-header">
        <h1>Smart Ambulance Dispatch System</h1>

        <div class="controls">
            <button
                on:click={centerOnUser}
                disabled={!userLocation}
                class="btn-primary"
            >
                📍 Center on Me
            </button>

            <button on:click={showAstar} class="btn-primary">
                A* Route
            </button>

            <button on:click={showPSO} class="btn-primary">
                PSO Facilities
            </button>
        </div>
    </div>

    <div class="map-wrapper">
        <div bind:this={mapContainer} class="map"></div>
    </div>

    <div class="instructions">
        <p>Click A* Route → select 2 points on map</p>
        <p>PSO button shows optimized ambulance facility placement</p>
    </div>
</div>

<style>
    .map-container {
        height: 100vh;
        display: flex;
        flex-direction: column;
        font-family:
            -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .map-header {
        background: #1e40af;
        color: white;
        padding: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        z-index: 1000;
    }

    .controls {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
    }

    .btn-primary {
        background: #3b82f6;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.375rem;
        cursor: pointer;
        font-size: 0.875rem;
        font-weight: 500;
    }

    .btn-primary:hover {
        background: #2563eb;
    }

    .btn-primary:disabled {
        background: #6b7280;
        cursor: not-allowed;
    }

    .map-wrapper {
        flex: 1;
    }

    .map {
        width: 100%;
        height: 100%;
    }

    .instructions {
        padding: 1rem;
        background: #f3f4f6;
        font-size: 0.9rem;
    }

    @media (max-width: 768px) {
        .map-header {
            flex-direction: column;
            gap: 1rem;
        }
    }
</style> -->

<style>
    .container {
        height: 100vh;
        width: 100%;
    }

    .topbar {
        position: absolute;
        z-index: 1000;
        top: 10px;
        left: 10px;
        display: flex;
        gap: 10px;
    }

    button {
        padding: 10px 16px;
        border: none;
        border-radius: 8px;
        background: #2563eb;
        color: white;
        cursor: pointer;
        font-weight: 600;
    }

    .map {
        width: 100%;
        height: 100vh;
    }
</style>
