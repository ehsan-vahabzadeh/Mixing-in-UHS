import numpy as np 
from sklearn import datasets
import pandas as pd
import matplotlib.pyplot as plt 
from scipy.stats import gamma

california = datasets.fetch_california_housing()
cal_data = california.data
df_cal = pd.DataFrame(cal_data, columns = california.feature_names)
print(df_cal.describe())
single_data = df_cal["MedInc"]
mean_avg_data =single_data.mean()
std_avg_data = single_data.std()
print(mean_avg_data, std_avg_data)
k, loc, theta = gamma.fit(single_data, floc=0)
gen_data = np.linspace(min(single_data), max(single_data), 100)
pdf_fitted = gamma.pdf(gen_data, k, loc= 0, scale = theta)
gamma_cdf = 1-  gamma.cdf(2, k, loc=0, scale= theta)
print("Gamma CDF at 6:", gamma_cdf)
plt.hist(single_data, density =True, bins=30, alpha=0.5, color='gray', edgecolor='black')
plt.plot(gen_data, pdf_fitted, 'r-')
plt.show()


# print(df_cal.describe())