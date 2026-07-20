"""
generate_methods_pdf.py
========================
Creates a multi-page PDF document explaining every property calculation
used in plot_h2_ch4_co2_properties.py.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

OUTFILE = "property_calculation_methods.pdf"

# ── page style ──────────────────────────────────────────────────────────────
PAGE_W, PAGE_H = 8.5, 11          # US Letter inches
MARGIN_L, MARGIN_R = 0.10, 0.90   # fraction of page width
TOP, BOT = 0.94, 0.06             # fraction of page height

FONT_TITLE = {"fontsize": 18, "fontweight": "bold", "family": "serif"}
FONT_SEC = {"fontsize": 14, "fontweight": "bold", "family": "serif"}
FONT_SUB = {"fontsize": 12, "fontweight": "bold", "family": "serif"}
FONT_BODY = {"fontsize": 10.5, "family": "serif"}
FONT_EQ = {"fontsize": 12, "family": "serif"}
FONT_NOTE = {"fontsize": 9.5, "family": "serif", "fontstyle": "italic",
             "color": "#444444"}
FONT_FOOT = {"fontsize": 8, "family": "serif", "color": "grey"}

LINE_H = 0.032   # vertical spacing between body lines (fraction of page)
EQ_GAP = 0.012   # extra gap before/after equations


def new_page(pdf):
    fig = plt.figure(figsize=(PAGE_W, PAGE_H))
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def put(ax, x, y, txt, fontdict=None, **kw):
    fontdict = fontdict or FONT_BODY
    ax.text(x, y, txt, fontdict=fontdict, va="top",
            transform=ax.transAxes, **kw)


def put_eq(ax, x, y, tex, fontdict=None):
    fontdict = fontdict or FONT_EQ
    ax.text(x, y, tex, fontdict=fontdict, va="top",
            transform=ax.transAxes)


def hline(ax, y, lw=0.5):
    ax.plot([MARGIN_L, MARGIN_R], [y, y], color="black", lw=lw,
            transform=ax.transAxes, clip_on=False)


# ═══════════════════════════════════════════════════════════════════════════════
with PdfPages(OUTFILE) as pdf:

    # ── PAGE 1: Title + Density ─────────────────────────────────────────────
    fig, ax = new_page(pdf)
    y = TOP

    put(ax, 0.50, y, "Property Calculation Methods", FONT_TITLE, ha="center")
    y -= 0.020
    put(ax, 0.50, y,
        "Supplementary note for plot_h2_ch4_co2_properties.py",
        FONT_NOTE, ha="center")
    y -= 0.010
    hline(ax, y)
    y -= LINE_H

    put(ax, MARGIN_L, y,
        "This document describes how each thermophysical property shown in "
        "Figures 1-3 is computed.\nGases considered: H2, CH4, CO2.  "
        "Temperatures: 298.15, 323.15, 373.15 K.  "
        "Pressures: 1-400 bar (Figs 1, 3) or 0.1-45 MPa (Fig 2).",
        FONT_BODY)
    y -= 3.0 * LINE_H

    # Section 1 - Density
    put(ax, MARGIN_L, y, "1.  Density  (Figure 1a)", FONT_SEC)
    y -= 1.4 * LINE_H

    put(ax, MARGIN_L, y,
        "Source:  CoolProp library (http://www.coolprop.org)",
        {**FONT_BODY, "fontweight": "bold"})
    y -= LINE_H

    body1 = (
        "Density is obtained directly from the CoolProp implementation of "
        "multi-parameter Helmholtz\n"
        "free-energy equations of state.  The specific EOS used for each "
        "fluid is:\n\n"
        "    H2    Leachman et al. (2009), J. Phys. Chem. Ref. Data 38(3)\n"
        "    CH4   Setzmann & Wagner (1991), J. Phys. Chem. Ref. Data 20(6)\n"
        "    CO2   Span & Wagner (1996), J. Phys. Chem. Ref. Data 25(6)\n\n"
        "The CoolProp call is:"
    )
    put(ax, MARGIN_L, y, body1)
    y -= 6.2 * LINE_H

    put(ax, MARGIN_L + 0.04, y,
        r"$\rho(T, P)$ = PropsSI('D', 'T', $T$ [K], 'P', $P$ [Pa], fluid)",
        FONT_EQ)
    y -= 1.8 * LINE_H

    put(ax, MARGIN_L, y,
        "where 'D' requests mass density in kg/m3.  Invalid or two-phase "
        "state points are caught by\n"
        "a try/except block and replaced with NaN.")
    y -= 3.0 * LINE_H

    # Section 2 - Compressibility
    put(ax, MARGIN_L, y,
        "2.  Isothermal Compressibility  (Figure 1b)", FONT_SEC)
    y -= 1.4 * LINE_H

    put(ax, MARGIN_L, y, "Definition:", {**FONT_BODY, "fontweight": "bold"})
    y -= LINE_H

    put(ax, MARGIN_L, y,
        "The isothermal compressibility is defined as the fractional change "
        "in density with pressure\n"
        "at constant temperature.  It is NOT the compressibility factor Z = "
        "Pv/(RT).")
    y -= 2.5 * LINE_H

    put_eq(ax, 0.30, y,
           r"$\beta_T \;=\; \dfrac{1}{\rho}\,\left(\dfrac{\partial \rho}"
           r"{\partial P}\right)_{\!T}$"
           r"$\qquad\mathrm{[Pa^{-1}]}$")
    y -= 2.5 * LINE_H

    put(ax, MARGIN_L, y, "Numerical method:",
        {**FONT_BODY, "fontweight": "bold"})
    y -= LINE_H

    put(ax, MARGIN_L, y,
        "The partial derivative is approximated with a second-order central "
        "finite difference:")
    y -= 1.5 * LINE_H

    put_eq(ax, 0.20, y,
           r"$\left(\dfrac{\partial \rho}{\partial P}\right)_{\!T}"
           r"\;\approx\;\dfrac{\rho(T,\,P+\Delta P)"
           r"\;-\;\rho(T,\,P-\Delta P)}{2\,\Delta P}$")
    y -= 2.5 * LINE_H

    put(ax, MARGIN_L, y,
        "where the pressure perturbation is:")
    y -= 1.5 * LINE_H

    put_eq(ax, 0.25, y,
           r"$\Delta P \;=\; \max(\varepsilon_{\mathrm{rel}}"
           r"\cdot P,\;\;100\;\mathrm{Pa})$"
           r"$,\qquad \varepsilon_{\mathrm{rel}} = 10^{-4}$")
    y -= 2.2 * LINE_H

    put(ax, MARGIN_L, y,
        "The 100 Pa floor prevents division by zero at very low pressures.  "
        "Both forward and backward\n"
        "density evaluations use CoolProp.  "
        "The result is converted from Pa-1 to MPa-1 for plotting:\n")
    y -= 2.2 * LINE_H

    put_eq(ax, 0.28, y,
           r"$\beta_T\;\mathrm{[MPa^{-1}]} \;=\; "
           r"\beta_T\;\mathrm{[Pa^{-1}]} \;\times\; 10^6$")
    y -= 1.5 * LINE_H

    put(ax, MARGIN_L, y,
        "Error characteristics:",
        {**FONT_BODY, "fontweight": "bold"})
    y -= LINE_H

    put(ax, MARGIN_L, y,
        "Central differencing is O(dP2) accurate.  Near CO2 phase "
        "boundaries (298 K, ~64 bar) the\n"
        "derivative exhibits a sharp spike because drho/dP diverges "
        "approaching the saturation curve.\n"
        "This is physically correct and not a numerical artefact.")

    put(ax, 0.50, BOT,
        "Page 1 of 4", FONT_FOOT, ha="center")
    pdf.savefig(fig)
    plt.close(fig)

    # ── PAGE 2: IFT + Solubility ────────────────────────────────────────────
    fig, ax = new_page(pdf)
    y = TOP

    put(ax, MARGIN_L, y,
        "3.  Gas-Water Interfacial Tension  (Figure 2a)", FONT_SEC)
    y -= 1.4 * LINE_H

    put(ax, MARGIN_L, y, "Source:",
        {**FONT_BODY, "fontweight": "bold"})
    y -= LINE_H

    put(ax, MARGIN_L, y,
        "IFT values are hard-coded literature data (digitised from published "
        "experimental curves).\nNo model or correlation is applied; "
        "the data points are plotted as-is with linear interpolation\n"
        "between markers.")
    y -= 3.0 * LINE_H

    put(ax, MARGIN_L, y,
        "The data is stored as Python dictionaries keyed by gas name and "
        "temperature (integer K).\n"
        "Each entry contains arrays of pressure [MPa] and IFT [mN/m].\n\n"
        "Temperatures in the IFT table use integer keys (298, 323, 373) "
        "mapped from the floating-point\n"
        "values 298.15, 323.15, 373.15 K used elsewhere in the script.")
    y -= 5.0 * LINE_H

    put(ax, MARGIN_L, y, "Key physical observations:",
        {**FONT_BODY, "fontweight": "bold"})
    y -= LINE_H
    put(ax, MARGIN_L, y,
        "  - H2-water IFT decreases only slightly with pressure "
        "(~72 to ~69 mN/m over 0-45 MPa).\n"
        "  - CH4-water IFT shows moderate reduction "
        "(~72 to ~52 mN/m).\n"
        "  - CO2-water IFT drops dramatically near the CO2 phase transition "
        "(~72 to ~23 mN/m),\n"
        "    reflecting the much stronger CO2-water molecular interaction "
        "and near-critical density changes.")
    y -= 5.0 * LINE_H

    hline(ax, y)
    y -= LINE_H

    put(ax, MARGIN_L, y,
        "4.  Approximate Solubility  (Figure 2b)", FONT_SEC)
    y -= 1.4 * LINE_H

    put(ax, MARGIN_L, y, "Model:",
        {**FONT_BODY, "fontweight": "bold"})
    y -= LINE_H

    put(ax, MARGIN_L, y,
        "Dissolved-gas mole fraction in pure water is estimated using "
        "Henry's law:")
    y -= 1.5 * LINE_H

    put_eq(ax, 0.35, y,
           r"$x \;=\; \dfrac{P}{H(T)}$")
    y -= 2.2 * LINE_H

    put(ax, MARGIN_L, y,
        "where P is the total pressure [MPa] and H(T) is the Henry-law "
        "constant [MPa] at temperature T.")
    y -= 1.5 * LINE_H

    put(ax, MARGIN_L, y, "Henry-law constants used (MPa):",
        {**FONT_BODY, "fontweight": "bold"})
    y -= LINE_H
    put(ax, MARGIN_L, y,
        "                   298.15 K      323.15 K      373.15 K\n"
        "    H2              7100           7500           6900\n"
        "    CH4             4000           4600           5800\n"
        "    CO2              167            260            440")
    y -= 4.5 * LINE_H

    put(ax, MARGIN_L, y,
        "These are approximate values for gas dissolution in pure water "
        "at low to moderate pressures,\n"
        "compiled from standard thermodynamic references (e.g. Sander, "
        "2015, Atmos. Chem. Phys.).")
    y -= 2.5 * LINE_H

    put(ax, MARGIN_L, y, "Limitations:",
        {**FONT_BODY, "fontweight": "bold", "color": "#b00000"})
    y -= LINE_H

    put(ax, MARGIN_L, y,
        "  - Henry's law is strictly valid only in the dilute / low-pressure "
        "limit.\n"
        "  - At high pressures (>~10 MPa), fugacity corrections and "
        "activity-coefficient models\n"
        "    (e.g. Duan & Sun, 2003 for CO2; Li et al., 2018 for H2) "
        "are required.\n"
        "  - Salinity effects (brine) are not accounted for; "
        "the Setschenow salting-out effect\n"
        "    reduces solubility significantly in formation brines.\n"
        "  - This is labelled in the figure as a "
        "\"Henry-law screening estimate\".")

    put(ax, 0.50, BOT,
        "Page 2 of 4", FONT_FOOT, ha="center")
    pdf.savefig(fig)
    plt.close(fig)

    # ── PAGE 3: Viscosity + Diffusivity ─────────────────────────────────────
    fig, ax = new_page(pdf)
    y = TOP

    put(ax, MARGIN_L, y,
        "5.  Dynamic Viscosity  (Figure 3a)", FONT_SEC)
    y -= 1.4 * LINE_H

    put(ax, MARGIN_L, y, "Source:",
        {**FONT_BODY, "fontweight": "bold"})
    y -= LINE_H

    put(ax, MARGIN_L, y,
        "Viscosity is obtained from CoolProp using the same Helmholtz-based "
        "EOS framework.\n"
        "CoolProp internally uses the following transport-property "
        "correlations:\n\n"
        "    H2    Muzny et al. (2013), J. Chem. Eng. Data 58(4)\n"
        "    CH4   Quinones-Cisneros et al. (2012), "
        "J. Chem. Eng. Data 57(12)\n"
        "    CO2   Fenghour et al. (1998), "
        "J. Phys. Chem. Ref. Data 27(1)")
    y -= 6.5 * LINE_H

    put(ax, MARGIN_L, y, "The CoolProp call is:")
    y -= 1.2 * LINE_H

    put(ax, MARGIN_L + 0.04, y,
        r"$\mu(T, P)$ = PropsSI('V', 'T', $T$ [K], 'P', $P$ [Pa], fluid)"
        "     [Pa.s]",
        FONT_EQ)
    y -= 1.8 * LINE_H

    put(ax, MARGIN_L, y,
        "The result is converted to micro-Pascal-seconds for plotting:")
    y -= 1.5 * LINE_H

    put_eq(ax, 0.25, y,
           r"$\mu\;\mathrm{[\mu Pa \cdot s]}"
           r"\;=\;\mu\;\mathrm{[Pa \cdot s]}\;\times\;10^6$")
    y -= 2.5 * LINE_H

    hline(ax, y)
    y -= LINE_H

    put(ax, MARGIN_L, y,
        "6.  Approximate Binary Gas-Phase Diffusion Coefficient  "
        "(Figure 3b)", FONT_SEC)
    y -= 1.4 * LINE_H

    put(ax, MARGIN_L, y, "Correlation:",
        {**FONT_BODY, "fontweight": "bold"})
    y -= LINE_H

    put(ax, MARGIN_L, y,
        "The Fuller-Schettler-Giddings (1966) correlation for gas-phase "
        "binary diffusion:")
    y -= 1.8 * LINE_H

    put_eq(ax, 0.12, y,
           r"$D_{AB}\;\mathrm{[cm^2/s]}"
           r"\;=\;\dfrac{0.00143\;\;T^{\,1.75}\;\sqrt{M_A^{-1}+M_B^{-1}}}"
           r"{P\;\left(\Sigma v_A^{\,1/3}+\Sigma v_B^{\,1/3}\right)^2}$")
    y -= 3.0 * LINE_H

    put(ax, MARGIN_L, y, "where:",
        {**FONT_BODY, "fontweight": "bold"})
    y -= LINE_H
    put(ax, MARGIN_L, y,
        r"    T  = temperature [K]" "\n"
        r"    P  = pressure [bar]" "\n"
        r"    MA, MB  = molecular weights [g/mol]" "\n"
        r"    Sv_A, Sv_B = Fuller atomic diffusion volumes [-]")
    y -= 4.5 * LINE_H

    put(ax, MARGIN_L, y, "Parameters used:",
        {**FONT_BODY, "fontweight": "bold"})
    y -= LINE_H

    put(ax, MARGIN_L, y,
        "    Species     MW [g/mol]     Fuller volume\n"
        "    H2           2.016            7.07\n"
        "    CH4         16.043           24.42\n"
        "    CO2         44.010           26.90")
    y -= 4.5 * LINE_H

    put(ax, MARGIN_L, y, "Gas pairs plotted:",
        {**FONT_BODY, "fontweight": "bold"})
    y -= LINE_H
    put(ax, MARGIN_L, y,
        "    H2-CH4   (purple)    and    H2-CO2   (orange)")
    y -= 2.0 * LINE_H

    put(ax, MARGIN_L, y, "Limitations:",
        {**FONT_BODY, "fontweight": "bold", "color": "#b00000"})
    y -= LINE_H
    put(ax, MARGIN_L, y,
        "  - The Fuller correlation is for ideal gas-phase binary diffusion "
        "only.\n"
        "  - It does NOT represent effective diffusion in a porous medium,\n"
        "    which depends on tortuosity, porosity, and saturation.\n"
        "  - It is provided for relative comparison of molecular "
        "transport rates.\n"
        "  - Labelled in the figure as \"Gas-phase Fuller estimate\".")

    put(ax, 0.50, BOT,
        "Page 3 of 4", FONT_FOOT, ha="center")
    pdf.savefig(fig)
    plt.close(fig)

    # ── PAGE 4: Unit conversions + summary table ────────────────────────────
    fig, ax = new_page(pdf)
    y = TOP

    put(ax, MARGIN_L, y,
        "7.  Unit Conversions", FONT_SEC)
    y -= 1.4 * LINE_H

    put(ax, MARGIN_L, y,
        "All internal calculations are performed in SI units.  "
        "The following conversions are applied\n"
        "for plotting:")
    y -= 2.5 * LINE_H

    put(ax, MARGIN_L, y,
        "    Pressure:        1 bar   = 1e5 Pa     = 0.1 MPa\n"
        "    Density:         [kg/m3]  (no conversion)\n"
        "    Compressibility: 1 Pa-1  = 1e6 MPa-1\n"
        "    Viscosity:       1 Pa.s  = 1e6 uPa.s\n"
        "    Diffusivity:     [cm2/s]  (Fuller output is already in "
        "cm2/s)\n"
        "    IFT:             [mN/m]   (literature data as-is)\n"
        "    Solubility:      [-]      (mole fraction, dimensionless)")
    y -= 8.0 * LINE_H

    hline(ax, y)
    y -= LINE_H

    put(ax, MARGIN_L, y,
        "8.  Summary of Data Sources", FONT_SEC)
    y -= 1.4 * LINE_H

    put(ax, MARGIN_L, y,
        "  Property                  Source                     "
        "         Rigour\n"
        "  " + "-" * 75 + "\n"
        "  Density                   CoolProp (Helmholtz EOS)   "
        "         Reference-quality\n"
        "  Isothermal compressibility  Finite-diff. of CoolProp density "
        "   Reference-quality\n"
        "  Dynamic viscosity         CoolProp (transport corr.) "
        "         Reference-quality\n"
        "  Gas-water IFT             Tabulated literature data  "
        "         Experimental\n"
        "  Solubility                Henry-law approximation    "
        "         Screening only\n"
        "  Diffusion coefficient     Fuller gas-phase corr.     "
        "         Screening only")
    y -= 8.5 * LINE_H

    hline(ax, y)
    y -= LINE_H

    put(ax, MARGIN_L, y,
        "9.  Error Handling", FONT_SEC)
    y -= 1.4 * LINE_H

    put(ax, MARGIN_L, y,
        "All CoolProp queries are wrapped in a safe_coolprop() helper that "
        "catches any exception\n"
        "(e.g. two-phase input, out-of-range state) and returns NaN.  "
        "NaN values produce gaps\n"
        "in the plotted curves rather than crashes.  This is particularly "
        "relevant for CO2 near its\n"
        "critical point (Tc = 304.13 K, Pc = 73.77 bar) and along the "
        "saturation curve at 298.15 K.")
    y -= 5.0 * LINE_H

    hline(ax, y)
    y -= LINE_H

    put(ax, MARGIN_L, y,
        "10.  References", FONT_SEC)
    y -= 1.4 * LINE_H

    refs = (
        "  [1] Bell, I.H. et al. (2014). \"Pure and pseudo-pure fluid "
        "thermophysical property\n"
        "       evaluation and the open-source thermophysical property "
        "library CoolProp.\"\n"
        "       Ind. Eng. Chem. Res. 53(6), 2498-2508.\n\n"
        "  [2] Fuller, E.N., Schettler, P.D., Giddings, J.C. (1966). "
        "\"A new method for\n"
        "       prediction of binary gas-phase diffusion coefficients.\" "
        "Ind. Eng. Chem. 58(5), 18-27.\n\n"
        "  [3] Sander, R. (2015). \"Compilation of Henry's law constants "
        "for water as solvent.\"\n"
        "       Atmos. Chem. Phys. 15, 4399-4981.\n\n"
        "  [4] Span, R. & Wagner, W. (1996). \"A new equation of state for "
        "CO2.\"\n"
        "       J. Phys. Chem. Ref. Data 25(6), 1509-1596.\n\n"
        "  [5] Leachman, J.W. et al. (2009). \"Fundamental equations of "
        "state for parahydrogen,\n"
        "       normal hydrogen, and orthohydrogen.\" "
        "J. Phys. Chem. Ref. Data 38(3), 721-748."
    )
    put(ax, MARGIN_L, y, refs, {**FONT_BODY, "fontsize": 9.5})

    put(ax, 0.50, BOT,
        "Page 4 of 4", FONT_FOOT, ha="center")
    pdf.savefig(fig)
    plt.close(fig)

print(f"Saved: {OUTFILE}")
