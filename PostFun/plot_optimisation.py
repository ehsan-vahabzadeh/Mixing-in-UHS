import os, re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --------- SETTINGS ---------
INPUT_DIR = r"Y:\Mixing Results\July"
CL = 180
TWH = 50
fname = f"optimal_plan_CL{CL}_TWh{TWH}.xlsx"
path = os.path.join(INPUT_DIR, fname)

# column names exactly as in your file
COL_INJ_TWH = "Cum H2 Injected [Twh]"
COL_PRO_TWH = "Cum H2 Produced [Twh]"
COL_INJ_M3  = "Cum H2 Injected [m3]"
COL_PRO_M3  = "Cum H2 Produced [m3]"
COL_NET_M3  = "Net H2 Stored [m3]"
COL_LCOS    = "LCOS"
COL_PERM    = "Permeability [mD]"
# ----------------------------

xls = pd.ExcelFile(path)  # needs openpyxl installed
cycle_sheets = sorted(
    (int(m.group(1)), s)
    for s in xls.sheet_names
    for m in [re.match(r"^cycle_(\d+)$", s)]
    if m
)

rows = []
for cyc, sname in cycle_sheets:
    df = pd.read_excel(xls, sheet_name=sname)

    inj_twh = df.get(COL_INJ_TWH, pd.Series([np.nan]*len(df))).sum(min_count=1)
    pro_twh = df.get(COL_PRO_TWH, pd.Series([np.nan]*len(df))).sum(min_count=1)

    # if TWh columns missing, fall back to m3 (keeps code robust)
    if not np.isfinite(inj_twh) or not np.isfinite(pro_twh):
        inj_twh = df[COL_INJ_M3].sum() * 39.41 * 0.08988 / 1e9   # m3 -> TWh
        pro_twh = df[COL_PRO_M3].sum() * 39.41 * 0.08988 / 1e9

    net_twh = inj_twh - pro_twh  # net stored (energy terms)

    # LCOS aggregation
    lcos = pd.to_numeric(df[COL_LCOS], errors="coerce")
    w    = pd.to_numeric(df.get(COL_PRO_TWH, pd.Series(0)), errors="coerce").fillna(0.0)
    # weighted by produced TWh; if all weights zero, fall back to mean
    lcos_w = (lcos.multiply(w)).sum() / w.sum() if w.sum() > 0 else lcos.mean()
    avg_perm = pd.to_numeric(df[COL_PERM], errors="coerce").mean()
    rows.append(dict(cycle=cyc, inj_twh=inj_twh, pro_twh=pro_twh,
                     net_twh=net_twh, lcos_mean=lcos.mean(), lcos_w=lcos_w, avg_perm=avg_perm))

agg = pd.DataFrame(rows).sort_values("cycle").reset_index(drop=True)

# ======= PLOTS =======

plt.figure(figsize=(14,4.5))

# (1) Injected vs Produced TWh by cycle
ax1 = plt.subplot(1,4,1)
ax1.plot(agg["inj_twh"], agg["pro_twh"],  "-o")
# ax1.plot(agg["cycle"], agg["inj_twh"],  "-o", label="Injected (TWh)")
# ax1.plot(agg["cycle"], agg["pro_twh"],  "-o", label="Produced (TWh)")
ax1.set_xlabel("Cycle No.")
ax1.set_ylabel("Energy (TWh)")
ax1.set_title(f"CL={CL} d, Target={TWH} TWh")
ax1.grid(alpha=0.3); ax1.legend()

# (2) LCOS vs cycle (weighted & mean)
ax2 = plt.subplot(1,4,2)
ax2.plot(agg["cycle"], agg["lcos_w"],   "-o", label="LCOS (weighted by Produced TWh)")
ax2.plot(agg["cycle"], agg["lcos_mean"],"--o", label="LCOS (simple mean)")
ax2.set_xlabel("Cycle No.")
ax2.set_ylabel("LCOS")
ax2.set_title("LCOS by cycle")
ax2.grid(alpha=0.3); ax2.legend()

# (3) LCOS vs Net Stored TWh (one point per cycle)
ax3 = plt.subplot(1,4,3)
ax3.scatter(agg["pro_twh"], agg["lcos_w"])
for c, x, y in zip(agg["cycle"], agg["pro_twh"], agg["lcos_w"]):
    ax3.annotate(str(int(c)), (x, y), textcoords="offset points", xytext=(5,5), fontsize=9)
ax3.set_xlabel("Net Stored (TWh)  = Injected − Produced")
ax3.set_ylabel("LCOS (weighted)")
ax3.set_title("LCOS vs Net Stored")
ax3.grid(alpha=0.3)

# (4) NEW: Avg permeability vs cycle
ax4 = plt.subplot(1,4,4)
ax4.plot(agg["cycle"], agg["avg_perm"], "-o", color="purple")
ax4.set_xlabel("Cycle No.")
ax4.set_ylabel("Average Permeability (mD)")
ax4.set_title("Average Permeability vs Cycle")
ax4.grid(alpha=0.3)

plt.tight_layout()
plt.show()

# Optional: print the table you plotted
print(agg.to_string(index=False))
