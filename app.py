import html
import textwrap

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from database import get_all_records, init_db, replace_current_forecast
from weather_api import fetch_weather_forecast


st.set_page_config(
    page_title="台灣天氣預報",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
    <style>
    .stApp {
        background: #F4F9FD;
    }

    .block-container {
        max-width: 1500px;
        padding-top: 1.15rem;
        padding-bottom: 2.5rem;
    }

    h1, h2, h3 {
        color: #174A7E;
    }

    h1 {
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 0.1rem;
    }

    .hero-subtitle {
        color: #66839A;
        font-size: 0.96rem;
        margin-top: -0.2rem;
        margin-bottom: 0.9rem;
    }

    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E3EDF5;
        padding: 15px 18px;
        border-radius: 17px;
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

    .tip-card {
        background: #FFFFFF;
        border: 1px solid #E3EDF5;
        border-radius: 18px;
        padding: 1rem 1.15rem;
        box-shadow: 0 6px 18px rgba(34, 82, 120, 0.05);
        margin-top: 0.4rem;
        margin-bottom: 0.8rem;
    }

    .tip-title {
        color: #174A7E;
        font-weight: 800;
        font-size: 1.05rem;
        margin-bottom: 0.45rem;
    }

    .tip-line {
        color: #36566F;
        line-height: 1.75;
    }

    .soft-note {
        background: #EAF5FD;
        border: 1px solid #D5EAF8;
        border-radius: 13px;
        padding: 0.65rem 0.85rem;
        color: #315D7A;
        margin: 0.3rem 0 0.7rem 0;
    }

    .forecast-table-wrap {
        background: #FFFFFF;
        border: 1px solid #DCEAF4;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 4px 14px rgba(34, 82, 120, 0.04);
    }

    .forecast-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.94rem;
    }

    .forecast-table th {
        background: #EAF4FB;
        color: #315D7A;
        text-align: left;
        padding: 0.8rem 0.9rem;
        font-weight: 750;
        border-bottom: 1px solid #DCEAF4;
    }

    .forecast-table td {
        padding: 0.8rem 0.9rem;
        color: #2E4F68;
        border-bottom: 1px solid #EEF4F8;
        vertical-align: middle;
    }

    .forecast-table tr:last-child td {
        border-bottom: none;
    }

    .forecast-table tr:hover td {
        background: #F8FCFF;
    }

    .weather-pill {
        display: inline-block;
        background: #EFF7FC;
        color: #285C7D;
        border-radius: 999px;
        padding: 0.22rem 0.55rem;
        font-weight: 650;
    }

    .rain-pill {
        display: inline-block;
        background: #EDF8F3;
        color: #28745B;
        border-radius: 999px;
        padding: 0.22rem 0.55rem;
        font-weight: 700;
    }

    .stButton > button {
        border-radius: 12px;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_data_from_db():
    rows = get_all_records()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([dict(row) for row in rows])

    for column in ["MinT", "MaxT", "PoP"]:
        if column not in df.columns:
            df[column] = pd.NA
        df[column] = pd.to_numeric(df[column], errors="coerce")

    if "CI" not in df.columns:
        df["CI"] = ""

    df["CI"] = df["CI"].fillna("").astype(str)
    df.loc[df["CI"].str.lower() == "nan", "CI"] = ""

    df["startTime"] = pd.to_datetime(df["startTime"], errors="coerce")
    df["endTime"] = pd.to_datetime(df["endTime"], errors="coerce")

    return df


def refresh_forecast():
    records = fetch_weather_forecast()

    if not records:
        return 0

    count = replace_current_forecast(records)
    load_data_from_db.clear()
    return count


def active_forecast_data(df):
    if df.empty:
        return df

    now = pd.Timestamp.now()
    active = df[df["endTime"] > now].copy()

    return active if not active.empty else df.copy()


def nearest_record(df_region, selected_time):
    exact = df_region[df_region["startTime"] == selected_time]

    if not exact.empty:
        return exact.iloc[0]

    idx = (df_region["startTime"] - selected_time).abs().idxmin()
    return df_region.loc[idx]


def friendly_period_label(timestamp):
    ts = pd.Timestamp(timestamp)
    today = pd.Timestamp.now().normalize()
    day_diff = (ts.normalize() - today).days

    if day_diff == 0:
        day = "今天"
    elif day_diff == 1:
        day = "明天"
    elif day_diff == 2:
        day = "後天"
    else:
        day = ts.strftime("%m/%d")

    if ts.hour < 12:
        part = "白天"
    elif ts.hour < 18:
        part = "下午"
    else:
        part = "晚上"

    return f"{day}{part}"


def weather_emoji(wx):
    text = str(wx or "")

    if "雷" in text:
        return "⛈️"
    if "雨" in text:
        return "🌧️"
    if "雪" in text:
        return "🌨️"
    if "陰" in text:
        return "☁️"
    if "多雲" in text or "雲" in text:
        return "⛅"
    if "晴" in text:
        return "☀️"

    return "🌤️"


def build_tips(row):
    tips = []

    min_t = row.get("MinT")
    max_t = row.get("MaxT")
    pop = row.get("PoP")

    if pd.notna(pop):
        if pop >= 50:
            tips.append("☂️ 降雨機率偏高，出門記得帶傘。")
        elif pop >= 30:
            tips.append("🌂 有下雨可能，帶把折傘會比較安心。")

    if pd.notna(min_t) and pd.notna(max_t):
        if max_t - min_t >= 8:
            tips.append("🧥 早晚溫差較大，可以準備一件薄外套。")
        if max_t >= 30:
            tips.append("🧴 白天偏熱，注意防曬與補充水分。")
        if min_t < 16:
            tips.append("🧣 氣溫偏低，建議增加保暖衣物。")

    if not tips:
        tips.append("🌿 天氣條件相對平穩，依個人行程準備即可。")

    return tips


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
        if pd.isna(max_t):
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
        pop = row.get("PoP")
        ci = str(row.get("CI") or "")
        wx = row["Wx"]

        min_t_str = f"{min_t:.0f}°C" if pd.notna(min_t) else "N/A"
        max_t_str = f"{max_t:.0f}°C" if pd.notna(max_t) else "N/A"
        pop_str = f"{pop:.0f}%" if pd.notna(pop) else "N/A"
        temp_label = f"{max_t:.0f}°" if pd.notna(max_t) else "?"

        popup_html = f"""
        <div style="font-family:sans-serif; min-width:180px;">
            <b style="font-size:15px;">📍 {name}</b><br>
            <hr style="margin:5px 0;">
            {weather_emoji(wx)} {wx}<br>
            🌡️ {min_t_str} – {max_t_str}<br>
            ☔ 降雨機率 {pop_str}<br>
            🙂 {ci if ci else 'N/A'}<br>
            🕒 {row['startTime'].strftime('%m/%d %H:%M')}
        </div>
        """

        color = temp_color(max_t)

        folium.CircleMarker(
            location=coords,
            radius=12,
            color=color,
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.62,
            tooltip=f"{name}｜{wx}",
            popup=folium.Popup(popup_html, max_width=270),
        ).add_to(taiwan_map)

        folium.Marker(
            location=coords,
            icon=folium.DivIcon(
                html=(
                    '<div style="font-size:10px;font-weight:800;color:#1F2D3D;'
                    'text-align:center;line-height:1;margin-top:-4px;">'
                    f"{temp_label}</div>"
                ),
                icon_size=(42, 20),
                icon_anchor=(21, 10),
            ),
        ).add_to(taiwan_map)

        markers_added += 1

    return taiwan_map, markers_added


def render_pretty_table(df_region):
    rows_html = []

    for _, row in df_region.iterrows():
        label = friendly_period_label(row["startTime"])
        wx = str(row["Wx"] or "")
        icon = weather_emoji(wx)

        min_t = (
            f"{row['MinT']:.0f}"
            if pd.notna(row["MinT"])
            else "—"
        )
        max_t = (
            f"{row['MaxT']:.0f}"
            if pd.notna(row["MaxT"])
            else "—"
        )
        pop = (
            f"{row['PoP']:.0f}%"
            if pd.notna(row["PoP"])
            else "—"
        )
        ci = str(row.get("CI") or "").strip() or "—"

        rows_html.append(
            f"""
            <tr>
                <td><b>{html.escape(label)}</b><br>
                    <span style="color:#8298AA;font-size:0.82rem;">
                    {row['startTime'].strftime('%m/%d %H:%M')}
                    </span>
                </td>
                <td><span class="weather-pill">
                    {icon} {html.escape(wx)}
                    </span>
                </td>
                <td><b>{min_t}–{max_t}°C</b></td>
                <td><span class="rain-pill">☔ {pop}</span></td>
                <td>{html.escape(ci)}</td>
            </tr>
            """
        )

    table_html = f"""
    <div class="forecast-table-wrap">
        <table class="forecast-table">
            <thead>
                <tr>
                    <th>預報時段</th>
                    <th>天氣</th>
                    <th>溫度</th>
                    <th>降雨機率</th>
                    <th>舒適度</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows_html)}
            </tbody>
        </table>
    </div>
    """

    # Render as HTML directly instead of Markdown.
    # This avoids Markdown treating indented <tr>/<td> tags as a code block.
    st.html(textwrap.dedent(table_html).strip())


# ── Bootstrap ────────────────────────────────────────────────────────────────
init_db()
df_all = load_data_from_db()

if df_all.empty:
    st.info("目前資料庫沒有天氣資料，正在從 CWA API 建立最新預報。")
    with st.spinner("正在取得天氣資料..."):
        refresh_forecast()
        df_all = load_data_from_db()


# ── Header ───────────────────────────────────────────────────────────────────
header_left, header_right = st.columns([5, 1])

with header_left:
    st.title("🌤️ 台灣天氣預報")
    st.markdown(
        '<div class="hero-subtitle">'
        'CWA 36 小時預報｜快速決定今天要不要帶傘、外套與防曬用品'
        '</div>',
        unsafe_allow_html=True,
    )

with header_right:
    st.write("")
    st.write("")
    if st.button("🔄 更新資料", use_container_width=True):
        with st.spinner("正在取得最新 CWA 天氣資料..."):
            count = refresh_forecast()

        st.success(f"已同步 {count} 筆最新預報。")
        st.rerun()


if not df_all.empty:
    df_view = active_forecast_data(df_all)

    locations = sorted(
        df_view["locationName"].dropna().unique().tolist()
    )
    available_times = sorted(
        df_view["startTime"].dropna().unique().tolist()
    )

    if not available_times:
        st.error("找不到可用預報時段。")
        st.stop()

    period_labels = [
        f"{friendly_period_label(ts)}｜{pd.Timestamp(ts).strftime('%m/%d %H:%M')}"
        for ts in available_times
    ]
    label_to_time = dict(zip(period_labels, available_times))

    now = pd.Timestamp.now()
    default_index = 0

    for index, ts in enumerate(available_times):
        matching = df_view[df_view["startTime"] == ts]
        if matching.empty:
            continue

        end = matching["endTime"].max()

        if ts <= now < end:
            default_index = index
            break

    control_left, control_right = st.columns([1, 2])

    with control_left:
        selected_location = st.selectbox(
            "📍 選擇縣市",
            options=locations,
        )

    with control_right:
        selected_label = st.radio(
            "⏰ 選擇預報時段",
            options=period_labels,
            index=min(default_index, len(period_labels) - 1),
            horizontal=True,
        )

    selected_time = pd.Timestamp(label_to_time[selected_label])

    df_region = (
        df_view[df_view["locationName"] == selected_location]
        .sort_values("startTime")
        .reset_index(drop=True)
    )

    selected_record = nearest_record(
        df_region,
        selected_time,
    )

    map_col, info_col = st.columns(
        [1.45, 1],
        gap="large",
    )

    with map_col:
        st.subheader("🗺️ 全台天氣地圖")
        st.caption(
            "點擊標記查看詳細天氣。"
            " 顏色依最高溫：🔵 <20°C　🟢 20–28°C　"
            "🟠 28–33°C　🔴 ≥33°C"
        )

        taiwan_map, marker_count = build_map(
            df_view,
            selected_time,
        )

        st_folium(
            taiwan_map,
            width="stretch",
            height=490,
            returned_objects=[],
            key=f"folium_map_{selected_label}",
        )

        st.caption(f"目前顯示 {marker_count} 個縣市標記。")

    with info_col:
        wx = str(selected_record.get("Wx") or "")
        min_t = selected_record.get("MinT")
        max_t = selected_record.get("MaxT")
        pop = selected_record.get("PoP")
        ci = str(selected_record.get("CI") or "").strip()

        st.subheader(
            f"📍 {selected_location}｜{weather_emoji(wx)} {wx}"
        )

        metric1, metric2 = st.columns(2)

        with metric1:
            temperature = (
                f"{min_t:.0f}–{max_t:.0f}°C"
                if pd.notna(min_t) and pd.notna(max_t)
                else "N/A"
            )
            st.metric("🌡️ 溫度", temperature)

        with metric2:
            rainfall = (
                f"{pop:.0f}%"
                if pd.notna(pop)
                else "N/A"
            )
            st.metric("☔ 降雨機率", rainfall)

        st.metric(
            "🙂 舒適度",
            ci if ci else "N/A",
        )

        tips = build_tips(selected_record)
        tips_html = "".join(
            f'<div class="tip-line">{tip}</div>'
            for tip in tips
        )

        st.markdown(
            f"""
            <div class="tip-card">
                <div class="tip-title">💡 出門小提醒</div>
                {tips_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="soft-note">
                預報時段：<b>{html.escape(selected_label)}</b><br>
                資料來源：中央氣象署 CWA Open Data
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Three-period cards ──────────────────────────────────────────────────
    st.subheader(f"🗓️ {selected_location} 36 小時預報")

    columns = st.columns(len(df_region))

    for column, (_, row) in zip(
        columns,
        df_region.iterrows(),
    ):
        with column:
            icon = weather_emoji(row["Wx"])
            temp_text = (
                f"{row['MinT']:.0f}–{row['MaxT']:.0f}°C"
                if pd.notna(row["MinT"])
                and pd.notna(row["MaxT"])
                else "N/A"
            )
            pop_text = (
                f"{row['PoP']:.0f}%"
                if pd.notna(row["PoP"])
                else "N/A"
            )

            st.metric(
                friendly_period_label(row["startTime"]),
                f"{icon} {temp_text}",
                f"☔ {pop_text}",
            )
            st.caption(str(row["Wx"]))

    # ── Details ─────────────────────────────────────────────────────────────
    with st.expander("📈 查看溫度趨勢", expanded=False):
        chart_df = df_region.set_index(
            df_region["startTime"].dt.strftime("%m/%d %H:%M")
        )[["MinT", "MaxT"]].rename(
            columns={
                "MinT": "最低溫 (°C)",
                "MaxT": "最高溫 (°C)",
            }
        )

        st.line_chart(chart_df, width="stretch")

    with st.expander("📋 查看詳細預報資料", expanded=False):
        render_pretty_table(df_region)

    st.caption(
        f"目前資料庫共有 {len(df_all)} 筆最新預報紀錄。"
    )
