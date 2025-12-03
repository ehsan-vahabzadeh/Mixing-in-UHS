import json
import matplotlib.pyplot as plt
import numpy as np
import os
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import warnings
from pyDGSA.dgsa import dgsa
from pyDGSA.dgsa import dgsa_interactions
from scipy.spatial.distance import pdist, squareform
from pyDGSA.cluster import KMedoids
from pyDGSA.plot import vert_pareto_plot
from sklearn.metrics import silhouette_score, davies_bouldin_score
import pandas as pd
from scipy.interpolate import interp1d
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
    for ii in range(len(X)):
        Y[ii] = (Y[ii] - np.min(Y)) / (np.max(Y) - np.min(Y))  # Normalize RF values
        for jj in range(len(X[ii])):
            X[ii,jj] = (X[ii,jj] - np.min(X[:,jj])) / (np.max(X[:,jj]) - np.min(X[:,jj]))
    # LSA(inputs, RF)
    # parameters = np.array([[input['FlowRate'], input['CycleLength'], input['Permeability'],
    #                         input['Pressure'], input['Density'], input['Porosity'], input['Temperature']] for input in X])
    parameters = X
    responses = Y[:].reshape(-1, 1)  # Convert to 2D array with one column
    # evaluate_clustering(RF[:,-1], min_k=2, max_k=8)
    distances = pdist(responses, metric="euclidean")
    distances = squareform(distances)
    n_clusters = 3
    clusterer = KMedoids(n_clusters=n_clusters, max_iter=3000, tol=1e-4)
    cluster_names = ['Low RF', 'Medium RF', 'High RF']
    cluster_colors = cm.viridis(np.linspace(0, 1, n_clusters))
    labels, medoids = clusterer.fit_predict(distances)
    # for i in range(n_clusters):
    #     sc = ax.scatter(x[labels == i], y[labels == i],
    #                 c=cluster_colors[i], label=cluster_names[i])
    parameter_names = ["Flow Rate", "Cycle Length", "Permeability", "Pressure", "Density", "Porosity", "Temperature"]
    mean_sensitivity = dgsa(
        parameters, labels, parameter_names=parameter_names, quantile=0.99, n_boots=5000, confidence=True
    )
    mean_sensitivity = mean_sensitivity.sort_values(by='sensitivity', ascending=True)
    print(mean_sensitivity.index)
    # print(mean_sensitivity['sensitivity']['FlowRate'],mean_sensitivity['confidence'])
    print(mean_sensitivity)
    # mean_interact_sensitivity = dgsa_interactions(parameters, labels, parameter_names=parameter_names)
    # print(mean_interact_sensitivity)
    # fig, ax = plt.subplots(figsize=(12, 7))

    # y_pos = np.arange(len(parameter_names))

    # bars = ax.barh(
    #     mean_sensitivity.index,
    #     mean_sensitivity['sensitivity'].values,
    #     color=['blue','blue','red','red','red','red','red'],
    #     edgecolor='black',
    #     height=0.55,
    #     xerr = mean_sensitivity['confidence'].values,
    # )
    # ax.set_xlabel('Mean Sensitivity', fontsize=16)
    # ax.tick_params(axis='x', labelsize=16)
    # ax.tick_params(axis='y', labelsize=16)
    # plt.show()
    # from pyDGSA.plot import plot_cdf
    # fig, ax = plot_cdf(parameters, labels, 'Porosity', parameter_names=parameter_names, 
    #                cluster_names=cluster_names)
    # plt.show()
    fig, ax = vert_pareto_plot(mean_sensitivity, confidence=True)
    plt.show()
    # fig, ax = vert_pareto_plot(mean_interact_sensitivity, np_plot="+10")
    # plt.show()
# Example usage
os.chdir("Y:\\Mixing Results\\July")  # Change to the directory containing your simulation files
input_directory = os.getcwd()


main(input_directory)
