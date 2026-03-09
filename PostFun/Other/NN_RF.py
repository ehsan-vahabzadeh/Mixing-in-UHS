import json
import matplotlib.pyplot as plt
import numpy as np
import os
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import warnings

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import MinMaxScaler
def NN_Model(X, Y):
    # 2. Split
    X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=0.30, random_state=42 )

    # 3. Standardize
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test  = scaler.transform(X_test)
    # scaler = MinMaxScaler(feature_range=(-1,1))
    # X_train = scaler.fit_transform(X_train)
    # X_test  = scaler.transform(X_test)
    # 4. Tensors & loaders
    X_train_t = torch.tensor(X_train, dtype=torch.float32)
    y_train_t = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1)
    X_test_t  = torch.tensor(X_test, dtype=torch.float32)
    y_test_t  = torch.tensor(y_test, dtype=torch.float32).unsqueeze(1)

    train_ds = TensorDataset(X_train_t, y_train_t)
    test_ds  = TensorDataset(X_test_t, y_test_t)

    train_loader = DataLoader(train_ds, batch_size=16, shuffle=True)
    test_loader  = DataLoader(test_ds, batch_size=16)

    # 5. Model definition
    class RecoveryMLP(nn.Module):
        def __init__(self):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(5, 32),
                nn.ReLU(),
                nn.Linear(32,16),
                nn.ReLU(),
                nn.Linear(16,1)
            )
        def forward(self, x):
            return self.net(x)

    model = RecoveryMLP()

    # 6. Loss & optimizer
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    
    # 7. Training loop
    epochs = 1000
    for epoch in range(1, epochs+1):
        model.train()
        total_loss = 0.0
        for xb, yb in train_loader:
            optimizer.zero_grad()
            preds = model(xb)
            loss  = criterion(preds, yb)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * xb.size(0)
        total_loss /= len(train_loader.dataset)
        if epoch % 10 == 0:
            print(f"Epoch {epoch:3d}/{epochs} | Train MSE: {total_loss:.4f}")

    # 8. Evaluation
    model.eval()
    with torch.no_grad():
        preds = model(X_test_t).numpy().flatten()
        truth = y_test_t.numpy().flatten()
        mse = mean_squared_error(truth, preds)
        r2  = r2_score(truth, preds)
    print(f"\nTest MSE: {mse:.4f},  Test R²: {r2:.4f}")
    
    
    
    
    
    
    # 1. Ensure model is in eval mode
    model.eval()

    # 2. Gather predictions and truths
    with torch.no_grad():
        # Test set
        y_pred_test  = model(X_test_t).cpu().numpy().flatten()
        y_true_test  =   y_test_t.cpu().numpy().flatten()
        # Train set
        y_pred_train = model(X_train_t).cpu().numpy().flatten()
        y_true_train =   y_train_t.cpu().numpy().flatten()

    # 3. Plot
    plt.figure(figsize=(12,6))

    # ---- Training subplot ----
    plt.subplot(1,2,1)
    plt.scatter(y_true_train, y_pred_train, alpha=0.7, edgecolor='k')
    # 45° line
    lims = [
        min(y_true_train.min(), y_pred_train.min()),
        max(y_true_train.max(), y_pred_train.max())
    ]
    plt.plot(lims, lims, 'r--', lw=1)
    plt.xlabel('Actual RF (Train)', fontsize=12)
    plt.ylabel('Predicted RF (Train)', fontsize=12)
    plt.title('Training Set', fontsize=14)
    plt.xlim(lims); plt.ylim(lims)
    plt.grid(True)

    # ---- Test subplot ----
    plt.subplot(1,2,2)
    plt.scatter(y_true_test, y_pred_test, alpha=0.7, edgecolor='k')
    lims = [
        min(y_true_test.min(), y_pred_test.min()),
        max(y_true_test.max(), y_pred_test.max())
    ]
    plt.plot(lims, lims, 'r--', lw=1)
    plt.xlabel('Actual RF (Test)', fontsize=12)
    plt.ylabel('Predicted RF (Test)', fontsize=12)
    plt.title('Test Set', fontsize=14)
    plt.xlim(lims); plt.ylim(lims)
    plt.grid(True)

    plt.tight_layout()
    plt.show()



def main(input_directory):
    rf_values = []
    labels = []
    inputs = []
    file_path = os.path.join(input_directory, 'mixing_results.xlsx')
    df = pd.read_excel(file_path)
    ordered_data = []
    for i in range(len(df)):
        row = []
        for label in df:
            row.append(df[label].iloc[i])
        ordered_data.append(row)
    for data in ordered_data:
        rf_values.append(data[7])
        inputs.append({
            "label": data[0],
            "FlowRate": data[1],
            "CycleLength":data[2],
            "Permeability": data[3],
            "Pressure": data[4],
            "delta_rho": data[10]
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
    "delta_rho"          # last
    ])
    # print(df.head())    # verify ordering and contents
    X = df[["FlowRate", "CycleLength", "Permeability", "Pressure", "delta_rho"]].values
    Y = np.array(rf_values)
    NN_Model(X, Y)   
    
os.chdir("Y:\\Mixing Results\\New May")  # Change to the directory containing your simulation files

# os.chdir("Y:\\Mixing Results\\May\\NewCH4")  # Change to the directory containing your simulation files
# os.chdir("Z:\\Mixing Results\\Feb\\Results\\30 Meter Height Reservoir")  # Change to the directory containing your simulation files
input_directory = os.getcwd()
main(input_directory)    