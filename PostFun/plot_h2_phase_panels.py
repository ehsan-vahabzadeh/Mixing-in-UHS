"""
plot_h2_phase_panels.py
=======================
Generates a single figure with 3 vertically stacked panels for Hydrogen (H2):
  (a) P–T phase diagram
  (b) Density vs Temperature at fixed pressures
  (c) Viscosity vs Temperature at fixed pressures

All fluid properties are queried from CoolProp.
Outputs: h2_phase_panels.png and h2_phase_panels.svg
"""

import numpy as np
import matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION — edit these parameters as needed
# ═══════════════════════════════════════════════════════════════════════════════

FLUID = "Hydrogen"

# Temperature display: False = Kelvin (recommended for H2), True = Celsius
USE_CELSIUS = False

# Pressure list for panels (b) and (c), in MPa
PRESSURES_MPA = [0.1, 0.3, 0.6, 1.0, 1.3, 2, 3, 5, 10, 20, 30, 50, 70]

# Temperature range for panels (b) and (c), in Kelvin
T_MIN_K = 200.0  # lower display bound
T_MAX_K = 400.0  # upper display bound
N_POINTS = 500   # number of temperature sample points

# Depth guide lines on panel (a)
SHOW_DEPTH_GUIDES = True
GEOTHERMAL_GRADIENT = 30.0   # K/km
PRESSURE_GRADIENT = 10.0     # MPa/km
T_SURFACE_K = 288.15         # surface temperature (15 °C)
P_SURFACE_MPA = 0.101325     # surface pressure (1 atm)

# Output settings
DPI = 300

# ═══════════════════════════════════════════════════════════════════════════════
# FLUID PROPERTIES FROM COOLPROP
# ═══════════════════════════════════════════════════════════════════════════════

T_CRIT = PropsSI("Tcrit", FLUID)           # critical temperature [K]
P_CRIT = PropsSI("pcrit", FLUID)           # critical pressure [Pa]
T_TRIPLE = PropsSI("Ttriple", FLUID)       # triple-point temperature [K]
P_TRIPLE = PropsSI("ptriple", FLUID)       # triple-point pressure [Pa]
RHO_CRIT = PropsSI("rhocrit", FLUID)       # critical density [kg/m³]

P_CRIT_MPA = P_CRIT / 1e6
P_TRIPLE_MPA = P_TRIPLE / 1e6

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def k_to_display(T_K):
    """Convert temperature array from Kelvin to display units."""
    if USE_CELSIUS:
        return T_K - 273.15
    return T_K


def temp_label():
    """Return the x-axis label string for temperature."""
    if USE_CELSIUS:
        return "Temperature (°C)"
    return "Temperature (K)"


def safe_props(output, T=None, P=None, Q=None, fluid=FLUID):
    """
    Safely query a CoolProp property. Returns np.nan on failure.

    Specify exactly two of T [K], P [Pa], Q (quality 0–1).
    """
    try:
        if T is not None and P is not None:
            return PropsSI(output, "T", T, "P", P, fluid)
        elif T is not None and Q is not None:
            return PropsSI(output, "T", T, "Q", Q, fluid)
        elif P is not None and Q is not None:
            return PropsSI(output, "P", P, "Q", Q, fluid)
    except Exception:
        return np.nan
    return np.nan


# ═══════════════════════════════════════════════════════════════════════════════
# DATA COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════════

# --- Saturation / vaporisation curve (triple point → critical point) ---
T_sat = np.linspace(T_TRIPLE + 0.01, T_CRIT - 0.01, 300)
P_sat = np.array([safe_props("P", T=t, Q=0) for t in T_sat]) / 1e6  # MPa

# Saturated liquid and vapor densities for panel (b) dome
rho_sat_liq = np.array([safe_props("D", T=t, Q=0) for t in T_sat])
rho_sat_vap = np.array([safe_props("D", T=t, Q=1) for t in T_sat])

# Saturated liquid and vapor viscosities for panel (c) dome
# CoolProp may not reliably provide viscosity along the saturation curve
# for all fluids; we attempt it and fall back to NaN gracefully.
mu_sat_liq = np.array([safe_props("V", T=t, Q=0) for t in T_sat]) * 1e3  # mPa·s
mu_sat_vap = np.array([safe_props("V", T=t, Q=1) for t in T_sat]) * 1e3  # mPa·s
has_sat_viscosity = not (np.all(np.isnan(mu_sat_liq)) and np.all(np.isnan(mu_sat_vap)))

# --- Isobaric curves for panels (b) and (c) ---
T_range = np.linspace(T_MIN_K, T_MAX_K, N_POINTS)

density_curves = {}    # MPa -> array of kg/m³
viscosity_curves = {}  # MPa -> array of mPa·s

for p_mpa in PRESSURES_MPA:
    p_pa = p_mpa * 1e6
    rho = np.full_like(T_range, np.nan)
    mu = np.full_like(T_range, np.nan)
    for i, t in enumerate(T_range):
        rho[i] = safe_props("D", T=t, P=p_pa)
        mu[i] = safe_props("V", T=t, P=p_pa)
    density_curves[p_mpa] = rho
    viscosity_curves[p_mpa] = mu * 1e3  # Pa·s → mPa·s

# Critical-point viscosity for panel (c) marker
mu_crit = safe_props("V", T=T_CRIT, P=P_CRIT) * 1e3  # mPa·s

# ═══════════════════════════════════════════════════════════════════════════════
# PLOTTING
# ═══════════════════════════════════════════════════════════════════════════════

plt.rcParams.update({
    "font.size": 10,
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 8,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "black",
    "xtick.color": "black",
    "ytick.color": "black",
    "axes.labelcolor": "black",
    "text.color": "black",
})

fig, axes = plt.subplots(3, 1, figsize=(7, 9), sharex=True)
panel_labels = ["a", "b", "c"]

# Shared x-axis data for display
T_sat_disp = k_to_display(T_sat)
T_range_disp = k_to_display(T_range)
T_crit_disp = k_to_display(np.array([T_CRIT]))[0]
T_triple_disp = k_to_display(np.array([T_TRIPLE]))[0]

# ───────────────────────────────────────────────────────────────────────────────
# PANEL (a): P–T phase diagram
# ───────────────────────────────────────────────────────────────────────────────
ax = axes[0]

# Vaporisation / saturation curve
ax.plot(T_sat_disp, P_sat, "k-", linewidth=1.5, label="Saturation curve")

# CoolProp does not directly provide the solid–liquid (melting) boundary.
# The melting curve is omitted here; add manually if needed.

# Critical and triple points
ax.plot(T_crit_disp, P_CRIT_MPA, "ko", markersize=6, zorder=5)
ax.annotate("Critical Point", xy=(T_crit_disp, P_CRIT_MPA),
            xytext=(12, 8), textcoords="offset points", fontsize=8,
            arrowprops=dict(arrowstyle="-", lw=0.6))

ax.plot(T_triple_disp, P_TRIPLE_MPA, "ks", markersize=5, zorder=5)
ax.annotate("Triple Point", xy=(T_triple_disp, P_TRIPLE_MPA),
            xytext=(12, -12), textcoords="offset points", fontsize=8,
            arrowprops=dict(arrowstyle="-", lw=0.6))

# Dashed vertical line at critical temperature
ax.axvline(T_crit_disp, color="k", linestyle="--", linewidth=0.7, alpha=0.6)

# Dashed horizontal line at critical pressure
ax.axhline(P_CRIT_MPA, color="k", linestyle="--", linewidth=0.7, alpha=0.6)

# Region labels
ax.text(T_triple_disp + 1, P_CRIT_MPA * 5, "Liquid", fontsize=9,
        fontstyle="italic", ha="left")
ax.text(T_crit_disp + 5 if not USE_CELSIUS else T_crit_disp + 5,
        P_TRIPLE_MPA * 3, "Gas", fontsize=9, fontstyle="italic", ha="left")
ax.text(T_crit_disp + 5 if not USE_CELSIUS else T_crit_disp + 5,
        P_CRIT_MPA * 5, "Supercritical\nRegion", fontsize=9,
        fontstyle="italic", ha="left")

# Depth guide lines
if SHOW_DEPTH_GUIDES:
    for depth_km, ls in [(1.0, ":"), (2.0, "-.")]:
        t_depth = T_SURFACE_K + GEOTHERMAL_GRADIENT * depth_km
        p_depth = P_SURFACE_MPA + PRESSURE_GRADIENT * depth_km
        t_disp = k_to_display(np.array([T_SURFACE_K, t_depth]))
        p_vals = [P_SURFACE_MPA, p_depth]
        ax.plot(t_disp, p_vals, color="gray", linestyle=ls, linewidth=1.0)
        ax.annotate(f"{depth_km:.0f} km", xy=(t_disp[-1], p_vals[-1]),
                    xytext=(5, 0), textcoords="offset points", fontsize=7,
                    color="gray")

ax.set_yscale("log")
ax.set_ylabel("Pressure (MPa)")
ax.set_xlim(k_to_display(np.array([T_MIN_K]))[0],
            k_to_display(np.array([T_MAX_K]))[0])

# ───────────────────────────────────────────────────────────────────────────────
# PANEL (b): Density vs Temperature
# ───────────────────────────────────────────────────────────────────────────────
ax = axes[1]

# Saturation dome (liquid + vapor branches)
ax.plot(T_sat_disp, rho_sat_liq, "k--", linewidth=1.0, label="Sat. liquid")
ax.plot(T_sat_disp, rho_sat_vap, "k--", linewidth=1.0, label="Sat. vapor")

# Isobaric density curves
for p_mpa in PRESSURES_MPA:
    ax.plot(T_range_disp, density_curves[p_mpa], "k-", linewidth=0.6)

# Label a few representative pressure curves at the right edge
for p_mpa in PRESSURES_MPA:
    rho_arr = density_curves[p_mpa]
    # Find last valid value for label placement
    valid = np.where(np.isfinite(rho_arr))[0]
    if len(valid) > 0:
        idx = valid[-1]
        ax.annotate(f"{p_mpa} MPa", xy=(T_range_disp[idx], rho_arr[idx]),
                    fontsize=5.5, ha="left", va="center",
                    xytext=(3, 0), textcoords="offset points")

# Critical point
ax.plot(T_crit_disp, RHO_CRIT, "ko", markersize=5, zorder=5)
ax.axvline(T_crit_disp, color="k", linestyle="--", linewidth=0.7, alpha=0.6)

ax.set_ylabel(r"Density (kg/m$^3$)")

# ───────────────────────────────────────────────────────────────────────────────
# PANEL (c): Viscosity vs Temperature
# ───────────────────────────────────────────────────────────────────────────────
ax = axes[2]

# Saturation dome for viscosity (if available)
if has_sat_viscosity:
    ax.plot(T_sat_disp, mu_sat_liq, "k--", linewidth=1.0, label="Sat. liquid")
    ax.plot(T_sat_disp, mu_sat_vap, "k--", linewidth=1.0, label="Sat. vapor")
else:
    # CoolProp may not reliably return saturated viscosity for H2 at all
    # temperatures. The saturation dome is omitted for viscosity.
    pass

# Isobaric viscosity curves
for p_mpa in PRESSURES_MPA:
    ax.plot(T_range_disp, viscosity_curves[p_mpa], "k-", linewidth=0.6)

# Label a few representative pressure curves at the right edge
for p_mpa in PRESSURES_MPA:
    mu_arr = viscosity_curves[p_mpa]
    valid = np.where(np.isfinite(mu_arr))[0]
    if len(valid) > 0:
        idx = valid[-1]
        ax.annotate(f"{p_mpa} MPa", xy=(T_range_disp[idx], mu_arr[idx]),
                    fontsize=5.5, ha="left", va="center",
                    xytext=(3, 0), textcoords="offset points")

# Critical point
if np.isfinite(mu_crit):
    ax.plot(T_crit_disp, mu_crit, "ko", markersize=5, zorder=5)
ax.axvline(T_crit_disp, color="k", linestyle="--", linewidth=0.7, alpha=0.6)

ax.set_ylabel(r"Viscosity (mPa$\cdot$s)")
ax.set_xlabel(temp_label())

# ───────────────────────────────────────────────────────────────────────────────
# PANEL LABELS AND FINAL LAYOUT
# ───────────────────────────────────────────────────────────────────────────────
for i, ax in enumerate(axes):
    ax.text(-0.08, 1.02, panel_labels[i], transform=ax.transAxes,
            fontsize=13, fontweight="bold", va="bottom", ha="right")

fig.tight_layout()

# Save outputs
fig.savefig("h2_phase_panels.png", dpi=DPI, bbox_inches="tight")
fig.savefig("h2_phase_panels.svg", bbox_inches="tight")
print("Saved: h2_phase_panels.png, h2_phase_panels.svg")

plt.show()
