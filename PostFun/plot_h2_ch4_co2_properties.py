"""
plot_h2_ch4_co2_properties.py
==============================
Publication-quality comparison of H2, CH4 and CO2 thermophysical
properties relevant to underground hydrogen storage.

Data sources and caveats
------------------------
* **Density & viscosity** -- computed from CoolProp (Helmholtz EOS).
* **Isothermal compressibility** -- finite-difference derivative of
  CoolProp density: beta_T = (1/rho)(drho/dP)_T.
* **IFT (gas--water)** -- hard-coded literature data (tabulated below).
* **Solubility (Fig 2b)** -- *approximate* Henry-law screening estimate
  in pure water.  NOT a rigorous high-pressure saline-brine model.
* **Diffusivity (Fig 3b)** -- *approximate* gas-phase Fuller binary
  diffusivity.  NOT an effective porous-medium diffusion coefficient;
  provided only for relative comparison of molecular transport rates.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from CoolProp.CoolProp import PropsSI

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# --- Gases and CoolProp identifiers ---
GASES = ["H2", "CH4", "CO2"]
COOLPROP_NAME = {"H2": "Hydrogen", "CH4": "Methane", "CO2": "CarbonDioxide"}

# --- Colour and style maps (consistent across all figures) ---
GAS_COLOR = {"H2": "#d62728", "CH4": "#1f77b4", "CO2": "#2ca02c"}
TEMP_LS = {298.15: "-", 323.15: "--", 373.15: ":"}
TEMP_LABEL = {298.15: "298 K", 323.15: "323 K", 373.15: "373 K"}

# --- Temperatures ---
TEMPERATURES_K = [298.15, 323.15, 373.15]

# --- Pressure ranges ---
P_MIN_BAR = 1.0
P_MAX_BAR = 400.0
N_P = 300

# --- Finite-difference step for compressibility ---
FD_REL_STEP = 1e-4          # relative dP/P for central difference

# --- Figure settings ---
FIGSIZE = (12, 5)
DPI = 600
OUTDIR = "."

# --- Henry-law constants H [MPa] for gas in pure water ---
# x = P / H(T)  (approximate, pure-water, low-pressure limit)
HENRY_MPA = {
    "H2":  {298.15: 7100.0, 323.15: 7500.0, 373.15: 6900.0},
    "CH4": {298.15: 4000.0, 323.15: 4600.0, 373.15: 5800.0},
    "CO2": {298.15:  167.0, 323.15:  260.0, 373.15:  440.0},
}

# --- Fuller diffusion volumes and molecular weights ---
FULLER_V = {"H2": 7.07, "CH4": 24.42, "CO2": 26.9}
MW = {"H2": 2.016, "CH4": 16.043, "CO2": 44.010}

# --- Diffusion gas pairs and colours ---
DIFF_PAIRS = [("H2", "CH4"), ("H2", "CO2")]
DIFF_COLOR = {("H2", "CH4"): "#9467bd", ("H2", "CO2"): "#ff7f0e"}

# ═══════════════════════════════════════════════════════════════════════════════
# LITERATURE IFT DATA (gas-water) -- embedded exactly as supplied
# ═══════════════════════════════════════════════════════════════════════════════

IFT_DATA = {
    "H2": {
        298: {
            "P_MPa": [0, 0.775397797, 1.659118727, 3.334455324, 4.823439412,
                       7.197674419, 9.943390453, 14.87668299, 19.99510404,
                       24.74173807, 30.04620563, 39.76988984, 45.12148103],
            "IFT_mNm": [72.63157895, 73.28947368, 73.28947368, 73.09210526,
                         72.96052632, 72.5, 72.17105263, 71.51315789,
                         71.05263158, 70.52631579, 70.06578947, 69.47368421,
                         68.88157895],
        },
        323: {
            "P_MPa": [0, 0.699204406, 1.768359853, 3.211750306, 4.840881273,
                       9.820073439, 14.79926561, 19.82588739, 24.94369645],
            "IFT_mNm": [69.21052632, 69.67105263, 69.80263158, 69.47368421,
                         69.21052632, 68.68421053, 68.15789474, 67.43421053,
                         67.10526316],
        },
        373: {
            "P_MPa": [0, 0.698898409, 1.769277846, 4.885250918, 9.862913097,
                       19.86444308, 24.93604651, 29.82252142, 39.96419829],
            "IFT_mNm": [59.73684211, 59.73684211, 59.60526316, 59.67105263,
                         59.47368421, 59.14473684, 58.75, 58.15789474,
                         57.69736842],
        },
    },
    "CH4": {
        298: {
            "P_MPa": [0, 4.714504284, 9.794063647, 14.7004284, 19.82190942,
                       24.84485924],
            "IFT_mNm": [72.5, 66.38157895, 64.27631579, 59.40789474,
                         58.28947368, 58.35526316],
        },
        323: {
            "P_MPa": [0, 4.770807834, 9.803243574, 14.84516524, 19.9244186,
                       24.95654835],
            "IFT_mNm": [67.30263158, 64.27631579, 62.30263158, 58.28947368,
                         56.25, 54.34210526],
        },
        373: {
            "P_MPa": [0, 4.827111383, 9.855875153, 14.85526316, 19.88831089,
                       24.87423501],
            "IFT_mNm": [64.14473684, 62.17105263, 60.98684211, 56.11842105,
                         54.01315789, 52.03947368],
        },
    },
    "CO2": {
        298: {
            "P_MPa": [0, 5.009791922, 9.977662179, 15.04651163, 20.21358629,
                       25.2879437],
            "IFT_mNm": [72.30263158, 32.89473684, 24.80263158, 25.0,
                         24.07894737, 23.09210526],
        },
        323: {
            "P_MPa": [0, 4.747858017, 9.962974296, 14.80416157, 19.88892289,
                       24.9623623],
            "IFT_mNm": [68.28947368, 49.21052632, 27.96052632, 27.10526316,
                         23.88157895, 23.09210526],
        },
        373: {
            "P_MPa": [0, 4.930232558, 9.930844553, 14.98592411, 19.79039168,
                       24.95807834],
            "IFT_mNm": [68.42105263, 50.0, 34.86842105, 28.02631579,
                         25.06578947, 24.01315789],
        },
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# MATPLOTLIB STYLE
# ═══════════════════════════════════════════════════════════════════════════════

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 11,
    "axes.labelsize": 13,
    "axes.titlesize": 14,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "legend.fontsize": 9,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "black",
    "axes.linewidth": 0.8,
    "axes.grid": False,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.top": True,
    "ytick.right": True,
    "text.color": "black",
})

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def bar_to_pa(p_bar):
    """Convert pressure from bar to Pa."""
    return p_bar * 1e5


def safe_coolprop(prop, T_K, P_Pa, fluid):
    """Query CoolProp property; return np.nan on failure."""
    try:
        return PropsSI(prop, "T", T_K, "P", P_Pa, fluid)
    except Exception:
        return np.nan


def compute_density(p_bar_arr, T_K, gas):
    """Return density [kg/m3] for an array of pressures [bar]."""
    fluid = COOLPROP_NAME[gas]
    return np.array([safe_coolprop("D", T_K, bar_to_pa(p), fluid)
                     for p in p_bar_arr])


def compute_viscosity(p_bar_arr, T_K, gas):
    """Return dynamic viscosity [Pa.s] for an array of pressures [bar]."""
    fluid = COOLPROP_NAME[gas]
    return np.array([safe_coolprop("V", T_K, bar_to_pa(p), fluid)
                     for p in p_bar_arr])


def compute_isothermal_compressibility(p_bar_arr, T_K, gas):
    """
    Compute isothermal compressibility  beta_T = (1/rho)(drho/dP)_T
    using a central finite-difference derivative of CoolProp density.

    The derivative is evaluated with a relative pressure step
    dP = FD_REL_STEP * P  (clipped to a minimum absolute step of 100 Pa
    to avoid division by zero at very low pressures).

    Returns beta_T in SI units [1/Pa].
    """
    fluid = COOLPROP_NAME[gas]
    beta = np.full_like(p_bar_arr, np.nan, dtype=float)
    for i, p_bar in enumerate(p_bar_arr):
        P_Pa = bar_to_pa(p_bar)
        dP = max(P_Pa * FD_REL_STEP, 100.0)
        try:
            rho = PropsSI("D", "T", T_K, "P", P_Pa, fluid)
            rho_plus = PropsSI("D", "T", T_K, "P", P_Pa + dP, fluid)
            rho_minus = PropsSI("D", "T", T_K, "P", P_Pa - dP, fluid)
            if rho > 0:
                drho_dP = (rho_plus - rho_minus) / (2.0 * dP)
                beta[i] = drho_dP / rho          # [1/Pa]
        except Exception:
            pass
    return beta


def henry_solubility_estimate(p_mpa_arr, T_K, gas):
    """
    Approximate Henry-law screening estimate of dissolved-gas mole
    fraction in pure water.  x = P / H(T).

    NOT a rigorous high-pressure saline-brine solubility model.
    """
    H = HENRY_MPA[gas][T_K]
    return p_mpa_arr / H


def fuller_binary_diffusivity(p_bar_arr, T_K, gas_a, gas_b):
    """
    Fuller--Schettler--Giddings correlation for gas-phase binary
    diffusion coefficient.

    D_AB = 0.00143 T^1.75 sqrt(1/M_A + 1/M_B)
           / (P_bar (v_A^{1/3} + v_B^{1/3})^2)

    Returns D_AB in [cm2/s].

    NOTE: this is an approximate gas-phase diffusivity, NOT an
    effective porous-medium diffusion coefficient.  Provided only
    for relative comparison of molecular transport rates.
    """
    Ma, Mb = MW[gas_a], MW[gas_b]
    va, vb = FULLER_V[gas_a], FULLER_V[gas_b]
    numer = 0.00143 * T_K**1.75 * np.sqrt(1.0 / Ma + 1.0 / Mb)
    denom = p_bar_arr * (va**(1.0 / 3.0) + vb**(1.0 / 3.0))**2
    return numer / denom


def save_fig(fig, basename):
    """Save a figure in PNG (600 dpi), SVG, and PDF."""
    for ext in ("png", "svg", "pdf"):
        path = f"{OUTDIR}/{basename}.{ext}"
        fig.savefig(path, dpi=DPI if ext == "png" else None,
                    bbox_inches="tight")
    print(f"  Saved {basename}  (.png / .svg / .pdf)")


# ═══════════════════════════════════════════════════════════════════════════════
# PRESSURE ARRAYS
# ═══════════════════════════════════════════════════════════════════════════════

P_bar = np.linspace(P_MIN_BAR, P_MAX_BAR, N_P)
P_MPa_sol = np.linspace(0.1, 45.0, N_P)        # for solubility panel

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 1 -- Density and isothermal compressibility
# ═══════════════════════════════════════════════════════════════════════════════
print("Computing Figure 1 ...")

fig1, (ax1a, ax1b) = plt.subplots(1, 2, figsize=FIGSIZE,
                                   constrained_layout=True)

for gas in GASES:
    for T in TEMPERATURES_K:
        col = GAS_COLOR[gas]
        ls = TEMP_LS[T]

        # Panel (a) -- density
        rho = compute_density(P_bar, T, gas)
        ax1a.plot(P_bar, rho, color=col, ls=ls, lw=1.4)

        # Panel (b) -- isothermal compressibility  [1/Pa -> 1/MPa]
        beta = compute_isothermal_compressibility(P_bar, T, gas)
        ax1b.plot(P_bar, beta * 1e6, color=col, ls=ls, lw=1.4)

# Axes labels
ax1a.set_xlabel("Pressure (bar)")
ax1a.set_ylabel(r"Density (kg/m$^{3}$)")
ax1a.set_title("(a)", loc="left", fontweight="bold")

ax1b.set_xlabel("Pressure (bar)")
ax1b.set_ylabel(r"Isothermal compressibility (MPa$^{-1}$)")
ax1b.set_yscale("log")
ax1b.set_title("(b)", loc="left", fontweight="bold")

# Combined legend  (gas colour + temperature style)
leg = []
for gas in GASES:
    leg.append(Line2D([0], [0], color=GAS_COLOR[gas], lw=2.0, label=gas))
for T in TEMPERATURES_K:
    leg.append(Line2D([0], [0], color="black", ls=TEMP_LS[T], lw=1.2,
                       label=TEMP_LABEL[T]))
ax1b.legend(handles=leg, frameon=False, loc="upper right", ncol=2)

save_fig(fig1, "fig1_density_isothermal_compressibility")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 2 -- IFT and approximate solubility
# ═══════════════════════════════════════════════════════════════════════════════
print("Computing Figure 2 ...")

fig2, (ax2a, ax2b) = plt.subplots(1, 2, figsize=FIGSIZE,
                                   constrained_layout=True)

# Panel (a) -- IFT from literature
IFT_TEMP_KEY = {298.15: 298, 323.15: 323, 373.15: 373}

for gas in GASES:
    col = GAS_COLOR[gas]
    for T in TEMPERATURES_K:
        tkey = IFT_TEMP_KEY[T]
        ls = TEMP_LS[T]
        entry = IFT_DATA[gas][tkey]
        ax2a.plot(entry["P_MPa"], entry["IFT_mNm"],
                  color=col, ls=ls, lw=1.4, marker="o", ms=3.5,
                  markerfacecolor=col, markeredgecolor="none")

ax2a.set_xlabel("Pressure (MPa)")
ax2a.set_ylabel(r"Gas$-$H$_{2}$O IFT (mN/m)")
ax2a.set_title("(a)", loc="left", fontweight="bold")

leg2a = []
for gas in GASES:
    leg2a.append(Line2D([0], [0], color=GAS_COLOR[gas], lw=2, label=gas))
for T in TEMPERATURES_K:
    leg2a.append(Line2D([0], [0], color="black", ls=TEMP_LS[T], lw=1.2,
                         label=TEMP_LABEL[T]))
ax2a.legend(handles=leg2a, frameon=False, loc="lower left", ncol=2)

# Panel (b) -- approximate Henry-law solubility
for gas in GASES:
    col = GAS_COLOR[gas]
    for T in TEMPERATURES_K:
        ls = TEMP_LS[T]
        x_sol = henry_solubility_estimate(P_MPa_sol, T, gas)
        ax2b.plot(P_MPa_sol, x_sol, color=col, ls=ls, lw=1.4)

ax2b.set_xlabel("Pressure (MPa)")
ax2b.set_ylabel("Dissolved gas mole fraction (--)")
ax2b.set_title("(b)", loc="left", fontweight="bold")
ax2b.set_yscale("log")

# Annotation warning
ax2b.text(0.97, 0.03, "Henry-law screening estimate",
          transform=ax2b.transAxes, ha="right", va="bottom",
          fontsize=8, fontstyle="italic", color="grey",
          bbox=dict(facecolor="white", edgecolor="grey",
                    boxstyle="round,pad=0.3", alpha=0.8))

leg2b = []
for gas in GASES:
    leg2b.append(Line2D([0], [0], color=GAS_COLOR[gas], lw=2, label=gas))
for T in TEMPERATURES_K:
    leg2b.append(Line2D([0], [0], color="black", ls=TEMP_LS[T], lw=1.2,
                         label=TEMP_LABEL[T]))
ax2b.legend(handles=leg2b, frameon=False, loc="upper left", ncol=2)

save_fig(fig2, "fig2_ift_solubility")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE 3 -- Viscosity and approximate diffusion coefficient
# ═══════════════════════════════════════════════════════════════════════════════
print("Computing Figure 3 ...")

fig3, (ax3a, ax3b) = plt.subplots(1, 2, figsize=FIGSIZE,
                                   constrained_layout=True)

# Panel (a) -- dynamic viscosity  [Pa.s -> uPa.s]
for gas in GASES:
    col = GAS_COLOR[gas]
    for T in TEMPERATURES_K:
        ls = TEMP_LS[T]
        mu = compute_viscosity(P_bar, T, gas)
        ax3a.plot(P_bar, mu * 1e6, color=col, ls=ls, lw=1.4)

ax3a.set_xlabel("Pressure (bar)")
ax3a.set_ylabel(r"Dynamic viscosity ($\mu$Pa$\cdot$s)")
ax3a.set_title("(a)", loc="left", fontweight="bold")

leg3a = []
for gas in GASES:
    leg3a.append(Line2D([0], [0], color=GAS_COLOR[gas], lw=2, label=gas))
for T in TEMPERATURES_K:
    leg3a.append(Line2D([0], [0], color="black", ls=TEMP_LS[T], lw=1.2,
                         label=TEMP_LABEL[T]))
ax3a.legend(handles=leg3a, frameon=False, loc="upper left", ncol=2)

# Panel (b) -- Fuller binary diffusivity  [cm2/s]
for pair in DIFF_PAIRS:
    col = DIFF_COLOR[pair]
    for T in TEMPERATURES_K:
        ls = TEMP_LS[T]
        D = fuller_binary_diffusivity(P_bar, T, pair[0], pair[1])
        lbl = f"{pair[0]}$-${pair[1]}"
        ax3b.plot(P_bar, D, color=col, ls=ls, lw=1.4)

ax3b.set_xlabel("Pressure (bar)")
ax3b.set_ylabel(r"Diffusion coefficient (cm$^{2}$/s)")
ax3b.set_title("(b)", loc="left", fontweight="bold")
ax3b.set_yscale("log")

ax3b.text(0.97, 0.03, "Gas-phase Fuller estimate",
          transform=ax3b.transAxes, ha="right", va="bottom",
          fontsize=8, fontstyle="italic", color="grey",
          bbox=dict(facecolor="white", edgecolor="grey",
                    boxstyle="round,pad=0.3", alpha=0.8))

leg3b = []
for pair in DIFF_PAIRS:
    leg3b.append(Line2D([0], [0], color=DIFF_COLOR[pair], lw=2,
                         label=f"{pair[0]}$-${pair[1]}"))
for T in TEMPERATURES_K:
    leg3b.append(Line2D([0], [0], color="black", ls=TEMP_LS[T], lw=1.2,
                         label=TEMP_LABEL[T]))
ax3b.legend(handles=leg3b, frameon=False, loc="upper right", ncol=2)

save_fig(fig3, "fig3_viscosity_diffusivity")

print("All figures generated.")
