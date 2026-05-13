# Single-Phase Multicomponent Simulation

This folder contains the main single-phase CH4 cushion-gas case for the
Mixing-in-UHS DuMuX module.

The case uses DuMuX/DUNE framework infrastructure for the grid, finite-volume
discretization, assembly, nonlinear solve, and output. The local code in this
folder configures the physical problem and connects the custom gas-mixture,
transport, and dispersion extensions used by this simulation.

## Simulation Structure

```text
appl/1p/CH4/
├── CMakeLists.txt
├── params.input
├── main.cc
├── properties.hh
├── problem.hh
├── spatialparams.hh
├── fluidsystems/
│   └── mixture.hh
├── runscript.py
└── vtk-merge-multi.py
```

Related custom framework extensions are outside this folder:

```text
dumux/flux/box/dispersionflux.hh
dumux/material/fluidmatrixinteractions/dispersiontensors/scheidegger.hh
dumux/material/binarycoefficients/h2_ch4.hh
dumux/porousmediumflow/compositional/localresidual.hh
```

## What DuMuX/DUNE Provides

The simulation relies on standard DuMuX/DUNE machinery for:

- DUNE structured grid infrastructure, here through `Dune::YaspGrid`
- DuMuX one-phase multicomponent model infrastructure
- Box finite-volume grid geometry and sub-control-volume faces
- Darcy advection and Fickian molecular diffusion interfaces
- residual assembly, Newton iteration, linear solve, and time stepping
- VTK output and grid-variable management

The custom code configures and extends this framework rather than replacing it.

## Local Case Files

### `properties.hh`

This is the main wiring file for the case. It uses DuMuX type tags and
properties to select:

- `OnePNC` as the base one-phase multicomponent model
- `BoxModel` as the discretization used in the active case
- `Dune::YaspGrid<2>` as the structured grid
- rotational extrusion for axisymmetric radial geometry
- `OnePTwoCTestProblem` from `problem.hh`
- the custom `MixingFluidSystem` wrapped by `OnePAdapter`
- `FicksLaw` for molecular diffusion
- `ScheideggersDispersionTensor` for compositional dispersion
- molar component balances through `UseMoles = true`

This file is a useful first stop because it shows how the simulation is built
from framework pieces and local model choices.

### `main.cc`

This is the standard DuMuX simulation driver. It:

- initializes DuMuX/DUNE runtime services
- reads input parameters
- creates the grid through `GridManager`
- obtains the leaf grid view
- builds grid geometry, problem, and grid variables
- initializes the solution vector
- sets up VTK output
- creates the assembler, linear solver, and Newton solver
- advances the time loop

Most of this file is standard simulation orchestration. The specific modelling
choices come from `properties.hh` and the type tag selected at compile time.

### `problem.hh`

This file defines the physical setup for the CH4 case:

- initial pressure and gas composition
- boundary conditions
- injection and production schedule
- well-region helper functions
- Neumann fluxes for injection/production
- material-balance diagnostics
- JSON/post-processing output

This is where the operating scenario is expressed in DuMuX problem-class form.

### `spatialparams.hh`

This file contains medium properties such as porosity and permeability. These
are queried by the framework during volume-variable and flux calculations.

### `fluidsystems/mixture.hh`

This is the custom high-pressure gas mixture model used by the case. It defines
a multicomponent fluid system for:

- H2O
- CH4
- H2
- CO2
- N2

Important local property logic includes:

- Peng-Robinson gas compressibility factor for density correction
- component Z-factor helper used by the dispersion model
- Wilke-style gas-mixture viscosity with high-pressure component viscosities
- high-pressure binary diffusion coefficient selection
- fallback values where documented correlations still need to be added

## Custom Transport And Property Extensions

### `dumux/flux/box/dispersionflux.hh`

This is the Box-method compositional dispersion flux implementation.

For each component, the implemented face flux has the structure:

```text
J_k_disp = -rho_alpha * (n^T D_disp grad x_k) * area * S_alpha * phi
```

where `D_disp` comes from the selected dispersion model, `grad x_k` is
reconstructed with Box shape-function gradients, and `n` is the face normal.

Useful code points:

- `gradX.axpy(x, gradN)` reconstructs the component-fraction gradient
- `vtmv(n, D, gradX)` computes the normal tensor flux through the face
- `faceTensorAverage(...)` gives a consistent face tensor if inside/outside
  extrusion factors differ

### `dumux/material/fluidmatrixinteractions/dispersiontensors/scheidegger.hh`

This file computes the dispersion matrix used by the Box flux. It reconstructs
a local face velocity, assigns longitudinal and transverse dispersivities, and
returns the directional Scheidegger-type matrix.

The current modes include:

- no dispersion
- grid-size based dispersivity
- a case-specific H2/CH4 Z-ratio correction using Peng-Robinson component
  compressibility factors

### `dumux/porousmediumflow/compositional/localresidual.hh`

This file adds the dispersion flux to the component conservation equations.

The residual follows the usual finite-volume structure:

```text
storage change + net face fluxes - sources
```

The local extension is the addition of:

```cpp
const auto dispersionFluxes = fluxVars.compositionalDispersionFlux(phaseIdx);
for (int compIdx = 0; compIdx < numComponents; ++compIdx)
    flux[conti0EqIdx + compIdx] += dispersionFluxes[compIdx];
```

So `dispersionflux.hh` computes the face rate, and `localresidual.hh` inserts
that rate into the component balances.

### `dumux/material/binarycoefficients/h2_ch4.hh`

This is a focused example of high-pressure binary diffusion. The H2-CH4
implementation starts from a low-pressure gas diffusivity estimate and applies
a dense-fluid correction in the style of:

```text
Riazi, M. R. and Whitson, C. H. (1993).
"Estimating diffusion coefficients of dense fluids."
Industrial & Engineering Chemistry Research, 32(12), 3081-3088.
```

This connects the transport model to pressure-dependent gas properties.

## Build And Run

From the configured DUNE/DuMuX workspace:

```bash
cmake --build Mixing-in-UHS/build-cmake --target appl_1pnc_box_CH4 -j2
```

The executable is created in:

```text
Mixing-in-UHS/build-cmake/appl/1p/CH4/
```

Run from that directory:

```bash
cd Mixing-in-UHS/build-cmake/appl/1p/CH4
./appl_1pnc_box_CH4 params.input
```

The main input file is:

```text
appl/1p/CH4/params.input
```

## Notes And Limitations

- Some empirical constants should eventually be moved to documented input
  tables.
- Dispersion mode 2 is case-specific and should be documented as a named model
  with a clear calibration range.
- Binary diffusion fallback values should be replaced by documented
  correlations or input-controlled values.
- Material-balance diagnostics and JSON output could be separated more cleanly
  from the physical problem class.
- Build outputs under `build-cmake/` should not be committed.
