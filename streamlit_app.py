import os
import joblib
import pandas as pd
import pydeck as pdk
import streamlit as st

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
MODEL_PATH  = "models/rf_model_unified.joblib"
MODEL_NAME  = "Aurafarm AI"
SHEET_URL   = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vR64ngnHsbGRjyGPpm9HCWe8bylsky-7kAxer6vr-fmVr_JKMHbJwKzPLe8yK5mxYKn3JNFw7KVNIJW/pubhtml"
    "/pub?output=csv"
)

# How many hours of history to show in the charts
HOURS_BACK  = 24

# Features your model expects
FEATURE_COLS = ["TVOC", "HP0", "HP3", "MQ135", "MQ7", "PM2.5", "PM10"]

# Robust renaming to catch both raw lowercase and Google Sheets headers
COLUMN_RENAME = {
    "time": "Timestamp", "Timestamp": "Timestamp", "Unnamed: 0": "Timestamp",
    "tvoc": "TVOC", "hp0": "HP0", "hp3": "HP3", 
    "mq135": "MQ135", "mq7": "MQ7", 
    "pm2.5": "PM2.5", "pm10": "PM10", "2.5": "PM2.5", "10": "PM10",
    "lat": "Latitude", "lon": "Longitude"
}

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(page_title="Aurafarm", layout="wide")

st.markdown("""
<style>
/* ── Viewport meta equivalent — ensure mobile scaling ── */
html { -webkit-text-size-adjust: 100%; }

/* ── Dark canvas ── */
html, body, [data-testid="stAppViewContainer"] {
    background: #0d1117 !important;
    color: #c9d1d9;
}
[data-testid="stHeader"]  { background: transparent !important; }
[data-testid="stSidebar"] { background: #161b22 !important; }

/* ── Block container — tight on mobile, roomy on desktop ── */
.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 2rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 100% !important;
}
@media (min-width: 768px) {
    .block-container {
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
}

/* ── Typography ── */
* { font-family: 'Inter', 'Segoe UI', sans-serif; }
h1, h2, h3, h4 { color: #e6edf3; letter-spacing: -0.3px; }

/* ── Eyebrow ── */
.eyebrow {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 1.3px;
    text-transform: uppercase;
    color: #6e7681;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 7px;
}
.eyebrow::before { content: "●"; color: #3fb950; font-size: 0.55rem; }

/* ── Cards ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 14px !important;
    box-shadow: 0 4px 24px rgba(0,0,0,0.35);
    padding: 18px 16px !important;
    margin-bottom: 16px !important;
    margin-top: 4px !important;
    box-sizing: border-box !important;
}
@media (min-width: 768px) {
    [data-testid="stVerticalBlockBorderWrapper"] {
        padding: 24px 26px !important;
        margin-bottom: 22px !important;
    }
}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"] {
    box-shadow: none !important;
    margin-bottom: 10px !important;
    margin-top: 0 !important;
}

/* ── Hero title scales down on mobile ── */
.hero-title {
    font-size: clamp(2rem, 8vw, 3rem);
    font-weight: 800;
    line-height: 1.1;
    color: #e6edf3;
    letter-spacing: -1px;
    text-align: center;
}
.hero-sub {
    font-size: clamp(0.8rem, 3vw, 0.95rem);
    color: #6e7681;
    text-align: center;
    margin-top: 6px;
    margin-bottom: 18px;
}

/* ── Status pill ── */
.status-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 12px 28px;
    width: auto;
    max-width: 100%;
    border-radius: 999px;
    font-weight: 700;
    font-size: clamp(0.85rem, 4vw, 1.1rem);
    white-space: nowrap;
    box-sizing: border-box;
}
.status-vape    { background:rgba(248,81,73,0.12);  border:1.5px solid rgba(248,81,73,0.5);  color:#ffa198; box-shadow:0 0 20px rgba(248,81,73,0.12); }
.status-clean   { background:rgba(63,185,80,0.10);  border:1.5px solid rgba(63,185,80,0.4);  color:#56d364; box-shadow:0 0 20px rgba(63,185,80,0.10); }
.status-offline { background:rgba(110,118,129,0.10); border:1.5px solid #30363d; color:#6e7681; }

/* ── Metric grid ── */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
}
@media (min-width: 540px)  { .metric-grid { grid-template-columns: repeat(4, 1fr); } }
@media (min-width: 900px)  { .metric-grid { grid-template-columns: repeat(7, 1fr); } }

.metric-cell {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 12px 14px;
}
.metric-label { font-size: 0.68rem; font-weight: 600; color: #6e7681; margin-bottom: 4px; }
.metric-value { font-size: 1.15rem; font-weight: 700; color: #e6edf3; }
.metric-delta-pos { font-size: 0.7rem; color: #56d364; }
.metric-delta-neg { font-size: 0.7rem; color: #ffa198; }
.metric-delta-neu { font-size: 0.7rem; color: #6e7681; }

/* ── Quick stats grid ── */
.qs-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    margin-bottom: 4px;
}
@media (min-width: 640px) { .qs-grid { grid-template-columns: repeat(4, 1fr); } }

.qs-cell {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 12px 14px;
}
.qs-label { font-size: 0.65rem; font-weight: 600; color: #6e7681; margin-bottom: 4px; }
.qs-value { font-size: 1.05rem; font-weight: 700; color: #e6edf3; }

/* ── Map visual elements ── */
.map-legend { display:flex; gap:16px; margin-top:10px; font-size:0.78rem; color:#6e7681; flex-wrap:wrap; }
.legend-dot { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:5px; vertical-align:middle; }
.heatmap-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.heatmap-inner { display:flex; gap:3px; min-width: 480px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# LOAD MODEL
# ─────────────────────────────────────────────
@st.cache_resource
def load_model():
    if os.path.exists(MODEL_PATH):
        try:
            return joblib.load(MODEL_PATH)
        except Exception as e:
            st.error(f"Error loading model: {e}")
    return None

my_model = load_model()

# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_sensor_data():
    try:
        df = pd.read_csv(SHEET_URL)
        df = df.rename(columns=COLUMN_RENAME)
        
        # Cleanup extra empty columns Google Sheets sometimes exports
        if "Unnamed: 1" in df.columns:
            df = df.drop(columns=["Unnamed: 1"])
            
        if "Timestamp" in df.columns:
            df["Display_Time"] = pd.to_datetime(df["Timestamp"], errors="coerce", dayfirst=True)
            df["Sort_Time"]    = df["Display_Time"] + pd.Timedelta(hours=7)
            df = df.dropna(subset=["Display_Time"]).sort_values("Sort_Time", ascending=False)
            
        # ⚠️ MODEL COMPATIBILITY LAYER
        if "eCO2" not in df.columns: df["eCO2"] = 400.0
        if "Temp" not in df.columns: df["Temp"] = 25.0
        if "Humidity" not in df.columns: df["Humidity"] = 50.0
        if "CH0" not in df.columns and "HP0" in df.columns: df["CH0"] = df["HP0"]
        if "CH3" not in df.columns and "HP3" in df.columns: df["CH3"] = df["HP3"]
            
        return df
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()

df = load_sensor_data()

if df.empty:
    st.warning("No data available. Check your Google Sheets connection.")
    st.stop()

latest   = df.iloc[0]
previous = df.iloc[1] if len(df) > 1 else latest

# ─────────────────────────────────────────────
# RUN MODEL
# ─────────────────────────────────────────────
prediction   = None
confidence   = None

try:
    available_features = [col for col in FEATURE_COLS if col in df.columns]
    all_features = df[available_features]
    
    if my_model:
        latest_features = latest[available_features].values.reshape(1, -1)
        prediction = int(my_model.predict(latest_features)[0])
        
        if hasattr(my_model, "predict_proba"):
            proba      = my_model.predict_proba(latest_features)[0]
            confidence = float(proba[prediction]) * 100
            
        df["is_vape"] = my_model.predict(all_features.values)
except Exception as e:
    st.error(f"Prediction error (Model likely expects old data format): {e}")

# ─────────────────────────────────────────────
# HERO CARD
# ─────────────────────────────────────────────
with st.container(border=True):
    st.markdown(
        "<div class='hero-title'>VAPONOWAY</div>"
        "<div class='hero-sub'>Facility Air Quality Monitor</div>",
        unsafe_allow_html=True,
    )

    if prediction is None:
        st.markdown(
            "<div style='text-align:center'><span class='status-pill status-offline'>⚠️ Detection Offline</span></div>",
            unsafe_allow_html=True,
        )
    elif prediction == 1:
        conf_str = f" · {confidence:.0f}%" if confidence else ""
        st.markdown(
            f"<div style='text-align:center'>"
            f"<span class='status-pill status-vape'>🚨 Vape Detected{conf_str}</span><br>"
            f"<span style='color:#484f58;font-size:0.75rem'>as of {latest['Display_Time'].strftime('%H:%M:%S')}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        conf_str = f" · {confidence:.0f}%" if confidence else ""
        st.markdown(
            f"<div style='text-align:center'>"
            f"<span class='status-pill status-clean'>✅ Air Quality Clean{conf_str}</span><br>"
            f"<span style='color:#484f58;font-size:0.75rem'>as of {latest['Display_Time'].strftime('%H:%M:%S')}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────
# METRIC CARDS 
# ─────────────────────────────────────────────
def fmt_delta(col, inverse=False):
    try:
        d = round(float(latest[col]) - float(previous[col]), 2)
        if d == 0:
            return f"<span class='metric-delta-neu'>→ {d:+.2f}</span>"
        up = d > 0
        good = not up if inverse else up
        cls = "metric-delta-pos" if good else "metric-delta-neg"
        arrow = "↑" if up else "↓"
        return f"<span class='{cls}'>{arrow} {abs(d)}</span>"
    except Exception:
        return ""

metrics = [
    ("TVOC",     f"{latest.get('TVOC', 0)} ppb",    fmt_delta("TVOC", inverse=True)),
    ("PM 2.5",   f"{latest.get('PM2.5', 0)} μg/m³", fmt_delta("PM2.5", inverse=True)),
    ("PM 10",    f"{latest.get('PM10', 0)} μg/m³",  fmt_delta("PM10", inverse=True)),
    ("MQ135",    f"{latest.get('MQ135', 0)}",       fmt_delta("MQ135", inverse=True)),
    ("MQ7",      f"{latest.get('MQ7', 0)}",         fmt_delta("MQ7", inverse=True)),
    ("HP0",      f"{latest.get('HP0', 0)} Ω",       fmt_delta("HP0", inverse=True)),
    ("HP3",      f"{latest.get('HP3', 0)} Ω",       fmt_delta("HP3", inverse=True)),
]

cells_html = "".join(
    f"<div class='metric-cell'>"
    f"<div class='metric-label'>{label}</div>"
    f"<div class='metric-value'>{val}</div>"
    f"{delta}"
    f"</div>"
    for label, val, delta in metrics
)

with st.container(border=True):
    st.markdown("<div class='eyebrow'>Live Readings</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-grid'>{cells_html}</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DETECTION HISTORY
# ─────────────────────────────────────────────
with st.container(border=True):
    st.markdown("<div class='eyebrow'>Detection History</div>", unsafe_allow_html=True)

    if my_model and "is_vape" in df.columns:
        vape_rows = df[df["is_vape"] == 1].copy()

        if not vape_rows.empty:
            vape_rows = vape_rows.sort_values("Display_Time")
            vape_rows["block"] = (
                vape_rows["Display_Time"].diff() > pd.Timedelta(minutes=5)
            ).cumsum()

            event_rows = []
            for _, grp in vape_rows.groupby("block"):
                event_rows.append({
                    "Date":       grp["Display_Time"].min().strftime("%Y-%m-%d"),
                    "Start":      grp["Display_Time"].min().strftime("%H:%M"),
                    "End":        grp["Display_Time"].max().strftime("%H:%M"),
                    "Duration":   str(grp["Display_Time"].max() - grp["Display_Time"].min()).split(".")[0],
                    "Peak TVOC":  f"{grp['TVOC'].max():.0f} ppb",
                    "Peak PM2.5": f"{grp.get('PM2.5', pd.Series([0])).max():.1f} μg/m³",
                })

            events_df = pd.DataFrame(event_rows[::-1])
            st.dataframe(
                events_df, use_container_width=True, hide_index=True,
            )
            st.caption(f"{len(events_df)} detection event(s) in available data.")
        else:
            st.markdown(
                "<div style='color:#484f58;padding:24px 0;text-align:center;font-size:0.85rem'>"
                "No vape events detected in the available data.</div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            "<div style='color:#484f58;padding:24px 0;text-align:center;font-size:0.85rem'>"
            "Detection system offline — history unavailable.</div>",
            unsafe_allow_html=True,
        )

    # ── Quick Stats ──
    st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)
    st.markdown("<div class='eyebrow'>Quick Stats</div>", unsafe_allow_html=True)

    if my_model and "is_vape" in df.columns:
        vape_qs = df[df["is_vape"] == 1].copy()
        if not vape_qs.empty:
            vape_qs2 = vape_qs.sort_values("Display_Time")
            vape_qs2["block"] = (vape_qs2["Display_Time"].diff() > pd.Timedelta(minutes=5)).cumsum()
            total_events = vape_qs2["block"].nunique()
            vape_qs2["hour"] = vape_qs2["Display_Time"].dt.hour
            worst_hour = int(vape_qs2["hour"].value_counts().idxmax())
            worst_hour_str = f"{worst_hour:02d}:00–{worst_hour+1:02d}:00"
            clean_rows = df[df["is_vape"] == 0].sort_values("Sort_Time")
            if len(clean_rows) > 1:
                gaps = clean_rows["Sort_Time"].diff().dropna()
                longest = gaps.max()
                h, rem = divmod(int(longest.total_seconds()), 3600)
                m = rem // 60
                longest_clean_str = f"{h}h {m}m" if h else f"{m}m"
            else:
                longest_clean_str = "N/A"
            peak_tvoc_str = f"{vape_qs['TVOC'].max():.0f} ppb"
        else:
            total_events, worst_hour_str, longest_clean_str, peak_tvoc_str = 0, "—", "—", "—"

        qs_cells = "".join(
            f"<div class='qs-cell'><div class='qs-label'>{lbl}</div><div class='qs-value'>{val}</div></div>"
            for lbl, val in [
                ("Total Events", str(total_events)),
                ("Worst Hour",   worst_hour_str),
                ("Clean Run",    longest_clean_str),
                ("Peak TVOC",    peak_tvoc_str),
            ]
        )
        st.markdown(f"<div class='qs-grid'>{qs_cells}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#484f58;font-size:0.85rem'>Model offline — stats unavailable.</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# LIVE GPS SENSOR MAP 
# ─────────────────────────────────────────────
with st.container(border=True):
    st.markdown("<div class='eyebrow'>Live Sensor Location</div>", unsafe_allow_html=True)

    # 1. Extract valid GPS data from the sheet
    if "Latitude" in df.columns and "Longitude" in df.columns:
        valid_gps = df.dropna(subset=["Latitude", "Longitude"])
    else:
        valid_gps = pd.DataFrame()

    # 2. Get the most recent location, or use a default if none exists yet
    if not valid_gps.empty:
        latest_gps = valid_gps.iloc[0]
        map_lat = float(latest_gps["Latitude"])
        map_lon = float(latest_gps["Longitude"])
    else:
        map_lat = 18.761778  # Default fallback latitude
        map_lon = 98.973028  # Default fallback longitude

    live_state = 1 if prediction == 1 else 0

    # 3. Create the dataframe specifically for PyDeck
    map_sensors = pd.DataFrame({
        "sensor_id":    ["ESP32 Node"],
        "location":     ["Live Location"],
        "lat":          [map_lat],
        "lon":          [map_lon],
        "vape_detected":[live_state],
    })

    # Add styling columns for the map dot
    map_sensors["status_text"] = map_sensors["vape_detected"].map({1: "Vape Detected", 0: "Clean"})
    map_sensors["fill_r"] = map_sensors["vape_detected"].map({1: 248, 0: 63})
    map_sensors["fill_g"] = map_sensors["vape_detected"].map({1: 81,  0: 185})
    map_sensors["fill_b"] = map_sensors["vape_detected"].map({1: 73,  0: 80})

    halo_layer = pdk.Layer(
        "ScatterplotLayer", data=map_sensors,
        get_position=["lon", "lat"],
        get_fill_color=["fill_r", "fill_g", "fill_b", 50],
        get_radius=14, radius_units="meters",
        radius_min_pixels=12, radius_max_pixels=24, pickable=False,
    )
    dot_layer = pdk.Layer(
        "ScatterplotLayer", data=map_sensors,
        get_position=["lon", "lat"],
        get_fill_color=["fill_r", "fill_g", "fill_b", 230],
        get_radius=5, radius_units="meters",
        radius_min_pixels=5, radius_max_pixels=12,
        pickable=True, stroked=True,
        get_line_color=[255, 255, 255, 80], line_width_min_pixels=1,
    )
    
    # Auto-center map on the live coordinates
    view_state = pdk.ViewState(latitude=map_lat, longitude=map_lon, zoom=17, pitch=0)

    st.pydeck_chart(
        pdk.Deck(
            layers=[halo_layer, dot_layer],
            initial_view_state=view_state,
            map_style="dark",
            tooltip={"text": "{sensor_id} — {location}\nStatus: {status_text}\nLat: {lat}\nLon: {lon}"},
        ),
        height=300,
        use_container_width=True,
    )

    st.markdown(
        "<div class='map-legend'>"
        "<span><span class='legend-dot' style='background:#3fb950'></span>Clean</span>"
        "<span><span class='legend-dot' style='background:#f85149'></span>Vape Detected</span>"
        "</div>",
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────
# TREND CHARTS 
# ─────────────────────────────────────────────
chart_data = df.sort_values("Sort_Time", ascending=True).copy()
cutoff     = chart_data["Sort_Time"].max() - pd.Timedelta(hours=HOURS_BACK)
chart_data = chart_data[chart_data["Sort_Time"] >= cutoff].set_index("Sort_Time")
numeric_cols = chart_data.select_dtypes(include="number").columns
chart_data   = chart_data[numeric_cols].resample("1min").mean().interpolate(method="time")

if my_model and "is_vape" in df.columns:
    vape_overlay = (
        df[df["Sort_Time"] >= cutoff].sort_values("Sort_Time")
        .set_index("Sort_Time")[["is_vape"]]
        .resample("1min").max()
        .rename(columns={"is_vape": "⚠ Vape Event"})
    )
    chart_data = chart_data.join(vape_overlay, how="left")

st.markdown(
    f"<div style='font-size:0.72rem;font-weight:700;letter-spacing:1.3px;text-transform:uppercase;"
    f"color:#6e7681;margin-bottom:10px;margin-top:4px;display:flex;align-items:center;gap:7px'>"
    f"<span style='color:#3fb950;font-size:0.55rem'>●</span>"
    f"Sensor Trends · Last {HOURS_BACK} Hours</div>",
    unsafe_allow_html=True,
)

CHART_H = 260 

cols_p = [c for c in ["PM2.5", "PM10"] if c in chart_data.columns]
if "⚠ Vape Event" in chart_data.columns: cols_p.append("⚠ Vape Event")
if cols_p:
    with st.container(border=True):
        st.markdown("<div class='eyebrow'>🟤 Particles</div>", unsafe_allow_html=True)
        st.line_chart(chart_data[cols_p], height=CHART_H, use_container_width=True)

cols_a = [c for c in ["TVOC"] if c in chart_data.columns]
if "⚠ Vape Event" in chart_data.columns: cols_a.append("⚠ Vape Event")
if cols_a:
    with st.container(border=True):
        st.markdown("<div class='eyebrow'>🌫 Air Quality</div>", unsafe_allow_html=True)
        st.line_chart(chart_data[cols_a], height=CHART_H, use_container_width=True)

cols_r = [c for c in ["HP0", "HP3", "MQ135", "MQ7"] if c in chart_data.columns]
if cols_r:
    with st.container(border=True):
        st.markdown("<div class='eyebrow'>⚡ Raw Sensor Readings</div>", unsafe_allow_html=True)
        st.line_chart(chart_data[cols_r], height=CHART_H, use_container_width=True)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown(
    "<div style='text-align:center;color:#484f58;font-size:0.72rem;padding:8px 0'>"
    "Aurafarm · Auto-refreshes every 30 s · Sensor data via Google Sheets"
    "</div>",
    unsafe_allow_html=True,
)
