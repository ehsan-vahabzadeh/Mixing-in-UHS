# %% [markdown]
# # GB Offshore Wind Farm: Resource, Price & Revenue Modelling
#
# Built step-by-step as interview prep (Aurora Energy Research).
# Each "Part" is a self-contained cell. Run cells top-to-bottom in an
# interactive Python window (VS Code supports the `# %%` cell markers),
# or run the whole file as a script.

# %%
import numpy as np
import matplotlib.pyplot as plt

# A fixed seed makes the simulation reproducible: every time we re-run this
# script we get the *same* "random" wind year, which matters when we're
# debugging or comparing before/after changes. In Part 5 (Monte Carlo) we'll
# deliberately let the seed vary across many runs.
rng = np.random.default_rng(seed=42)

N_HOURS = 8760  # one non-leap year, hourly resolution

# %% [markdown]
# ## Part 1 — Wind resource

# %%
# --- Step 1: simulate hourly wind speed from a Weibull distribution -------
#
# WHY Weibull, not Normal? Wind speed is non-negative and right-skewed (lots
# of moderate-wind hours, a shrinking tail of very high-wind hours, and it
# can never go below 0). The Normal distribution allows negative values and
# is symmetric, so it's the wrong shape for wind. The Weibull distribution
# is the industry-standard choice for wind resource modelling because it's
# flexible enough to match measured wind climates with just two parameters:
#   - shape k:   controls how "peaked" the distribution is around its mode.
#                k=2 is a common empirical fit for real wind sites (this
#                special case is also called a "Rayleigh distribution").
#   - scale λ:   roughly sets the typical wind speed magnitude (it is NOT
#                the mean directly; mean = λ * Gamma(1 + 1/k)).
#
# We use scipy's convention via numpy directly here (numpy has a native
# Weibull sampler): np.random.Generator.weibull(a) draws from a *standard*
# Weibull with shape `a` and scale 1, so we multiply by λ to rescale.
k_shape = 2.0      # shape parameter (dimensionless)
lam_scale = 9.0    # scale parameter, in m/s -- typical for GB offshore sites

wind_speed_ms = lam_scale * rng.weibull(a=k_shape, size=N_HOURS)

# Sanity check on the *input* distribution before we touch the power curve:
# mean wind speed should come out around 7-8 m/s for these parameters, which
# is realistic for a good GB offshore site (onshore GB sites are usually a
# couple of m/s lower).
print(f"Mean simulated wind speed: {wind_speed_ms.mean():.2f} m/s")
print(f"Max simulated wind speed:  {wind_speed_ms.max():.2f} m/s")

# %%
# --- Step 2: convert wind speed -> capacity factor via a power curve ------
#
# A real turbine power curve is a lookup table from the manufacturer, but
# every one has the same qualitative shape, which we approximate here:
#   v < 4 m/s        : too little energy in the wind to turn the rotor
#                       usefully -> output = 0 ("cut-in" speed)
#   4 <= v < 13 m/s   : power in wind scales with v^3 (kinetic energy flux
#                       is proportional to velocity cubed), so output ramps
#                       up on a cubic curve until it hits the generator's
#                       rated (maximum) electrical capacity
#   13 <= v < 25 m/s  : turbine is already at its electrical/mechanical
#                       limit, so it deliberately pitches its blades to
#                       *spill* excess wind energy and holds output flat
#                       at rated capacity (capacity factor = 1.0)
#   v >= 25 m/s       : turbine shuts down entirely to protect the
#                       structure from storm damage ("cut-out" speed)
V_CUTIN = 4.0
V_RATED = 13.0
V_CUTOUT = 25.0


def wind_speed_to_capacity_factor(v: np.ndarray) -> np.ndarray:
    """Map wind speed (m/s) to turbine capacity factor in [0, 1]."""
    cf = np.zeros_like(v)

    # Cubic ramp region: normalise so cf=0 exactly at cut-in and cf=1
    # exactly at rated speed. Using v**3 (not v) is what makes this a
    # physically-motivated ramp rather than an arbitrary straight line.
    ramp_mask = (v >= V_CUTIN) & (v < V_RATED)
    cf[ramp_mask] = (v[ramp_mask] ** 3 - V_CUTIN ** 3) / (V_RATED ** 3 - V_CUTIN ** 3)

    # Flat-rated region: bolted to 1.0, regardless of how much windier it
    # gets, right up until cut-out.
    flat_mask = (v >= V_RATED) & (v < V_CUTOUT)
    cf[flat_mask] = 1.0

    # Everything else (v < cut-in, or v >= cut-out) stays at the 0 we
    # initialised with -- no need to write it explicitly.
    return cf


capacity_factor = wind_speed_to_capacity_factor(wind_speed_ms)

# --- Step 3: scale to a 1 GW farm to get hourly MW output -----------------
FARM_CAPACITY_MW = 1000.0
wind_output_mw = capacity_factor * FARM_CAPACITY_MW

# %%
# --- Step 4: the headline sanity-check number -----------------------------
#
# Annual load factor (a.k.a. capacity factor, plant-level) = average output
# over the year, divided by nameplate capacity. It answers: "if this farm
# ran at full 1 GW output 100% of the time, what fraction of that maximum
# possible energy did it actually deliver?"
annual_load_factor = wind_output_mw.mean() / FARM_CAPACITY_MW
print(f"\nAnnual load factor: {annual_load_factor:.1%}")

if 0.40 <= annual_load_factor <= 0.50:
    print("-> Realistic for GB offshore wind (typical range ~40-50%).")
else:
    print("-> WARNING: outside the ~40-50% range expected for GB offshore "
          "wind -- check k, lambda, or the power curve breakpoints.")

# %%
# --- Quick visual sanity check --------------------------------------------
fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

axes[0].plot(wind_speed_ms[:24 * 14], color="steelblue", linewidth=0.8)
axes[0].axhline(V_CUTIN, color="grey", linestyle="--", linewidth=0.8, label="cut-in")
axes[0].axhline(V_RATED, color="green", linestyle="--", linewidth=0.8, label="rated")
axes[0].axhline(V_CUTOUT, color="red", linestyle="--", linewidth=0.8, label="cut-out")
axes[0].set_ylabel("Wind speed (m/s)")
axes[0].set_title("First 2 weeks of simulated wind speed")
axes[0].legend(loc="upper right", fontsize=8)

axes[1].plot(wind_output_mw[:24 * 14], color="darkorange", linewidth=0.8)
axes[1].set_ylabel("Output (MW)")
axes[1].set_xlabel("Hour of year")
axes[1].set_title("Corresponding wind farm output (1 GW capacity)")

plt.tight_layout()
plt.savefig("aurora_interview_prep/part1_wind_resource.png", dpi=120)
print("\nSaved plot to aurora_interview_prep/part1_wind_resource.png")
