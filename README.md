## Summary

This Repository contains the code to generate the results of the paper below:

Vahabzadeh E.,  Nazari F., Pourakaberian A., Niasar V.

Techno-Economic Optimisation of Underground Hydrogen Storage in UK Depleted Gas Reservoirs

## Installation


In order to install the DuMuX module and all other necessary dune-modules, please execute the following steps:

```bash
mkdir your_target_folder_name
cd your_target_folder_name
wget https://git.iws.uni-stuttgart.de/dumux-pub/vahabzadeh2026a/-/raw/main/install_vahabzadeh2026a.py
python3 install_vahabzadeh2026a.py
```

## Tests

- To execute the simulation, head to `DUMUX/Mixing-in-UHS/build-cmake/appl/CH4/` and run
```bash
make appl_1pnc_box_CH4
./appl_1pnc_box_CH4 
```
The results can then be inspected via
```bash
paraview appl_1pnc_box_CH4.pvd
```
## Surrogate Modelling and Optimisation
The simulation outputs generated using DuMuX are post-processed to construct a comprehensive dataset describing hydrogen recovery behaviour under a wide range of reservoir and operational conditions.
This dataset is used to train an artificial neural network (ANN) surrogate model that emulates reservoir-scale hydrogen recovery with high accuracy.
The trained surrogate is then embedded within a techno-economic optimisation framework, where large ensembles of candidate storage scenarios are evaluated and a national-scale underground hydrogen storage portfolio is optimised using mixed-integer linear programming implemented in Gurobi.
- postprocess_compute_pe_ng_rf_dataset.py
Reads DuMuX JSON outputs, computes RF and derived quantities (e.g., Pe, Ng, Fo, θ, Δρ) across cycles, and exports consolidated Excel/CSV tables.

- plot_pe_ng_rf_surfaces_and_fits.py
Loads the consolidated dataset and generates the Pe–Ng–RF contour surface and RF-vs-Pe / RF-vs-Ng plots (including fitted correlations).

- doe_sample_field_data_kmeans_lhs.py
Samples UK field properties using KMeans clustering and LHS (with temperature conditioned on pressure) to generate a realistic design-of-experiments scenario set.

- build_optim_scenarios_from_ann.py
Uses a trained ANN surrogate (plus scalers) to evaluate sampled scenarios and writes cycle-wise optimisation datasets (costs, energy, wells, RF/MRF, constraints).

- optimise_portfolio_gurobi.py
Solves the national-scale portfolio optimisation in Gurobi (one scenario per reservoir, optional well limits, discounting, LCOS/cost objective) and exports the optimal plan to Excel.

- analyse_selected_vs_all_reservoirs.py
Aggregates selected reservoirs from optimisation outputs and compares their property distributions against the full field dataset (summary stats + boxplots).

## Versions

 |              module name              |      branch name      |                 commit sha                 |         commit date         |
 |---------------------------------------|-----------------------|--------------------------------------------|-----------------------------|
 |              dune-subgrid             |  origin/releases/2.9  |  41ab447c59ea508c4b965be935b81928e7985a6b  |  2023-12-16 13:51:43 +0000  |
 |            vahabzadeh2026a            |      origin/main      |                      -                     |                             |
 |          dune-localfunctions          |  origin/releases/2.9  |  f2c7cfb96327fbfd29744dccf5eac015a1dfa06f  | 2023-12-16 13:51:43 +0000  |
 |             dune-geometry             |  origin/releases/2.9  |  7d5b1d81ad997f81637ac97f753f80a64ff9cdb0  | 2023-12-16 13:50:03 +0000  |
 |              dune-common              |  origin/releases/2.9  |  ad69f2ab2d78313e1111069fdd2539104fc4dab1  | 2023-12-26 20:29:09 +0000  |
 |                 dumux                 |  origin/releases/3.8  |  c8f61c1f81ca511415c656e834cc0ded17572025  | 2023-12-01 10:12:26 +0000  |
 |              dune-uggrid              |  origin/releases/2.9  |  e26f81ff7d84f5d7b228edb3313beae592d502f7  | 2023-12-16 13:51:01 +0000  |
 |               dune-grid               |  origin/releases/2.9  |  75b66b0ebf0656e21af08798188b3d2848c9574d  | 2023-12-16 13:50:39 +0000  |
 |               dune-istl               |  origin/releases/2.9  |  1582b9e200ad098d0f00de2c135f9eed38508319  | 2023-10-19 09:15:16 +0000  |

## License

This project is licensed under the terms and conditions of the GNU General Public
License (GPL) version 3 or - at your option - any later version.
The GPL can be found under [GPL-3.0-or-later.txt](LICENSES/GPL-3.0-or-later.txt)
provided in the `LICENSES` directory located at the topmost of the source code tree.

