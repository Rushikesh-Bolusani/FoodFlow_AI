"""FoodFlow AI — Hostel Mess Management Dashboard.

Enterprise-grade SaaS analytics dashboard for institutional kitchens.
Run from repo root:
    venv/Scripts/python.exe -m streamlit run dashboard/app.py
"""

from __future__ import annotations

import io
import os
import socket
import sys
import threading
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import qrcode
import requests
import streamlit as st

# ===== PAGE CONFIGURATION =====
st.set_page_config(
    page_title="FoodFlow AI — Hostel Mess Management",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===== ENTERPRISE SAAS DESIGN SYSTEM (CSS) =====
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global Typography & Base Palette */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        background-color: #F8F9FA !important;
        color: #1E293B !important;
    }

    /* Main Container Padding */
    .main .block-container {
        padding-top: 1.75rem !important;
        padding-bottom: 3rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 1400px !important;
    }

    /* Header Bar Clean Styling */
    header[data-testid="stHeader"] {
        background-color: #FFFFFF !important;
        border-bottom: 1px solid #E5E7EB !important;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E5E7EB !important;
        box-shadow: 1px 0 3px rgba(0, 0, 0, 0.02) !important;
    }

    [data-testid="stSidebar"] .block-container {
        padding-top: 1.5rem !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
    }

    /* Sidebar Navigation Menu Container */
    [data-testid="stSidebar"] [data-testid="stRadio"] > label {
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        color: #94A3B8 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        margin-bottom: 0.4rem !important;
        display: block !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {
        gap: 0.35rem !important;
    }

    /* Completely Hide Default Radio Dot / Circle Elements */
    [data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child,
    [data-testid="stSidebar"] [data-testid="stRadio"] label div[aria-hidden="true"],
    [data-testid="stSidebar"] [data-testid="stRadio"] input[type="radio"] {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        margin: 0 !important;
        opacity: 0 !important;
        position: absolute !important;
    }

    /* Sidebar Nav Items Styled as Clean SaaS Nav Links */
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        background: transparent !important;
        border: 1px solid transparent !important;
        border-radius: 6px !important;
        padding: 0.6rem 0.85rem !important;
        margin-bottom: 0.15rem !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        transition: all 0.15s ease-in-out !important;
        cursor: pointer !important;
        box-shadow: none !important;
    }

    /* Lucide Line Icons via CSS ::before on each Nav Item */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label::before {
        content: "";
        display: inline-block;
        width: 16px;
        height: 16px;
        margin-right: 10px;
        background-repeat: no-repeat;
        background-position: center;
        background-size: contain;
        flex-shrink: 0;
    }

    /* 1. Leftover Waste Tracker - Bar Chart */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(1)::before {
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="%23475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>');
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(1):has(input:checked)::before {
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="%231E3A5F" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>');
    }

    /* 2. AI Plate Return Scanner - Camera */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(2)::before {
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="%23475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>');
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(2):has(input:checked)::before {
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="%231E3A5F" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>');
    }

    /* 3. Tomorrow's Cooking Quantities - Clock / Schedule */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(3)::before {
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="%23475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>');
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(3):has(input:checked)::before {
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="%231E3A5F" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>');
    }

    /* 4. Financial & Carbon Impact - Trend Chart */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(4)::before {
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="%23475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>');
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(4):has(input:checked)::before {
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="%231E3A5F" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>');
    }

    /* 5. Mess Waste Benchmarks - Trophy / Award */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(5)::before {
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="%23475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="7"></circle><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline></svg>');
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(5):has(input:checked)::before {
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="%231E3A5F" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="7"></circle><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline></svg>');
    }

    /* 6. Weekly Menu & Event Schedule - Calendar */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(6)::before {
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="%23475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>');
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(6):has(input:checked)::before {
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="%231E3A5F" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>');
    }

    /* 7. Diner Feedback & QR Code - Message */
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(7)::before {
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="%23475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>');
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:nth-child(7):has(input:checked)::before {
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="%231E3A5F" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>');
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: #F1F5F9 !important;
        border-color: #E2E8F0 !important;
    }

    /* Active Selected Menu Item */
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked),
    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"] {
        background: #EFF6FF !important;
        border: 1px solid #BFDBFE !important;
        border-left: 4px solid #1E3A5F !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label p {
        color: #475569 !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        letter-spacing: -0.01em !important;
        margin: 0 !important;
    }

    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {
        color: #1E3A5F !important;
        font-weight: 600 !important;
    }

    /* Header Banner Component */
    .top-banner {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.75rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }

    .page-title-block {
        margin-bottom: 1.5rem;
    }

    .page-title {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        color: #1E293B !important;
        letter-spacing: -0.02em !important;
        margin: 0 0 0.25rem 0 !important;
    }

    .page-caption {
        font-size: 0.875rem !important;
        color: #64748B !important;
        margin: 0 !important;
    }

    /* Metric KPI Cards */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 1.15rem 1.25rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        margin-bottom: 1.25rem;
        min-height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .metric-title {
        font-size: 0.75rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.4rem;
    }

    .metric-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #1E293B;
        letter-spacing: -0.02em;
        line-height: 1.1;
    }

    .metric-sub {
        font-size: 0.8rem;
        font-weight: 500;
        margin-top: 0.35rem;
    }
    .metric-sub.positive { color: #0F766E; }
    .metric-sub.negative { color: #C0392B; }
    .metric-sub.neutral  { color: #64748B; }

    /* Section Subheadings */
    .section-header {
        font-size: 1.15rem !important;
        font-weight: 600 !important;
        color: #1E293B !important;
        margin: 1.5rem 0 0.75rem 0 !important;
        letter-spacing: -0.01em !important;
    }

    /* Enterprise Styled Table */
    .saas-table-wrapper {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        overflow-x: auto;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        margin-bottom: 1.5rem;
    }

    .saas-table {
        width: 100%;
        border-collapse: collapse;
        text-align: left;
        font-size: 0.875rem;
        color: #334155;
    }

    .saas-table th {
        background-color: #F8FAFC;
        color: #1E293B;
        font-weight: 600;
        padding: 0.8rem 1rem;
        border-bottom: 1px solid #E5E7EB;
        font-size: 0.8rem;
        letter-spacing: 0.02em;
    }

    .saas-table td {
        padding: 0.75rem 1rem;
        border-bottom: 1px solid #F1F5F9;
        font-size: 0.875rem;
    }

    .saas-table tr:last-child td {
        border-bottom: none;
    }

    .saas-table tr:nth-child(even) {
        background-color: #FAFAFA;
    }

    .saas-table tr:hover {
        background-color: #F1F5F9;
    }

    .saas-table .num-col {
        text-align: right;
        font-variant-numeric: tabular-nums;
    }

    /* Recommendation & Action Cards */
    .rec-card-saas {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-left: 4px solid #1E3A5F;
        border-radius: 8px;
        padding: 1.1rem 1.25rem;
        margin-bottom: 0.85rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }

    .rec-priority-high {
        background: #FEF2F2;
        color: #991B1B;
        border: 1px solid #FECACA;
        padding: 0.2rem 0.55rem;
        border-radius: 9999px;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }

    .rec-priority-med {
        background: #FFFBEB;
        color: #92400E;
        border: 1px solid #FDE68A;
        padding: 0.2rem 0.55rem;
        border-radius: 9999px;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }

    /* Feedback Cards */
    .feedback-card-saas {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    }

    /* Status Badges */
    .badge-status {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-status.online {
        background: #ECFDF5;
        color: #065F46;
        border: 1px solid #A7F3D0;
    }
    .badge-status.offline {
        background: #FEF2F2;
        color: #991B1B;
        border: 1px solid #FECACA;
    }
    .status-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
    }
    .badge-status.online .status-dot { background: #10B981; }
    .badge-status.offline .status-dot { background: #EF4444; }

    /* Clean Buttons */
    div.stButton > button[kind="primary"] {
        background-color: #1E3A5F !important;
        border-color: #1E3A5F !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        padding: 0.5rem 1rem !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #162C48 !important;
        border-color: #162C48 !important;
    }

    div.stButton > button[kind="secondary"],
    div.stDownloadButton > button {
        background-color: #FFFFFF !important;
        border: 1px solid #D1D5DB !important;
        color: #374151 !important;
        font-weight: 500 !important;
        border-radius: 6px !important;
        padding: 0.5rem 1rem !important;
    }
    div.stButton > button[kind="secondary"]:hover,
    div.stDownloadButton > button:hover {
        background-color: #F9FAFB !important;
        border-color: #9CA3AF !important;
        color: #111827 !important;
    }

    /* Clean Input, Selectbox, and Card Framing */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        background-color: #FFFFFF !important;
        border-color: #D1D5DB !important;
        border-radius: 6px !important;
    }

    /* Container Card for Forms or Tools */
    .content-box {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 1.25rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        margin-bottom: 1.25rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

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
            uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, log_level="error")

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

# Color palette tokens for enterprise charts
CHART_NAVY = "#1E3A5F"
CHART_TEAL = "#0F766E"
CHART_SLATE = "#64748B"
CHART_AMBER = "#D97706"
CHART_BLUE = "#3B5998"
CHART_PALETTE = [CHART_NAVY, CHART_TEAL, CHART_BLUE, CHART_SLATE, CHART_AMBER]


def apply_chart_theme(fig, height=350):
    """Applies a clean, enterprise-grade light layout to Plotly figures."""
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(
            family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            color="#1E293B",
            size=12,
        ),
        title_font=dict(
            family="Inter, sans-serif",
            color="#1E293B",
            size=15,
            weight=600,
        ),
        margin=dict(l=40, r=25, t=55, b=45),
        height=height,
        xaxis=dict(
            showgrid=True,
            gridcolor="#F1F5F9",
            zeroline=False,
            linecolor="#E2E8F0",
            tickfont=dict(color="#64748B", size=11),
            title_font=dict(color="#64748B", size=12),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#F1F5F9",
            zeroline=False,
            linecolor="#E2E8F0",
            tickfont=dict(color="#64748B", size=11),
            title_font=dict(color="#64748B", size=12),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#64748B", size=11),
        ),
    )
    return fig


def render_metric_card(title: str, value: str, subtext: str = "", subtext_type: str = "neutral") -> None:
    """Renders a clean white KPI card with light border and shadow."""
    subtext_html = f'<div class="metric-sub {subtext_type}">{subtext}</div>' if subtext else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div>
                <div class="metric-title">{title}</div>
                <div class="metric-value">{value}</div>
            </div>
            {subtext_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_styled_table(
    df: pd.DataFrame,
    numeric_cols: list[str] | None = None,
    col_widths: dict[str, str] | None = None,
) -> None:
    """Renders a responsive, zebra-striped, light-themed table."""
    if df is None or df.empty:
        st.info("No records to display.")
        return

    numeric_cols_set = set(numeric_cols or [])
    html = ['<div class="saas-table-wrapper"><table class="saas-table"><thead><tr>']

    for col in df.columns:
        align_class = ' class="num-col"' if col in numeric_cols_set else ""
        width_style = f' style="width:{col_widths[col]};"' if col_widths and col in col_widths else ""
        html.append(f"<th{align_class}{width_style}>{col}</th>")
    html.append("</tr></thead><tbody>")

    for _, row in df.iterrows():
        html.append("<tr>")
        for col in df.columns:
            val = row[col]
            align_class = ' class="num-col"' if col in numeric_cols_set else ""
            if isinstance(val, float):
                display_val = f"{val:,.2f}" if abs(val) < 100 else f"{val:,.1f}"
            elif isinstance(val, int):
                display_val = f"{val:,}"
            else:
                display_val = str(val) if pd.notna(val) else "—"
            html.append(f"<td{align_class}>{display_val}</td>")
        html.append("</tr>")

    html.append("</tbody></table></div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def generate_qr_bytes(url: str) -> bytes:
    qr = qrcode.QRCode(version=1, box_size=8, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1E293B", back_color="#FFFFFF")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@st.cache_data(ttl=5)
def fetch_api(endpoint: str, params: dict | None = None):
    try:
        res = requests.get(f"{API_BASE}/{endpoint}", params=params, timeout=8)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None


today = date.today()
tomorrow = today + timedelta(days=1)

# Static fallback datasets for Hostel 1 Mess demo
STATIC_TODAY_WASTE = [
    {"dish_name": "Chicken Biryani", "meal": "lunch", "wasted_grams": 8500, "prep_grams": 65000, "record_date": today.isoformat()},
    {"dish_name": "Sambar Rice", "meal": "lunch", "wasted_grams": 4200, "prep_grams": 50000, "record_date": today.isoformat()},
    {"dish_name": "Curd Rice", "meal": "lunch", "wasted_grams": 3100, "prep_grams": 40000, "record_date": today.isoformat()},
    {"dish_name": "Boiled Eggs", "meal": "lunch", "wasted_grams": 1800, "prep_grams": 25000, "record_date": today.isoformat()},
    {"dish_name": "Green Salad & Pickles", "meal": "lunch", "wasted_grams": 1200, "prep_grams": 15000, "record_date": today.isoformat()},
    {"dish_name": "Chapati & Kurma", "meal": "dinner", "wasted_grams": 5400, "prep_grams": 45000, "record_date": today.isoformat()},
    {"dish_name": "Dal Tadka", "meal": "dinner", "wasted_grams": 2800, "prep_grams": 35000, "record_date": today.isoformat()},
]

STATIC_7DAY_WASTE = [
    {"record_date": (today - timedelta(days=i)).isoformat(), "wasted_grams": g}
    for i, g in zip(range(6, -1, -1), [26500, 24100, 29800, 21400, 27500, 22000, 27000])
]

STATIC_TOMORROW_MENU = [
    {"meal": "breakfast", "dish_name": "Idli, Sambar & Coconut Chutney", "category": "Breakfast"},
    {"meal": "lunch", "dish_name": "Chicken Biryani, Sambar Rice & Curd Rice", "category": "Main Course"},
    {"meal": "snacks", "dish_name": "Samosa & Masala Tea", "category": "Snacks"},
    {"meal": "dinner", "dish_name": "Chapati, Veg Kurma & Dal Tadka", "category": "Dinner"},
]

STATIC_FORECAST = [
    {"meal": "breakfast", "dish_name": "Idli & Sambar", "predicted_attendance": 320, "recommended_cook_grams": 38000, "base_cook_grams": 42000, "notes": "Reduced Sambar prep by 4kg based on Wednesday trend"},
    {"meal": "lunch", "dish_name": "Chicken Biryani & Rice", "predicted_attendance": 450, "recommended_cook_grams": 72000, "base_cook_grams": 80000, "notes": "High attendance expected; optimize portion scoop size"},
    {"meal": "snacks", "dish_name": "Samosa & Tea", "predicted_attendance": 280, "recommended_cook_grams": 22000, "base_cook_grams": 25000, "notes": "Standard snack turnout expected"},
    {"meal": "dinner", "dish_name": "Chapati & Veg Kurma", "predicted_attendance": 380, "recommended_cook_grams": 54000, "base_cook_grams": 60000, "notes": "Adjusted Kurma spice level based on diner feedback"},
]

STATIC_RECOMMENDATIONS = [
    {"title": "Reduce Chicken Biryani Portion Scoop Size", "priority": "high", "suggestion": "Plate return logs show 8.5kg Biryani returned. Reduce serving ladle size from 250g to 200g with optional seconds.", "expected_savings_kg": 65},
    {"title": "Adjust Veg Kurma Spice Level", "priority": "medium", "suggestion": "3 diner reviews reported high spice levels leading to uneaten curries. Moderate chili content.", "expected_savings_kg": 35},
]

STATIC_IMPACT = {
    "total_calories_lost": 34500,
    "total_protein_kg": 5.4,
    "total_cost_rupees": 4850,
    "total_co2e_kg": 22.8,
}

STATIC_BENCHMARKS = [
    {"site_name": "Hostel 1 Mess", "total_waste_kg": 27.0, "avg_daily_waste_kg": 25.4, "waste_percentage": 11.2, "waste_per_diner_grams": 54.0, "total_cost_rupees": 4850, "top_wasted_dish": "Chicken Biryani"},
    {"site_name": "Hostel 2 Mess", "total_waste_kg": 38.5, "avg_daily_waste_kg": 36.1, "waste_percentage": 14.8, "waste_per_diner_grams": 72.5, "total_cost_rupees": 6900, "top_wasted_dish": "Chapati & Veg Kurma"},
    {"site_name": "Central Cafeteria", "total_waste_kg": 52.0, "avg_daily_waste_kg": 49.5, "waste_percentage": 16.2, "waste_per_diner_grams": 81.0, "total_cost_rupees": 9400, "top_wasted_dish": "Rice & Sambar"},
]

STATIC_FEEDBACK = [
    {"rating": 5, "comment": "Lunch Chicken Biryani was delicious today! Portion size was just right.", "meal": "lunch"},
    {"rating": 3, "comment": "Veg Kurma at dinner was a bit too spicy for some students.", "meal": "dinner"},
    {"rating": 4, "comment": "Sambar taste is great, but smaller rice scoop sizes would reduce leftover on plates.", "meal": "lunch"},
    {"rating": 5, "comment": "Idli & Chutney for breakfast was super fresh!", "meal": "breakfast"},
]

# Fetch site details
sites = fetch_api("sites") or []
site_options = {s["name"]: s["id"] for s in sites}
selected_site_name = "Hostel 1" if "Hostel 1" in site_options else (list(site_options.keys())[0] if site_options else "Hostel 1")
selected_site_id = site_options.get(selected_site_name, 1)

active_site_info = next((s for s in sites if s["id"] == selected_site_id), None)
location_str = active_site_info["location"] if active_site_info and active_site_info.get("location") else "Hostel Block 1 Mess"

health = fetch_api("health")
is_online = bool(health)
status_badge_class = "online" if is_online else "offline"
status_text = "System Operational" if is_online else "System Offline"

# ===== TOP HEADER BANNER =====
st.markdown(
    f"""
<div class="top-banner">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1.25rem;">
        <div>
            <div style="display:flex; align-items:center; gap:0.6rem;">
                <h1 style="color:#1E293B; margin:0; font-size:1.45rem; font-weight:700; letter-spacing:-0.02em;">{selected_site_name} Mess</h1>
                <span style="background:#F1F5F9; color:#475569; padding:0.2rem 0.55rem; border-radius:4px; font-size:0.75rem; font-weight:600;">{selected_site_name}</span>
            </div>
            <p style="color:#64748B; margin:0.25rem 0 0 0; font-size:0.875rem;">{location_str} · Food Waste Intelligence & AI Forecasting Board</p>
        </div>
        <div style="display:flex; gap:2rem; flex-wrap:wrap; align-items:center;">
            <div>
                <span style="color:#64748B; font-size:0.75rem; font-weight:600; text-transform:uppercase; letter-spacing:0.04em;">Current Date</span>
                <div style="color:#1E293B; font-weight:600; font-size:0.95rem;">{today.strftime('%A, %d %b %Y')}</div>
            </div>
            <div>
                <span style="color:#64748B; font-size:0.75rem; font-weight:600; text-transform:uppercase; letter-spacing:0.04em;">System Status</span>
                <div style="margin-top:0.2rem;">
                    <span class="badge-status {status_badge_class}">
                        <span class="status-dot"></span>
                        {status_text}
                    </span>
                </div>
            </div>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ===== SIDEBAR BRANDING & NAVIGATION =====
st.sidebar.markdown(
    """
<div style="padding: 0.25rem 0 1.25rem 0; border-bottom: 1px solid #E5E7EB; margin-bottom: 1rem;">
    <div style="display: flex; align-items: center; gap: 0.65rem;">
        <div style="background: #1E3A5F; color: #FFFFFF; width: 30px; height: 30px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 15px; letter-spacing: -0.02em;">F</div>
        <div>
            <div style="font-size: 1.05rem; font-weight: 700; color: #1E293B; letter-spacing: -0.02em; line-height: 1.1;">FoodFlow AI</div>
            <div style="font-size: 0.75rem; color: #64748B; font-weight: 500;">Hostel Mess Management</div>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

nav_options = [
    "Leftover Waste Tracker",
    "AI Plate Return Scanner",
    "Tomorrow's Cooking Quantities",
    "Financial & Carbon Impact",
    "Mess Waste Benchmarks",
    "Weekly Menu & Event Schedule",
    "Diner Feedback & QR Code",
]

if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = nav_options[0]

nav_page = st.sidebar.radio(
    "Navigation Menu",
    options=nav_options,
    key="nav_page",
    label_visibility="collapsed",
)


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


st.sidebar.markdown(
    """
<div style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #E5E7EB;">
    <div style="font-size: 0.8rem; font-weight: 600; color: #1E293B; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.75rem;">Plate Return QR Feedback</div>
</div>
""",
    unsafe_allow_html=True,
)

default_app_url = get_default_deploy_url()
deploy_base = st.sidebar.text_input(
    "Server Base URL",
    value=default_app_url,
    help="Set your live domain (e.g. https://foodflowai.streamlit.app or http://192.168.0.4:8000)",
    label_visibility="collapsed",
)
qr_target_url = f"{deploy_base.rstrip('/')}/feedback_form/index.html?site_id={selected_site_id}"

qr_img_bytes = generate_qr_bytes(qr_target_url)
st.sidebar.image(qr_img_bytes, caption="Hostel 1 Countertop QR Code", use_container_width=True)
st.sidebar.markdown(
    f"""
    <div style="margin-top: 0.4rem; margin-bottom: 0.6rem;">
        <a href="{qr_target_url}" target="_blank" style="color: #1E3A5F; font-size: 0.8rem; font-weight: 600; text-decoration: none;">Open Feedback Form &rarr;</a>
    </div>
    """,
    unsafe_allow_html=True,
)
st.sidebar.download_button(
    label="Download QR Poster (PNG)",
    data=qr_img_bytes,
    file_name="hostel1_feedback_qr.png",
    mime="image/png",
    use_container_width=True,
)


# ===== PAGE 1: LEFTOVER WASTE TRACKER =====
if nav_page == "Leftover Waste Tracker":
    st.markdown(
        f"""
        <div class="page-title-block">
            <h2 class="page-title">Leftover Waste Tracker</h2>
            <p class="page-caption">{today.strftime('%A, %d %B %Y')} · Real-time dish-wise leftover quantities logged at Hostel 1 plate return counter.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    today_waste = fetch_api(
        "waste",
        {"site_id": selected_site_id, "start": today.isoformat(), "end": today.isoformat(), "limit": 1000},
    ) or STATIC_TODAY_WASTE

    if today_waste:
        df = pd.DataFrame(today_waste)
        total_kg = df["wasted_grams"].sum() / 1000.0
        prep_kg = df["prep_grams"].fillna(0).sum() / 1000.0
        pct = (total_kg / prep_kg * 100.0) if prep_kg else 0.0
        top = df.groupby("dish_name")["wasted_grams"].sum().sort_values(ascending=False)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_metric_card("Today's Leftover", f"{total_kg:,.1f} kg", "Logged across plate returns", "neutral")
        with c2:
            render_metric_card(
                "Share of Food Cooked",
                f"{pct:.1f}%",
                "Target: < 10% waste ratio",
                "positive" if pct < 12 else "negative",
            )
        with c3:
            render_metric_card(
                "Highest Leftover Dish",
                top.index[0] if len(top) else "None",
                "Needs portion adjustment",
                "neutral",
            )
        with c4:
            render_metric_card(
                "Quantity For Top Dish",
                f"{top.iloc[0]/1000:,.1f} kg" if len(top) else "0.0 kg",
                "Top volume contributor",
                "negative",
            )

        col_ch1, col_ch2 = st.columns([3, 2])

        with col_ch1:
            by_dish = df.groupby("dish_name")[["wasted_grams", "prep_grams"]].sum().reset_index()
            by_dish["leftover_kg"] = by_dish["wasted_grams"] / 1000.0
            by_dish = by_dish.sort_values("leftover_kg", ascending=True)

            fig = px.bar(
                by_dish,
                x="leftover_kg",
                y="dish_name",
                orientation="h",
                title="Leftover Quantity by Dish Today (kg)",
                labels={"leftover_kg": "Leftover (kg)", "dish_name": "Dish Name"},
                color_discrete_sequence=[CHART_NAVY],
            )
            fig = apply_chart_theme(fig, height=360)
            st.plotly_chart(fig, use_container_width=True)

        with col_ch2:
            meal_df = df.groupby("meal")["wasted_grams"].sum().reset_index()
            meal_df["leftover_kg"] = meal_df["wasted_grams"] / 1000.0
            meal_df["meal"] = pd.Categorical(meal_df["meal"], MEAL_ORDER, ordered=True)
            meal_df = meal_df.sort_values("meal")
            meal_df["meal_label"] = meal_df["meal"].apply(lambda x: str(x).capitalize())

            fig_m = px.bar(
                meal_df,
                x="meal_label",
                y="leftover_kg",
                title="Leftovers by Meal Session",
                labels={"meal_label": "Meal Session", "leftover_kg": "Leftover (kg)"},
                color_discrete_sequence=[CHART_TEAL],
            )
            fig_m = apply_chart_theme(fig_m, height=360)
            st.plotly_chart(fig_m, use_container_width=True)

    week_start = today - timedelta(days=6)
    week_waste = fetch_api(
        "waste",
        {"site_id": selected_site_id, "start": week_start.isoformat(), "end": today.isoformat(), "limit": 1000},
    ) or STATIC_7DAY_WASTE

    if week_waste:
        wdf = pd.DataFrame(week_waste)
        wdf["record_date"] = pd.to_datetime(wdf["record_date"])
        daily = wdf.groupby("record_date")["wasted_grams"].sum().reset_index()
        daily["leftover_kg"] = daily["wasted_grams"] / 1000.0
        daily["formatted_date"] = daily["record_date"].dt.strftime("%b %d")

        fig_d = px.line(
            daily,
            x="formatted_date",
            y="leftover_kg",
            markers=True,
            title="7-Day Leftover Trend at Hostel 1 (kg)",
            labels={"formatted_date": "Date", "leftover_kg": "Leftover (kg)"},
            color_discrete_sequence=[CHART_NAVY],
        )
        fig_d.update_traces(line=dict(width=2.5), marker=dict(size=6))
        fig_d = apply_chart_theme(fig_d, height=300)
        st.plotly_chart(fig_d, use_container_width=True)


# ===== PAGE 2: AI PLATE RETURN SCANNER =====
elif nav_page == "AI Plate Return Scanner":
    st.markdown(
        """
        <div class="page-title-block">
            <h2 class="page-title">AI Plate Return Scanner</h2>
            <p class="page-caption">Automated computer vision detection and dish-wise waste estimation from plate return imagery.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_scan1, col_scan2 = st.columns([1, 1], gap="large")

    with col_scan1:
        st.markdown('<div class="content-box">', unsafe_allow_html=True)
        st.markdown('<div class="section-header" style="margin-top:0;">Image Acquisition</div>', unsafe_allow_html=True)

        scan_meal = st.selectbox("Meal Session", MEAL_ORDER, index=1, key="scan_meal_select")
        input_mode = st.radio("Input Method", ["Upload Image File", "Mobile / Web Camera"], horizontal=True)

        input_bytes = None
        input_name = "tray.jpg"
        input_type = "image/jpeg"

        if input_mode == "Mobile / Web Camera":
            camera_file = st.camera_input("Take photo of food tray with camera")
            if camera_file is not None:
                input_bytes = camera_file.getvalue()
                input_name = "mobile_camera_tray.jpg"
        else:
            uploaded_file = st.file_uploader(
                "Upload Plate Return Photo",
                type=["jpg", "jpeg", "png", "webp"],
                help="Upload an image of a food tray returning from Hostel 1 mess.",
            )
            if uploaded_file is not None:
                input_bytes = uploaded_file.getvalue()
                input_name = uploaded_file.name
                input_type = uploaded_file.type
                st.image(uploaded_file, caption="Uploaded Tray Image", use_container_width=True)

        st.markdown(
            f"""
            <div style="margin-top:1rem; padding-top:0.75rem; border-top:1px solid #E5E7EB; font-size:0.8rem; color:#64748B;">
                Mobile direct scanner: <a href="{deploy_base.rstrip('/')}/feedback_form/scan.html" target="_blank" style="color:#1E3A5F; font-weight:600; text-decoration:none;">Open Scanner PWA &rarr;</a>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_scan2:
        if input_bytes is not None:
            last_bytes = st.session_state.get("last_processed_bytes")
            should_run = (last_bytes != input_bytes) or st.button(
                "Run Detection Analysis", type="primary", use_container_width=True
            )

            if should_run:
                with st.spinner("Analyzing tray image with fine-tuned YOLOv8..."):
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
                count = detection.get("detected_count", 0)
                total_g = detection.get("total_estimated_wasted_grams", 0)

                st.markdown(
                    f"""
                    <div class="metric-card" style="margin-bottom: 1rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div class="metric-title">Detection Result</div>
                                <div class="metric-value">{total_g/1000.0:.2f} kg <span style="font-size: 1rem; font-weight: 500; color: #64748B;">({int(total_g)}g)</span></div>
                            </div>
                            <span style="background: #EFF6FF; color: #1E3A5F; border: 1px solid #BFDBFE; padding: 0.3rem 0.75rem; border-radius: 9999px; font-weight: 600; font-size: 0.8rem;">{count} Dishes Found</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if detection.get("annotated_image_b64"):
                    st.image(
                        detection["annotated_image_b64"],
                        caption="YOLOv8 Detection & Leftover Weight Estimation",
                        use_container_width=True,
                    )

                detections_list = detection.get("detections", [])
                if detections_list:
                    det_df = pd.DataFrame(detections_list)
                    det_table = det_df[["dish_name", "confidence", "estimated_wasted_grams"]].rename(
                        columns={
                            "dish_name": "Dish Identified",
                            "confidence": "Confidence",
                            "estimated_wasted_grams": "Estimated Wasted (g)",
                        }
                    )
                    det_table["Confidence"] = det_table["Confidence"].apply(lambda c: f"{float(c):.1%}")

                    st.markdown('<div class="section-header">Identified Food Items</div>', unsafe_allow_html=True)
                    render_styled_table(det_table, numeric_cols=["Confidence", "Estimated Wasted (g)"])

                    if st.button("Save Waste Records to Database", use_container_width=True):
                        with st.spinner("Saving records to system database..."):
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
                                    st.success(f"Successfully saved {saved_count} waste record(s) for {selected_site_name} ({scan_meal.capitalize()})!")
                                    st.cache_data.clear()
                                else:
                                    st.error(f"Failed to save records: {save_res.text}")
                            except Exception as save_err:
                                st.error(f"Error saving records: {save_err}")
                else:
                    st.warning("No dish leftovers detected in this frame above the confidence threshold.")
        else:
            st.markdown(
                """
                <div class="content-box" style="text-align:center; padding:3rem 1.5rem; color:#64748B;">
                    <div style="font-size:1.1rem; font-weight:600; color:#1E293B; margin-bottom:0.4rem;">No Image Loaded</div>
                    <div style="font-size:0.875rem;">Upload an image or capture a photo on the left to begin automated YOLOv8 waste analysis.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ===== PAGE 3: TOMORROW'S COOKING QUANTITIES =====
elif nav_page == "Tomorrow's Cooking Quantities":
    st.markdown(
        f"""
        <div class="page-title-block">
            <h2 class="page-title">Tomorrow's Cooking Quantities</h2>
            <p class="page-caption">{tomorrow.strftime('%A, %d %B %Y')} · Recommended cook volumes based on historical leftover patterns and forecasted attendance.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tomorrow_menu = fetch_api("menu/tomorrow", {"site_id": selected_site_id}) or STATIC_TOMORROW_MENU
    forecast = fetch_api("forecast", {"site_id": selected_site_id, "target_date": tomorrow.isoformat()}) or STATIC_FORECAST
    recs = fetch_api("recommendations", {"site_id": selected_site_id}) or STATIC_RECOMMENDATIONS

    if tomorrow_menu:
        st.markdown('<div class="section-header">Scheduled Menu for Tomorrow</div>', unsafe_allow_html=True)
        mdf = pd.DataFrame(tomorrow_menu)
        menu_cols = st.columns(len([m for m in MEAL_ORDER if not mdf[mdf["meal"] == m].empty]))
        idx = 0
        for meal in MEAL_ORDER:
            rows = mdf[mdf["meal"] == meal]
            if rows.empty:
                continue
            dishes = "<br>• ".join(sorted(rows["dish_name"].unique()))
            with menu_cols[idx]:
                st.markdown(
                    f"""
                    <div class="content-box" style="min-height:140px;">
                        <div style="font-size:0.8rem; font-weight:700; color:#1E3A5F; text-transform:uppercase; letter-spacing:0.04em;">{meal.capitalize()}</div>
                        <div style="font-size:0.75rem; color:#64748B; margin-bottom:0.5rem;">{MEAL_TIMES.get(meal, '')}</div>
                        <div style="font-size:0.85rem; color:#1E293B; line-height:1.4;">• {dishes}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            idx += 1

    if forecast:
        st.markdown('<div class="section-header">Recommended Cooking Plan</div>', unsafe_allow_html=True)
        fdf = pd.DataFrame(forecast)
        fdf["recommended_kg"] = fdf["recommended_cook_grams"] / 1000.0
        fdf["base_kg"] = fdf["base_cook_grams"] / 1000.0
        fdf["meal"] = fdf["meal"].apply(lambda m: str(m).capitalize())

        formatted_fdf = fdf[["meal", "dish_name", "predicted_attendance", "recommended_kg", "notes"]].rename(
            columns={
                "meal": "Meal Session",
                "dish_name": "Dish Name",
                "predicted_attendance": "Expected Diners",
                "recommended_kg": "Recommended Cook (kg)",
                "notes": "Adjustment Rationale",
            }
        )
        render_styled_table(
            formatted_fdf,
            numeric_cols=["Expected Diners", "Recommended Cook (kg)"],
            col_widths={"Meal Session": "15%", "Dish Name": "25%", "Expected Diners": "15%", "Recommended Cook (kg)": "18%", "Adjustment Rationale": "27%"},
        )

    st.markdown('<div class="section-header">Kitchen Action Suggestions</div>', unsafe_allow_html=True)
    if recs:
        for r in recs:
            p_class = "rec-priority-high" if r.get("priority") == "high" else "rec-priority-med"
            st.markdown(
                f"""
                <div class="rec-card-saas">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:0.95rem; font-weight:600; color:#1E293B;">{r['title']}</span>
                        <span class="{p_class}">{r['priority']}</span>
                    </div>
                    <p style="color:#475569; font-size:0.875rem; margin:0.4rem 0 0.5rem 0;">{r['suggestion']}</p>
                    <div style="color:#0F766E; font-size:0.8rem; font-weight:600;">
                        Expected monthly waste reduction: ~{r['expected_savings_kg']} kg
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No active kitchen adjustments needed currently.")


# ===== PAGE 4: FINANCIAL & CARBON IMPACT =====
elif nav_page == "Financial & Carbon Impact":
    st.markdown(
        """
        <div class="page-title-block">
            <h2 class="page-title">Financial & Carbon Impact</h2>
            <p class="page-caption">Cumulative ingredient value lost, wasted nutritional value, and environmental carbon footprint.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    impact = fetch_api("impact", {"site_id": selected_site_id}) or STATIC_IMPACT
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_metric_card(
            "Calories Wasted",
            f"{impact.get('total_calories_lost', 0):,.0f} kcal",
            "Lost dietary energy",
            "neutral",
        )
    with m2:
        render_metric_card(
            "Protein Lost",
            f"{impact.get('total_protein_kg', 0):,.1f} kg",
            "Institutional nutrition lost",
            "neutral",
        )
    with m3:
        render_metric_card(
            "Ingredient Value Lost",
            f"₹{impact.get('total_cost_rupees', 0):,.0f}",
            "Avoidable food budget waste",
            "negative",
        )
    with m4:
        render_metric_card(
            "Carbon Emissions",
            f"{impact.get('total_co2e_kg', 0):,.1f} kg",
            "CO₂ equivalent emissions",
            "negative",
        )

    meals_eq = int(impact.get("total_calories_lost", 0) / 650.0)
    st.markdown(
        f"""
        <div class="content-box" style="border-left: 4px solid #1E3A5F; margin-top: 1rem;">
            <div style="font-size:0.85rem; font-weight:600; color:#1E3A5F; text-transform:uppercase; letter-spacing:0.04em;">Social Nutrition Equivalent</div>
            <div style="font-size:0.95rem; color:#1E293B; margin-top:0.35rem;">
                The cumulative leftover calories recorded across plate returns represent approximately <strong>{meals_eq:,} complete meals</strong> (evaluated at standard institutional diet of 650 kcal per serving).
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ===== PAGE 5: MESS WASTE BENCHMARKS =====
elif nav_page == "Mess Waste Benchmarks":
    st.markdown(
        """
        <div class="page-title-block">
            <h2 class="page-title">Mess Waste Benchmarks</h2>
            <p class="page-caption">Kitchen waste performance metrics and grams leftover per diner across campus dining facilities.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    benchmarks = fetch_api("benchmarks") or STATIC_BENCHMARKS
    if benchmarks:
        df_bench = pd.DataFrame(benchmarks)
        df_bench_formatted = df_bench[
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
                "site_name": "Kitchen Facility",
                "total_waste_kg": "Total Leftover (kg)",
                "avg_daily_waste_kg": "Daily Average (kg)",
                "waste_percentage": "Leftover %",
                "waste_per_diner_grams": "Grams / Diner",
                "total_cost_rupees": "Cost Lost (₹)",
                "top_wasted_dish": "Highest Leftover Dish",
            }
        )

        st.markdown('<div class="section-header">Cross-Facility Performance Table</div>', unsafe_allow_html=True)
        render_styled_table(
            df_bench_formatted,
            numeric_cols=["Total Leftover (kg)", "Daily Average (kg)", "Leftover %", "Grams / Diner", "Cost Lost (₹)"],
        )

        fig_per = px.bar(
            df_bench,
            x="site_name",
            y="waste_per_diner_grams",
            title="Grams Leftover per Diner by Facility",
            labels={"site_name": "Facility", "waste_per_diner_grams": "Grams / Diner"},
            color_discrete_sequence=[CHART_NAVY],
        )
        fig_per = apply_chart_theme(fig_per, height=350)
        st.plotly_chart(fig_per, use_container_width=True)
    else:
        st.info("No benchmark metrics available.")


# ===== PAGE 6: WEEKLY MENU & EVENT SCHEDULE =====
elif nav_page == "Weekly Menu & Event Schedule":
    st.markdown(
        """
        <div class="page-title-block">
            <h2 class="page-title">Weekly Menu & Event Schedule</h2>
            <p class="page-caption">Institutional calendar events, attendance turnout modifiers, and diner satisfaction trends.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_p1, col_p2 = st.columns([3, 2], gap="large")

    with col_p1:
        st.markdown('<div class="section-header">Weekly Menu Schedule</div>', unsafe_allow_html=True)
        selected_dow = st.selectbox(
            "Select Day of Week",
            options=list(DAYS.keys()),
            format_func=lambda x: DAYS[x],
            index=today.weekday(),
            label_visibility="collapsed",
        )
        menu_items = fetch_api("menu", {"site_id": selected_site_id, "day_of_week": selected_dow}) or []
        if menu_items:
            df_m = pd.DataFrame(menu_items)
            df_m["meal"] = pd.Categorical(df_m["meal"], MEAL_ORDER, ordered=True)
            df_m = df_m.sort_values(["meal", "dish_name"])
            df_m["meal_name"] = df_m["meal"].apply(lambda m: str(m).capitalize())
            render_styled_table(
                df_m[["meal_name", "dish_name", "category"]].rename(
                    columns={
                        "meal_name": "Meal Session",
                        "dish_name": "Dish Name",
                        "category": "Course Type",
                    }
                )
            )
        else:
            st.info("No dishes scheduled for this day.")

        st.markdown('<div class="section-header">Institutional Calendar & Attendance Modifiers</div>', unsafe_allow_html=True)
        events = fetch_api("calendar") or []
        if events:
            df_e = pd.DataFrame(events)
            df_e["attendance_impact_pct"] = df_e["attendance_impact_pct"].apply(
                lambda p: f"{int(p):+d}%" if pd.notna(p) and not isinstance(p, str) else str(p)
            )
            render_styled_table(
                df_e[["event_date", "title", "event_type", "attendance_impact_pct", "notes"]].rename(
                    columns={
                        "event_date": "Date",
                        "title": "Event Name",
                        "event_type": "Category",
                        "attendance_impact_pct": "Turnout Impact",
                        "notes": "Kitchen Action Note",
                    }
                ),
                numeric_cols=["Turnout Impact"],
            )

    with col_p2:
        st.markdown('<div class="section-header">Diner Feedback Overview</div>', unsafe_allow_html=True)
        fb_stats = fetch_api("feedback/stats", {"site_id": selected_site_id}) or {}
        avg = fb_stats.get("average_rating")

        c_f1, c_f2 = st.columns(2)
        with c_f1:
            render_metric_card(
                "Average Rating",
                f"{avg:.1f} / 5.0" if avg else "None",
                "Diner survey satisfaction",
                "positive" if (avg and avg >= 4.0) else "neutral",
            )
        with c_f2:
            render_metric_card(
                "Responses",
                f"{fb_stats.get('total_responses', 0):,}",
                "Countertop QR submissions",
                "neutral",
            )

        reasons = fb_stats.get("reasons_breakdown", [])
        if reasons:
            df_fb = pd.DataFrame(reasons)
            fig_fb = px.bar(
                df_fb,
                x="count",
                y="reason_label",
                orientation="h",
                title="Primary Reasons for Leftover Food",
                labels={"count": "Response Count", "reason_label": "Reason Reported"},
                color_discrete_sequence=[CHART_NAVY],
            )
            fig_fb = apply_chart_theme(fig_fb, height=320)
            st.plotly_chart(fig_fb, use_container_width=True)


# ===== PAGE 7: DINER FEEDBACK & QR CODE =====
elif nav_page == "Diner Feedback & QR Code":
    st.markdown(
        """
        <div class="page-title-block">
            <h2 class="page-title">Diner Feedback & QR Code</h2>
            <p class="page-caption">Manage Hostel 1 plate return QR codes, fill out the diner form, and review comments.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c_qr1, c_qr2 = st.columns([1, 1], gap="large")
    with c_qr1:
        st.markdown('<div class="content-box">', unsafe_allow_html=True)
        st.markdown('<div class="section-header" style="margin-top:0;">Plate Return QR Standee</div>', unsafe_allow_html=True)
        st.image(qr_img_bytes, caption="Hostel 1 Permanent Countertop QR Code", width=280)
        st.markdown(
            f"""
            <div style="margin-top:0.75rem; font-size:0.875rem;">
                <strong>Direct URL:</strong> <a href="{qr_target_url}" target="_blank" style="color:#1E3A5F; font-weight:600; text-decoration:none;">{qr_target_url}</a>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-header">Live Diner Form Preview</div>', unsafe_allow_html=True)
        import streamlit.components.v1 as components

        components.iframe(qr_target_url, height=540, scrolling=True)

    with c_qr2:
        st.markdown('<div class="section-header" style="margin-top:0;">Recent Diner Reviews</div>', unsafe_allow_html=True)
        recent_fb = fetch_api("feedback", {"site_id": selected_site_id, "limit": 10}) or STATIC_FEEDBACK
        if recent_fb:
            for item in recent_fb:
                if item.get("comment"):
                    rating_num = int(item.get("rating") or 0)
                    stars = "★" * rating_num + "☆" * (5 - rating_num)
                    st.markdown(
                        f"""
                        <div class="feedback-card-saas">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="color:#D97706; font-size:0.9rem; font-weight:700;">{stars}</span>
                                <span style="color:#64748B; font-size:0.75rem; font-weight:600; text-transform:uppercase;">{item.get('meal', 'meal')}</span>
                            </div>
                            <p style="color:#1E293B; margin:0.4rem 0 0.5rem 0; font-size:0.875rem; line-height:1.4;">"{item['comment']}"</p>
                            <span style="color:#64748B; font-size:0.75rem;">{selected_site_name} Mess Diner</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        else:
            st.info("No comments submitted yet.")
