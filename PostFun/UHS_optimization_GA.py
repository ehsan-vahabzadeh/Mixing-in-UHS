import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import glob
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from CoolProp.CoolProp import PropsSI
import torch
import joblib
import torch.nn as nn
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.termination import get_termination
def get_activation(name):
    if name == "relu":
        return nn.ReLU()
    elif name == "tanh":
        return nn.Tanh()
    elif name == "sigmoid":
        return nn.Sigmoid()
    else:
        raise ValueError(f"Unknown activation function: {name}")  
def build_model(input_dim, hidden_sizes, activations):
    layers = []
    in_dim = input_dim

    for out_dim, act_name in zip(hidden_sizes, activations):
        layers.append(nn.Linear(in_dim, out_dim))
        layers.append(get_activation(act_name))
        # layers.append(nn.Dropout(0.2))  # Add dropout for regularization
        in_dim = out_dim
    layers += [nn.Linear(in_dim, 1)]   # <- bound to (0,1)
    layers.append(nn.Sigmoid())  # Output layer
    return nn.Sequential(*layers)
class SingleObjRFProblem(ElementwiseProblem):
    def __init__(self, objective, lb, ub):
        n_var = len(lb)
        super().__init__(n_var=n_var, n_obj=1, n_constr=0, xl=np.array(lb, dtype=float), xu=np.array(ub, dtype=float))
        self.objective = objective

    def _evaluate(self, x, out, *args, **kwargs):
        # ensure float vector
        x = np.asarray(x, dtype=float)
        # evaluate your loss (= -RF)
        f = self.objective(x)
        # Guard against NaNs/infs
        if not np.isfinite(f):
            f = 1e12
        out["F"] = f
def extract_best_from_pymoo(res):
    # Ensure 2D
    F = np.atleast_2d(res.F)
    X = np.atleast_2d(res.X)

    # Single objective → minimize column 0
    idx = np.argmin(F[:, 0] if F.shape[1] >= 1 else F[:, 0])
    xbest = X[idx]
    fbest = F[idx, 0] if F.ndim == 2 else F[idx]
    return xbest.astype(float), float(fbest)
def ga_with_pymoo(objective, lb, ub, pop_size=80, n_gen=300, seed=42):
    problem = SingleObjRFProblem(objective, lb, ub)

    alg = NSGA2(
        pop_size=pop_size,
        eliminate_duplicates=True
    )

    term = get_termination("n_gen", n_gen)

    res = minimize(problem, alg, termination=term, seed=seed, verbose=False)

    xopt = res.X[0].astype(float)
    xopt, fopt = extract_best_from_pymoo(res)  # <<— instead of float(res.F)
    return xopt, fopt
def build_objective(permeability, porosity, pressure, temperature, delta_rho, model, scalers, clf):
    def objective(x):
        scaler = scalers["X_scaler"]
        y_scaler = scalers["y_scaler"]
        if len(x) == 3:
            flow, cl, cg_ratio = x
            full_input = np.array([[flow, cl, permeability, pressure, delta_rho, porosity, temperature, cg_ratio]])
        else:
            flow, cl = x
            full_input = np.array([[flow, cl, permeability, pressure, delta_rho, porosity, temperature, 0.0]])
        scaled = scaler.transform(full_input)
        input_tensor = torch.tensor(scaled, dtype=torch.float32)
        X = np.array([[flow, cl, permeability, pressure, delta_rho, porosity, temperature]])
        pred = clf.predict(X)
        if pred == 0:
            return 1e12
        with torch.no_grad():
            rf = model(input_tensor).item()
            if rf > 1:
                print("Warning: RF exceeds 1.0, capping to 1.0")
                rf = 1.0  # Cap RF at 1.0
            # rf_original = y_scaler.inverse_transform([[rf]]).ravel()[0]
        return -rf  # because we're maximizing
    return objective

def main(input_directory):
    rf_values = []
    labels = []
    inputs = []
    df_list = []
    file_path = os.path.join(input_directory, 'mixing_results_withCG.xlsx')
    # file_path = os.path.join(input_directory, 'mixing_results_withoutCG.xlsx')
    df = pd.read_excel(file_path)
    
    valid = []
    for i in range(len(df)):
        if df['RF_final'].iloc[i] == 0:
            valid.append(0)
        else:
            valid.append(1)
    # df = df.dropna()  # Drop rows with NaN values
    df = df.rename(columns = {
        'FlowRate': 'Flow Rate',
        'CycleLength': 'Cycle Length',
        'RF_final': 'RF',
        'delta_rho': 'Density',
        })
    df['valid'] = valid
    df = df.drop(columns=['label','CushionGas','theta','CG Ratio','Nusselt_number','Raileigh_number', 'Pe', 'Ng','RF'])
    X = df[["Flow Rate", "Cycle Length", "Permeability", "Pressure", "Density", 'porosity', 'Temperature']].values
    y = df["valid"].values
    clf = DecisionTreeClassifier(max_depth=3, min_samples_leaf=10)
    clf.fit(X, y)

    
    # Path to your consolidated CSV
    csv_path = r"Y:\Mixing Results\Field Data\consolidated_output - Final.csv"

    # Read the CSV file
    df = pd.read_csv(csv_path)

    # Select and convert the necessary columns to numeric
    columns = [
        "Field Name",
        "Porosity [-]",
        "Permeability [mD]",
        "Reservoir Pressure[MPa]",
        "Reservoir Temp [C]",
    ]
    df[columns[1:]] = df[columns[1:]].apply(pd.to_numeric, errors='coerce')
 
    df_clean = df.dropna(subset=columns).reset_index(drop=True)
    df_clean['Reservoir Pressure[MPa]'] = df_clean['Reservoir Pressure[MPa]'] * 10
    df_clean['Reservoir Temp [C]'] = df_clean['Reservoir Temp [C]'] + 273.15  # Convert to Kelvin
    df_clean = df_clean.rename(columns={"Reservoir Pressure[MPa]": "Pressure","Reservoir Temp [C]": "Temperature","Porosity [-]": "Porosity","Permeability [mD]": "Permeability"})
    activation = ["tanh", "sigmoid"]
    model = build_model(input_dim=8, hidden_sizes=[15, 30], activations=activation)
    model.load_state_dict(torch.load("ann_model_withCG.pt"))
    model.eval()
    scalers = joblib.load("scalers_withCG.pkl")
    


    CG_types = ['H2', 'CO2', 'CH4', 'N2']
    results =[]
    for ii in range(len(df_clean)):
        for cg_type in CG_types:
            H2_density = PropsSI("D", "P", df_clean['Pressure'].iloc[ii] * 1e5, "T", df_clean['Temperature'].iloc[ii], "Hydrogen")
            CG_density = PropsSI("D", "P", df_clean['Pressure'].iloc[ii] * 1e5, "T", df_clean['Temperature'].iloc[ii] , cg_type)
            X_const = np.array([df_clean['Permeability'].iloc[ii], df_clean['Porosity'].iloc[ii], df_clean['Pressure'].iloc[ii], df_clean['Temperature'].iloc[ii], CG_density - H2_density])
            if cg_type != 'H2':
                lb = [1e5, 14]  
                ub = [1.5e6, 180]
            else:
                lb = [1e5, 14, 0.0]  
                ub = [1.5e6, 180, 5.0] 
            objective = build_objective(X_const[0], X_const[1], X_const[2], X_const[3], X_const[4], model, scalers,clf)
            xopt, fopt = ga_with_pymoo(objective, lb, ub, pop_size=300, n_gen=300, seed=42)
            results.append({
            "Field Name": df_clean['Field Name'].iloc[ii],
            "Porosity [-]": X_const[1],
            "Permeability [mD]": X_const[0],
            "Reservoir Pressure[bar]": X_const[2],
            "Reservoir Temp [K]": X_const[3],
            "Cushion Gas": cg_type,
            "Density Difference [kg/m3]": CG_density - H2_density,
            "Optimized Flow Rate [sm3/d]": xopt[0],
            "Optimized Cycle Length [d]": xopt[1],
            "Optimized CG Ratio": (xopt[2] if len(xopt) == 3 else 0),
            "Max Predicted RF [-]": -fopt
            })
    df_results = pd.DataFrame(results)
    df_results.to_csv(os.path.join(input_directory, 'optimized_results_no_CG_GA.csv'), index=False)
os.chdir("Y:\\Mixing Results\\July")  # Change to the directory containing your simulation files
# os.chdir("Y:\\Mixing Results\\May\\NewCH4")  # Change to the directory containing your simulation files
# os.chdir("Z:\\Mixing Results\\Feb\\Results\\30 Meter Height Reservoir")  # Change to the directory containing your simulation files
input_directory = os.getcwd()
main(input_directory) 