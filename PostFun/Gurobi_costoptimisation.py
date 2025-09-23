# pip install torch gurobipy gurobi-ml

# ---------- 1) Build a tiny PyTorch model (or load yours) ----------
import torch, torch.nn as nn
import gurobipy as gp
from gurobi_ml import add_predictor_constr
import numpy as np
import os

def fold_input_scaler_into_first_linear(model: nn.Module, scaler) -> None:
    """
    Modifies the first nn.Linear in-place to absorb an input scaler.
    Supports StandardScaler (mean_, scale_) and MinMaxScaler (min_, scale_).
    After this, give RAW inputs to the model.
    """
    # find first Linear
    first_lin = None
    for m in model.modules():
        if isinstance(m, nn.Linear):
            first_lin = m
            break
    if first_lin is None:
        raise ValueError("No nn.Linear layer found to fold scaler into.")

    W = first_lin.weight.detach().clone()   # (out, in)
    b = first_lin.bias.detach().clone()     # (out,)

    # derive a (per-feature gains) and c (per-feature offsets) for z = a ⊙ x + c
    if hasattr(scaler, "mean_") and hasattr(scaler, "scale_"):  # StandardScaler
        a = 1.0 / np.asarray(scaler.scale_, dtype=np.float64)
        c = -np.asarray(scaler.mean_, dtype=np.float64) / np.asarray(scaler.scale_, dtype=np.float64)
    elif hasattr(scaler, "min_") and hasattr(scaler, "scale_"):  # MinMaxScaler
        a = np.asarray(scaler.scale_, dtype=np.float64)
        c = np.asarray(scaler.min_, dtype=np.float64)
    else:
        raise ValueError("Unsupported scaler: expected StandardScaler or MinMaxScaler attributes.")

    a_t = torch.as_tensor(a, dtype=W.dtype, device=W.device)         # (in,)
    c_t = torch.as_tensor(c, dtype=W.dtype, device=W.device)         # (in,)

    # W' = W * diag(a)  (scale columns),  b' = b + W @ c
    with torch.no_grad():
        W_new = W * a_t.unsqueeze(0)                # broadcast over columns
        b_new = b + torch.mv(W, c_t)                # W @ c

        first_lin.weight.copy_(W_new)
        first_lin.bias.copy_(b_new)


# ---------- 2) Put it into Gurobi and optimize through it ----------

input_directory = os.getcwd()
# Load (exactly like your example)
mlp = torch.load("toy_relu_mlp.pt", map_location="cpu", weights_only=False)

m = gp.Model("nn_direct")
m.Params.OutputFlag = 0  # quiet

# Decision variables = network inputs (bound them!)
x = m.addMVar((2,), lb=[0.0, 0.0], ub=[1.0, 1.0], name="x")

# Output var (optional: bound it if you want)
y = m.addMVar((1,), name="y")

# *** This single call embeds the PyTorch net into the model ***
# It adds the right linear/ReLU constraints and ties x -> y through the NN.
add_predictor_constr(m, mlp, x, y)

# Example objective: maximize the NN output
m.setObjective(y[0], gp.GRB.MAXIMIZE)
m.optimize()

print("Status:", m.Status)                      # 2 = OPTIMAL
print("x*   :", x.X.tolist())
print("y*   :", float(y[0].X))