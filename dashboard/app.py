"""FoodFlow AI — Institutional Food Waste Intelligence Dashboard.

Run from repo root:
    venv/Scripts/python.exe -m streamlit run dashboard/app.py
"""

import os
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as bg
import streamlit as st
from datetime import date, timedelta

# Page configuration
st.set_page_config(
    page_title="FoodFlow AI — Dashboard",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for rich aesthetics
st.markdown("""
<style>
    .main {
        background-color: #0f172a;
    }
    .stAppViewContainer {
        background-color: #0f172a;
    }
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .metric-title {
        color: #94a3b8;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        color: #f8fafc;
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 0.2rem;
    }
    .metric-sub {
        color: #10b981;
        font-size: 0.85rem;
        margin-top: 0.2rem;
        font-weight: 500;
    }
    .rec-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-left: 4px solid #10b981;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        border-top: 1px solid #334155;
        border-right: 1px solid #334155;
        border-bottom: 1px solid #334155;
    }
    .badge-high {
        background-color: #ef4444;
        color: #ffffff;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-med {
        background-color: #f59e0b;
        color: #ffffff;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

API_BASE = os.environ.get("FOODFLOW_API_URL", "http://127.0.0.1:8000/api")


@st.cache_data(ttl=5)
def fetch_api(endpoint: str, params: dict = None):
    try:
        res = requests.get(f"{API_BASE}/{endpoint}", params=params, timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        return None
    return None


def post_api(endpoint: str, payload: dict):
    try:
        res = requests.post(f"{API_BASE}/{endpoint}", json=payload, timeout=5)
        if res.status_code in (200, 201):
            return res.json()
    except Exception as e:
        st.error(f"API Error: {e}")
    return None


# Sidebar
st.sidebar.image("https://img.icons8.com/emoji/96/sprouting-plant.png", width=60)
st.sidebar.title("FoodFlow AI")
st.sidebar.caption("Institutional Waste Intelligence")

# Fetch Sites
sites = fetch_api("sites") or []
site_options = {"All Sites": None}
for s in sites:
    site_options[s["name"]] = s["id"]

selected_site_name = st.sidebar.selectbox("Filter Kitchen Location", list(site_options.keys()))
selected_site_id = site_options[selected_site_name]

st.sidebar.markdown("---")
st.sidebar.markdown("**System Health & Quick Links**")
health = fetch_api("health")
if health:
    st.sidebar.success("Backend Connected (FastAPI)")
else:
    st.sidebar.warning("Backend Disconnected — check uvicorn server")

st.sidebar.markdown("📱 [Open Mobile Feedback Form](http://127.0.0.1:8000/feedback_form/index.html)")

# Main Tabs
tab_overview, tab_impact, tab_benchmarks, tab_forecast, tab_planner = st.tabs([
    "📊 Waste Overview",
    "🌱 Nutrition & Cost Impact",
    "🏆 Multi-Site Benchmarks",
    "🔮 Demand Forecast & AI Rules",
    "📅 Menu Planner & Feedback",
])

# ==========================================
# TAB 1: WASTE OVERVIEW
# ==========================================
with tab_overview:
    st.header("Cafeteria Waste Overview")
    st.caption("Live monitoring of plate returns, preparation quantities, and dish-level waste trends.")

    # Summary metrics
    impact_data = fetch_api("impact", {"site_id": selected_site_id}) or {}
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Wasted</div>
            <div class="metric-value">{impact_data.get('total_waste_kg', 0):,.1f} kg</div>
            <div class="metric-sub">Over {impact_data.get('days_count', 0)} days tracked</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Waste Ratio</div>
            <div class="metric-value">{impact_data.get('waste_percentage', 0):.1f}%</div>
            <div class="metric-sub">Target: &lt; 8.0%</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Financial Loss</div>
            <div class="metric-value">₹{impact_data.get('total_cost_rupees', 0):,.0f}</div>
            <div class="metric-sub">Ingredient value wasted</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Carbon Impact</div>
            <div class="metric-value">{impact_data.get('total_co2e_kg', 0):,.1f} kg</div>
            <div class="metric-sub">CO₂e emitted from waste</div>
        </div>
        """, unsafe_allow_html=True)

    # Waste Records
    waste_records = fetch_api("waste", {"site_id": selected_site_id, "limit": 500}) or []
    if waste_records:
        df_waste = pd.DataFrame(waste_records)
        df_waste['record_date'] = pd.to_datetime(df_waste['record_date'])

        # Daily Trend Chart
        df_daily = df_waste.groupby('record_date')['wasted_grams'].sum().reset_index()
        df_daily['wasted_kg'] = df_daily['wasted_grams'] / 1000.0

        fig_daily = px.line(
            df_daily,
            x='record_date',
            y='wasted_kg',
            title='Daily Food Waste Trend (kg)',
            markers=True,
            color_discrete_sequence=['#10b981']
        )
        fig_daily.update_layout(
            template="plotly_dark",
            paper_bgcolor="#1e293b",
            plot_bgcolor="#1e293b",
            xaxis_title="Date",
            yaxis_title="Wasted (kg)"
        )
        st.plotly_chart(fig_daily, use_container_width=True)

        col_left, col_right = st.columns(2)
        with col_left:
            # Waste by Meal
            df_meal = df_waste.groupby('meal')['wasted_grams'].sum().reset_index()
            df_meal['wasted_kg'] = df_meal['wasted_grams'] / 1000.0
            fig_meal = px.pie(
                df_meal,
                names='meal',
                values='wasted_kg',
                title='Waste Breakdown by Meal',
                hole=0.4,
                color_discrete_sequence=['#3b82f6', '#10b981', '#f59e0b']
            )
            fig_meal.update_layout(template="plotly_dark", paper_bgcolor="#1e293b", plot_bgcolor="#1e293b")
            st.plotly_chart(fig_meal, use_container_width=True)

        with col_right:
            # Waste by Dish
            df_dish = df_waste.groupby('dish_name')['wasted_grams'].sum().reset_index()
            df_dish['wasted_kg'] = df_dish['wasted_grams'] / 1000.0
            df_dish = df_dish.sort_values(by='wasted_kg', ascending=True).tail(8)

            fig_dish = px.bar(
                df_dish,
                x='wasted_kg',
                y='dish_name',
                orientation='h',
                title='Highest Wasted Dishes (kg)',
                color='wasted_kg',
                color_continuous_scale='Emerald'
            )
            fig_dish.update_layout(template="plotly_dark", paper_bgcolor="#1e293b", plot_bgcolor="#1e293b")
            st.plotly_chart(fig_dish, use_container_width=True)

    else:
        st.info("No waste records found. Run database seed or submit waste records.")


# ==========================================
# TAB 2: NUTRITION & COST IMPACT
# ==========================================
with tab_impact:
    st.header("Waste → Nutrition, Financial & Carbon Conversion")
    st.caption("Translating leftover grams into wasted meals, lost nutrition, financial cost, and ESG carbon footprints.")

    impact = fetch_api("impact", {"site_id": selected_site_id}) or {}

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Calories Wasted", f"{impact.get('total_calories_lost', 0):,.0f} kcal", "Lost Energy")
    with m2:
        st.metric("Protein Lost", f"{impact.get('total_protein_kg', 0):,.1f} kg", "Body-Building Protein")
    with m3:
        st.metric("Financial Value Lost", f"₹{impact.get('total_cost_rupees', 0):,.0f}", "Direct Ingredient Cost")
    with m4:
        st.metric("CO₂ Equivalent", f"{impact.get('total_co2e_kg', 0):,.1f} kg CO₂e", "Environmental Impact")

    st.markdown("---")
    st.subheader("Nutritional Equivalent Comparison")
    
    # Calculate equivalents
    meals_equivalent = int(impact.get('total_calories_lost', 0) / 650.0)
    trees_equivalent = round(impact.get('total_co2e_kg', 0) / 22.0, 1)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.info(f"🍱 **Nutritional Equivalent**: The calories wasted in this period could have fully fed **{meals_equivalent:,} additional diners** with a complete 650 kcal meal.")
    with col_b:
        st.success(f"🌳 **Environmental Equivalent**: Absorbing the CO₂e carbon footprint from this wasted food requires planting **{trees_equivalent} mature trees**.")


# ==========================================
# TAB 3: MULTI-SITE BENCHMARKS
# ==========================================
with tab_benchmarks:
    st.header("Multi-Site Kitchen Benchmarking")
    st.caption("Comparing cafeteria performance, waste per diner, and efficiency across institutional sites.")

    benchmarks = fetch_api("benchmarks") or []
    if benchmarks:
        df_bench = pd.DataFrame(benchmarks)

        st.subheader("Site Performance Summary")
        st.dataframe(
            df_bench[[
                'site_name', 'total_waste_kg', 'avg_daily_waste_kg',
                'waste_percentage', 'waste_per_diner_grams', 'total_cost_rupees', 'top_wasted_dish'
            ]].rename(columns={
                'site_name': 'Kitchen Location',
                'total_waste_kg': 'Total Waste (kg)',
                'avg_daily_waste_kg': 'Daily Avg (kg)',
                'waste_percentage': 'Waste %',
                'waste_per_diner_grams': 'Waste / Diner (g)',
                'total_cost_rupees': 'Cost Lost (₹)',
                'top_wasted_dish': 'Top Wasted Dish',
            }),
            use_container_width=True,
        )

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            fig_per_diner = px.bar(
                df_bench,
                x='site_name',
                y='waste_per_diner_grams',
                title='Waste per Diner (Grams / Person)',
                color='site_name',
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig_per_diner.update_layout(template="plotly_dark", paper_bgcolor="#1e293b", plot_bgcolor="#1e293b")
            st.plotly_chart(fig_per_diner, use_container_width=True)

        with col_b2:
            fig_cost_site = px.pie(
                df_bench,
                names='site_name',
                values='total_cost_rupees',
                title='Financial Loss Distribution by Kitchen (₹)',
                hole=0.3
            )
            fig_cost_site.update_layout(template="plotly_dark", paper_bgcolor="#1e293b", plot_bgcolor="#1e293b")
            st.plotly_chart(fig_cost_site, use_container_width=True)


# ==========================================
# TAB 4: DEMAND FORECAST & AI RULES
# ==========================================
with tab_forecast:
    st.header("Predictive Demand Forecasting & AI Operational Rules")
    st.caption("Next-day recommended cook quantities using time-series predictions + calendar event awareness.")

    site_id_for_fc = selected_site_id or (sites[0]['id'] if sites else 1)
    
    forecast_data = fetch_api("forecast", {"site_id": site_id_for_fc}) or []
    if forecast_data:
        df_fc = pd.DataFrame(forecast_data)
        
        st.subheader("Tomorrow's Optimal Prep Quantities")
        st.dataframe(
            df_fc[[
                'meal', 'dish_name', 'predicted_attendance',
                'recommended_cook_grams', 'base_cook_grams', 'notes'
            ]].rename(columns={
                'meal': 'Meal',
                'dish_name': 'Dish',
                'predicted_attendance': 'Predicted Diners',
                'recommended_cook_grams': 'Recommended Cook (g)',
                'base_cook_grams': 'Base Demand (g)',
                'notes': 'AI Reasoning / Event Factor',
            }),
            use_container_width=True,
        )

    st.markdown("---")
    st.subheader("Automated Operator Recommendations")
    
    recs = fetch_api("recommendations", {"site_id": selected_site_id}) or []
    if recs:
        for r in recs:
            badge_class = "badge-high" if r['priority'] == 'high' else "badge-med"
            st.markdown(f"""
            <div class="rec-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong style="color:#f8fafc; font-size:1.1rem;">{r['title']}</strong>
                    <span class="{badge_class}">{r['priority'].upper()} PRIORITY</span>
                </div>
                <p style="color:#cbd5e1; margin-top:0.5rem; font-size:0.95rem;">{r['suggestion']}</p>
                <div style="color:#10b981; font-size:0.85rem; font-weight:600; margin-top:0.4rem;">
                    💡 Potential Monthly Reduction: ~{r['expected_savings_kg']} kg waste saved
                </div>
            </div>
            """, unsafe_allow_html=True)


# ==========================================
# TAB 5: MENU PLANNER & FEEDBACK
# ==========================================
with tab_planner:
    st.header("Weekly Menu Planner & Diner Feedback Analytics")
    st.caption("Manage weekly menu schedules, monitor upcoming calendar events, and analyze diner plate return reasons.")

    col_p1, col_p2 = st.columns([3, 2])

    with col_p1:
        st.subheader("Weekly Menu Schedule")
        days_map = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}
        selected_dow = st.selectbox("Select Day of Week", options=list(days_map.keys()), format_func=lambda x: days_map[x])

        menu_items = fetch_api("menu", {"site_id": selected_site_id, "day_of_week": selected_dow}) or []
        if menu_items:
            df_m = pd.DataFrame(menu_items)
            st.dataframe(
                df_m[['meal', 'dish_name', 'category', 'site_name']].rename(columns={
                    'meal': 'Meal',
                    'dish_name': 'Dish Scheduled',
                    'category': 'Category',
                    'site_name': 'Kitchen',
                }),
                use_container_width=True,
            )
        else:
            st.info("No explicit menu schedule for this day. Default kitchen menu active.")

        st.markdown("---")
        st.subheader("Upcoming Calendar Events (Exams / Holidays)")
        events = fetch_api("calendar") or []
        if events:
            df_e = pd.DataFrame(events)
            st.dataframe(
                df_e[['event_date', 'title', 'event_type', 'attendance_impact_pct', 'notes']].rename(columns={
                    'event_date': 'Date',
                    'title': 'Event Title',
                    'event_type': 'Type',
                    'attendance_impact_pct': 'Impact %',
                    'notes': 'Details',
                }),
                use_container_width=True,
            )

    with col_p2:
        st.subheader("Diner Feedback Sentiment")
        fb_stats = fetch_api("feedback/stats", {"site_id": selected_site_id}) or {}
        
        st.metric("Total Responses Captured", fb_stats.get("total_responses", 0))

        reasons = fb_stats.get("reasons_breakdown", [])
        if reasons:
            df_fb = pd.DataFrame(reasons)
            fig_fb = px.bar(
                df_fb,
                x='count',
                y='reason_label',
                orientation='h',
                title='Top Reasons Food Was Left',
                color='count',
                color_continuous_scale='Purples'
            )
            fig_fb.update_layout(template="plotly_dark", paper_bgcolor="#1e293b", plot_bgcolor="#1e293b")
            st.plotly_chart(fig_fb, use_container_width=True)

        st.markdown("---")
        st.subheader("Recent Comments")
        recent_fb = fetch_api("feedback", {"site_id": selected_site_id, "limit": 5}) or []
        for item in recent_fb:
            if item.get("comment"):
                st.caption(f"💬 *\"{item['comment']}\"* — {item.get('meal', 'meal').capitalize()} ({item.get('site_name', 'Mess')})")
