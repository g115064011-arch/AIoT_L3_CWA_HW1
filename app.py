import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from database import get_all_records, init_db, insert_records
from weather_api import fetch_weather_forecast

# ── Page configuration ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Taiwan Weather Forecast",
    page_icon="🌤️",
    layout="wide",
)


# ── Data helpers ─────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_data_from_db():
    """
    Load all forecast records from SQLite and return as a pandas DataFrame.
    Result is cached so the DB is not queried on every Streamlit re-run.
    """
    rows = get_all_records()
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([dict(r) for r in rows])

    # Convert temperature columns to numeric (they are stored as REAL but
    # come back as float already; this guard handles any edge cases).
    df["MinT"] = pd.to_numeric(df["MinT"], errors="coerce")
    df["MaxT"] = pd.to_numeric(df["MaxT"], errors="coerce")

    # Parse startTime as datetime for sorting / charting
    df["startTime"] = pd.to_datetime(df["startTime"])
    df["endTime"]   = pd.to_datetime(df["endTime"])

    return df


def run_pipeline():
    """
    Full data pipeline: initialise DB → fetch CWA API → insert records.
    Returns the number of newly inserted rows.
    """
    init_db()
    records = fetch_weather_forecast()
    if records:
        inserted = insert_records(records)
        return inserted
    return 0


# ── Coordinates for all 22 CWA counties / cities ─────────────────────────────
# Latitude / longitude for the geographic centre of each county or city.
# These are fixed reference points and do not change with forecast data.
COORDINATES = {
    "臺北市": (25.0330, 121.5654),
    "新北市": (25.0120, 121.4657),
    "桃園市": (24.9937, 121.3010),
    "臺中市": (24.1477, 120.6736),
    "臺南市": (22.9999, 120.2269),
    "高雄市": (22.6273, 120.3014),
    "基隆市": (25.1283, 121.7419),
    "新竹市": (24.8138, 120.9675),
    "嘉義市": (23.4800, 120.4491),
    "新竹縣": (24.7036, 121.1542),
    "苗栗縣": (24.5602, 120.8214),
    "彰化縣": (24.0518, 120.5161),
    "南投縣": (23.9609, 120.9718),
    "雲林縣": (23.7092, 120.4313),
    "嘉義縣": (23.4518, 120.2555),
    "屏東縣": (22.5519, 120.5487),
    "宜蘭縣": (24.7021, 121.7377),
    "花蓮縣": (23.9871, 121.6015),
    "臺東縣": (22.7972, 121.0710),
    "澎湖縣": (23.5711, 119.5793),
    "金門縣": (24.4493, 118.3767),
    "連江縣": (26.1605, 119.9497),
}


def build_map(df, selected_time):
    """
    Build a Folium map of Taiwan with one CircleMarker per county/city.

    For each location the record matching `selected_time` is used.
    If a location has no record for that exact startTime, the nearest
    available time is used instead (graceful fallback, never crashes).

    Markers are colour-coded by MaxT:
        < 20 °C  → blue
        20–28 °C → green
        28–33 °C → orange
        >= 33 °C → red

    Args:
        df (pd.DataFrame): Full forecast DataFrame from load_data_from_db().
        selected_time (pd.Timestamp): The forecast startTime chosen by the user.

    Returns:
        tuple[folium.Map, int]: The map and the number of markers added.
    """
        # For each location, select the record matching the selected forecast time.
    # If there is no exact match, use the closest available forecast time.
    snapshot_rows = []

    for location_name, group in df.groupby("locationName"):
        exact = group[group["startTime"] == selected_time]

        if not exact.empty:
            row = exact.iloc[0].copy()
        else:
            idx = (group["startTime"] - selected_time).abs().idxmin()
            row = group.loc[idx].copy()

        # Make sure locationName is preserved
        row["locationName"] = location_name
        snapshot_rows.append(row)

    snapshot = pd.DataFrame(snapshot_rows)

    # Taiwan centre, zoom level 8 shows the whole island comfortably
    taiwan_map = folium.Map(
        location=[23.8, 121.0],
        zoom_start=8,
        tiles="OpenStreetMap",
    )

    def temp_color(max_t):
        if max_t is None:
            return "gray"
        if max_t < 20:
            return "blue"
        if max_t < 28:
            return "green"
        if max_t < 33:
            return "orange"
        return "red"

    markers_added = 0
    for _, row in snapshot.iterrows():
        name   = row["locationName"]
        coords = COORDINATES.get(name)
        if coords is None:
            continue   # skip any location without known coordinates

        max_t  = row["MaxT"]
        min_t  = row["MinT"]
        wx     = row["Wx"]
        start  = (
            row["startTime"].strftime("%Y-%m-%d %H:%M")
            if pd.notna(row["startTime"]) else "—"
        )
        end = (
            row["endTime"].strftime("%Y-%m-%d %H:%M")
            if pd.notna(row["endTime"]) else "—"
        )

        # Guard against NaN temperatures (show "N/A" gracefully)
        min_t_str = f"{min_t:.0f} °C" if pd.notna(min_t) else "N/A"
        max_t_str = f"{max_t:.0f} °C" if pd.notna(max_t) else "N/A"
        label_t   = f"{max_t:.0f}°" if pd.notna(max_t) else "?"
        color     = temp_color(max_t if pd.notna(max_t) else None)

        popup_html = f"""
        <div style="font-family:sans-serif; min-width:150px;">
            <b style="font-size:14px;">{name}</b><br>
            <hr style="margin:4px 0;">
            🌤 {wx}<br>
            🌡 {min_t_str} — {max_t_str}<br>
            🕐 {start}<br>
            <span style="color:#888;font-size:11px;">until {end}</span>
        </div>
        """

        folium.CircleMarker(
            location=coords,
            radius=18,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.55,
            tooltip=name,
            popup=folium.Popup(popup_html, max_width=240),
        ).add_to(taiwan_map)

        # Add a text label inside the circle
        folium.Marker(
            location=coords,
            icon=folium.DivIcon(
                html=f'<div style="font-size:9px;font-weight:bold;color:#222;'
                     f'text-align:center;line-height:1.2;margin-top:-4px;">'
                     f'{name}<br>{label_t}</div>',
                icon_size=(60, 30),
                icon_anchor=(30, 15),
            ),
        ).add_to(taiwan_map)

        markers_added += 1

    return taiwan_map, markers_added


# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Controls")

    refresh = st.button("Refresh data from CWA API", use_container_width=True)
    if refresh:
        with st.spinner("Fetching latest forecast from CWA API..."):
            inserted = run_pipeline()
            load_data_from_db.clear()   # invalidate cache after new insert
        if inserted > 0:
            st.success(f"Inserted {inserted} new records.")
        else:
            st.info("Data is already up to date. No new records inserted.")

    st.divider()
    st.caption("Data source: CWA Open Data API  \nEndpoint: F-C0032-001")


# ── Main area ─────────────────────────────────────────────────────────────────

st.title("🌤️ Taiwan Weather Forecast")
st.caption("36-hour forecast for all Taiwan counties and cities — sourced from CWA Open Data")

# ── Bootstrap: make sure DB exists and has data ───────────────────────────────
init_db()
df_all = load_data_from_db()

if df_all.empty:
    st.info("No forecast data found in the database. Click **Refresh data from CWA API** in the sidebar to fetch data.")
    with st.spinner("Auto-fetching initial data..."):
        run_pipeline()
        load_data_from_db.clear()
        df_all = load_data_from_db()

# ── Region selector ───────────────────────────────────────────────────────────
if not df_all.empty:
    locations = sorted(df_all["locationName"].unique().tolist())

    selected_location = st.selectbox(
        label="Select a region (縣市):",
        options=locations,
        index=0,
    )

    # Filter to selected region, sorted by startTime
    df_region = (
        df_all[df_all["locationName"] == selected_location]
        .sort_values("startTime")
        .reset_index(drop=True)
    )

    st.divider()

    # ── Forecast table ────────────────────────────────────────────────────────
    st.subheader(f"Forecast table — {selected_location}")

    display_df = df_region[["locationName", "startTime", "endTime", "Wx", "MinT", "MaxT"]].copy()
    display_df["startTime"] = display_df["startTime"].dt.strftime("%Y-%m-%d %H:%M")
    display_df["endTime"]   = display_df["endTime"].dt.strftime("%Y-%m-%d %H:%M")
    display_df.columns      = ["Location", "Start Time", "End Time", "Weather", "Min Temp (°C)", "Max Temp (°C)"]

    st.dataframe(display_df, width="stretch", hide_index=True)

    st.divider()

    # ── Temperature line chart ────────────────────────────────────────────────
    st.subheader(f"Temperature trend — {selected_location}")

    # Build chart DataFrame: index = startTime label, columns = MinT / MaxT
    chart_df = df_region.set_index(
        df_region["startTime"].dt.strftime("%m/%d %H:%M")
    )[["MinT", "MaxT"]].rename(columns={"MinT": "Min Temp (°C)", "MaxT": "Max Temp (°C)"})

    st.line_chart(chart_df, width="stretch")

    st.caption(
        f"Showing {len(df_region)} forecast period(s) for {selected_location}. "
        f"Total records in database: {len(df_all)}."
    )

    # ── Taiwan weather map ────────────────────────────────────────────────────
    st.divider()
    st.subheader("Taiwan Weather Map")

    # Build the list of distinct forecast startTimes available in the database.
    # Sorted ascending so the earliest period is the default (index 0).
    available_times = sorted(df_all["startTime"].unique().tolist())

    # Format them as human-readable strings for the dropdown label.
    time_labels = [
        pd.Timestamp(t).strftime("%Y-%m-%d %H:%M") for t in available_times
    ]
    time_label_to_ts = dict(zip(time_labels, available_times))

    selected_label = st.selectbox(
        label="Select forecast period for map:",
        options=time_labels,
        index=0,
        key="map_time_selector",
        help="Choose which 12-hour forecast window to display on the map.",
    )
    selected_time = pd.Timestamp(time_label_to_ts[selected_label])

    st.info(
        f"Map showing forecast period: **{selected_label}** "
        f"— {selected_time.strftime('%A, %B %d %Y')}  "
        f"{'(Morning)' if selected_time.hour < 12 else '(Evening/Night)' if selected_time.hour >= 18 else '(Afternoon)'}"
    )
    st.caption(
        "Each circle shows the forecast for that county/city in the selected period. "
        "Click a marker to see details. Colour: 🔵 <20°C  🟢 20-28°C  🟠 28-33°C  🔴 ≥33°C"
    )

    taiwan_map, num_markers = build_map(df_all, selected_time)

    st_folium(
        taiwan_map,
        width="stretch",
        height=560,
        returned_objects=[],   # we don't need click callbacks
        key=f"folium_map_{selected_label}",  # force re-render when time changes
    )

    st.caption(f"Map shows {num_markers} location marker(s) for period starting {selected_label}.")
