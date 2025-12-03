import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import os
import glob
from sklearn.preprocessing import LabelEncoder
from pysr import PySRRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sympy import pretty
font = {'family' : 'sans-serif',
        'size'   : 20}
plt.rc('font', **font)
def pysr_fun(X):
    y = X["RF"]
    X = X[["Pe", "Ng"]]
    X = X.values
    y = y.values    
    model = PySRRegressor(
    model_selection="best",  # selects best equation based on loss and complexity
    niterations=30,         # increase for more thorough search
    population_size=100,
    maxdepth=10,
    binary_operators=["*","^"],
    extra_sympy_mappings={"inv": lambda x: 1/x},
    loss="loss(x, y) = (x - y)^2",  # standard MSE
    maxsize=20,             # controls complexity of expressions
    verbosity=1
    )

    model.fit(X, y)
    print(model) 
    print(model.get_best())
    print(model.get_best()["equation"]) 
    y_pred = model.predict(X)
    print("R²:", r2_score(y, y_pred))
    print("MSE:", mean_squared_error(y, y_pred))
    print("MAE:", mean_absolute_error(y, y_pred))

    plt.scatter(y, y_pred, alpha=0.5)
    plt.plot([y.min(), y.max()], [y.min(), y.max()], 'r--')  # 1:1 line
    plt.xlabel("True RF")
    plt.ylabel("Predicted RF")
    plt.title("Predicted vs True")
    plt.grid(True)
    plt.show()
def Pearson(X):
    # Compute Pearson correlation
    corr = X.corr(method='pearson')
    plt.figure(figsize=(12, 10))
    sns.heatmap(corr, annot=True, fmt=".2f",  square=True, linewidths=0.5)
    plt.title("Pearson Correlation Heatmap of Input Features and RF")
    plt.tight_layout()
    plt.show()
    
    spearman_corr = X.corr(method='spearman')
    plt.figure(figsize=(12, 10))
    sns.heatmap(spearman_corr, annot=True, fmt=".2f", cmap='plasma', center=0)
    plt.title("Spearman Correlation Heatmap of Input Features and RF", fontsize=14)
    plt.tight_layout()
    plt.show()
    
def annotate_corr(x, y, **kwargs):
    """Draw correlation coefficient in the upper triangle."""
    r, _ = np.corrcoef(x, y)[0, 1], None
    ax = plt.gca()
    ax.set_axis_off()
    ax.annotate(f"{r:.2f}", xy=(0.5, 0.5), xycoords=ax.transAxes,
                ha='center', va='center', fontsize=32)

def custom_regplot(x, y, **kwargs):
    ax = plt.gca()
    var_names = kwargs.get('label', '')
    
    # Color logic: if x or y is RF_final, use black
    color = 'black' if ax.get_xlabel() == 'RF_final' or ax.get_ylabel() == 'RF_final' else 'skyblue'
    
    sns.regplot(x=x, y=y, lowess=True,
                scatter_kws={'s': 15, 'color': color},
                line_kws={'color': color},
                ax=ax)
    
def pairwise(df):
    sns.set(style="white")
    g = sns.PairGrid(df, height=2, aspect=1)
    g = sns.PairGrid(df, diag_sharey=False, corner=False)
    g.map_lower(
    sns.scatterplot,
    s=15, alpha=0.6, color='grey'
    )
    g.map_upper(annotate_corr, fontsize=32)
    g.map_diag(sns.histplot, kde=True, color="grey", edgecolor='black',alpha = 0.6, bins=15)
    for ax in g.axes.flatten():
        if ax is not None:
            ax.tick_params(axis='x', labelsize=20)
            ax.tick_params(axis='y', labelsize=20)
            ax.set_xlabel(ax.get_xlabel(), fontsize=18)
            ax.set_ylabel(ax.get_ylabel(), fontsize=18)

    plt.tight_layout()
    plt.show()
    
def main(input_directory):
    rf_values = []
    labels = []
    inputs = []
    df_list = []
    # file_path = os.path.join(input_directory, 'mixing_results_new.xlsx')
    file_path = os.path.join(input_directory, 'mixing_results_plot.xlsx')
    df = pd.read_excel(file_path)
    df = df.drop(columns=['label','CushionGas','theta','CG Ratio','Nusselt_number','Raileigh_number','Pe','Ng','theta','Fo','max_pressure','CushionGas','CG Ratio'])
    df = df.dropna()  # Drop rows with NaN values
    df = df[df['RF_final'] > 0]
    df = df.rename(columns = {
        'RF_final': 'RF',
        'FlowRate': 'Flow Rate',
        'CycleLength': 'Cycle Length',
        'delta_rho': 'Density',
        })
    
    df_list.append(df)
    if df_list:
        df = pd.concat(df_list, ignore_index=True)
    else:
        df = pd.DataFrame()
    df = df[['Flow Rate','Cycle Length', 'porosity', 'RF', 'Permeability', 'Pressure', 'Temperature','Density' ]]    
    # Pearson(df)
    pairwise(df)
    # pysr_fun(df)
      
    
os.chdir("Y:\\Mixing Results\\July")  # Change to the directory containing your simulation files
# os.chdir("Y:\\Mixing Results\\May\\NewCH4")  # Change to the directory containing your simulation files
# os.chdir("Z:\\Mixing Results\\Feb\\Results\\30 Meter Height Reservoir")  # Change to the directory containing your simulation files
input_directory = os.getcwd()
main(input_directory) 