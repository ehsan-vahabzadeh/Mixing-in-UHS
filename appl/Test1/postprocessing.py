# processing.py
import subprocess
import argparse
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from numpy import genfromtxt
from math import isclose
import json

import pyvista as pv
import vtk

try:
    plt.style.use('~/Templates/matplotlib/plot_style.txt')
except:
    print('plotstyle not found; default matplotlib is used')

### Argument parser
parser = argparse.ArgumentParser()

parser.add_argument('dumux', nargs='+', help='List of dumux cases')
parser.add_argument('-dumuxName', nargs='+', help='List of dumux cases names for plot')

parser.add_argument('-dumuxLineStyle', nargs='+', help='List of linstyles for DuMux cases for plot')

parser.add_argument('-cmg', nargs='+', help='List of cmg cases')
parser.add_argument('-cmgName', nargs='+', help='List of cmg cases names for plot')

parser.add_argument('-pyvista', action="store_true", help='Create rendered image pyvista')


parser.add_argument('-gif', action="store_true", help='Create rendered gif animation')
args = parser.parse_args()

DuMuxCases = []
HistoryCases = []
CMGCases = []

class DuMuxData:
    def __init__(self, name):
        self.name = name
        self.jsonFile = str(name + ".json") 
        with open(self.jsonFile, "r") as json_file:
            data = json.load(json_file)
        self.path = name
        self.label = name
        self.time = np.array(data["time"])/(60*60*24)
        self.rates = data["wellRate"]
        self.fieldrate = np.array([sum(values) for values in zip(*data["wellRate"].values())])
        self.averagereservoirpressure =  data["averageReservoirPressure"]
        self.bhp =  data["bottomHolePressure"]
        self.inventory = data["inventory"]
        self.materialBalanceError = data["materialBalanceError"]
        self.convertedMG =  data["convertedMG"]
        self.convertedGeo =  data["convertedGeo"]
        self.pvd = self.path + '.pvd'
        self.linestyle = '-'
        DuMuxCases.append(self)

    def setLabel(self, label):
        self.label = label

    def setLineStyle(self, linestyle):
        self.linestyle = linestyle

class cmgData:
    def __init__(self, path = None):
        self.path = ('./GEM_Comparison/')
        self.time = genfromtxt(self.path + 'time.txt')
        self.bhp = genfromtxt(self.path + "bhp.txt")/100
        CMGCases.append(self)

    def setLabel(self, label):
        self.label = label

for i in range(len(args.dumux)):
    dumux_data = DuMuxData(str(args.dumux[i]))
    if args.dumuxName is not None:
        dumux_data.setLabel(str(args.dumuxName[i]))
    if args.dumuxLineStyle is not None:
        dumux_data.setLineStyle(str(args.dumuxLineStyle[i]))


if args.cmg != None:
    for i in range(len(args.cmg)):
        cmg_data = cmgData(str(args.cmg[i]))
        if args.cmgName is not None:
            cmg_data.setLabel(str(args.cmgName[i]))


plt.xlabel("Time [d]")
plt.ylabel("Fieldrate [mol/s]")
for case in DuMuxCases:
    plt.plot(case.time, case.fieldrate, label = case.label, linestyle = case.linestyle)
plt.legend()
plt.savefig("fieldrate_plot.pdf", bbox_inches="tight")
plt.close()

plt.xlabel("Time [d]")
plt.ylabel("Average reservoir pressure [bar]")
for case in DuMuxCases:
    plt.plot(case.time, case.averagereservoirpressure, label = case.label, linestyle = case.linestyle)
plt.legend()
plt.savefig("avPressure_plot.pdf", bbox_inches="tight")
plt.close()

plt.xlabel("Time [d]")
plt.ylabel("Bottom-hole pressure [bar]")
for case in DuMuxCases:
    plt.plot(case.time, case.bhp, label = case.label, linestyle = case.linestyle)
plt.legend()
plt.savefig("pressure_plot.pdf", bbox_inches="tight")
plt.close()

plt.xlabel("Time [d]")
plt.ylabel("$\mathrm{H_2}$ Fraction [-]")
for case in DuMuxCases:
    plt.plot(case.time, case.rates["H2"]/case.fieldrate, label =case.label, linestyle = case.linestyle)
plt.legend()
plt.savefig("H2fraction_plot.pdf", bbox_inches="tight")
plt.close()

plt.xlabel("Time [d]")
plt.ylabel("$\mathrm{H_2S}$ Fraction [-]")
for case in DuMuxCases:
    plt.plot(case.time, case.rates["H2S"]/case.fieldrate, label =case.label, linestyle = case.linestyle)
plt.legend()
plt.savefig("H2Sfraction_plot.pdf", bbox_inches="tight")
plt.close()

plt.xlabel("Time [d]")
plt.ylabel("Consumption rate MG [mol/s]")
for case in DuMuxCases:
    plt.plot(case.time, case.convertedMG["H2"], label =case.label, linestyle = case.linestyle)
plt.legend()
plt.savefig("consumption_plotMG.pdf", bbox_inches="tight")
plt.close()

plt.xlabel("Time [d]")
plt.ylabel("Conversion rate geo [mol/s]")
for case in DuMuxCases:
    plt.plot(case.time, case.convertedGeo["H2"], label =case.label, linestyle = case.linestyle)
plt.legend()
plt.savefig("consumption_plotGeo.pdf", bbox_inches="tight")
plt.close()


plt.title("MatBal")
plt.xlabel("Time [d]")
for case in DuMuxCases:
    plt.plot(case.time, case.materialBalanceError["H2"], label =case.label, linestyle = case.linestyle)
plt.legend()
plt.savefig("materialBalanceError.pdf", bbox_inches="tight")
plt.close()

if args.pyvista:
    print("Pyvista export running")
    plotTimes = [2.592e+6, 2*2.592e+6, 3*2.592e+6, 9072000]
    fig, axes = plt.subplots(2, 2, figsize=(15, 14))
    axes = axes.flatten()
    for i, time in enumerate(plotTimes):
        for j, case in enumerate(DuMuxCases):
            reader = pv.get_reader(case.pvd)
            reader.set_active_time_value(time)
            mesh = reader.read()[0]
            referencePoint = [mesh.center[0], mesh.center[1], mesh.bounds[0]]
            data = mesh.sample_over_line(referencePoint,referencePoint,1)

            a = [mesh.bounds[0], mesh.bounds[2], mesh.center[2]]
            b = [mesh.bounds[1], mesh.bounds[3], mesh.center[2]]
            data = mesh.sample_over_line(a,b)
            values = data.get_array("x^H2_gas")
            distance = data['Distance']
            axes[i].plot(distance,values, label =case.label, linestyle = case.linestyle)

        axes[i].set_ylabel("$\mathrm{H_2}$ fraction in the gas phase, -")
        axes[i].set_xlabel("Distance, m")
        axes[i].set_title(f't = {time/60/60/24:.0f}d')
        axes[i].legend()
    plt.savefig('HydrogenOverLine.pdf', bbox_inches="tight")
    plt.close()

    scalingFactor = 1.2

    sargs = dict(
        title_font_size = int(36*scalingFactor),
        label_font_size = int(30*scalingFactor),
        shadow = False,
        n_labels = 3,
        italic = False,
        fmt = "%.1f",
        # font_family = "times",
        color = "black",
        title = r'$c^\mathrm{H_2}_g$',
        height=.85, 
        vertical=True,
        position_x=0.05, 
        position_y=0.05
    )

if args.gif:
    print("Gif export is running")
    # Open a gif
    for case in DuMuxCases:
        reader = pv.get_reader(case.pvd)
        pv.set_plot_theme('document')

        plotter = pv.Plotter(off_screen = True, window_size=[int(1200*scalingFactor) , int(600*scalingFactor)],lighting='three lights')
        plotter.open_gif(case.name +"H2Fraction.gif", loop =1)

        for i, time in enumerate(reader.time_values):
            reader.set_active_time_value(time)
            mesh = reader.read()[0]
            plotter.add_mesh(mesh, scalar_bar_args = sargs, show_edges = True,scalars = "x^H2_gas", smooth_shading = False,cmap="coolwarm", clim = [0, 0.95], reset_camera = True, lighting=False)
            annotation = plotter.add_text(text=f't = {time/60/60/24:.0f}d', position = "upper_right", font_size= 16)
            plotter.camera.zoom(1.22)
            plotter.add_mesh(pv.Tube((1525/2,1525/2,50),(1525/2, 1525/2, 250), radius = 7.5), color = "dimgray" )
            plotter.camera.elevation = 0
            if (isclose(time, 2.592e+6, abs_tol = 1) or i==0):
                plotter.screenshot(case.name +'H2FractionInjection.png', transparent_background=True)
                plotter.save_graphic(case.name +'H2FractionInjection.svg')
                plotter.save_graphic(case.name +'H2FractionInjection.pdf')
            plotter.write_frame()
            plotter.remove_actor(annotation)

        plotter.close()





