import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.metrics import r2_score, mean_squared_error
import matplotlib.pyplot as plt
import os
from pysr import PySRRegressor
def main(input_directory):
    
    rf_values = []
    labels = []
    inputs = []
    file_path = os.path.join(input_directory, 'mixing_results_withoutCG.xlsx')
    # file_path = os.path.join(input_directory, 'mixing_results_withCG.xlsx')
    df = pd.read_excel(file_path)
    ordered_data = []
    for i in range(len(df)):
        row = []
        for label in df:
            row.append(df[label].iloc[i])
        ordered_data.append(row)
    for data in ordered_data:
        rf_values.append(data[9])
        inputs.append({
            "label": data[0],
            "FlowRate": data[1],
            "CycleLength":data[2],
            "Permeability": data[3],
            "Pressure": data[5],
            "delta_rho": data[12],
            "porosity": data[4],
            "Temperature": data[6],
            "CG Ratio": data[16],
            "RF_final": data[9]
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
    "delta_rho",
    "porosity",
    "Temperature",
    "CG Ratio",
    "RF_final" 
    ])
    df = df.dropna()  # Drop rows with NaN values
    # print(df.head())    # verify ordering and contents
    Input_label = ["FlowRate", "CycleLength", "Permeability", "Pressure", "delta_rho", 'porosity', 'Temperature','CG Ratio']
    X = df[["FlowRate", "CycleLength", "Permeability", "Pressure", "delta_rho", 'porosity', 'Temperature','CG Ratio']].values
    Y = df["RF_final"].values
    df_lin = [X,Y]

    # keep only finite rows; RF should be in (0,1]
    mask =  np.isfinite(Y)
    mask &= (Y > 0) & (Y <= 1)
    X = X[mask]
    Y = Y[mask]

    # -------- 2) Train / test split (80/20) --------
    X_train, X_test, y_train, y_test = train_test_split(
        X, Y, test_size=0.20, random_state=42
    )

    # -------- 3) Plain Linear Regression (closed-form equation) --------
    lin = LinearRegression()
    lin.fit(X_train, y_train)

    yhat_tr = lin.predict(X_train)
    yhat_te = lin.predict(X_test)

    def rmse(a, b): return float(np.sqrt(np.mean((a - b)**2)))

    print("=== Linear Regression (OLS) ===")
    print("Train: R2 = %.3f | RMSE = %.4f" % (r2_score(y_train, yhat_tr), rmse(y_train, yhat_tr)))
    print("Test : R2 = %.3f | RMSE = %.4f" % (r2_score(y_test, yhat_te), rmse(y_test, yhat_te)))

    # Nicely formatted linear equation in original units
    coefs = lin.coef_
    inter = lin.intercept_
    terms = " + ".join([f"({coefs[i]:+.4e})*{Input_label[i]}" for i in range(len(Input_label))])
    eq_str = f"RF_hat = {inter:+.4e} " + (" + " if terms else "") + terms
    print("\nOLS Equation:")
    print(eq_str)

    # Also show coefficients with names (useful for the paper)
    coef_series = pd.Series(coefs, index=Input_label).sort_values(key=np.abs, ascending=False)
    print("\nCoefficients (largest |β| first):")
    print(coef_series.to_string(float_format=lambda v: f"{v:.3e}"))

    # -------- 4) Optional: RidgeCV (still linear, often better generalization) --------
    alphas = np.logspace(-4, 4, 41)
    ridge = RidgeCV(alphas=alphas, cv=5).fit(X_train, y_train)
    yhat_tr_r = ridge.predict(X_train)
    yhat_te_r = ridge.predict(X_test)

    print("\n=== RidgeCV (linear, L2 regularization) ===")
    print("Chosen alpha:", ridge.alpha_)
    print("Train: R2 = %.3f | RMSE = %.4f" % (r2_score(y_train, yhat_tr_r), rmse(y_train, yhat_tr_r)))
    print("Test : R2 = %.3f | RMSE = %.4f" % (r2_score(y_test, yhat_te_r), rmse(y_test, yhat_te_r)))

    coefs_r = ridge.coef_
    inter_r = ridge.intercept_
    terms_r = " + ".join([f"({coefs_r[i]:+.4e})*{Input_label[i]}" for i in range(len(Input_label))])
    eq_str_r = f"RF_hat = {inter_r:+.4e} " + (" + " if terms_r else "") + terms_r
    print("\nRidge Equation:")
    print(eq_str_r)

    # -------- 5) Quick diagnostic plot (test set) --------
    plt.figure(figsize=(4.2, 4.2), dpi=140)
    plt.scatter(y_test, yhat_te, s=18, alpha=0.6, label="OLS")
    plt.scatter(y_test, yhat_te_r, s=18, alpha=0.6, label="Ridge")
    m = [min(y_test.min(), yhat_te.min(), yhat_te_r.min()),
        max(y_test.max(), yhat_te.max(), yhat_te_r.max())]
    plt.plot(m, m, "k--", lw=1.0, label="y=x")
    plt.xlabel("RF (true)")
    plt.ylabel("RF (predicted)")
    plt.legend(frameon=True)
    plt.tight_layout()
    plt.show() 
    
os.chdir("Y:\\Mixing Results\\July")  # Change to the directory containing your simulation files
# os.chdir("Y:\\Mixing Results\\May\\NewCH4")  # Change to the directory containing your simulation files
# os.chdir("Z:\\Mixing Results\\Feb\\Results\\30 Meter Height Reservoir")  # Change to the directory containing your simulation files
input_directory = os.getcwd()
main(input_directory)