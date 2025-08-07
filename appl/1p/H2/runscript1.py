import subprocess
import argparse
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import vtk
import os
    command = 'find . -maxdepth 1 -type f \\( -name "*.vtu" -o -name "*.pvtu" \\) -delete'
    subprocess.run(command, shell=True, check=True)
