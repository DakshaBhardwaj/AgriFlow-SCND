import os
import sys
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# Dynamic path resolution
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

def plot_supply_chain_map(nodes_df, farm_flows, market_flows):
    """
    Creates an interactive map of India showing nodes and shipping routes.
    """
    fig = go.Figure()

    # 1. Draw active shipping routes (Farms -> Hubs)
    # Using None-separator to draw multiple lines efficiently in a single trace
    route_lat = []
    route_lon = []
    route_text = []
    
    if not farm_flows.empty:
        # Group to find total flows across the horizon
        agg_farm = farm_flows.groupby(["farm_id", "hub_id"])["shipped_tons"].sum().reset_index()
        for _, row in agg_farm.iterrows():
            f_node = nodes_df[nodes_df["node_id"] == row["farm_id"]].iloc[0]
            h_node = nodes_df[nodes_df["node_id"] == row["hub_id"]].iloc[0]
            route_lat.extend([f_node["lat"], h_node["lat"], None])
            route_lon.extend([f_node["lon"], h_node["lon"], None])
            route_text.append(f"Farm {f_node['name']} -> Hub {h_node['name']}: {row['shipped_tons']:.1f} tons total")

    # 2. Draw active shipping routes (Hubs -> Markets)
    if not market_flows.empty:
        agg_market = market_flows.groupby(["hub_id", "market_id"])["shipped_tons"].sum().reset_index()
        for _, row in agg_market.iterrows():
            h_node = nodes_df[nodes_df["node_id"] == row["hub_id"]].iloc[0]
            m_node = nodes_df[nodes_df["node_id"] == row["market_id"]].iloc[0]
            route_lat.extend([h_node["lat"], m_node["lat"], None])
            route_lon.extend([h_node["lon"], m_node["lon"], None])
            route_text.append(f"Hub {h_node['name']} -> Market {m_node['name']}: {row['shipped_tons']:.1f} tons total")

    # Add routes trace
    fig.add_trace(go.Scattergeo(
        lon=route_lon,
        lat=route_lat,
        mode="lines",
        line=dict(width=2, color="#4F46E5"),
        name="Shipping Lanes",
        opacity=0.6,
        hoverinfo="skip"
    ))

    # 3. Add Nodes
    colors = {"Farm": "#10B981", "Hub": "#F59E0B", "Market": "#EF4444"}
    symbols = {"Farm": "circle", "Hub": "hexagon-open", "Market": "square"}
    
    for n_type in ["Farm", "Hub", "Market"]:
        df_sub = nodes_df[nodes_df["type"] == n_type]
        fig.add_trace(go.Scattergeo(
            lon=df_sub["lon"],
            lat=df_sub["lat"],
            mode="markers+text",
            marker=dict(
                size=12 if n_type != "Hub" else 15,
                color=colors[n_type],
                symbol=symbols[n_type],
                line=dict(width=2, color="white")
            ),
            text=df_sub["name"],
            textposition="top center",
            name=n_type + "s",
            hovertemplate="<b>%{text}</b><br>Lat: %{lat}<br>Lon: %{lon}<extra></extra>"
        ))

    # Center map on India
    fig.update_layout(
        title=dict(text="Indian Perishable Supply Chain Logistics Network", font=dict(size=16)),
        geo=dict(
            projection_type="mercator",
            showland=True,
            landcolor="#F3F4F6",
            subunitcolor="white",
            countrycolor="#D1D5DB",
            showlakes=False,
            showcountries=True,
            lonaxis_range=[68.0, 98.0],
            lataxis_range=[8.0, 36.0],
            fitbounds="locations"
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        height=550,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.7)")
    )
    return fig


def plot_cost_breakdown(summary_dict):
    """
    Creates a pie chart showing total supply chain cost proportions.
    """
    # Remove Total Cost to avoid double counting
    plot_data = {k: v for k, v in summary_dict.items() if "Total" not in k}
    
    df_costs = pd.DataFrame({
        "Cost Category": list(plot_data.keys()),
        "Value (INR)": list(plot_data.values())
    })
    
    # Custom color palette (sleek dark mode friendly)
    colors = ["#6366F1", "#3B82F6", "#10B981", "#EF4444", "#8B5CF6"]
    
    fig = px.pie(
        df_costs,
        names="Cost Category",
        values="Value (INR)",
        color_discrete_sequence=colors,
        hole=0.4
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        height=320,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    return fig

def plot_inventory_levels(inventory_df):
    """
    Bar chart showing monthly cold storage occupancy levels by crop type.
    """
    if inventory_df.empty:
        fig = go.Figure()
        fig.update_layout(title="No Inventory Stored", height=300)
        return fig
        
    fig = px.bar(
        inventory_df,
        x="month",
        y="stored_tons",
        color="crop",
        facet_col="hub_id",
        title="Monthly Cold Storage Inventory Levels",
        labels={"month": "Month", "stored_tons": "Stored Quantity (Tons)", "crop": "Crop Type"},
        color_discrete_sequence=["#3B82F6", "#F59E0B", "#10B981"]
    )
    fig.update_layout(height=350, margin=dict(t=50, b=40))
    return fig

def plot_shortages(shortages_df):
    """
    Bar chart showing unmet crop demand across cities.
    """
    if shortages_df.empty:
        fig = go.Figure()
        fig.update_layout(title="Zero Unmet Demand (Perfect Supply Match)", height=300)
        return fig
        
    fig = px.bar(
        shortages_df,
        x="month",
        y="shortage_tons",
        color="crop",
        facet_col="market_id",
        title="Unmet Market Demand (Shortage)",
        labels={"month": "Month", "shortage_tons": "Shortage (Tons)"},
        color_discrete_sequence=["#EF4444", "#EC4899", "#8B5CF6"]
    )
    fig.update_layout(height=350, margin=dict(t=50, b=40))
    return fig