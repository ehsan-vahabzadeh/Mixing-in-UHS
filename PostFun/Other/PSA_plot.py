import numpy as np
import matplotlib.pyplot as plt
# ------------------------
# Data
# ------------------------
x_data = np.array([0.1, 0.2, 0.75])
y_data = np.array([1.9, 1.2, 0.016])

# ------------------------
# Double exponential model
# ------------------------
def PSA_cap_model(x):
    return (10.4702 * np.exp(-60.7137 * x) +
            3.1879  * np.exp(-4.8854  * x))

# Smooth curve for plotting
x_line = np.linspace(0, 1.0, 400)
y_line = PSA_cap_model(x_line)

# 50× and 100× versions
y_line_50 = 50 * y_line
y_line_100 = 100 * y_line

# ------------------------
# Plot
# ------------------------
plt.figure(figsize=(8, 5))

# Data points
# plt.scatter(x_data, y_data, s=60, label="Cost Points", color="black")
# Model curves
plt.plot(x_line, y_line, linewidth=2, label="Low Scenario", color="black")
plt.plot(x_line, y_line_50, linewidth=2, linestyle="--", label="Medium Scenario", color="black")
plt.plot(x_line, y_line_100, linewidth=2, linestyle=":", label="High Scenario", color="black")

# Axis labels
plt.xlabel("H₂ composition [-]", fontsize=18)
plt.ylabel("PSA capital [$/kg]", fontsize=18)
plt.ylim(-1, 20)
plt.xlim(0.4, 1.0)
# Ticks
plt.xticks(fontsize=18)
plt.yticks(fontsize=18)

# Layout + legend
plt.legend(fontsize=16,edgecolor='black')
plt.tight_layout()
plt.savefig("PSA_cost_model.jpeg", dpi=300)
plt.show()
