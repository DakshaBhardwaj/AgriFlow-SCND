import os
import pandas as pd

# Ensure the data directory exists
os.makedirs("data", exist_ok=True)

nodes_data = [
    # Farms (Supply points)
    {"node_id": "Farm_Shimla", "name": "Shimla Orchard", "type": "Farm", "lat": 31.1048, "lon": 77.1734, "fixed_cost": 0, "storage_cap": 0, "process_cap": 0},
    {"node_id": "Farm_Nagpur", "name": "Nagpur Orange Farm", "type": "Farm", "lat": 21.1458, "lon": 79.0882, "fixed_cost": 0, "storage_cap": 0, "process_cap": 0},
    {"node_id": "Farm_Nashik", "name": "Nashik Agri Land", "type": "Farm", "lat": 19.9975, "lon": 73.7898, "fixed_cost": 0, "storage_cap": 0, "process_cap": 0},
    
    # Potential Cold-Storage Hubs
    {"node_id": "Hub_Delhi", "name": "Delhi Cold Chain Hub", "type": "Hub", "lat": 28.6139, "lon": 77.2090, "fixed_cost": 250000, "storage_cap": 800, "process_cap": 1000},
    {"node_id": "Hub_Indore", "name": "Indore Regional Storage", "type": "Hub", "lat": 22.7196, "lon": 75.8577, "fixed_cost": 150000, "storage_cap": 500, "process_cap": 600},
    {"node_id": "Hub_Hyderabad", "name": "Hyderabad Distribution Hub", "type": "Hub", "lat": 17.3850, "lon": 78.4867, "fixed_cost": 180000, "storage_cap": 600, "process_cap": 750},
    
    # Markets (Metro Demand Points)
    {"node_id": "Market_Mumbai", "name": "Mumbai Wholesale Market", "type": "Market", "lat": 19.0760, "lon": 72.8777, "fixed_cost": 0, "storage_cap": 0, "process_cap": 0},
    {"node_id": "Market_Delhi", "name": "Azadpur Mandi Delhi", "type": "Market", "lat": 28.5355, "lon": 77.3910, "fixed_cost": 0, "storage_cap": 0, "process_cap": 0},
    {"node_id": "Market_Bengaluru", "name": "Bengaluru Central Market", "type": "Market", "lat": 12.9716, "lon": 77.5946, "fixed_cost": 0, "storage_cap": 0, "process_cap": 0}
]

df_nodes = pd.DataFrame(nodes_data)
df_nodes.to_csv("data/network_nodes.csv", index=False)
print("Saved: data/network_nodes.csv")

# ==========================================
# 2. PRODUCT SPECIFICATIONS (Crops in INR)
# ==========================================
product_data = [
    # Spoilage is monthly fraction lost in cold storage.
    # Transit loss is fraction lost per kilometer traveled.
    {
        "product_id": "Apples", 
        "price_per_ton": 90000,       # Wholesale value (₹/ton)
        "holding_cost": 1200,         # Storage cost per ton/month (₹)
        "shortage_penalty": 180000,   # Contract violation penalty (₹/ton)
        "spoilage_rate": 0.02,        # 2% storage loss/month
        "transit_loss_per_km": 0.00005 # 0.005% lost per km in transit
    },
    {
        "product_id": "Oranges", 
        "price_per_ton": 40000, 
        "holding_cost": 800, 
        "shortage_penalty": 80000, 
        "spoilage_rate": 0.06,        # 6% storage loss/month
        "transit_loss_per_km": 0.00015 # 0.015% lost per km in transit
    },
    {
        "product_id": "Onions", 
        "price_per_ton": 20000, 
        "holding_cost": 500, 
        "shortage_penalty": 40000, 
        "spoilage_rate": 0.04,        # 4% storage loss/month
        "transit_loss_per_km": 0.00010 # 0.01% lost per km in transit
    }
]

df_products = pd.DataFrame(product_data)
df_products.to_csv("data/product_specs.csv", index=False)
print("Saved: data/product_specs.csv")

# ==========================================
# 3. DEMAND & SUPPLY (6-Month Time Series)
# ==========================================
demand_supply_rows = []
# Horizon: Months 1 to 6
for month in range(1, 7):
    # --- SUPPLY GENERATION (Farms) ---
    # Shimla Apples: Peaks early (Month 1, 2)
    shimla_apples = 120 if month in [1, 2] else 15
    demand_supply_rows.append({"month": month, "node_id": "Farm_Shimla", "product_id": "Apples", "quantity": shimla_apples, "action": "Supply"})
    
    # Nagpur Oranges: Peaks late (Month 4, 5)
    nagpur_oranges = 150 if month in [4, 5] else 10
    demand_supply_rows.append({"month": month, "node_id": "Farm_Nagpur", "product_id": "Oranges", "quantity": nagpur_oranges, "action": "Supply"})
    
    # Nashik Onions: Peaks mid-season (Month 2, 3)
    nashik_onions = 200 if month in [2, 3] else 25
    demand_supply_rows.append({"month": month, "node_id": "Farm_Nashik", "product_id": "Onions", "quantity": nashik_onions, "action": "Supply"})
    
    # --- DEMAND GENERATION (Markets) ---
    # Demand is stable across the year in metros
    markets = {
        "Market_Mumbai": {"Apples": 40, "Oranges": 50, "Onions": 65},
        "Market_Delhi": {"Apples": 50, "Oranges": 45, "Onions": 75},
        "Market_Bengaluru": {"Apples": 35, "Oranges": 40, "Onions": 55}
    }
    for m_id, crops in markets.items():
        for crop, qty in crops.items():
            demand_supply_rows.append({"month": month, "node_id": m_id, "product_id": crop, "quantity": qty, "action": "Demand"})

    
df_demand_supply = pd.DataFrame(demand_supply_rows)
df_demand_supply.to_csv("data/demand_supply.csv", index=False)
print("Saved: data/demand_supply.csv")
print("\nAgricultural supply chain dataset successfully generated!")