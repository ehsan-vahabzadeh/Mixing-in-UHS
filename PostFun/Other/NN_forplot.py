import json
import matplotlib.pyplot as plt
import numpy as np
import os
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import warnings
import optuna
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import KFold
import joblib
torch.manual_seed(42)
np.random.seed(42)
DOF_LIMIT = 2400
def train_and_evaluate_model_kfold(X, Y, trial=None):
    # === Optuna hyperparameters ===
    if trial:
        X_split, X_test, Y_split, y_test = train_test_split(X, Y, test_size=0.2, random_state=42)
        lr = trial.suggest_float('lr', 1e-5, 3e-3, log=True)
        n_layers = trial.suggest_int("n_layers", 1, 3)  # You can change range
        hidden_sizes = []
        activations = []

        for i in range(n_layers):
            hidden_sizes.append(trial.suggest_int(f"n_units_l{i}", 1, 32))
            activations.append(trial.suggest_categorical(f"activation_l{i}", ["relu", "tanh", "sigmoid"]))
        total_params = count_params(X.shape[1], hidden_sizes)
        trial.set_user_attr("constraint", total_params - DOF_LIMIT)
        if total_params > DOF_LIMIT:
            return float("inf")
        batch_size = 8
        epochs = 200  # Reduce for optimization speed

        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        mse_list = []
        patience = 50
        for train_index, val_index in kf.split(X_split):
            X_train, X_val = X_split[train_index], X_split[val_index]
            y_train, y_val = Y_split[train_index], Y_split[val_index]

            scaler = StandardScaler()
            # scaler = MinMaxScaler()
            X_train = scaler.fit_transform(X_train)
            X_val = scaler.transform(X_val)

            X_train_t = torch.tensor(X_train, dtype=torch.float32)
            y_train_t = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1)
            X_val_t = torch.tensor(X_val, dtype=torch.float32)
            y_val_t = torch.tensor(y_val, dtype=torch.float32).unsqueeze(1)

            train_ds = TensorDataset(X_train_t, y_train_t)
            train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

            model = build_model(X.shape[1], hidden_sizes, activations)
            criterion = nn.MSELoss()
            optimizer = optim.Adam(model.parameters(), lr=lr)
            best_val_loss = float('inf')
            for epoch in range(epochs):
                model.train()
                for xb, yb in train_loader:
                    optimizer.zero_grad()
                    loss = criterion(model(xb), yb)
                    loss.backward()
                    optimizer.step()
                model.eval()
                with torch.no_grad():
                    val_predictions = model(X_val_t)
                    val_loss = criterion(val_predictions, y_val_t).item()
                if val_loss < best_val_loss - 1e-6:  # small threshold to detect real improvement
                    best_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                    if patience_counter >= patience:
                        break  # Stop training early
            model.eval()
            with torch.no_grad():
                preds = model(X_val_t).numpy().flatten()
                truth = y_val_t.numpy().flatten()
                mse = mean_squared_error(truth, preds)
                mse_list.append(mse)

        return np.mean(mse_list)

    else:
        # === Standard training mode ===
        X_split, X_test, Y_split, y_test = train_test_split(X, Y, test_size=0.2, shuffle=True, random_state=42)
        scaler = StandardScaler()
        y_scaler = MinMaxScaler()
        X_train = scaler.fit_transform(X_split)
        X_test = scaler.transform(X_test)
        # y_train = y_scaler.fit_transform(Y_split.reshape(-1, 1))
        # y_test   = y_scaler.transform(y_test.reshape(-1, 1))
        
        X_train_t = torch.tensor(X_train, dtype=torch.float32)
        y_train_t = torch.tensor(Y_split, dtype=torch.float32).unsqueeze(1)
        X_test_t = torch.tensor(X_test, dtype=torch.float32)
        y_test_t = torch.tensor(y_test, dtype=torch.float32).unsqueeze(1)
        # with consideration of CG in RF
        # lr = 0.002999999999999999
        # hidden_sizes = [22, 21]
        # activation = ["sigmoid", "sigmoid"]
        # batch_size = 8
        # epochs = 300

        # without the consideration of CG in RF
        # lr = 0.005134627406023883
        # hidden_sizes = [17, 12, 29]
        # activation = ["sigmoid", "sigmoid", "tanh"]
        # batch_size = 8
        # epochs = 300
        lr = 0.00020469703577854776
        hidden_sizes = [23, 32, 12]
        # activation = ["relu", "tanh"]
        activation = ["relu", "tanh","relu"]
        batch_size = 8
        epochs = 300
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        mse_list = []
        patience = 50
        
        all_train_losses = []
        all_val_losses = []
        for train_index, val_index in kf.split(X_train):
            X_train, X_val = X_split[train_index], X_split[val_index]
            y_train, y_val = Y_split[train_index], Y_split[val_index]

            scaler = StandardScaler()
            y_scaler = MinMaxScaler()
            X_train = scaler.fit_transform(X_train)
            X_val = scaler.transform( X_val)
            # y_train = y_scaler.fit_transform(y_train.reshape(-1, 1))
            # y_val   = y_scaler.transform(y_val.reshape(-1, 1))
            X_train_t = torch.tensor(X_train, dtype=torch.float32)
            y_train_t = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1)
            X_val_t = torch.tensor(X_val, dtype=torch.float32)
            y_val_t = torch.tensor(y_val, dtype=torch.float32).unsqueeze(1)
            train_ds = TensorDataset(X_train_t, y_train_t)
            train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

            model = build_model(X.shape[1], hidden_sizes, activation)
            criterion = nn.MSELoss()
            optimizer = optim.Adam(model.parameters(), lr=lr)
            l1_lambda = 5e-5  # Regularization strength
            train_losses = []
            val_losses = []
            best_val_loss = float('inf')
            for epoch in range(epochs):
                model.train()
                batch_losses = []
                batch_losses1 = []
                for xb, yb in train_loader:
                    optimizer.zero_grad()
                    loss = criterion(model(xb), yb)
                    loss.backward()
                    optimizer.step()
                    batch_losses.append(loss.item())  # Only store MSE (not L1) for plotting

                train_losses.append(np.mean(batch_losses))
                model.eval()
                with torch.no_grad():
                    val_predictions = model(X_val_t)
                    val_loss = criterion(val_predictions, y_val_t).item()
                    val_losses.append(val_loss)
                if val_loss < best_val_loss - 1e-6:  # small threshold to detect real improvement
                    best_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                    if patience_counter >= patience:
                        break  # Stop training early
            model.eval()
            with torch.no_grad():
                preds = model(X_val_t).numpy().flatten()
                truth = y_val_t.numpy().flatten()
                mse = mean_squared_error(truth, preds)
                mse_list.append(mse)    
            all_train_losses.append(train_losses)
            all_val_losses.append(val_losses)    
                
        model.eval()
        # 2. Gather predictions and truths
        with torch.no_grad():
            # Test set
            y_pred_test  = model(X_test_t).cpu().numpy().flatten()
            y_true_test  =   y_test_t.cpu().numpy().flatten()
            # Train set
            y_pred_train = model(X_train_t).cpu().numpy().flatten()
            y_true_train =   y_train_t.cpu().numpy().flatten()

            # y_pred_train = y_scaler.inverse_transform(y_pred_train.reshape(-1, 1)).ravel()
            # y_true_train = y_scaler.inverse_transform(y_true_train.reshape(-1, 1)).ravel()
            # y_pred_test = y_scaler.inverse_transform(y_pred_test.reshape(-1, 1)).ravel()
            # y_true_test = y_scaler.inverse_transform(y_true_test.reshape(-1, 1)).ravel()
            print('y_pred_scaled min/max:', y_pred_test.min(), y_pred_test.max())
            r2_train = r2_score(y_true_train, y_pred_train)
            r2_test = r2_score(y_true_test, y_pred_test)
            mse_train = mean_squared_error(y_true_train, y_pred_train)
            mse_test = mean_squared_error(y_true_test, y_pred_test)
        
            # Plotting
            plt.figure(figsize=(18, 6))
            fontsize = 18
            fontsize_ticks = 16
            # ---- Training subplot ----
            plt.subplot(1, 3, 1)
            sc1 = plt.scatter(y_true_train, y_pred_train, c='royalblue', alpha=0.7, edgecolor='k', s=60)
            lims = [min(y_true_train.min(), y_pred_train.min()), max(y_true_train.max(), y_pred_train.max())]
            plt.plot(lims, lims, 'r--', lw=2)
            plt.xlabel('Actual RF', fontsize=fontsize)
            plt.ylabel('Predicted RF', fontsize=fontsize)
            plt.xticks(fontsize=fontsize_ticks)
            plt.yticks(fontsize=fontsize_ticks)
            plt.title('Training Set', fontsize=fontsize)
            plt.xlim(lims)
            plt.ylim(lims)
            plt.grid(True)
            plt.text(0.05, 0.95, f'$R^2$ = {r2_train:.2f}\nMSE = {mse_train:.4f}', 
                    transform=plt.gca().transAxes, fontsize=fontsize,
                    verticalalignment='top', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))

            # ---- Test subplot ----
            plt.subplot(1, 3, 2)
            sc2 = plt.scatter(y_true_test, y_pred_test, c='darkorange', alpha=0.7, edgecolor='k', s=60)
            lims = [min(y_true_test.min(), y_pred_test.min()), max(y_true_test.max(), y_pred_test.max())]
            plt.plot(lims, lims, 'r--', lw=2)
            plt.xlabel('Actual RF (Test)', fontsize=fontsize)
            plt.ylabel('Predicted RF (Test)', fontsize=fontsize)
            plt.xticks(fontsize=fontsize_ticks)
            plt.yticks(fontsize=fontsize_ticks)
            plt.title('Test Set', fontsize=fontsize)
            plt.xlim(lims)
            plt.ylim(lims)
            plt.grid(True)
            plt.text(0.05, 0.95, f'$R^2$ = {r2_test:.2f}\nMSE = {mse_test:.4f}', 
                    transform=plt.gca().transAxes, fontsize=fontsize,
                    verticalalignment='top', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))

            # ---- Loss subplot ----
            plt.subplot(1, 3, 3)
            for i in range(len(all_train_losses)):
                plt.plot(all_train_losses[i], label=f"Train Fold {i+1}", linestyle='-', linewidth=2)
                plt.plot(all_val_losses[i], label=f"Val Fold {i+1}", linestyle='--', linewidth=2)
            plt.xlabel("Epoch", fontsize=fontsize)
            plt.ylabel("MSE Loss", fontsize=fontsize)
            plt.title("Training vs Validation Loss", fontsize=fontsize)
            plt.xticks(fontsize=fontsize_ticks)
            plt.yticks(fontsize=fontsize_ticks)
            plt.grid(True)
            plt.legend(fontsize=fontsize)
            plt.tight_layout()
            plt.show()
            
            torch.save(model.state_dict(), "ann_model_plot.pt")
            joblib.dump({"X_scaler": scaler, "y_scaler": y_scaler}, "scalers_plot.pkl")
            
            # torch.save(model.state_dict(), "ann_model_withCG.pt")
            # joblib.dump({"X_scaler": scaler, "y_scaler": y_scaler}, "scalers_withCG.pkl")
        return model, scaler
def constraints(trial):
    """Return positive if violating constraint."""
    return (trial.user_attrs["constraint"],)
def count_params(input_dim, hidden_sizes):
    params = 0
    in_dim = input_dim
    for h in hidden_sizes:
        params += in_dim * h + h  # weights + bias
        in_dim = h
    params += in_dim * 1 + 1  # output layer
    return params
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
    layers.append(nn.Linear(in_dim, 1))  # Output layer
    layers.append(nn.Sigmoid())          # Constrain output to (0,1)
    return nn.Sequential(*layers)

    
def optimize_hyperparameters(X, Y, n_trials=30):
    def objective(trial):
        # return train_and_evaluate_model(X, Y, trial)
        return train_and_evaluate_model_kfold(X, Y, trial)
    # === Optuna study setup ===
    if __name__ == "__main__":
        sampler = optuna.integration.BoTorchSampler(
        constraints_func=constraints,
        n_startup_trials=10,
    )
    study = optuna.create_study(direction="minimize", sampler=sampler)
    study.optimize(objective, n_trials=n_trials)
    print("\n✅ Best Trial:")
    print(study.best_trial.params)
    optuna.visualization.plot_optimization_history(study)
    return study.best_trial.params

# === Run script ===
def NN_Model(X, Y, use_optimization=False):
    if use_optimization:
        storage = optuna.storages.RDBStorage(
        url="sqlite:///optuna_optimization_history.db",
        engine_kwargs={"pool_size": 20, "connect_args": {"timeout": 10}},)
        study = optuna.create_study(storage=storage)
        best_params = optimize_hyperparameters(X, Y, n_trials=50)
        print("✅ Re-training model with best parameters...")
        train_and_evaluate_model_kfold(X, Y, trial=optuna.trial.FixedTrial(best_params))
    else:
        # model, scaler = train_and_evaluate_model(X, Y)
        model, scaler = train_and_evaluate_model_kfold(X, Y)
        return model, scaler



def main(input_directory):
    
    rf_values = []
    labels = []
    inputs = []
    file_path = os.path.join(input_directory, 'mixing_results_plot.xlsx')
    df = pd.read_excel(file_path)
    ordered_data = []
    for i in range(len(df)):
        row = []
        for label in df:
            row.append(df[label].iloc[i])
        ordered_data.append(row)
    for data in ordered_data:
        rf_values.append(data[11])
        inputs.append({
            "label": data[0],
            "FlowRate": data[1],
            "CycleLength":data[2],
            "Permeability": data[3],
            "Pressure": data[5],
            "delta_rho": data[14],
            "porosity": data[4],
            "Temperature": data[6],
            "CG Ratio": data[17],
            "RF_final": data[11]
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
    indexRF = df[ (df["RF_final"] == 0.0)].index
    df = df.drop(indexRF)  # Drop rows with NaN values
    # print(df.head())    # verify ordering and contents
    X = df[["FlowRate", "CycleLength", "Permeability", "Pressure", "delta_rho", 'porosity', 'Temperature']].values
    Y = df["RF_final"].values
    # NN_Model(X, Y, use_optimization=True) 
    NN_Model(X, Y)  
    
os.chdir("Y:\\Mixing Results\\July")  # Change to the directory containing your simulation files
# os.chdir("Y:\\Mixing Results\\May\\NewCH4")  # Change to the directory containing your simulation files
# os.chdir("Z:\\Mixing Results\\Feb\\Results\\30 Meter Height Reservoir")  # Change to the directory containing your simulation files
input_directory = os.getcwd()
main(input_directory)    