# Checks in the primary one-phase simulation path

This inventory refers to appl/1p/CH4, the paper's CH4 case. The previous inventory described the separate appl/CH4 two-phase variant. Source was inspected; no simulation or CTest test has been run successfully in this workspace.

| Check | Source | Accurate description |
| --- | --- | --- |
| CTest registrations | appl/1p/CH4/CMakeLists.txt:7 and :13 | DuMuX registers TPFA and Box runs with params.input. They are executable case runs without a numerical reference-output comparison in these declarations. |
| Newton controls | appl/1p/CH4/params.input:35 | Sets relative shift, step limits and line search for the framework solver. |
| One-phase selection | appl/1p/CH4/properties.hh:42 and :65 | Inherits OnePNC and adapts the gas phase of the mixture. This establishes model configuration, not validation. |
| H2 balance guard | appl/1p/CH4/problem.hh:541, :566 and :585 | Computes a per-step H2 inventory/flow residual, divides by current H2 inventory and throws above the configured tolerance. params.input:15 sets 1e-3. Other components are written to JSON without the same stopping guard. |
| Output diagnostics | appl/1p/CH4/problem.hh:595 | Writes pressure, H2 error, component inventories and injected/produced amounts to JSON. |
| Post-processing screening | PostFun/compute_dimensionless_numbers.py:299 and :324 | Warns or skips cases with insufficient recovery output or pressure beyond a screening threshold. This is dataset screening, not a unit test of the simulator. |
| Surrogate evaluation | PostFun/ANN_Training.py:27, :44 and :217 | Uses a 20% holdout, five-fold training validation and R2/MSE. This checks ANN predictions against simulation labels, not the physical model against measurements. |

The repository also contains development cases and comparison plots. I found no repository CI workflow, Python pytest/unittest suite, automated reference-solution comparison or documented mesh/time-step convergence study in this checkout. The checked-in build directory previously pointed to another machine, so it does not provide a local passing-test claim.

Suggested interview phrasing: “For this proof of concept, I had executable case runs, solver convergence controls, a configured H2 material-balance stopping criterion and holdout/cross-validation for the surrogate. For a shared production tool, I would add smaller reference cases, conservation checks covering every boundary, refinement studies and CI.”
