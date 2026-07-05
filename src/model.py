import pyomo.environ as pyo

def build_supply_chain_model(farms, hubs, markets, crops, months,
                            dist_farm_hub, dist_hub_market, params,
                            base_shipping_cost=15.0):
    """
    Constructs the MILP ConcreteModel for the agricultural supply chain.
    base_shipping_cost: Cost in ₹ per ton-km (default: ₹15.0/ton-km)
    """
    model = pyo.ConcreteModel(name="Indian_Agri_Supply_Chain_Optimizer")

    # ==========================================
    # 1. SETS
    # ==========================================
    model.F = pyo.Set(initialize=farms, doc="Farms (Supply)")
    model.H = pyo.Set(initialize=hubs, doc="Candidate Cold-Storage Hubs")
    model.M = pyo.Set(initialize=markets, doc="Metro Markets (Demand)")
    model.C = pyo.Set(initialize=crops, doc="Crop Types")
    model.T = pyo.Set(initialize=months, doc="Time Horizon (Months)")

    # ==========================================
    # 2. PARAMETERS
    # ==========================================
    # Distances
    model.dist_fh = pyo.Param(model.F, model.H, initialize=dist_farm_hub, default=9999.0)
    model.dist_hm = pyo.Param(model.H, model.M, initialize=dist_hub_market, default=9999.0)
    
    # Financial and shipping parameters
    model.ship_cost = pyo.Param(initialize=base_shipping_cost)
    model.fixed_costs = pyo.Param(model.H, initialize=params["fixed_costs"])
    model.holding_costs = pyo.Param(model.C, initialize=params["holding_costs"])
    model.selling_prices = pyo.Param(model.C, initialize=params["selling_prices"])
    model.shortage_penalties = pyo.Param(model.C, initialize=params["shortage_penalties"])
    
    # Capacity parameters
    model.storage_caps = pyo.Param(model.H, initialize=params["storage_caps"])
    model.processing_caps = pyo.Param(model.H, initialize=params["processing_caps"])
    
    # Perishability parameters
    model.transit_losses = pyo.Param(model.C, initialize=params["transit_losses"])
    model.spoilage_rates = pyo.Param(model.C, initialize=params["spoilage_rates"])
    
    # Supply and Demand curves (mapped as dictionaries, defaulting to 0 for off-season)
    model.supply = pyo.Param(model.F, model.C, model.T, initialize=params["supply"], default=0.0)
    model.demand = pyo.Param(model.M, model.C, model.T, initialize=params["demand"], default=0.0)

    # ==========================================
    # 3. DECISION VARIABLES
    # ==========================================
    # Strategic Binary Variable: 1 if hub is open, 0 if closed
    model.y = pyo.Var(model.H, domain=pyo.Binary, doc="Hub opened status")
    
    # Flow Variables (continuous, non-negative tons)
    model.x = pyo.Var(model.F, model.H, model.C, model.T, domain=pyo.NonNegativeReals, doc="Flow from farm to hub")
    model.z = pyo.Var(model.H, model.M, model.C, model.T, domain=pyo.NonNegativeReals, doc="Flow from hub to market")
    
    # Inventory and Shortage Variables
    model.I = pyo.Var(model.H, model.C, model.T, domain=pyo.NonNegativeReals, doc="Hub inventory at month-end")
    model.s = pyo.Var(model.M, model.C, model.T, domain=pyo.NonNegativeReals, doc="Market demand shortage")

    # ==========================================
    # 4. OBJECTIVE FUNCTION
    # ==========================================
    def obj_rule(m):
        # 1. Monthly lease cost for open hubs
        fixed_hub_cost = sum(m.fixed_costs[h] * m.y[h] for h in m.H) * len(m.T)
        
        # 2. Shipping costs (Distance * Quantity * Base Rate)
        transport_farm_to_hub = sum(
            m.ship_cost * m.dist_fh[f, h] * m.x[f, h, c, t]
            for f in m.F for h in m.H for c in m.C for t in m.T
        )
        transport_hub_to_market = sum(
            m.ship_cost * m.dist_hm[h, market] * m.z[h, market, c, t]
            for h in m.H for market in m.M for c in m.C for t in m.T
        )
        
        # 3. Monthly inventory holding costs at cold storages
        holding_cost = sum(
            m.holding_costs[c] * m.I[h, c, t]
            for h in m.H for c in m.C for t in m.T
        )
        
        # 4. Penalty cost for unmet customer demand
        shortage_penalty = sum(
            m.shortage_penalties[c] * m.s[market, c, t]
            for market in m.M for c in m.C for t in m.T
        )
        
        return fixed_hub_cost + transport_farm_to_hub + transport_hub_to_market + holding_cost + shortage_penalty

    model.Obj = pyo.Objective(rule=obj_rule, sense=pyo.minimize, doc="Minimize total supply chain costs")

    # ==========================================
    # 5. CONSTRAINTS
    # ==========================================

    # A. Farm Outflow Constraint: Outflow cannot exceed harvest yield
    def farm_supply_rule(m, f, c, t):
        return sum(m.x[f, h, c, t] for h in m.H) <= m.supply[f, c, t]
    model.FarmSupplyCon = pyo.Constraint(model.F, model.C, model.T, rule=farm_supply_rule)

    # B. Market Demand Constraint: Arriving flow (after transit losses) + shortage = demand
    def market_demand_rule(m, m_id, c, t):
        arriving_flow = sum(
            m.z[h, m_id, c, t] * (1.0 - m.transit_losses[c] * m.dist_hm[h, m_id])
            for h in m.H
        )
        return arriving_flow + m.s[m_id, c, t] == m.demand[m_id, c, t]
    model.MarketDemandCon = pyo.Constraint(model.M, model.C, model.T, rule=market_demand_rule)

    # C. Hub Inflow-Outflow & Inventory Balance Constraint
    def hub_balance_rule(m, h, c, t):
        # Arriving inflow from all farms (minus transport transit loss)
        inflow = sum(
            m.x[f, h, c, t] * (1.0 - m.transit_losses[c] * m.dist_fh[f, h])
            for f in m.F
        )
        
        if t == m.T.first():
            # First period: starting inventory is 0
            return m.I[h, c, t] == inflow - sum(m.z[h, metro, c, t] for metro in m.M)
        else:
            # Succeeding periods: include carry-over inventory after monthly storage decay
            prev_inventory_after_spoilage = m.I[h, c, t-1] * (1.0 - m.spoilage_rates[c])
            return m.I[h, c, t] == prev_inventory_after_spoilage + inflow - sum(m.z[h, metro, c, t] for metro in m.M)
            
    model.HubBalanceCon = pyo.Constraint(model.H, model.C, model.T, rule=hub_balance_rule)

    # D. Hub Throughput (Processing) Capacity: Big-M linking constraint
    def hub_processing_rule(m, h, t):
        inflow_total = sum(m.x[f, h, c, t] for f in m.F for c in m.C)
        return inflow_total <= m.processing_caps[h] * m.y[h]
    model.HubProcessingCon = pyo.Constraint(model.H, model.T, rule=hub_processing_rule)

    # E. Hub Storage Capacity: Big-M linking constraint
    def hub_storage_rule(m, h, t):
        total_inventory = sum(m.I[h, c, t] for c in m.C)
        return total_inventory <= m.storage_caps[h] * m.y[h]
    model.HubStorageCon = pyo.Constraint(model.H, model.T, rule=hub_storage_rule)

    return model

