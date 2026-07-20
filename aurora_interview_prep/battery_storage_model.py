# %% [markdown]
# # GB Battery Storage: Dispatch, Valuation, Monte Carlo, and Cannibalisation
#
# Synthetic interview-prep model for a 50 MW / 100 MWh GB battery.
#
# Run cells top-to-bottom in VS Code, or run the whole file:
#
#     python aurora_interview_prep/battery_storage_model.py
#
# The LP uses scipy.optimize.linprog. The optional MILP extension uses
# scipy.optimize.milp on a shorter sample by default because 8,760 binary
# variables is a much heavier problem than the annual LP.

# %%
from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import csr_matrix, lil_matrix


# %% [markdown]
# ## Fixed technical and financial assumptions

# %%
N_HOURS = 8_760
HOURS_PER_DAY = 24
N_DAYS = N_HOURS // HOURS_PER_DAY

POWER_LIMIT_MW = 50.0
ENERGY_CAPACITY_MWH = 100.0
ROUND_TRIP_EFFICIENCY = 0.85

# I use symmetric efficiency: eta on charge and eta on discharge.
# That means eta * eta = 0.85, so eta = sqrt(0.85) = 0.922.
ETA = math.sqrt(ROUND_TRIP_EFFICIENCY)

DEGRADATION_COST_GBP_PER_MWH = 2.0
START_SOC_MWH = 50.0

PRICE_MEAN_GBP_PER_MWH = 70.0
FIXED_OM_GBP_PER_YEAR = 1_000_000.0
CAPEX_GBP = 30_000_000.0
DISCOUNT_RATE = 0.08
ASSET_LIFE_YEARS = 15

OUTPUT_DIR = Path(__file__).resolve().parent


# %% [markdown]
# ## Shared result containers

# %%
@dataclass(frozen=True)
class BatteryParams:
    power_mw: float = POWER_LIMIT_MW
    energy_mwh: float = ENERGY_CAPACITY_MWH
    eta: float = ETA
    degradation_cost: float = DEGRADATION_COST_GBP_PER_MWH
    start_soc_mwh: float = START_SOC_MWH


@dataclass
class DispatchResult:
    charge_mw: np.ndarray
    discharge_mw: np.ndarray
    soc_mwh: np.ndarray
    annual_revenue_gbp: float
    solver_status: int = 0
    solver_message: str = ""


@dataclass
class LpTemplate:
    a_eq: csr_matrix
    b_eq: np.ndarray
    bounds: list[tuple[float, float]]
    n_hours: int
    terminal_soc: float | None


# %% [markdown]
# ## Part 1 - stochastic GB-like price series

# %%
def daily_price_shape(n_hours: int = N_HOURS) -> np.ndarray:
    """Zero-mean daily shape: morning/evening peaks, overnight/midday dips."""
    hour = np.arange(n_hours) % HOURS_PER_DAY

    morning_peak = 13.0 * np.exp(-0.5 * ((hour - 8.0) / 2.0) ** 2)
    evening_peak = 25.0 * np.exp(-0.5 * ((hour - 18.0) / 2.7) ** 2)
    overnight_dip = -13.0 * np.exp(-0.5 * ((hour - 3.0) / 2.8) ** 2)
    midday_dip = -8.0 * np.exp(-0.5 * ((hour - 13.0) / 2.4) ** 2)

    shape = morning_peak + evening_peak + overnight_dip + midday_dip
    one_day = shape[:HOURS_PER_DAY]
    return shape - one_day.mean()


def generate_price_series(
    rng: np.random.Generator,
    n_hours: int = N_HOURS,
    mu: float = PRICE_MEAN_GBP_PER_MWH,
    theta: float = 0.075,
    sigma: float = 5.5,
    expected_spike_events_per_year: float = 28.0,
    anchor_annual_mean: bool = True,
) -> tuple[np.ndarray, dict[str, float]]:
    """Generate synthetic hourly GB-like prices.

    Core process:
        P_t = P_(t-1) + theta * (mu - P_(t-1)) + sigma * epsilon_t

    Then a zero-mean intraday shape is added, plus Poisson scarcity spikes.
    The optional annual mean anchor is a practical calibration step that keeps
    the synthetic year close to the requested 70 GBP/MWh without erasing the
    daily cycles or scarcity events.
    """
    base = np.empty(n_hours)
    base[0] = mu
    shocks = rng.normal(0.0, 1.0, size=n_hours)

    for t in range(1, n_hours):
        base[t] = base[t - 1] + theta * (mu - base[t - 1]) + sigma * shocks[t]

    prices = base + daily_price_shape(n_hours)

    n_spike_events = int(rng.poisson(expected_spike_events_per_year))
    spike_hours = rng.integers(0, n_hours, size=n_spike_events)
    spike_uplift = np.zeros(n_hours)

    for start_hour in spike_hours:
        duration = int(rng.integers(1, 5))
        jump = float(rng.lognormal(mean=math.log(125.0), sigma=0.45))
        for offset in range(duration):
            hour = start_hour + offset
            if hour < n_hours:
                spike_uplift[hour] += jump * (0.62**offset)

    prices = prices + spike_uplift

    if anchor_annual_mean:
        prices = prices - (prices.mean() - mu)

    # Negative prices are possible in GB, but this is a simple wholesale
    # arbitrage model, so keep the synthetic tails finite.
    prices = np.clip(prices, -25.0, 500.0)

    info = {
        "annual_average_price": float(prices.mean()),
        "min_price": float(prices.min()),
        "max_price": float(prices.max()),
        "spike_event_count": float(n_spike_events),
        "hours_above_150": float(np.sum(prices > 150.0)),
    }
    return prices, info


def plot_price_sanity(prices: np.ndarray, output_dir: Path = OUTPUT_DIR) -> Path:
    """Save price sanity plots: two-week trace and annual histogram."""
    output = output_dir / "battery_part1_price_series.png"

    fig, axes = plt.subplots(2, 1, figsize=(11, 7))
    first_hours = 14 * HOURS_PER_DAY

    axes[0].plot(prices[:first_hours], color="#255f85", linewidth=1.0)
    axes[0].set_title("Synthetic GB hourly prices - first 14 days")
    axes[0].set_ylabel("GBP/MWh")
    axes[0].grid(alpha=0.25)

    axes[1].hist(prices, bins=80, color="#52796f", edgecolor="white")
    axes[1].axvline(prices.mean(), color="#b23a48", linewidth=1.4, label=f"Mean = {prices.mean():.1f}")
    axes[1].set_title("Annual price distribution")
    axes[1].set_xlabel("GBP/MWh")
    axes[1].set_ylabel("Hours")
    axes[1].legend()
    axes[1].grid(alpha=0.20)

    fig.tight_layout()
    fig.savefig(output, dpi=140)
    plt.close(fig)
    return output


# %% [markdown]
# ## Part 2 - naive daily cheapest/priciest-hour heuristic

# %%
def heuristic_daily_dispatch(
    prices: np.ndarray,
    params: BatteryParams = BatteryParams(),
    hours_each_side: int = 2,
    terminal_soc: float | None = START_SOC_MWH,
) -> DispatchResult:
    """Daily rule: charge in the N cheapest hours, discharge in N priciest.

    The rule is deliberately myopic. It only looks within each calendar day,
    so it misses inter-day opportunity cost and does not know the future value
    of stored energy beyond today's top hours.
    """
    n_hours = len(prices)
    charge = np.zeros(n_hours)
    discharge = np.zeros(n_hours)
    soc = np.zeros(n_hours)
    current_soc = params.start_soc_mwh

    for day_start in range(0, n_hours, HOURS_PER_DAY):
        day_end = min(day_start + HOURS_PER_DAY, n_hours)
        day_prices = prices[day_start:day_end]
        n = min(hours_each_side, len(day_prices) // 2)

        cheapest = set(np.argsort(day_prices)[:n] + day_start)
        priciest = set(np.argsort(day_prices)[-n:] + day_start)

        for t in range(day_start, day_end):
            if t in cheapest:
                max_charge_by_space = (params.energy_mwh - current_soc) / params.eta
                charge[t] = max(0.0, min(params.power_mw, max_charge_by_space))
                current_soc += params.eta * charge[t]
            elif t in priciest:
                max_discharge_by_soc = current_soc * params.eta
                discharge[t] = max(0.0, min(params.power_mw, max_discharge_by_soc))
                current_soc -= discharge[t] / params.eta

            current_soc = min(params.energy_mwh, max(0.0, current_soc))
            soc[t] = current_soc

    if terminal_soc is not None and soc[-1] < terminal_soc:
        # The heuristic is not an optimiser; to make annual valuation fair, buy
        # back the missing terminal inventory in the final hour if needed.
        required_grid_charge = min(
            params.power_mw,
            max(0.0, (terminal_soc - soc[-1]) / params.eta),
        )
        charge[-1] += required_grid_charge
        soc[-1] += params.eta * required_grid_charge

    revenue = calculate_revenue(prices, charge, discharge, params)
    return DispatchResult(charge, discharge, soc, revenue)


# %% [markdown]
# ## Part 3 - optimal dispatch LP

# %%
def build_lp_template(
    n_hours: int,
    params: BatteryParams = BatteryParams(),
    terminal_soc: float | None = START_SOC_MWH,
) -> LpTemplate:
    """Build the sparse equality matrix and bounds shared by LP solves."""
    n_vars = 3 * n_hours
    n_eq = n_hours + (1 if terminal_soc is not None else 0)
    a_eq = lil_matrix((n_eq, n_vars), dtype=float)
    b_eq = np.zeros(n_eq, dtype=float)

    charge_offset = 0
    discharge_offset = n_hours
    soc_offset = 2 * n_hours

    for t in range(n_hours):
        row = t
        a_eq[row, charge_offset + t] = -params.eta
        a_eq[row, discharge_offset + t] = 1.0 / params.eta
        a_eq[row, soc_offset + t] = 1.0

        if t == 0:
            b_eq[row] = params.start_soc_mwh
        else:
            a_eq[row, soc_offset + t - 1] = -1.0

    if terminal_soc is not None:
        a_eq[n_hours, soc_offset + n_hours - 1] = 1.0
        b_eq[n_hours] = terminal_soc

    bounds = (
        [(0.0, params.power_mw)] * n_hours
        + [(0.0, params.power_mw)] * n_hours
        + [(0.0, params.energy_mwh)] * n_hours
    )

    return LpTemplate(a_eq=a_eq.tocsr(), b_eq=b_eq, bounds=bounds, n_hours=n_hours, terminal_soc=terminal_soc)


def lp_objective_vector(prices: np.ndarray, params: BatteryParams = BatteryParams()) -> np.ndarray:
    """Return minimisation objective for scipy.linprog.

    Maximise: sum(price * discharge - price * charge - degradation * discharge)
    Minimise: sum(price * charge - (price - degradation) * discharge)
    """
    return np.concatenate(
        [
            prices,
            -(prices - params.degradation_cost),
            np.zeros(len(prices)),
        ]
    )


def calculate_revenue(
    prices: np.ndarray,
    charge_mw: np.ndarray,
    discharge_mw: np.ndarray,
    params: BatteryParams = BatteryParams(),
) -> float:
    """Annual gross arbitrage revenue net of degradation cost."""
    return float(
        np.sum(prices * discharge_mw - prices * charge_mw - params.degradation_cost * discharge_mw)
    )


def solve_battery_lp(
    prices: np.ndarray,
    params: BatteryParams = BatteryParams(),
    template: LpTemplate | None = None,
    terminal_soc: float | None = START_SOC_MWH,
) -> DispatchResult:
    """Solve the annual battery dispatch LP."""
    n_hours = len(prices)
    if template is None:
        template = build_lp_template(n_hours, params, terminal_soc=terminal_soc)

    result = linprog(
        c=lp_objective_vector(prices, params),
        A_eq=template.a_eq,
        b_eq=template.b_eq,
        bounds=template.bounds,
        method="highs",
    )

    if not result.success:
        raise RuntimeError(f"Battery LP failed: {result.message}")

    charge = result.x[:n_hours]
    discharge = result.x[n_hours : 2 * n_hours]
    soc = result.x[2 * n_hours :]
    revenue = calculate_revenue(prices, charge, discharge, params)

    return DispatchResult(charge, discharge, soc, revenue, result.status, result.message)


def analyse_binding_constraints(
    dispatch: DispatchResult,
    params: BatteryParams = BatteryParams(),
    tolerance: float = 1e-5,
) -> dict[str, float]:
    """Count the hours where main battery constraints bind."""
    charge = dispatch.charge_mw
    discharge = dispatch.discharge_mw
    soc = dispatch.soc_mwh

    charged_mwh = float(charge.sum())
    discharged_mwh = float(discharge.sum())

    return {
        "charge_power_bound_hours": float(np.sum(charge >= params.power_mw - tolerance)),
        "discharge_power_bound_hours": float(np.sum(discharge >= params.power_mw - tolerance)),
        "empty_energy_bound_hours": float(np.sum(soc <= tolerance)),
        "full_energy_bound_hours": float(np.sum(soc >= params.energy_mwh - tolerance)),
        "idle_hours": float(np.sum((charge <= tolerance) & (discharge <= tolerance))),
        "simultaneous_charge_discharge_hours": float(np.sum((charge > tolerance) & (discharge > tolerance))),
        "grid_charge_mwh": charged_mwh,
        "grid_discharge_mwh": discharged_mwh,
        "round_trip_loss_mwh": charged_mwh - discharged_mwh,
    }


def plot_lp_dispatch(
    prices: np.ndarray,
    dispatch: DispatchResult,
    output_dir: Path = OUTPUT_DIR,
    first_days: int = 14,
) -> Path:
    """Save a price/dispatch/SOC plot for the first few days."""
    output = output_dir / "battery_part3_lp_dispatch_first_14_days.png"
    n = first_days * HOURS_PER_DAY
    hours = np.arange(n)

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)

    axes[0].plot(hours, prices[:n], color="#1f4e79", linewidth=1.0)
    axes[0].set_ylabel("Price\nGBP/MWh")
    axes[0].grid(alpha=0.25)

    axes[1].bar(hours, dispatch.discharge_mw[:n], color="#2f9e44", width=0.9, label="Discharge")
    axes[1].bar(hours, -dispatch.charge_mw[:n], color="#d9480f", width=0.9, label="Charge")
    axes[1].axhline(0.0, color="black", linewidth=0.8)
    axes[1].set_ylabel("MW")
    axes[1].legend(loc="upper right")
    axes[1].grid(alpha=0.20)

    axes[2].plot(hours, dispatch.soc_mwh[:n], color="#5f3dc4", linewidth=1.2)
    axes[2].axhline(0.0, color="grey", linewidth=0.7)
    axes[2].axhline(ENERGY_CAPACITY_MWH, color="grey", linewidth=0.7)
    axes[2].set_ylabel("SOC\nMWh")
    axes[2].set_xlabel("Hour")
    axes[2].grid(alpha=0.25)

    fig.suptitle("Optimal LP dispatch - first 14 days")
    fig.tight_layout()
    fig.savefig(output, dpi=140)
    plt.close(fig)
    return output


# %% [markdown]
# ## Part 4 - investor valuation

# %%
def value_asset(
    annual_revenue_gbp: float,
    fixed_om_gbp_per_year: float = FIXED_OM_GBP_PER_YEAR,
    capex_gbp: float = CAPEX_GBP,
    discount_rate: float = DISCOUNT_RATE,
    asset_life_years: int = ASSET_LIFE_YEARS,
) -> dict[str, float]:
    """Convert annual gross revenue into simple payback and NPV."""
    annual_net_cashflow = annual_revenue_gbp - fixed_om_gbp_per_year
    payback_years = math.inf if annual_net_cashflow <= 0 else capex_gbp / annual_net_cashflow
    annuity_factor = sum(1.0 / ((1.0 + discount_rate) ** year) for year in range(1, asset_life_years + 1))
    npv = -capex_gbp + annual_net_cashflow * annuity_factor

    return {
        "annual_revenue_gbp": annual_revenue_gbp,
        "annual_net_cashflow_gbp": annual_net_cashflow,
        "simple_payback_years": payback_years,
        "npv_gbp": npv,
    }


# %% [markdown]
# ## Part 5 - Monte Carlo wrapper

# %%
def run_monte_carlo(
    n_sims: int,
    seed: int,
    params: BatteryParams = BatteryParams(),
    terminal_soc: float | None = START_SOC_MWH,
    progress_every: int = 50,
) -> dict[str, np.ndarray | float]:
    """Simulate many years, solve the LP for each, and collect valuations."""
    rng = np.random.default_rng(seed)
    template = build_lp_template(N_HOURS, params, terminal_soc=terminal_soc)

    revenues = np.empty(n_sims)
    npvs = np.empty(n_sims)

    start = perf_counter()
    for i in range(n_sims):
        prices, _ = generate_price_series(rng)
        dispatch = solve_battery_lp(prices, params, template=template, terminal_soc=terminal_soc)
        valuation = value_asset(dispatch.annual_revenue_gbp)
        revenues[i] = dispatch.annual_revenue_gbp
        npvs[i] = valuation["npv_gbp"]

        if progress_every and (i + 1) % progress_every == 0:
            elapsed = perf_counter() - start
            print(f"  Monte Carlo {i + 1:>4}/{n_sims} solved in {elapsed:,.1f}s")

    return {
        "revenues": revenues,
        "npvs": npvs,
        "mean_revenue": float(np.mean(revenues)),
        "p10_revenue": float(np.percentile(revenues, 10)),
        "p50_revenue": float(np.percentile(revenues, 50)),
        "p90_revenue": float(np.percentile(revenues, 90)),
        "mean_npv": float(np.mean(npvs)),
        "p10_npv": float(np.percentile(npvs, 10)),
        "p50_npv": float(np.percentile(npvs, 50)),
        "p90_npv": float(np.percentile(npvs, 90)),
    }


def plot_monte_carlo_histogram(revenues: np.ndarray, output_dir: Path = OUTPUT_DIR) -> Path:
    output = output_dir / "battery_part5_monte_carlo_revenue_histogram.png"

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.hist(revenues / 1_000_000.0, bins=40, color="#4c6ef5", edgecolor="white")
    ax.axvline(np.percentile(revenues, 10) / 1_000_000.0, color="#c92a2a", label="P10")
    ax.axvline(np.percentile(revenues, 50) / 1_000_000.0, color="#212529", label="P50")
    ax.axvline(np.percentile(revenues, 90) / 1_000_000.0, color="#2b8a3e", label="P90")
    ax.set_title("Monte Carlo distribution of annual battery revenue")
    ax.set_xlabel("Annual gross revenue (GBP million/year)")
    ax.set_ylabel("Simulated years")
    ax.legend()
    ax.grid(alpha=0.20)

    fig.tight_layout()
    fig.savefig(output, dpi=140)
    plt.close(fig)
    return output


# %% [markdown]
# ## Part 6 - saturation / cannibalisation experiment

# %%
def apply_storage_saturation(prices: np.ndarray, installed_storage_gw: float, reference_gw: float = 10.0) -> np.ndarray:
    """Shrink within-day spreads as storage buildout rises.

    This is intentionally crude and transparent: daily mean prices are held
    fixed, while deviations from the daily mean are compressed by a multiplier.
    More installed storage means batteries collectively charge in cheap hours
    and discharge in peak hours, narrowing the peak-to-trough spread.
    """
    spread_multiplier = 1.0 / (1.0 + installed_storage_gw / reference_gw)
    reshaped = prices.reshape((-1, HOURS_PER_DAY))
    daily_mean = reshaped.mean(axis=1, keepdims=True)
    saturated = daily_mean + spread_multiplier * (reshaped - daily_mean)
    return saturated.reshape(-1)


def run_saturation_curve(
    base_prices: np.ndarray,
    installed_storage_gw_points: list[float],
    params: BatteryParams = BatteryParams(),
    terminal_soc: float | None = START_SOC_MWH,
) -> list[dict[str, float]]:
    template = build_lp_template(len(base_prices), params, terminal_soc=terminal_soc)
    rows: list[dict[str, float]] = []

    for storage_gw in installed_storage_gw_points:
        adjusted_prices = apply_storage_saturation(base_prices, storage_gw)
        dispatch = solve_battery_lp(adjusted_prices, params, template=template, terminal_soc=terminal_soc)
        rows.append(
            {
                "installed_storage_gw": storage_gw,
                "spread_multiplier": 1.0 / (1.0 + storage_gw / 10.0),
                "annual_revenue_gbp": dispatch.annual_revenue_gbp,
                "annual_revenue_gbp_per_mw": dispatch.annual_revenue_gbp / params.power_mw,
                "average_price_gbp_per_mwh": float(adjusted_prices.mean()),
                "average_daily_spread_gbp_per_mwh": float(
                    np.mean(adjusted_prices.reshape((-1, HOURS_PER_DAY)).max(axis=1) - adjusted_prices.reshape((-1, HOURS_PER_DAY)).min(axis=1))
                ),
            }
        )

    return rows


def plot_saturation_curve(rows: list[dict[str, float]], output_dir: Path = OUTPUT_DIR) -> Path:
    output = output_dir / "battery_part6_saturation_cannibalisation_curve.png"

    storage = np.array([row["installed_storage_gw"] for row in rows])
    revenue_per_mw = np.array([row["annual_revenue_gbp_per_mw"] for row in rows]) / 1_000.0

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(storage, revenue_per_mw, marker="o", color="#0b7285", linewidth=2.0)
    ax.set_title("Storage saturation narrows spreads and cannibalises revenue")
    ax.set_xlabel("Installed storage in system (GW, stylised)")
    ax.set_ylabel("Annual revenue (GBPk/MW-year)")
    ax.grid(alpha=0.25)

    fig.tight_layout()
    fig.savefig(output, dpi=140)
    plt.close(fig)
    return output


# %% [markdown]
# ## Part 7 - optional MILP charge/discharge exclusivity

# %%
def solve_battery_milp(
    prices: np.ndarray,
    params: BatteryParams = BatteryParams(),
    terminal_soc: float | None = START_SOC_MWH,
    time_limit_seconds: float = 60.0,
) -> DispatchResult:
    """MILP with one binary per hour to prevent simultaneous charge/discharge.

    Binary y_t:
        y_t = 1 allows charging, forces discharge to zero.
        y_t = 0 allows discharging, forces charge to zero.

    In this model the binary is often unnecessary: with positive prices,
    positive degradation cost, and efficiency losses, simultaneous charge and
    discharge is economically dominated in the LP relaxation.
    """
    n_hours = len(prices)
    base_template = build_lp_template(n_hours, params, terminal_soc=terminal_soc)

    n_vars = 4 * n_hours
    objective = np.concatenate([lp_objective_vector(prices, params), np.zeros(n_hours)])

    lower = np.concatenate(
        [
            np.zeros(n_hours),
            np.zeros(n_hours),
            np.zeros(n_hours),
            np.zeros(n_hours),
        ]
    )
    upper = np.concatenate(
        [
            np.full(n_hours, params.power_mw),
            np.full(n_hours, params.power_mw),
            np.full(n_hours, params.energy_mwh),
            np.ones(n_hours),
        ]
    )

    # Extend the LP SOC equalities with zero columns for binary variables.
    a_eq = lil_matrix((base_template.a_eq.shape[0], n_vars), dtype=float)
    a_eq[:, : 3 * n_hours] = base_template.a_eq
    equality = LinearConstraint(a_eq.tocsr(), base_template.b_eq, base_template.b_eq)

    # charge_t <= power * y_t
    # discharge_t <= power * (1 - y_t)
    a_ub = lil_matrix((2 * n_hours, n_vars), dtype=float)
    ub = np.zeros(2 * n_hours)
    lb = np.full(2 * n_hours, -np.inf)

    for t in range(n_hours):
        a_ub[t, t] = 1.0
        a_ub[t, 3 * n_hours + t] = -params.power_mw
        ub[t] = 0.0

        row = n_hours + t
        a_ub[row, n_hours + t] = 1.0
        a_ub[row, 3 * n_hours + t] = params.power_mw
        ub[row] = params.power_mw

    exclusivity = LinearConstraint(a_ub.tocsr(), lb, ub)

    integrality = np.zeros(n_vars, dtype=int)
    integrality[3 * n_hours :] = 1

    result = milp(
        c=objective,
        integrality=integrality,
        bounds=Bounds(lower, upper),
        constraints=[equality, exclusivity],
        options={"time_limit": time_limit_seconds, "mip_rel_gap": 1e-4},
    )

    if not result.success:
        raise RuntimeError(f"Battery MILP failed: {result.message}")

    charge = result.x[:n_hours]
    discharge = result.x[n_hours : 2 * n_hours]
    soc = result.x[2 * n_hours : 3 * n_hours]
    revenue = calculate_revenue(prices, charge, discharge, params)
    return DispatchResult(charge, discharge, soc, revenue, result.status, result.message)


# %% [markdown]
# ## Reporting helpers

# %%
def gbp_m(value: float) -> str:
    return f"GBP {value / 1_000_000.0:,.2f}m"


def write_dispatch_csv(
    prices: np.ndarray,
    heuristic: DispatchResult,
    optimal: DispatchResult,
    output_dir: Path = OUTPUT_DIR,
) -> Path:
    output = output_dir / "battery_dispatch_comparison.csv"
    with output.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "hour",
                "price_gbp_per_mwh",
                "heuristic_charge_mw",
                "heuristic_discharge_mw",
                "heuristic_soc_mwh",
                "lp_charge_mw",
                "lp_discharge_mw",
                "lp_soc_mwh",
            ]
        )
        for hour in range(len(prices)):
            writer.writerow(
                [
                    hour,
                    prices[hour],
                    heuristic.charge_mw[hour],
                    heuristic.discharge_mw[hour],
                    heuristic.soc_mwh[hour],
                    optimal.charge_mw[hour],
                    optimal.discharge_mw[hour],
                    optimal.soc_mwh[hour],
                ]
            )
    return output


def write_saturation_csv(rows: list[dict[str, float]], output_dir: Path = OUTPUT_DIR) -> Path:
    output = output_dir / "battery_saturation_curve.csv"
    with output.open("w", newline="") as f:
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output


def write_monte_carlo_csv(revenues: np.ndarray, npvs: np.ndarray, output_dir: Path = OUTPUT_DIR) -> Path:
    output = output_dir / "battery_monte_carlo_results.csv"
    with output.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["simulation", "annual_revenue_gbp", "npv_gbp"])
        for i, (revenue, npv) in enumerate(zip(revenues, npvs), start=1):
            writer.writerow([i, revenue, npv])
    return output


def print_dict(title: str, rows: dict[str, float]) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    for key, value in rows.items():
        if "gbp" in key or "revenue" in key or "npv" in key or "cashflow" in key:
            print(f"{key:38s}: {gbp_m(float(value))}")
        elif "years" in key:
            if math.isinf(float(value)):
                print(f"{key:38s}: not paid back")
            else:
                print(f"{key:38s}: {float(value):,.2f}")
        else:
            print(f"{key:38s}: {float(value):,.2f}")


# %% [markdown]
# ## Main workflow

# %%
def run_workflow(args: argparse.Namespace) -> None:
    params = BatteryParams()
    rng = np.random.default_rng(args.seed)
    terminal_soc = params.start_soc_mwh if args.enforce_terminal_soc else None

    print("GB battery storage model")
    print("========================")
    print(f"Power / energy             : {params.power_mw:.0f} MW / {params.energy_mwh:.0f} MWh")
    print(f"Efficiency treatment       : symmetric eta = sqrt(0.85) = {params.eta:.3f} on charge and discharge")
    print(f"Degradation cost           : GBP {params.degradation_cost:.2f}/MWh discharged")
    print(f"Starting SOC               : {params.start_soc_mwh:.1f} MWh")
    print(f"Terminal SOC constraint    : {terminal_soc if terminal_soc is not None else 'none'}")

    # Part 1
    prices, price_info = generate_price_series(rng)
    price_plot = plot_price_sanity(prices)
    print_dict("Part 1 price sanity checks", price_info)
    print(f"Saved price plot            : {price_plot}")

    # Part 2
    heuristic = heuristic_daily_dispatch(prices, params, hours_each_side=args.heuristic_hours, terminal_soc=terminal_soc)
    print(f"\nPart 2 heuristic revenue    : {gbp_m(heuristic.annual_revenue_gbp)}")

    # Part 3
    template = build_lp_template(N_HOURS, params, terminal_soc=terminal_soc)
    lp_start = perf_counter()
    optimal = solve_battery_lp(prices, params, template=template, terminal_soc=terminal_soc)
    lp_elapsed = perf_counter() - lp_start
    binding = analyse_binding_constraints(optimal, params)
    dispatch_plot = plot_lp_dispatch(prices, optimal)
    dispatch_csv = write_dispatch_csv(prices, heuristic, optimal)

    uplift = optimal.annual_revenue_gbp - heuristic.annual_revenue_gbp
    print(f"Part 3 LP revenue           : {gbp_m(optimal.annual_revenue_gbp)}")
    print(f"LP uplift vs heuristic      : {gbp_m(uplift)} ({uplift / heuristic.annual_revenue_gbp:.1%})")
    print(f"LP solve time               : {lp_elapsed:,.2f}s")
    print_dict("Part 3 binding-constraint diagnostics", binding)
    print("Note: efficiency is not a separate inequality. It is embedded in the SOC")
    print("      balance and creates the spread hurdle; the counted hard bounds are")
    print("      power and energy.")
    print(f"Saved dispatch plot         : {dispatch_plot}")
    print(f"Saved dispatch CSV          : {dispatch_csv}")

    # Part 4
    valuation = value_asset(optimal.annual_revenue_gbp)
    print_dict("Part 4 valuation", valuation)

    # Part 5
    if args.mc_sims > 0:
        print(f"\nPart 5 Monte Carlo          : solving {args.mc_sims} synthetic years")
        mc = run_monte_carlo(
            args.mc_sims,
            seed=args.seed + 10_000,
            params=params,
            terminal_soc=terminal_soc,
            progress_every=args.mc_progress_every,
        )
        mc_plot = plot_monte_carlo_histogram(mc["revenues"])
        mc_csv = write_monte_carlo_csv(mc["revenues"], mc["npvs"])
        print_dict(
            "Part 5 annual revenue distribution",
            {
                "mean_revenue_gbp": mc["mean_revenue"],
                "p10_revenue_gbp": mc["p10_revenue"],
                "p50_revenue_gbp": mc["p50_revenue"],
                "p90_revenue_gbp": mc["p90_revenue"],
                "mean_npv_gbp": mc["mean_npv"],
                "p10_npv_gbp": mc["p10_npv"],
                "p50_npv_gbp": mc["p50_npv"],
                "p90_npv_gbp": mc["p90_npv"],
            },
        )
        print(f"Saved MC histogram          : {mc_plot}")
        print(f"Saved MC CSV                : {mc_csv}")

    # Part 6
    storage_points = [0, 2, 5, 10, 15, 20, 30, 40]
    saturation_rows = run_saturation_curve(prices, storage_points, params, terminal_soc=terminal_soc)
    saturation_plot = plot_saturation_curve(saturation_rows)
    saturation_csv = write_saturation_csv(saturation_rows)
    print("\nPart 6 saturation / cannibalisation")
    print("-----------------------------------")
    for row in saturation_rows:
        print(
            f"{row['installed_storage_gw']:>5.1f} GW -> "
            f"{row['annual_revenue_gbp_per_mw'] / 1_000.0:>7.1f} GBPk/MW-year "
            f"(daily spread {row['average_daily_spread_gbp_per_mwh']:>5.1f} GBP/MWh)"
        )
    print(f"Saved saturation plot       : {saturation_plot}")
    print(f"Saved saturation CSV        : {saturation_csv}")

    # Part 7
    if args.run_milp:
        milp_hours = min(args.milp_hours, N_HOURS)
        print(f"\nPart 7 MILP demo            : solving first {milp_hours} hours")
        milp_start = perf_counter()
        milp_result = solve_battery_milp(
            prices[:milp_hours],
            params,
            terminal_soc=terminal_soc,
            time_limit_seconds=args.milp_time_limit,
        )
        milp_elapsed = perf_counter() - milp_start

        lp_subset = solve_battery_lp(
            prices[:milp_hours],
            params,
            terminal_soc=terminal_soc,
        )
        print(f"MILP revenue                : {gbp_m(milp_result.annual_revenue_gbp)}")
        print(f"LP on same period           : {gbp_m(lp_subset.annual_revenue_gbp)}")
        print(f"MILP solve time             : {milp_elapsed:,.2f}s")
        print("The MILP should be close to the LP here because the economics already")
        print("discourage simultaneous charge and discharge.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synthetic GB battery storage optimisation model.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for the base synthetic year.")
    parser.add_argument("--mc-sims", type=int, default=500, help="Monte Carlo simulations. Use 0 to skip.")
    parser.add_argument("--mc-progress-every", type=int, default=50, help="Print MC progress every N simulations.")
    parser.add_argument("--heuristic-hours", type=int, default=2, help="Daily N cheapest/N priciest heuristic hours.")
    parser.add_argument(
        "--no-terminal-soc",
        action="store_false",
        dest="enforce_terminal_soc",
        help="Do not force final SOC to equal starting SOC.",
    )
    parser.set_defaults(enforce_terminal_soc=True)
    parser.add_argument("--run-milp", action="store_true", help="Run the optional MILP exclusivity demo.")
    parser.add_argument("--milp-hours", type=int, default=168, help="Hours used for optional MILP demo.")
    parser.add_argument("--milp-time-limit", type=float, default=60.0, help="MILP time limit in seconds.")
    return parser.parse_args()


if __name__ == "__main__":
    run_workflow(parse_args())

