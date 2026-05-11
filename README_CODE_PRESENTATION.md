# Mixing-in-UHS Code Presentation Guide

DuMuX/DUNE-based code for porous-media gas mixing, transport, and underground
hydrogen storage simulations.

This document is written as a code-presentation guide. It separates standard
DuMuX/DUNE framework functionality from the case-specific configuration and the
custom extensions for gas mixing, dispersion, and high-pressure properties.

## What This Code Does

The main walkthrough case is:

```text
appl/1p/CH4/
```

This case models one-phase multicomponent gas flow in porous media. It is used
for hydrogen mixing with cushion-gas components such as CH4, CO2, N2, and H2.

The simulation includes:

- Darcy advection
- Fickian molecular diffusion
- custom hydrodynamic dispersion fluxes
- high-pressure gas density, viscosity, and diffusion models
- cyclic injection and production schedules
- material-balance diagnostics and JSON/post-processing output

## What Comes From DuMuX/DUNE

The following are mainly framework-provided:

- DUNE grid infrastructure, including `Dune::YaspGrid`
- DuMuX Box and TPFA finite-volume discretizations
- DuMuX type-tag/property system
- grid geometry, grid variables, and flux-variable infrastructure
- assembler, Newton solver, linear solver, and time loop
- VTK output infrastructure
- standard Darcy advection and Fickian molecular diffusion patterns
- the standard residual structure: storage plus fluxes plus sources

The custom code in this repository works inside this framework.

## Main Contributions To Highlight

The most important custom or modified parts are:

- custom compositional dispersion flux implementation for the Box method
- extension of the compositional local residual so dispersion contributes to
  component balances
- Scheidegger-type dispersion model with case-specific dispersion modes
- high-pressure gas mixture fluid system with Peng-Robinson compressibility
  logic
- high-pressure gas viscosity and binary diffusion coefficient models
- dense-gas diffusion treatment, including Riazi-Whitson style correction for
  selected binary pairs
- case-specific DuMuX problem setup, boundary conditions, operating schedule,
  material-balance diagnostics, and post-processing output

## Recommended Walkthrough Order

For an interview, use this order:

1. `appl/1p/CH4/properties.hh`
2. `appl/1p/CH4/main.cc`
3. `appl/1p/CH4/problem.hh`
4. `appl/1p/CH4/fluidsystems/mixture.hh`
5. `dumux/material/binarycoefficients/h2_ch4.hh`
6. `dumux/material/fluidmatrixinteractions/dispersiontensors/scheidegger.hh`
7. `dumux/flux/box/dispersionflux.hh`
8. `dumux/porousmediumflow/compositional/localresidual.hh`

This starts with how the simulation is wired, then moves toward the physical
models, the numerical flux, and finally the conservation equation.

## Key Files

### `appl/1p/CH4/properties.hh`

This is the best entry point for the architecture.

It uses the DuMuX type-tag/property system to select:

- base model: one-phase multicomponent flow, `OnePNC`
- discretization: Box finite volume through `BoxModel`
- grid: 2D structured `Dune::YaspGrid`
- geometry: rotational extrusion for axisymmetric radial geometry
- problem class: `OnePTwoCTestProblem`
- fluid system: custom gas mixture wrapped with `OnePAdapter`
- molecular diffusion: `FicksLaw`
- compositional dispersion: `ScheideggersDispersionTensor`
- equation basis: molar balances through `UseMoles = true`

Presentation phrase:

> `properties.hh` is the compile-time wiring layer. It connects the framework
> components with my case-specific problem, fluid system, and dispersion model.

### `appl/1p/CH4/main.cc`

This is the simulation driver.

It performs the standard DuMuX workflow:

- initialize DuMuX/DUNE runtime services
- read parameters
- create the grid using `GridManager`
- obtain the leaf grid view
- create grid geometry, problem, and grid variables
- initialize the solution vector
- set up VTK output
- create the assembler, linear solver, and Newton solver
- advance the time loop

Presentation phrase:

> `main.cc` is mostly standard DuMuX simulation orchestration. The custom
> modelling choices are injected through the type-tag/property system.

### `appl/1p/CH4/problem.hh`

This defines the case-specific physical setup:

- initial pressure and composition
- boundary conditions
- injection and production schedule
- well-region logic
- source/sink terms through Neumann boundary fluxes
- material-balance tracking
- JSON/post-processing output

Presentation phrase:

> `problem.hh` is where the reservoir operating scenario lives. The framework
> calls this class when it needs initial conditions, boundary conditions, source
> terms, and post-time-step diagnostics.

### `appl/1p/CH4/fluidsystems/mixture.hh`

This is the custom high-pressure fluid-property model.

It defines a multicomponent fluid system for:

- H2O
- CH4
- H2
- CO2
- N2

Important property logic includes:

- Peng-Robinson compressibility factor for gas density
- component Z-factor helper used by the dispersion model
- pure-component fugacity coefficient placeholders
- Wilke-style gas-mixture viscosity with high-pressure component viscosities
- high-pressure binary diffusion coefficient selection
- fallback diffusion coefficients where documented correlations are not yet
  implemented

Presentation phrase:

> This file connects thermophysical property modelling to the transport
> simulation. It is also where I would be honest about limitations: some
> correlations are research-code choices and need clearer validation ranges for
> production property software.

### `dumux/material/binarycoefficients/h2_ch4.hh`

This is a focused example of a high-pressure binary diffusion model.

The useful story:

> For H2-CH4, the code starts from a low-pressure gas diffusivity estimate and
> applies a dense-fluid correction in the spirit of Riazi and Whitson,
> "Estimating diffusion coefficients of dense fluids", Industrial & Engineering
> Chemistry Research, 1993.

This file is useful for a property-software interview because it connects model
selection, pressure dependence, viscosity/density effects, and validity limits.

### `dumux/material/fluidmatrixinteractions/dispersiontensors/scheidegger.hh`

This file computes the dispersion matrix used by the Box flux calculation.

It:

- reconstructs a local velocity at the sub-control-volume face
- computes longitudinal and transverse dispersivity
- returns a Scheidegger-type directional dispersion matrix
- supports a grid-size based mode
- supports a case-specific mode using an H2/CH4 Peng-Robinson Z-ratio correction

Presentation phrase:

> This file converts physical modelling assumptions about hydrodynamic
> dispersion into the matrix used by the numerical flux calculation.

### `dumux/flux/box/dispersionflux.hh`

This is one of the key custom numerical pieces.

It computes component-wise dispersion fluxes across Box sub-control-volume
faces. In simplified form:

```text
J_k_disp = -rho_alpha * (n^T D_disp grad x_k) * area * S_alpha * phi
```

where:

- `rho_alpha` is gas mass or molar density
- `n` is the face normal
- `D_disp` is the dispersion matrix
- `grad x_k` is the gradient of component fraction
- `area` is the face area including extrusion
- `S_alpha` is phase saturation
- `phi` is porosity

Important implementation details:

- shape-function gradients reconstruct `grad x_k`
- `vtmv(n, D, gradX)` computes the normal component of the tensor flux
- `faceTensorAverage` gives a consistent face tensor when inside/outside
  extrusion factors differ
- main-component balancing is handled consistently with DuMuX conventions

Presentation phrase:

> This is where the physical dispersion model becomes a finite-volume face flux.

### `dumux/porousmediumflow/compositional/localresidual.hh`

This is where the custom dispersion flux is added to the conservation equations.

The residual follows the standard pattern:

```text
residual = storage change + net face fluxes - sources
```

Standard contributions:

- component storage
- advective flux
- molecular diffusive flux
- energy hooks, which are zero for the isothermal case

Custom extension:

```cpp
const auto dispersionFluxes = fluxVars.compositionalDispersionFlux(phaseIdx);
for (int compIdx = 0; compIdx < numComponents; ++compIdx)
    flux[conti0EqIdx + compIdx] += dispersionFluxes[compIdx];
```

Presentation phrase:

> `dispersionflux.hh` computes the face flux; `localresidual.hh` inserts that
> face flux into the component balance equations.

## Repository Structure

```text
Mixing-in-UHS/
├── appl/
│   ├── 1p/
│   │   ├── CH4/                 # Main single-phase CH4 cushion-gas case
│   │   ├── CO2/                 # Related single-phase CO2 case
│   │   ├── H2/                  # Related single-phase H2 case
│   │   └── N2/                  # Related single-phase N2 case
│   ├── CH4/, CO2/, H2/, N2/     # Other/older scenario variants
│   └── Cartesian/               # Cartesian-grid variants
├── dumux/
│   ├── flux/
│   │   └── box/dispersionflux.hh
│   ├── material/
│   │   ├── binarycoefficients/
│   │   ├── components/
│   │   └── fluidmatrixinteractions/dispersiontensors/
│   └── porousmediumflow/compositional/localresidual.hh
├── PostFun/                     # Post-processing and optimization scripts
├── Plots/                       # Generated plots and result summaries
├── CMakeLists.txt
└── dune.module
```

## Build And Run

If the module is already configured, the focused CH4 Box target can be built
with:

```bash
cmake --build Mixing-in-UHS/build-cmake --target appl_1pnc_box_CH4 -j2
```

The executable is created under:

```text
Mixing-in-UHS/build-cmake/appl/1p/CH4/
```

Run from that directory so relative input and output paths are resolved
correctly:

```bash
cd Mixing-in-UHS/build-cmake/appl/1p/CH4
./appl_1pnc_box_CH4 params.input
```

Simulation parameters are defined in:

```text
appl/1p/CH4/params.input
```

## Suggested Interview Narrative

> I used DuMuX/DUNE as the simulation framework. The framework provides the
> grid, discretization, assembly, nonlinear solve, and output infrastructure. My
> work was to configure a one-phase multicomponent gas-mixing model and extend
> it with high-pressure property logic and hydrodynamic dispersion. The type-tag
> setup in `properties.hh` wires the model together. The physical case is in
> `problem.hh`. The real-gas property work is in `mixture.hh` and the binary
> coefficient files. The dispersion model is in `scheidegger.hh`, the Box face
> flux is in `dispersionflux.hh`, and the conservation-equation hook is in
> `localresidual.hh`.

## Known Limitations And TODOs

This is research code, not a polished commercial property package. Important
limitations to discuss honestly:

- some empirical constants and correlations should be moved to documented input
  tables
- correlation validity ranges should be made explicit
- dispersion mode 2 is case-specific and should become a named model with its
  own reference and calibration range
- binary diffusion fallback values should be replaced with documented
  correlations or user-configurable parameters
- material-balance diagnostics and JSON output could be separated more cleanly
  from the physical problem class
- build outputs under `build-cmake/` should not be committed to the repository

## Attribution

The code builds on DuMuX and DUNE. DuMuX/DUNE framework functionality remains
the work of their respective projects and contributors. This repository contains
case configuration and research extensions for gas-mixing and underground
hydrogen storage simulations.
