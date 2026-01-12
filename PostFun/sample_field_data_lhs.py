import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pyDOE2 import lhs
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression


def main() -> None:
    # Reproducibility
    np.random.seed(4585032)

    # Plot style
    font = {"family": "sans-serif", "size": 18}
    plt.rc("font", **font)

    # Paths
    csv_path = r"Y:\Mixing Results\Field Data\consolidated_output - Final.csv"
    output_path = r"Y:\Mixing Results\Field Data\sampled_doe_hybrid.csv"

    # Columns
    columns_needed = [
        "Permeability [mD]",
        "Reservoir Pressure[MPa]",
        "Reservoir Temp [C]",
        "Porosity [-]",
    ]

    # KMeans settings
    n_clusters = 3
    kmeans_random_state = 42
    cluster_colors = ["red", "green", "blue"]

    # LHS settings
    flow_min, flow_max = 1e5, 1.5e6
    cycle_min, cycle_max = 180, 360
    samples_per_cluster = 150

    # === 1. Load Data ===
    df = pd.read_csv(csv_path, encoding="cp1252")

    # === 2. Select and Convert Required Columns ===
    df[columns_needed] = df[columns_needed].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=columns_needed).reset_index(drop=True)

    # === 3. KMeans Clustering ===
    X = df[columns_needed].values
    kmeans = KMeans(n_clusters=n_clusters, random_state=kmeans_random_state)
    df["Cluster"] = kmeans.fit_predict(X)

    # Plot KMeans clusters (Perm vs Pressure)
    for cluster in range(n_clusters):
        cluster_data = df[df["Cluster"] == cluster]
        plt.scatter(
            cluster_data[columns_needed[0]],
            cluster_data[columns_needed[1]],
            color=cluster_colors[cluster],
            label=f"Cluster {cluster}",
            alpha=0.7,
            edgecolor="k",
        )

    plt.xlabel(columns_needed[0])
    plt.ylabel(columns_needed[1])
    plt.title("KMeans Clustering")
    plt.legend(["K < 200", "200 < K < 1000", "1000 < K"])
    plt.grid(True)
    plt.show()

    # === 4. LHS Sampling for Flow Rate and Cycle Length ===
    sampled_data = []

    for cluster_id in range(n_clusters):
        cluster_data = df[df["Cluster"] == cluster_id]
        if cluster_data.empty:
            continue

        # LHS for rock properties (perm, pressure, porosity)
        lhs_samples = lhs(3, samples=samples_per_cluster)

        perm_min = cluster_data["Permeability [mD]"].min()
        perm_max = cluster_data["Permeability [mD]"].max()
        if cluster_id == 2:
            perm_max = 1000

        pressure_min = cluster_data["Reservoir Pressure[MPa]"].min()
        pressure_max = cluster_data["Reservoir Pressure[MPa]"].max()

        porosity_min = cluster_data["Porosity [-]"].min()
        porosity_max = cluster_data["Porosity [-]"].max()

        perm_samples = lhs_samples[:, 0] * (perm_max - perm_min) + perm_min
        pressure_samples = lhs_samples[:, 1] * (pressure_max - pressure_min) + pressure_min
        porosity_samples = lhs_samples[:, 2] * (porosity_max - porosity_min) + porosity_min

        # Temp ~ f(pressure) + noise
        pressure_real = cluster_data["Reservoir Pressure[MPa]"].values.reshape(-1, 1)
        temp_real = cluster_data["Reservoir Temp [C]"].values
        reg = LinearRegression().fit(pressure_real, temp_real)

        temp_pred = reg.predict(pressure_samples.reshape(-1, 1))
        residual_std = np.std(temp_real - reg.predict(pressure_real))
        temp_samples = temp_pred + np.random.normal(0, residual_std, size=temp_pred.shape)

        perm_pressure_samples = pd.DataFrame(
            {
                "Permeability [mD]": perm_samples,
                "Reservoir Pressure[MPa]": pressure_samples,
                "Reservoir Temp [C]": temp_samples,
                "Porosity [-]": porosity_samples,
            }
        )

        # LHS sampling for operational parameters (flow, cycle); CG set to 0 (as in original code)
        lhs_samples = lhs(2, samples=samples_per_cluster)
        flow_rates = lhs_samples[:, 0] * (flow_max - flow_min) + flow_min
        cycle_lengths = np.round(lhs_samples[:, 1] * (cycle_max - cycle_min) + cycle_min)
        CG_values = lhs_samples[:, 1] * 0

        perm_pressure_samples["Flow Rate [m³/d]"] = flow_rates
        perm_pressure_samples["Cycle Length [days]"] = cycle_lengths
        perm_pressure_samples["CG"] = CG_values
        perm_pressure_samples["Cluster"] = cluster_id

        sampled_data.append(perm_pressure_samples)

    # === 5. Combine All and Save ===
    final_samples = pd.concat(sampled_data, ignore_index=True)
    final_samples.to_csv(output_path, index=False)

    # === 6. Plots for Samples ===
    plt.figure(figsize=(16, 12))

    # Plot 1: Flow rate vs Permeability
    plt.subplot(3, 3, 1)
    plt.scatter(
        final_samples["Permeability [mD]"],
        final_samples["Flow Rate [m³/d]"],
        c=final_samples["Cluster"],
        cmap="Set1",
        edgecolor="k",
        alpha=0.7,
    )
    plt.xlabel("Permeability [mD]", fontsize=18)
    plt.ylabel("Flow Rate [m³/d]", fontsize=18)
    plt.grid(True)

    # Plot 2: Flow rate vs Pressure
    plt.subplot(3, 3, 2)
    plt.scatter(
        final_samples["Reservoir Pressure[MPa]"],
        final_samples["Flow Rate [m³/d]"],
        c=final_samples["Cluster"],
        cmap="Set1",
        edgecolor="k",
        alpha=0.7,
    )
    plt.xlabel("Reservoir Pressure [MPa]", fontsize=18)
    plt.ylabel("Flow Rate [m³/d]", fontsize=18)
    plt.grid(True)

    # Plot 3: Cycle length vs Permeability
    plt.subplot(3, 3, 3)
    plt.scatter(
        final_samples["Permeability [mD]"],
        final_samples["Cycle Length [days]"],
        c=final_samples["Cluster"],
        cmap="Set1",
        edgecolor="k",
        alpha=0.7,
    )
    plt.xlabel("Permeability [mD]", fontsize=18)
    plt.ylabel("Cycle Length [days]", fontsize=18)
    plt.grid(True)

    # Plot 4: Cycle length vs Pressure
    plt.subplot(3, 3, 4)
    plt.scatter(
        final_samples["Reservoir Pressure[MPa]"],
        final_samples["Cycle Length [days]"],
        c=final_samples["Cluster"],
        cmap="Set1",
        edgecolor="k",
        alpha=0.7,
    )
    plt.xlabel("Reservoir Pressure [MPa]", fontsize=18)
    plt.ylabel("Cycle Length [days]", fontsize=18)
    plt.grid(True)

    plt.subplot(3, 3, 5)
    plt.scatter(
        final_samples["Reservoir Temp [C]"],
        final_samples["Cycle Length [days]"],
        c=final_samples["Cluster"],
        cmap="Set1",
        edgecolor="k",
        alpha=0.7,
    )
    plt.xlabel("Reservoir Temp [C]", fontsize=18)
    plt.ylabel("Cycle Length [days]", fontsize=18)
    plt.grid(True)

    plt.subplot(3, 3, 6)
    plt.scatter(
        final_samples["Reservoir Temp [C]"],
        final_samples["Flow Rate [m³/d]"],
        c=final_samples["Cluster"],
        cmap="Set1",
        edgecolor="k",
        alpha=0.7,
    )
    plt.xlabel("Reservoir Temp [C]", fontsize=18)
    plt.ylabel("Flow Rate [m³/d]", fontsize=18)
    plt.grid(True)

    plt.subplot(3, 3, 7)
    plt.scatter(
        final_samples["Porosity [-]"],
        final_samples["Cycle Length [days]"],
        c=final_samples["Cluster"],
        cmap="Set1",
        edgecolor="k",
        alpha=0.7,
    )
    plt.xlabel("Porosity [-]", fontsize=18)
    plt.ylabel("Cycle Length [days]", fontsize=18)
    plt.grid(True)

    plt.subplot(3, 3, 8)
    plt.scatter(
        final_samples["CG"],
        final_samples["Cycle Length [days]"],
        c=final_samples["Cluster"],
        cmap="Set1",
        edgecolor="k",
        alpha=0.7,
    )
    plt.xlabel("CG", fontsize=18)
    plt.ylabel("Cycle Length [days]", fontsize=18)
    plt.grid(True)

    plt.subplot(3, 3, 9)
    plt.scatter(
        final_samples["CG"],
        final_samples["Flow Rate [m³/d]"],
        c=final_samples["Cluster"],
        cmap="Set1",
        edgecolor="k",
        alpha=0.7,
    )
    plt.xlabel("CG", fontsize=18)
    plt.ylabel("Flow Rate [m³/d]", fontsize=18)
    plt.grid(True)

    plt.tight_layout()
    plt.show()

    # === Plot original Perm vs Pressure again ===
    plt.figure(figsize=(8, 6))
    plt.scatter(
        df["Permeability [mD]"],
        df["Reservoir Pressure[MPa]"] * 10,
        color="black",
        alpha=1,
        s=80,
        label="Field Data",
    )
    plt.scatter(
        final_samples["Permeability [mD]"],
        final_samples["Reservoir Pressure[MPa]"] * 10,
        color="white",
        edgecolor="black",
        s=80,
        label="Sampled",
    )
    plt.xlabel("Permeability [mD]", fontsize=18)
    plt.ylabel("Reservoir Pressure [bar]", fontsize=18)
    plt.legend(fontsize=14)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # === Plot original porosity vs Temp  ===
    plt.figure(figsize=(8, 6))
    plt.scatter(
        df["Porosity [-]"],
        df["Reservoir Temp [C]"] + 273.15,
        color="black",
        alpha=1,
        s=80,
        label="Field Data",
    )
    plt.scatter(
        final_samples["Porosity [-]"],
        final_samples["Reservoir Temp [C]"] + 273.15,
        color="white",
        edgecolor="black",
        s=80,
        label="Sampled",
    )
    plt.xlabel("Porosity [-]", fontsize=18)
    plt.ylabel("Reservoir Temp [C]", fontsize=18)
    plt.legend(fontsize=14)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # === Plot original porosity vs Pressure  ===
    plt.figure(figsize=(8, 6))
    plt.scatter(
        df["Porosity [-]"],
        df["Reservoir Pressure[MPa]"],
        color="black",
        alpha=1,
        s=80,
        label="Field Data",
    )
    plt.scatter(
        final_samples["Porosity [-]"],
        final_samples["Reservoir Pressure[MPa]"],
        color="white",
        edgecolor="black",
        s=80,
        label="Sampled",
    )
    plt.xlabel("Porosity [-]", fontsize=18)
    plt.ylabel("Reservoir Pressure [MPa]", fontsize=18)
    plt.legend(fontsize=14)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # === Plot original porosity vs Permeability  ===
    plt.figure(figsize=(8, 6))
    plt.scatter(
        df["Porosity [-]"],
        df["Permeability [mD]"],
        color="black",
        alpha=0.7,
        s=80,
        label="Field Data",
    )
    plt.scatter(
        final_samples["Porosity [-]"],
        final_samples["Permeability [mD]"],
        color="white",
        edgecolor="black",
        s=80,
        alpha=0.7,
        label="Sampled Data",
    )
    plt.xlabel("Porosity [-]", fontsize=18)
    plt.ylabel("Permeability [mD]", fontsize=18)
    plt.tight_layout()
    plt.show()

    # === Plot Temp vs Pressure  ===
    plt.figure(figsize=(8, 6))
    plt.scatter(
        df["Reservoir Temp [C]"] + 273.15,
        df["Reservoir Pressure[MPa]"] * 10,
        color="black",
        alpha=0.7,
        s=80,
        label="Field Data",
    )
    plt.scatter(
        final_samples["Reservoir Temp [C]"] + 273.15,
        final_samples["Reservoir Pressure[MPa]"] * 10,
        color="white",
        edgecolor="black",
        s=80,
        alpha=0.7,
        label="Sampled Data",
    )
    plt.xlabel("Reservoir Temperature [K]", fontsize=18)
    plt.ylabel("Reservoir Pressure [bar]", fontsize=18)
    plt.legend(fontsize=14, edgecolor="black")
    plt.tight_layout()
    plt.show()

    # === Plot Temp vs Permeability  ===
    plt.figure(figsize=(8, 6))
    plt.scatter(
        df["Reservoir Temp [C]"],
        df["Permeability [mD]"],
        color="black",
        alpha=1,
        s=80,
        label="Field Data",
    )
    plt.scatter(
        final_samples["Reservoir Temp [C]"],
        final_samples["Permeability [mD]"],
        color="white",
        edgecolor="black",
        s=80,
        label="Sampled",
    )
    plt.xlabel("Reservoir Temp [C]", fontsize=18)
    plt.ylabel("Permeability [mD]", fontsize=18)
    plt.legend(fontsize=14)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # === 7. Optional permeability binning plot (separate view) ===
    bins = [-np.inf, 10, 100, np.inf]
    labels = ["<10 mD", "10–100 mD", ">100 mD"]

    df["Cluster"] = pd.cut(df["Permeability [mD]"], bins=bins, labels=labels, right=False)

    print(df["Permeability [mD]"].describe())
    print(df["Cluster"].value_counts(dropna=False))

    colors = ["red", "green", "blue"]
    for label, color in zip(labels, colors):
        m = df["Cluster"] == label
        plt.scatter(
            df.loc[m, "Permeability [mD]"],
            df.loc[m, "Reservoir Pressure[MPa]"],
            color=color,
            label=label,
            alpha=0.5,
            edgecolor="k",
        )
    plt.xlabel("Permeability [mD]")
    plt.ylabel("Reservoir Pressure [MPa]")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    main()
