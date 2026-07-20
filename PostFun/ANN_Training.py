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
DOF_LIMIT = 24000
PLOT_CACHE_VERSION = 2
DEFAULT_PLOT_CACHE_FILE = "ann_training_plot_cache.json"


def parameter_plot_output_dir(plot_cache_path=None):
    env_dir = os.environ.get("ANN_PLOT_OUTPUT_DIR")
    if env_dir:
        return os.path.abspath(env_dir)
    return os.getcwd()

def relative_error(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return np.abs((y_true - y_pred) / np.where(y_true == 0, np.nan, y_true))


def as_float_list(values):
    return np.asarray(values, dtype=float).tolist()


def write_plot_cache(
    path,
    feature_names,
    n_samples,
    X_train_raw,
    X_test_raw,
    y_true_train,
    y_pred_train,
    y_true_test,
    y_pred_test,
    all_train_losses,
    all_val_losses,
    output_dir=None,
):
    output_dir = output_dir or parameter_plot_output_dir(path)
    cache = {
        "version": PLOT_CACHE_VERSION,
        "output_dir": output_dir,
        "feature_names": list(feature_names),
        "n_samples": int(n_samples),
        "X_train_raw": as_float_list(X_train_raw),
        "X_test_raw": as_float_list(X_test_raw),
        "y_true_train": as_float_list(y_true_train),
        "y_pred_train": as_float_list(y_pred_train),
        "y_true_test": as_float_list(y_true_test),
        "y_pred_test": as_float_list(y_pred_test),
        "all_train_losses": [as_float_list(losses) for losses in all_train_losses],
        "all_val_losses": [as_float_list(losses) for losses in all_val_losses],
    }

    cache_dir = output_dir
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
    with open(path, "w") as f:
        json.dump(cache, f)
    print(f"Saved ANN plotting cache: {path}")


def load_plot_cache(path, feature_names, n_samples):
    if not path or not os.path.exists(path):
        return None

    with open(path, "r") as f:
        cache = json.load(f)

    if cache.get("version") != PLOT_CACHE_VERSION:
        print(f"Ignoring ANN plotting cache with old version: {path}")
        return None
    if cache.get("feature_names") != list(feature_names):
        print(f"Ignoring ANN plotting cache with different input columns: {path}")
        return None
    if cache.get("n_samples") != int(n_samples):
        print(f"Ignoring ANN plotting cache with different sample count: {path}")
        return None

    cache["_cache_path"] = os.path.abspath(path)
    return cache


def plot_test_porosity_vs_permeability(X_test_raw, feature_names, fontsize=20, fontsize_ticks=20):
    feature_lookup = {name: idx for idx, name in enumerate(feature_names)}
    if "Permeability" not in feature_lookup or "porosity" not in feature_lookup:
        print("Skipping porosity-permeability test plot; required columns are missing.")
        return

    x_raw = np.asarray(X_test_raw, dtype=float)
    permeability = x_raw[:, feature_lookup["Permeability"]]
    porosity = x_raw[:, feature_lookup["porosity"]]
    mask = np.isfinite(permeability) & np.isfinite(porosity) & (permeability > 0)

    fig, ax = plt.subplots(figsize=(8.5, 7.5))
    ax.scatter(permeability[mask], porosity[mask], c='grey', alpha=0.45, edgecolor='k', s=70)
    ax.set_xscale("log")
    ax.set_xlabel("Permeability [mD]", fontsize=fontsize)
    ax.set_ylabel("Porosity [-]", fontsize=fontsize)
    ax.tick_params(axis="both", labelsize=fontsize_ticks)
    ax.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.show()


def plot_cached_training_diagnostics(cache, fontsize=20, fontsize_ticks=20):
    output_dir = parameter_plot_output_dir(cache.get("_cache_path"))
    feature_names = cache["feature_names"]
    y_true_train = np.asarray(cache["y_true_train"], dtype=float)
    y_pred_train = np.asarray(cache["y_pred_train"], dtype=float)
    y_true_test = np.asarray(cache["y_true_test"], dtype=float)
    y_pred_test = np.asarray(cache["y_pred_test"], dtype=float)
    X_test_raw = np.asarray(cache["X_test_raw"], dtype=float)
    all_train_losses = cache.get("all_train_losses", [])
    all_val_losses = cache.get("all_val_losses", [])

    r2_train = r2_score(y_true_train, y_pred_train)
    r2_test = r2_score(y_true_test, y_pred_test)
    mse_train = mean_squared_error(y_true_train, y_pred_train)
    mse_test = mean_squared_error(y_true_test, y_pred_test)

    plt.figure(figsize=(18, 6))

    plt.subplot(1, 3, 1)
    plt.scatter(y_true_train, y_pred_train, c='royalblue', alpha=0.7, edgecolor='k', s=60)
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
    plt.text(0.05, 0.95, f'$R^2$ = {r2_train:.4f}\nMSE = {mse_train:.4f}',
             transform=plt.gca().transAxes, fontsize=fontsize,
             verticalalignment='top', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))

    plt.subplot(1, 3, 2)
    plt.scatter(y_true_test, y_pred_test, c='darkorange', alpha=0.7, edgecolor='k', s=60)
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
    plt.text(0.05, 0.95, f'$R^2$ = {r2_test:.4f}\nMSE = {mse_test:.4f}',
             transform=plt.gca().transAxes, fontsize=fontsize,
             verticalalignment='top', bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))

    ax_loss = plt.subplot(1, 3, 3)
    if all_train_losses and all_val_losses:
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
    else:
        ax_loss.set_visible(False)
    plt.tight_layout()
    plt.show()

    bins = np.linspace(0, 0.1, 21)
    plt.figure(figsize=(12, 10))

    plt.subplot(2, 2, 1)
    plt.hist(relative_error(y_true_train, y_pred_train), bins=bins, color='#7a0b01', alpha=0.7, edgecolor='black')
    plt.xticks(fontsize=fontsize_ticks)
    plt.yticks(fontsize=fontsize_ticks)
    plt.xlim([0, 0.1])
    plt.xlabel('Train, Relative Error [-]', fontsize=fontsize)
    plt.ylabel('Frequency [-]', fontsize=fontsize)

    plt.subplot(2, 2, 3)
    plt.hist(relative_error(y_true_test, y_pred_test), bins=bins, color='#7a0b01', alpha=0.7, edgecolor='black')
    plt.xticks(fontsize=fontsize_ticks)
    plt.yticks(fontsize=fontsize_ticks)
    plt.xlabel('Test, Relative Error [-]', fontsize=fontsize)
    plt.ylabel('Frequency [-]', fontsize=fontsize)
    plt.xlim([0, 0.1])

    plt.subplot(2, 2, 2)
    plt.scatter(y_true_train, y_pred_train, c='grey', alpha=0.4, edgecolor='k', s=60)
    lims = [min(y_true_test.min(), y_pred_test.min()), max(y_true_test.max(), y_pred_test.max())]
    plt.plot(lims, lims, 'r--', lw=2)
    plt.xlabel('Simulation RF [-]', fontsize=fontsize)
    plt.ylabel('ANN RF [-]', fontsize=fontsize)
    plt.xticks(fontsize=fontsize_ticks)
    plt.yticks(fontsize=fontsize_ticks)
    plt.xlim(lims)
    plt.ylim(lims)
    plt.text(0.05, 0.95, f'$R^2$ = {r2_train:.4f}\nMSE = {mse_train:.4f}',
             transform=plt.gca().transAxes, fontsize=fontsize,
             verticalalignment='top')

    plt.subplot(2, 2, 4)
    plt.scatter(y_true_test, y_pred_test, c='grey', alpha=0.4, edgecolor='k', s=60)
    lims = [min(y_true_test.min(), y_pred_test.min()), max(y_true_test.max(), y_pred_test.max())]
    plt.plot(lims, lims, 'r--', lw=2)
    plt.xlabel('Simulation RF [-]', fontsize=fontsize)
    plt.ylabel('ANN RF [-]', fontsize=fontsize)
    plt.xticks(fontsize=fontsize_ticks)
    plt.yticks(fontsize=fontsize_ticks)
    plt.xlim(lims)
    plt.ylim(lims)
    plt.text(0.05, 0.95, f'$R^2$ = {r2_test:.4f}\nMSE = {mse_test:.4f}',
             transform=plt.gca().transAxes, fontsize=fontsize,
             verticalalignment='top')

    plt.tight_layout()
    plt.show()

    plot_relative_error_vs_parameters(
        X_test_raw,
        y_true_test,
        y_pred_test,
        feature_names,
        fontsize=fontsize,
        fontsize_ticks=fontsize_ticks,
        output_dir=output_dir,
    )


def plot_relative_error_vs_parameters(
    X_raw,
    y_true,
    y_pred,
    feature_names,
    fontsize=20,
    fontsize_ticks=20,
    output_dir=None,
):
    fontsize = min(fontsize, 16)
    fontsize_ticks = min(fontsize_ticks, 14)
    rel_errors = relative_error(y_true, y_pred)
    x_raw = np.asarray(X_raw, dtype=float)
    feature_lookup = {name: idx for idx, name in enumerate(feature_names)}

    panels = [
        {
            "feature": "porosity",
            "xlabel": "Porosity [-]",
            "thresholds": [0.10, 0.20],
            "category_labels": ["Low\n<0.10", "Medium\n0.10-0.20", "High\n>0.20"],
            "scatter_scale": 1.0,
            "scatter_xlabel": "Porosity [-]",
        },
        {
            "feature": "Permeability",
            "xlabel": "Permeability [mD]",
            "thresholds": [10.0, 100.0],
            "category_labels": ["Low\n<10", "Medium\n10-100", "High\n>100"],
            "scatter_scale": 1.0,
            "scatter_xlabel": "Permeability [mD]",
        },
        {
            "feature": "Pressure",
            "xlabel": "Pressure [bar]",
            "thresholds": [150.0, 300.0],
            "category_labels": ["Low\n<150", "Medium\n150-300", "High\n>300"],
            "scatter_scale": 1.0,
            "scatter_xlabel": "Pressure [bar]",
        },
        {
            "feature": "FlowRate",
            "xlabel": "Flow rate [$10^6$ sm$^3$/d]",
            "thresholds": [5e5, 1e6],
            "category_labels": ["Low\n<0.5", "Medium\n0.5-1.0", "High\n>1.0"],
            "scatter_scale": 1e6,
            "scatter_xlabel": "Flow rate [$10^6$ sm$^3$/d]",
        },
    ]

    box_color = "#7a0b01"
    scatter_color = "grey"

    fig_box, axes_box = plt.subplots(2, 2, figsize=(12, 9.5), constrained_layout=True)
    axes_box = axes_box.ravel()
    for idx, (ax, panel) in enumerate(zip(axes_box, panels)):
        ax.set_box_aspect(0.85)
        feature = panel["feature"]
        if feature not in feature_lookup:
            ax.set_visible(False)
            continue

        values = x_raw[:, feature_lookup[feature]]
        mask = np.isfinite(values) & np.isfinite(rel_errors)
        x_vals = values[mask]
        y_vals = rel_errors[mask]
        thresholds = panel["thresholds"]

        category_masks = [
            x_vals < thresholds[0],
            (x_vals >= thresholds[0]) & (x_vals <= thresholds[1]),
            x_vals > thresholds[1],
        ]
        grouped_errors = [y_vals[category_mask] for category_mask in category_masks]
        non_empty_positions = [
            idx + 1 for idx, group in enumerate(grouped_errors) if len(group) > 0
        ]
        non_empty_groups = [group for group in grouped_errors if len(group) > 0]

        if non_empty_groups:
            box = ax.boxplot(
                non_empty_groups,
                positions=non_empty_positions,
                widths=0.55,
                patch_artist=True,
                showmeans=True,
                meanline=True,
                showfliers=False,
            )
            for body in box["boxes"]:
                body.set(facecolor=box_color, alpha=0.70, edgecolor="black", linewidth=1.6)
            for key in ["whiskers", "caps", "medians"]:
                for artist in box[key]:
                    artist.set(color="black", linewidth=1.4)
            for artist in box["means"]:
                artist.set(color="black", linewidth=2.0)
        else:
            ax.text(
                0.5,
                0.5,
                "No data",
                transform=ax.transAxes,
                ha="center",
                va="center",
                fontsize=fontsize,
            )

        ax.set_xlim(0.4, 3.6)
        ax.set_xticks([1, 2, 3])
        ax.set_xticklabels(panel["category_labels"], fontsize=fontsize_ticks)
        ax.set_xlabel(panel["xlabel"], fontsize=fontsize)
        if idx % 2 == 0:
            ax.set_ylabel("Relative Error [-]", fontsize=fontsize)
        else:
            ax.set_ylabel("")
        ax.tick_params(axis="y", labelsize=fontsize_ticks)
        ax.grid(axis="y", alpha=0.25)

    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        boxplot_path = os.path.join(output_dir, "ann_relative_error_parameter_boxplots.png")
        fig_box.savefig(boxplot_path, dpi=500, bbox_inches="tight")
        print(f"Saved parameter boxplot figure: {boxplot_path}")
    plt.show()

    fig_scatter, axes_scatter = plt.subplots(2, 2, figsize=(12, 9.5), constrained_layout=True)
    axes_scatter = axes_scatter.ravel()
    for idx, (ax, panel) in enumerate(zip(axes_scatter, panels)):
        ax.set_box_aspect(0.85)
        feature = panel["feature"]
        if feature not in feature_lookup:
            ax.set_visible(False)
            continue

        values = x_raw[:, feature_lookup[feature]] / panel["scatter_scale"]
        mask = np.isfinite(values) & np.isfinite(rel_errors)

        ax.scatter(values[mask], rel_errors[mask], c=scatter_color, alpha=0.45, edgecolor='k', s=60)
        ax.set_xlabel(panel["scatter_xlabel"], fontsize=fontsize)
        if idx % 2 == 0:
            ax.set_ylabel("Relative Error [-]", fontsize=fontsize)
        else:
            ax.set_ylabel("")
        ax.tick_params(axis="both", labelsize=fontsize_ticks)
        ax.grid(True, alpha=0.25)

    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        scatter_path = os.path.join(output_dir, "ann_relative_error_parameter_scatter.png")
        fig_scatter.savefig(scatter_path, dpi=500, bbox_inches="tight")
        print(f"Saved parameter scatter figure: {scatter_path}")
    plt.show()


def train_and_evaluate_model_kfold(X, Y, trial=None, feature_names=None, plot_cache_path=None):
    # === Optuna hyperparameters ===
    if trial:
        X_split, X_test, Y_split, y_test = train_test_split(X, Y, test_size=0.2, random_state=42)
        lr = trial.suggest_float('lr', 1e-5, 3e-3, log=True)
        n_layers = trial.suggest_int("n_layers", 1, 3)  # You can change range
        hidden_sizes = []
        activations = []

        for i in range(n_layers):
            hidden_sizes.append(trial.suggest_int(f"n_units_l{i}", 1, 128))
            activations.append(trial.suggest_categorical(f"activation_l{i}", ["relu", "tanh", "sigmoid"]))
            # activations.append(trial.suggest_categorical(f"activation_l{i}", ["relu"]))
        total_params = count_params(X.shape[1], hidden_sizes)
        trial.set_user_attr("constraint", total_params - DOF_LIMIT)
        if total_params > DOF_LIMIT:
            return float("inf")
        batch_size = 64
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
        if feature_names is None:
            feature_names = [
                "FlowRate",
                "CycleLength",
                "Permeability",
                "Pressure",
                "delta_rho",
                "porosity",
                "Temperature",
                "CG Ratio",
                "Cycle_No",
            ]
        X_train_raw = X_split.copy()
        X_test_raw = X_test.copy()
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
        
        # without the consideration of CG in RF/ Latest
        # lr = 0.0019425918125583334
        # hidden_sizes = [22,8]
        # activation = ["relu", "tanh"]
        # # activation = ["relu", "relu"]
        # batch_size = 8
        # epochs = 300
        
        
        # RF per cycle
        lr = 0.002110872822127545
        hidden_sizes = [36,92,108]
        activation = ["tanh", "relu", "sigmoid"]
        # activation = ["relu", "relu"]
        batch_size = 64
        epochs = 200
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
            X_train_plot_t = torch.tensor(scaler.transform(X_train_raw), dtype=torch.float32)
            X_test_plot_t = torch.tensor(scaler.transform(X_test_raw), dtype=torch.float32)

            # Test set
            y_pred_test  = model(X_test_plot_t).cpu().numpy().flatten()
            y_true_test  = y_test.flatten()
            # Train set
            y_pred_train = model(X_train_plot_t).cpu().numpy().flatten()
            y_true_train = Y_split.flatten()

            # y_pred_train = y_scaler.inverse_transform(y_pred_train.reshape(-1, 1)).ravel()
            # y_true_train = y_scaler.inverse_transform(y_true_train.reshape(-1, 1)).ravel()
            # y_pred_test = y_scaler.inverse_transform(y_pred_test.reshape(-1, 1)).ravel()
            # y_true_test = y_scaler.inverse_transform(y_true_test.reshape(-1, 1)).ravel()
            print('y_pred_scaled min/max:', y_pred_test.min(), y_pred_test.max())
            r2_train = r2_score(y_true_train, y_pred_train)
            r2_test = r2_score(y_true_test, y_pred_test)
            mse_train = mean_squared_error(y_true_train, y_pred_train)
            mse_test = mean_squared_error(y_true_test, y_pred_test)

            if plot_cache_path:
                cache_output_dir = parameter_plot_output_dir(plot_cache_path)
                write_plot_cache(
                    plot_cache_path,
                    feature_names,
                    len(Y),
                    X_train_raw,
                    X_test_raw,
                    y_true_train,
                    y_pred_train,
                    y_true_test,
                    y_pred_test,
                    all_train_losses,
                    all_val_losses,
                    output_dir=cache_output_dir,
                )

            plot_test_porosity_vs_permeability(
                X_test_raw,
                feature_names,
                fontsize=20,
                fontsize_ticks=20,
            )
            parameter_plot_dir = parameter_plot_output_dir(plot_cache_path)
        
            # Plotting
            plt.figure(figsize=(18, 6))
            fontsize = 20
            fontsize_ticks = 20
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
            plt.text(0.05, 0.95, f'$R^2$ = {r2_train:.4f}\nMSE = {mse_train:.4f}', 
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
            plt.text(0.05, 0.95, f'$R^2$ = {r2_test:.4f}\nMSE = {mse_test:.4f}', 
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
            
            from matplotlib.lines import Line2D

            cluster_colors = ['#fcc44b', '#9b3004', '#f16c09', "#f90b07", 'black']

            plt.figure(figsize=(12, 10))
            fontsize = 20
            fontsize_ticks = 20

            for i in range(len(all_train_losses)):
                plt.plot(all_train_losses[i],
                        linestyle='-',
                        linewidth=2,
                        color=cluster_colors[i])
                plt.plot(all_val_losses[i],
                        linestyle='--',
                        linewidth=2,
                        color=cluster_colors[i])

            plt.xlabel("Epoch [-]", fontsize=fontsize)
            plt.ylabel("MSE Loss [-]", fontsize=fontsize)
            plt.xticks(fontsize=fontsize_ticks)
            plt.yticks(fontsize=fontsize_ticks)
            # plt.yscale('log')

            ax = plt.gca()

            # ---- Legend 1: Fold colors ----
            fold_handles = [
                Line2D([0], [0], color=cluster_colors[i], lw=5, label=f"Fold {i+1}")
                for i in range(len(cluster_colors))
            ]

            legend_folds = ax.legend(
                handles=fold_handles,
                fontsize=fontsize,
                title_fontsize=fontsize,
                loc='upper right',
                frameon = False
            )

            ax.add_artist(legend_folds)  # IMPORTANT

            # ---- Legend 2: Line styles ----
            style_handles = [
                Line2D([0], [0], color='black', lw=5, linestyle='-', label='Train'),
                Line2D([0], [0], color='black', lw=5, linestyle='--', label='Validation')
            ]

            ax.legend(
                handles=style_handles,
                fontsize=fontsize,
                title_fontsize=fontsize,
                loc='center right',
                frameon = False
            )

            plt.tight_layout()
            plt.show()
            # torch.save(model.state_dict(), "ann_model_withoutCG_AC.pt")
            # joblib.dump({"X_scaler": scaler, "y_scaler": y_scaler}, "scalers_withoutCG_AC.pkl")
            
            # torch.save(model.state_dict(), "ann_model_withCG.pt")
            # joblib.dump({"X_scaler": scaler, "y_scaler": y_scaler}, "scalers_withCG.pkl")
            
            # torch.save(model.state_dict(), "ann_model_gurobi.pt")
            # joblib.dump({"X_scaler": scaler, "y_scaler": y_scaler}, "scalers_gurobi.pkl")

            fig = plt.figure(figsize=(12, 10))
            bins = np.linspace(0, 0.1, 21)  # 20 identical bins from 0 to 0.1
            # Subplot 1: Histogram Train
            
            plt.subplot(2, 2, 1)
            r2_train = r2_score(y_true_train, y_pred_train)
            relative_errors_train = []
            for ii in range(len(y_true_train)):     
                rel_error = abs((y_true_train[ii] - y_pred_train[ii]) / y_true_train[ii])
                relative_errors_train.append(rel_error)
            plt.hist(relative_errors_train, bins=bins, color='#7a0b01', alpha=0.7, edgecolor='black')
            plt.xticks(fontsize=fontsize_ticks)
            plt.yticks(fontsize=fontsize_ticks)
            # plt.title("Train $R^2$ Score Distribution")
            # plt.text(0.985, 180, f"$\\mu$ = {r2_train:.3f}\n$\\sigma$ = 0.001", fontsize=10)
            plt.xlim([0, 0.1])
            plt.xlabel('Train, Relative Error [-]', fontsize=fontsize)
            plt.ylabel('Frequency [-]', fontsize=fontsize)
            # Subplot 2: Histogram Test
            plt.subplot(2, 2, 3)
            r2_test = r2_score(y_true_test, y_pred_test)
            relative_errors_test = []
            for ii in range(len(y_true_test)):     
                rel_error = abs((y_true_test[ii] - y_pred_test[ii]) / y_true_test[ii])
                relative_errors_test.append(rel_error)
            plt.hist(relative_errors_test, bins=bins, color='#7a0b01', alpha=0.7, edgecolor='black')
            plt.xticks(fontsize=fontsize_ticks)
            plt.yticks(fontsize=fontsize_ticks)
            plt.xlabel('Test, Relative Error [-]', fontsize=fontsize)
            plt.ylabel('Frequency [-]', fontsize=fontsize)
            plt.xlim([0, 0.1])
            # Subplot 3: Scatter Train with 95% pred band
            plt.subplot(2, 2, 2)
            sc2 = plt.scatter(y_true_train, y_pred_train, c='grey', alpha=0.4, edgecolor='k', s=60)
            lims = [min(y_true_test.min(), y_pred_test.min()), max(y_true_test.max(), y_pred_test.max())]
            plt.plot(lims, lims, 'r--', lw=2)
            plt.xlabel('Simulation RF [-]', fontsize=fontsize)
            plt.ylabel('ANN RF [-]', fontsize=fontsize)
            plt.xticks(fontsize=fontsize_ticks)
            plt.yticks(fontsize=fontsize_ticks)
            # plt.title('Training Set', fontsize=fontsize)
            plt.xlim(lims)
            plt.ylim(lims) 
            plt.text(0.05, 0.95, f'$R^2$ = {r2_train:.4f}\nMSE = {mse_train:.4f}', 
                    transform=plt.gca().transAxes, fontsize=fontsize,
                    verticalalignment='top' )

            # Subplot 4: Scatter Test with 95% pred band
            plt.subplot(2, 2, 4)
            plt.scatter(y_true_test, y_pred_test, c='grey', alpha=0.4, edgecolor='k', s=60)
            lims = [min(y_true_test.min(), y_pred_test.min()), max(y_true_test.max(), y_pred_test.max())]
            plt.plot(lims, lims, 'r--', lw=2)
            plt.xlabel('Simulation RF [-]', fontsize=fontsize)
            plt.ylabel('ANN RF [-]', fontsize=fontsize)
            plt.xticks(fontsize=fontsize_ticks)
            plt.yticks(fontsize=fontsize_ticks)
            # plt.title('Test Set', fontsize=fontsize)
            plt.xlim(lims)
            plt.ylim(lims)
            plt.text(0.05, 0.95, f'$R^2$ = {r2_test:.4f}\nMSE = {mse_test:.4f}', 
                    transform=plt.gca().transAxes, fontsize=fontsize,
                    verticalalignment='top')

            plt.tight_layout()
            plt.show()

            plot_relative_error_vs_parameters(
                X_test_raw,
                y_true_test,
                y_pred_test,
                feature_names,
                fontsize=fontsize,
                fontsize_ticks=fontsize_ticks,
                output_dir=parameter_plot_dir,
            )
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
def NN_Model(X, Y, feature_names=None, use_optimization=False, plot_cache_path=None):
    if feature_names is None:
        feature_names = [f"feature_{i}" for i in range(X.shape[1])]

    if use_optimization:
        storage = optuna.storages.RDBStorage(
        url="sqlite:///optuna_optimization_history.db",
        engine_kwargs={"pool_size": 20, "connect_args": {"timeout": 10}},)
        study = optuna.create_study(storage=storage)
        best_params = optimize_hyperparameters(X, Y, n_trials=200)
        print("✅ Re-training model with best parameters...")
        train_and_evaluate_model_kfold(X, Y, trial=optuna.trial.FixedTrial(best_params))
    else:
        force_training = os.environ.get("ANN_FORCE_TRAINING", "0") == "1"
        plot_only = os.environ.get("ANN_PLOT_ONLY", "0") == "1"
        if plot_cache_path and not force_training:
            cache = load_plot_cache(plot_cache_path, feature_names, len(Y))
            if cache is not None:
                print(f"Loaded ANN plotting cache: {plot_cache_path}")
                plot_cached_training_diagnostics(cache)
                return None, None
            if plot_only:
                raise FileNotFoundError(
                    f"ANN plotting cache was not found or is not compatible: {plot_cache_path}. "
                    "Run once with ANN_FORCE_TRAINING=1 to train the ANN and create the cache."
                )
            print(f"No compatible ANN plotting cache found. Training once and saving: {plot_cache_path}")

        # model, scaler = train_and_evaluate_model(X, Y)
        model, scaler = train_and_evaluate_model_kfold(
            X,
            Y,
            feature_names=feature_names,
            plot_cache_path=plot_cache_path,
        )
        return model, scaler



def main(input_directory):
    
    rf_values = []
    labels = []
    inputs = []
    file_path = os.path.join(input_directory, 'mixing_results_withoutCG_allcycles.xlsx')
    # file_path = os.path.join(input_directory, 'mixing_results_withoutCG.xlsx')
    # file_path = os.path.join(input_directory, 'mixing_results_withCG.xlsx')
    df = pd.read_excel(file_path)
    ordered_data = []
    for i in range(len(df)):
        row = []
        for label in df:
            row.append(df[label].iloc[i])
        ordered_data.append(row)
    for data in ordered_data:
        inputs.append({
            "label": data[0],
            "FlowRate": data[1],
            "CycleLength":data[2],
            "Permeability": data[3],
            "Pressure": data[5],
            "delta_rho": data[15],
            "porosity": data[4],
            "Temperature": data[6],
            "CG Ratio": data[18],
            "Cycle_No":data[11],
            "rf": data[12]
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
    "rf",
    "Cycle_No" 
    ])
    df = df.dropna()  # Drop rows with NaN values
    # print(df.head())    # verify ordering and contents
    input_labels = ["FlowRate", "CycleLength", "Permeability", "Pressure", "delta_rho", 'porosity', 'Temperature','CG Ratio', 'Cycle_No']
    X = df[input_labels].values
    Y = df["rf"].values
    plot_cache_path = os.environ.get(
        "ANN_PLOT_CACHE",
        os.path.join(input_directory, DEFAULT_PLOT_CACHE_FILE),
    )
    # NN_Model(X, Y, use_optimization=True) 
    NN_Model(X, Y, feature_names=input_labels, plot_cache_path=plot_cache_path)  
    
if __name__ == "__main__":
    os.chdir("Y:\\Mixing Results\\July")  # Change to the directory containing your simulation files
    # os.chdir("Y:\\Mixing Results\\May\\NewCH4")  # Change to the directory containing your simulation files
    # os.chdir("Z:\\Mixing Results\\Feb\\Results\\30 Meter Height Reservoir")  # Change to the directory containing your simulation files
    input_directory = os.getcwd()
    main(input_directory)
