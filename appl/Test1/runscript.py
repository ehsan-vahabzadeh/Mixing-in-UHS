import subprocess
import argparse
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

import pyvista as pv
import vtk

subprocess.call(['make'] + ['appl_2pncgeobio_biogeochemical_tpfa'])

subprocess.call(['make'] + ['appl_2pncgeobio_biogeochemical_tpfa_oldDiff'])


testname = "biogeochemical_base"
params = 'params.input'
subprocess.call(['./'+'appl_2pncgeobio_biogeochemical_tpfa'] + [params] + ['-Problem.Name', testname] + ['-Geochemistry.EnableGeo', 'false'] + ['-Microbes.EnableMG', 'false'])

testname = "biogeochemical_base_oldDiff"
params = 'params.input'
subprocess.call(['./'+'appl_2pncgeobio_biogeochemical_tpfa_oldDiff'] + [params] + ['-Problem.Name', testname] + ['-Geochemistry.EnableGeo', 'false'] + ['-Microbes.EnableMG', 'false'])


# testname = "biogeochemical_geo_10"
# params = 'params.input'
# subprocess.call(['./'+'appl_2pncgeobio_biogeochemical_tpfa'] + [params] + ['-Problem.Name', testname] + ['-Geochemistry.EnableGeo', 'true'] + ['-Geochemistry.ScalingFactor', '10'] + ['-Microbes.EnableMG', 'false'])

# testname = "biogeochemical_geo_100"
# params = 'params.input'
# subprocess.call(['./'+'appl_2pncgeobio_biogeochemical_tpfa'] + [params] + ['-Problem.Name', testname] + ['-Geochemistry.EnableGeo', 'true'] + ['-Geochemistry.ScalingFactor', '100'] + ['-Microbes.EnableMG', 'false'])

# testname = "biogeochemical_geo_10_bio"
# params = 'params.input'
# subprocess.call(['./'+'appl_2pncgeobio_biogeochemical_tpfa'] + [params] + ['-Problem.Name', testname] + ['-Geochemistry.EnableGeo', 'true'] + ['-Geochemistry.ScalingFactor', '10'] + ['-Microbes.EnableMG', 'true'])

# testname = "biogeochemical_geo_bio_new"
# params = 'params.input'
# subprocess.call(['./'+'appl_2pncgeobio_biogeochemical_tpfa'] + [params] + ['-Problem.Name', testname] + ['-Geochemistry.EnableGeo', 'true'] + ['-Geochemistry.ScalingFactor', '10'] + ['-Microbes.EnableMG', 'true'])

# testname = "biogeochemical_geo_100_bio"
# params = 'params.input'
# subprocess.call(['./'+'appl_2pncgeobio_biogeochemical_tpfa'] + [params] + ['-Problem.Name', testname] + ['-Geochemistry.EnableGeo', 'false'] + ['-Geochemistry.ScalingFactor', '100'] + ['-Microbes.EnableMG', 'true'])

# testname = "biogeochemical_geo_1000"
# params = 'params.input'
# subprocess.call(['./'+'appl_2pncgeobio_biogeochemical_tpfa'] + [params] + ['-Problem.Name', testname] + ['-Geochemistry.EnableGeo', 'false'] + ['-Geochemistry.ScalingFactor', '1000'] + ['-Microbes.EnableMG', 'false'])

# testname = "biogeochemical_geo_1000_bio"
# params = 'params.input'
# subprocess.call(['./'+'appl_2pncgeobio_biogeochemical_tpfa'] + [params] + ['-Problem.Name', testname] + ['-Geochemistry.EnableGeo', 'false'] + ['-Geochemistry.ScalingFactor', '1000'] + ['-Microbes.EnableMG', 'true'])