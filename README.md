# Mixing-in-UHS: Techno-Economic Optimisation of Underground Hydrogen Storage

## Summary

This repository contains the simulation code, post-processing tools, surrogate modelling, and optimisation framework for the following paper:

> Vahabzadeh E., Nazari F., Pourakaberian A., Niasar V.
> **Techno-Economic Optimisation of Underground Hydrogen Storage in UK Depleted Gas Reservoirs** (Under Review)

The workflow consists of three main stages:

1. **Reservoir-Scale Simulation** — Single-phase, multi-component (1PNC) flow simulations of hydrogen injection/extraction cycles in porous media using DuMuX, with different cushion gases (CH₄, CO₂, N₂, H₂).
2. **Surrogate Modelling** — An artificial neural network (ANN) trained on reservoir rock properties and operational parameters to rapidly predict hydrogen recovery factor.
3. **Techno-Economic Optimisation** — A mixed-integer linear programme (MILP) solved with Gurobi to select cost-optimal storage portfolios across UK depleted gas reservoirs subject to national energy delivery targets.

## Repository Structure

```
Mixing-in-UHS/
├── appl/                        # DuMuX simulation applications
│   ├── CH4/                     # H₂ + CH₄ cushion gas scenario
│   ├── CO2/                     # H₂ + CO₂ cushion gas scenario
│   ├── H2/                      # H₂ without cushion gas
│   ├── N2/                      # H₂ + N₂ cushion gas scenario
│   ├── 1p/                      # Single-phase reference cases
│   ├── Cartesian/               # Cartesian grid variants
│   ├── Test1/, Test2/           # Verification test cases
│   └── CMakeLists.txt
├── dumux/                       # Custom DuMuX extensions
│   ├── flux/                    # Modified Fick's law and Maxwell-Stefan law
│   ├── material/
│   │   ├── binarycoefficients/  # Binary diffusion coefficients (H₂–CH₄, H₂–CO₂, etc.)
│   │   ├── components/          # Component property models (H₂, CH₄, CO₂, N₂, H₂O)
│   │   └── fluidmatrixinteractions/
│   └── porousmediumflow/        # Compositional model extensions
├── PostFun/                     # Post-processing and optimisation scripts
│   ├── compute_dimensionless_numbers.py
│   ├── average_velocity.py
│   ├── plot_pe_ng_rf.py
│   ├── correlation_feature.py
│   ├── ANN_Training.py
│   ├── NN_optmisation_for_gurobi.py
│   ├── generate_optimisation_scenarios.py
│   ├── optimise_uk_portfolio.py
│   ├── Cost_optimisation_gurobi_pool.py
│   ├── std_plot_optimisation.py
│   ├── mix_and_match.py
│   ├── ann_model_withoutCG_AC.pt     # Pre-trained ANN weights
│   └── scalers_withoutCG_AC.pkl      # Fitted feature scalers
├── Plots/                       # Output plots and consolidated data
├── install_vahabzadeh2026a.py   # Automated installation script
├── CMakeLists.txt               # Top-level build configuration
└── dune.module                  # DUNE module metadata
```

## Installation

### Prerequisites

- C++ compiler with C++17 support
- CMake ≥ 3.13
- Python 3.8+
- Git

### Building the DuMuX Module

The installation script automatically clones all required DUNE modules (dune-common, dune-grid, dune-istl, dune-geometry, dune-localfunctions, dune-uggrid, dune-subgrid) and DuMuX, then configures the build:

```bash
mkdir your_target_folder
cd your_target_folder
wget https://git.iws.uni-stuttgart.de/dumux-pub/vahabzadeh2026a/-/raw/main/install_vahabzadeh2026a.py
python3 install_vahabzadeh2026a.py
```

### Python Dependencies (Post-Processing)

```bash
pip install numpy pandas matplotlib scipy scikit-learn torch optuna joblib CoolProp pyvista seaborn pysr gurobipy
```

> **Note:** The Gurobi optimiser requires a valid [Gurobi licence](https://www.gurobi.com/academia/academic-program-and-licenses/).

## Simulation

Each subdirectory under `appl/` contains a self-contained DuMuX application for a specific cushion gas type. The simulations model:

- **Physics:** Single-phase (gas), multi-component (H₂, CH₄, CO₂, N₂) flow with compositional dispersion (Scheidegger or full-tensor), molecular diffusion (Fick's law with Millington-Quirk effective diffusivity).
- **Geometry:** 2D axisymmetric (radial) domain with rotational extrusion, discretised with box (vertex-centred) finite volumes on a structured YaspGrid.
- **Operations:** Configurable multi-cycle injection–extraction schedules with development (cushion gas) and operational periods, well flow rates, and cycle durations.

### Running a Simulation

```bash
cd DUMUX/Mixing-in-UHS/build-cmake/appl/CH4/
make appl_1pnc_box_CH4
./appl_1pnc_box_CH4
```

Inspect results with ParaView:

```bash
paraview appl_1pnc_box_CH4.pvd
```

Key simulation parameters are configured in `params.input` within each application directory (grid dimensions, permeability, porosity, pressure, temperature, cycle lengths, flow rates, etc.).

## Post-Processing Pipeline

### 1. Velocity and Plume Metrics Extraction

**`average_velocity.py`** — Reads VTU simulation outputs, extracts hydrogen plume geometry (spatial moments, tip velocity, plume length/height) at the end of each injection half-cycle, and exports metrics to JSON.

### 2. Dimensionless Number Computation

**`compute_dimensionless_numbers.py`** — Parses simulation JSON outputs together with velocity metrics to compute:
- **Péclet number (Pe):** Ratio of advective to dispersive transport
- **Gravity number (Ng):** Ratio of gravitational to viscous forces
- **Recovery factor (RF):** Fraction of injected hydrogen recovered per cycle

Uses CoolProp for thermophysical property evaluation (density, viscosity, compressibility) at reservoir conditions. Exports consolidated Excel/CSV tables.

### 3. Correlation and Visualisation

**`plot_pe_ng_rf.py`** — Generates Pe–Ng–RF contour surfaces and scatter plots with fitted analytical correlations (Hill-type for Pe, logarithmic for Ng).

**`correlation_feature.py`** — Computes Pearson/Spearman correlation heatmaps and pairwise scatter matrices of input features versus recovery factor. Optionally uses PySR for symbolic regression to discover closed-form RF expressions.

### 4. ANN Surrogate Model Training

**`ANN_Training.py`** — Trains a PyTorch neural network to predict cycle-wise recovery factor from input features (flow rate, cycle length, permeability, pressure, density difference, porosity, temperature, CG ratio, cycle number).
- Architecture optimised with Optuna (BO-based hyperparameter search with DOF constraints)
- 5-fold cross-validation with early stopping
- Best model: 3 hidden layers (36-tanh, 92-ReLU, 108-sigmoid) with sigmoid output

**`NN_optmisation_for_gurobi.py`** — Variant ANN training for the Gurobi-compatible surrogate with scaled outputs (MinMaxScaler).

### 5. Scenario Generation

**`generate_optimisation_scenarios.py`** — Uses the trained ANN surrogate to evaluate a large design space of candidate storage scenarios:
- Latin Hypercube Sampling over flow rates, cushion gas ratios, and well counts
- Evaluates RF for each candidate across 10 operational cycles
- Computes LCOS (Levelised Cost of Storage), CAPEX, OPEX, and energy metrics

### 6. Portfolio Optimisation

**`optimise_uk_portfolio.py`** — Solves the national-scale MILP:
- **Objective:** Minimise total present-value cost across all selected reservoirs
- **Constraints:** Meet annual energy delivery target (TWh), at most one operating scenario per reservoir, optional well budget
- Evaluates multiple project horizons (1–30 years) with discounted cash flow analysis

**`Cost_optimisation_gurobi_pool.py`** — Extended version with Gurobi solution pool to generate multiple near-optimal portfolio alternatives.

### 7. Results Analysis

**`std_plot_optimisation.py`** — Compares property distributions (permeability, porosity, pressure, depth) of selected reservoirs against the full UK dataset using overlaid boxplots.

**`mix_and_match.py`** — Utility to merge geographic coordinates (latitude/longitude) from master reservoir data into optimised results for mapping.

## Data Files

| File | Description |
|------|-------------|
| `Plots/consolidated_output - Final.csv` | UK depleted gas reservoir property database |
| `PostFun/ann_model_withoutCG_AC.pt` | Pre-trained ANN weights (without CG in RF, all cycles) |
| `PostFun/scalers_withoutCG_AC.pkl` | Fitted StandardScaler for ANN input features |
| `compiled_optimal_data.csv` | Compiled optimisation results |
| `all_points_lcos_vs_loss.csv` | Full scenario LCOS vs. loss data |
| `rf_validity_plot.joblib` | Random forest classifier for validity screening |
| `toy_relu_mlp.pt` | Auxiliary MLP model weights |

## Versions

| Module | Branch | Commit SHA | Commit Date |
|--------|--------|------------|-------------|
| dune-subgrid | origin/releases/2.9 | 41ab447c | 2023-12-16 |
| dune-localfunctions | origin/releases/2.9 | f2c7cfb9 | 2023-12-16 |
| dune-geometry | origin/releases/2.9 | 7d5b1d81 | 2023-12-16 |
| dune-common | origin/releases/2.9 | ad69f2ab | 2023-12-26 |
| dumux | origin/releases/3.8 | c8f61c1f | 2023-12-01 |
| dune-uggrid | origin/releases/2.9 | e26f81ff | 2023-12-16 |
| dune-grid | origin/releases/2.9 | 75b66b0e | 2023-12-16 |
| dune-istl | origin/releases/2.9 | 1582b9e2 | 2023-10-19 |

## License

This project is licensed under the terms and conditions of the GNU General Public License (GPL) version 3 or — at your option — any later version. See [GPL-3.0-or-later.txt](LICENSES/GPL-3.0-or-later.txt).
