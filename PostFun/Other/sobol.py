import numpy as np
import pandas as pd
from SALib.sample import saltelli
from SALib.analyze import sobol
import matplotlib.pyplot as plt
import os
def run_sobol_analysis(df_path):
    df = pd.read_excel(df_path)

    param_names = ["FlowRate", "CycleLength", "Permeability", "Pressure", "delta_rho", "Temperature", "porosity"]
    problem = {
        'num_vars': len(param_names),
        'names': param_names,
        'bounds': [[df[p].min(), df[p].max()] for p in param_names]
    }

    param_values = saltelli.sample(problem, 1024, calc_second_order=False)

    # Dummy model for demonstration — replace with your surrogate model
    def evaluate_model(X):
        weights = np.linspace(0.5, 1.5, len(param_names))
        return np.dot(X, weights) / sum(weights)

    Y = evaluate_model(param_values)

    Si = sobol.analyze(problem, Y, calc_second_order=False)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(problem['names'], Si['S1'], yerr=Si['S1_conf'], color='salmon', edgecolor='black')
    ax.set_title("First-order Sobol Sensitivity Indices")
    ax.set_ylabel("Sobol Index")
    ax.grid(True)
    plt.tight_layout()
    plt.show()

    return Si

# Example usage
os.chdir("Y:\\Mixing Results\\July")  # Change to the directory containing your simulation files
input_directory = os.getcwd()
input_directory = os.path.join(input_directory, 'mixing_results_new.xlsx')
run_sobol_analysis(input_directory)
