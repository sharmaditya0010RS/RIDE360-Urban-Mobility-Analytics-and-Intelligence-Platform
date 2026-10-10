"""
RIDE360 | Urban Mobility Intelligence
A premium mobility analytics and operational intelligence platform.
"""

from __future__ import annotations

from html import escape

import streamlit as st
from common import cell, frame, setup_page

# ============================================================
# PAGE CONFIGURATION
# ============================================================

batch = setup_page(
    "",
)


# ============================================================
# SAFE HTML RENDERING
# ============================================================

def render_html(html: str):
    """Render HTML and CSS without Markdown parsing."""
    st.html(html)


# ============================================================
# GLOBAL CSS
# ============================================================

render_html("""
<style>

@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --background: #080D18;
    --surface: #101827;
    --surface-light: #162238;
    --border: rgba(148, 163, 184, 0.13);
    --primary: #38BDF8;
    --secondary: #818CF8;
    --text: #F1F5F9;
    --muted: #94A3B8;
}

.stApp {
    background:
        radial-gradient(
            ellipse at 85% 5%,
            rgba(56,189,248,0.09),
            transparent 35%
        ),
        radial-gradient(
            ellipse at 10% 80%,
            rgba(99,102,241,0.06),
            transparent 40%
        ),
        var(--background);

    color: var(--text);
    font-family: 'DM Sans', sans-serif;
}

.block-container {
    max-width: 1380px;
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

h1, h2, h3 {
    font-family: 'Space Grotesk', sans-serif !important;
}


/* ============================================================
   NAVIGATION
============================================================ */

.ride-navbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;

    padding: 20px 28px;
    margin-bottom: 28px;

    background: rgba(16,24,39,0.85);
    border: 1px solid var(--border);
    border-radius: 18px;
}

.brand {
    display: flex;
    align-items: center;
    gap: 16px;
}

.brand-logo {
    width: 55px;
    height: 55px;

    display: flex;
    justify-content: center;
    align-items: center;

    background: linear-gradient(
        135deg,
        #38BDF8,
        #2563EB
    );

    border-radius: 15px;

    font-family: 'Space Grotesk', sans-serif;
    font-size: 30px;
    font-weight: 700;
    color: #06111F;

    box-shadow: 0 8px 30px rgba(56,189,248,0.15);
}

.brand-name {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 27px;
    font-weight: 700;
    letter-spacing: -1px;
    color: #FFFFFF;
}

.brand-name span {
    color: var(--primary);
}

.brand-caption {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2px;
    color: var(--muted);
}

.nav-right {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1.5px;
    color: #94A3B8;
}


/* ============================================================
   HERO
============================================================ */

.hero {
    position: relative;
    overflow: hidden;

    padding: 75px 55px;
    margin-bottom: 45px;

    border-radius: 26px;

    background:
        radial-gradient(
            circle at 85% 50%,
            rgba(56,189,248,0.15),
            transparent 40%
        ),
        linear-gradient(
            135deg,
            #14213A,
            #0B1425 70%
        );

    border: 1px solid rgba(56,189,248,0.14);
}

.hero::before {
    content: "";
    position: absolute;

    width: 480px;
    height: 480px;

    right: -100px;
    top: -100px;

    border-radius: 50%;
    border: 1px solid rgba(56,189,248,0.15);

    box-shadow:
        0 0 0 60px rgba(56,189,248,0.025),
        0 0 0 120px rgba(56,189,248,0.018),
        0 0 0 180px rgba(56,189,248,0.012);
}

.hero-content {
    position: relative;
    z-index: 2;
    max-width: 760px;
}

.hero-eyebrow {
    display: inline-block;

    padding: 9px 16px;
    margin-bottom: 28px;

    border-radius: 30px;

    background: rgba(56,189,248,0.08);
    border: 1px solid rgba(56,189,248,0.20);

    color: #7DD3FC;

    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2px;
}

.hero-title {
    font-family: 'Space Grotesk', sans-serif;

    font-size: clamp(38px, 5vw, 64px);
    font-weight: 700;

    line-height: 1.15;
    letter-spacing: -2px;

    color: #FFFFFF;
    margin-bottom: 25px;
}

.hero-title span {
    background: linear-gradient(
        90deg,
        #38BDF8,
        #818CF8
    );

    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero-description {
    font-size: 16px;
    line-height: 1.9;
    color: #A8B8CE;
    max-width: 610px;
}

.hero-features {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 32px;
}

.feature-pill {
    padding: 10px 16px;

    border-radius: 9px;

    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.08);

    color: #CBD5E1;
    font-size: 12px;
    font-weight: 600;
}


/* ============================================================
   SECTION HEADERS
============================================================ */

.section-header {
    margin-top: 20px;
    margin-bottom: 25px;
}

.section-eyebrow {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 2.5px;
    color: var(--primary);
    margin-bottom: 10px;
}

.section-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 30px;
    font-weight: 700;
    color: #F8FAFC;
    margin-bottom: 8px;
}

.section-description {
    font-size: 14px;
    color: var(--muted);
}


/* ============================================================
   KPI CARDS
============================================================ */

.kpi-card {
    min-height: 165px;

    padding: 25px;

    border-radius: 18px;

    background: linear-gradient(
        145deg,
        #152138,
        #0E1728
    );

    border: 1px solid var(--border);

    transition: all 0.3s ease;
}

.kpi-card:hover {
    transform: translateY(-4px);
    border-color: rgba(56,189,248,0.4);
}

.kpi-label {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #94A3B8;
}

.kpi-value {
    font-family: 'Space Grotesk', sans-serif;

    font-size: 37px;
    font-weight: 700;

    color: #FFFFFF;

    margin-top: 20px;
    margin-bottom: 8px;
}

.kpi-description {
    color: #64748B;
    font-size: 12px;
}


/* ============================================================
   WORKSPACE CARDS
============================================================ */

.workspace-card {
    min-height: 195px;

    padding: 28px;

    border-radius: 18px;

    background: linear-gradient(
        145deg,
        #142038,
        #0D1627
    );

    border: 1px solid var(--border);

    transition: all 0.3s ease;
}

.workspace-card:hover {
    transform: translateY(-5px);

    border-color: rgba(56,189,248,0.4);

    box-shadow: 0 15px 35px rgba(0,0,0,0.2);
}

.workspace-number {
    font-family: 'Space Grotesk', sans-serif;

    font-size: 12px;
    font-weight: 700;
    letter-spacing: 2px;

    color: #38BDF8;

    margin-bottom: 24px;
}

.workspace-title {
    font-family: 'Space Grotesk', sans-serif;

    font-size: 20px;
    font-weight: 700;

    color: #F8FAFC;

    margin-bottom: 12px;
}

.workspace-description {
    font-size: 13px;
    line-height: 1.7;
    color: #94A3B8;
}


/* ============================================================
   STREAMLIT PAGE LINKS
============================================================ */

[data-testid="stPageLink"] {
    background: rgba(56,189,248,0.07);
    border: 1px solid rgba(56,189,248,0.18);

    border-radius: 10px;

    padding: 12px 16px;

    transition: all 0.3s ease;
}

[data-testid="stPageLink"]:hover {
    background: rgba(56,189,248,0.14);
    border-color: #38BDF8;
}

[data-testid="stPageLink"] a {
    color: #7DD3FC !important;
    font-weight: 700;
}


/* ============================================================
   FOOTER
============================================================ */

.ride-footer {
    text-align: center;

    padding: 35px 15px;
    margin-top: 55px;

    border-top: 1px solid var(--border);

    color: #64748B;
    font-size: 12px;
    line-height: 2;
}

.ride-footer strong {
    color: #38BDF8;
}


/* ============================================================
   RESPONSIVE
============================================================ */

@media (max-width: 768px) {

    .hero {
        padding: 45px 25px;
    }

    .hero-title {
        font-size: 38px;
    }

    .ride-navbar {
        padding: 16px;
    }

    .nav-right {
        display: none;
    }

    .kpi-card {
        min-height: 145px;
    }

    .workspace-card {
        min-height: 175px;
    }

}

</style>
""")


# ============================================================
# HELPERS
# ============================================================

def format_number(value):
    try:
        return f"{int(float(value)):,}"
    except (TypeError, ValueError, OverflowError):
        return "0"


def format_percentage(value):
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError, OverflowError):
        return "0.0%"


def kpi_card(label, value, description):
    render_html(f"""
    <div class="kpi-card">
        <div class="kpi-label">{escape(str(label))}</div>
        <div class="kpi-value">{escape(str(value))}</div>
        <div class="kpi-description">{escape(str(description))}</div>
    </div>
    """)


def section_header(eyebrow, title, description):
    render_html(f"""
    <div class="section-header">
        <div class="section-eyebrow">{escape(eyebrow)}</div>
        <div class="section-title">{escape(title)}</div>
        <div class="section-description">{escape(description)}</div>
    </div>
    """)


# ============================================================
# NAVBAR WITH SINGLE LOGO
# ============================================================

render_html("""
<div class="ride-navbar">
    <div class="brand">
        <div class="brand-logo">â—ˆ</div>
        <div>
            <div class="brand-name">RIDE<span>360</span></div>
            <div class="brand-caption">URBAN MOBILITY INTELLIGENCE PLATFORM</div>
        </div>
    </div>
    <div class="nav-right">
        DATA-DRIVEN MOBILITY PLATFORM
    </div>
</div>
""")


# ============================================================
# HERO BANNER
# ============================================================

# ============================================================
# HERO BANNER â€” FIXED
# ============================================================

render_html("""
<div class="hero">
    <div class="hero-content">

        <div class="hero-title">
            Smarter Mobility.<br>
            <span>Powered by Intelligence.</span>
        </div>

        <div class="hero-description">
            Transform ride-booking data into meaningful
            operational intelligence. Analyze travel demand,
            booking performance, fleet utilization,
            cancellation patterns and customer behavior
            through one unified analytics platform.
        </div>

        <div class="hero-features">
            <div class="feature-pill">Booking Analytics</div>
            <div class="feature-pill">Demand Intelligence</div>
            <div class="feature-pill">Fleet Performance</div>
            <div class="feature-pill">Customer Insights</div>
        </div>

    </div>
</div>
""")


# ============================================================
# EXECUTIVE KPI SECTION
# ============================================================

section_header(
    "EXECUTIVE OVERVIEW",
    "Mobility Performance Snapshot",
    "A high-level view of operational performance across the mobility network."
)

executive = frame("executive", batch)

if not executive.empty:

    total = cell(
        executive,
        "total_booking_records",
        default=0
    )

    completed = cell(
        executive,
        "completed_bookings",
        default=0
    )

    cancelled = cell(
        executive,
        "cancelled_bookings",
        default=0
    )

    completion_rate = cell(
        executive,
        "completion_rate_pct",
        default=0
    )

    col1, col2, col3, col4 = st.columns(
        4,
        gap="medium"
    )

    with col1:
        kpi_card(
            "Total Bookings",
            format_number(total),
            "Total ride booking records"
        )

    with col2:
        kpi_card(
            "Completed Rides",
            format_number(completed),
            "Successfully completed journeys"
        )

    with col3:
        kpi_card(
            "Cancelled Rides",
            format_number(cancelled),
            "Cancelled booking records"
        )

    with col4:
        kpi_card(
            "Completion Rate",
            format_percentage(completion_rate),
            "Overall booking fulfillment"
        )

else:

    st.info(
        "Executive analytics will appear when warehouse data becomes available."
    )


# ============================================================
# WORKSPACE SECTION
# ============================================================

st.markdown("<br><br>", unsafe_allow_html=True)

section_header(
    "ANALYTICS WORKSPACES",
    "Explore Mobility Intelligence",
    "Seven specialized workspaces designed to uncover actionable insights."
)


workspaces = [

    (
        "01",
        "Executive Pulse",
        "Monitor booking outcomes, operational baselines and performance trends.",
        "pages/1_Overview.py"
    ),

    (
        "02",
        "Demand Signals",
        "Understand daily demand, peak booking hours and seasonal patterns.",
        "pages/2_Demand.py"
    ),

    (
        "03",
        "Service Reliability",
        "Investigate cancellation drivers, service risks and booking reliability.",
        "pages/3_Cancellations.py"
    ),

    (
        "04",
        "Fleet Intelligence",
        "Explore vehicle-category performance, booking mix and revenue contribution.",
        "pages/4_Vehicles.py"
    ),

    (
        "05",
        "Network Intelligence",
        "Discover pickup hotspots, destination trends and high-demand corridors.",
        "pages/5_Locations.py"
    ),

    (
        "06",
        "Customer Signals",
        "Analyze booking frequency, customer activity and behavioral segments.",
        "pages/6_Customers.py"
    ),

    (
        "07",
        "Report Center",
        "Access Power BI reports, PDF insights, Excel files and analytical deliverables.",
        "pages/7_Report_Center.py"
    ),

]


# ============================================================
# WORKSPACE GRID
# ============================================================

for offset in range(0, len(workspaces), 3):

    columns = st.columns(
        3,
        gap="medium"
    )

    for col, workspace in zip(
        columns,
        workspaces[offset:offset + 3]
    ):

        number, title, description, path = workspace

        with col:

            render_html(f"""
            <div class="workspace-card">
                <div class="workspace-number">
                    WORKSPACE {escape(number)}
                </div>
                <div class="workspace-title">
                    {escape(title)}
                </div>
                <div class="workspace-description">
                    {escape(description)}
                </div>
            </div>
            """)

            st.page_link(
                path,
                label="Explore Workspace â†’",
                width='stretch'
            )


# ============================================================
# FOOTER
# ============================================================

render_html(f"""
<div class="ride-footer">
    <strong>RIDE360</strong> |
    Urban Mobility Intelligence Platform

    <br>

    Analytical Batch: {escape(str(batch))}
    &nbsp; | &nbsp;
    PostgreSQL Analytical Warehouse
    &nbsp; | &nbsp;
    Read-Only Reporting

    <br>

    Â© 2026 RIDE360. Move Smarter With Data.
</div>
""")
