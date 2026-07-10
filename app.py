import streamlit as st
from streamlit_keplergl import keplergl_static
from keplergl import KeplerGl
import pandas as pd
import numpy as np
import json
import plotly.express as px
import plotly.graph_objects as go
from geopy.distance import geodesic
from io import StringIO
from datetime import datetime

st.set_page_config(layout="wide", page_title="GPS Analytics Visualizer")

st.title("Geo Analytics Visualizer")
st.markdown("Upload GPS or GeoJSON data to visualize points, routes, and polygons on a map.")

# ---------- SESSION STATE ----------
if "data" not in st.session_state:
    st.session_state.data = None
if "filtered" not in st.session_state:
    st.session_state.filtered = None
if "demo_loaded" not in st.session_state:
    st.session_state.demo_loaded = None


def parse_csv(file) -> pd.DataFrame:
    df = pd.read_csv(file)
    lat_cols = [c for c in df.columns if c.lower() in ("lat", "latitude", "y")]
    lon_cols = [c for c in df.columns if c.lower() in ("lon", "lng", "long", "longitude", "x")]
    if lat_cols and lon_cols:
        df.rename(columns={lat_cols[0]: "lat", lon_cols[0]: "lon"}, inplace=True)
    return df


def _extract_coords(geom: dict) -> list[tuple[float, float]]:
    gtype = geom.get("type", "")
    coords = geom.get("coordinates", [])
    if gtype == "Point":
        return [tuple(coords[:2])]
    if gtype == "MultiPoint":
        return [tuple(p[:2]) for p in coords]
    if gtype == "LineString":
        return [tuple(p[:2]) for p in coords]
    if gtype == "MultiLineString":
        return [tuple(p[:2]) for line in coords for p in line]
    if gtype == "Polygon":
        return [tuple(p[:2]) for p in coords[0]]  # exterior ring
    if gtype == "MultiPolygon":
        return [tuple(p[:2]) for poly in coords for ring in poly for p in ring]
    return []


def _geojson_to_rows(data: dict) -> list[dict]:
    features = data.get("features", data.get("data", []))
    if not features:
        return []
    rows = []
    for f in features:
        props = f.get("properties", {}).copy()
        geom = f.get("geometry", {})
        gtype = geom.get("type", "")
        points = _extract_coords(geom)
        for idx, (lon, lat) in enumerate(points):
            row = props.copy()
            row["lat"] = lat
            row["lon"] = lon
            row["vertex_index"] = idx
            row["geometry_type"] = gtype
            rows.append(row)
    return rows


def parse_json(file) -> pd.DataFrame:
    data = json.load(file)
    if isinstance(data, list):
        return pd.DataFrame(data)
    if isinstance(data, dict):
        if "features" in data or "data" in data:
            rows = _geojson_to_rows(data)
            if rows:
                return pd.DataFrame(rows)
    st.error("Unrecognised JSON structure.")
    st.stop()


def parse_geojson(file) -> pd.DataFrame:
    data = json.load(file)
    rows = _geojson_to_rows(data)
    if not rows:
        st.error("No features found in GeoJSON.")
        st.stop()
    return pd.DataFrame(rows)


def standardise_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    cols_lower = {c: c.lower() for c in df.columns}
    df.rename(columns=cols_lower, inplace=True)

    # normalise timestamp
    ts_candidates = [c for c in df.columns if c in ("timestamp", "time", "datetime", "date", "utc")]
    if ts_candidates:
        ts_col = ts_candidates[0]
        df["timestamp"] = pd.to_datetime(df[ts_col], errors="coerce")
    else:
        df["timestamp"] = pd.NaT

    # ensure lat/lon are numeric
    for col in ("lat", "latitude", "lon", "longitude", "lng"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # device id
    dev_candidates = [c for c in df.columns if c in ("device_id", "device", "id", "name", "track_id", "trip_id")]
    if dev_candidates:
        df["device_id"] = df[dev_candidates[0]].astype(str)
    else:
        df["device_id"] = "device_1"

    # speed & altitude
    for col, target in [("speed", "speed_kmh"), ("altitude", "altitude_m"), ("alt", "altitude_m")]:
        if col in df.columns:
            df[target] = pd.to_numeric(df[col], errors="coerce")

    return df


def add_distances(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "lat" not in df.columns or "lon" not in df.columns:
        return df
    df = df.copy()
    df = df.sort_values(["device_id", "timestamp"]).reset_index(drop=True)
    dists = []
    prev = None
    for _, row in df.iterrows():
        cur = (row["lat"], row["lon"])
        if prev is not None and pd.notna(row["lat"]) and pd.notna(row["lon"]):
            d = geodesic(prev, cur).kilometers
        else:
            d = 0.0
        dists.append(d)
        prev = cur
    df["dist_km"] = dists
    return df


def load_and_process(raw: pd.DataFrame):
    raw = standardise_df(raw)
    if "lat" not in raw.columns or "lon" not in raw.columns:
        st.error("Could not detect latitude/longitude columns. Ensure your file contains lat/lon fields.")
        st.stop()
    raw = raw.dropna(subset=["lat", "lon"])
    if raw.empty:
        st.error("No valid GPS points found.")
        st.stop()
    raw = add_distances(raw)
    st.session_state.data = raw
    st.session_state.filtered = raw.copy()


def load_demo(path: str):
    with open(path) as f:
        data = json.load(f)
    ext = path.rsplit(".", 1)[-1].lower()
    if ext == "csv":
        raw = parse_csv(path)
    elif "features" in data:
        raw = pd.DataFrame(_geojson_to_rows(data))
    else:
        raw = pd.DataFrame(data)
    load_and_process(raw)


# ---------- FILE UPLOAD ----------
uploaded = st.file_uploader(
    "Upload GPS file (CSV, JSON, GeoJSON)",
    type=["csv", "json", "geojson"],
)

# ---------- LOAD ----------
if uploaded is not None:
    st.session_state.demo_loaded = None
    ext = uploaded.name.rsplit(".", 1)[-1].lower()
    with st.spinner("Parsing file…"):
        if ext == "csv":
            raw = parse_csv(uploaded)
        elif ext == "geojson":
            raw = parse_geojson(uploaded)
        else:
            raw = parse_json(uploaded)
    load_and_process(raw)

if st.session_state.data is None and st.session_state.demo_loaded is None:
    st.info("Upload a GPS or GeoJSON file to get started.")
    col_a, col_b = st.columns(2)
    if col_a.button("Load demo: Points"):
        load_demo("data/geojson_output_points.json")
        st.session_state.demo_loaded = "points"
        st.rerun()
    if col_b.button("Load demo: Routes"):
        load_demo("data/geojson_output_lines.json")
        st.session_state.demo_loaded = "routes"
        st.rerun()

# ---------- SIDEBAR FILTERS ----------
if st.session_state.data is not None:
    df = st.session_state.data

    st.sidebar.header("Filters")

    devices = sorted(df["device_id"].unique())
    sel_devices = st.sidebar.multiselect("Device(s)", devices, default=list(devices))

    if df["timestamp"].notna().any():
        t_min = df["timestamp"].min().to_pydatetime()
        t_max = df["timestamp"].max().to_pydatetime()
        date_range = st.sidebar.date_input("Date range", [t_min, t_max], min_value=t_min, max_value=t_max)
        time_range = st.sidebar.slider(
            "Time of day (24h)", 0, 24, (0, 24),
        )
    else:
        date_range = None
        time_range = None

    # apply filters
    mask = df["device_id"].isin(sel_devices)
    if date_range and len(date_range) == 2:
        d0, d1 = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)
        mask &= df["timestamp"].between(d0, d1)
    if time_range:
        hour = df["timestamp"].dt.hour
        mask &= hour.between(time_range[0], time_range[1] - 1, inclusive="left")

    filtered = df[mask].copy()
    st.session_state.filtered = filtered

    # ---------- MAP ----------
    st.subheader("Route Map")
    if filtered.empty:
        st.warning("No data matches the current filters.")
    else:
        pt_data = filtered[["lat", "lon"]].dropna().copy()
        pt_data.index = pt_data.index.astype(str)

        try:
            import geopandas as gpd
            from shapely.geometry import LineString, Polygon, Point

            geoms = []
            seg_df = filtered.dropna(subset=["lat", "lon"]).sort_values("vertex_index")
            for dev, grp in seg_df.groupby("device_id"):
                coords = list(zip(grp["lon"], grp["lat"]))
                gtype = grp["geometry_type"].iloc[0] if "geometry_type" in grp.columns else "LineString"
                if gtype == "Polygon" and len(coords) >= 3:
                    geoms.append({"device_id": dev, "geometry": Polygon(coords)})
                elif gtype in ("LineString", "MultiPoint", "MultiLineString") and len(coords) >= 2:
                    geoms.append({"device_id": dev, "geometry": LineString(coords)})
                elif len(coords) == 1:
                    geoms.append({"device_id": dev, "geometry": Point(coords[0])})

            if geoms:
                gdf = gpd.GeoDataFrame(geoms, crs="EPSG:4326")
                map_1 = KeplerGl(height=500)
                map_1.add_data(data=gdf, name="routes")
            else:
                map_1 = KeplerGl(height=500)
                map_1.add_data(data=pt_data, name="routes")
        except ImportError:
            map_1 = KeplerGl(height=500)
            map_1.add_data(data=pt_data, name="routes")

        # auto-fit map to data bounds
        lats, lons = filtered["lat"].dropna(), filtered["lon"].dropna()
        if not lats.empty:
            center_lat = (lats.max() + lats.min()) / 2
            center_lon = (lons.max() + lons.min()) / 2
            lat_span = lats.max() - lats.min()
            lon_span = lons.max() - lons.min()
            max_span = max(lat_span, lon_span)
            if max_span < 0.001:
                zoom = 16
            elif max_span < 0.01:
                zoom = 14
            elif max_span < 0.1:
                zoom = 11
            elif max_span < 1:
                zoom = 9
            elif max_span < 5:
                zoom = 7
            else:
                zoom = 5
            map_1.config = {
                "version": "v1",
                "config": {
                    "mapState": {
                        "latitude": center_lat,
                        "longitude": center_lon,
                        "zoom": zoom,
                        "pitch": 0,
                        "bearing": 0,
                    }
                },
            }

        keplergl_static(map_1)

    # ---------- SUMMARY STATS ----------
    st.subheader("Summary Statistics")
    n_points = len(filtered)
    n_devices = filtered["device_id"].nunique()
    total_km = filtered["dist_km"].sum()
    avg_speed = filtered["speed_kmh"].mean() if "speed_kmh" in filtered.columns else None

    has_polygons = "geometry_type" in filtered.columns and filtered["geometry_type"].str.contains("Polygon").any()
    has_lines = "geometry_type" in filtered.columns and filtered["geometry_type"].isin(["LineString", "MultiLineString"]).any()

    if has_polygons:
        try:
            from shapely.geometry import Polygon as ShpPolygon
            areas = []
            for dev, grp in filtered.groupby("device_id"):
                coords = list(zip(grp["lon"], grp["lat"]))
                if len(coords) >= 3:
                    areas.append(ShpPolygon(coords).area * 111_320 ** 2 / 1_000_000)
            avg_area = sum(areas) / len(areas) if areas else None
        except ImportError:
            avg_area = None
    else:
        avg_area = None

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Points", f"{n_points:,}")
    col2.metric("Features", n_devices)
    col3.metric("Distance", f"{total_km:.2f} km" if total_km > 0 else "—")
    col4.metric("Avg Speed", f"{avg_speed:.2f} km/h" if avg_speed else "—")
    col5.metric("Avg Area", f"{avg_area:.2f} km²" if avg_area else "—")

    # ---------- CHARTS ----------
    st.subheader("Charts")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Speed", "Altitude", "Distance over time", "Cumulative distance", "Feature distribution"])

    if filtered.empty:
        for t in [tab1, tab2, tab3, tab4]:
            t.warning("No data to display.")
    else:
        chart_data = filtered.sort_values("timestamp").reset_index(drop=True)

        with tab1:
            if "speed_kmh" in chart_data.columns:
                fig = px.line(chart_data, x="timestamp", y="speed_kmh", color="device_id",
                              title="Speed over time", labels={"speed_kmh": "Speed (km/h)"})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No speed data available.")

        with tab2:
            if "altitude_m" in chart_data.columns:
                fig = px.line(chart_data, x="timestamp", y="altitude_m", color="device_id",
                              title="Altitude over time", labels={"altitude_m": "Altitude (m)"})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No altitude data available.")

        with tab3:
            fig = go.Figure()
            for dev in chart_data["device_id"].unique():
                dev_data = chart_data[chart_data["device_id"] == dev]
                fig.add_trace(go.Scatter(
                    x=dev_data["timestamp"], y=dev_data["dist_km"],
                    mode="lines", name=dev, stackgroup="one",
                ))
            fig.update_layout(title="Distance per segment over time", yaxis_title="Segment distance (km)")
            st.plotly_chart(fig, use_container_width=True)

        with tab4:
            cum_fig = go.Figure()
            for dev in chart_data["device_id"].unique():
                dev_data = chart_data[chart_data["device_id"] == dev].sort_values("timestamp")
                cum_fig.add_trace(go.Scatter(
                    x=dev_data["timestamp"],
                    y=dev_data["dist_km"].cumsum(),
                    mode="lines",
                    name=dev,
                ))
            cum_fig.update_layout(title="Cumulative distance over time", yaxis_title="Total distance (km)")
            st.plotly_chart(cum_fig, use_container_width=True)

        with tab5:
            if "geometry_type" in chart_data.columns:
                counts = chart_data.groupby(["device_id", "geometry_type"]).size().reset_index(name="count")
                fig = px.bar(counts, x="device_id", y="count", color="geometry_type",
                             title="Points per feature by geometry type")
                st.plotly_chart(fig, use_container_width=True)
            else:
                counts = chart_data["device_id"].value_counts().reset_index()
                counts.columns = ["device_id", "count"]
                fig = px.bar(counts, x="device_id", y="count", title="Points per feature")
                st.plotly_chart(fig, use_container_width=True)

        # ---------- RAW DATA PREVIEW ----------
        with st.expander("Raw data preview"):
            st.dataframe(filtered, use_container_width=True)

else:
    with st.expander("Expected file formats"):
        st.markdown("""
        **CSV example:**
        ```
        latitude,longitude,timestamp,device_id,speed,altitude
        40.7128,-74.0060,2025-01-01 10:00:00,dev_1,45.2,100
        40.7130,-74.0058,2025-01-01 10:01:00,dev_1,48.1,102
        ```

        **GeoJSON example (Point, LineString & Polygon):**
        ```json
        {
          "type": "FeatureCollection",
          "features": [
            {
              "type": "Feature",
              "geometry": {
                "type": "Point",
                "coordinates": [-74.0060, 40.7128]
              },
              "properties": {
                "id": "point_1",
                "speed": 45.2
              }
            },
            {
              "type": "Feature",
              "geometry": {
                "type": "LineString",
                "coordinates": [
                  [-74.0060, 40.7128],
                  [-74.0055, 40.7135],
                  [-74.0048, 40.7140]
                ]
              },
              "properties": {
                "id": "route_1"
              }
            },
            {
              "type": "Feature",
              "geometry": {
                "type": "Polygon",
                "coordinates": [[
                  [-74.0060, 40.7128],
                  [-74.0060, 40.7140],
                  [-74.0040, 40.7140],
                  [-74.0040, 40.7128],
                  [-74.0060, 40.7128]
                ]]
              },
              "properties": {
                "id": "zone_1"
              }
            }
          ]
        }
        ```
        """)
