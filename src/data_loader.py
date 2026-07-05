import pandas as pd
import numpy as np

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Computes the great-circle distance in kilometers between two points
    on the Earth using their decimal latitude and longitude.
    """
    # Convert degrees to radians
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    
    # Differences in coordinates
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # Haversine formula
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371.0  # Earth's radius in kilometers
    
    return c * r

class AgriDataLoader:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.nodes_df = None
        self.products_df = None
        self.demand_supply_df = None
        
    def load_all_data(self):
        """Loads CSV files from the data directory"""
        try:
            self.nodes_df = pd.read_csv(f"{self.data_dir}/network_nodes.csv")
            self.products_df = pd.read_csv(f"{self.data_dir}/product_specs.csv")
            self.demand_supply_df = pd.read_csv(f"{self.data_dir}/demand_supply.csv")
            print("Successfully loaded agricultural network CSV datasets.")
        except Exception as e:
            print(f"Error loading CSV files: {e}")
            raise e
            
    def get_sets(self):
        """Extracts sets for farms, hubs, markets, crops, and planning horizon"""
        farms = list(self.nodes_df[self.nodes_df["type"] == "Farm"]["node_id"])
        hubs = list(self.nodes_df[self.nodes_df["type"] == "Hub"]["node_id"])
        markets = list(self.nodes_df[self.nodes_df["type"] == "Market"]["node_id"])
        crops = list(self.products_df["product_id"])
        months = sorted(list(self.demand_supply_df["month"].unique()))
        
        return farms, hubs, markets, crops, months

    def get_distance_dictionaries(self):
        """Calculates distance matrices (in km) between all nodes"""
        farms_df = self.nodes_df[self.nodes_df["type"] == "Farm"]
        hubs_df = self.nodes_df[self.nodes_df["type"] == "Hub"]
        markets_df = self.nodes_df[self.nodes_df["type"] == "Market"]
        
        dist_farm_hub = {}
        for _, farm in farms_df.iterrows():
            for _, hub in hubs_df.iterrows():
                d = haversine_distance(farm["lat"], farm["lon"], hub["lat"], hub["lon"])
                dist_farm_hub[(farm["node_id"], hub["node_id"])] = round(d, 2)
                
        dist_hub_market = {}
        for _, hub in hubs_df.iterrows():
            for _, market in markets_df.iterrows():
                d = haversine_distance(hub["lat"], hub["lon"], market["lat"], market["lon"])
                dist_hub_market[(hub["node_id"], market["node_id"])] = round(d, 2)
                
        return dist_farm_hub, dist_hub_market

    def get_parameters(self):
        """Prepares dictionary-mapped parameters for Pyomo indices"""
        # Crop specifications
        specs = self.products_df.set_index("product_id")
        holding_costs = specs["holding_cost"].to_dict()
        transit_losses = specs["transit_loss_per_km"].to_dict()
        spoilage_rates = specs["spoilage_rate"].to_dict()
        selling_prices = specs["price_per_ton"].to_dict()
        shortage_penalties = specs["shortage_penalty"].to_dict()
        
        # Hub specifications
        hubs_df = self.nodes_df[self.nodes_df["type"] == "Hub"].set_index("node_id")
        fixed_costs = hubs_df["fixed_cost"].to_dict()
        storage_caps = hubs_df["storage_cap"].to_dict()
        processing_caps = hubs_df["process_cap"].to_dict()
        
        # Time-series Supply & Demand
        supply_df = self.demand_supply_df[self.demand_supply_df["action"] == "Supply"]
        supply_dict = supply_df.set_index(["node_id", "product_id", "month"])["quantity"].to_dict()
        
        demand_df = self.demand_supply_df[self.demand_supply_df["action"] == "Demand"]
        demand_dict = demand_df.set_index(["node_id", "product_id", "month"])["quantity"].to_dict()
        
        # Return all prepared dictionaries
        return {
            "holding_costs": holding_costs,
            "transit_losses": transit_losses,
            "spoilage_rates": spoilage_rates,
            "selling_prices": selling_prices,
            "shortage_penalties": shortage_penalties,
            "fixed_costs": fixed_costs,
            "storage_caps": storage_caps,
            "processing_caps": processing_caps,
            "supply": supply_dict,
            "demand": demand_dict
        }