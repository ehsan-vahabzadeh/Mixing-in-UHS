import json
import matplotlib.pyplot as plt
import numpy as np
import os
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from matplotlib.ticker import MaxNLocator
import warnings
from pyDGSA.dgsa import dgsa
from pyDGSA.dgsa import dgsa_interactions
from scipy.spatial.distance import pdist, squareform
from pyDGSA.cluster import KMedoids
# from sklearn_extra.cluster import KMedoids
from pyDGSA.plot import vert_pareto_plot
from sklearn.metrics import silhouette_score, davies_bouldin_score
import pandas as pd
from scipy.interpolate import interp1d
import random

np.random.seed(42)
# import gurobipy as gp
# from gurobipy import GRB

import numpy as np
import matplotlib.pyplot as plt

def LSA(inputs, RF):
    RF_one = RF[:, -1]

    # Step 1: Get low, median, high indices
    low_idx = np.argmin(RF_one)
    high_idx = np.argmax(RF_one)
    median_idx = np.argsort(RF_one)[len(RF_one)//2]

    reference_indices = {
        # "Low RF": low_idx,
        # "Median RF": median_idx,
        "High RF": high_idx
    }

    param_labels = ["FlowRate", "CycleLength", "Permeability", "Pressure", "Temperature", "Density"]
    all_sensitivities = {name: [] for name in param_labels}

    case_sensitivities = {}

    for label, idx in reference_indices.items():
        x0 = np.array([inputs[idx][p] for p in param_labels])
        rf0 = RF_one[idx]

        sens = []
        for i, p in enumerate(param_labels):
            local_sens = []
            for idx_in, row in enumerate(inputs):
                delta_x = (row[p] - x0[i]) / x0[i] if x0[i] != 0 else 0
                delta_RF = (RF_one[idx_in] - rf0) / rf0 if rf0 != 0 else 0
                if delta_x != 0:
                    norm_sens = delta_RF / delta_x
                    local_sens.append(norm_sens)
            if local_sens:
                avg = np.mean(local_sens)
                all_sensitivities[p].append(avg)
                sens.append(avg)
            else:
                all_sensitivities[p].append(np.nan)
                sens.append(np.nan)
        case_sensitivities[label] = sens

    # === Plotting ===
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(param_labels))
    width = 0.25

    for i, (label, sens_values) in enumerate(case_sensitivities.items()):
        ax.bar(x + i*width, sens_values, width, label=label)

    # Compute and plot average across all reference cases
    avg_vals = [np.nanmean(all_sensitivities[p]) for p in param_labels]
    ax.plot(x + width, avg_vals, color='black', marker='o', linestyle='--', label='Average Sensitivity')

    ax.set_xticks(x + width)
    ax.set_xticklabels(param_labels)
    ax.set_ylabel("Normalized Local Sensitivity")
    ax.set_title("Local Sensitivity at Different RF Reference Points")
    ax.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


# Main function to load data, calculate RF, and plot the results
def main(input_directory):
    file_path = os.path.join(input_directory, 'mixing_results_plot.xlsx')
    # file_path = os.path.join(input_directory, 'mixing_results_withoutCG.xlsx')
    df = pd.read_excel(file_path)
    ordered_data = []
    rf_values = []
    inputs = []
    labels = []
    for i in range(len(df)):
        row = []
        for label in df:
            row.append(df[label].iloc[i])
            
        ordered_data.append(row)
    for data in ordered_data:
        if data[11] == 0:
            continue
        rf_values.append(data[11])
        inputs.append({
            "label": data[0],
            "FlowRate": data[1],
            "CycleLength":data[2],
            "Permeability": data[3],
            "Pressure": data[5],
            "Density": data[14],
            "Temperature": data[6],
            "Porosity": data[4],
        })
        # inputs.append(params['FlowRate',1])
        # inputs.append(params['CycleLength',2])
        # inputs.append(params['Permeability',3])
        # inputs.append(params['Pressure',4])
        labels.append(data[0])  # Use the cushion gas type as the label
    df = pd.DataFrame(inputs, columns=[
    "label",    # first
    "FlowRate",      # second
    "CycleLength",
    "Permeability",
    "Pressure",
    "Density",
    "Temperature",
    "Porosity"
    ])
    # print(df.head())    # verify ordering and contents
    X = df[["FlowRate", "CycleLength", "Permeability", "Pressure", "Density", "Temperature", "Porosity"]].values
    Y = np.array(rf_values)
    # for ii in range(len(X)):
    #     Y[ii] = (Y[ii] - np.min(Y)) / (np.max(Y) - np.min(Y))  # Normalize RF values
    #     for jj in range(len(X[ii])):
    #         X[ii,jj] = (X[ii,jj] - np.min(X[:,jj])) / (np.max(X[:,jj]) - np.min(X[:,jj]))
    # LSA(inputs, RF)
    # parameters = np.array([[input['FlowRate'], input['CycleLength'], input['Permeability'],
    #                         input['Pressure'], input['Density'], input['Porosity'], input['Temperature']] for input in X])
    parameters = X
    responses = Y[:].reshape(-1, 1)  # Convert to 2D array with one column
    # evaluate_clustering(RF[:,-1], min_k=2, max_k=8)
    distances = pdist(responses, metric="euclidean")
    distances = squareform(distances)
    n_clusters = 3
    clusterer = KMedoids(n_clusters=n_clusters, max_iter=3000)
    cluster_names = ['RF < 0.5', 'RF > 0.75', '0.5 < RF < 0.75', 'RF']
    cluster_colors = ['#fcc44b', '#9b3004', '#f16c09', 'black']
    labels, medoids = clusterer.fit_predict(distances)
    # AA = silhouette_score(responses, clusterer.fit_predict(responses))
    # print("Silhouette score:", AA)
    fig, ax = plt.subplots(figsize=(8, 5), facecolor='white')
    for i in range(n_clusters):
        sc = ax.scatter(Y[labels == i], Y[labels == i],
                    c=cluster_colors[i], label=cluster_names[i])
    plt.show()
    # fig, ax = plt.subplots(figsize=(8, 5), facecolor='white')
    # perm_vec = X[:,2]  # Permeability
    # for i in range(n_clusters):
    #     sc = ax.scatter(Y[labels == i], perm_vec[labels == i],
    #                 c=cluster_colors[i], label=cluster_names[i])
    # plt.show()

    parameter_names = ["Flow Rate", "Cycle Length", "Permeability", "Pressure", r"$\Delta \rho$", "Porosity", "Temperature"]
    mean_sensitivity = dgsa(
        parameters, labels, parameter_names=parameter_names, quantile=0.95, n_boots=3000, confidence=True
    )
    mean_sensitivity = mean_sensitivity.sort_values(by='sensitivity', ascending=True)
    print(mean_sensitivity.index)
    # print(mean_sensitivity['sensitivity']['FlowRate'],mean_sensitivity['confidence'])
    print(mean_sensitivity)
    # mean_interact_sensitivity = dgsa_interactions(parameters, labels, parameter_names=parameter_names)
    # print(mean_interact_sensitivity)
    fig, ax = plt.subplots(figsize=(7, 7))

    y_pos = np.arange(len(parameter_names))

    bars = ax.barh(
        mean_sensitivity.index,
        mean_sensitivity['sensitivity'].values,
        # color=['blue','blue','red','red','red','red','red'],
        color ='#7a0b01',
        edgecolor='black',
        height=0.55,
        xerr = mean_sensitivity['confidence'].values / mean_sensitivity['sensitivity'].values,
        alpha=0.7
    )
    ax.set_xlabel('Standardised Sensitivity', fontsize=16)
    ax.tick_params(axis='x', labelsize=16)
    ax.tick_params(axis='y', labelsize=16)
    plt.savefig('sens_plot.jpg', dpi=300) 
    plt.show()
    from pyDGSA.plot import plot_cdf
    percentiles = np.arange(1, 100)
    plt.rcParams.update({
    "font.size": 16,
    "axes.linewidth": 1.3,
    "xtick.major.width": 1.0,
    "ytick.major.width": 1.0
    })

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.ravel()   # flatten to 1D for easy indexing
    param_indices = [2,3,4,1]
    param_name = ["Permeability [md]", "Pressure [bar]", r"$\Delta \rho$ [kg m$^{-3}$]", "Cycle Length [d]"]
    line_styles = ['dashed', 'dotted', 'dashdot', 'solid']
    # -------------------------------------
    # Build each subplot
    # -------------------------------------
    for idx, ax in enumerate(axes):

        p_index = param_indices[idx]

        for c in range(n_clusters + 1):
            # Compute percentiles for cluster c
           
            if c == n_clusters:
                x = np.percentile(parameters[:, p_index], percentiles)
            else:
                 x = np.percentile(parameters[np.where(labels == c), p_index], percentiles)
            ax.plot(
                x, percentiles/100,
                color=cluster_colors[c],
                linewidth=3.0,
                linestyle=line_styles[c],
                label=f'{cluster_names[c]}'
            )
            if p_index == 2:
                ax.set_xticks([100,500,1000,1500])
            if p_index == 2 or p_index == 4:
                ax.set_ylabel("CDF", fontsize=16)
        # ax.xaxis.set_major_locator(MaxNLocator(nbins=6))
        ax.set_xlabel(param_name[idx], fontsize=16)
        

        # Put legend only in the first subplot to avoid clutter
        if idx == 1:
            # ax.legend(frameon=False, fontsize=16, )
            ax.legend(frameon=False, bbox_to_anchor=(1.05, 1), fontsize=16)
    plt.savefig('CDF_plots.jpg', dpi=300)    
    plt.show()
    
    # fig, ax = vert_pareto_plot(mean_sensitivity, confidence=True)
    # plt.show()
    # fig, ax = vert_pareto_plot(mean_interact_sensitivity, np_plot="+10")
    # plt.show()
# Example usage
os.chdir("Y:\\Mixing Results\\July")  # Change to the directory containing your simulation files
input_directory = os.getcwd()


# main(input_directory)

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# --------------------------------------------
# Extract the TWh groups exactly as ECDF code
# --------------------------------------------
labels =["RF", "RF < 0.5", "0.5 < RF < 0.75", "RF > 0.75"]
# labels = [f"{t} TWh" for t in twh_values]
# labels.insert(0, "Reservoirs")
# SAME COLOR SEQUENCE as ECDF
# colors = ["black","#4d0000", "#660000", "#800000", "#b30000",
#             "#e60000", "#ff704d", "#ff9966"]
cluster_colors = ['black','#fcc44b','#f16c09', '#9b3004']
# Build legend handles (rectangular patches)
handles = [
    Patch(facecolor=c, edgecolor="white", label=l)
    for c, l in zip(cluster_colors[:len(labels)], labels)
]

# --------------------------------------------
# Create legend-only figure
# --------------------------------------------
fig, ax = plt.subplots(figsize=(8, 1))

ax.legend(
    handles=handles,
    loc="center",
    frameon=False,
    ncol=len(handles),
    fontsize=20,
    handlelength=3,
    handleheight=1.5
)

ax.set_axis_off()  # remove axes

plt.tight_layout()

fig.savefig('legend_only_figure.jpg', dpi=400, bbox_inches="tight")

plt.show()
