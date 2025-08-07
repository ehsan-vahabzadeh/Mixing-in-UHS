# Biochemical - Case Description
This simulation case allows testing the implemented model of bio-geo-reactive transport during UHS on a simple geometric structure. In the following, the implemented model is briefly explained.

![image](assets/H2Fraction.gif)


## Fluid and solid system
The fluidsystem comprises two phases (water and gas), which are composed of six components: water ($\mathrm{H_2O}$), methane ($\mathrm{CH_4}$), hydrogen ($\mathrm{H_2}$), carbon dioxide ($\mathrm{CO_2}$), nitrogen ($\mathrm{N_2}$), and hydrogen sulfur ($\mathrm{H_2S}$). Apart from the chemical components, the methanogenic archaea are implemented as an additional pseudo component, which does not affect the fluids' viscosity and density. The characteristic growth parameters are based on [recent literature values](https://www.earthdoc.org/content/papers/10.3997/2214-4609.202035171) and are defined as follows:


|Parameter| Symbol | Value |
| :---      | :---:       | :---:   |
|Maximal growth rate | $\psi^\mathrm{growth}_\mathrm{max}$ | $1.338\cdot 10^{-4} \mathrm{1/s}$ |
|$\mathrm{H_2}$ half velocity constant | $\alpha_\mathrm{H_2}$ | $3.6\cdot 10^{-7}$ |
|$\mathrm{CO_2}$ half velocity constant | $\alpha_\mathrm{CO_2}$ | $1.98\cdot 10^{-6}$ |
|Yield coefficient | $Y$ | $3.9\cdot 10^{11}$ $\mathrm{1/mol}$ |
|Initial number of bacteria | $n^*$ | $1\cdot 10^8$ $\mathrm{m^{-3}}$|

Regarding the solid system, three components are introduced: pyrite, pyrrhotite, and one inert component, quartz. At the current state, the geochemical reaction rate is defined artificially.


## Spatial discretization
The grid composes of a cartesian (YASP) grid with the dimensions $\mathrm{1550m x 1550m x 50m}$. The discretization is defined with 31x31x10 cells. The distribution of petrophysical properties is homogeneous with $\phi = 0.2$, $k_x = k_y = 100\mathrm{mD}$, and $k_z = 10\mathrm{mD}$.

## Fluid-matrix interactions
The fluid-matrix interactions regarding advective flux are defined by the model of Brooks & Corey with the following parameters:

| Parameter | Value |
| :---:       | :---:   |
| $S_{wc}$ | 0.2|
| $S_{gr}$ | 0.1 |
| $\lambda$ | 2 |
| $p_{ce}$  | 0 |

## Initialization
The initialization is performed based on the hydrostatic equilibrium with $p_{\text{init}} = 100\mathrm{bar}$ at the top of the formation. The saturation is at connate water saturation, and the gas is composed of methane and a minor part of $\mathrm{H_2O}$ in thermodynamic equilibrium. The initial volume fraction of pyrite is initially set to 5%. The temperature is set to $T = 40{^\circ}C$.

## Operation schedule
A simplified storage operation is defined as 30 days of injection, 30 days idle, 30 days of production, and 15 days idle.  The operation is
rate controlled with identical rates for injection and production ($1\cdot 10^6\mathrm{Sm^3/d}$ 95% $\mathrm{H_2}$, 5% $\mathrm{CO_2}$).