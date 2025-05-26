import streamlit as st
import osmnx as ox
import networkx as nx
import folium
from streamlit_folium import st_folium
from math import sqrt

st.set_page_config(page_title="Emergency Route Optimization", layout="wide")
st.title("Emergency Route Optimization")

# Predefined emergency service types and destinations
service_type = st.selectbox("Select Emergency Service", ["Ambulance", "Fire Brigade"])

# Different destinations for each service
if service_type == "Ambulance":
    destinations = {
        "Max Hospital": (30.3220, 78.0280),
        "Doon Hospital": (30.3310, 78.0400),
        "Government Hospital": (30.3450, 78.0600),
        "City Hospital": (30.3600, 78.0700),
        "Health Care Center": (30.3500, 78.0500),
    }
elif service_type == "Fire Brigade":
    destinations = {
        "Fire Station 1": (30.3260, 78.0450),
        "Fire Station 2": (30.3380, 78.0580),
        "Emergency Fire Base": (30.3480, 78.0650),
    }

# Manual input toggle
manual_input = st.checkbox("Enter coordinates manually")

if manual_input:
    lat = st.number_input("Enter destination latitude", value=30.3500, format="%.6f")
    lon = st.number_input("Enter destination longitude", value=78.0500, format="%.6f")
    end_coords = (lat, lon)
    selected_place = f"Manual Entry ({lat}, {lon})"
else:
    selected_place = st.selectbox("Select Destination:", list(destinations.keys()))
    end_coords = destinations[selected_place]

# Starting point (e.g., current ambulance/firetruck location)
start_coords = (30.3165, 78.0322)

def euclidean_heuristic(u, v, G):
    x1, y1 = G.nodes[u]['x'], G.nodes[u]['y']
    x2, y2 = G.nodes[v]['x'], G.nodes[v]['y']
    return sqrt((x1 - x2)**2 + (y1 - y2)**2)

@st.cache_data(show_spinner=True)
def get_routes_and_map(start_coords, end_coords):
    G = ox.graph_from_point(start_coords, dist=3000, network_type='drive')

    start_node = ox.distance.nearest_nodes(G, start_coords[1], start_coords[0])
    end_node = ox.distance.nearest_nodes(G, end_coords[1], end_coords[0])

    # Compute shortest path (default)
    route1 = nx.astar_path(G, start_node, end_node,
                           heuristic=lambda u, v: euclidean_heuristic(u, v, G),
                           weight='length')

    # Simulate traffic on some edges
    traffic_edges = set()
    for u, v, k, data in G.edges(keys=True, data=True):
        if data.get('length', 0) > 150:  # assume edges > 150m are "congested"
            G[u][v][k]['length'] *= 3
            traffic_edges.add((u, v, k))

    # Recalculate path with traffic
    route2 = nx.astar_path(G, start_node, end_node,
                           heuristic=lambda u, v: euclidean_heuristic(u, v, G),
                           weight='length')

    # Build map
    route_coords1 = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route1]
    route_coords2 = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in route2]

    m = folium.Map(location=route_coords1[0], zoom_start=14)

    folium.PolyLine(route_coords1, color="green", weight=6, opacity=0.8, tooltip="Optimal Route").add_to(m)

    if route1 != route2:
        folium.PolyLine(route_coords2, color="red", weight=4, opacity=0.8, dash_array="5,10", tooltip="Traffic Route").add_to(m)

    folium.Marker(route_coords1[0], popup="Start", icon=folium.Icon(color="blue")).add_to(m)
    folium.Marker(route_coords1[-1], popup=selected_place, icon=folium.Icon(color="red")).add_to(m)

    return m, G, route1, route2


m, G, route1, route2 = get_routes_and_map(start_coords, end_coords)

st.write(f"Routing from {start_coords} to {selected_place} at {end_coords}")
st_data = st_folium(m, width=700, height=500)

# Estimate lengths and times
main_length = sum(G[u][v][0]['length'] for u, v in zip(route1[:-1], route1[1:]))
alt_length = sum(G[u][v][0]['length'] for u, v in zip(route2[:-1], route2[1:]))

main_speed = 8.33  # 30 km/h = 8.33 m/s
alt_speed = 5.56   # 20 km/h = 5.56 m/s

main_time = main_length / main_speed / 60  # in minutes
alt_time = alt_length / alt_speed / 60

# Display route info
st.markdown("### 📊 Route Comparison")
st.success(f"**Chosen Route Length:** {main_length:.2f} meters")
st.info(f"**Alternative Route Length:** {alt_length:.2f} meters")

col1, col2 = st.columns(2)

with col1:
    st.success("**Main Route (Optimized)**")
    st.write(f"🚗 Length: **{main_length:.2f} meters**")
    st.write(f"⏱️ Estimated Time: **{main_time:.1f} minutes**")

with col2:
    st.warning("**Alternative Route (With Traffic)**")
    st.write(f"🚗 Length: **{alt_length:.2f} meters**")
    st.write(f"⏱️ Estimated Time: **{alt_time:.1f} minutes**")
