import os
import sys

# Dynamic path resolution: Appends the parent folder of 'src' to sys.path
# This guarantees imports work when running `python src/runner.py` directly.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Standard imports continue normally
import pyomo.environ as pyo
import pandas as pd
from src.data_loader import AgriDataLoader
from src.model import build_supply_chain_model

def run_optimization(data_dir="data", base_shipping_cost=15.0, solver_name="glpk", custom_fixed_costs=None):
    """
    Loads network data, constructs the MILP model, solves it, 
    and returns parsed results as structured pandas DataFrames.
    """
    # 1. Load data
    loader = AgriDataLoader(data_dir)
    loader.load_all_data()
    
    farms, hubs, markets, crops, months = loader.get_sets()
    dist_farm_hub, dist_hub_market = loader.get_distance_dictionaries()
    params = loader.get_parameters()
    
    # In-memory parameter override (eliminates disk writing)
    if custom_fixed_costs:
        for hub_id, cost in custom_fixed_costs.items():
            if hub_id in params["fixed_costs"]:
                params["fixed_costs"][hub_id] = cost
    
    # 2. Build model
    model = build_supply_chain_model(
        farms, hubs, markets, crops, months,
        dist_farm_hub, dist_hub_market, params,
        base_shipping_cost=base_shipping_cost
    )
    
    # 3. Solve model
    print(f"Solving MILP model using solver: {solver_name}...")
    solver = pyo.SolverFactory(solver_name)
    
    try:
        results = solver.solve(model, tee=False)
    except Exception as e:
        print(f"\n[ERROR] Solver execution failed. Ensure '{solver_name}' is installed and on PATH.")
        raise e

    # Check solver status
    tc = results.solver.termination_condition
    if tc != pyo.TerminationCondition.optimal:
        print(f"\n[WARNING] Optimization ended with non-optimal condition: {tc}")
        return {"status": "Non-Optimal", "condition": str(tc)}
        
    print("Optimization completed successfully. Extracting results...")

    # ==========================================
    # 4. RESULTS EXTRACTION
    # ==========================================
    
    # A. Hub Decisions
    hub_decisions = []
    for h in model.H:
        opened = bool(model.y[h].value > 0.5)
        hub_decisions.append({
            "hub_id": h,
            "status": "OPEN" if opened else "CLOSED",
            "fixed_cost": model.fixed_costs[h],
            "storage_capacity": model.storage_caps[h],
            "processing_capacity": model.processing_caps[h]
        })
    df_hubs = pd.DataFrame(hub_decisions)

    # B. Farm to Hub Flows
    farm_flows = []
    for f in model.F:
        for h in model.H:
            for c in model.C:
                for t in model.T:
                    qty = model.x[f, h, c, t].value
                    if qty and qty > 1e-4:
                        dist = model.dist_fh[f, h]
                        ship_cost = qty * dist * model.ship_cost.value
                        farm_flows.append({
                            "month": t, "farm_id": f, "hub_id": h, "crop": c,
                            "shipped_tons": round(qty, 2), "distance_km": dist,
                            "shipping_cost_inr": round(ship_cost, 2)
                        })
    df_farm_flows = pd.DataFrame(farm_flows) if farm_flows else pd.DataFrame(
        columns=["month", "farm_id", "hub_id", "crop", "shipped_tons", "distance_km", "shipping_cost_inr"]
    )

    # C. Hub to Market Flows
    market_flows = []
    for h in model.H:
        for m in model.M:
            for c in model.C:
                for t in model.T:
                    qty = model.z[h, m, c, t].value
                    if qty and qty > 1e-4:
                        dist = model.dist_hm[h, m]
                        arriving = qty * (1.0 - model.transit_losses[c] * dist)
                        ship_cost = qty * dist * model.ship_cost.value
                        market_flows.append({
                            "month": t, "hub_id": h, "market_id": m, "crop": c,
                            "shipped_tons": round(qty, 2), "arriving_tons": round(max(0.0, arriving), 2),
                            "distance_km": dist, "shipping_cost_inr": round(ship_cost, 2)
                        })
    df_market_flows = pd.DataFrame(market_flows) if market_flows else pd.DataFrame(
        columns=["month", "hub_id", "market_id", "crop", "shipped_tons", "arriving_tons", "distance_km", "shipping_cost_inr"]
    )

    # D. Inventory Stored
    inventory = []
    for h in model.H:
        for c in model.C:
            for t in model.T:
                qty = model.I[h, c, t].value
                if qty and qty > 1e-4:
                    holding_cost = qty * model.holding_costs[c]
                    inventory.append({
                        "month": t, "hub_id": h, "crop": c,
                        "stored_tons": round(qty, 2), "holding_cost_inr": round(holding_cost, 2)
                    })
    df_inventory = pd.DataFrame(inventory) if inventory else pd.DataFrame(
        columns=["month", "hub_id", "crop", "stored_tons", "holding_cost_inr"]
    )

    # E. Shortages
    shortages = []
    for m in model.M:
        for c in model.C:
            for t in model.T:
                qty = model.s[m, c, t].value
                if qty and qty > 1e-4:
                    penalty = qty * model.shortage_penalties[c]
                    shortages.append({
                        "month": t, "market_id": m, "crop": c,
                        "shortage_tons": round(qty, 2), "penalty_cost_inr": round(penalty, 2)
                    })
    df_shortages = pd.DataFrame(shortages) if shortages else pd.DataFrame(
        columns=["month", "market_id", "crop", "shortage_tons", "penalty_cost_inr"]
    )

    # F. Vectorized Financial Summary (C-optimized aggregation, no loops)
    total_cost_val = pyo.value(model.Obj)
    total_fixed_cost = sum(row["fixed_cost"] for _, row in df_hubs.iterrows() if row["status"] == "OPEN") * len(model.T)
    total_farm_shipping = df_farm_flows["shipping_cost_inr"].sum()
    total_market_shipping = df_market_flows["shipping_cost_inr"].sum()
    total_holding = df_inventory["holding_cost_inr"].sum()
    total_penalty = df_shortages["penalty_cost_inr"].sum()
    
    summary = {
        "Total Cost (INR)": round(total_cost_val, 2),
        "Fixed Hub Lease Cost (INR)": round(total_fixed_cost, 2),
        "Farm to Hub Shipping Cost (INR)": round(total_farm_shipping, 2),
        "Hub to Market Shipping Cost (INR)": round(total_market_shipping, 2),
        "Inventory Holding Cost (INR)": round(total_holding, 2),
        "Shortage Penalty Cost (INR)": round(total_penalty, 2)
    }

    return {
        "status": "Optimal",
        "hubs": df_hubs,
        "farm_flows": df_farm_flows,
        "market_flows": df_market_flows,
        "inventory": df_inventory,
        "shortages": df_shortages,
        "summary": summary
    }

if __name__ == "__main__":
    try:
        res = run_optimization()
        print("\n--- OPTIMIZATION SUMMARY ---")
        for k, v in res["summary"].items():
            print(f"{k}: ₹{v:,}")
            
        print("\n--- HUB OPENING DECISIONS ---")
        print(res["hubs"])
    except Exception as e:
        print(f"Failed to run direct test: {e}")