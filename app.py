import pandas as pd
import streamlit as st

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

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.divider()

    # ── Temperature line chart ────────────────────────────────────────────────
    st.subheader(f"Temperature trend — {selected_location}")

    # Build chart DataFrame: index = startTime label, columns = MinT / MaxT
    chart_df = df_region.set_index(
        df_region["startTime"].dt.strftime("%m/%d %H:%M")
    )[["MinT", "MaxT"]].rename(columns={"MinT": "Min Temp (°C)", "MaxT": "Max Temp (°C)"})

    st.line_chart(chart_df, use_container_width=True)

    st.caption(
        f"Showing {len(df_region)} forecast period(s) for {selected_location}. "
        f"Total records in database: {len(df_all)}."
    )
