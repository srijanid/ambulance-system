<script lang="ts">
    import { onMount } from "svelte";
    import { browser } from "$app/environment";

    let mapContainer: HTMLDivElement;
    let map: any;
    let userLocation: { lat: number; lng: number } | null = null;

    // Function to get user's current location
    async function getUserLocation(): Promise<{
        lat: number;
        lng: number;
    } | null> {
        return new Promise((resolve) => {
            if (!navigator.geolocation) {
                console.error("Geolocation is not supported by this browser.");
                resolve(null);
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const { latitude, longitude } = position.coords;
                    resolve({ lat: latitude, lng: longitude });
                },
                (error) => {
                    console.error("Error getting location:", error);
                    resolve(null);
                },
            );
        });
    }

    onMount(async () => {
        // Only run on client side
        if (!browser) return;

        // Dynamically import Leaflet to avoid SSR issues
        const L = (await import("leaflet")).default;

        // Get user location
        userLocation = await getUserLocation();
        const defaultLat = userLocation?.lat || 40.7128; // Default to NYC if no location
        const defaultLng = userLocation?.lng || -74.006;

        // Initialize the map
        map = L.map(mapContainer).setView([defaultLat, defaultLng], 13);

        // Add OpenStreetMap tiles
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "© OpenStreetMap contributors",
        }).addTo(map);

        // Add user location marker if available
        if (userLocation) {
            L.marker([userLocation.lat, userLocation.lng], {
                icon: L.divIcon({
                    html: "📍",
                    className: "custom-div-icon user-location",
                    iconSize: [30, 30],
                    iconAnchor: [15, 15],
                }),
            })
                .addTo(map)
                .bindPopup("Your Location")
                .openPopup();
        }
    });

    // Function to recenter map on user location
    function centerOnUser() {
        if (map && userLocation) {
            map.setView([userLocation.lat, userLocation.lng], 15);
        }
    }
</script>

<svelte:head>
    <link
        rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    />
    <title>Map - Ambulance App</title>
</svelte:head>

<div class="map-container">
    <div class="map-header">
        <h1>Map View</h1>
        <div class="controls">
            <button
                on:click={centerOnUser}
                disabled={!userLocation}
                class="btn-primary"
            >
                📍 Center on Me
            </button>
        </div>
    </div>

    <div class="map-wrapper">
        <div bind:this={mapContainer} class="map"></div>
    </div>

    <div class="instructions">
        <p>🔍 Zoom in/out using mouse wheel or map controls</p>
        <p>📍 Click the "Center on Me" button to view your location</p>
    </div>
</div>

<style>
    .map-container {
        height: 100vh;
        display: flex;
        flex-direction: column;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
            sans-serif;
    }

    .map-header {
        background: #1e40af;
        color: white;
        padding: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .map-header h1 {
        margin: 0;
        font-size: 1.5rem;
        font-weight: 600;
    }

    .controls {
        display: flex;
        align-items: center;
        gap: 1rem;
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
        transition: background-color 0.2s;
    }

    .btn-primary:hover:not(:disabled) {
        background: #2563eb;
    }

    .btn-primary:disabled {
        background: #6b7280;
        cursor: not-allowed;
    }

    .map-wrapper {
        flex: 1;
        position: relative;
        display: flex;
    }

    .map {
        flex: 1;
        height: 100%;
    }

    .instructions {
        background: #f9fafb;
        padding: 1rem;
        border-top: 1px solid #e5e7eb;
        font-size: 0.875rem;
        color: #6b7280;
    }

    .instructions p {
        margin: 0.25rem 0;
    }

    /* Custom marker styles */
    :global(.custom-div-icon) {
        background: none;
        border: none;
        font-size: 24px;
        text-align: center;
        line-height: 30px;
        filter: drop-shadow(2px 2px 4px rgba(0, 0, 0, 0.3));
    }

    :global(.user-location) {
        animation: bounce 2s infinite;
    }

    @keyframes bounce {
        0%,
        20%,
        50%,
        80%,
        100% {
            transform: translateY(0);
        }
        40% {
            transform: translateY(-10px);
        }
        60% {
            transform: translateY(-5px);
        }
    }

    /* Popup styles */
    :global(.leaflet-popup-content) {
        margin: 8px 12px;
        line-height: 1.4;
    }

    :global(.popup-content h3) {
        margin: 0 0 0.5rem 0;
        color: #1f2937;
        font-size: 1rem;
        font-weight: 600;
    }

    :global(.popup-content p) {
        margin: 0.25rem 0;
        font-size: 0.875rem;
        color: #4b5563;
    }

    /* Responsive design */
    @media (max-width: 768px) {
        .map-header {
            flex-direction: column;
            gap: 0.75rem;
            text-align: center;
        }
    }
</style>
