import io
import pandas as pd
import matplotlib.pyplot as plt

# ==== paste your table exactly as given (tabs are fine) ====
data = io.StringIO("""
Year	Oil	Gas	Coal	Renewables	Nuclear
1965	38.05271111	13.30931057	33.03665624	13.60566492	1.995657163
1975	45.52716647	16.57748961	25.13637968	10.19099586	2.567968373
1985	39.14479757	18.8764595	27.63190254	10.33321507	4.013625318
1995	38.90839857	20.80017177	25.76861357	9.802602334	4.720213757
2005	36.75589283	21.45488773	28.53179167	8.818107111	4.439320653
2015	33.83867961	23.05945741	29.36894317	9.451719789	4.281200019
2025	32.49304039	23.94533453	27.09724442	12.16610142	4.298279243
2035	29.60152922	25.53393576	22.49906323	17.60633974	4.759132053
2050	24.22849375	26.50588604	15.66531675	27.92265794	5.677645517
""")

df = pd.read_csv(data, sep=r"\s+")

# Combine into two series
df["Fossil"]      = df["Oil"] + df["Natural"] + df["Coal"] if "Natural" in df.columns else \
                    df["Oil"] + df["Gas"] + df["Coal"]
df["Renewables+"] = df["Renewables"] + df["Nuclear"] if "Nuclear" in df.columns else \
                    df["Renewables"] + df["Nuclear"]

# --- Presentation style ---
plt.rcParams.update({
    "figure.figsize": (11, 6.5),
    "font.size": 18,
    "axes.labelsize": 20,
    "axes.titlesize": 22,
    "legend.fontsize": 20,
    "xtick.labelsize": 20,
    "ytick.labelsize": 20,
    "lines.linewidth": 3.2,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

fig, ax = plt.subplots()
alpha_val = 1
ax.plot(df["Year"], df["Oil"],      label="Oil", linewidth=5,
        color="dimgray", marker="o",alpha=alpha_val) 
ax.plot(df["Year"], df["Gas"],      label="Gas",
        color="darkgray", marker="o",alpha=alpha_val) 
ax.plot(df["Year"], df["Coal"],      label="Coal",
        color="lightgray", marker="o",alpha=alpha_val) 

ax.plot(df["Year"], df["Renewables"],      label="Renewables",linewidth=5,
        color="forestgreen", marker="o",alpha=alpha_val)
ax.plot(df["Year"], df["Nuclear"],      label="nuclear + hydro",
        color="lime", marker="o",alpha=alpha_val)
# ax.plot(df["Year"], df["Fossil"],      label="Fossil",
#         color="black", marker="o")
# ax.plot(df["Year"], df["Renewables+"], label="Renewables+",
#         color="lime", marker="o")

# --- Add top & right axes ---
ax.spines['top'].set_visible(True)
ax.spines['right'].set_visible(True)
ax.set_xticks(df["Year"])
ax.set_title("Global Primary Energy Share by Source")
ax.set_xlabel("Year")
ax.set_ylabel("Share of primary energy (%)")

ax.set_ylim(0, 50)
ax.set_xlim(1960, 2055)

ax.legend(loc="best", frameon=True)
ax.grid(alpha=0.35)

plt.tight_layout()
plt.show()