import os
import sys
import pytest
import pyomo.environ as pyo

# Dynamic path resolution: guarantees imports work when running tests directly
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.runner import run_optimization

def test_solver_optimal():
    """
    Test 1: Verify that the MILP model compiles and solves to optimality using GLPK.
    """
    res = run_optimization(solver_name="glpk")
    assert res["status"] == "Optimal"
    assert "summary" in res
    assert res["summary"]["Total Cost (INR)"] > 0

def test_hub_linking_constraints():
    """
    Test 2: Verify Big-M linking constraints. 
    Closed hubs (y_h = 0) must have exactly ZERO inflow, outflow, and inventory.
    """
    res = run_optimization()
    hubs_df = res["hubs"]
    
    # Filter hubs that the optimizer chose to keep CLOSED
    closed_hubs = hubs_df[hubs_df["status"] == "CLOSED"]["hub_id"].tolist()
    
    # 1. Verify no flow from farm to closed hubs
    farm_flows = res["farm_flows"]
    if not farm_flows.empty:
        closed_inflows = farm_flows[farm_flows["hub_id"].isin(closed_hubs)]
        assert closed_inflows.empty, "Closed hubs cannot receive farm inflows!"
        
    # 2. Verify no flow from closed hubs to markets
    market_flows = res["market_flows"]
    if not market_flows.empty:
        closed_outflows = market_flows[market_flows["hub_id"].isin(closed_hubs)]
        assert closed_outflows.empty, "Closed hubs cannot send market outflows!"
        
    # 3. Verify no inventory is stored in closed hubs
    inventory = res["inventory"]
    if not inventory.empty:
        closed_inventory = inventory[inventory["hub_id"].isin(closed_hubs)]
        assert closed_inventory.empty, "Closed hubs cannot store inventory!"

def test_flow_conservation_with_decay():
    """
    Test 3: Verify mathematical flow conservation with decay:
    Ending Inventory (t) = Starting Inventory (t-1)*(1-spoilage) + Inflow (t)*(1-transit_loss) - Outflow (t)
    """
    res = run_optimization()
    hubs_df = res["hubs"]
    open_hubs = hubs_df[hubs_df["status"] == "OPEN"]["hub_id"].tolist()
    
    if not open_hubs:
        pytest.skip("No open hubs to verify conservation.")
        
    # Test on the first open hub (e.g., Delhi or Indore)
    test_hub = open_hubs[0]
    
    # Fetch parameters to calculate transit loss and spoilage rates
    from src.data_loader import AgriDataLoader
    loader = AgriDataLoader()
    loader.load_all_data()
    params = loader.get_parameters()
    dist_fh, _ = loader.get_distance_dictionaries()
    
    farm_flows = res["farm_flows"]
    market_flows = res["market_flows"]
    inventory = res["inventory"]
    
    spoilage_rates = params["spoilage_rates"]
    transit_losses = params["transit_losses"]
    
    # Check conservation across all months (1-6) and crops
    for t in range(1, 7):
        for crop in ["Apples", "Oranges", "Onions"]:
            # 1. Total inflow into the hub in month t (after transit loss)
            inflow_val = 0.0
            if not farm_flows.empty:
                sub_in = farm_flows[(farm_flows["hub_id"] == test_hub) & 
                                    (farm_flows["month"] == t) & 
                                    (farm_flows["crop"] == crop)]
                for _, row in sub_in.iterrows():
                    dist = dist_fh[(row["farm_id"], test_hub)]
                    loss_factor = 1.0 - transit_losses[crop] * dist
                    inflow_val += row["shipped_tons"] * loss_factor
                    
            # 2. Total outflow from the hub to all metro markets in month t (before transit loss out of hub)
            outflow_val = 0.0
            if not market_flows.empty:
                sub_out = market_flows[(market_flows["hub_id"] == test_hub) & 
                                       (market_flows["month"] == t) & 
                                       (market_flows["crop"] == crop)]
                outflow_val = sub_out["shipped_tons"].sum()
                
            # 3. Ending inventory at month t
            stored_val = 0.0
            if not inventory.empty:
                sub_inv = inventory[(inventory["hub_id"] == test_hub) & 
                                    (inventory["month"] == t) & 
                                    (inventory["crop"] == crop)]
                if not sub_inv.empty:
                    stored_val = sub_inv.iloc[0]["stored_tons"]
                    
            # 4. Carry-over inventory from month t-1 (after monthly spoilage rate)
            prev_stored_val = 0.0
            if t > 1 and not inventory.empty:
                sub_inv_prev = inventory[(inventory["hub_id"] == test_hub) & 
                                         (inventory["month"] == t-1) & 
                                         (inventory["crop"] == crop)]
                if not sub_inv_prev.empty:
                    prev_stored_val = sub_inv_prev.iloc[0]["stored_tons"]
            
            prev_stored_after_spoilage = prev_stored_val * (1.0 - spoilage_rates[crop])
            
            # Conservation check: Carry-over + Inflow = Outflow + Ending Stock
            left_side = prev_stored_after_spoilage + inflow_val
            right_side = outflow_val + stored_val
            
            # Assert equality within a small numerical margin (0.2 tons) to account for float precision
            assert left_side == pytest.approx(right_side, abs=0.2), \
                f"Conservation mismatch at {test_hub} for {crop} in month {t}: In={left_side}, Out={right_side}"