import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.ndimage import gaussian_filter, distance_transform_edt
from sklearn.metrics import r2_score, mean_squared_error

fontsize = 18


def nearest_outside_fill(Z, mask):
    """Fill ~mask with nearest value from mask==True."""
    outside = ~mask
    dist, (iy, ix) = distance_transform_edt(outside, return_indices=True)
    Zfilled = Z.copy()
    Zfilled[outside] = Z[iy[outside], ix[outside]]
    return Zfilled


def boundary_safe_gaussian(Z, mask, sigma, mode="nearest"):
    """Gaussian smooth inside mask, while avoiding boundary artifacts."""
    Zfilled = nearest_outside_fill(Z, mask)
    Zsmooth = gaussian_filter(Zfilled, sigma=sigma, mode=mode)
    Zsmooth[~mask] = np.nan
    return Zsmooth


def load_results_table(base_input_dir: str, filename: str) -> pd.DataFrame:
    file_path = os.path.join(base_input_dir, filename)
    return pd.read_excel(file_path)


def extract_arrays(df: pd.DataFrame):
    """
    Extract RF, Pe, Ng, theta, Fo, porosity arrays for RF_final > 0.
    Keeps behavior consistent with the original script.
    """
    # Select and convert numeric columns
    columns = [
        "RF_final",
        "Pe",
        "Ng",
        "Fo",
        "theta",
        "CycleLength",
        "FlowRate",
        "Permeability",
        "porosity",
        "Pressure",
        "Temperature",
        "delta_rho",
        "CushionGas",
        "max_pressure",
    ]
    df[columns[1:]] = df[columns[1:]].apply(pd.to_numeric, errors="coerce")

    RF_values = []
    Pe_values = []
    Ng_values = []
    theta_values = []
    Fo_values = []
    phi_values = []

    for ii in range(len(df)):
        if df["RF_final"].iloc[ii] > 0:
            RF_values.append(df["RF_final"].iloc[ii])
            Pe_values.append(df["Pe"].iloc[ii])
            Ng_values.append(df["Ng"].iloc[ii])
            theta_values.append(df["theta"].iloc[ii])
            Fo_values.append(df["Fo"].iloc[ii])
            phi_values.append(df["porosity"].iloc[ii])

    return (
        np.array(RF_values),
        np.array(Pe_values),
        np.array(Ng_values),
        np.array(theta_values),
        np.array(Fo_values),
        np.array(phi_values),
    )


def main():
    base_input_dir = r"Y:\Mixing Results\July"
    excel_name = "mixing_results_plot.xlsx"

    df = load_results_table(base_input_dir, excel_name)

    (
        RF_values,
        Pe_values,
        Ng_values,
        theta_values,
        Fo_values,
        phi_values,
    ) = extract_arrays(df)

    # Keep the original variable names used below
    Pe = Pe_values
    Ng = Ng_values

    ################################################################################  Pe vs Ng


    # Pe = np.log10(Pe_values)
    # Ng = np.log10(Ng_values)
    Pe = Pe_values
    Ng = Ng_values

    x, y, z = Pe, Ng, RF_values
    from scipy.interpolate import griddata
    from scipy.ndimage import gaussian_filter
    from scipy.interpolate import LinearNDInterpolator
    from scipy.spatial import Delaunay
    # Build a regular grid
    xi = np.linspace(min(x), max(x), 250)
    yi = np.linspace(min(y), max(y), 250)
    Xi, Yi = np.meshgrid(xi, yi)
    z = np.clip(RF_values, 0, 1)  # ensure physical range if needed
    tri = Delaunay(np.column_stack([x, y]))
    lin = LinearNDInterpolator(tri, z, fill_value=np.nan)
    Zi = lin(Xi, Yi)
    mask = np.isfinite(Zi)          # True inside (where Zi is defined)
    # smooth with boundary-safe method (it already re-masks outside to NaN)
    Zi_smooth = boundary_safe_gaussian(Zi, mask, sigma=5.0)
    Zi_smooth[~mask] = np.nan
    Zi_smooth2 = Zi.copy()
    # Zi_smooth[~mask] = gaussian_filter(Zi[~mask], sigma=3)


    fig, ax = plt.subplots(1, 3, figsize=(14, 8))
    fig.subplots_adjust(wspace=0.2)

    # 1) Filled contour
    levels = 5
    colors = plt.cm.get_cmap('Greys',levels)
    plot = ax[0].contourf(
        Xi,
        Yi,
        Zi_smooth,
        cmap='plasma',
        # levels=levels,
    )

    # plot = ax[0].scatter(
    #     Pe,
    #     Ng,
    #     c=RF_values,
    #     cmap='plasma',
    #     edgecolor='k'
    # )
    # cbar = plt.colorbar(contour, ax=ax[0], pad = 0.3)
    # cbar.set_label("RF", fontsize=12)
    # ax[0].set_xlabel(r"$\theta \, Pe$ [-]", fontsize=18)
    # ax[0].set_xscale('log')
    # ax[0].set_yscale('log')
    print(min(Pe), max(Pe))
    ax[0].set_xlabel(r"Pe [-]", fontsize=fontsize)
    ax[0].set_ylabel("Ng [-]", fontsize=fontsize)
    ax[0].tick_params(axis='x', labelsize=fontsize)
    ax[0].tick_params(axis='y', labelsize=fontsize)
    # ax[0].legend(loc='best', frameon=True, fontsize=12)
    ax[0].set_xlim([2.5, max(Pe)])
    from matplotlib.ticker import MaxNLocator

    # mask NaNs (outside triangle)
    Zm = np.ma.masked_invalid(Zi_smooth)

    # pick consistent levels (you can change nbins)
    levels = MaxNLocator(nbins=8).tick_values(Zm.min(), Zm.max())

    # filled contours
    cf = ax[0].contourf(Xi, Yi, Zm, levels=levels, cmap='plasma', extend='both')

    # contour lines over the fill
    cs = ax[0].contour(Xi, Yi, Zm, levels=levels, colors='k', linewidths=0.6)
    def RF_Ng_Pe(x,y, M):
        return M[0] * np.power(x, M[1]) + M[2] * np.power(y, M[3])
    Multipliers0 = [0.6896, 0.0815, -0.0535, 0.3235] # For case without porosity Ng/Pe
    y_pred = RF_Ng_Pe(Pe,Ng, Multipliers0)
    r2 = r2_score(RF_values, y_pred)
    rmse = np.sqrt(mean_squared_error(RF_values, y_pred))

    scatter = ax[1].scatter(
        Pe,
        RF_values,
        c=RF_values,
        cmap='plasma',
        edgecolor='k',
        alpha=0.3
    )
    ax[1].set_xlabel(r"Pe [-]", fontsize=fontsize)
    ax[1].set_ylabel("RF [-]", fontsize=fontsize)
    ax[1].tick_params(axis='x', labelsize=fontsize)
    ax[1].tick_params(axis='y', labelsize=fontsize)
    # ax[1].legend(loc='best', frameon=True, fontsize=12)
    scatter = ax[2].scatter(
        Ng,
        RF_values,
        c=RF_values,
        cmap='plasma',
        edgecolor='k',
        alpha=0.3
    )
    # def exp_fun(x, M):
    #     return M[0] * np.exp( M[1] * x) + M[2]

    # Multipliers = [-0.9133, -0.1759, 0.8993]
    # y_pred = exp_fun(Pe, Multipliers)
    # r2_1 = r2_score(RF_values, y_pred)
    # rmse = np.sqrt(mean_squared_error(RF_values, y_pred))
    # xs = np.linspace(Pe.min(), Pe.max(), 500)
    # ax[1].plot(xs, exp_fun(xs, Multipliers), 'k-', lw=2, alpha=0.5)

    def hb_fun(x, M):
        return M[0] + ((0.94-M[0]) * x)/ (M[1] + x)
    Multipliers_hb = [-3.2627, 0.5235]
    y_pred = hb_fun(Pe, Multipliers_hb)
    r2_1 = r2_score(RF_values, y_pred)
    rmse = np.sqrt(mean_squared_error(RF_values, y_pred))
    xs = np.linspace(Pe.min(), Pe.max(), 500)
    ax[1].plot(xs, hb_fun(xs, Multipliers_hb), 'k-', lw=2, alpha=0.5)

    ax[2].set_xlabel("Ng [-]", fontsize=fontsize)
    ax[2].set_ylabel("RF [-]", fontsize=fontsize)
    ax[2].tick_params(axis='x', labelsize=fontsize)
    ax[2].tick_params(axis='y', labelsize=fontsize)
    # ax[2].legend(loc='best', frameon=True, fontsize=12)
    def ln_fun(x, M):
        return M[0] * np.log((M[1] * x) + 1) + M[2]  
    Multipliers2 = [-0.0936,0.3623,0.8687] # For case without porosity Ng/Pe in NG equation
    y_pred = ln_fun(Ng, Multipliers2)
    r2_2 = r2_score(RF_values, y_pred)
    rmse = np.sqrt(mean_squared_error(RF_values, y_pred))
    xs = np.linspace(Ng.min()+1e-6, Ng.max(), 500)
    ax[2].plot(xs, ln_fun(xs, Multipliers2), 'k-', lw=2, alpha=0.5)
    # cbar = plt.colorbar(plot, ax=ax[2])
    # cbar.ax.tick_params(labelsize=fontsize)
    # cbar.set_label("RF[-]", fontsize=fontsize)
    # plt.tight_layout()
    eq_txt1 = f"$RF = {Multipliers0[0]:.2f}\cdot Pe^{{{Multipliers0[1]:.2f}}} {Multipliers0[2]:.2f}\cdot Ng^{{{Multipliers0[3]:.2f}}}$\n$R^2$ = {r2:.2f}"
    ax[0].text(0.25, 0.98, eq_txt1,
               transform=ax[0].transAxes,
               ha='left', va='top', fontsize=18,
               bbox=dict(fc='white', alpha=0.8, boxstyle='round,pad=0.2'))
    # eq_txt2 = f"$RF = {Multipliers[0]:.2f} \cdot exp({Multipliers[1]:.2f} \cdot Pe) + {Multipliers[2]:.2f}$\n$R^2$ = {r2_1:.2f}"
    eq_txt2 = f"$RF = {Multipliers_hb[0]:.2f} + \\frac{{(RF_{{max}}  {Multipliers_hb[0]:.2f}) \cdot Pe}}{{{Multipliers_hb[1]:.2f} + Pe}}$\n$R^2$ = {r2_1:.2f}"
    ax[1].text(1.5, 0.1, eq_txt2,
               transform=ax[0].transAxes,
               ha='left', va='top', fontsize=18,
               bbox=dict(fc='white', alpha=0.8, boxstyle='round,pad=0.2'))
    eq_txt3 = f"$RF = {Multipliers2[0]:.2f} \cdot log({Multipliers2[1]:.2f} \cdot Ng + 1) + {Multipliers2[2]:.2f}$\n$R^2$ = {r2_2:.2f}"
    ax[2].text(2.5, 0.982, eq_txt3,
               transform=ax[0].transAxes,
               ha='left', va='top', fontsize=18,
               bbox=dict(fc='white', alpha=0.8, boxstyle='round,pad=0.2'))
    plt.show()


if __name__ == "__main__":
    main()
