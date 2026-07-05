import os
import sys

# Dynamic path resolution: guarantees imports work when running streamlit
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

import streamlit as st
import pandas as pd
from src.runner import run_optimization
from src.data_loader import AgriDataLoader
from src.visualizer import (
    plot_supply_chain_map,
    plot_cost_breakdown,
    plot_inventory_levels,
    plot_shortages
)

# Set up Streamlit Page Layout
st.set_page_config(
    page_title="Agri-Supply Chain Optimizer",
    layout="wide"
)

# Inject Glassnode Design Tokens via Custom CSS
st.markdown("""
<style>
/* Import Inter Font */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');

/* Base Styles */
html, body, [class*="css"], .stApp, .stMarkdown, p, h1, h2, h3, h4, h5, h6, span, button, label, input {
    font-family: 'Inter', sans-serif !important;
}

/* Core Typography Colors for Maximum Readability (excluding span/div to protect custom colors) */
body, .stMarkdown p, p, li, label {
    color: #333333 !important; /* Graphite - secondary neutral, highly legible */
}

h1, h2, h3, h4, h5, h6 {
    color: #000000 !important; /* Pure Black - heading headers */
}

/* Sidebar Text and Labels */
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4, [data-testid="stSidebar"] h5, [data-testid="stSidebar"] h6 {
    color: #000000 !important;
}

[data-testid="stSidebar"] label {
    color: #333333 !important;
    font-weight: 500 !important;
}

/* Muted Descriptions and Captions */
small, .stCaption, [data-testid="stHelp"] {
    color: #5a5a5a !important; /* Iron */
}

/* Input text focus */
select, option, input {
    color: #000000 !important;
}

/* Page Canvas Background: Cloud (#edeff2) */
.stApp {
    background-color: #edeff2 !important;
}

/* Sidebar Background: Paper (#f7f8fa) with Mist (#dedfe1) border */
[data-testid="stSidebar"] {
    background-color: #f7f8fa !important;
    border-right: 1px solid #dedfe1 !important;
}

/* Metric Cards: White surfaces, Mist borders, 2px radius */
[data-testid="metric-container"] {
    background-color: #ffffff !important;
    border: 1px solid #dedfe1 !important;
    border-radius: 2px !important;
    padding: 16px !important;
    box-shadow: rgba(0, 0, 0, 0.04) 0px 2px 4px 0px !important;
}

[data-testid="stMetricLabel"] {
    color: #6f6f6f !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}

[data-testid="stMetricValue"] {
    color: #000000 !important;
    font-size: 26px !important;
    font-weight: 700 !important;
    letter-spacing: -0.5px !important;
}

/* Streamlit Tab Customization: Restrained fonts and line highlights */
[data-testid="stTabBar"] {
    border-bottom: 1px solid #dedfe1 !important;
    background-color: transparent !important;
}

button[data-baseweb="tab"] {
    font-size: 14px !important;
    font-weight: 500 !important;
    color: #5a5a5a !important;
    background-color: transparent !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #000000 !important;
    border-bottom: 2px solid #000000 !important;
}

/* Interactive Buttons: Near-rectangular solid black silhouettes with forced white text */
div.stButton > button:first-child, div.stButton > button:first-child * {
    background-color: #000000 !important;
    color: #ffffff !important;
    border: 1px solid #000000 !important;
    border-radius: 2px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 8px 18px !important;
    transition: all 0.15s ease !important;
}

div.stButton > button:first-child:hover, div.stButton > button:first-child:hover * {
    background-color: #1a1a1a !important;
    border-color: #1a1a1a !important;
    color: #ffffff !important;
}

/* Forms and Numerical Inputs: 2px radius and Mist borders with highly visible dark text */
div[data-baseweb="input"] {
    border-radius: 2px !important;
    border: 1px solid #dedfe1 !important;
    background-color: #ffffff !important;
}

div[data-baseweb="input"] input {
    color: #000000 !important;
    background-color: #ffffff !important;
    -webkit-text-fill-color: #000000 !important; /* Prevents browser overrides */
}

/* Text Element Highlights (Glacier Tint #e2e7fc wash) */
.highlight {
    background-color: #e2e7fc !important;
    color: #000000 !important;
    padding: 2px 6px !important;
    border-radius: 2px !important;
    font-weight: 700 !important;
}
</style>
""", unsafe_allow_html=True)

# Hero Header Band (Light display styling)
st.write(
    "<h1 style='font-size: 32px; font-weight: 700; color: #000000; margin-bottom: 8px; letter-spacing: -0.8px;'>"
    "Perishable Agri-Supply Chain <span class='highlight'>Network Design</span> Optimizer"
    "</h1>",
    unsafe_allow_html=True
)
st.markdown("""
<div style='font-size: 14px; color: #5a5a5a; margin-bottom: 24px;'>
This operations research application uses <b>Mixed-Integer Linear Programming (MILP)</b> to design and optimize regional crop distribution. 
It balances monthly cold-storage lease choices (Delhi, Indore, Hyderabad) against transit losses and seasonal crop harvesting schedules in INR (₹).
</div>
""", unsafe_allow_html=True)

# ==========================================
# 1. SIDEBAR PARAMETER CONTROL
# ==========================================
st.sidebar.header("Logistics Parameter Controls")

# Shipping Cost Slider (₹/ton-km)
base_ship_cost = st.sidebar.slider(
    "Base Shipping Rate (₹ / Ton-KM)",
    min_value=5.0,
    max_value=50.0,
    value=15.0,
    step=1.0,
    help="Transport tariff per ton of crop moved per kilometer"
)

st.sidebar.subheader("Hub Fixed Monthly Lease Costs (₹)")
fixed_delhi = st.sidebar.number_input("Delhi Hub Fixed Cost", value=250000, step=10000)
fixed_indore = st.sidebar.number_input("Indore Hub Fixed Cost", value=150000, step=10000)
fixed_hyderabad = st.sidebar.number_input("Hyderabad Hub Fixed Cost", value=180000, step=10000)

# ==========================================
# 2. RUN OPTIMIZATION
# ==========================================
# Read node profiles to render the baseline network maps and charts
loader = AgriDataLoader("data")
loader.load_all_data()
nodes_df = loader.nodes_df.copy()

# Bundle UI parameters into an in-memory dictionary
custom_fixed_costs = {
    "Hub_Delhi": fixed_delhi,
    "Hub_Indore": fixed_indore,
    "Hub_Hyderabad": fixed_hyderabad
}

if st.sidebar.button("Run Optimizer", type="primary"):
    with st.spinner("Solving mathematical model..."):
        try:
            # Pass controls directly in-memory to the solver (no disk I/O)
            res = run_optimization(
                base_shipping_cost=base_ship_cost,
                custom_fixed_costs=custom_fixed_costs
            )
        except Exception as e:
            st.error(f"Solver Error: {e}")
            res = None
            
        if res and res["status"] == "Optimal":
            st.success("Solver status: OPTIMAL SOLUTION FOUND!")
            
            summary = res["summary"]
            
            # --- KPI Cards ---
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            with kpi1:
                st.metric("Total System Cost", f"₹{summary['Total Cost (INR)']:,}")
            with kpi2:
                total_shipping = summary["Farm to Hub Shipping Cost (INR)"] + summary["Hub to Market Shipping Cost (INR)"]
                st.metric("Total Transportation Cost", f"₹{total_shipping:,}")
            with kpi3:
                st.metric("Fixed Hub Leasing Cost", f"₹{summary['Fixed Hub Lease Cost (INR)']:,}")
            with kpi4:
                st.metric("Shortage Penalty Paid", f"₹{summary['Shortage Penalty Cost (INR)']:,}")

            # --- Layout Tabs ---
            tab_map, tab_metrics, tab_data = st.tabs([
                "Route Map", 
                "Inventory & Supply Gap Analysis", 
                "Detailed Logistics Schedules"
            ])
            
            with tab_map:
                col_map_left, col_map_right = st.columns([2, 1])
                with col_map_left:
                    map_fig = plot_supply_chain_map(nodes_df, res["farm_flows"], res["market_flows"])
                    st.plotly_chart(map_fig, use_container_width=True)
                with col_map_right:
                    st.subheader("Hub Selection Status")
                    st.dataframe(
                        res["hubs"][["hub_id", "status", "fixed_cost", "storage_capacity"]],
                        use_container_width=True
                    )
                    # Pure HTML legend to prevent markdown parser from stripping styles
                    st.write("""
                    <div style="font-size: 14px; line-height: 1.8; margin-top: 10px;">
                        <strong>Legend:</strong><br>
                        <span style="color:#10B981; font-size:18px; margin-right: 5px;">■</span> <b>Farms</b>: Crop harvesting points.<br>
                        <span style="color:#F59E0B; font-size:18px; margin-right: 5px;">■</span> <b>Hubs</b>: Candidate cold-storage consolidation points.<br>
                        <span style="color:#EF4444; font-size:18px; margin-right: 5px;">■</span> <b>Markets</b>: Urban metro demand points.
                    </div>
                    """, unsafe_allow_html=True)
                    
            with tab_metrics:
                col_chart_left, col_chart_right = st.columns([1, 1])
                with col_chart_left:
                    pie_fig = plot_cost_breakdown(summary)
                    st.plotly_chart(pie_fig, use_container_width=True)
                with col_chart_right:
                    st.subheader("Cost Distribution")
                    st.markdown("""
                    The pie chart shows the breakdown of the total logistics budget. 
                    * **Shortage Penalty**: High penalties mean there is a supply deficit due to seasonal harvesting caps.
                    * **Leasing vs Transport**: Raising lease costs will force the model to close hubs and increase transport runs.
                    """)
                
                st.divider()
                
                col_inv_left, col_inv_right = st.columns([1, 1])
                with col_inv_left:
                    inv_fig = plot_inventory_levels(res["inventory"])
                    st.plotly_chart(inv_fig, use_container_width=True)
                with col_inv_right:
                    shortage_fig = plot_shortages(res["shortages"])
                    st.plotly_chart(shortage_fig, use_container_width=True)
                    
            with tab_data:
                st.subheader("Farm-to-Hub Shipping Flows")
                if not res["farm_flows"].empty:
                    st.dataframe(res["farm_flows"], use_container_width=True)
                else:
                    st.write("No flow recorded.")
                    
                st.subheader("Hub-to-Market Shipping Flows")
                if not res["market_flows"].empty:
                    st.dataframe(res["market_flows"], use_container_width=True)
                else:
                    st.write("No flow recorded.")
                    
                st.subheader("Hub Monthly Inventory Levels")
                if not res["inventory"].empty:
                    st.dataframe(res["inventory"], use_container_width=True)
                else:
                    st.write("No inventory held.")
        else:
            st.error("Failed to solve the model. Verify data configurations.")
else:
    st.info("Adjust parameters in the sidebar and click **Run Optimizer** to solve.")