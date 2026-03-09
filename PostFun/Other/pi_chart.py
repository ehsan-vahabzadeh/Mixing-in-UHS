from matplotlib import pyplot as plt
import numpy as np


energies = ['Renewable', 'Nuclear', 'Gas', 'Oil'];
Val_2025 = [319,40,720,780]
Val_2050 = [863,79,168,139]
colors = ['#2066a8','#cde1ec','#f6d6c2','#ae282c']
fig, ax = plt.subplots(1, 2, figsize=(10, 7))
ax[0].pie(Val_2025,colors=colors,  labels=energies, autopct='%1.1f%%', textprops={'fontsize': 14}, startangle = 90,  wedgeprops = {"edgecolor" : "white",
                      'linewidth': 2,
                      'antialiased': True})
ax[1].pie(Val_2050, colors=colors,  labels=energies, autopct='%1.1f%%', textprops={'fontsize': 14}, startangle = 90, wedgeprops = {"edgecolor" : "white",
                      'linewidth': 2,
                      'antialiased': True})

# show plot
plt.show()