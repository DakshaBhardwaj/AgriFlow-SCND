# Mixed-Integer Linear Programming (MILP) Formulation

This document describes the complete mathematical structure of the Indian Perishable Agricultural Supply Chain Network Design Optimizer.

---

## 1. Sets and Indices

* $f \in F$: Set of Farms (supply points, e.g., Shimla, Nagpur, Nashik)
* $h \in H$: Set of Candidate Cold-Storage Hub locations (e.g., Delhi, Indore, Hyderabad)
* $m \in M$: Set of Metro Markets (demand nodes, e.g., Mumbai, Delhi, Bengaluru)
* $c \in C$: Set of Crop categories (e.g., Apples, Oranges, Onions)
* $t \in T$: Set of Planning periods (Months $1 \dots 6$)

---

## 2. Decision Variables

### Strategic Variable (Discrete)
* $y_h \in \{0, 1\}$: Binary decision; equals $1$ if potential hub $h$ is leased/opened, and $0$ otherwise.

### Operational Variables (Continuous & Non-Negative)
* $x_{f,h,c,t} \ge 0$: Flow volume of crop $c$ shipped from farm $f$ to hub $h$ in month $t$ (in tons).
* $z_{h,m,c,t} \ge 0$: Flow volume of crop $c$ shipped from hub $h$ to market $m$ in month $t$ (in tons).
* $I_{h,c,t} \ge 0$: Carry-over inventory of crop $c$ stored at hub $h$ at the end of month $t$ (in tons).
* $s_{m,c,t} \ge 0$: Unmet demand (shortage) of crop $c$ at market $m$ in month $t$ (in tons).

---

## 3. Parameters

### Distance & Costs
* $\mathrm{DistFarm}_{f,h}$: Spherical distance between farm $f$ and hub $h$ in kilometers (km).
* $\mathrm{DistHub}_{h,m}$: Spherical distance between hub $h$ and market $m$ in kilometers (km).
* $C^{\mathrm{ship}}$: Shipping tariff rate per unit of distance (₹/ton-km).
* $F_h$: Fixed monthly cost to lease and operate hub $h$ (₹/month).
* $H_c$: Inventory holding cost per unit of volume stored (₹/ton/month).
* $P_c$: Shortage penalty cost per unit of unmet customer demand (₹/ton).

### Operational Capacities
* $\mathrm{CapProcessing}_h$: Monthly maximum processing throughput capacity of hub $h$ (tons).
* $\mathrm{CapStorage}_h$: Maximum inventory capacity of hub $h$ (tons).
* $\mathrm{Supply}_{f,c,t}$: Harvest supply capacity of crop $c$ at farm $f$ in month $t$ (tons).
* $\mathrm{Demand}_{m,c,t}$: Consumer demand for crop $c$ at market $m$ in month $t$ (tons).

### Crop Perishability Rates
* $\alpha_c$: Transit loss coefficient of crop $c$ between farms and hubs (loss fraction per km).
* $\beta_c$: Transit loss coefficient of crop $c$ between hubs and markets (loss fraction per km).
* $\gamma_c$: Storage decay/spoilage rate of crop $c$ in cold storage (spoilage fraction per month).

---

## 4. Objective Function

Minimize the total system operations cost over the planning horizon:

$$
\min Z = \mathrm{FixedHubCost} + \mathrm{TransportationCost} + \mathrm{HoldingCost} + \mathrm{ShortagePenalty}
$$

Detailed expansion:

$$
\min Z = \sum_{t \in T} \sum_{h \in H} F_h y_h 
+ C^{\mathrm{ship}} \sum_{t \in T} \left( \sum_{f \in F}\sum_{h \in H}\sum_{c \in C} \mathrm{DistFarm}_{f,h} x_{f,h,c,t} + \sum_{h \in H}\sum_{m \in M}\sum_{c \in C} \mathrm{DistHub}_{h,m} z_{h,m,c,t} \right)
+ \sum_{t \in T}\sum_{h \in H}\sum_{c \in C} H_c I_{h,c,t}
+ \sum_{t \in T}\sum_{m \in M}\sum_{c \in C} P_c s_{m,c,t}
$$

---

## 5. Constraints

### A. Farm Supply Outflow Constraint
The total outflow of crop $c$ shipped from farm $f$ to all candidate hubs in month $t$ cannot exceed its seasonal harvest supply:

$$
\sum_{h \in H} x_{f,h,c,t} \le \mathrm{Supply}_{f,c,t} \quad \forall f \in F, c \in C, t \in T
$$

### B. Market Demand Conservation
The sum of flows arriving at market $m$ from all hubs (discounted by the transit spoilage over distance) plus the unmet shortage variable must equal the consumer demand:

$$
\sum_{h \in H} z_{h,m,c,t} \cdot \left(1 - \beta_c \mathrm{DistHub}_{h,m}\right) + s_{m,c,t} = \mathrm{Demand}_{m,c,t} \quad \forall m \in M, c \in C, t \in T
$$

### C. Hub Inflow-Outflow & Inventory Balance
For each hub $h$, crop $c$, and month $t$:

*   **Month $t = 1$** (Initial stock is assumed to be $0$):

$$
I_{h,c,1} = \sum_{f \in F} x_{f,h,c,1} \cdot \left(1 - \alpha_c \mathrm{DistFarm}_{f,h}\right) - \sum_{m \in M} z_{h,m,c,1}
$$

*   **Months $t > 1$** (Ending stock equals previous stock adjusted for monthly spoilage, plus net incoming flows):

$$
I_{h,c,t} = I_{h,c,t-1}\cdot\left(1 - \gamma_c\right) + \sum_{f \in F} x_{f,h,c,t} \cdot \left(1 - \alpha_c \mathrm{DistFarm}_{f,h}\right) - \sum_{m \in M} z_{h,m,c,t}
$$

### D. Hub Capacity Limits (Big-M Linking Constraints)
These constraints link the continuous flow and inventory decisions to the strategic binary decision variable $y_h$. If a hub is closed ($y_h = 0$), its capacities are forced to zero, disabling all incoming flows and storage.

*   **Hub Processing Throughput Capacity**:

$$
\sum_{f \in F}\sum_{c \in C} x_{f,h,c,t} \le \mathrm{CapProcessing}_h \cdot y_h \quad \forall h \in H, t \in T
$$

*   **Hub Storage Capacity**:

$$
\sum_{c \in C} I_{h,c,t} \le \mathrm{CapStorage}_h \cdot y_h \quad \forall h \in H, t \in T
$$
