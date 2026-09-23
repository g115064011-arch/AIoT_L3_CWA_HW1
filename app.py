import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from database import get_all_records, init_db, insert_records
from weather_api import fetch_weather_forecast


# ── Page configuration ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="台灣天氣預報",
    page_icon="🌤️",
    layout="wide",
)


# ── Styling ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .stApp {
        background: #F4F9FD;
    }

    .block-container {
        max-width: 1500px;
        padding-top: 1.8rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        color: #174A7E;
    }

    h1 {
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 0.15rem;
    }

    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E3EDF5;
        padding: 18px 20px;
        border-radius: 18px;
        box-shadow: 0 6px 18px rgba(34, 82, 120, 0.06);
    }

    div[data-testid="stMetricLabel"] {
        color: #57748E;
        font-weight: 600;
    }

    div[data-testid="stMetricValue"] {
        color: #173F63;
        font-weight: 800;
    }

    div[data-baseweb="select"] > div {
        border-radius: 12px;
        border-color: #D9E8F3;
        background: #FFFFFF;
    }

    section[data-testid="stSidebar"] {
        background: #EAF4FB;
        border-right: 1px solid #DCEBF5;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid #E3EDF5;
        background: #FFFFFF;
    }

    .section-card {
        background: #FFFFFF;
        border: 1px solid #E3EDF5;
        border-radius: 18px;
        padding: 1rem 1.1rem;
        box-shadow: 0 6px 18px rgba(34, 82, 120, 0.05);
        margin-bottom: 0.8rem;
    }

    .hero-subtitle {
        color: #66839A;
        font-size: 0.98rem;
        margin-top: -0.25rem;
        margin-bottom: 1rem;
    }

    .soft-note {
        background: #EAF5FD;
        border: 1px solid #D5EAF8;
        border-radius: 14px;
        padding: 0.7rem 0.9rem;
        color: #315D7A;
        margin: 0.4rem 0 0.9rem 0;
    }

    .stButton > button {
        border-radius: 12px;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Data helpers ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data_from_db():
    rows = get_all_records()
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([dict(r) for r in rows])

    df["MinT"] = pd.to_numeric(df["MinT"], errors="coerce")
    df["MaxT"] = pd.to_numeric(df["MaxT"], errors="coerce")
    df["startTime"] = pd.to_datetime(df["startTime"])
    df["endTime"] = pd.to_datetime(df["endTime"])

    return df


def run_pipeline():
    init_db()
    records = fetch_weather_forecast()
    if records:
        return insert_records(records)
    return 0


def nearest_record(df_region, selected_time):
    exact = df_region[df_region["startTime"] == selected_time]
    if not exact.empty:
        return exact.iloc[0]

    idx = (df_region["startTime"] - selected_time).abs().idxmin()
    return df_region.loc[idx]


# ── Coordinates for all 22 CWA counties / cities ─────────────────────────────
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
    # Avoid groupby().apply() compatibility issues by building rows explicitly.
    snapshot_rows = []

    for location_name, group in df.groupby("locationName"):
        exact = group[group["startTime"] == selected_time]

        if not exact.empty:
            row = exact.iloc[0].copy()
        else:
            idx = (group["startTime"] - selected_time).abs().idxmin()
            row = group.loc[idx].copy()

        row["locationName"] = location_name
        snapshot_rows.append(row)

    snapshot = pd.DataFrame(snapshot_rows)

    taiwan_map = folium.Map(
        location=[23.8, 121.0],
        zoom_start=8,
        tiles="OpenStreetMap",
    )

    def temp_color(max_t):
        if max_t is None or pd.isna(max_t):
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
        name = row["locationName"]
        coords = COORDINATES.get(name)

        if coords is None:
            continue

        max_t = row["MaxT"]
        min_t = row["MinT"]
        wx = row["Wx"]

        start = (
            row["startTime"].strftime("%Y-%m-%d %H:%M")
            if pd.notna(row["startTime"])
            else "—"
        )
        end = (
            row["endTime"].strftime("%Y-%m-%d %H:%M")
            if pd.notna(row["endTime"])
            else "—"
        )

        min_t_str = f"{min_t:.0f} °C" if pd.notna(min_t) else "N/A"
        max_t_str = f"{max_t:.0f} °C" if pd.notna(max_t) else "N/A"
        label_t = f"{max_t:.0f}°" if pd.notna(max_t) else "?"
        color = temp_color(max_t)

        popup_html = f"""
        <div style="font-family:sans-serif; min-width:170px;">
            <b style="font-size:15px;">📍 {name}</b><br>
            <hr style="margin:5px 0;">
            🌤️ {wx}<br>
            🌡️ {min_t_str} — {max_t_str}<br>
            🕒 {start}<br>
            <span style="color:#7a7a7a;font-size:11px;">至 {end}</span>
        </div>
        """

        folium.CircleMarker(
            location=coords,
            radius=18,
            color=color,
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.58,
            tooltip=f"{name}｜{wx}",
            popup=folium.Popup(popup_html, max_width=260),
        ).add_to(taiwan_map)

        folium.Marker(
            location=coords,
            icon=folium.DivIcon(
                html=(
                    '<div style="font-size:9px;font-weight:700;color:#1F2D3D;'
                    'text-align:center;line-height:1.2;margin-top:-4px;">'
                    f"{name}<br>{label_t}</div>"
                ),
                icon_size=(60, 30),
                icon_anchor=(30, 15),
            ),
        ).add_to(taiwan_map)

        markers_added += 1

    return taiwan_map, markers_added


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 控制面板")
    st.caption("更新資料與查看資料來源")

    refresh = st.button("🔄 從 CWA API 更新資料", use_container_width=True)

    if refresh:
        with st.spinner("正在取得最新天氣預報..."):
            inserted = run_pipeline()
            load_data_from_db.clear()

        if inserted > 0:
            st.success(f"已新增 {inserted} 筆資料。")
        else:
            st.info("目前資料已是最新狀態。")

    st.divider()
    st.markdown("### 📡 資料來源")
    st.caption("中央氣象署 CWA Open Data API")
    st.caption("資料集：F-C0032-001")
    st.caption("36 小時縣市天氣預報")


# ── Main area ────────────────────────────────────────────────────────────────
st.title("🌤️ 台灣天氣預報")
st.markdown(
    '<div class="hero-subtitle">CWA 36 小時天氣預報｜快速查看縣市天氣、溫度趨勢與全台互動地圖</div>',
    unsafe_allow_html=True,
)

init_db()
df_all = load_data_from_db()

if df_all.empty:
    st.info("目前資料庫沒有天氣資料，系統將自動從 CWA API 取得資料。")
    with st.spinner("正在建立初始資料..."):
        run_pipeline()
        load_data_from_db.clear()
        df_all = load_data_from_db()

if not df_all.empty:
    locations = sorted(df_all["locationName"].unique().tolist())
    available_times = sorted(df_all["startTime"].unique().tolist())
    time_labels = [
        pd.Timestamp(t).strftime("%Y-%m-%d %H:%M")
        for t in available_times
    ]
    time_label_to_ts = dict(zip(time_labels, available_times))

    # ── Top controls ─────────────────────────────────────────────────────────
    select_col1, select_col2 = st.columns([1, 1])

    with select_col1:
        selected_location = st.selectbox(
            "📍 選擇縣市",
            options=locations,
            index=0,
        )

    with select_col2:
        selected_label = st.selectbox(
            "⏰ 選擇預報時段",
            options=time_labels,
            index=0,
            key="map_time_selector",
            help="選擇要顯示在全台地圖上的 12 小時預報時段。",
        )

    selected_time = pd.Timestamp(time_label_to_ts[selected_label])

    df_region = (
        df_all[df_all["locationName"] == selected_location]
        .sort_values("startTime")
        .reset_index(drop=True)
    )

    selected_record = nearest_record(df_region, selected_time)

    # ── Summary cards ────────────────────────────────────────────────────────
    card1, card2, card3, card4 = st.columns(4)

    with card1:
        st.metric("📍 目前地區", selected_location)

    with card2:
        min_t = selected_record["MinT"]
        max_t = selected_record["MaxT"]
        temp_text = (
            f"{min_t:.0f}–{max_t:.0f}°C"
            if pd.notna(min_t) and pd.notna(max_t)
            else "N/A"
        )
        st.metric("🌡️ 溫度範圍", temp_text)

    with card3:
        st.metric("🌤️ 天氣", str(selected_record["Wx"]))

    with card4:
        period_label = selected_record["startTime"].strftime("%m/%d %H:%M")
        st.metric("🕒 預報開始", period_label)

    st.markdown(
        f'<div class="soft-note">目前地圖顯示時段：<b>{selected_label}</b> ｜ '
        f'共 {len(df_all["locationName"].unique())} 個縣市資料</div>',
        unsafe_allow_html=True,
    )

    # ── Main map ─────────────────────────────────────────────────────────────
    st.subheader("🗺️ 全台天氣地圖")
    st.caption(
        "點擊縣市標記可查看天氣與溫度。"
        " 顏色：🔵 <20°C　🟢 20–28°C　🟠 28–33°C　🔴 ≥33°C"
    )

    taiwan_map, num_markers = build_map(df_all, selected_time)

    st_folium(
        taiwan_map,
        width="stretch",
        height=610,
        returned_objects=[],
        key=f"folium_map_{selected_label}",
    )

    st.caption(f"目前顯示 {num_markers} 個縣市標記。")

    # ── Lower dashboard: chart + table ──────────────────────────────────────
    st.divider()
    chart_col, table_col = st.columns([1, 1.15], gap="large")

    with chart_col:
        st.subheader(f"📈 {selected_location} 溫度趨勢")

        chart_df = df_region.set_index(
            df_region["startTime"].dt.strftime("%m/%d %H:%M")
        )[["MinT", "MaxT"]].rename(
            columns={
                "MinT": "最低溫 (°C)",
                "MaxT": "最高溫 (°C)",
            }
        )

        st.line_chart(chart_df, width="stretch")

    with table_col:
        st.subheader(f"📋 {selected_location} 詳細預報")

        display_df = df_region[
            ["startTime", "endTime", "Wx", "MinT", "MaxT"]
        ].copy()

        display_df["startTime"] = display_df["startTime"].dt.strftime(
            "%Y-%m-%d %H:%M"
        )
        display_df["endTime"] = display_df["endTime"].dt.strftime(
            "%Y-%m-%d %H:%M"
        )

        display_df.columns = [
            "開始時間",
            "結束時間",
            "天氣",
            "最低溫 (°C)",
            "最高溫 (°C)",
        ]

        st.dataframe(
            display_df,
            width="stretch",
            hide_index=True,
        )

    st.caption(
        f"資料庫目前共有 {len(df_all)} 筆預報資料；"
        f"{selected_location} 共有 {len(df_region)} 個預報時段。"
    )
