from pyDOE2 import lhs
import numpy as np

# Pick N samples in D dimensions
N = 100
D = 4  # e.g. cycle, pressure, permeability, flow

# Generate LHS in [0,1]^D
unit_lhs = lhs(D, samples=N, criterion='maximin')  
# criterion='maximin' maximizes the minimum distance between points

# unit_lhs is shape (N, D), each column stratified in [0,1]
# Suppose your real ranges are:
bounds = [
    (14, 180),       # cycle_length in days
    (60, 300),     # pressure in Pa
    (100, 1000),     # permeability in mD
    (1e5, 1.5e6)     # flow_rate in sm^3/d
]

X_lhs = np.zeros_like(unit_lhs)
for j, (low, high) in enumerate(bounds):
    X_lhs[:, j] = unit_lhs[:, j] * (high - low) + low
print(X_lhs)