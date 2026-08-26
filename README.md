# Mixing-in-UHS

## Techno-Economic Optimisation of Hydrogen Geological Storage in UK Depleted Gas Reservoirs

Research code, processed data, trained surrogate models, and optimisation outputs accompanying the paper:

> Ehsan Vahabzadeh, Farzaneh Nazari, Gabriel D. Patrón, Arash Pourakaberian, Calvin Tsay, and Vahid Niasar.
>
> **Techno-Economic Optimisation of Hydrogen Geological Storage in UK Depleted Gas Reservoirs.**
>
> *Energy Conversion and Management* — **accepted for publication**.

Publication identifiers and a link to the final article will be added when they become available.

## Overview

This repository links reservoir-scale hydrogen mixing to national-scale storage planning. It combines compositional DuMuX simulations, physical transport metrics, a PyTorch surrogate model, and mixed-integer optimisation to identify cost-effective underground hydrogen storage (UHS) portfolios across UK depleted gas reservoirs.

The study addresses three connected questions:

1. How do reservoir properties, operating conditions, and cushion-gas choice affect hydrogen mixing and recovery?
2. Can a surrogate model reproduce the recovery factors predicted by full-physics simulations?
3. Which reservoir and operating portfolios meet annual hydrogen-delivery targets at minimum cost?

```mermaid
flowchart LR
    A[UK reservoir data<br/>and LHS samples] --> B[DuMuX compositional<br/>simulations]
    B --> C[Recovery factor<br/>Pe and Ng]
    C --> D[PyTorch ANN<br/>surrogate]
    D --> E[Screened reservoir-operation<br/>scenario library]
    E --> F[Gurobi MILP<br/>portfolio optimisation]
    F --> G[Reservoir selection<br/>LCOS and purity strategy]
```

## Main findings reported in the paper

- Permeability, porosity, reservoir pressure, and the density contrast between H₂ and the cushion gas are the dominant controls on recovery within the sampled design space.
- The ANN achieved a holdout-test \(R^2\) of 0.9980 and an MSE of \(10^{-5}\). Re-simulation of 15 optimisation-selected cases gave an RF RMSE of 0.017.
- For annual delivery targets of 5–200 TWh, long-term optimised levelised costs of storage (LCOS) were approximately 30–60 USD MWh⁻¹.
- Frequently selected reservoirs occupy a relatively narrow property window: permeability of 10–30 mD, porosity of 0.10–0.15, and pressure of 250–300 bar.
- H₂ cushion gas is most attractive at lower delivery targets or when purification approaches the cost of hydrogen production. At larger targets, purification is generally preferred to retaining a large H₂ cushion inventory.

These values are results of the assumptions and screening framework used in the paper; they are not site-specific performance guarantees.

## Model scope

The primary paper simulations use a modified DuMuX single-phase, multicomponent (`1pnc`) model with:

- fully compressible H₂/CH₄, H₂/CO₂, H₂/N₂, and H₂-cushion-gas systems;
- 2D radial geometry and fully implicit flow-transport coupling;
- molecular diffusion and hydrodynamic dispersion;
- buoyancy driven by composition-dependent gas density; and
- configurable injection, withdrawal, idle, and cushion-gas-development periods.

The study is a reservoir-screening assessment. The models are homogeneous, isothermal, and gas dominated, and do not resolve site-specific heterogeneity, detailed wellbore hydraulics, geomechanics, mobile water, microbial reactions, or geochemical reactions. Portfolio results also exclude hydrogen-network routing and hourly energy-system dispatch.

### Sampled parameter space

| Parameter | Range |
| --- | ---: |
| Porosity | 0.05–0.30 |
| Permeability | 1–1500 mD |
| Reservoir temperature | 293–393 K |
| Reservoir pressure | 50–450 bar |
| Injection/withdrawal rate | 100,000–1,500,000 sm³ d⁻¹ |
| Cycle length | 14–360 days |
| H₂ cushion-gas ratio | 0–5 |

The numerical mixing study treats CH₄, N₂, CO₂, and H₂ as controlled end-member cushion-gas cases. In the optimisation dataset, the H₂ cushion-gas ratio is the retained H₂ cushion volume divided by the working-gas volume.

## Repository layout

```text
Mixing-in-UHS/
├── appl/
│   ├── 1p/                       # Primary 1pnc paper simulations
│   │   ├── H2/                  # H₂ cushion-gas cases
│   │   ├── CH4/                 # H₂–CH₄ cases
│   │   ├── CO2/                 # H₂–CO₂ cases
│   │   └── N2/                  # H₂–N₂ cases
│   ├── Cartesian/                # Cartesian-grid variants
│   ├── H2/, CH4/, CO2/, N2/      # Additional two-phase variants
│   └── Test*/                    # Verification/development cases
├── dumux/                         # Project-specific DuMuX extensions
│   ├── flux/                      # Diffusive/dispersive flux laws
│   ├── material/                  # Components and binary coefficients
│   └── porousmediumflow/          # Compositional-flow extensions
├── PostFun/                       # Analysis, ANN, and optimisation scripts
│   └── Other/                     # Exploratory and legacy analyses
├── Plots/                         # Processed data and generated figures
├── install_vahabzadeh2026a.py     # Reproducible DUNE/DuMuX installer
├── CMakeLists.txt
└── dune.module
```

## Installation

### Prerequisites

- Linux or another environment supported by DUNE/DuMuX
- a C++17 compiler
- CMake 3.13 or newer
- Git
- Python 3.8 or newer for post-processing
- standard [DUNE](https://www.dune-project.org/) build dependencies

### Recommended installation

The installer downloads the exact DUNE 2.9 and DuMuX 3.8 revisions listed in the [version table](#pinned-dunedumux-revisions), clones this repository, and configures all modules.

```bash
mkdir uhs-reproduction
cd uhs-reproduction
curl -O https://raw.githubusercontent.com/ehsan-vahabzadeh/Mixing-in-UHS/main/install_vahabzadeh2026a.py
python3 install_vahabzadeh2026a.py
```

The resulting source and build directories are:

```text
DUMUX/Mixing-in-UHS/
DUMUX/Mixing-in-UHS/build-cmake/
```

To rebuild an existing installation from the `DUMUX` directory:

```bash
./dune-common/bin/dunecontrol --opts=dumux/cmake.opts all
```

### Python environment

The repository does not yet provide a locked Python environment. A minimal environment for the main analysis workflow can be created with:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install numpy pandas scipy matplotlib seaborn scikit-learn \
  torch optuna joblib CoolProp pyvista openpyxl gurobipy
```

Some exploratory scripts in `PostFun/Other/` additionally use packages such as SALib, PySR, Cartopy, pyDOE2, pymoo, pyswarm, and pyDGSA.

Gurobi requires a valid licence. Academic users can obtain one through the [Gurobi Academic Program](https://www.gurobi.com/academia/academic-program-and-licenses/).

## Running a reservoir simulation

The `appl/1p/` directory contains the single-phase compositional cases used by the paper. For example, build and run the box-discretised H₂–CH₄ case as follows:

```bash
cd DUMUX/Mixing-in-UHS
cmake --build build-cmake --target appl_1pnc_box_CH4 -j 4
cd build-cmake/appl/1p/CH4
./appl_1pnc_box_CH4 params.input
```

Equivalent box targets are available for `H2`, `CO2`, and `N2`:

```text
appl_1pnc_box_H2
appl_1pnc_box_CO2
appl_1pnc_box_N2
```

Each case is configured through its own `params.input`. Important sections include:

| Section | Controls |
| --- | --- |
| `[TimeLoop]` | end time and time-step limits |
| `[Grid]` | radial-domain dimensions and resolution |
| `[Problem]` | output name, gravity, temperature, and dispersion mode |
| `[BoundaryConditions]` | cycle schedule, well rates, cushion gas, and completion height |
| `[SpatialParams]` | porosity and permeability |
| `[Newton]` | nonlinear-solver tolerances |

Simulation output includes `.vtu` snapshots, a `.pvd` time-series index, and a JSON material-balance/recovery record. Open the `.pvd` file in [ParaView](https://www.paraview.org/) to inspect the concentration and pressure fields.

## Analysis and optimisation workflow

The main scripts are intended to be run in the following order:

| Stage | Script | Purpose |
| --- | --- | --- |
| 1 | `PostFun/average_velocity.py` | Extract plume geometry and velocity at injection endpoints from VTU/PVD output |
| 2 | `PostFun/compute_dimensionless_numbers.py` | Calculate Péclet number, gravity number, and cycle-wise recovery factor |
| 3 | `PostFun/plot_pe_ng_rf.py` and `PostFun/correlation_feature.py` | Analyse transport regimes, correlations, and feature sensitivity |
| 4 | `PostFun/ANN_Training.py` | Train and validate the nine-input PyTorch recovery-factor surrogate |
| 5 | `PostFun/generate_optimisation_scenarios.py` | Sample feasible reservoir-operation scenarios and predict recovery |
| 6 | `PostFun/optimise_uk_portfolio.py` | Select a minimum-cost portfolio for a specified delivery target |
| 7 | `PostFun/Cost_optimisation_gurobi_pool.py` | Generate multiple near-optimal portfolio alternatives |
| 8 | `PostFun/std_plot_optimisation.py` | Compare selected and full-inventory reservoir-property distributions |

The ANN inputs are flow rate, cycle length, permeability, pressure, H₂/cushion-gas density difference, porosity, temperature, H₂ cushion-gas ratio, and cycle number. Its sigmoid output keeps predicted recovery factors between zero and one.

### Configuration required before running Python scripts

Several scripts preserve absolute Windows paths from the original analysis. Before running them on another machine:

1. Replace `INPUT_DIR`, `base_input_dir`, or `csv_path` with local paths.
2. Run model-dependent scripts from `PostFun/`, or update model and scaler paths explicitly.
3. Set the delivery target, cycle length, H₂ price, purification-cost multiplier, and optional well budget in each script's `USER SETTINGS` block.
4. Point the scenario generator to the desired validity classifier. The checked-in classifier is `rf_validity_plot.joblib`, while one legacy code path refers to `rf_validity.joblib`.

Simulation JSON files consumed by `compute_dimensionless_numbers.py` follow this naming convention:

```text
<Gas>-<FlowRate>-<CycleLength>-<Permeability>-<Pressure>-<Temperature>-<PorosityPercent>-<CGRatio>.json
```

Example:

```text
CH4-500000-180-25-250-333-12-0.json
```

## Data and trained artefacts

| Path | Description |
| --- | --- |
| `Plots/consolidated_output - Final.csv` | Source UK depleted-gas-reservoir property inventory; the manuscript retains 96 eligible reservoirs after filtering |
| `PostFun/ann_model_withoutCG_AC.pt` | Trained PyTorch ANN weights |
| `PostFun/scalers_withoutCG_AC.pkl` | Fitted feature/output scalers used with the ANN |
| `rf_validity_plot.joblib` | Random-forest validity classifier used by scenario-screening analyses |
| `compiled_optimal_data.csv` | Consolidated optimal-scenario results |
| `all_points_lcos_vs_loss.csv` | LCOS and total-loss-cost points across scenarios |
| `Plots/` | Processed figures and optimisation summaries |

The source reservoir CSV includes literature/database references where available. Users are responsible for observing the terms of the underlying data providers.

## Pinned DUNE/DuMuX revisions

| Module | Branch | Commit | Date |
| --- | --- | --- | --- |
| dune-common | `releases/2.9` | `ad69f2ab` | 2023-12-26 |
| dune-geometry | `releases/2.9` | `7d5b1d81` | 2023-12-16 |
| dune-grid | `releases/2.9` | `75b66b0e` | 2023-12-16 |
| dune-istl | `releases/2.9` | `1582b9e2` | 2023-10-19 |
| dune-localfunctions | `releases/2.9` | `f2c7cfb9` | 2023-12-16 |
| dune-subgrid | `releases/2.9` | `41ab447c` | 2023-12-16 |
| dune-uggrid | `releases/2.9` | `e26f81ff` | 2023-12-16 |
| dumux | `releases/3.8` | `c8f61c1f` | 2023-12-01 |

Full commit hashes are recorded in `install_vahabzadeh2026a.py`.

## Citation

Until the final volume, page/article number, and DOI are available, please cite the accepted manuscript as:

> Vahabzadeh, E., Nazari, F., Patrón, G. D., Pourakaberian, A., Tsay, C., and Niasar, V. (2026). Techno-Economic Optimisation of Hydrogen Geological Storage in UK Depleted Gas Reservoirs. *Energy Conversion and Management*. Accepted for publication.

```bibtex
@article{vahabzadeh2026hydrogen,
  author  = {Vahabzadeh, Ehsan and Nazari, Farzaneh and Patrón, Gabriel D. and
             Pourakaberian, Arash and Tsay, Calvin and Niasar, Vahid},
  title   = {Techno-Economic Optimisation of Hydrogen Geological Storage in
             {UK} Depleted Gas Reservoirs},
  journal = {Energy Conversion and Management},
  year    = {2026},
  note    = {Accepted for publication}
}
```

## Acknowledgements

This work was supported by bp through the bp International Centre for Advanced Materials (bp-ICAM), reference EP/X524839/1-2857249. Farzaneh Nazari also acknowledges a President's Doctoral Scholarship from The University of Manchester.

## Contact

For questions about the paper or repository, contact the corresponding author:

**Vahid Niasar**<br>
Department of Chemical Engineering, The University of Manchester<br>
[vahid.niasar@manchester.ac.uk](mailto:vahid.niasar@manchester.ac.uk)

## Licence

The DuMuX-derived source files carry `SPDX-License-Identifier: GPL-3.0-or-later` headers. A standalone repository-level licence file is not currently included; consult the headers of individual files when reusing code.
