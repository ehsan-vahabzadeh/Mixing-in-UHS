"""
plot_compressibility_energy.py
==============================
Single publication-ready figure with two subplots:
  (a) Energy density at STP -- gravimetric [kWh/kg] (left y) and
      volumetric [kWh/m^3] (right y) as grouped bars.
  (b) Line plot vs pressure -- isothermal compressibility (left y, log)
      and density (right y) for H2 and CH4 at 4 temperatures,
      with an inset zooming into the low-compressibility zone.

All fluid properties are queried from CoolProp.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle
from matplotlib.lines import Line2D
from CoolProp.CoolProp import PropsSI

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

LHV = {"Hydrogen": 119.96, "Methane": 50.00}   # MJ/kg (NIST)

T_STD_C = 15.0       # deg C
P_STD_PA = 101325    # Pa  (1 atm)

# Pressure range for line plot
P_MIN_MPA = 0.1
P_MAX_MPA = 40.0
N_P = 200

# 4 temperatures for line plot
TEMPERATURES_C = [25, 80, 120, 150]

DPI = 300
OUTDIR = "."

# ═══════════════════════════════════════════════════════════════════════════════
# STYLE
# ═══════════════════════════════════════════════════════════════════════════════

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 18,
    "axes.labelsize": 20,
    "axes.titlesize": 22,
    "xtick.labelsize": 16,
    "ytick.labelsize": 16,
    "legend.fontsize": 13,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "black",
    "axes.grid": False,
    "xtick.color": "black",
    "ytick.color": "black",
    "axes.labelcolor": "black",
    "text.color": "black",
})

# Bar-chart colours
COL_H2 = "#2171b5"
COL_CH4 = "#e6550d"
COL_H2_L = "#6baed6"
COL_CH4_L = "#fdae6b"

# Line-plot colour gradients -- 4 shades per gas
CMAP_H2 = plt.cm.Blues
CMAP_CH4 = plt.cm.Oranges


def shade(n, cmap):
    return [cmap(0.40 + 0.55 * i / (n - 1)) for i in range(n)]


LINE_COL_H2 = shade(len(TEMPERATURES_C), CMAP_H2)
LINE_COL_CH4 = shade(len(TEMPERATURES_C), CMAP_CH4)

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER
# ═══════════════════════════════════════════════════════════════════════════════


def safe_prop(output, T_K, P_Pa, fluid):
    try:
        return PropsSI(output, "T", T_K, "P", P_Pa, fluid)
    except Exception:
        return np.nan


# ═══════════════════════════════════════════════════════════════════════════════
# DATA -- STP values for bar chart
# ═══════════════════════════════════════════════════════════════════════════════

T_std_K = T_STD_C + 273.15

rho_h2_stp = PropsSI("D", "T", T_std_K, "P", P_STD_PA, "Hydrogen")
rho_ch4_stp = PropsSI("D", "T", T_std_K, "P", P_STD_PA, "Methane")

lhv_h2_kwh = LHV["Hydrogen"] / 3.6
lhv_ch4_kwh = LHV["Methane"] / 3.6

vol_h2 = rho_h2_stp * lhv_h2_kwh
vol_ch4 = rho_ch4_stp * lhv_ch4_kwh

# ═══════════════════════════════════════════════════════════════════════════════
# DATA -- line-plot arrays (compressibility + density vs pressure)
# ═══════════════════════════════════════════════════════════════════════════════

pressures_mpa = np.linspace(P_MIN_MPA, P_MAX_MPA, N_P)
pressures_pa = pressures_mpa * 1e6

comp = {}   # (fluid, T_C) -> array  [1/MPa]
dens = {}   # (fluid, T_C) -> array  [kg/m3]

for fluid in ["Hydrogen", "Methane"]:
    for T_C in TEMPERATURES_C:
        T_K = T_C + 273.15
        b = np.full(N_P, np.nan)
        r = np.full(N_P, np.nan)
        for i, P_Pa in enumerate(pressures_pa):
            b[i] = safe_prop("isothermal_compressibility", T_K, P_Pa, fluid)
            r[i] = safe_prop("D", T_K, P_Pa, fluid)
        comp[(fluid, T_C)] = b * 1e6   # 1/Pa -> 1/MPa
        dens[(fluid, T_C)] = r          # kg/m3

print("Data computation complete.")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE
# ═══════════════════════════════════════════════════════════════════════════════

fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(18, 8))

# ─────────────────────────────────────────────────────────────────────────────
# SUBPLOT (a): Energy density bar chart at STP
# ─────────────────────────────────────────────────────────────────────────────

x = np.arange(2)
bar_w = 0.30

bars_grav = ax_a.bar(x - bar_w / 2, [lhv_h2_kwh, lhv_ch4_kwh],
                     bar_w, color=[COL_H2, COL_CH4], edgecolor="black",
                     linewidth=0.8, zorder=3)
ax_a.set_ylabel("Gravimetric (kWh/kg)", color=COL_H2)
ax_a.tick_params(axis="y", colors=COL_H2)

ax_a2 = ax_a.twinx()
bars_vol = ax_a2.bar(x + bar_w / 2, [vol_h2, vol_ch4],
                     bar_w, color=[COL_H2_L, COL_CH4_L], edgecolor="black",
                     linewidth=0.8, hatch="///", zorder=3)
ax_a2.set_ylabel(r"Volumetric (kWh/m$^3$)", color=COL_CH4)
ax_a2.tick_params(axis="y", colors=COL_CH4)

ax_a.set_xticks(x)
ax_a.set_xticklabels(["H$_2$", "CH$_4$"])

for bar, val in zip(bars_grav, [lhv_h2_kwh, lhv_ch4_kwh]):
    ax_a.text(bar.get_x() + bar.get_width() / 2, val,
              f"{val:.1f}", ha="center", va="bottom",
              fontsize=14, fontweight="bold", color=COL_H2)
for bar, val in zip(bars_vol, [vol_h2, vol_ch4]):
    ax_a2.text(bar.get_x() + bar.get_width() / 2, val,
               f"{val:.1f}", ha="center", va="bottom",
               fontsize=14, fontweight="bold", color=COL_CH4)

ax_a.set_ylim(0, max(lhv_h2_kwh, lhv_ch4_kwh) * 1.20)
ax_a2.set_ylim(0, max(vol_h2, vol_ch4) * 1.20)

handles_a = [
    Patch(facecolor=COL_H2, edgecolor="black", label="Gravimetric (kWh/kg)"),
    Patch(facecolor=COL_H2_L, edgecolor="black", hatch="///",
          label=r"Volumetric (kWh/m$^3$)"),
]
ax_a.legend(handles=handles_a, frameon=False, loc="upper center", fontsize=13)
ax_a.set_title("(a)  Energy density at STP", fontweight="bold")

# ─────────────────────────────────────────────────────────────────────────────
# SUBPLOT (b): Compressibility (left y, log) + Density (right y) vs Pressure
# ─────────────────────────────────────────────────────────────────────────────

ax_comp = ax_b                  # left y -- compressibility
ax_dens = ax_b.twinx()          # right y -- density

# Compressibility lines (solid)
for j, T_C in enumerate(TEMPERATURES_C):
    ax_comp.plot(pressures_mpa, comp[("Hydrogen", T_C)],
                 color=LINE_COL_H2[j], linewidth=2.0)
    ax_comp.plot(pressures_mpa, comp[("Methane", T_C)],
                 color=LINE_COL_CH4[j], linewidth=2.0)

# Density lines (dashed)
for j, T_C in enumerate(TEMPERATURES_C):
    ax_dens.plot(pressures_mpa, dens[("Hydrogen", T_C)],
                 color=LINE_COL_H2[j], linewidth=2.0, linestyle="--")
    ax_dens.plot(pressures_mpa, dens[("Methane", T_C)],
                 color=LINE_COL_CH4[j], linewidth=2.0, linestyle="--")

ax_comp.set_yscale("log")
ax_comp.set_xlabel("Pressure (MPa)")
ax_comp.set_ylabel(r"Isothermal compressibility (MPa$^{-1}$)", color=COL_H2)
ax_comp.tick_params(axis="y", colors=COL_H2)

ax_dens.set_ylabel(r"Density (kg/m$^3$)", color=COL_CH4)
ax_dens.tick_params(axis="y", colors=COL_CH4)

ax_b.set_title("(b)  Compressibility & density vs pressure", fontweight="bold")

# ── Legend ──
leg_handles = [
    Line2D([0], [0], color=LINE_COL_H2[-1], lw=3, label="H$_2$"),
    Line2D([0], [0], color=LINE_COL_CH4[-1], lw=3, label="CH$_4$"),
    Line2D([0], [0], color="grey", lw=2, ls="-", label="Compressibility"),
    Line2D([0], [0], color="grey", lw=2, ls="--", label="Density"),
]
for j, T_C in enumerate(TEMPERATURES_C):
    frac = 0.40 + 0.55 * j / (len(TEMPERATURES_C) - 1)
    leg_handles.append(Line2D([0], [0], color=str(1.0 - frac), lw=3,
                              label=f"{T_C} $^\\circ$C"))

ax_comp.legend(handles=leg_handles, frameon=False, loc="upper right",
               fontsize=11, ncol=2)

# ── Inset: zoom into low compressibility (< 0.1 MPa-1) ──
# Use fig.add_axes to avoid mark_inset rendering bug with twinx + log scale
# fig.canvas.draw()   # force layout so get_position() returns final coords
# pos = ax_b.get_position()
# ins_x = pos.x0 + pos.width * 0.22
# ins_y = pos.y0 + pos.height * 0.28
# ins_w = pos.width * 0.40
# ins_h = pos.height * 0.40
# ax_ins = fig.add_axes([ins_x, ins_y, ins_w, ins_h])

# for j, T_C in enumerate(TEMPERATURES_C):
#     ax_ins.plot(pressures_mpa, comp[("Hydrogen", T_C)],
#                 color=LINE_COL_H2[j], linewidth=1.4)
#     ax_ins.plot(pressures_mpa, comp[("Methane", T_C)],
#                 color=LINE_COL_CH4[j], linewidth=1.4)

# beta_ref = comp[("Hydrogen", TEMPERATURES_C[0])]
# mask = beta_ref < 0.1
# p_zoom = pressures_mpa[mask][0] if np.any(mask) else pressures_mpa[N_P // 2]

# ax_ins.set_xlim(p_zoom * 0.95, P_MAX_MPA * 1.01)
# ax_ins.set_ylim(0, 0.10)
# ax_ins.set_xlabel("P (MPa)", fontsize=12)
# ax_ins.set_ylabel(r"$\beta$ (MPa$^{-1}$)", fontsize=12)
# ax_ins.tick_params(labelsize=11)
# ax_ins.grid(True, linestyle=":", color="lightgray", alpha=0.7)
# ax_ins.patch.set_alpha(0.92)

# # Dashed rectangle on main plot to show zoomed region
# rect = Rectangle((p_zoom * 0.95, ax_comp.get_ylim()[0]),
#                   P_MAX_MPA - p_zoom * 0.95, 0.1,
#                   transform=ax_comp.transData,
#                   fill=False, ec="0.5", lw=0.8, ls="--", zorder=5)
# ax_comp.add_patch(rect)

# ─────────────────────────────────────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────────────────────────────────────

fig.subplots_adjust(left=0.07, right=0.92, bottom=0.10, top=0.92, wspace=0.45)
fig.savefig(f"{OUTDIR}/energy_compressibility_h2_ch4.png", dpi=DPI,
            bbox_inches="tight")
fig.savefig(f"{OUTDIR}/energy_compressibility_h2_ch4.svg", bbox_inches="tight")
print("Saved energy_compressibility_h2_ch4.png / .svg")
print("Done.")
