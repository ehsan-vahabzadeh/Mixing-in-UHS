import subprocess
import argparse
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

import vtk

# Compile the code first
subprocess.call(['make', 'appl_1pnc_box_CH4'])

# Define the test cases and their parameters
test_cases = [
    {
        "name": "CH4-1e5-14-100-10",
        "InjectionRateDev": '-3.77',
        "InjectionRateOp": '-3.77',
        "ProductionRate": '3.77',
        "Well_Height": '10',
        "ReferencePermeability": '9.869233e-14',
        "TEnd": '154',
        "InjectionDurationDev": '14',
        "InjectionDurationOp": '7',
        "ExtractionDurationOp": '7'
    },
    {
        "name": "CH4-1e5-14-100-20",
        "InjectionRateDev": str(-3.77 / 2),  # Change values as needed
        "InjectionRateOp": str(-3.77 / 2),
        "ProductionRate": str(3.77 / 2),
        "Well_Height": '20',
        "ReferencePermeability": '9.869233e-14',
        "TEnd": '154',
        "InjectionDurationDev": '14',
        "InjectionDurationOp": '7',
        "ExtractionDurationOp": '7'
    }
]

# Loop over each test case and run the simulations
for test_case in test_cases:
    params = 'params.input'
    subprocess.call([
        'mpirun', '-np', '16', 'appl_1pnc_box_CH4', params,
        '-Problem.Name', test_case["name"],
        '-BoundaryConditions.InjectionRateDev', test_case["InjectionRateDev"],
        '-BoundaryConditions.InjectionRateOp', test_case["InjectionRateOp"],
        '-BoundaryConditions.ProductionRate', test_case["ProductionRate"],
        '-BoundaryConditions.Well_Height', test_case["Well_Height"],
        '-SpatialParams.ReferencePermeability', test_case["ReferencePermeability"],
        '-TimeLoop.TEnd', test_case["TEnd"],
        '-BoundaryConditions.InjectionDurationDev', test_case["InjectionDurationDev"],
        '-BoundaryConditions.InjectionDurationOp', test_case["InjectionDurationOp"],
        '-BoundaryConditions.ExtractionDurationOp', test_case["ExtractionDurationOp"]
    ])
