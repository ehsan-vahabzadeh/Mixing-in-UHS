
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pyvista as pv
from numpy import genfromtxt
import subprocess
import vtk
from math import isclose
import pandas as pd

## Plot of relevant results
try:
    plt.style.use('~/Templates/matplotlib/plot_style.txt')
except:
    print('plotstyle not found')

mpl.rcParams['figure.figsize'] = 8, 6

class DuMuxData:
    def __init__(self):
        self.path = ('../build-cmake/test/porousmediumflow/2pncgeobio/biogeochemical/')
        self.time = genfromtxt('time.txt')/(60*60*24)
        self.rates = genfromtxt("well1rate.txt")
        self.fieldrate = np.sum(self.rates,1)
        self.averagereservoirpressure =  genfromtxt("averagepressure.txt")
        self.convertedMG =  genfromtxt("convertedMG.txt")
        self.convertedGeo =  genfromtxt("convertedGeo.txt")
        self.inventory = genfromtxt("inventory.txt")
        self.materialBalanceError = genfromtxt("materialBalanceError.txt")
        self.bhp = genfromtxt("bhp.txt")/1e5
        

class CMG:
    def __init__(self):
        self.path = ('./GEM_Comparison/')
        self.time = genfromtxt(self.path + 'time.txt')
        self.bhp = genfromtxt(self.path + "bhp.txt")/100


DuMux = DuMuxData()

CMGData = CMG()

cases = [DuMux, CMGData]

plt.xlabel("Time [d]")
plt.ylabel("Fieldrate [mol/s]")
plt.plot(DuMux.time, DuMux.fieldrate)
plt.savefig("fieldrate_plot.pdf", bbox_inches="tight")
plt.savefig("fieldrate_plot.png", transparent=True, dpi=1200)
plt.close()

plt.xlabel("Time [d]")
plt.ylabel("Average reservoir pressure [bar]")
for case in cases:
    # plt.plot(case.time, case.averagereservoirpressure/1e5, label = 'Average Res. P')
    plt.plot(case.time, case.bhp, label = "BHP")
plt.legend()
plt.savefig("pressure_plot.pdf", bbox_inches="tight")
plt.savefig("pressure_plot.png", transparent=True, dpi=1200)
plt.close()

plt.xlabel("Time [d]")
plt.ylabel("$\mathrm{H_2}$ Fraction [-]")
plt.plot(DuMux.time, DuMux.rates[:,3]/DuMux.fieldrate)
# plt.plot(CMGData.time, CMGData.h2fraction)
plt.savefig("H2fraction_plot.pdf", bbox_inches="tight")
plt.savefig("H2fraction_plot.png", transparent=True, dpi=1200)
plt.close()

plt.xlabel("Time [d]")
plt.ylabel("Consumption rate MG [mol/s]")
plt.plot(DuMux.time, DuMux.convertedMG[:,3])
plt.savefig("consumption_plotMG.pdf", bbox_inches="tight")
plt.savefig("consumption_plotMG.png", transparent=True, dpi=1200)
plt.close()

plt.xlabel("Time [d]")
plt.ylabel("Conversion rate geo [mol/s]")
plt.plot(DuMux.time, DuMux.convertedGeo[:,3])
plt.savefig("consumption_plotGeo.pdf", bbox_inches="tight")
plt.savefig("consumption_plotGeo.png", transparent=True, dpi=1200)
plt.close()

plt.title("MatBal")
plt.xlabel("Time [d]")
plt.ylabel("MatBalError")
plt.plot(DuMux.time, DuMux.materialBalanceError[:,3])
plt.savefig("materialBalanceError.pdf", bbox_inches="tight")
plt.savefig("materialBalanceError.png", transparent=True, dpi=1200)
plt.close()



index = 0
plotTimes = [2.592e+6, 2*2.592e+6, 3*2.592e+6, 1e9]

fig = plt.figure()

h2fractiongas = []
co2fractiongas = []
nMg = []


reader = pv.get_reader("biogeochemical_microbes.pvd")
for time in reader.time_values:
    reader.set_active_time_value(time)
    mesh = reader.read()[0]
    referencePoint = [mesh.center[0], mesh.center[1], mesh.bounds[0]]
    data = mesh.sample_over_line(referencePoint,referencePoint,1)
    h2fractiongas.append(data.get_array("x^H2_gas")[0])
    co2fractiongas.append(data.get_array("x^CO2_gas")[0])
    nMg.append(data.get_array("n_MG")[0])
    

    if isclose(time, plotTimes[index], abs_tol = 1):
        # reader.set_active_time_value(time)
        # mesh = reader.read()[0]
        a = [mesh.bounds[0], mesh.bounds[2], mesh.center[2]]
        b = [mesh.bounds[1], mesh.bounds[3], mesh.center[2]]
        data = mesh.sample_over_line(a,b)
        values = data.get_array("x^H2_gas")
        distance = data['Distance']
        index +=1
        plt.plot(distance,values, label =f't = {time/60/60/24:.0f} days')

plt.ylabel("$\mathrm{H_2}$ fraction in the gas phase, -")
plt.xlabel("Distance, m")
plt.legend()
plt.savefig("HydrogenOverLine.pdf", bbox_inches="tight")
plt.close()

np.savetxt("h2fractionFirstCell.txt",h2fractiongas)
np.savetxt("co2fractionFirstCell.txt",co2fractiongas)
np.savetxt("nMg.txt",nMg)

sargs = dict(
    title_font_size = 50,
    label_font_size = 36,
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

# Open a gif

reader = pv.get_reader("biogeochemical_microbes.pvd")
pv.set_plot_theme('document')

plotter = pv.Plotter(off_screen = True, window_size=[1280, 600])
plotter.open_gif("H2Fraction.gif", loop =1)

for time in reader.time_values:
    reader.set_active_time_value(time)
    mesh = reader.read()[0]
    plotter.add_mesh(mesh, scalar_bar_args = sargs, show_edges = True, scalars = "x^H2_gas", smooth_shading = False,cmap="coolwarm", clim = [0, 0.95], reset_camera = True)
    annotation = plotter.add_text(text=f't = {time/60/60/24:.3f}d', position = "upper_right", font_size= 16)
    plotter.camera.zoom(1.25)
    if (isclose(time, 2.592e+6, abs_tol = 1)):
        plotter.screenshot('H2FractionInjection.png', transparent_background=True)
        plotter.save_graphic('H2FractionInjection.pdf')
    plotter.write_frame()
    plotter.remove_actor(annotation)

plotter.close()


