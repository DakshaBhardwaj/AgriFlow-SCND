# 🌾 Indian Perishable Agricultural Supply Chain Network Design (SCND) Optimizer

This repository contains an end-to-end Operations Research project implementing a **Mixed-Integer Linear Programming (MILP)** optimization model to design and manage a seasonal, perishable agricultural supply chain corridor in India. 

It balances strategic capital placement (Cold-Storage Facility Location) with tactical distribution schedules (Multi-Period Network Flow) and inventory shelf-life constraints (Spoilage & Perishability).

---

## 🚀 Business Problem & Scenario

Agricultural harvests in India are highly seasonal (e.g., Shimla Apples peak in autumn, Nagpur Oranges in winter, Nashik Onions in spring), while metropolitan demand is steady year-round. Because these crops are perishable, logistics companies must decide:
1. **Strategic Selection**: Which cold-storage distribution hubs should be leased/opened (Delhi, Indore, Hyderabad) to balance fixed establishment costs against transportation savings?
2. **Tactical Routing**: How much crop should be transported from farms to hubs, and from hubs to markets (Mumbai, Delhi, Bengaluru) in each period?
3. **Inventory Management**: How much inventory should be stored in cold storages month-over-month to satisfy off-season demand, taking into account monthly spoilage decay rates?

---

## 🧮 Mathematical Model Formulation

The system is modeled as a **Multi-Period Mixed-Integer Linear Program (MILP)** over a horizon $T = \{1 \dots 6\}$ months.

### 1. Sets and Indices
- $f \in F$: Farms (Supply points)
- $h \in H$: Candidate Cold-Storage Hubs
- $m \in M$: Metro Markets (Demand points)
- $c \in C$: Crop types (Apples, Oranges, Onions)
- $t \in T$: Time periods (Months)

### 2. Decision Variables
- $y_h \in \{0, 1\}$: Binary variable indicating if candidate hub $h$ is opened.
- $x_{f,h,c,t} \ge 0$: Continuous flow of crop $c$ from farm $f$ to hub $h$ in month $t$ (tons).
- $z_{h,m,c,t} \ge 0$: Continuous flow of crop $c$ from hub $h$ to market $m$ in month $t$ (tons).
- $I_{h,c,t} \ge 0$: Inventory of crop $c$ held at hub $h$ at the end of month $t$ (tons).
- $s_{m,c,t} \ge 0$: Unmet demand (shortage) of crop $c$ at market $m$ in month $t$ (tons).

### 3. Objective Function
Minimize total logistics cost:
$$
\min \sum_{t \in T} \left( \sum_{h \in H} F_h y_h + C^{\text{ship}} \left[ \sum_{f,h,c} D_{f,h} x_{f,h,c,t} + \sum_{h,m,c} D_{h,m} z_{h,m,c,t} \right] + \sum_{h,c} H_c I_{h,c,t} + \sum_{m,c} P_c s_{m,c,t} \right)
$$
Where:
- $F_h$: Fixed lease cost of hub $h$ per month (₹).
- $C^{\text{ship}}$: Shipping tariff per ton-km (₹15/ton-km).
- $D_{i,j}$: Distance between nodes in kilometers (calculated via the Haversine formula).
- $H_c$: Monthly holding cost per ton of crop $c$ (₹).
- $P_c$: Contract shortage penalty cost per ton (₹).

### 4. Key Constraints
* **Farm Harvest Limit**: Outflow from farm $f$ cannot exceed harvest yield:
  $$
  \sum_{h \in H} x_{f,h,c,t} \le \text{Supply}_{f,c,t} \quad \forall f \in F, c \in C, t \in T
  $$
* **Demand Conservation**: Inflow arriving at market $m$ (after transit losses) plus shortage equals demand:
  $$
  \sum_{h \in H} z_{h,m,c,t} \cdot (1 - \text{LossRate}_c \cdot D_{h,m}) + s_{m,c,t} = \text{Demand}_{m,c,t} \quad \forall m \in M, c \in C, t \in T
  $$
* **Inventory Balance**: Inflow (after transit decay) + carry-over inventory (after storage spoilage) must equal outflow plus ending inventory:
  $$
  I_{h,c,t} = I_{h,c,t-1} (1 - \text{SpoilageRate}_c) + \sum_{f \in F} x_{f,h,c,t} (1 - \text{LossRate}_c D_{f,h}) - \sum_{m \in M} z_{h,m,c,t}
  $$
* **Big-M Linking Constraints**:
  - Processing Capacity: $\sum_{f,c} x_{f,h,c,t} \le \text{CapacityProcessing}_h \cdot y_h \quad \forall h, t$
  - Storage Capacity: $\sum_c I_{h,c,t} \le \text{CapacityStorage}_h \cdot y_h \quad \forall h, t$

---

## 🛠️ Project Structure

```
agri_supply_chain/
│
├── data/
│   ├── network_nodes.csv        # Geolocations, lease costs (₹), and capacities
│   ├── demand_supply.csv        # 6-month seasonal supply/demand schedules
│   └── product_specs.csv        # Crop perishability, holding, and penalty specs
│
├── src/
│   ├── data_loader.py           # Ingests CSVs and calculates spherical Haversine distances
│   ├── model.py                 # Pyomo MILP optimization model structure
│   ├── runner.py                # Compiles model, runs GLPK, and extracts DataFrames
│   └── visualizer.py            # Custom Plotly visualizations (Indian map, pie charts)
│
├── app.py                       # Streamlit web dashboard
├── tests/
│   └── test_model.py            # Pytest test suite (flow conservation, Big-M checks)
├── requirements.txt             # Dependency requirements
└── generate_data.py             # Generates crop profiles and node datasets
```

---

## ⚙️ Setup and Execution

### 1. Prerequisites
Ensure you have **GLPK** (GNU Linear Programming Kit) installed and on your system path.
* **Mac**: `brew install glpk`
* **Ubuntu**: `sudo apt-get install glpk-utils`
* **Windows**: Download binaries and add the `w64` folder to PATH.

Verify with:
```bash
glpsol --help
```

### 2. Installation
Clone the repository and set up your virtual environment:
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 3. Generate Data
```bash
python generate_data.py
```

### 4. Run Tests
```bash
pytest
```

### 5. Launch the Streamlit Dashboard
```bash
streamlit run app.py
```
This will open a local web server (usually at `http://localhost:8501`) showing the interactive dashboard. You can adjust transport tariffs and warehouse lease rates in real-time, click "Run Optimizer", and see how the active routes and hub decisions on the Indian map dynamically shift!
