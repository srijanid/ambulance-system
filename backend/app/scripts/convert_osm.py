import osmnx as ox
from pathlib import Path
import networkx as nx

# Use absolute path
SCRIPT_DIR = Path(__file__).parent.absolute()
BASE_DIR = SCRIPT_DIR.parent  # backend/app
GRAPHML_PATH = BASE_DIR / "data" / "processed" / "eastern-zone.graphml"

# Download Kolkata and surrounding areas only
CITIES = [
    "Kolkata, West Bengal, India",
]

# Bounding box around Kolkata (more manageable)
# ~50km radius from Kolkata center
KOLKATA_BBOX = (22.65, 22.45, 88.50, 88.20)  # (north, south, east, west)

print("Fetching map data from OpenStreetMap...")

try:
    # Check if GraphML already exists to avoid re-downloading
    if GRAPHML_PATH.exists():
        print("Step 1: Loading existing graph from cache...")
        G = ox.load_graphml(str(GRAPHML_PATH))
        print(f"✓ Loaded cached graph: {len(G.nodes)} nodes, {len(G.edges)} edges")
    else:
        # Try PBF approach first (if file exists) - MUCH faster
        PBF_PATH = BASE_DIR / "data" / "maps" / "eastern-zone-latest.osm.pbf"
        
        if PBF_PATH.exists():
            print("Step 1: Loading from PBF file (fastest method)...")
            try:
                G = ox.graph_from_file(
                    str(PBF_PATH),
                    network_type="drive",
                    simplify=True
                )
                print(f"✓ Loaded from PBF: {len(G.nodes)} nodes, {len(G.edges)} edges")
            except Exception as pbf_err:
                print(f"  PBF loading failed: {pbf_err}, falling back to cities...")
                G = None
        else:
            G = None
        
        # Fall back to city-based download if PBF not available or failed
        if G is None:
            print("Step 1: Downloading graph for Kolkata & surroundings...")
            try:
                # Try city name first
                print("  Attempting city-based download...")
                G = ox.graph_from_place(
                    CITIES[0],
                    network_type="drive",
                    simplify=True
                )
                print(f"✓ Downloaded from place: {len(G.nodes)} nodes, {len(G.edges)} edges")
            except Exception as city_err:
                print(f"  City download failed: {city_err}")
                print("  Trying bounding box approach...")
                try:
                    G = ox.graph_from_bbox(
                        KOLKATA_BBOX,
                        network_type="drive",
                        simplify=True,
                        truncate_by_edge=True
                    )
                    print(f"✓ Downloaded from bbox: {len(G.nodes)} nodes, {len(G.edges)} edges")
                except Exception as bbox_err:
                    raise Exception(f"Both methods failed! City: {city_err}, Bbox: {bbox_err}")

    print("Step 2: Projecting graph...")
    G = ox.project_graph(G)

    GRAPHML_PATH.parent.mkdir(parents=True, exist_ok=True)

    print("Step 3: Saving GraphML...")
    ox.save_graphml(G, str(GRAPHML_PATH))

    print(f"✓ Nodes: {len(G.nodes)} | Edges: {len(G.edges)}")
    print(f"✓ Saved GraphML at: {GRAPHML_PATH}")

    print("DONE ✔")

except Exception as e:
    print(f"✗ Error: {e}")




# import os
# import osmnx as ox

# # -------------------------------------------------
# # BASE PATH = backend/app
# # -------------------------------------------------

# BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # backend/app

# PBF_PATH = os.path.join(
#     BASE_DIR,
#     "data",
#     "maps",
#     "eastern-zone-latest.osm.pbf"
# )

# GRAPHML_PATH = os.path.join(
#     BASE_DIR,
#     "data",
#     "processed",
#     "eastern-zone.graphml"
# )

# print("Converting PBF → GraphML...")

# # -------------------------------------------------
# # LOAD PBF
# # -------------------------------------------------
# G = ox.graph_from_file(
#     PBF_PATH,
#     network_type="drive",
#     simplify=True
# )

# # -------------------------------------------------
# # SAVE GRAPHML
# # -------------------------------------------------
# ox.save_graphml(G, GRAPHML_PATH)

# print("Saved GraphML at:", GRAPHML_PATH)