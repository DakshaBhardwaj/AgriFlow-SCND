# Indian Perishable Agricultural Supply Chain Network Design (SCND) Optimizer

An end-to-end Operations Research case study utilizing **Mixed-Integer Linear Programming (MILP)** to optimize regional crop logistics, cold-storage facility locations, and inventory scheduling in India.

This project balances strategic capital placement (warehouse location) against tactical distribution schedules (multi-period flow) and inventory shelf-life constraints (transit and storage spoilage).

---

## Business Case Study

Agricultural harvests in India are highly seasonal (e.g., Shimla apples peak in autumn, Nagpur oranges in winter, and Nashik onions in spring), whereas consumer demand in metropolitan markets is continuous year-round. Because these crops are perishable, logistics companies must solve three coupled decision layers:

1.  **Strategic Network Design**: Which regional cold-storage distribution hubs (Delhi, Indore, Hyderabad) should be leased and opened to minimize total system cost?
2.  **Tactical Distribution**: What quantities of each crop should be shipped from farms to hubs, and from hubs to markets (Mumbai, Delhi, Bengaluru) in each planning period?
3.  **Inventory Control**: How much crop volume should be stored at hubs month-over-month to satisfy off-season demand, taking into account transit loss and storage decay?

---

## Mathematical Model Formulation

The system is modeled as a multi-period Mixed-Integer Linear Program (MILP) solved over a planning horizon $T = \{1 \dots 6\}$ months.

### 1. Sets and Indices
*   $f \in F$: Farms (supply nodes)
*   $h \in H$: Candidate cold-storage hubs (potential facility locations)
*   $m \in M$: Metro markets (retail demand nodes)
*   $c \in C$: Crop types (Apples, Oranges, Onions)
*   $t \in T$: Time periods (Months)

### 2. Decision Variables
*   $y_h \in \{0, 1\}$: Binary variable indicating if candidate hub $h$ is opened.
*   $x_{f,h,c,t} \ge 0$: Continuous flow of crop $c$ shipped from farm $f$ to hub $h$ in month $t$ (tons).
*   $z_{h,m,c,t} \ge 0$: Continuous flow of crop $c$ shipped from hub $h$ to market $m$ in month $t$ (tons).
*   $I_{h,c,t} \ge 0$: Inventory of crop $c$ held at hub $h$ at the end of month $t$ (tons).
*   $s_{m,c,t} \ge 0$: Unmet demand (shortage) of crop $c$ at market $m$ in month $t$ (tons).

### 3. Objective Function
Minimize the total supply chain operating cost:

$$
\min Z = \sum_{t \in T} \sum_{h \in H} F_h y_h 
+ C^{\mathrm{ship}} \sum_{t \in T} \left( \sum_{f \in F}\sum_{h \in H}\sum_{c \in C} D_{f,h} x_{f,h,c,t} + \sum_{h \in H}\sum_{m \in M}\sum_{c \in C} D_{h,m} z_{h,m,c,t} \right)
+ \sum_{t \in T}\sum_{h \in H}\sum_{c \in C} H_c I_{h,c,t}
+ \sum_{t \in T}\sum_{m \in M}\sum_{c \in C} P_c s_{m,c,t}
$$

Where:
*   $F_h$: Fixed lease cost of hub $h$ per month (₹).
*   $C^{\mathrm{ship}}$: Shipping tariff rate per unit of distance (₹15/ton-km).
*   $D_{i,j}$: Distance between nodes in kilometers (calculated via the Haversine formula).
*   $H_c$: Monthly holding cost per ton of crop $c$ (₹).
*   $P_c$: Shortage penalty cost per ton (₹).

### 4. Key Constraints

*   **Farm Capacity Bound**:

$$
\sum_{h \in H} x_{f,h,c,t} \le \text{Supply}_{f,c,t} \quad \forall f \in F, c \in C, t \in T
$$

*   **Market Demand Balance**:

$$
\sum_{h \in H} z_{h,m,c,t} \cdot (1 - \beta_c D_{h,m}) + s_{m,c,t} = \text{Demand}_{m,c,t} \quad \forall m \in M, c \in C, t \in T
$$

*   **Hub Inventory Conservation**:

$$
I_{h,c,t} = I_{h,c,t-1} (1 - \gamma_c) + \sum_{f \in F} x_{f,h,c,t} (1 - \alpha_c D_{f,h}) - \sum_{m \in M} z_{h,m,c,t} \quad \forall h \in H, c \in C, t \in T
$$

*   **Big-M Throughput Linking**:

$$
\sum_{f \in F}\sum_{c \in C} x_{f,h,c,t} \le \text{CapProcessing}_h \cdot y_h \quad \forall h \in H, t \in T
$$

*   **Big-M Storage Linking**:

$$
\sum_{c \in C} I_{h,c,t} \le \text{CapStorage}_h \cdot y_h \quad \forall h \in H, t \in T
$$

---

## Project Structure

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

## Technical Stack
*   **Modeling Language**: Pyomo (ConcreteModel)
*   **Optimization Solver**: GLPK (GNU Linear Programming Kit)
*   **Data Science**: Pandas, NumPy
*   **Visualizations**: Plotly (Scattergeo, bar, and pie charts)
*   **Interactive Web UI**: Streamlit
*   **Testing Framework**: Pytest

---

## Setup and Execution

### 1. Prerequisites
Ensure you have **GLPK** installed and on your system path.
*   **Mac**: `brew install glpk`
*   **Ubuntu**: `sudo apt-get install glpk-utils`
*   **Windows**: Download binaries and add the `w64` folder to PATH.

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

### 3. Generate Datasets
```bash
python generate_data.py
```

### 4. Run Verification Tests
```bash
pytest
```

### 5. Launch the Streamlit Dashboard
```bash
streamlit run app.py
```
This will open a local web server (usually at `http://localhost:8501`) showing the interactive dashboard. You can adjust transport tariffs and warehouse lease rates in the sidebar, click "Run Optimizer", and see how the active routes and hub decisions on the Indian map dynamically shift.
