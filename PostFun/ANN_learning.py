import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error
import matplotlib.pyplot as plt

# -------------------------
# 1) Make "simulation" data
# -------------------------
np.random.seed(42)
torch.manual_seed(42)

N = 8000

# Inputs: (roughly similar to your UHS features)
flow_rate   = np.random.uniform(0.2, 1.0, N)      # normalized
cycle_len   = np.random.uniform(30, 180, N)       # days
perm_md     = np.random.uniform(10, 2000, N)      # mD
porosity    = np.random.uniform(0.05, 0.30, N)    # fraction
pressure    = np.random.uniform(50, 250, N)       # bar (toy)
delta_rho   = np.random.uniform(0.0, 50.0, N)     # kg/m3

X = np.vstack([flow_rate, cycle_len, perm_md, porosity, pressure, delta_rho]).T

# Toy "physics-ish" RF function: nonlinear + interactions + bounded in [0,1]
# NOTE: This is just to mimic complexity, not real reservoir physics.
def true_rf(x):
    fr, cl, k, phi, p, dr = x.T
    # some nonlinear effects + interactions:
    term1 = 0.8*np.tanh(0.002*(k - 200))                  # permeability effect saturates
    term2 = 0.6*np.tanh(6*(phi - 0.15))                   # porosity effect saturates
    term3 = -0.25*np.tanh(0.03*(dr - 15))                 # buoyancy/mixing penalty
    term4 = -0.15*np.tanh(0.02*(fr*cl - 60))              # rate*cycle interaction
    term5 = 0.10*np.tanh(0.02*(p - 120))                  # pressure weak effect
    raw = term1 + term2 + term3 + term4 + term5
    # squash to [0,1]
    rf = 1/(1 + np.exp(-raw))
    return rf

y_clean = true_rf(X)
noise = np.random.normal(0.0, 0.015, size=N)  # small noise
y = np.clip(y_clean + noise, 0.0, 1.0)

# -------------------------
# 2) Train/test split + scaling
# -------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, shuffle=True
)

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

X_train_t = torch.tensor(X_train_s, dtype=torch.float32)
y_train_t = torch.tensor(y_train, dtype=torch.float32).unsqueeze(1)
X_test_t  = torch.tensor(X_test_s, dtype=torch.float32)
y_test_t  = torch.tensor(y_test, dtype=torch.float32).unsqueeze(1)

train_loader = DataLoader(TensorDataset(X_train_t, y_train_t), batch_size=128, shuffle=True)

# -------------------------
# 3) Define the surrogate (MLP)
# -------------------------
class SurrogateMLP(nn.Module):
    def __init__(self, in_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()  # keep RF in [0,1]
        )

    def forward(self, x):
        return self.net(x)

model = SurrogateMLP(in_dim=X_train.shape[1])
criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=1e-3)

# -------------------------
# 4) Train (with simple early stopping)
# -------------------------
best_val = float("inf")
patience = 20
pat = 0
max_epochs = 200

train_losses = []
val_losses = []

for epoch in range(max_epochs):
    model.train()
    batch_loss = 0.0
    for xb, yb in train_loader:
        optimizer.zero_grad()
        pred = model(xb)
        loss = criterion(pred, yb)
        loss.backward()
        optimizer.step()
        batch_loss += loss.item()

    train_loss = batch_loss / len(train_loader)

    model.eval()
    with torch.no_grad():
        val_pred = model(X_test_t)
        val_loss = criterion(val_pred, y_test_t).item()

    train_losses.append(train_loss)
    val_losses.append(val_loss)

    # early stopping
    if val_loss < best_val - 1e-6:
        best_val = val_loss
        pat = 0
        best_state = {k: v.clone() for k, v in model.state_dict().items()}
    else:
        pat += 1
        if pat >= patience:
            break

# restore best model
model.load_state_dict(best_state)

# -------------------------
# 5) Evaluate
# -------------------------
model.eval()
with torch.no_grad():
    yhat_test = model(X_test_t).cpu().numpy().ravel()
    yhat_train = model(X_train_t).cpu().numpy().ravel()

r2_te = r2_score(y_test, yhat_test)
rmse_te = np.sqrt(mean_squared_error(y_test, yhat_test))

print(f"Test R^2 = {r2_te:.4f}")
print(f"Test RMSE = {rmse_te:.4f} (RF is 0..1)")

# Parity plot
plt.figure(figsize=(6,6))
plt.scatter(y_test, yhat_test, alpha=0.4, edgecolor=None)
lims = [min(y_test.min(), yhat_test.min()), max(y_test.max(), yhat_test.max())]
plt.plot(lims, lims)
plt.xlabel("True RF")
plt.ylabel("Pred RF")
plt.title("Parity plot (test)")
plt.grid(True)
plt.show()

# Loss curves
plt.figure(figsize=(7,4))
plt.plot(train_losses, label="train")
plt.plot(val_losses, label="val")
plt.xlabel("epoch")
plt.ylabel("MSE")
plt.title("Loss curves")
plt.grid(True)
plt.legend()
plt.show()