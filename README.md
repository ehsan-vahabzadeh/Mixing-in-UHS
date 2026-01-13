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
- **`compute_dimensionless_numbers.py`**  
  Reads DuMuX JSON outputs, computes recovery factor and derived quantities (Pe, Ng) across cycles, and exports consolidated Excel/CSV tables.

- **`plot_pe_ng_rf.py`**  
  Loads the consolidated dataset and generates Pe–Ng–RF contour surfaces and RF–Pe / RF–Ng plots, including fitted correlations.

- **`sample_field_data_lhs.py`**  
  Samples UK field properties Latin Hypercube Sampling (LHS) to generate a realistic design-of-experiments scenario set.

- **`generate_optimisation_scenarios.py`**  
  Uses a trained ANN surrogate (with associated scalers) to evaluate sampled scenarios and generate cycle-wise optimisation datasets containing costs, energy metrics, wells, and constraints.

- **`optimise_uk_portfolio.py`**  
  Solves the national-scale underground hydrogen storage portfolio optimisation using Gurobi, selecting cost-optimal scenarios subject to energy targets and operational constraints.

- **`ANN_Training.py`**  
  ANN training and testing with hyperparamter optimisations.
  
- **`std_plot_optimisation.py`**  
  Aggregates reservoirs selected by the optimisation and compares their property distributions against the full dataset using summary statistics and boxplots.

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

