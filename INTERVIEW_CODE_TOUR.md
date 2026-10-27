# Interview code tour: follow the calculation

Use the **numbered bookmark labels** as the presentation order. The VS Code Bookmarks sidebar may group or sort entries by file and source line, so its visual order can differ from the route below. The primary paper simulator is `appl/1p/CH4` (single-phase, multicomponent gas in a 2D radial grid); `appl/CH4` is a separate two-phase variant.

| Stop | Show | Short explanation |
| --- | --- | --- |
| 01 | `sample_field_data_lhs.py`: CSV read | Begin with processed data from real UK reservoirs. These observations supply plausible property ranges. |
| 02 | Same file: KMeans | Group reservoirs with related permeability, pressure and porosity before sampling. |
| 03 | Same file: LHS | Sample reservoir-property combinations across each cluster. The resulting cases are reservoir-informed synthetic cases, not exact copies of measured fields. |
| 04 | `input_generator.py`: case creation | Package sampled properties and operating values as DuMuX case parameters, including unit conversions. The generator writes JSON. |
| 05 | `runscript.py`: `SLURM_NTASKS` and `mpirun` | Explain the parallel batch-run pattern used for HPC: each case supplies command-line overrides to the DuMuX executable. In this checkout the runner embeds its case list; it does **not** automatically read the generator's JSON. |
| 06 | `properties.hh`: type tag | One DuMuX setup stop: select `OnePNC`, the gas-phase fluid adapter, radial Box geometry, diffusion and dispersion. `problem.hh` and `spatialparams.hh` are connected through properties here. Some inherited names still contain “Two.” |
| 07 | `params.input` | Show the human-readable grid, schedule, transport, rock and Newton settings. Case overrides from the runner replace selected values. |
| 08 | `spatialparams.hh` | Show where the code reads rock properties and returns porosity, permeability and temperature to the physical model. |
| 09 | `main.cc`: `Parameters::init` and `gridManager.init` | Start following program execution: initialize the parameter tree, create the grid and finite-volume geometry, and construct the problem object. |
| 10 | `problem.hh`: `initial_` | The problem supplies the initial pressure and methane-rich composition used to fill the solution vector. |
| 11 | `problem.hh`: `neumann` | The well boundary specifies development injection, H₂ injection, idle time and extraction of the local mixture. This translates the operating schedule into component fluxes. |
| 12 | `main.cc`: `TimeLoop` | Convert the configured end time from days to seconds, set the initial and maximum time steps, and start the transient simulation. |
| 13 | `main.cc`: `FVAssembler<TypeTag, DiffMethod::numeric>` | DuMuX assembles the finite-volume residual and numerical Jacobian; a linear solver handles each Newton update. |
| 14 | `main.cc`: `nonLinearSolver.solve` | At each time step, solve the coupled nonlinear equations, update the prior solution and choose the next time step. |
| 15 | `localresidual.hh`: `computeStorage` | The accumulation term holds each component's pore inventory, using porosity, saturation, fluid density and composition. |
| 16 | `localresidual.hh`: `computeFlux` | Existing face terms account for advective transport and molecular diffusion. This is where to introduce the component balance before discussing the extension. |
| 17 | `localresidual.hh`: dispersion addition | The custom code adds a dispersive flux to each component residual when compositional dispersion is enabled. This is the most direct “what changed” line. |
| 18 | `dispersionflux.hh`: face calculation | Show one physical calculation: a composition gradient and dispersion tensor determine flux across the face, scaled by density and face geometry. Mention the Scheidegger tensor verbally; no separate deep dive is needed. |
| 19 | `problem.hh`: `postTimeStep` | Return to the application after each solve. It accumulates production, injection and reservoir inventories and prepares time histories. |
| 20 | `problem.hh`: H₂ guard and JSON | The program checks relative H₂ material-balance error against its configured tolerance, throws above it and records histories in JSON. VTK output is written from `main.cc`. This is a targeted runtime check, not a full validation suite. |
| 21 | `ANN_Training.py`: split and CV | Explain how simulation-derived recovery factors become training labels. The code uses a 20% holdout and five-fold validation within training. |
| 22 | `ANN_Training.py`: metrics | Show R² and MSE on surrogate predictions. These compare the ANN with simulator results, not the simulator with field measurements. |
| 23 | `ANN_Training.py`: features | Point to the nine predictors, linking the reservoir and operating inputs back to the original design. |
| 24 | `generate_optimisation_scenarios.py` | Apply the trained model to many candidate settings, then derive recovery and cost quantities for optimisation. |
| 25 | `optimise_uk_portfolio.py`: objective | Binary choices select candidate scenarios; the model minimizes total loss cost. |
| 26 | Same file: constraints | Meet an energy-delivery target and choose at most one scenario per reservoir. An optional well budget can also be applied. |

## Spoken bridge between 20 and 21

“The simulator records H₂ injected and produced over each cycle. Post-processing converts those histories into a recovery factor, which is the label for the surrogate.” The recovery-factor function is in `PostFun/compute_dimensionless_numbers.py`, but there is deliberately no bookmark there because this walkthrough does not discuss dimensionless-number analysis.

## Rehearsal guidance

The bookmarks are a navigation map and answer bank, not 26 mandatory stops in ten minutes. Spend the most time on 09–20, especially 13 and 15–18. Move quickly through 01–08 and 21–26. Do not execute `runscript.py` while presenting: it deletes matching output files in its current directory before launching many MPI cases.

The repository has executable case registrations, solver controls, an H₂ balance stopping criterion and ANN evaluation. There is no CI-backed regression suite documented in this checkout. See `INTERVIEW_TESTS_AND_CHECKS.md` for precise wording.
