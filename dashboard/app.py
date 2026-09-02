"""FoodFlow AI — Hostel 1 Kitchen Dashboard.

Run from repo root:
    venv/Scripts/python.exe -m streamlit run dashboard/app.py
"""

from __future__ import annotations

import io
import os
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import qrcode
import requests
import streamlit as st

st.set_page_config(
    page_title="FoodFlow AI — Hostel 1 Kitchen Board",
    page_icon="🍱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    /* Hide Radio Bubble Selection Dots */
    div[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }
    
    /* Convert Radio Options into Professional Sliding Division Cards */
    div[data-testid="stSidebar"] div[role="radiogroup"] label {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-left: 4px solid #475569 !important;
        border-radius: 10px !important;
        padding: 0.75rem 1rem !important;
        margin-bottom: 0.5rem !important;
        width: 100% !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        cursor: pointer !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15) !important;
    }
    
    /* Hover Animation & Sliding Effect */
    div[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background-color: #334155 !important;
        border-left-color: #10b981 !important;
        transform: translateX(6px) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25) !important;
    }
    
    /* Active Selected Item Division Card */
    div[data-testid="stSidebar"] div[role="radiogroup"] label[aria-checked="true"],
    div[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%) !important;
        border-color: #10b981 !important;
        border-left: 6px solid #10b981 !important;
        transform: translateX(4px) !important;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.2) !important;
    }
    
    /* Division Menu Text Styling */
    div[data-testid="stSidebar"] div[role="radiogroup"] label p {
        color: #f8fafc !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.01em !important;
        margin: 0 !important;
    }
    
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    .metric-title { color: #94a3b8; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; }
    .metric-value { color: #f8fafc; font-size: 1.8rem; font-weight: 700; margin-top: 0.2rem; }
    .metric-sub { color: #10b981; font-size: 0.85rem; margin-top: 0.2rem; }
    .rec-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-left: 4px solid #10b981;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        border: 1px solid #334155;
        border-left-width: 4px;
    }
    .badge-high { background-color: #ef4444; color: #fff; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .badge-med { background-color: #f59e0b; color: #fff; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
</style>
""",
    unsafe_allow_html=True,
)

import sys
import threading
import time
from pathlib import Path

# Ensure repo root is in sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Ensure database is initialized & seeded
try:
    from backend.database import init_db
    from backend.seed import seed_all
    init_db()
    seed_all(reset=False)
except Exception:
    pass


def start_backend_if_needed():
    """Auto-starts FastAPI server in a background thread if not already running."""
    try:
        r = requests.get("http://127.0.0.1:8000/api/health", timeout=1)
        if r.status_code == 200:
            return
    except Exception:
        pass

    try:
        import uvicorn
        from backend.main import app as fastapi_app

        def _run_server():
            uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="error")

        t = threading.Thread(target=_run_server, daemon=True)
        t.start()
        time.sleep(1.5)
    except Exception:
        pass


start_backend_if_needed()

API_BASE = os.environ.get("FOODFLOW_API_URL", "http://127.0.0.1:8000/api")
DAYS = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}
MEAL_ORDER = ["breakfast", "lunch", "snacks", "dinner"]
MEAL_TIMES = {
    "breakfast": "7:30–10:00 AM",
    "lunch": "12:30–2:00 PM",
    "snacks": "4:30–5:30 PM",
    "dinner": "7:30–9:00 PM",
}


def generate_qr_bytes(url: str) -> bytes:
    qr = qrcode.QRCode(version=1, box_size=8, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@st.cache_data(ttl=5)
def fetch_api(endpoint: str, params: dict = None):
    try:
        res = requests.get(f"{API_BASE}/{endpoint}", params=params, timeout=8)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None


today = date.today()
tomorrow = today + timedelta(days=1)

# Fetch site details
sites = fetch_api("sites") or []
site_options = {s["name"]: s["id"] for s in sites}
selected_site_name = "Hostel 1" if "Hostel 1" in site_options else (list(site_options.keys())[0] if site_options else "Hostel 1")
selected_site_id = site_options.get(selected_site_name, 1)

active_site_info = next((s for s in sites if s["id"] == selected_site_id), None)
location_str = active_site_info["location"] if active_site_info and active_site_info.get("location") else "Hostel Block 1 Mess"

health = fetch_api("health")
status_str = "🟢 API Online" if health else "🔴 API Offline"

# ===== TOP HEADER BANNER =====
st.markdown(
    f"""
<div style="background-color:#1e293b; border:1px solid #334155; border-radius:12px; padding:1.2rem; margin-bottom:1.5rem;">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
        <div>
            <h2 style="color:#ffffff; margin:0; font-size:1.6rem; font-weight:800;">🍱 {selected_site_name} Mess</h2>
            <p style="color:#94a3b8; margin:0.2rem 0 0 0; font-size:0.95rem;">{location_str} • Food Waste Intelligence & AI Forecasting Board</p>
        </div>
        <div style="display:flex; gap:1.5rem; flex-wrap:wrap; align-items:center;">
            <div style="text-align:right;">
                <span style="color:#94a3b8; font-size:0.8rem; font-weight:600; text-transform:uppercase;">Current Date</span>
                <div style="color:#f8fafc; font-weight:700; font-size:1.1rem;">{today.strftime('%A, %d %b %Y')}</div>
            </div>
            <div style="text-align:right;">
                <span style="color:#94a3b8; font-size:0.8rem; font-weight:600; text-transform:uppercase;">System Status</span>
                <div style="color:{'#10b981' if health else '#ef4444'}; font-weight:700; font-size:1.1rem;">{status_str}</div>
            </div>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
    <link rel="manifest" href="/feedback_form/manifest.json">
    <meta name="theme-color" content="#10b981">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-title" content="FoodFlow AI">
    """,
    unsafe_allow_html=True,
)

# ===== SIDEBAR NAVIGATION =====
st.sidebar.title("🍱 FoodFlow AI")
st.sidebar.caption("Hostel 1 Mess Management")

nav_options = [
    "📊 Leftover Waste Tracker",
    "📸 AI Plate Return Scanner",
    "🍳 Tomorrow's Cooking Quantities",
    "💰 Financial & Carbon Impact",
    "🏆 Mess Waste Benchmarks",
    "📅 Weekly Menu & Event Schedule",
    "📱 Diner Feedback & QR Code",
]

if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = nav_options[0]

nav_page = st.sidebar.radio(
    "Navigation Menu",
    options=nav_options,
    key="nav_page",
)

import socket


def get_local_wifi_ip():
    """Auto-detect active local Wi-Fi IPv4 address for mobile phone scanning."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_default_deploy_url():
    env_url = os.environ.get("DEPLOY_URL")
    if env_url:
        return env_url

    # Check if running on Streamlit Cloud or public web host via request headers
    try:
        if hasattr(st, "context") and hasattr(st.context, "headers"):
            headers = st.context.headers
            host = headers.get("x-forwarded-host") or headers.get("host")
            if host and "localhost" not in host and "127.0.0.1" not in host:
                proto = headers.get("x-forwarded-proto", "https")
                return f"{proto}://{host}"
    except Exception:
        pass

    local_ip = get_local_wifi_ip()
    return f"http://{local_ip}:8000"


st.sidebar.markdown("---")
st.sidebar.markdown("### 📱 Fixed Diner QR Feedback")
default_app_url = get_default_deploy_url()
deploy_base = st.sidebar.text_input(
    "Server Base URL for QR Code",
    value=default_app_url,
    help="Set your live domain (e.g. https://foodflowai.streamlit.app or http://192.168.0.4:8000)",
)
qr_target_url = f"{deploy_base.rstrip('/')}/feedback_form/index.html?site_id={selected_site_id}"

qr_img_bytes = generate_qr_bytes(qr_target_url)
st.sidebar.image(qr_img_bytes, caption="Hostel 1 QR Code (Scan with phone camera)", use_container_width=True)
st.sidebar.markdown(f"[🔗 Open Feedback Form]({qr_target_url})")
st.sidebar.download_button(
    label="📥 Download Hostel 1 QR Poster PNG",
    data=qr_img_bytes,
    file_name="hostel1_feedback_qr.png",
    mime="image/png",
    use_container_width=True,
)


# ===== PAGE 1: LEFTOVER WASTE TRACKER =====
if nav_page == "📊 Leftover Waste Tracker":
    st.header("📊 Leftover Waste Tracker")
    st.caption(f"{today.strftime('%A, %d %B %Y')} · Real-time dish-wise leftover quantities logged at Hostel 1 plate return counter.")

    today_waste = fetch_api(
        "waste",
        {"site_id": selected_site_id, "start": today.isoformat(), "end": today.isoformat(), "limit": 1000},
    ) or []

    if today_waste:
        df = pd.DataFrame(today_waste)
        total_kg = df["wasted_grams"].sum() / 1000.0
        prep_kg = df["prep_grams"].fillna(0).sum() / 1000.0
        pct = (total_kg / prep_kg * 100.0) if prep_kg else 0.0
        top = df.groupby("dish_name")["wasted_grams"].sum().sort_values(ascending=False)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Today's leftover", f"{total_kg:,.1f} kg")
        c2.metric("Share of food cooked", f"{pct:.1f}%")
        c3.metric("Highest leftover dish", top.index[0] if len(top) else "—")
        c4.metric("That dish today", f"{top.iloc[0]/1000:,.1f} kg" if len(top) else "—")

        by_dish = df.groupby("dish_name")[["wasted_grams", "prep_grams"]].sum().reset_index()
        by_dish["leftover_kg"] = by_dish["wasted_grams"] / 1000.0
        by_dish = by_dish.sort_values("leftover_kg", ascending=False)

        fig = px.bar(
            by_dish,
            x="leftover_kg",
            y="dish_name",
            orientation="h",
            title="Leftover quantity by dish today (kg)",
            color="leftover_kg",
            color_continuous_scale="Emrld",
        )
        fig.update_layout(template="plotly_dark", paper_bgcolor="#1e293b", plot_bgcolor="#1e293b", yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

        meal_df = df.groupby("meal")["wasted_grams"].sum().reset_index()
        meal_df["leftover_kg"] = meal_df["wasted_grams"] / 1000.0
        meal_df["meal"] = pd.Categorical(meal_df["meal"], MEAL_ORDER, ordered=True)
        meal_df = meal_df.sort_values("meal")
        fig_m = px.bar(
            meal_df,
            x="meal",
            y="leftover_kg",
            title="Leftovers by meal today",
            color="meal",
        )
        fig_m.update_layout(template="plotly_dark", paper_bgcolor="#1e293b", plot_bgcolor="#1e293b")
        st.plotly_chart(fig_m, use_container_width=True)
    else:
        st.info("No leftover records logged for Hostel 1 today yet. Use the AI Food Scanner to log records.")

    week_start = today - timedelta(days=6)
    week_waste = fetch_api(
        "waste",
        {"site_id": selected_site_id, "start": week_start.isoformat(), "end": today.isoformat(), "limit": 1000},
    ) or []
    if week_waste:
        wdf = pd.DataFrame(week_waste)
        wdf["record_date"] = pd.to_datetime(wdf["record_date"])
        daily = wdf.groupby("record_date")["wasted_grams"].sum().reset_index()
        daily["leftover_kg"] = daily["wasted_grams"] / 1000.0
        fig_d = px.line(daily, x="record_date", y="leftover_kg", markers=True, title="Last 7 days of leftovers at Hostel 1 (kg)")
        fig_d.update_layout(template="plotly_dark", paper_bgcolor="#1e293b", plot_bgcolor="#1e293b")
        st.plotly_chart(fig_d, use_container_width=True)


# ===== PAGE 2: AI PLATE RETURN SCANNER =====
elif nav_page == "📸 AI Plate Return Scanner":
    st.header("📸 AI Plate Return Scanner")
    st.caption("Scan food directly using your mobile phone camera or upload a photo of the food tray at Hostel 1 plate return.")

    col_scan1, col_scan2 = st.columns([1, 1])

    with col_scan1:
        scan_meal = st.selectbox("Meal session for scan", MEAL_ORDER, index=1, key="scan_meal_select")
        input_mode = st.radio("Input Source", ["📁 Upload Image File", "📷 Mobile / Web Camera"], horizontal=True)

        input_bytes = None
        input_name = "tray.jpg"
        input_type = "image/jpeg"

        if input_mode == "📷 Mobile / Web Camera":
            st.info("Click below to activate camera shutter:")
            camera_file = st.camera_input("Take photo of food tray with camera")
            if camera_file is not None:
                input_bytes = camera_file.getvalue()
                input_name = "mobile_camera_tray.jpg"
        else:
            uploaded_file = st.file_uploader(
                "Upload plate return photo",
                type=["jpg", "jpeg", "png", "webp"],
                help="Upload an image of a food tray returning from Hostel 1 mess.",
            )
            if uploaded_file is not None:
                input_bytes = uploaded_file.getvalue()
                input_name = uploaded_file.name
                input_type = uploaded_file.type
                st.image(uploaded_file, caption="Uploaded Tray Image", use_container_width=True)

        st.markdown(f"📱 **Mobile Direct Scanner Web App:** [{deploy_base.rstrip('/')}/feedback_form/scan.html]({deploy_base.rstrip('/')}/feedback_form/scan.html)")

    with col_scan2:
        if input_bytes is not None:
            # Auto-run detection if new photo captured/uploaded or requested via button
            last_bytes = st.session_state.get("last_processed_bytes")
            should_run = (last_bytes != input_bytes) or st.button("🔍 Re-run YOLO Detection", type="primary", use_container_width=True)

            if should_run:
                with st.spinner("Analyzing plate return image with YOLOv8..."):
                    try:
                        files = {"file": (input_name, input_bytes, input_type)}
                        params = {
                            "site_id": selected_site_id,
                            "meal": scan_meal,
                            "save_record": "false",
                        }
                        res = requests.post(f"{API_BASE}/detect", files=files, params=params, timeout=15)
                        if res.status_code == 200:
                            st.session_state["last_detection"] = res.json()
                            st.session_state["uploaded_file_bytes"] = input_bytes
                            st.session_state["uploaded_file_name"] = input_name
                            st.session_state["uploaded_file_type"] = input_type
                            st.session_state["last_processed_bytes"] = input_bytes
                        else:
                            st.error(f"Detection failed: {res.text}")
                    except Exception as err:
                        st.error(f"Could not connect to detection service: {err}")

            detection = st.session_state.get("last_detection")
            if detection:
                st.subheader("Detection Result")
                count = detection.get("detected_count", 0)
                total_g = detection.get("total_estimated_wasted_grams", 0)

                st.success(f"Detected **{count}** dish item(s) — Total estimated leftover: **{total_g/1000.0:.2f} kg** ({int(total_g)}g)")

                if detection.get("annotated_image_b64"):
                    st.image(
                        detection["annotated_image_b64"],
                        caption="YOLOv8 Annotated Leftovers",
                        use_container_width=True,
                    )

                detections_list = detection.get("detections", [])
                if detections_list:
                    det_df = pd.DataFrame(detections_list)
                    st.dataframe(
                        det_df[["dish_name", "confidence", "estimated_wasted_grams"]].rename(
                            columns={
                                "dish_name": "Dish Identified",
                                "confidence": "Confidence",
                                "estimated_wasted_grams": "Estimated Wasted (g)",
                            }
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )

                    if st.button("💾 Save Leftover Records to Database", use_container_width=True):
                        with st.spinner("Saving waste records..."):
                            try:
                                files = {
                                    "file": (
                                        st.session_state.get("uploaded_file_name", "tray.jpg"),
                                        st.session_state.get("uploaded_file_bytes"),
                                        st.session_state.get("uploaded_file_type", "image/jpeg"),
                                    )
                                }
                                params = {
                                    "site_id": selected_site_id,
                                    "meal": scan_meal,
                                    "save_record": "true",
                                }
                                save_res = requests.post(f"{API_BASE}/detect", files=files, params=params, timeout=15)
                                if save_res.status_code == 200:
                                    save_data = save_res.json()
                                    saved_count = len(save_data.get("saved_records", []))
                                    st.toast(f"Saved {saved_count} waste record(s) to database!", icon="✅")
                                    st.success(f"Successfully saved {saved_count} waste record(s) for {selected_site_name} ({scan_meal.capitalize()})!")
                                    st.cache_data.clear()
                                else:
                                    st.error(f"Failed to save records: {save_res.text}")
                            except Exception as save_err:
                                st.error(f"Error saving records: {save_err}")
                else:
                    st.warning("No dishes detected in this frame above confidence threshold.")
        else:
            st.info("Upload an image on the left to start detection.")


# ===== PAGE 3: TOMORROW'S COOKING QUANTITIES =====
elif nav_page == "🍳 Tomorrow's Cooking Quantities":
    st.header("🍳 Tomorrow's Cooking Quantities")
    st.caption(f"{tomorrow.strftime('%A, %d %B %Y')} · Recommended cook quantities per dish based on historical waste & expected diner turnout.")

    tomorrow_menu = fetch_api("menu/tomorrow", {"site_id": selected_site_id}) or []
    forecast = fetch_api("forecast", {"site_id": selected_site_id, "target_date": tomorrow.isoformat()}) or []
    recs = fetch_api("recommendations", {"site_id": selected_site_id}) or []

    if tomorrow_menu:
        mdf = pd.DataFrame(tomorrow_menu)
        st.subheader("Tomorrow's scheduled menu")
        for meal in MEAL_ORDER:
            rows = mdf[mdf["meal"] == meal]
            if rows.empty:
                continue
            dishes = ", ".join(sorted(rows["dish_name"].unique()))
            st.markdown(f"**{meal.capitalize()}** ({MEAL_TIMES[meal]}) — {dishes}")
    else:
        st.info("No menu scheduled for tomorrow yet. Add dishes in the menu planner section.")

    if forecast:
        st.subheader("Recommended cook quantity per dish")
        fdf = pd.DataFrame(forecast)
        fdf["recommended_kg"] = fdf["recommended_cook_grams"] / 1000.0
        fdf["base_kg"] = fdf["base_cook_grams"] / 1000.0
        st.dataframe(
            fdf[["meal", "dish_name", "predicted_attendance", "recommended_kg", "notes"]].rename(
                columns={
                    "meal": "Meal Session",
                    "dish_name": "Dish Name",
                    "predicted_attendance": "Expected Diners",
                    "recommended_kg": "Recommended Cook (kg)",
                    "notes": "Why this amount",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No cook plan available for tomorrow.")

    st.subheader("Kitchen action suggestions")
    if recs:
        for r in recs:
            badge = "badge-high" if r["priority"] == "high" else "badge-med"
            st.markdown(
                f"""
                <div class="rec-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="color:#f8fafc;">{r['title']}</strong>
                        <span class="{badge}">{r['priority'].upper()}</span>
                    </div>
                    <p style="color:#cbd5e1; margin-top:0.5rem;">{r['suggestion']}</p>
                    <div style="color:#10b981; font-size:0.85rem; font-weight:600;">
                        Expected monthly savings: ~{r['expected_savings_kg']} kg.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.success("No urgent kitchen actions right now.")


# ===== PAGE 4: FINANCIAL & CARBON IMPACT =====
elif nav_page == "💰 Financial & Carbon Impact":
    st.header("💰 Financial & Carbon Impact")
    st.caption("Cumulative ingredient value lost (₹), wasted calories, protein lost, and environmental carbon footprint.")

    impact = fetch_api("impact", {"site_id": selected_site_id}) or {}
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Calories wasted", f"{impact.get('total_calories_lost', 0):,.0f} kcal")
    m2.metric("Protein lost", f"{impact.get('total_protein_kg', 0):,.1f} kg")
    m3.metric("Ingredient value lost", f"₹{impact.get('total_cost_rupees', 0):,.0f}")
    m4.metric("Carbon from leftovers", f"{impact.get('total_co2e_kg', 0):,.1f} kg CO₂e")

    meals_eq = int(impact.get("total_calories_lost", 0) / 650.0)
    st.info(f"Those leftover calories could have fed **{meals_eq:,} people** (counting 650 kcal per meal).")


# ===== PAGE 5: MESS WASTE BENCHMARKS =====
elif nav_page == "🏆 Mess Waste Benchmarks":
    st.header("🏆 Mess Waste Benchmarks")
    st.caption("Kitchen waste performance metrics and grams leftover per diner.")

    benchmarks = fetch_api("benchmarks") or []
    if benchmarks:
        df_bench = pd.DataFrame(benchmarks)
        st.dataframe(
            df_bench[
                [
                    "site_name",
                    "total_waste_kg",
                    "avg_daily_waste_kg",
                    "waste_percentage",
                    "waste_per_diner_grams",
                    "total_cost_rupees",
                    "top_wasted_dish",
                ]
            ].rename(
                columns={
                    "site_name": "Kitchen",
                    "total_waste_kg": "Total Leftover (kg)",
                    "avg_daily_waste_kg": "Daily Average (kg)",
                    "waste_percentage": "Leftover %",
                    "waste_per_diner_grams": "Grams / Diner",
                    "total_cost_rupees": "Cost Lost (₹)",
                    "top_wasted_dish": "Highest Leftover Dish",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
        fig_per = px.bar(df_bench, x="site_name", y="waste_per_diner_grams", title="Grams leftover per diner")
        fig_per.update_layout(template="plotly_dark", paper_bgcolor="#1e293b", plot_bgcolor="#1e293b")
        st.plotly_chart(fig_per, use_container_width=True)
    else:
        st.info("No benchmark metrics available.")


# ===== PAGE 6: WEEKLY MENU & EVENT SCHEDULE =====
elif nav_page == "📅 Weekly Menu & Event Schedule":
    st.header("📅 Weekly Menu & Event Schedule")
    col_p1, col_p2 = st.columns([3, 2])

    with col_p1:
        selected_dow = st.selectbox(
            "Select Day of Week",
            options=list(DAYS.keys()),
            format_func=lambda x: DAYS[x],
            index=today.weekday(),
        )
        menu_items = fetch_api("menu", {"site_id": selected_site_id, "day_of_week": selected_dow}) or []
        if menu_items:
            df_m = pd.DataFrame(menu_items)
            df_m["meal"] = pd.Categorical(df_m["meal"], MEAL_ORDER, ordered=True)
            df_m = df_m.sort_values(["meal", "dish_name"])
            st.dataframe(
                df_m[["meal", "dish_name", "category"]].rename(
                    columns={
                        "meal": "Meal Session",
                        "dish_name": "Dish Name",
                        "category": "Type",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No dishes scheduled for this day.")

        st.subheader("Upcoming holidays and events")
        events = fetch_api("calendar") or []
        if events:
            df_e = pd.DataFrame(events)
            st.dataframe(
                df_e[["event_date", "title", "event_type", "attendance_impact_pct", "notes"]].rename(
                    columns={
                        "event_date": "Date",
                        "title": "Event Name",
                        "event_type": "Type",
                        "attendance_impact_pct": "Turnout Change",
                        "notes": "Kitchen Note",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    with col_p2:
        fb_stats = fetch_api("feedback/stats", {"site_id": selected_site_id}) or {}
        avg = fb_stats.get("average_rating")
        st.metric("Diner rating", f"{avg:.1f} / 5" if avg else "No ratings yet")
        st.metric("Feedback entries collected", fb_stats.get("total_responses", 0))
        reasons = fb_stats.get("reasons_breakdown", [])
        if reasons:
            df_fb = pd.DataFrame(reasons)
            fig_fb = px.bar(df_fb, x="count", y="reason_label", orientation="h", title="Why food was left")
            fig_fb.update_layout(template="plotly_dark", paper_bgcolor="#1e293b", plot_bgcolor="#1e293b")
            st.plotly_chart(fig_fb, use_container_width=True)


# ===== PAGE 7: DINER FEEDBACK & QR CODE =====
elif nav_page == "📱 Diner Feedback & QR Code":
    st.header("📱 Diner Feedback & QR Code")
    st.caption("Manage Hostel 1 plate return QR codes, fill out the diner form, and review comments.")

    c_qr1, c_qr2 = st.columns([1, 1])
    with c_qr1:
        st.subheader("Printable QR Standee")
        st.image(qr_img_bytes, caption="Hostel 1 Permanent Feedback QR Code", width=340)
        st.markdown(f"**🔗 Direct Feedback Form Link:** [{qr_target_url}]({qr_target_url})")

        st.markdown("---")
        st.subheader("Live Mobile Form Preview")
        import streamlit.components.v1 as components
        components.iframe(qr_target_url, height=580, scrolling=True)

    with c_qr2:
        st.subheader("Recent diner comments")
        recent_fb = fetch_api("feedback", {"site_id": selected_site_id, "limit": 10}) or []
        if recent_fb:
            for item in recent_fb:
                if item.get("comment"):
                    stars = "★" * int(item.get("rating") or 0)
                    st.markdown(
                        f"""
                        <div style="background-color:#1e293b; border:1px solid #334155; border-radius:8px; padding:0.8rem; margin-bottom:0.6rem;">
                            <div style="color:#fbbf24; font-weight:700;">{stars} ({item.get('rating', '-')}/5)</div>
                            <p style="color:#f8fafc; margin:0.3rem 0; font-size:0.95rem;">"{item['comment']}"</p>
                            <span style="color:#94a3b8; font-size:0.8rem;">{item.get('meal', 'meal').capitalize()} • {selected_site_name}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        else:
            st.info("No comments submitted yet.")
