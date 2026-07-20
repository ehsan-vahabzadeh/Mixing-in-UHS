# isothermal_compressibility_plot.py
# Compute and plot isothermal compressibility vs pressure for CO2, H2, N2, CH4

import numpy as np
import matplotlib.pyplot as plt

# --- Try CoolProp; fall back to Peng–Robinson (PR) ---
USE_COOLPROP = False
try:
    from CoolProp.CoolProp import PropsSI
    USE_COOLPROP = True
except Exception:
    USE_COOLPROP = False

R = 8.31446261815324  # J/(mol*K)

GASES = {
    "CO2": {"M": 44.0095e-3,  "Tc": 304.13,  "Pc": 7.3773e6, "omega": 0.225},
    "H2":  {"M": 2.01588e-3,  "Tc": 33.19,   "Pc": 1.293e6, "omega": -0.216},
    "N2":  {"M": 28.0134e-3,  "Tc": 126.2,   "Pc": 3.3958e6, "omega": 0.0372},
    "CH4": {"M": 16.04246e-3, "Tc": 190.56,  "Pc": 4.599e6, "omega": 0.011},
}

# ---------- Peng–Robinson helpers (fallback) ----------
def pr_Z(P, T, g):
    """Peng–Robinson Z-factor (gas root)."""
    kappa = 0.37464 + 1.54226*g["omega"] - 0.26992*(g["omega"]**2)
    Tr = T / g["Tc"]
    alpha = (1 + kappa*(1 - np.sqrt(Tr)))**2
    a = 0.45724 * (R**2) * (g["Tc"]**2) / g["Pc"]
    b = 0.07780 * R * g["Tc"] / g["Pc"]
    A = a * alpha * P / (R**2 * T**2)
    B = b * P / (R * T)
    # Z^3 + c2 Z^2 + c1 Z + c0 = 0
    c2 = -(1 - B)
    c1 = (A - 3*B*B - 2*B)
    c0 = -(A*B - B*B - B**3)
    roots = np.roots([1.0, c2, c1, c0])
    real_roots = [r.real for r in roots if abs(r.imag) < 1e-8]
    return (max(real_roots) if real_roots else float(roots[np.argmin(np.abs(roots.imag))].real))

def pr_rho(P, T, g):
    Z = pr_Z(P, T, g)
    return P * g["M"] / (Z * R * T), Z

def viscosity(P, T, gas):
    """
    c_f = (1/rho)*(drho/dP)_T. Returns (c_f [1/Pa], rho [kg/m3], Z, method).
    """
    g = GASES[gas]
    if USE_COOLPROP:
        miu  = PropsSI('VISCOSITY', 'P', P,  'T', T, gas)
        return miu
    
    
# ---------- Isothermal compressibility ----------
def isothermal_cf(P, T, gas, dP=1e5):
    """
    c_f = (1/rho)*(drho/dP)_T. Returns (c_f [1/Pa], rho [kg/m3], Z, method).
    """
    g = GASES[gas]
    if USE_COOLPROP:
        rho  = PropsSI('D', 'P', P,  'T', T, gas)
        Pm, Pp = max(P-dP, 100.0), P + dP
        rho_m  = PropsSI('D', 'P', Pm, 'T', T, gas)
        rho_p  = PropsSI('D', 'P', Pp, 'T', T, gas)
        drhodP = (rho_p - rho_m) / (Pp - Pm)
        Z = P * g["M"] / (rho * R * T)
        return (drhodP / rho), rho, Z, "CoolProp"
    else:
        rho, Z = pr_rho(P, T, g)
        Pm, Pp = max(P-dP, 100.0), P + dP
        rho_m, _ = pr_rho(Pm, T, g)
        rho_p, _ = pr_rho(Pp, T, g)
        drhodP = (rho_p - rho_m) / (Pp - Pm)
        return (drhodP / rho), rho, Z, "PR"

# ---------- User settings ----------
temps = [ 303.15]    # K (25°C, 50°C, 75°C, 100°C)
P_bar = np.linspace(20, 450, 250)           # 20 → 300 bar
P_Pa  = P_bar * 1e5
qq = 0

# ---------- Compute & plot ----------
plt.figure(figsize=(10,6))
colors = ["red", "blue", "green", "orange"]
linstyles = ['solid', 'dashed', 'dotted', 'dashdot']
for gas in ["CO2", "H2", "N2", "CH4"]:
    gg = 0
    for T in temps:
        cfs = [isothermal_cf(P, T, gas)[0] for P in P_Pa]  # 1/Pa
        plt.plot(P_bar, np.array(cfs)*1e6,
                 label=f"{gas}, {T-273.15:.0f}°C", color = colors[qq], linestyle = linstyles[gg])
        # convert to °C in legend
        gg += 1
    qq += 1
plt.xlabel("Pressure [bar]", fontsize=18)
plt.ylabel(r"Isothermal compressibility $c_f$ [1/MPa]", fontsize=18)
plt.tick_params(axis= 'both', which='major', labelsize=16)
plt.ylim(0, 0.6)
plt.title(f"Isothermal Compressibility vs Pressure")
plt.legend(fontsize=16)
plt
plt.grid(True)
plt.tight_layout()
plt.show()



# ---------- Compute & plot ----------
plt.figure(figsize=(10,6))
qq = 0
colors = ["red", "blue", "green", "orange"]
linstyles = ['solid', 'dashed', 'dotted', 'dashdot']
for gas in ["CO2", "H2", "N2", "CH4"]:
    gg = 0
    for T in temps:
        cfs = [viscosity(P, T, gas) for P in P_Pa] 
        plt.plot(P_bar, np.array(cfs)* 1000,
                 label=f"{gas}, {T-273.15:.0f}°C", color = colors[qq], linestyle = linstyles[gg])
        # convert to °C in legend
        gg += 1
    qq += 1
plt.xlabel("Pressure [bar]", fontsize=18)
plt.ylabel(r"Viscosity[cP]", fontsize=18)
plt.tick_params(axis= 'both', which='major', labelsize=16)
# plt.ylim(0, 0.6)
plt.title(f"Viscosity vs Pressure")
plt.legend(fontsize=16)
plt
plt.grid(True)
plt.tight_layout()
plt.show()